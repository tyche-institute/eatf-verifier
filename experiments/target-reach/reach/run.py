"""Runner of the target-reach toolkit.

    python -I reach/run.py STEP [STEP ...] --subject subjects/<name>/subject.json
                           [--clone DIR] [--python VENV_PYTHON] [--work DIR] [--defs DIR]
                           [--workers N] [--out DIR]

Steps:
    define     enumerate checks and blocks from the clone; writes checks.json
               and blocks.json next to subject.json
    targets    apply the target rule to them; writes targets.json
    verify     the clone is at the subject's commit; the copied paths hold no
               changed, untracked or ignored file; the subject and test files
               match the SHA-256 values written by `define`; the interpreter
               is CPython in the subject's version; its packages are those of
               requirements.txt beside subject.json, and no other except pip;
               and the subject's distribution is not installed in the
               interpreter's own environment, so that every run imports the
               copy
    suite      1 run of the subject's tests without the recorder
    baseline   that suite run (the tests that fail in it are deselected
               afterwards, by their exact node id, and the test files that
               cannot be collected are ignored), then 2 recorder runs of the
               unmodified subject
    deletions  1 recorder run per reached check of the subject files (a check
               that fires in at least 1 case of the study at baseline) on a
               copy where the check's raise statements are `pass`, and 1 run
               of an unmodified control copy; a run that gives no record is
               repeated 1 time, alone, on a fresh copy; the records of an
               earlier `deletions` step are removed first
    whole-baseline   the subject's whole test suite (subject.json
               "suite_runs", 1 pytest call each) 2 times, each on its own
               unmodified copy, without the recorder
    whole-deletions  the whole test suite 1 time on every deletion copy and on
               the control copy, without the recorder; the time limit holds
               for all the suite runs of a copy together; a run that exceeds
               it, or of which a pytest call leaves no result file, is
               repeated 1 time, alone, on a fresh copy
    witness    the tests of witnesses/<name>/, written after the run for a
               deletion the whole suite does not detect: each file names its
               check in a line `# deleted check: <id>` and is run, without the
               recorder, on an unmodified copy and on the copy without the
               check; the witness holds when every test of the file passes on
               the first copy and at least 1 fails on the second
    pack       the records that the steps above name, without the junit XML
               files, as generated/<name>/records.tar.xz (sorted names, no
               times, no owners)

Every run happens in a fresh copy (subject.json "copy") under the work
directory; the clone is only read. `--clone` and `--python` are remembered in
<work>/local.json after the first use.

Every pytest call of every step loads the offline module
(guard/reach_offline.py): an attempt to connect a socket to an address that is
neither a loopback address nor a Unix socket, or to look up through
`socket.getaddrinfo` a host that is neither `localhost` nor an address
literal, is refused and counted. The counts are in the records: suite.json,
refused.json, deletions/refused.json, whole/base.json, whole/deletions.json
and witnesses.json. For a run that was repeated, the count is that of the
repeated run; deletions/repeated.json and the field `first_run` of
whole/deletions.json keep what the first attempt gave.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_ROOT = HERE.parent
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from reach.blocks import enumerate_blocks  # noqa: E402
from reach.checks import enumerate_checks, load_json, read_source, rel_to_source, sha256  # noqa: E402
from reach.delete import delete_check  # noqa: E402
from reach.study import firing_checks  # noqa: E402
from reach.targets import compute_targets  # noqa: E402

GUARD = TOOL_ROOT / "guard"            # holds reach_offline.py and no other module
OFFLINE = ["-p", "reach_offline"]      # outside connections are refused and counted


def refused(path: Path) -> dict | None:
    """What the offline module wrote at the end of 1 pytest call: the number of
    refused attempts and the tests that made them. None when the call did not
    reach its end. The file is removed."""
    if not path.exists():
        return None
    doc = load_json(path)
    path.unlink()
    return {"attempts": doc["attempts"], "tests": doc["tests"]}

WORKERS = 10


def dump(path: Path, data) -> None:
    """Plain data only: a value that JSON cannot hold is an error, not a repr."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def say(*parts) -> None:
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


class Context:
    def __init__(self, args) -> None:
        self.subject_path = Path(args.subject).resolve()
        self.subject = load_json(self.subject_path)
        name = self.subject["name"]
        self.defs = Path(args.defs).resolve() if args.defs else self.subject_path.parent
        self.work = Path(args.work).resolve() if args.work else TOOL_ROOT / "work" / name
        self.work.mkdir(parents=True, exist_ok=True)
        local_path = self.work / "local.json"
        local = load_json(local_path) if local_path.exists() else {}
        if args.clone:
            local["clone"] = str(Path(args.clone).resolve())
        if args.python:
            local["python"] = str(Path(args.python).absolute())
        if "clone" not in local or "python" not in local:
            raise SystemExit("give --clone and --python on first use")
        dump(local_path, local)
        self.clone = Path(local["clone"])
        self.python = Path(local["python"])
        self.workers = args.workers
        self.out = Path(args.out).resolve() if args.out else None
        self.records = self.work / "records"
        self.copies = self.work / "copies"
        self.logs = self.work / "logs"
        self.witnesses = (Path(args.witnesses).resolve() if args.witnesses
                          else TOOL_ROOT / "witnesses" / name)

    @property
    def checks_path(self) -> Path:
        return self.defs / "checks.json"

    @property
    def blocks_path(self) -> Path:
        return self.defs / "blocks.json"

    def env(self, **extra: str) -> dict[str, str]:
        env = {
            "PATH": f"{self.python.parent}:/usr/bin:/bin",
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        env.update(extra)
        return env

    def pythonpath(self, copy: Path, recorder: bool) -> str:
        """The toolkit for a recorder run, the folder of the offline module, and the
        copy's source root when it is not the copy itself (`python -m pytest`
        already puts the copy on the path)."""
        parts = ([str(TOOL_ROOT)] if recorder else []) + [str(GUARD)]
        src = self.subject.get("source_root", ".")
        if src not in (".", ""):
            parts.append(str(copy / src))
        return os.pathsep.join(parts)

    def timing(self, entry: dict) -> None:
        self.logs.mkdir(parents=True, exist_ok=True)
        with (self.logs / "timing.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")


# -- define and verify -------------------------------------------------------------

def define(ctx: Context) -> None:
    checks = enumerate_checks(ctx.subject, ctx.clone)
    blocks = enumerate_blocks(ctx.subject, ctx.clone, checks)
    blocks["test_files_sha256"] = {f: sha256(ctx.clone / f) for f in blocks["test_files"]}
    dump(ctx.checks_path, checks)
    dump(ctx.blocks_path, blocks)
    n_sub = sum(1 for c in checks["checks"] if c["role"] == "subject")
    included = [b for b in blocks["blocks"] if b["included"]]
    counts = ctx.subject.get("scope_counts")
    say(f"define: {len(checks['checks'])} checks ({n_sub} in subject files, "
        f"{sum(c['reachable'] for c in checks['checks'])} reachable); "
        f"{blocks['counts']['blocks']} blocks in the {len(blocks['test_files'])} test files of the subject, "
        f"{len(included)} included in {len({b['file'] for b in included})} files"
        + (f"; the test directories hold {counts['blocks_in_test_directories']} blocks in "
           f"{counts['test_files_in_test_directories']} test files" if counts else ""))


def targets(ctx: Context) -> None:
    doc = compute_targets(load_json(ctx.blocks_path), load_json(ctx.checks_path))
    dump(ctx.defs / "targets.json", doc)
    say(f"targets: rule {doc['rule_version']}; {json.dumps(doc['counts'], sort_keys=True)}")


def verify(ctx: Context) -> None:
    problems = []
    commit = ctx.subject.get("commit")
    if commit:
        git_env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
        head = subprocess.run(["git", "-C", str(ctx.clone), "rev-parse", "HEAD"], capture_output=True,
                              text=True, env=git_env).stdout.strip()
        # changed, untracked and ignored files of the copied paths: every copy would hold them
        dirty = subprocess.run(["git", "-C", str(ctx.clone), "status", "--porcelain", "--untracked-files=all",
                                "--ignored", "--", *ctx.subject["copy"]],
                               capture_output=True, text=True, env=git_env)
        if head != commit:
            problems.append(f"clone is at {head or '?'}, not {commit}")
        # a copy leaves out what make_copy ignores, so those entries do not count
        left_out = re.compile(r"(^|/)(__pycache__|\.pytest_cache)/|\.pyc$")
        extra = [line for line in dirty.stdout.splitlines() if line.strip() and not left_out.search(line[3:])]
        if dirty.returncode != 0 or extra:
            problems.append("the copied paths of the clone hold files that are not those of the commit: "
                            f"{('; '.join(extra) or dirty.stderr.strip())[:200]}")
    checks, blocks = load_json(ctx.checks_path), load_json(ctx.blocks_path)
    if checks["subject"] != {k: ctx.subject[k] for k in sorted(ctx.subject)}:
        problems.append("checks.json was written from another subject.json: run `define` again")
    for rel, digest in checks["sha256"].items():
        if sha256(ctx.clone / rel_to_source(ctx.subject, rel)) != digest:
            problems.append(f"{rel}: SHA-256 differs from checks.json")
    for rel, digest in blocks["test_files_sha256"].items():
        if sha256(ctx.clone / rel) != digest:
            problems.append(f"{rel}: SHA-256 differs from blocks.json")
    reported = subprocess.run([str(ctx.python), "-I", "-c", INTERPRETER_PROBE],
                              capture_output=True, text=True).stdout.strip()
    problem = interpreter_problem(reported, ctx.subject.get("python"))
    if problem:
        problems.append(problem)
    requirements = ctx.defs / "requirements.txt"
    if requirements.exists():
        problems += environment_problems(ctx.python, requirements)
    probe = ("import importlib.metadata as m, importlib.util as u, sys\n"
             "dist, module = sys.argv[1], sys.argv[2]\n"
             "try:\n    m.distribution(dist); print('distribution installed')\n"
             "except m.PackageNotFoundError:\n    pass\n"
             "try:\n    found = u.find_spec(module) is not None\n"
             "except ModuleNotFoundError:\n    found = False\n"
             "if found:\n    print('module importable')\n")
    first = Path(ctx.subject["subject_files"][0]).with_suffix("")
    module = ".".join(first.parts[:-1] if first.name == "__init__" else first.parts)
    found = subprocess.run([str(ctx.python), "-I", "-c", probe, ctx.subject["distribution"], module],
                           capture_output=True, text=True, cwd="/", env=ctx.env())
    if found.returncode != 0 or found.stdout.strip():
        problems.append(f"{ctx.subject['distribution']} is installed in the interpreter's own environment "
                        f"({found.stdout.strip() or found.stderr.strip()[-200:]})")
    if problems:
        raise SystemExit("verify failed:\n  " + "\n  ".join(problems))
    say(f"verify: commit {str(commit)[:12]}, {len(checks['sha256'])} subject files and "
        f"{len(blocks['test_files_sha256'])} test files match, {reported}")


INTERPRETER_PROBE = "import platform, sys; print(platform.python_implementation(), sys.version.split()[0])"


def interpreter_problem(reported: str, python: str | None) -> str | None:
    """`reported` is what INTERPRETER_PROBE prints in the environment of the subject;
    the subject asks for CPython in the version `python`."""
    if python and reported != f"CPython {python}":
        return f"the interpreter is {reported or 'unknown'}, not CPython {python}"
    return None


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def environment_problems(python: Path, requirements: Path) -> list[str]:
    """The interpreter's packages against the pins of requirements.txt (lines
    `name==version`): every pin is installed at that version, and nothing else
    is installed except pip."""
    pins, problems = {}, []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"([A-Za-z0-9._-]+)==(\S+)", line)
        if m is None:
            problems.append(f"requirements.txt: `{line}` is no pin `name==version`")
            continue
        pins[canonical(m.group(1))] = m.group(2)
    probe = ("import importlib.metadata as m, json\n"
             "print(json.dumps(sorted([d.metadata['Name'] or '', d.version] for d in m.distributions())))\n")
    found = subprocess.run([str(python), "-I", "-c", probe], capture_output=True, text=True, cwd="/")
    if found.returncode != 0:
        return problems + [f"the packages of the interpreter cannot be listed: {found.stderr.strip()[-200:]}"]
    installed = {canonical(name): version for name, version in json.loads(found.stdout)}
    installed.pop("pip", None)
    for name, version in sorted(pins.items()):
        if installed.get(name) != version:
            problems.append(f"requirements.txt pins {name}=={version}; installed: {installed.get(name)}")
    for name in sorted(set(installed) - set(pins)):
        problems.append(f"{name}=={installed[name]} is installed and not in requirements.txt")
    return problems


# -- copies and runs ----------------------------------------------------------------

def make_copy(ctx: Context, dest: Path, changed: str | None = None) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in ctx.subject["copy"]:
        src = ctx.clone / item
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=ignore)
        else:
            (dest / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / item)
    make_copy_check(ctx, dest, skip=None)


def make_copy_check(ctx: Context, dest: Path, skip: str | None) -> None:
    """Every subject file of the copy is the file `define` read, except `skip`."""
    checks = load_json(ctx.checks_path)
    for rel, digest in checks["sha256"].items():
        if rel != skip and sha256(dest / rel_to_source(ctx.subject, rel)) != digest:
            raise SystemExit(f"copy {dest}: {rel} differs from the clone")


def pytest_command(ctx: Context, recorder: bool) -> list[str]:
    """The pytest call of the suite run and of a recorder run. A recorder run
    ignores the test files that the suite run could not collect; the recorder
    itself deselects the tests that failed in the suite run, by their exact
    node id, which it reads from the file named by REACH_SUITE."""
    cmd = [str(ctx.python), "-m", "pytest", "-q", *ctx.subject.get("pytest_args", []), *OFFLINE,
           "--rootdir=.", "--tb=native", "-rfE", "--continue-on-collection-errors"]
    if recorder:
        cmd += ["-p", "reach.recorder"]
        path = ctx.records / "suite.json"
        for ignored in (load_json(path).get("not_collected", []) if path.exists() else []):
            cmd += [f"--ignore={ignored}"]
    return cmd + list(ctx.subject["tests"])


def recorder_run(ctx: Context, name: str, cwd: Path, out: Path, timeout: float) -> dict:
    offline = out.with_name(out.stem + ".offline.tmp")
    env = ctx.env(PYTHONPATH=ctx.pythonpath(cwd, recorder=True), REACH_SUBJECT=str(ctx.subject_path),
                  REACH_CHECKS=str(ctx.checks_path), REACH_BLOCKS=str(ctx.blocks_path),
                  REACH_OUT=str(out), REACH_ROOT=str(cwd), REACH_SUITE=str(ctx.records / "suite.json"),
                  OFFLINE_OUT=str(offline))
    out.parent.mkdir(parents=True, exist_ok=True)
    for old in (out, offline):
        if old.exists():
            old.unlink()
    start = time.monotonic()
    try:
        proc = subprocess.run(pytest_command(ctx, True), cwd=cwd, env=env, capture_output=True,
                              text=True, timeout=timeout)
        timed_out, code, text = False, proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        timed_out, code = True, None
        text = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
    seconds = round(time.monotonic() - start, 3)
    ctx.logs.mkdir(parents=True, exist_ok=True)
    (ctx.logs / f"{name}.log").write_text(text, encoding="utf-8")
    entry = {"run": name, "returncode": code, "timed_out": timed_out, "seconds": seconds,
             "record": out.exists(), "timeout": timeout, "refused": refused(offline)}
    ctx.timing(entry)
    return entry


# pytest's last line, such as "76 passed, 1 warning in 2.11s"
SUMMARY = re.compile(r"^=* ?((?:\d+ [a-z]+(?: [a-z]+)*(?:, )?)+) in [0-9.]+s", re.M)


def suite(ctx: Context) -> None:
    dest = ctx.copies / "suite"
    make_copy(ctx, dest)
    start = time.monotonic()
    offline = ctx.records / "suite.offline.tmp"
    outcomes = ctx.records / "suite.outcomes.tmp"
    offline.parent.mkdir(parents=True, exist_ok=True)
    for old in (offline, outcomes):
        if old.exists():
            old.unlink()
    proc = subprocess.run(pytest_command(ctx, False), cwd=dest,
                          env=ctx.env(PYTHONPATH=ctx.pythonpath(dest, recorder=False),
                                      OFFLINE_OUT=str(offline), OUTCOMES_OUT=str(outcomes)),
                          capture_output=True, text=True, timeout=3600)
    text = proc.stdout + proc.stderr
    ctx.logs.mkdir(parents=True, exist_ok=True)
    (ctx.logs / "suite.log").write_text(text, encoding="utf-8")
    if not outcomes.exists():
        raise SystemExit("suite: the run without the recorder did not reach its end (see logs/suite.log)")
    seen = load_json(outcomes)
    outcomes.unlink()
    # the offline module names the tests of which a report failed, by their exact node id
    # (deselected afterwards), and the collectors that failed (their files are ignored)
    failures = seen["failed_tests"]
    if "" in seen["failed_collectors"]:
        raise SystemExit("suite: pytest could not collect the test paths (see logs/suite.log)")
    not_collected = sorted({n.split("::")[0] for n in seen["failed_collectors"]})
    found = SUMMARY.findall(text)
    summary = found[-1] if found else ""
    dump(ctx.records / "suite.json", {"returncode": proc.returncode, "summary": summary,
                                      "failures": failures, "not_collected": not_collected,
                                      "refused": refused(offline)})
    ctx.timing({"run": "suite", "returncode": proc.returncode,
                "seconds": round(time.monotonic() - start, 3)})
    say("suite without recorder:", proc.returncode, summary,
        f"({len(failures)} failing tests deselected, {len(not_collected)} files not collected)")


def baseline(ctx: Context) -> None:
    suite(ctx)
    entries = []
    for name in ("base-1", "base-2"):
        dest = ctx.copies / name
        make_copy(ctx, dest)
        entry = recorder_run(ctx, name, dest, ctx.records / f"{name}.json", timeout=3600)
        entries.append(entry)
        say(name, "returncode", entry["returncode"], entry["seconds"], "s")
        if entry["timed_out"] or not entry["record"]:
            raise SystemExit(f"{name}: no record")
    dump(ctx.records / "refused.json", {e["run"]: e["refused"] for e in entries})
    slowest = max(e["seconds"] for e in entries)
    dump(ctx.records / "timeout.json", {"rule": "max(60 s, 10 x the slower baseline run)",
                                        "timeout_seconds": max(60.0, round(10 * slowest, 1))})


def reached_checks(ctx: Context) -> list[dict]:
    """The checks of the subject files that fire in at least 1 case of the study
    at baseline (reach/study.py): the check at the raise site of the case's
    exception, or a check whose exception a handler caught before."""
    checks = load_json(ctx.checks_path)
    reached = firing_checks(load_json(ctx.records / "base-1.json"))
    return [c for c in checks["checks"] if c["role"] == "subject" and c["id"] in reached]


def safe(check_id: str) -> str:
    return check_id.replace("#", "-")


def deletion_copy(ctx: Context, check: dict, dest: Path) -> tuple[list[dict], str]:
    """A fresh copy with the check deleted: (the removed statements, SHA-256 of the changed file)."""
    make_copy(ctx, dest, changed=check["file"])
    target = dest / rel_to_source(ctx.subject, check["file"])
    mark = target.read_bytes().startswith(b"\xef\xbb\xbf")
    new, changed = delete_check(read_source(target), check)
    target.write_text(new, encoding="utf-8-sig" if mark else "utf-8")
    make_copy_check(ctx, dest, skip=check["file"])
    return changed, sha256(target)


def deletions(ctx: Context) -> None:
    timeout = load_json(ctx.records / "timeout.json")["timeout_seconds"]
    root = ctx.copies / "deletions"
    out_dir = ctx.records / "deletions"
    for stale in (out_dir, root):  # nothing of an earlier run stays
        if stale.exists():
            shutil.rmtree(stale)
    jobs = [("_control", root / "_control", out_dir / "_control.json")]
    make_copy(ctx, root / "_control")
    manifest, reached = {}, {}
    for check in reached_checks(ctx):
        dest = root / safe(check["id"])
        changed, digest = deletion_copy(ctx, check, dest)
        manifest[check["id"]] = {"dir": safe(check["id"]), "file": check["file"], "removed": changed,
                                 "sha256_after": digest}
        reached[check["id"]] = check
        jobs.append((check["id"], dest, out_dir / f"{safe(check['id'])}.json"))
    dump(out_dir / "manifest.json", manifest)
    say(f"deletions: {len(jobs) - 1} deletion copies and 1 control copy, {ctx.workers} at a time")
    start = time.monotonic()

    def one(job):
        name, cwd, out = job
        return recorder_run(ctx, f"deletion-{safe(name)}", cwd, out, timeout)

    with ThreadPoolExecutor(ctx.workers) as pool:
        entries = list(pool.map(one, jobs))
    no_record, attempts, repeated = {}, {}, {}
    for job, entry in zip(jobs, entries):
        attempts[job[0]] = entry["refused"]
        if entry["timed_out"] or not entry["record"]:
            # once more, alone, on a fresh copy
            if job[0] == "_control":
                make_copy(ctx, job[1])
            else:
                _, digest = deletion_copy(ctx, reached[job[0]], job[1])
                if digest != manifest[job[0]]["sha256_after"]:
                    raise SystemExit(f"deletions: the fresh copy of {job[0]} is not the first one")
            again = one(job)
            attempts[job[0]] = again["refused"]
            repeated[job[0]] = {"timed_out": entry["timed_out"], "returncode": entry["returncode"],
                                "refused": entry["refused"]}
            if again["timed_out"] or not again["record"]:
                no_record[job[0]] = {"timed_out": [entry["timed_out"], again["timed_out"]],
                                     "returncode": [entry["returncode"], again["returncode"]]}
    dump(out_dir / "no-record.json", no_record)
    dump(out_dir / "repeated.json", repeated)
    dump(out_dir / "refused.json", attempts)
    ctx.timing({"run": "deletions-stage", "runs": len(jobs),
                "seconds": round(time.monotonic() - start, 3), "workers": ctx.workers})
    say(f"deletions: done in {time.monotonic() - start:.1f} s; without record: {sorted(no_record)}")


# -- the whole test suite, without the recorder ------------------------------------------

def junit_outcomes(path: Path, prefix: str) -> dict[str, str]:
    """Test id -> passed, failed or skipped, from the junit XML file of 1 pytest call.
    A file that pytest cannot collect is 1 failed entry; an id that occurs
    twice with 2 outcomes is failed."""
    out: dict[str, str] = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        key = f"{prefix}|{case.get('classname')}::{case.get('name')}"
        tags = {child.tag for child in case}
        result = "failed" if tags & {"failure", "error"} else ("skipped" if "skipped" in tags else "passed")
        out[key] = result if out.get(key, result) == result else "failed"
    return out


def whole_run(ctx: Context, name: str, cwd: Path, timeout: float) -> dict:
    """Every suite run of the subject on 1 copy: {"outcomes": {id: outcome}, "timed_out": bool,
    "no_result": the suite runs whose pytest call ended without a readable result file,
    "seconds": float, "refused": the refused connection attempts of all the calls, or None
    when a call did not reach its end}. The time limit is that of all the suite runs
    together: each pytest call gets what the calls before it left, and no call starts
    after the limit."""
    outcomes: dict[str, str] = {}
    timed_out, seconds = False, 0.0
    no_result: list[str] = []
    attempts, by_test, counted = 0, {}, True
    path = ctx.pythonpath(cwd, recorder=False)
    for run in ctx.subject["suite_runs"]:
        if timed_out or seconds >= timeout:
            timed_out = True
            break
        xml = ctx.records / "whole" / "xml" / f"{name}.{run['name']}.xml"
        xml.parent.mkdir(parents=True, exist_ok=True)
        offline = xml.with_suffix(".offline.tmp")
        for old in (xml, offline):
            if old.exists():
                old.unlink()
        cmd = [str(ctx.python), "-m", "pytest", "-q", *ctx.subject.get("pytest_args", []),
               *run.get("args", []), *OFFLINE, "--rootdir=.", "--tb=no",
               "--continue-on-collection-errors", f"--junitxml={xml}", *run["paths"]]
        start = time.monotonic()
        try:
            subprocess.run(cmd, cwd=cwd, env=ctx.env(PYTHONPATH=path, OFFLINE_OUT=str(offline)),
                           capture_output=True, text=True, timeout=timeout - seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        seconds += time.monotonic() - start
        if not timed_out:
            try:
                outcomes.update(junit_outcomes(xml, run["name"]))
            except (OSError, ET.ParseError):
                no_result.append(run["name"])
        count = refused(offline)
        if count is None:
            counted = False
        else:
            attempts += count["attempts"]
            by_test.update({f"{run['name']}|{test}": n for test, n in count["tests"].items()})
    ctx.timing({"run": f"whole-{name}", "seconds": round(seconds, 3), "timed_out": timed_out,
                "tests": len(outcomes)})
    return {"outcomes": outcomes, "timed_out": timed_out, "no_result": no_result,
            "seconds": round(seconds, 3),
            "refused": {"attempts": attempts, "tests": by_test} if counted and not timed_out else None}


def whole_baseline(ctx: Context) -> None:
    runs = []
    for i in (1, 2):  # each run on its own copy
        dest = ctx.copies / f"whole-base-{i}"
        make_copy(ctx, dest)
        runs.append(whole_run(ctx, f"base-{i}", dest, timeout=7200))
    if any(r["timed_out"] for r in runs):
        raise SystemExit("whole-baseline: a run exceeded 7200 s")
    if any(r["no_result"] for r in runs):
        raise SystemExit("whole-baseline: a pytest call ended without its result file")
    a, b = (r["outcomes"] for r in runs)
    passing = sorted(k for k in a if a[k] == "passed" and b.get(k) == "passed")
    unstable = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    slowest = max(r["seconds"] for r in runs)
    dump(ctx.records / "whole" / "base.json", {
        "suite_runs": ctx.subject["suite_runs"], "passing": passing, "unstable": unstable,
        "counts": {"run 1": dict(sorted(Counter(a.values()).items())),
                   "run 2": dict(sorted(Counter(b.values()).items())),
                   "passing in both": len(passing), "unstable": len(unstable)},
        "seconds": [r["seconds"] for r in runs],
        "refused": [r["refused"] for r in runs],
        "timeout_rule": "max(60 s, 10 x the slower baseline run)",
        "timeout_seconds": max(60.0, round(10 * slowest, 1))})
    say(f"whole-baseline: {len(passing)} tests pass in both runs, {len(unstable)} unstable, "
        f"run 1 {dict(sorted(Counter(a.values()).items()))}, {slowest:.1f} s")


def whole_deletions(ctx: Context) -> None:
    base = load_json(ctx.records / "whole" / "base.json")
    passing, timeout = base["passing"], base["timeout_seconds"]
    manifest = load_json(ctx.records / "deletions" / "manifest.json")
    checks = {c["id"]: c for c in load_json(ctx.checks_path)["checks"]}
    root = ctx.copies / "whole-deletions"
    jobs = [("_control", root / "_control")] + [(cid, root / m["dir"]) for cid, m in sorted(manifest.items())]

    def fresh(job) -> None:
        cid, copy = job
        if cid == "_control":
            make_copy(ctx, copy)
            return
        _, digest = deletion_copy(ctx, checks[cid], copy)
        if digest != manifest[cid]["sha256_after"]:
            raise SystemExit(f"whole-deletions: the copy of {cid} is not the one the recorder run used")

    for job in jobs:
        fresh(job)
    start = time.monotonic()

    def one(job):
        cid, copy = job
        run = whole_run(ctx, safe(cid), copy, timeout)
        lost = [k for k in passing if run["outcomes"].get(k) != "passed"]
        # a run that exceeds the limit, or of which a call leaves no result file, has no
        # count of tests: when the repeated run ends so too, the deletion counts as detected
        broken = bool(run["timed_out"] or run["no_result"])
        return cid, {"detected": bool(broken or lost), "timed_out": run["timed_out"],
                     "no_result": run["no_result"],
                     "tests_not_passing": 0 if broken else len(lost),
                     "examples": [] if broken else lost[:10], "seconds": run["seconds"],
                     "refused": run["refused"], "runs": 1}

    with ThreadPoolExecutor(ctx.workers) as pool:
        results = dict(pool.map(one, jobs))
    for job in jobs:
        first = results[job[0]]
        if first["timed_out"] or first["no_result"]:
            # once more, alone, on a fresh copy: the outcome of the repeated run counts
            fresh(job)
            results[job[0]] = dict(one(job)[1], runs=2,
                                   first_run={k: first[k] for k in ("timed_out", "no_result", "refused")})
    dump(ctx.records / "whole" / "deletions.json", results)
    hidden = sorted(c for c, r in results.items() if c != "_control" and not r["detected"])
    say(f"whole-deletions: {len(jobs) - 1} copies and the control in {time.monotonic() - start:.1f} s; "
        f"control detected: {results['_control']['detected']}; not detected: {len(hidden)}")


# -- the records, packed for the deposit --------------------------------------------------

def junit_failures(path: Path, prefix: str, copy: Path) -> dict[str, str]:
    """Test id -> the message of its first failure or error, from the junit XML
    file of 1 pytest call; memory addresses and the path of the copy are masked."""
    out: dict[str, str] = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        key = f"{prefix}|{case.get('classname')}::{case.get('name')}"
        for child in case:
            if child.tag in ("failure", "error") and key not in out:
                text = (child.get("message") or "").replace(str(copy), "<copy>")
                out[key] = re.sub(r" at 0x[0-9a-fA-F]+", " at 0x*", text)[:300]
    return out


def witness(ctx: Context) -> None:
    """Witness tests, written after the run for deletions that the whole suite
    does not detect. Each file `test_*.py` of the folder names 1 check in a line
    `# deleted check: <id>`. It runs without the recorder on an unmodified copy
    and on the copy without that check. It holds when every test of the file
    passes on the unmodified copy and at least 1 fails on the other; the record
    keeps the message of each failure, which says whether the input is accepted
    without the check (`DID NOT RAISE`) or handled differently."""
    folder = ctx.witnesses
    ctx.logs.mkdir(parents=True, exist_ok=True)
    checks = {c["id"]: c for c in load_json(ctx.checks_path)["checks"]}
    results = {}

    def run_on(copy: Path, file: Path, label: str) -> tuple[dict[str, str], int | None, dict[str, str]]:
        """(outcome of every test of the file, refused connection attempts, failure messages)."""
        (copy / "_witness").mkdir(exist_ok=True)
        shutil.copy2(file, copy / "_witness" / file.name)
        xml = ctx.records / "whole" / "xml" / f"witness.{file.stem}.{label}.xml"
        xml.parent.mkdir(parents=True, exist_ok=True)
        offline = xml.with_suffix(".offline.tmp")
        for old in (xml, offline):
            if old.exists():
                old.unlink()
        cmd = [str(ctx.python), "-m", "pytest", "-q", *ctx.subject.get("pytest_args", []), *OFFLINE,
               "--rootdir=.", "--tb=short", f"--junitxml={xml}", f"_witness/{file.name}"]
        proc = subprocess.run(cmd, cwd=copy,
                              env=ctx.env(PYTHONPATH=ctx.pythonpath(copy, recorder=False),
                                          OFFLINE_OUT=str(offline)),
                              capture_output=True, text=True, timeout=600)
        (ctx.logs / f"witness.{file.stem}.{label}.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        count = refused(offline)
        return (junit_outcomes(xml, "witness") if xml.exists() else {},
                None if count is None else count["attempts"],
                junit_failures(xml, "witness", copy) if xml.exists() else {})

    for file in sorted(folder.glob("test_*.py")):
        named = re.findall(r"^# deleted check: (\S+)\s*$", file.read_text(encoding="utf-8"), re.M)
        if len(named) != 1 or named[0] not in checks:
            raise SystemExit(f"witness {file.name}: 1 line `# deleted check: <id>` naming a check is needed")
        cid = named[0]
        plain, deleted = ctx.copies / "witness" / "unmodified", ctx.copies / "witness" / safe(cid)
        make_copy(ctx, plain)
        deletion_copy(ctx, checks[cid], deleted)
        (before, refused_before, _), (after, refused_after, messages) = (
            run_on(plain, file, "unmodified"), run_on(deleted, file, "deleted"))
        holds = (bool(before) and all(v == "passed" for v in before.values())
                 and any(after.get(k) == "failed" for k in before))
        results[file.name] = {"check": cid, "sha256": sha256(file), "unmodified": before,
                              "deleted": after, "deleted_failures": messages, "holds": holds,
                              "refused": {"unmodified": refused_before, "deleted": refused_after}}
        say(f"witness {file.name}: {cid}: unmodified {dict(Counter(before.values()))}, "
            f"deleted {dict(Counter(after.values()))}, holds: {holds}")
    dump(ctx.records / "witnesses.json", results)


def pack(ctx: Context) -> None:
    """generated/<name>/records.tar.xz: the records that the steps of this file
    name, and no other file that lies under <work>/records. The same records give
    the same bytes: sorted names, no times, no owners."""
    out = (ctx.out or TOOL_ROOT / "generated" / ctx.subject["name"]) / "records.tar.xz"
    out.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(ctx.records / name for name in record_names(ctx))
    tmp = out.with_suffix(".tmp")
    with tarfile.open(tmp, "w:xz", format=tarfile.PAX_FORMAT, preset=9) as tar:
        for p in files:
            info = tarfile.TarInfo("records/" + p.relative_to(ctx.records).as_posix())
            data = p.read_bytes()
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    tmp.replace(out)
    say(f"pack: {len(files)} records, {out.stat().st_size} bytes, SHA-256 {sha256(out)}")


def record_names(ctx: Context) -> list[str]:
    """The records of 1 subject, relative to <work>/records: those of the baseline,
    of every deletion the manifest names, of the whole suite and of the witnesses.
    A record that a step must have written and that is absent is an error. The
    control copy, like a deletion copy, has no record when no-record.json names it."""
    names = ["suite.json", "base-1.json", "base-2.json", "refused.json", "timeout.json"]
    manifest_path = ctx.records / "deletions" / "manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        no_record = load_json(ctx.records / "deletions" / "no-record.json")
        names += ["deletions/manifest.json", "deletions/no-record.json", "deletions/repeated.json",
                  "deletions/refused.json"]
        if "_control" not in no_record:
            names.append("deletions/_control.json")
        names += [f"deletions/{m['dir']}.json" for cid, m in sorted(manifest.items())
                  if cid not in no_record]
    for name in ("whole/base.json", "whole/deletions.json", "witnesses.json"):
        if (ctx.records / name).exists():
            names.append(name)
    absent = [n for n in names if not (ctx.records / n).exists()]
    if absent:
        raise SystemExit(f"pack: records absent: {absent}")
    return names


STEPS = {"define": define, "targets": targets, "verify": verify, "suite": suite, "baseline": baseline,
         "deletions": deletions, "whole-baseline": whole_baseline, "whole-deletions": whole_deletions,
         "witness": witness, "pack": pack}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="target-reach runner")
    parser.add_argument("steps", nargs="+", choices=list(STEPS))
    parser.add_argument("--subject", required=True)
    parser.add_argument("--clone")
    parser.add_argument("--python")
    parser.add_argument("--work")
    parser.add_argument("--defs")
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--out", help="for `pack`: the directory of records.tar.xz")
    parser.add_argument("--witnesses", help="for `witness`: the folder of the witness tests")
    args = parser.parse_args(argv)
    ctx = Context(args)
    for step in args.steps:
        say("==", step)
        STEPS[step](ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
