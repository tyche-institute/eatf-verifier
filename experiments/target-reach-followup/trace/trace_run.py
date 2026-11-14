"""Run the whole test suite of a subject under the trace plugin; write reach.json.

    python3 -I -B trace/trace_run.py --subject ../target-reach/subjects/<name>/subject.json
                                     [--clone DIR] [--python VENV_PYTHON] [--work DIR] [--out DIR]
                                     [--repeats N] [--base whole/base.json]

Every suite run of subject.json ("suite_runs") runs with the same pytest
arguments, environment variables and offline module as the step
`whole-baseline` of `../target-reach/reach/run.py`, on a fresh unmodified copy
made by that runner's `make_copy`, and with 1 more plugin: `plugin.py` of this
folder, put on the module search path as `reach_trace` in a folder of the work
directory that holds no other module. The recorder of the toolkit is not
loaded.

With `--repeats N` (default 1), the suite runs N times without the plugin and
N times with it, each run on its own fresh copy, alternating; the runs
without the plugin give the run-time overhead. The entry-point sets of the
first traced run are those written.

Writes `<out>/reach.json` (default `generated/trace/<name>/`): per function of
`checks.json` that started, the entry-point names under which it started;
the functions that started only under no entry point; the codes that started
and are no function of `checks.json` (lambdas, generator expressions,
definitions that `checks.json` does not list); the test outcomes; the
interpreter and the installed packages; the time of each run. `--clone` and
`--python` default to `../target-reach/work/<name>/local.json`.

Sentinels (the program writes reach.json and then exits with an error when 1
does not hold):

    T3        the tests that pass in the traced run are the tests that pass
              in both whole-baseline runs of the deposited records
              (`whole/base.json` in `generated/<name>/records.tar.xz` of the
              toolkit), and no traced pytest call ends without its result file
    T3-repeat with N >= 2, every traced run gives the same entry-point sets
              and the same passing tests; the differences are listed
    T3-repeat-reach  with N >= 2, every traced run gives the same set of
              codes that started under at least 1 entry point, which is all
              that rule 3 reads
    T-map     every started code of a subject file whose name is not
              `<lambda>` or `<genexpr>` is a function of checks.json, or is
              listed under `unmapped` with its reason
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent                                  # target-reach-followup
E = EXP.parent / "target-reach"
if str(E) not in sys.path:
    sys.path.insert(0, str(E))

from reach import run as reach_run  # noqa: E402
from reach.checks import functions, load_json, read_source, rel_to_source  # noqa: E402

PLUGIN_NAME = "reach_trace"


def dump_text(data) -> str:
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def deposited_base(name: str) -> dict:
    """whole/base.json of the deposited records of the toolkit."""
    with tarfile.open(E / "generated" / name / "records.tar.xz", "r:xz") as tar:
        return json.load(tar.extractfile("records/whole/base.json"))


def function_index(subject: dict, root: Path, files: list[str]) -> tuple[dict, dict]:
    """(file, first line, name) -> qualified name as checks.json names it, and
    (file, first line, name) -> reason for every other code-holding node of
    the files (a definition that checks.json does not list, a lambda, a
    generator expression). The first line of a definition is that of its
    first decorator, or of the `def` line when there is none: the first line
    the interpreter gives the code object."""
    out, other = {}, {}
    for rel in files:
        tree = ast.parse(read_source(root / rel_to_source(subject, rel)))
        listed = set()
        for qual, node in functions(tree).items():
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            out[(rel, first, node.name)] = qual
            listed.add(id(node))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and id(node) not in listed:
                first = min([node.lineno] + [d.lineno for d in node.decorator_list])
                other[(rel, first, node.name)] = ("a definition that checks.json does not list (in a loop, "
                                                  "an exception handler, an async with or a match "
                                                  "statement, or nested in such a definition)")
            elif isinstance(node, ast.Lambda):
                other[(rel, node.lineno, "<lambda>")] = "a lambda; it holds no raise statement"
            elif isinstance(node, ast.GeneratorExp):
                other[(rel, node.lineno, "<genexpr>")] = ("a generator expression; it holds no raise "
                                                          "statement")
    return out, other


def environment(python: Path) -> dict:
    probe = ("import json, sys, platform, importlib.metadata as m; print(json.dumps({"
             "'implementation': platform.python_implementation(), 'version': platform.python_version(), "
             "'packages': sorted(f\"{d.metadata['Name']}=={d.version}\" for d in m.distributions())}))")
    out = subprocess.run([str(python), "-I", "-B", "-c", probe], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def suite_once(ctx, cwd: Path, name: str, plugin_dir: Path | None, trace_files: Path | None,
               trace_out: Path | None, timeout: float) -> dict:
    """The suite runs of the subject on 1 copy, as reach/run.py whole_run calls
    them, with the trace plugin when plugin_dir is given."""
    outcomes: dict[str, str] = {}
    no_result: list[str] = []
    seconds = 0.0
    attempts, counted = 0, True
    xml_dir = ctx.records / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)
    traces = []
    for run in ctx.subject["suite_runs"]:
        xml = xml_dir / f"{name}.{run['name']}.xml"
        offline = xml.with_suffix(".offline.tmp")
        out_json = None
        for old in (xml, offline):
            if old.exists():
                old.unlink()
        path = ctx.pythonpath(cwd, recorder=False)
        extra = {}
        cmd = [str(ctx.python), "-m", "pytest", "-q", *ctx.subject.get("pytest_args", []),
               *run.get("args", []), *reach_run.OFFLINE]
        if plugin_dir is not None:
            out_json = trace_out.with_name(f"{trace_out.stem}.{run['name']}.json")
            if out_json.exists():
                out_json.unlink()
            path = path + ":" + str(plugin_dir)
            cmd += ["-p", PLUGIN_NAME]
            extra = {"TRACE_ROOT": str(cwd / ctx.subject.get("source_root", ".")),
                     "TRACE_FILES": str(trace_files), "TRACE_OUT": str(out_json)}
        cmd += ["--rootdir=.", "--tb=no", "--continue-on-collection-errors", f"--junitxml={xml}",
                *run["paths"]]
        start = time.monotonic()
        proc = subprocess.run(cmd, cwd=cwd, env=ctx.env(PYTHONPATH=path, OFFLINE_OUT=str(offline), **extra),
                              capture_output=True, text=True, timeout=timeout)
        seconds += time.monotonic() - start
        (ctx.logs / f"{name}.{run['name']}.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        try:
            outcomes.update(reach_run.junit_outcomes(xml, run["name"]))
        except Exception:  # noqa: BLE001 - an unreadable result file is recorded, not raised
            no_result.append(run["name"])
        count = reach_run.refused(offline)
        if count is None:
            counted = False
        else:
            attempts += count["attempts"]
        if out_json is not None:
            traces.append(load_json(out_json) if out_json.exists() else None)
    return {"outcomes": outcomes, "no_result": no_result, "seconds": round(seconds, 3),
            "refused": attempts if counted else None, "traces": traces}


def merge_traces(traces: list[dict]) -> dict:
    """The codes of all the suite runs of 1 copy, merged per code."""
    merged: dict[tuple, dict] = {}
    for doc in traces:
        for c in doc["codes"]:
            k = (c["file"], c["first_line"], c["name"], c["qualname"])
            m = merged.setdefault(k, {"starts": 0, "starts_under_none": 0, "entry_points": set(),
                                      "starts_other_threads": 0, "tests_under_none": [],
                                      "first_test": {}})
            for n, t in c["first_test_per_entry_point"].items():
                m["first_test"].setdefault(n, t)
            m["starts"] += c["starts"]
            m["starts_under_none"] += c["starts_under_none"]
            m["entry_points"] |= set(c["entry_points"])
            m["starts_other_threads"] += c["starts_other_threads"]
            for t in c["tests_under_none"]:
                if t not in m["tests_under_none"] and len(m["tests_under_none"]) < 5:
                    m["tests_under_none"].append(t)
    return merged


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="trace the entry points under which functions start")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--clone")
    parser.add_argument("--python")
    parser.add_argument("--work")
    parser.add_argument("--out")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--base", help="a whole/base.json to compare with, instead of the deposited one")
    args = parser.parse_args(argv)
    subject_path = Path(args.subject).resolve()
    subject = load_json(subject_path)
    name = subject["name"]
    local_path = E / "work" / name / "local.json"
    local = load_json(local_path) if local_path.exists() else {}
    clone = args.clone or local.get("clone")
    python = args.python or local.get("python")
    if not clone or not python:
        raise SystemExit("give --clone and --python")
    work = Path(args.work).resolve() if args.work else EXP / "work" / "trace" / name
    out = Path(args.out).resolve() if args.out else EXP / "generated" / "trace" / name
    ns = argparse.Namespace(subject=str(subject_path), defs=None, work=str(work), clone=clone,
                            python=python, workers=1, out=None, witnesses=str(work / "no-witnesses"))
    ctx = reach_run.Context(ns)       # writes <work>/local.json, reads the definitions only
    ctx.logs.mkdir(parents=True, exist_ok=True)
    checks_doc = load_json(ctx.checks_path)
    files = sorted(checks_doc["sha256"])  # subject and observed files

    plugin_dir = work / "plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_bytes = (HERE / "plugin.py").read_bytes()
    (plugin_dir / f"{PLUGIN_NAME}.py").write_bytes(plugin_bytes)
    trace_files = work / "trace-files.json"
    trace_files.write_text(dump_text({"files": files, "entry_points": subject["entry_points"]}),
                           encoding="utf-8")

    plain_runs, traced_runs = [], []
    for i in range(1, args.repeats + 1):
        for traced in (False, True):
            label = f"{'traced' if traced else 'plain'}-{i}"
            dest = ctx.copies / label
            reach_run.make_copy(ctx, dest)  # fresh, checked against the digests of checks.json
            r = suite_once(ctx, dest, label, plugin_dir if traced else None, trace_files,
                           ctx.records / f"{label}.trace.json", timeout=7200)
            (traced_runs if traced else plain_runs).append(r)
            reach_run.say(f"{label}: {dict(sorted(Counter(r['outcomes'].values()).items()))} "
                          f"in {r['seconds']} s")

    first = traced_runs[0]
    traces_ok = all(t is not None for r in traced_runs for t in r["traces"])
    merged = merge_traces([t for t in first["traces"] if t is not None])
    index, other = function_index(subject, dest, files)
    known = {(f["file"], f["function"]) for f in checks_doc["functions"]}

    fn_rows: dict[tuple, dict] = {}
    unmapped = []
    for (rel, line, cname, qual), m in sorted(merged.items()):
        key = index.get((rel, line, cname))
        if key is None or (rel, key) not in known:
            unmapped.append({"file": rel, "first_line": line, "name": cname, "qualname": qual,
                             "starts": m["starts"], "entry_points": sorted(m["entry_points"]),
                             "reason": other.get((rel, line, cname))})
            continue
        row = fn_rows.setdefault((rel, key), {"file": rel, "function": key, "entry_points": set(),
                                              "starts": 0, "starts_under_none": 0,
                                              "starts_other_threads": 0, "tests_under_none": [],
                                              "first_test_per_entry_point": {}})
        for n, t in sorted(m["first_test"].items()):
            row["first_test_per_entry_point"].setdefault(n, t)
        row["entry_points"] |= m["entry_points"]
        row["starts"] += m["starts"]
        row["starts_under_none"] += m["starts_under_none"]
        row["starts_other_threads"] += m["starts_other_threads"]
        row["tests_under_none"] += [t for t in m["tests_under_none"] if t not in row["tests_under_none"]]
    rows = []
    for k in sorted(fn_rows):
        r = fn_rows[k]
        r["entry_points"] = sorted(r["entry_points"])
        rows.append(r)

    base = load_json(Path(args.base)) if args.base else deposited_base(name)
    passing = sorted(k for k, v in first["outcomes"].items() if v == "passed")
    t3 = (not first["no_result"]) and passing == base["passing"]
    missing = sorted(set(base["passing"]) - set(passing))
    extra = sorted(set(passing) - set(base["passing"]))

    def signature(r: dict) -> tuple:
        m = merge_traces([t for t in r["traces"] if t is not None])
        return (tuple(sorted((k, tuple(sorted(v["entry_points"]))) for k, v in m.items())),
                tuple(sorted(k for k, v in r["outcomes"].items() if v == "passed")))

    def started_under(r: dict) -> set:
        m = merge_traces([t for t in r["traces"] if t is not None])
        return {k for k, v in m.items() if v["entry_points"]}

    repeat_ok, repeat_diff, repeat_reach_ok = None, [], None
    if len(traced_runs) >= 2:
        repeat_ok = all(signature(r) == signature(first) for r in traced_runs[1:])
        repeat_reach_ok = all(started_under(r) == started_under(first) for r in traced_runs[1:])
        m1 = merge_traces([t for t in first["traces"] if t is not None])
        check_fns = {(c["file"], c["function"]) for c in checks_doc["checks"]}
        for i, r in enumerate(traced_runs[1:], 2):
            mi = merge_traces([t for t in r["traces"] if t is not None])
            for k in sorted(set(m1) | set(mi)):
                a = sorted(m1[k]["entry_points"]) if k in m1 else None
                b = sorted(mi[k]["entry_points"]) if k in mi else None
                if a != b:
                    fn = index.get(k[:3])
                    repeat_diff.append({"run": i, "file": k[0], "first_line": k[1], "qualname": k[3],
                                        "run_1": a, f"run_{i}": b,
                                        "first_test_per_entry_point": (mi.get(k) or {}).get("first_test", {}),
                                        "holds_a_check": (k[0], fn) in check_fns})
    anonymous_or_listed = all(u["reason"] for u in unmapped)

    sentinels = [
        {"name": "T3: the tests that pass in the traced run are the tests that pass in both deposited "
                 "whole-baseline runs, and every traced pytest call left its result file",
         "pass": bool(t3 and traces_ok),
         "detail": {"passing_traced": len(passing), "passing_deposited": len(base["passing"]),
                    "missing": missing[:20], "extra": extra[:20], "no_result": first["no_result"],
                    "trace_files_written": traces_ok}},
        {"name": "T-map: every started code of a subject file is a function of checks.json or is listed "
                 "under unmapped with its reason", "pass": anonymous_or_listed},
    ]
    if repeat_ok is not None:
        sentinels.append({"name": "T3-repeat: every traced run gives the same entry-point sets and the "
                                  "same passing tests", "pass": repeat_ok, "detail": repeat_diff})
        sentinels.append({"name": "T3-repeat-reach: every traced run gives the same set of codes that "
                                  "started under at least 1 entry point (the input of rule 3)",
                          "pass": repeat_reach_ok})
    env = environment(ctx.python)
    started_under = [r for r in rows if r["entry_points"]]
    doc = {
        "subject": name,
        "version": subject.get("version"),
        "entry_points": subject["entry_points"],
        "suite_runs": subject["suite_runs"],
        "files": files,
        "interpreter": f"{env['implementation']} {env['version']}",
        "packages": env["packages"],
        "plugin_sha256": sha256_bytes(plugin_bytes),
        "tool_id": (first["traces"][0] or {}).get("tool_id") if first["traces"] else None,
        "definition": ("a function started under an entry point when, at 1 of its PY_START events "
                       "in the traced whole-suite run, a frame of the same thread whose code is a "
                       "function code of a subject file named like an entry point was on the frame "
                       "chain from the new frame outward, the new frame included"),
        "functions": rows,
        "functions_started_only_under_no_entry_point": [
            {"file": r["file"], "function": r["function"], "starts": r["starts"],
             "tests": r["tests_under_none"]} for r in rows if not r["entry_points"]],
        "unmapped": unmapped,
        "counts": {
            "functions_in_checks_json": len(known),
            "functions_started": len(rows),
            "functions_started_under_an_entry_point": len(started_under),
            "functions_started_only_under_no_entry_point": len(rows) - len(started_under),
            "functions_started_at_least_once_under_no_entry_point": sum(1 for r in rows
                                                                        if r["starts_under_none"]),
            "functions_started_in_another_thread": sum(1 for r in rows if r["starts_other_threads"]),
            "unmapped_codes": len(unmapped),
        },
        "outcomes": {
            "traced": dict(sorted(Counter(first["outcomes"].values()).items())),
            "deposited_whole_baseline": base["counts"],
            "refused_connection_attempts_traced": first["refused"],
        },
        "seconds": {"without_plugin": [r["seconds"] for r in plain_runs],
                    "with_plugin": [r["seconds"] for r in traced_runs]},
        "sentinels": sentinels,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "reach.json").write_text(dump_text(doc), encoding="utf-8")
    failed = [s["name"].split(":")[0] for s in sentinels if not s["pass"]]
    c = doc["counts"]
    reach_run.say(f"trace {name}: {c['functions_started']} functions started, "
                  f"{c['functions_started_under_an_entry_point']} under an entry point, "
                  f"{len(unmapped)} unmapped codes; seconds {doc['seconds']}; "
                  f"sentinels that do not hold: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
