"""Runner for the PyJWT mutation-adequacy study (see PROTOCOL.md).

Run with the study's own interpreter, from any directory:

    work/venv/bin/python -I run_s2.py <step> [<step> ...]

Steps, in the protocol's order of execution:

    verify     the subject and its test files match the SHA-256 values fixed in
               checks.json and cases.json, the clone is clean at the fixed
               commit, and the venv matches work/pip-freeze.txt
    suite      the whole suite, without the recorder, in a fresh copy
    baseline   2 recorder runs of the unmutated library; sets the timeout
    deletions  the 44 check deletions and 1 unmodified control copy, one
               recorder run each
    mutmut     mutmut's own run, on a copy with [tool.mutmut] appended
    mutants    one recorder run per subject mutant, and 1 run through the
               mutated package with no mutant active

Every run happens in a copy of jwt/, tests/ and pyproject.toml (the files
mutmut copies for this project); the clone in work/pyjwt is never run.
Records go to work/records/. A step that is run again skips the runs whose
record and log line already exist.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
SUBJECT = WORK / "pyjwt"
VENV = WORK / "venv"
PY = VENV / "bin" / "python"
RUNS = WORK / "runs"
RECORDS = WORK / "records"
LOGS = WORK / "logs"
PLUGIN = HERE / "plugin"
CHECKS = HERE / "checks.json"
CASES = HERE / "cases.json"
COPY = ["jwt", "tests", "pyproject.toml"]
WORKERS = 10
PYTHON_VERSION = "3.12.3"
MUTMUT_CONFIG = """
[tool.mutmut]
source_paths = ["jwt"]
only_mutate = ["jwt/api_jws.py", "jwt/api_jwt.py"]
pytest_add_cli_args_test_selection = ["tests/"]
use_git_change_detection = false
"""
PYTEST = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:randomly",
          "--rootdir=.", "--tb=native"]
RECORDER = PYTEST + ["-p", "s2_recorder", "--continue-on-collection-errors"]

MANGLED_METHOD = re.compile(r"^xǁ(?P<cls>[^ǁ]+)ǁ(?P<name>.+)__mutmut_(?P<variant>\d+)$")
MANGLED_FUNCTION = re.compile(r"^x_(?P<name>.+)__mutmut_(?P<variant>\d+)$")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def say(*parts) -> None:
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


# -- environment ------------------------------------------------------------

def clean_env(**extra: str) -> dict[str, str]:
    """A minimal environment: no inherited PYTHONPATH, PYTEST_ADDOPTS,
    MUTANT_UNDER_TEST or coverage hooks."""
    env = {
        "PATH": f"{VENV / 'bin'}:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.update(extra)
    return env


def verify() -> None:
    checks, cases = load(CHECKS), load(CASES)
    commit = checks["subject"]["commit"]
    head = subprocess.run(["git", "-C", str(SUBJECT), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(SUBJECT), "status", "--porcelain"],
                           capture_output=True, text=True, check=True).stdout.strip()
    problems = []
    if head != commit:
        problems.append(f"clone is at {head}, not {commit}")
    if dirty:
        problems.append(f"clone has changes: {dirty[:200]}")
    for rel, digest in checks["subject"]["sha256"].items():
        if sha256(SUBJECT / rel) != digest:
            problems.append(f"{rel}: SHA-256 differs")
    for name, digest in cases["test_files_sha256"].items():
        if sha256(SUBJECT / "tests" / name) != digest:
            problems.append(f"tests/{name}: SHA-256 differs")
    version = subprocess.run([str(PY), "-I", "-c", "import sys; print(sys.version.split()[0])"],
                             capture_output=True, text=True, check=True).stdout.strip()
    if version != PYTHON_VERSION:
        problems.append(f"Python {version}, not {PYTHON_VERSION}")
    freeze = subprocess.run([str(PY), "-I", "-m", "pip", "freeze"], capture_output=True,
                            text=True, check=True, env=clean_env()).stdout.split()
    fixed = (WORK / "pip-freeze.txt").read_text(encoding="utf-8").split()
    if sorted(freeze) != sorted(fixed):
        problems.append(f"venv differs from pip-freeze.txt: {sorted(set(freeze) ^ set(fixed))}")
    importable = subprocess.run([str(PY), "-I", "-c",
                                 "import importlib.util as u; print(u.find_spec('jwt') is None)"],
                                capture_output=True, text=True, check=True, cwd="/",
                                env=clean_env()).stdout.strip()
    if importable != "True":
        problems.append("a jwt package is importable from the venv itself")
    if problems:
        raise SystemExit("verify failed:\n  " + "\n  ".join(problems))
    say("verify: clone at", commit[:12], "clean;", len(checks["subject"]["sha256"]), "subject files and",
        len(cases["test_files_sha256"]), "test files match; Python", version, "; venv matches",
        len(fixed), "pinned packages; jwt not installed")


# -- copies and deletions ---------------------------------------------------

def make_copy(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for item in COPY:
        src = SUBJECT / item
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=ignore)
        else:
            shutil.copy2(src, dest / item)
    for rel, digest in load(CHECKS)["subject"]["sha256"].items():
        if sha256(dest / rel) != digest:
            raise SystemExit(f"copy {dest}: {rel} differs from the subject")


def functions(tree: ast.Module) -> dict[str, ast.AST]:
    """Same walk as define_s2.functions."""
    found: dict[str, ast.AST] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[prefix + child.name] = child
            elif isinstance(child, (ast.If, ast.Try)):
                walk(child, prefix)

    walk(tree, "")
    return found


def raise_nodes(fn: ast.AST) -> list[ast.Raise]:
    """Same numbering as define_s2.raise_nodes and the recorder."""
    out: list[ast.Raise] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(child, ast.Raise):
                out.append(child)
            visit(child)

    visit(fn)
    return sorted(out, key=lambda r: (r.lineno, r.col_offset))


def delete_raises(source: str, function: str, ordinals: list[int]) -> tuple[str, list[dict]]:
    """Every listed raise statement of `function` becomes `pass`; its
    continuation lines become empty, so every other line keeps its number."""
    tree = ast.parse(source)
    fn = functions(tree)[function]
    raises = raise_nodes(fn)
    lines = [line.encode("utf-8") for line in source.splitlines(keepends=True)]
    changed = []
    for k in sorted(ordinals, reverse=True):
        node = raises[k]
        first, last = node.lineno - 1, node.end_lineno - 1
        prefix = lines[first][:node.col_offset]
        suffix = lines[last][node.end_col_offset:]
        if prefix.strip():
            raise SystemExit(f"{function} raise {k}: does not start its line")
        if suffix.strip() and not suffix.strip().startswith(b"#"):
            raise SystemExit(f"{function} raise {k}: shares its last line with other code")
        removed = b"".join(lines[first:last + 1]).decode("utf-8")
        if first == last:
            lines[first] = prefix + b"pass" + suffix
        else:
            lines[first] = prefix + b"pass\n"
            for i in range(first + 1, last):
                lines[i] = b"\n"
            lines[last] = suffix if suffix.strip() else b"\n"
        changed.append({"raise": k, "lines": [node.lineno, node.end_lineno], "removed": removed})
    out = b"".join(lines).decode("utf-8")
    new_tree = ast.parse(out)
    compile(out, function, "exec")
    if len(out.splitlines()) != len(source.splitlines()):
        raise SystemExit(f"{function}: the deletion changed the line count")
    left = raise_nodes(functions(new_tree)[function])
    if len(left) != len(raises) - len(ordinals):
        raise SystemExit(f"{function}: {len(raises) - len(left)} raises gone, expected {len(ordinals)}")
    for name, node in functions(tree).items():
        if name != function and ast.dump(node) != ast.dump(functions(new_tree)[name]):
            raise SystemExit(f"{function}: the deletion also changed {name}")
    return out, sorted(changed, key=lambda c: c["raise"])


# -- runs -------------------------------------------------------------------

def log_line(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def logged(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        out[entry["name"]] = entry
    return out


def recorder_run(name: str, cwd: Path, out: Path, timeout: float, mutant: str | None = None,
                 select: str = "cases") -> dict:
    env = clean_env(PYTHONPATH=str(PLUGIN), S2_CASES=str(CASES), S2_CHECKS=str(CHECKS),
                    S2_OUT=str(out), S2_PACKAGE="jwt", S2_SELECT=select)
    if mutant is not None:
        env["S2_MUTANT"] = mutant
    if out.exists():
        out.unlink()
    start = time.monotonic()
    try:
        proc = subprocess.run([str(PY)] + RECORDER, cwd=cwd, env=env, capture_output=True,
                              text=True, timeout=timeout)
        timed_out, code, tail = False, proc.returncode, (proc.stdout + proc.stderr)[-1500:]
    except subprocess.TimeoutExpired as e:
        timed_out, code = True, None
        tail = ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes)
                else (e.stdout or ""))[-1500:]
    seconds = round(time.monotonic() - start, 3)
    return {"name": name, "mutant": mutant, "cwd": str(cwd), "returncode": code,
            "timed_out": timed_out, "seconds": seconds, "record": out.exists(),
            "timeout": timeout, "tail": tail}


def run_many(jobs: list[tuple], log: Path) -> None:
    """jobs: (name, cwd, out, mutant). Skips the jobs already logged with a record."""
    done = logged(log)

    def finished(job) -> bool:
        entry = done.get(job[0])
        return entry is not None and (entry["timed_out"] or (entry["record"] and job[2].exists()))

    todo = [j for j in jobs if not finished(j)]
    timeout = load(RECORDS / "baseline" / "timeout.json")["timeout_seconds"]
    say(f"{len(todo)} of {len(jobs)} runs to do, {WORKERS} at a time, timeout {timeout} s")
    started = time.monotonic()

    def one(job):
        name, cwd, out, mutant = job
        return recorder_run(name, cwd, out, timeout, mutant)

    with ThreadPoolExecutor(WORKERS) as pool:
        for i, entry in enumerate(pool.map(one, todo), 1):
            log_line(log, entry)
            if entry["timed_out"] or not entry["record"]:
                say("  ", entry["name"], "timed out" if entry["timed_out"] else "no record")
            if i % 50 == 0 or i == len(todo):
                say(f"  {i}/{len(todo)} done, {time.monotonic() - started:.0f} s")


def suite() -> None:
    dest = RUNS / "suite"
    make_copy(dest)
    start = time.monotonic()
    proc = subprocess.run([str(PY)] + PYTEST, cwd=dest, env=clean_env(), capture_output=True, text=True,
                          timeout=1800)
    lines = (proc.stdout + proc.stderr).strip().splitlines()
    summary = lines[-1] if lines else ""
    skipped = [line for line in lines if line.startswith("SKIPPED")]
    dump(RECORDS / "suite.json", {"returncode": proc.returncode, "summary": summary, "skipped": skipped,
                                  "seconds": round(time.monotonic() - start, 3)})
    say("suite:", proc.returncode, summary)
    if proc.returncode != 0:
        raise SystemExit("the suite does not pass without the recorder")


def baseline() -> None:
    dest = RUNS / "baseline"
    make_copy(dest)
    entries = []
    for name in ("base-1", "base-2"):
        entry = recorder_run(name, dest, RECORDS / "baseline" / f"{name}.json", timeout=1800)
        entries.append(entry)
        log_line(RECORDS / "baseline" / "runs.jsonl", entry)
        say(name, "returncode", entry["returncode"], entry["seconds"], "s")
        if entry["timed_out"] or not entry["record"]:
            raise SystemExit(f"{name}: no record")
    slowest = max(e["seconds"] for e in entries)
    dump(RECORDS / "baseline" / "timeout.json",
         {"baseline_seconds": slowest, "rule": "max(60 s, 10 x the slower baseline run)",
          "timeout_seconds": max(60.0, round(10 * slowest, 1))})


def deletions() -> None:
    checks = load(CHECKS)
    root = RUNS / "deletions"
    jobs = []
    control = root / "_control"
    if not (control / "jwt").exists():
        make_copy(control)
    jobs.append(("_control", control, RECORDS / "deletions" / "_control.json", None))
    for check in checks["checks"]:
        if not check["mutated"]:
            continue
        dest = root / check["id"]
        target = dest / check["file"]
        if not (dest / "deletion.json").exists():
            make_copy(dest)
            source = target.read_text(encoding="utf-8")
            new, changed = delete_raises(source, check["function"], check["raises"])
            target.write_text(new, encoding="utf-8")
            dump(dest / "deletion.json", {"check": check["id"], "file": check["file"],
                                          "function": check["function"], "raises": changed,
                                          "sha256_before": hashlib.sha256(source.encode()).hexdigest(),
                                          "sha256_after": sha256(target)})
        jobs.append((check["id"], dest, RECORDS / "deletions" / f"{check['id']}.json", None))
    say(f"deletions: {len(jobs) - 1} deletion copies and 1 control copy")
    run_many(jobs, RECORDS / "deletions" / "runs.jsonl")


def mutmut() -> None:
    dest = WORK / "mutmut"
    if (dest / "mutants").exists():
        raise SystemExit(f"{dest / 'mutants'} exists; remove it to run mutmut again")
    make_copy(dest)
    with (dest / "pyproject.toml").open("a", encoding="utf-8") as handle:
        handle.write(MUTMUT_CONFIG)
    LOGS.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with (LOGS / "mutmut-run.log").open("w", encoding="utf-8") as handle:
        proc = subprocess.run([str(VENV / "bin" / "mutmut"), "run", "--max-children", str(WORKERS)],
                              cwd=dest, env=clean_env(), stdout=handle, stderr=subprocess.STDOUT)
    dump(RECORDS / "mutmut.json", {"returncode": proc.returncode,
                                   "seconds": round(time.monotonic() - start, 1),
                                   "config": MUTMUT_CONFIG.strip()})
    say("mutmut: returncode", proc.returncode)


def mutant_function(key: str) -> tuple[str, str]:
    """'jwt.api_jws.xǁPyJWSǁ_load__mutmut_7' -> ('jwt/api_jws.py', 'PyJWS._load')."""
    module, _, mangled = key.rpartition(".")
    m = MANGLED_METHOD.match(mangled)
    if m:
        return module.replace(".", "/") + ".py", f"{m['cls']}.{m['name']}"
    m = MANGLED_FUNCTION.match(mangled)
    if m:
        return module.replace(".", "/") + ".py", m["name"]
    raise SystemExit(f"cannot read mutant name {key}")


def mutant_list() -> list[dict]:
    checks = load(CHECKS)
    out = []
    for rel in sorted(checks["subject_functions"]):
        meta = load(WORK / "mutmut" / "mutants" / (rel + ".meta"))
        for key, code in sorted(meta["exit_code_by_key"].items()):
            file, function = mutant_function(key)
            if file != rel:
                raise SystemExit(f"{key} is listed under {rel}")
            subject = function in checks["subject_functions"][rel]
            if not subject and function not in checks["outside_functions"][rel]:
                raise SystemExit(f"{key}: {function} is neither a subject nor an outside function")
            out.append({"key": key, "file": file, "function": function, "subject": subject,
                        "exit_code": code})
    return out


def mutants() -> None:
    root = WORK / "mutmut" / "mutants"
    listed = mutant_list()
    dump(RECORDS / "mutants" / "list.json", listed)
    subject = [m for m in listed if m["subject"]]
    say(f"mutants: {len(listed)} from mutmut, {len(subject)} in subject functions")
    jobs = [("_none", root, RECORDS / "mutants" / "_none.json", "")]
    jobs += [(m["key"], root, RECORDS / "mutants" / f"{m['key']}.json", m["key"]) for m in subject]
    run_many(jobs, RECORDS / "mutants" / "runs.jsonl")


STEPS = {"verify": verify, "suite": suite, "baseline": baseline, "deletions": deletions,
         "mutmut": mutmut, "mutants": mutants}


def main(argv: list[str]) -> int:
    if not argv or any(a not in STEPS for a in argv):
        print(__doc__)
        return 2
    if Path(sys.prefix).resolve() != VENV.resolve():
        raise SystemExit(f"run with {PY}")
    for step in argv:
        say("==", step)
        STEPS[step]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
