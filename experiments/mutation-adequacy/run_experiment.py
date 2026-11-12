#!/usr/bin/env python3
"""Run the mutation-adequacy experiment fixed in PROTOCOL.md.

Stages, in the protocol's order:

    cases     build work/cases.json from the two deposited oracles
    baseline  run both harnesses on the unmutated ports (P1, sentinel 1)
    deletion  delete each guard in each port, plus an unmodified control copy
    mutmut    mutmut 3.8.1 over the Python subject files
    stryker   StrykerJS 9.6.1 over the TypeScript subject files
    all       every stage above, in order

Run it with the experiment's own virtual environment, from any directory:

    experiments/mutation-adequacy/work/venv/bin/python \
        experiments/mutation-adequacy/run_experiment.py all

Everything it writes goes to work/, which is not tracked. analyse.py turns
work/ into the tracked results under generated/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
WORK = HERE / "work"
OUT = WORK / "outcomes"
LOGS = WORK / "logs"
VENV = WORK / "venv"
TSC = REPO_ROOT / "lib" / "node_modules" / "typescript" / "bin" / "tsc"
STRYKER = HERE / "stryker" / "node_modules" / "@stryker-mutator" / "core" / "bin" / "stryker.js"
PY_SUBJECT = ["eatf_verifier/verifier.py", "eatf_verifier/overt.py", "eatf_verifier/tsa.py"]

sys.path.insert(0, str(HERE))
import cases as cases_module  # noqa: E402
from deletions import delete_guard  # noqa: E402


def regions() -> dict:
    return json.loads((HERE / "guard-regions.json").read_text(encoding="utf-8"))


def check_subject() -> None:
    for files in regions()["files"].values():
        for rel, meta in files.items():
            digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
            if digest != meta["sha256"]:
                raise SystemExit(f"subject file differs from guard-regions.json: {rel}")
    if Path(sys.prefix).resolve() != VENV.resolve():
        raise SystemExit(f"run this with {VENV / 'bin' / 'python'}, not {sys.executable}")


def harness_env(out_dir: Path, **extra: str) -> dict:
    env = dict(os.environ)
    env.update({
        "EATF_MUTATION_CASES": str(WORK / "cases.json"),
        "EATF_MUTATION_OUT": str(out_dir),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    env.update(extra)
    return env


def run(cmd: list[str], *, cwd: Path, env: dict | None = None, log: Path | None = None,
        check: bool = True) -> subprocess.CompletedProcess:
    if log is None:
        proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    else:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as handle:
            proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=handle,
                                  stderr=subprocess.STDOUT)
    if check and proc.returncode != 0:
        tail = proc.stdout[-2000:] if log is None else log.read_text()[-2000:]
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{tail}")
    return proc


def fresh(path: Path) -> Path:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


# -- stages ------------------------------------------------------------------

def stage_cases() -> None:
    cases_module.main()


def stage_baseline() -> None:
    run(["npm", "run", "build"], cwd=REPO_ROOT, log=LOGS / "baseline-build.log")
    out_py, out_ts = fresh(OUT / "python"), fresh(OUT / "typescript")
    py = run([sys.executable, str(HERE / "harness_py.py"), "--package-root",
              str(REPO_ROOT / "lib-python"), "--label", "baseline"],
             cwd=WORK, env=harness_env(out_py), check=False)
    ts = run(["node", str(HERE / "harness-ts.mjs")], cwd=WORK, check=False,
             env=harness_env(out_ts, EATF_TS_DIST=str(REPO_ROOT / "lib" / "dist"),
                             EATF_MUTANT_LABEL="baseline"))
    print(f"baseline: python exit {py.returncode}, typescript exit {ts.returncode}")
    print(py.stdout + ts.stdout, end="")

    # sentinel 1: the unmutated ports reproduce the deposited codes
    seen = {
        "python": {o["id"]: o for o in json.loads((out_py / "baseline.json").read_text())["outcomes"]},
        "typescript": {o["id"]: o for o in json.loads((out_ts / "baseline.json").read_text())["outcomes"]},
    }
    mismatches = []
    with (REPO_ROOT / "experiments/decision-path/generated/results/results.csv").open() as handle:
        for row in csv.DictReader(handle):
            for port, prefix in (("python", "py"), ("typescript", "ts")):
                got = seen[port][row["id"]]
                want_valid = row[f"{prefix}_valid"] == "True"
                want_code = row[f"{prefix}_code"] or None
                if (got["valid"], got["code"]) != (want_valid, want_code):
                    mismatches.append((port, row["id"], got, want_valid, want_code))
    with (REPO_ROOT / "experiments/path-shadowing/generated/results.csv").open() as handle:
        for row in csv.DictReader(handle):
            for port, prefix in (("python", "py"), ("typescript", "ts")):
                got = seen[port][row["case"]]
                if (got["valid"], got["code"]) != (False, row[f"{prefix}_code"]):
                    mismatches.append((port, row["case"], got, False, row[f"{prefix}_code"]))
    if mismatches:
        raise SystemExit(f"sentinel 1 failed: {mismatches}")
    print("sentinel 1: both ports reproduce the deposited codes on all 25 cases")


def _ts_copy(target: Path) -> Path:
    fresh(target)
    shutil.copytree(REPO_ROOT / "lib" / "src", target / "src")
    shutil.copy2(REPO_ROOT / "lib" / "tsconfig.json", target / "tsconfig.json")
    shutil.copy2(REPO_ROOT / "lib" / "package.json", target / "package.json")
    (target / "node_modules").symlink_to(REPO_ROOT / "lib" / "node_modules", target_is_directory=True)
    return target


def stage_deletion() -> None:
    data = regions()
    guards = list(data["guards"])
    original = (REPO_ROOT / "lib-python/eatf_verifier/verifier.py").read_text(encoding="utf-8")
    out_py, out_ts = fresh(OUT / "python-deletion"), fresh(OUT / "typescript-deletion")
    replaced: dict[str, dict] = {"python": {}, "typescript": {}}

    for guard in ["control", *guards]:
        root = fresh(WORK / "deletion" / "python" / guard)
        shutil.copytree(REPO_ROOT / "lib-python" / "eatf_verifier", root / "eatf_verifier",
                        ignore=shutil.ignore_patterns("__pycache__"))
        if guard != "control":
            text, rows = delete_guard(original, guard, data)
            (root / "eatf_verifier" / "verifier.py").write_text(text, encoding="utf-8")
            replaced["python"][guard] = rows
        run([sys.executable, str(HERE / "harness_py.py"), "--package-root", str(root),
             "--label", guard], cwd=WORK, env=harness_env(out_py), check=False)

        target = _ts_copy(WORK / "deletion" / "typescript" / guard)
        verifier = target / "src" / "verifier.ts"
        if guard == "control":
            verifier.write_text("// @ts-nocheck\n" + verifier.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            proc = run(["node", str(HERE / "delete-ts.mjs"), guard,
                        str(REPO_ROOT / "lib/src/verifier.ts"), str(verifier)], cwd=WORK)
            replaced["typescript"][guard] = json.loads(proc.stdout)["replaced"]
        run(["node", str(TSC), "-p", str(target / "tsconfig.json")], cwd=target,
            log=LOGS / f"deletion-tsc-{guard}.log")
        run(["node", str(HERE / "harness-ts.mjs")], cwd=WORK, check=False,
            env=harness_env(out_ts, EATF_TS_DIST=str(target / "dist"), EATF_MUTANT_LABEL=guard))
        print(f"deletion {guard}: python and typescript recorded")

    (WORK / "deletion" / "replaced.json").write_text(json.dumps(replaced, indent=2) + "\n")


def stage_mutmut(max_children: int) -> None:
    project = fresh(WORK / "py")
    shutil.copytree(REPO_ROOT / "lib-python" / "eatf_verifier", project / "eatf_verifier",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (project / "tests").mkdir()
    shutil.copy2(HERE / "harness_py.py", project / "tests" / "test_harness.py")
    shutil.copy2(HERE / "mutmut.toml", project / "pyproject.toml")
    out = fresh(OUT / "python-mutmut")
    start = time.monotonic()
    run([str(VENV / "bin" / "mutmut"), "run", "--max-children", str(max_children)],
        cwd=project, env=harness_env(out), log=LOGS / "mutmut-run.log")
    print(f"mutmut: finished in {time.monotonic() - start:.0f} s")
    rows = locate_python_mutants(project)
    (WORK / "python-mutants.json").write_text(json.dumps(rows, indent=1) + "\n")
    print(f"mutmut: {len(rows)} mutants located -> {WORK / 'python-mutants.json'}")


def locate_python_mutants(project: Path) -> list[dict]:
    """Place each mutmut mutant at the first original line it changes, by putting
    the mutant function back into an unmutated copy of its module and diffing
    the two modules line by line."""
    from difflib import SequenceMatcher

    import libcst as cst
    from mutmut.mutation.diff_apply import (
        find_top_level_function_or_method,
        read_functions_from_index,
        read_mutant_function,
    )
    from mutmut.utils.format_utils import orig_function_and_class_names_from_key

    previous = Path.cwd()
    os.chdir(project)  # mutmut's helpers resolve mutants/<path> relative to the project
    try:
        rows = []
        for rel in PY_SUBJECT:
            meta = json.loads((project / "mutants" / f"{rel}.meta").read_text())
            original = (project / rel).read_text(encoding="utf-8")
            orig_module = cst.parse_module(original)
            mutants_module = None
            for name, exit_code in sorted(meta["exit_code_by_key"].items(),
                                          key=lambda kv: (kv[0].rpartition("__mutmut_")[0],
                                                          int(kv[0].rpartition("__mutmut_")[2]))):
                functions = read_functions_from_index(name, rel)
                if functions is not None:
                    mutant_fn = functions[1]
                else:
                    if mutants_module is None:
                        mutants_module = cst.parse_module((project / "mutants" / rel).read_text())
                    mutant_fn = read_mutant_function(mutants_module, name)
                fn_name, class_name = orig_function_and_class_names_from_key(name)
                orig_fn = find_top_level_function_or_method(orig_module, fn_name)
                if orig_fn is None:
                    raise SystemExit(f"cannot find {fn_name} for {name}")
                patched = orig_module.deep_replace(
                    orig_fn, mutant_fn.with_changes(name=cst.Name(fn_name),
                                                    leading_lines=orig_fn.leading_lines)).code
                a, b = original.splitlines(), patched.splitlines()
                ops = [op for op in SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
                       if op[0] != "equal"]
                rows.append({
                    "id": name,
                    "file": f"lib-python/{rel}",
                    "function": fn_name if class_name is None else f"{class_name}.{fn_name}",
                    "line": ops[0][1] + 1 if ops else None,
                    "original": [a[i] for op in ops for i in range(op[1], op[2])],
                    "mutated": [b[j] for op in ops for j in range(op[3], op[4])],
                    "exit_code": exit_code,
                    "duration": meta["durations_by_key"].get(name),
                })
        return rows
    finally:
        os.chdir(previous)


def stage_stryker() -> None:
    out = fresh(OUT / "typescript-stryker")
    report = WORK / "stryker" / "mutation.json"
    if report.exists():
        report.unlink()
    start = time.monotonic()
    run(["node", str(STRYKER), "run", str(HERE / "stryker" / "stryker.config.json")],
        cwd=REPO_ROOT, env=harness_env(out, EATF_REPO_ROOT=str(REPO_ROOT)),
        log=LOGS / "stryker-run.log")
    print(f"stryker: finished in {time.monotonic() - start:.0f} s -> {report}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stage", choices=["cases", "baseline", "deletion", "mutmut", "stryker", "all"])
    parser.add_argument("--max-children", type=int, default=8)
    args = parser.parse_args(argv)
    check_subject()
    WORK.mkdir(exist_ok=True)
    if args.stage in ("cases", "all"):
        stage_cases()
    if args.stage in ("baseline", "all"):
        stage_baseline()
    if args.stage in ("deletion", "all"):
        stage_deletion()
    if args.stage in ("mutmut", "all"):
        stage_mutmut(args.max_children)
    if args.stage in ("stryker", "all"):
        stage_stryker()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
