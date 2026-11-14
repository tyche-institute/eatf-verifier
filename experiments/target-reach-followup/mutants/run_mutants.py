"""Run the negative tests under the recorder and the whole suite on every mutant copy.

    python3 -I -B mutants/run_mutants.py --subject NAME_OR_SUBJECT_JSON
        [--workers N] [--extra-tests DIR] [--only ID [ID ...]]
        [--clone DIR] [--python PYTHON] [--work DIR]

Reads <work>/manifest.json and <work>/mutated/ (written by materialize.py).
The clone and the interpreter of the subject default to those that the
toolkit's work/<name>/local.json names; both are only read.

Steps, each skipped when its records exist (the program can be stopped and
started again):

1. baseline: `verify`, `baseline` and `whole-baseline` of reach/run.py, with
   <work> as the work directory: the run without the recorder, 2 recorder
   runs on 2 unmodified copies, the time limit, and 2 whole-suite runs on 2
   unmodified copies.
2. mutants: for each mutant, a fresh copy of the subject in which the 1
   modified file replaces the file (every other subject file is checked
   against the digest that `define` recorded); on it 1 recorder run, as the
   step `deletions` runs a deletion copy (reach.run.recorder_run, the time
   limit of the baseline); then, on another fresh copy, 1 whole-suite run, as
   the step `whole-deletions` runs it (reach.run.whole_run, the time limit of
   the whole-suite baseline, for all suite runs together). N copies run at a
   time (default 10).
3. repeats: a recorder run that gave no record, and a whole-suite run that
   exceeded its limit or of which a pytest call left no result file, is
   repeated 1 time, alone, on a fresh copy; the repeated run counts.
4. with --extra-tests DIR: the files test_*.py of DIR are copied into each
   copy as `_extra/` and run as 1 more pytest call, without the recorder,
   with the time limit of the whole suite: 2 times on 2 unmodified copies,
   and 1 time on every mutant copy (a third run per mutant), with the same
   repeat rule. The runs are kept per digest of DIR.

Records: <work>/records/ (the toolkit's baseline records, and mutants/<id>.json
for the recorder runs) and <work>/runs/<id>.json (1 per mutant: the status of
each run, the tests of the whole suite that pass in both unmodified runs and
do not pass on the mutant copy, and the seconds).
"""

from __future__ import annotations

import argparse
import copy as copy_module
import hashlib
import json
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (WORKERS, context, default_work, dump, load_json, local_settings, need_python_312,  # noqa: E402
                    reach_run, rel_to_source, sha256, subject_paths)

LOCK = threading.Lock()


def say(*parts) -> None:
    with LOCK:
        print(time.strftime("%H:%M:%S"), *parts, flush=True)


def baseline(ctx) -> None:
    rec = ctx.records
    if not all((rec / n).exists() for n in ("suite.json", "base-1.json", "base-2.json", "timeout.json")):
        reach_run.verify(ctx)
        reach_run.baseline(ctx)
    if not (rec / "whole" / "base.json").exists():
        reach_run.whole_baseline(ctx)


def mutant_copy(ctx, manifest: dict, work: Path, mid: str, dest: Path) -> None:
    """A fresh copy of the subject with the modified file of 1 mutant."""
    m = manifest[mid]
    reach_run.make_copy(ctx, dest)
    target = dest / rel_to_source(ctx.subject, m["file"])
    before = sha256(target)
    data = (work / m["path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != m["sha256"]:
        raise SystemExit(f"{mid}: the modified file is not the one materialize.py wrote")
    if before == m["sha256"]:
        raise SystemExit(f"{mid}: the modified file is the unmodified file")
    target.write_bytes(data)
    reach_run.make_copy_check(ctx, dest, skip=m["file"])


def drop(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def recorder(ctx, manifest, work, mid: str, timeout: float) -> dict:
    dest = ctx.copies / "mutants" / mid
    mutant_copy(ctx, manifest, work, mid, dest)
    out = ctx.records / "mutants" / f"{mid}.json"
    entry = reach_run.recorder_run(ctx, f"mutant-{mid}", dest, out, timeout)
    drop(dest)
    return {k: entry[k] for k in ("returncode", "timed_out", "seconds", "record", "timeout", "refused")}


def junit_run(ctx, manifest, work, mid: str | None, timeout: float, extra: Path | None = None) -> dict:
    """The whole suite (or, with `extra`, the extra tests) on a fresh copy of the
    mutant (or, with mid None, of the unmodified subject)."""
    label = mid or "unmodified"
    dest = ctx.copies / ("extra" if extra else "whole") / f"{label}-{threading.get_ident()}"
    if mid is None:
        reach_run.make_copy(ctx, dest)
    else:
        mutant_copy(ctx, manifest, work, mid, dest)
    run_ctx = ctx
    name = f"mutant-{label}"
    if extra is not None:
        (dest / "_extra").mkdir()
        for f in sorted(extra.glob("test_*.py")):
            shutil.copy2(f, dest / "_extra" / f.name)
        run_ctx = copy_module.copy(ctx)
        run_ctx.subject = dict(ctx.subject, suite_runs=[{"name": "extra", "paths": ["_extra"]}])
        name = f"extra-{label}"
    result = reach_run.whole_run(run_ctx, name, dest, timeout)
    for run in run_ctx.subject["suite_runs"]:
        xml = ctx.records / "whole" / "xml" / f"{name}.{run['name']}.xml"
        if xml.exists():
            xml.unlink()
    drop(dest)
    return result


def lost_tests(result: dict, passing: list[str]) -> list[str]:
    return sorted(k for k in passing if result["outcomes"].get(k) != "passed")


def whole_entry(result: dict, passing: list[str], runs: int, first: dict | None = None) -> dict:
    broken = result["timed_out"] or bool(result["no_result"])
    status = "timeout" if result["timed_out"] else ("error" if result["no_result"] else "completed")
    entry = {"status": status, "timed_out": result["timed_out"], "no_result": result["no_result"],
             "lost": [] if broken else lost_tests(result, passing), "tests": len(result["outcomes"]),
             "seconds": result["seconds"], "refused": result["refused"], "runs": runs}
    if first is not None:
        entry["first_run"] = first
    return entry


def needs_repeat(entry: dict) -> bool:
    return entry["runs"] == 1 and entry["status"] != "completed"


def recorder_entry(raw: dict, runs: int, first: dict | None = None) -> dict:
    if raw["record"] and not raw["timed_out"]:
        status = "completed"
    elif runs == 2 and raw["timed_out"] and first and first["timed_out"]:
        status = "timeout"
    else:
        status = "error" if runs == 2 else "no record"
    entry = dict(raw, status=status, runs=runs)
    if first is not None:
        entry["first_run"] = first
    return entry


def extra_digest(folder: Path) -> str:
    files = sorted(folder.glob("test_*.py"))
    if not files:
        raise SystemExit(f"{folder}: no file test_*.py")
    h = hashlib.sha256()
    for f in files:
        h.update(f"{f.name}\0{sha256(f)}\n".encode())
    return h.hexdigest()[:16]


def main(argv: list[str]) -> int:
    need_python_312()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subject", required=True)
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--extra-tests")
    parser.add_argument("--only", nargs="+")
    parser.add_argument("--clone")
    parser.add_argument("--python")
    parser.add_argument("--work")
    args = parser.parse_args(argv)
    subject_path, subject = subject_paths(args.subject)
    name = subject["name"]
    work = Path(args.work).resolve() if args.work else default_work(name)
    clone, python = local_settings(name, args.clone, args.python)
    ctx = context(subject_path, work, clone, python, args.workers)
    doc = load_json(work / "manifest.json")
    if doc["subject"] != name:
        raise SystemExit(f"{work / 'manifest.json'} is of {doc['subject']}")
    manifest = doc["mutants"]
    missing = sorted(m for m, v in manifest.items() if v["path"] is None)
    if missing:
        raise SystemExit(f"materialize.py wrote no modified file for {len(missing)} mutants: {missing[:5]}")
    ids = sorted(manifest)
    if args.only:
        unknown = sorted(set(args.only) - set(ids))
        if unknown:
            raise SystemExit(f"unknown mutants: {unknown}")
        ids = sorted(args.only)

    say(f"== baseline of {name}")
    baseline(ctx)
    rec_timeout = load_json(ctx.records / "timeout.json")["timeout_seconds"]
    whole_base = load_json(ctx.records / "whole" / "base.json")
    passing, whole_timeout = whole_base["passing"], whole_base["timeout_seconds"]
    runs_dir = work / "runs"
    runs_dir.mkdir(exist_ok=True)

    def read(mid: str) -> dict | None:
        p = runs_dir / f"{mid}.json"
        return load_json(p) if p.exists() else None

    # -- mutants: 1 recorder run and 1 whole-suite run each ------------------------------------
    todo = [m for m in ids if (r := read(m)) is None or r.get("sha256") != manifest[m]["sha256"]]
    say(f"== mutants: {len(todo)} of {len(ids)} to run, {args.workers} at a time; time limits "
        f"{rec_timeout} s (recorder) and {whole_timeout} s (whole suite)")
    start = time.monotonic()
    done = [0]

    def one(mid: str) -> None:
        t0 = time.monotonic()
        raw = recorder(ctx, manifest, work, mid, rec_timeout)
        whole = junit_run(ctx, manifest, work, mid, whole_timeout)
        entry = {"mutant": mid, "sha256": manifest[mid]["sha256"], "file": manifest[mid]["file"],
                 "recorder": recorder_entry(raw, 1), "whole": whole_entry(whole, passing, 1),
                 "seconds": round(time.monotonic() - t0, 3), "workers": args.workers}
        dump(runs_dir / f"{mid}.json", entry)
        with LOCK:
            done[0] += 1
            n = done[0]
        if n % 50 == 0 or n == len(todo):
            say(f"  {n}/{len(todo)} mutants, {time.monotonic() - start:.0f} s")

    with ThreadPoolExecutor(args.workers) as pool:
        for _ in pool.map(one, todo):
            pass

    # -- repeats, 1 at a time ---------------------------------------------------------------------
    for mid in ids:
        entry = read(mid)
        changed = False
        if entry["recorder"]["status"] == "no record":
            first = {k: entry["recorder"][k] for k in ("timed_out", "returncode", "refused", "seconds")}
            raw = recorder(ctx, manifest, work, mid, rec_timeout)
            entry["recorder"] = recorder_entry(raw, 2, first)
            changed = True
            say(f"  repeated recorder run of {mid}: {entry['recorder']['status']}")
        if needs_repeat(entry["whole"]):
            first = {k: entry["whole"][k] for k in ("timed_out", "no_result", "refused", "seconds")}
            entry["whole"] = whole_entry(junit_run(ctx, manifest, work, mid, whole_timeout), passing, 2, first)
            changed = True
            say(f"  repeated whole-suite run of {mid}: {entry['whole']['status']}")
        if changed:
            dump(runs_dir / f"{mid}.json", entry)

    # -- extra tests --------------------------------------------------------------------------------
    if args.extra_tests:
        folder = Path(args.extra_tests).resolve()
        digest = extra_digest(folder)
        base_path = work / "extra" / digest / "base.json"
        if not base_path.exists():
            results = [junit_run(ctx, manifest, work, None, whole_timeout, folder) for _ in (1, 2)]
            if any(r["timed_out"] or r["no_result"] for r in results):
                raise SystemExit("extra tests: an unmodified run exceeded the limit or left no result")
            a, b = (r["outcomes"] for r in results)
            dump(base_path, {"files": sorted(f.name for f in folder.glob("test_*.py")),
                             "passing": sorted(k for k in a if a[k] == "passed" and b.get(k) == "passed"),
                             "tests": sorted(set(a) | set(b)),
                             "unstable": sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)),
                             "seconds": [r["seconds"] for r in results]})
        extra_passing = load_json(base_path)["passing"]
        todo = [m for m in ids if digest not in (read(m).get("extra") or {})]
        say(f"== extra tests {digest}: {len(todo)} of {len(ids)} mutants to run")

        def extra_one(mid: str) -> None:
            result = whole_entry(junit_run(ctx, manifest, work, mid, whole_timeout, folder), extra_passing, 1)
            with LOCK:
                entry = read(mid)
                entry.setdefault("extra", {})[digest] = result
                dump(runs_dir / f"{mid}.json", entry)

        with ThreadPoolExecutor(args.workers) as pool:
            for _ in pool.map(extra_one, todo):
                pass
        for mid in ids:
            entry = read(mid)
            e = entry["extra"][digest]
            if needs_repeat(e):
                first = {k: e[k] for k in ("timed_out", "no_result", "refused", "seconds")}
                entry["extra"][digest] = whole_entry(junit_run(ctx, manifest, work, mid, whole_timeout, folder),
                                                     extra_passing, 2, first)
                dump(runs_dir / f"{mid}.json", entry)
    say(f"== done in {time.monotonic() - start:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
