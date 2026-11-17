#!/usr/bin/env python3
"""Whole-suite runs on copies without the checks that fire in no case (part `no-fire/`).

    python3 -I -B nofire_deletions.py [--dry [--collect] [--check-deletions] [--no-verify]]
        [--libraries NAME ...] [--only NAME ...] [--expect-total N]
        [--clone NAME=DIR ...] [--python NAME=PYTHON ...] [--work DIR] [--workers N]
        [--out FILE] [--summary FILE] [--records DIR] [--toolkit DIR] [--subjects DIR] [--generated DIR]

The toolkit is ../../target-reach (T below, `--toolkit`); this script imports its
runner, `reach/run.py`, and changes none of its files.

Checks. For each library of `--libraries` (default google-auth, oauthlib,
authlib, joserfc), the rows of `<generated>/<name>/checks.csv` (default
`T/generated`) with `reachable` = `yes` and `cases_fired` = `0`. The script
prints the number per library and stops, before anything else, when their sum
is not `--expect-total` (default 103). Every such check must be a check of
the subject files in `<subjects>/<name>/checks.json` (default `T/subjects`),
statically reachable.

Run (without --dry), for each library of `--only` (default: all of
`--libraries`), in a work folder `<work>/<name>` (default `<work>` is
../work/no-fire), with T's own functions:

1. `verify` (T's step, unchanged): clone at the commit and clean, digests of
   the subject and test files, CPython 3.12.3, the packages of
   `<subjects>/<name>/requirements.txt` and nothing else but pip.
2. `whole_baseline` (T's step `whole-baseline`, unchanged): the whole suite
   2 times, each on its own unmodified copy; the tests that pass in both
   runs, and the time limit max(60 s, 10 x the slower run).
3. The manifest of the deletion copies: for each check, `deletion_copy`
   (T's function, as the step `deletions` makes its copies) gives the removed
   statements and the SHA-256 of the changed file; written to
   `<work>/<name>/records/deletions/manifest.json`, the file that T's
   `whole_deletions` reads. The copies made for it are removed.
4. `whole_deletions` (T's step `whole-deletions`, unchanged): the whole
   suite on a fresh deletion copy for every check and on 1 unmodified
   control copy, `--workers` (default 10) copies at a time, the time limit of
   step 2 for all the suite runs of a copy together; a run that exceeds it,
   or of which a pytest call leaves no result file, is repeated 1 time, alone,
   on a fresh copy. Detection is T's (PROTOCOL.md, section 4, "Whole suite"):
   a test that passes in both runs of step 2 does not pass on the copy (it
   fails, has an error, is skipped or is absent), or the copy's run is broken
   (time limit exceeded or no result file, 2 times).

T's `whole_run` does not keep the exit status of pytest. To record it, this
script puts 2 thin wrappers into the loaded module `reach.run` of its own
process: `whole_run` calls T's `whole_run` unchanged and notes which copy it
runs, and `subprocess.run` calls the standard `subprocess.run` unchanged and
notes the exit status (or "timeout") of each pytest call that writes a junit
XML file. The output of those calls, which T does not keep, goes to
`<work>/<name>/logs/whole/`.

Output: `--out` (default `deletions-nofire.csv` next to this file), 1 row for
the control copy (`_control`) and 1 per check, libraries in the order given,
checks sorted, with the columns

    library, check, returncode, detected, failing_tests, timed_out, no_result,
    runs, first_run_returncode, tests_not_passing, failed_or_error, skipped,
    absent, detected_by_failure, refused_attempts, seconds

`returncode`: `run=status` per suite run of subject.json, joined by `;`, for
the run that counts (the repeated run when there were 2); `not run` when the
time limit was used up before the call started. `failing_tests`: every test
that passes in both runs of step 2 and does not pass on the copy, as
`run|class::name (failed|skipped|absent)`, joined by ` ; `; empty when the run
is broken. `detected_by_failure`: yes when at least 1 of them fails or has an
error (the narrower reading "a test fails or errors"). `refused_attempts`:
outside connections that the offline module refused. A summary per library
(baseline counts, time limit, T's deposited baseline, the control) goes to
`--summary` (default `summary.json` next to this file), T's records
whole/base.json and whole/deletions.json to `--records/<name>/` (default `records/`).

--dry: nothing runs on the copies. For each library: the checks with their
files and the lines of their raise statements, T's `verify` (static; skipped
with --no-verify), and every pytest command the run would give, with its
folder and environment (built as T's `whole_run` builds them; the unit tests
compare the two). --collect adds, on 1 fresh unmodified copy, `pytest
--collect-only -q` with the options of each suite run, to see that the
environment imports. --check-deletions applies T's `delete_check` to each
check's file in memory (nothing is written, nothing runs) and reports the
statements it would change.

Defaults of --clone and --python: `<work>/src/<name>` (with subject.json's
`repository_directory` appended) and `<work>/venvs/<name>/bin/python`.

--only reruns some of the libraries: the rows and summaries of the others are
kept from the files of --out and --summary, in the order of --libraries.
"""
from __future__ import annotations

import argparse
import csv
import importlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent                     # target-reach-extension/no-fire
EXTENSION = HERE.parent
TOOLKIT = EXTENSION.parent / "target-reach"
WORK = EXTENSION / "work" / "no-fire"
LIBRARIES = ("google-auth", "oauthlib", "authlib", "joserfc")
EXPECT_TOTAL = 103
COLUMNS = ("library", "check", "returncode", "detected", "failing_tests", "timed_out", "no_result", "runs",
           "first_run_returncode", "tests_not_passing", "failed_or_error", "skipped", "absent",
           "detected_by_failure", "refused_attempts", "seconds")


def load_toolkit(toolkit: Path):
    """T's runner module `reach.run`, imported from `toolkit`."""
    if str(toolkit) not in sys.path:
        sys.path.insert(0, str(toolkit))
    rm = importlib.import_module("reach.run")
    if Path(rm.__file__).resolve().parent.parent != toolkit.resolve():
        raise SystemExit(f"reach.run was imported from {rm.__file__}, not from {toolkit}")
    return rm


def pairs(values: list[str] | None, option: str) -> dict[str, str]:
    out = {}
    for value in values or []:
        name, sep, path = value.partition("=")
        if not sep or not name or not path:
            raise SystemExit(f"{option} takes NAME=PATH, not {value!r}")
        out[name] = path
    return out


# -- the checks ------------------------------------------------------------------------

def population_rows(checks_csv: Path) -> tuple[int, list[dict]]:
    """(number of rows, rows with reachable yes and cases_fired 0) of 1 checks.csv."""
    with checks_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return len(rows), [r for r in rows if r["reachable"] == "yes" and r["cases_fired"] == "0"]


def population(generated: Path, subjects: Path, libraries: list[str], expect_total: int) -> dict[str, list[dict]]:
    """Library -> the checks of checks.json that checks.csv gives as reachable and never fired."""
    found, total = {}, 0
    for name in libraries:
        n_rows, rows = population_rows(generated / name / "checks.csv")
        found[name] = rows
        total += len(rows)
        print(f"{name}: {len(rows)} of the {n_rows} rows of {generated / name / 'checks.csv'} "
              f"have reachable yes and cases_fired 0", flush=True)
    print(f"total: {total}", flush=True)
    if total != expect_total:
        raise SystemExit(f"the checks number {total}, not {expect_total}: nothing is run")
    out = {}
    for name, rows in found.items():
        defs = json.loads((subjects / name / "checks.json").read_text(encoding="utf-8"))
        by_id = {c["id"]: c for c in defs["checks"]}
        checks = []
        for row in rows:
            check = by_id.get(row["check"])
            if check is None or check["file"] != row["file"] or check["role"] != "subject" \
                    or not check["reachable"]:
                raise SystemExit(f"{name}: {row['check']} of checks.csv is no reachable subject check "
                                 f"of {subjects / name / 'checks.json'}")
            checks.append(check)
        if len({c["id"] for c in checks}) != len(checks):
            raise SystemExit(f"{name}: a check occurs twice in checks.csv")
        out[name] = sorted(checks, key=lambda c: c["id"])
    return out


# -- the context of T's runner ------------------------------------------------------------

def make_context(rm, name: str, subjects: Path, work: Path, clone: str | None, python: str | None,
                 workers: int):
    subject_path = subjects / name / "subject.json"
    subject = json.loads(subject_path.read_text(encoding="utf-8"))
    if clone is None:
        clone = str(work / "src" / name / (subject.get("repository_directory") or ""))
    if python is None:
        python = str(work / "venvs" / name / "bin" / "python")
    args = argparse.Namespace(subject=str(subject_path), defs=str(subjects / name), work=str(work / name),
                              clone=clone, python=python, workers=workers, out=None, witnesses=None)
    return rm.Context(args)


def whole_commands(rm, ctx, name: str, cwd: Path) -> list[dict]:
    """The pytest calls of T's `whole_run(ctx, name, cwd, ...)`, as it builds them."""
    out = []
    for run in ctx.subject["suite_runs"]:
        xml = ctx.records / "whole" / "xml" / f"{name}.{run['name']}.xml"
        offline = xml.with_suffix(".offline.tmp")
        cmd = [str(ctx.python), "-m", "pytest", "-q", *ctx.subject.get("pytest_args", []),
               *run.get("args", []), *rm.OFFLINE, "--rootdir=.", "--tb=no",
               "--continue-on-collection-errors", f"--junitxml={xml}", *run["paths"]]
        env = ctx.env(PYTHONPATH=ctx.pythonpath(cwd, recorder=False), OFFLINE_OUT=str(offline))
        out.append({"run": run["name"], "cwd": str(cwd), "cmd": cmd, "env": env})
    return out


def deposited_whole_base(generated: Path, name: str) -> dict | None:
    """records/whole/base.json of T's deposited records.tar.xz, or None."""
    path = generated / name / "records.tar.xz"
    if not path.exists():
        return None
    with tarfile.open(path) as tar:
        try:
            member = tar.extractfile("records/whole/base.json")
        except KeyError:
            return None
        return json.loads(member.read().decode("utf-8")) if member else None


# -- the exit status of T's pytest calls ----------------------------------------------------

def junit_path(cmd) -> str | None:
    for part in cmd if isinstance(cmd, (list, tuple)) else []:
        if isinstance(part, str) and part.startswith("--junitxml="):
            return part.split("=", 1)[1]
    return None


def text_of(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


class _SubprocessProxy:
    """Stands for the module `subprocess` inside `reach.run`: `run` is observed, the rest is the module."""

    def __init__(self, observer: "Observer") -> None:
        self._observer = observer

    def run(self, *args, **kwargs):
        return self._observer.run(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(subprocess, name)


class Observer:
    """Notes the exit status of every pytest call that T's `whole_run` makes, by copy and suite run."""

    def __init__(self, rm) -> None:
        self.rm = rm
        self.real_whole_run = rm.whole_run
        self.local = threading.local()
        self.lock = threading.Lock()
        self.attempts: dict[str, list[dict[str, object]]] = {}

    def install(self) -> None:
        self.rm.subprocess = _SubprocessProxy(self)
        self.rm.whole_run = self.whole_run

    def uninstall(self) -> None:
        self.rm.subprocess = subprocess
        self.rm.whole_run = self.real_whole_run

    def whole_run(self, ctx, name, cwd, timeout):
        with self.lock:
            attempt = len(self.attempts.get(name, [])) + 1
        self.local.codes, self.local.attempt = {}, attempt
        codes = self.local.codes
        try:
            return self.real_whole_run(ctx, name, cwd, timeout)
        finally:
            self.local.codes = None
            by_run = {}
            for run in ctx.subject["suite_runs"]:
                xml = str(ctx.records / "whole" / "xml" / f"{name}.{run['name']}.xml")
                by_run[run["name"]] = codes.get(xml, "not run")
            with self.lock:
                self.attempts.setdefault(name, []).append(by_run)

    def run(self, cmd, *args, **kwargs):
        codes = getattr(self.local, "codes", None)
        xml = junit_path(cmd)
        if codes is None or xml is None:
            return subprocess.run(cmd, *args, **kwargs)
        try:
            proc = subprocess.run(cmd, *args, **kwargs)
        except subprocess.TimeoutExpired as e:
            codes[xml] = "timeout"
            self.save_log(xml, text_of(e.stdout) + text_of(e.stderr))
            raise
        codes[xml] = proc.returncode
        self.save_log(xml, text_of(proc.stdout) + text_of(proc.stderr))
        return proc

    def save_log(self, xml: str, text: str) -> None:
        path = Path(xml)                                  # <work>/records/whole/xml/<copy>.<run>.xml
        folder = path.parents[3] / "logs" / "whole"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{path.stem}.attempt-{self.local.attempt}.log").write_text(text, encoding="utf-8")


# -- the run ----------------------------------------------------------------------------------

def build_manifest(rm, ctx, checks: list[dict]) -> dict:
    """manifest.json as T's step `deletions` writes it, from copies made by T's `deletion_copy`."""
    root = ctx.copies / "manifest"
    manifest = {}
    for check in checks:
        dest = root / rm.safe(check["id"])
        changed, digest = rm.deletion_copy(ctx, check, dest)
        if not changed:
            raise SystemExit(f"{check['id']}: deleting the check changes no statement")
        manifest[check["id"]] = {"dir": rm.safe(check["id"]), "file": check["file"], "removed": changed,
                                 "sha256_after": digest}
        shutil.rmtree(dest)
    shutil.rmtree(root, ignore_errors=True)
    return manifest


def rows_of(rm, ctx, name: str, manifest: dict, observer: Observer) -> list[dict]:
    base = rm.load_json(ctx.records / "whole" / "base.json")
    results = rm.load_json(ctx.records / "whole" / "deletions.json")
    passing = base["passing"]
    runs = [r["name"] for r in ctx.subject["suite_runs"]]
    out = []
    for cid in ["_control", *sorted(manifest)]:
        r = results[cid]
        attempts = observer.attempts.get(rm.safe(cid), [])
        if len(attempts) != r["runs"]:
            raise SystemExit(f"{name} {cid}: {len(attempts)} observed runs, {r['runs']} in deletions.json")
        codes = ";".join(f"{run}={attempts[-1].get(run, 'not run')}" for run in runs)
        first = ";".join(f"{run}={attempts[0].get(run, 'not run')}" for run in runs) if r["runs"] == 2 else ""
        broken = bool(r["timed_out"] or r["no_result"])
        labeled = []
        if not broken:
            outcomes = {}
            for run in runs:
                outcomes.update(rm.junit_outcomes(ctx.records / "whole" / "xml" / f"{rm.safe(cid)}.{run}.xml",
                                                  run))
            lost = [k for k in passing if outcomes.get(k) != "passed"]
            if len(lost) != r["tests_not_passing"] or lost[:10] != r["examples"]:
                raise SystemExit(f"{name} {cid}: the result files give {len(lost)} tests not passing, "
                                 f"deletions.json {r['tests_not_passing']}")
            labeled = [(k, outcomes.get(k, "absent")) for k in lost]
        kinds = [kind for _, kind in labeled]
        refused = r["refused"]
        out.append({
            "library": name, "check": cid, "returncode": codes, "detected": "yes" if r["detected"] else "no",
            "failing_tests": " ; ".join(f"{k} ({kind})" for k, kind in labeled),
            "timed_out": "yes" if r["timed_out"] else "no", "no_result": ";".join(r["no_result"]),
            "runs": r["runs"], "first_run_returncode": first, "tests_not_passing": r["tests_not_passing"],
            "failed_or_error": kinds.count("failed"), "skipped": kinds.count("skipped"),
            "absent": kinds.count("absent"), "detected_by_failure": "yes" if "failed" in kinds else "no",
            "refused_attempts": "" if refused is None else refused["attempts"], "seconds": r["seconds"]})
    return out


def run_library(rm, ctx, name: str, checks: list[dict], observer: Observer, generated: Path) -> tuple[list, dict]:
    for stale in (ctx.records / "whole", ctx.records / "deletions", ctx.copies):  # nothing of an earlier run
        if stale.exists():
            shutil.rmtree(stale)
    observer.attempts.clear()                         # copy names such as base-1 recur in every library
    start = time.time()
    rm.verify(ctx)
    rm.whole_baseline(ctx)
    manifest = build_manifest(rm, ctx, checks)
    rm.dump(ctx.records / "deletions" / "manifest.json", manifest)
    rm.whole_deletions(ctx)
    rows = rows_of(rm, ctx, name, manifest, observer)
    base = rm.load_json(ctx.records / "whole" / "base.json")
    deposited = deposited_whole_base(generated, name)
    summary = {
        "checks": len(checks), "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start)),
        "ended": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "whole_baseline": {"counts": base["counts"], "seconds": base["seconds"],
                           "timeout_seconds": base["timeout_seconds"], "refused": base["refused"],
                           "returncodes": {f"base-{i}": observer.attempts.get(f"base-{i}") for i in (1, 2)}},
        "deposited_whole_baseline": None if deposited is None else {
            "passing in both": len(deposited["passing"]), "timeout_seconds": deposited["timeout_seconds"],
            "passing now and not in the deposit": len(set(base["passing"]) - set(deposited["passing"])),
            "passing in the deposit and not now": len(set(deposited["passing"]) - set(base["passing"]))},
        "control": next(r for r in rows if r["check"] == "_control"),
        "detected": sum(1 for r in rows if r["check"] != "_control" and r["detected"] == "yes"),
        "not_detected": sorted(r["check"] for r in rows if r["check"] != "_control" and r["detected"] == "no"),
    }
    print(f"{name}: {summary['detected']} of {len(checks)} deletions detected; control detected: "
          f"{summary['control']['detected']}", flush=True)
    return rows, summary


def kept_rows(path: Path, names: list[str]) -> list[dict]:
    """The rows of an earlier --out file for the libraries outside `names`."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [r for r in csv.DictReader(handle) if r["library"] not in names]


def in_order(rows: list[dict], libraries: list[str]) -> list[dict]:
    """The rows sorted by library in the order of --libraries; the order within a library is kept."""
    return sorted(rows, key=lambda r: libraries.index(r["library"]) if r["library"] in libraries else len(libraries))


def keep_records(ctx, dest: Path) -> None:
    """T's records whole/base.json and whole/deletions.json of a library, copied to dest/whole/."""
    (dest / "whole").mkdir(parents=True, exist_ok=True)
    for name in ("base.json", "deletions.json"):
        shutil.copy2(ctx.records / "whole" / name, dest / "whole" / name)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


# -- the dry mode -------------------------------------------------------------------------

def collect(rm, ctx) -> list[dict]:
    """`pytest --collect-only -q` per suite run on 1 fresh unmodified copy, with the run's options."""
    dest = ctx.copies / "collect"
    rm.make_copy(ctx, dest)
    out = []
    try:
        for run in ctx.subject["suite_runs"]:
            offline = ctx.logs / f"collect.{run['name']}.offline.tmp"
            offline.parent.mkdir(parents=True, exist_ok=True)
            cmd = [str(ctx.python), "-m", "pytest", "--collect-only", "-q", *ctx.subject.get("pytest_args", []),
                   *run.get("args", []), *rm.OFFLINE, "--rootdir=.", "--continue-on-collection-errors",
                   *run["paths"]]
            proc = subprocess.run(cmd, cwd=dest, env=ctx.env(PYTHONPATH=ctx.pythonpath(dest, recorder=False),
                                                             OFFLINE_OUT=str(offline)),
                                  capture_output=True, text=True, timeout=1800)
            (ctx.logs / f"collect.{run['name']}.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
            lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
            refused = rm.refused(offline)
            out.append({"run": run["name"], "returncode": proc.returncode, "last_line": lines[-1] if lines else "",
                        "refused": None if refused is None else refused["attempts"]})
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    return out


def dry(rm, ctx, name: str, checks: list[dict], args, generated: Path) -> None:
    print(f"== {name}: {len(checks)} checks; clone {ctx.clone}; python {ctx.python}; work {ctx.work}", flush=True)
    if not args.no_verify:
        rm.verify(ctx)
    deposited = deposited_whole_base(generated, name)
    print(f"time limit: max(60 s, 10 x the slower whole-baseline run), from the new whole-baseline; "
          f"T's deposited whole-baseline: "
          + ("none" if deposited is None else f"{len(deposited['passing'])} tests pass in both runs, "
             f"limit {deposited['timeout_seconds']} s"), flush=True)
    for check in checks:
        lines = ";".join(f"{a}-{z}" if a != z else str(a) for a, z in check["lines"])
        extra = ""
        if args.check_deletions:
            source = ctx.clone / rm.rel_to_source(ctx.subject, check["file"])
            _, changed = rm.delete_check(rm.read_source(source), check)
            extra = f"; delete_check changes {len(changed)} statement(s)"
        print(f"check {check['id']}: {check['file']} line(s) {lines}{extra}", flush=True)
    copies = [(f"base-{i}", ctx.copies / f"whole-base-{i}", "whole-baseline, unmodified") for i in (1, 2)]
    copies += [("_control", ctx.copies / "whole-deletions" / "_control", "whole-deletions, unmodified control")]
    copies += [(rm.safe(c["id"]), ctx.copies / "whole-deletions" / rm.safe(c["id"]), f"whole-deletions, {c['id']}")
               for c in checks]
    for label, cwd, what in copies:
        for call in whole_commands(rm, ctx, label, cwd):
            print(json.dumps({"library": name, "copy": what, **call}), flush=True)
    if args.collect:
        for result in collect(rm, ctx):
            print(f"collect-only {name} {result['run']}: exit {result['returncode']}, {result['last_line']!r}, "
                  f"refused {result['refused']}", flush=True)


# -- main ------------------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dry", action="store_true", help="list the checks and the commands; run nothing")
    parser.add_argument("--collect", action="store_true", help="with --dry: pytest --collect-only on 1 copy")
    parser.add_argument("--check-deletions", action="store_true",
                        help="with --dry: apply delete_check in memory and report what it changes")
    parser.add_argument("--no-verify", action="store_true", help="with --dry: skip T's verify")
    parser.add_argument("--libraries", nargs="+", default=list(LIBRARIES))
    parser.add_argument("--only", nargs="+", help="run these of --libraries (default: all)")
    parser.add_argument("--expect-total", type=int, default=EXPECT_TOTAL)
    parser.add_argument("--clone", action="append", help="NAME=DIR")
    parser.add_argument("--python", action="append", help="NAME=PYTHON")
    parser.add_argument("--work", default=str(WORK))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--out", default=str(HERE / "deletions-nofire.csv"))
    parser.add_argument("--summary", default=str(HERE / "summary.json"))
    parser.add_argument("--records", default=str(HERE / "records"))
    parser.add_argument("--toolkit", default=str(TOOLKIT))
    parser.add_argument("--subjects")
    parser.add_argument("--generated")
    args = parser.parse_args(argv)
    if (args.collect or args.check_deletions or args.no_verify) and not args.dry:
        raise SystemExit("--collect, --check-deletions and --no-verify go with --dry")
    toolkit = Path(args.toolkit).resolve()
    subjects = Path(args.subjects).resolve() if args.subjects else toolkit / "subjects"
    generated = Path(args.generated).resolve() if args.generated else toolkit / "generated"
    work = Path(args.work).resolve()
    rm = load_toolkit(toolkit)
    workers = args.workers or rm.WORKERS
    clones, pythons = pairs(args.clone, "--clone"), pairs(args.python, "--python")
    only = args.only or args.libraries
    if set(only) - set(args.libraries):
        raise SystemExit(f"--only names libraries outside --libraries: {sorted(set(only) - set(args.libraries))}")

    checks = population(generated, subjects, args.libraries, args.expect_total)
    if args.dry:
        for name in only:
            ctx = make_context(rm, name, subjects, work, clones.get(name), pythons.get(name), workers)
            dry(rm, ctx, name, checks[name], args, generated)
        return 0

    out, summary_path, records = Path(args.out), Path(args.summary), Path(args.records)
    all_rows = kept_rows(out, only)                       # rows of the libraries outside --only stay
    earlier = rm.load_json(summary_path)["libraries"] if summary_path.exists() else {}
    libraries = {k: v for k, v in earlier.items() if k not in only}
    summary = {"toolkit": str(toolkit), "workers": workers, "libraries": libraries}
    observer = Observer(rm)
    observer.install()
    try:
        for name in only:
            ctx = make_context(rm, name, subjects, work, clones.get(name), pythons.get(name), workers)
            rows, libraries[name] = run_library(rm, ctx, name, checks[name], observer, generated)
            keep_records(ctx, records / name)
            all_rows = in_order(all_rows + rows, args.libraries)
            write_csv(out, all_rows)                       # after each library, so that a stop keeps the rest
            rm.dump(summary_path, summary)                 # T's dump sorts the keys
    finally:
        observer.uninstall()
    print(f"wrote {out}: {len(all_rows)} rows; summary {summary_path}; records {records}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
