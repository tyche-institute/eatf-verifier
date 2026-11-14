"""Verification of the repaired variants of 3 joserfc 1.8.0 tests.

    python3 -I -B repaired/joserfc/verify.py [--python VENV_PYTHON] [--clone DIR]
                                             [--work DIR] [--out FILE] [--no-recorder]

Run from the experiment directory or from anywhere: every default path is
taken relative to this file. `--python` and `--clone` default to the
interpreter and the clone named in ../target-reach/work/joserfc/local.json;
`--work` defaults to work/repaired/verify; `--out` to verify.json beside this
file.

What it does, on fresh copies of the unmodified release (the paths of
"copy" in ../target-reach/subjects/joserfc/subject.json):

0. Checks. The clone is at the commit and its copied paths are clean, and
   the `verify` step of ../target-reach/reach/run.py passes on the clone and
   the interpreter (its work folder, which receives only local.json, is
   <work>/toolkit-verify).
1. Probe run. 1 pytest call on a copy that also holds tests_repaired/: the 3
   original tests and the 3 variants, with the offline module of the toolkit
   (../target-reach/guard/reach_offline.py) and a probe plugin that this
   script writes into the work folder. The probe wraps the `__exit__` method
   of unittest's assertRaises context, which serves the callable form too,
   and records for each execution of an assertRaises block: the line of the
   test that called it (for the `with` form, the line of the `with`
   statement), the class of the exception, the innermost frame of
   its traceback and the innermost frame inside the package directory. The
   raise site (file relative to the source root, line) is looked up in the
   line ranges of the checks in ../target-reach/subjects/joserfc/checks.json.
2. Whole-suite runs. The suite run of subject.json ("tests"), 1 time on a
   copy with tests_repaired/ added to the test paths and 1 time on a copy
   without it, each as 1 pytest call with the offline module and a junit XML
   result file.
3. Recorder run (skipped with --no-recorder). A derived subject in the work
   folder: a directory that holds the copied paths of the clone plus
   tests_repaired/, and a subject.json that differs from the toolkit's in 5
   fields only (name, no commit, copy, tests, suite_runs). The toolkit's own
   runner (../target-reach/reach/run.py) runs `define targets baseline` on it
   with its definitions and records in the work folder; the deciding check of
   each of the 6 blocks is read from both baseline recorder records.

Every pytest call gets the environment of the toolkit's runner: PATH, HOME,
LANG and LC_ALL set to C.UTF-8, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1,
and the options of "pytest_args".

The script writes `--out` and then exits with status 1 when a sentinel does
not hold. The sentinels are listed in SENTINELS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent             # repaired/joserfc
EXPERIMENT = HERE.parents[1]                       # target-reach-followup
TOOLKIT = EXPERIMENT.parent / "target-reach"
SUBJECT_DIR = TOOLKIT / "subjects" / "joserfc"
GUARD = TOOLKIT / "guard"
VARIANTS = HERE / "tests_repaired"
VARIANT_DIR = "tests_repaired"                     # where the folder goes in a copy

SENTINELS = {
    "S1": "the clone is at the commit of subject.json and its copied paths hold no changed, "
          "untracked or ignored file, and the `verify` step of the toolkit's runner passes on the "
          "clone and the interpreter (digests of the subject and test files, CPython in the version "
          "of subject.json, packages exactly those of requirements.txt besides pip, joserfc not "
          "installed)",
    "S2": "in every copy, the subject files and the test files have the SHA-256 values of "
          "checks.json and blocks.json, before and after the runs, and the variant files equal "
          "those of tests_repaired/",
    "S3": "each original case: exactly 1 execution at the expected line, the caught class is the "
          "expected class, the innermost frame of the traceback is the innermost frame inside the "
          "package, and its line belongs to the expected deciding check",
    "S4": "each variant: exactly 1 execution, the caught class is the expected class, the innermost "
          "frame is the innermost frame inside the package, its line belongs to the target, and the "
          "test passes",
    "S5": "the whole suite with the variants exits with 0, has no failed or erroneous test and no "
          "collection error, and its passing tests are those of the whole suite without the "
          "variants plus the 3 variants",
    "S6": "no pytest call made an attempt to reach another machine",
    "S7": "recorder run (when made): the derived checks are those of checks.json, the blocks of the "
          "original test files are those of blocks.json, the rule gives every original block the target "
          "of targets.json, both baseline records give each of the 6 "
          "blocks the same deciding check, and it is the check of the probe run",
}

CASES = [
    {
        "original_test": "tests/jwe/test_compact.py::TestJWECompact::test_ciphertext_exceeds_size",
        "original_index": 0,
        "original_where": "tests/jwe/test_compact.py:276",
        "original_block": "tests/jwe/test_compact.py::TestJWECompact.test_ciphertext_exceeds_size#0",
        "expected_class": "joserfc.errors.ExceededSizeError",
        "deciding": "_rfc7516.registry.JWERegistry.validate_compact_value_size#1",
        "target": "_rfc7516.registry.JWERegistry.validate_ciphertext_size#1",
        "variant_test": "tests_repaired/test_repaired_jwe_compact.py::TestJWECompactRepaired::"
                        "test_repaired_ciphertext_exceeds_size",
    },
    {
        "original_test": "tests/jws/test_compact.py::TestCompact::test_payload_exceeded_size_error",
        "original_index": 0,
        "original_where": "tests/jws/test_compact.py:71",
        "original_block": "tests/jws/test_compact.py::TestCompact.test_payload_exceeded_size_error#0",
        "expected_class": "joserfc.errors.ExceededSizeError",
        "deciding": "_rfc7515.registry.JWSRegistry.validate_compact_value_size#1",
        "target": "_rfc7515.registry.JWSRegistry.validate_payload_size#1",
        "variant_test": "tests_repaired/test_repaired_jws_compact.py::TestCompactRepaired::"
                        "test_repaired_payload_exceeded_size_error",
    },
    {
        "original_test": "tests/jws/test_json.py::TestJSON::test_b64_must_be_protected",
        "original_index": 1,
        "original_where": "tests/jws/test_json.py:166",
        "original_block": "tests/jws/test_json.py::TestJSON.test_b64_must_be_protected#1",
        "expected_class": "joserfc.errors.UnsupportedHeaderError",
        "deciding": "registry.reject_unprotected_crit_header#2",
        "target": "_rfc7797.json._is_payload_base64_encoded#1",
        "variant_test": "tests_repaired/test_repaired_jws_json.py::TestJSONRepaired::"
                        "test_repaired_b64_must_be_protected",
    },
]

# The probe plugin, written into the work folder and loaded with `-p repaired_probe`.
PROBE = r'''
"""Records every execution of a unittest assertRaises block (written by verify.py)."""
import json
import os
import sys
import unittest.case

PACKAGE = os.path.realpath(os.environ["PROBE_PACKAGE"])
SOURCE_ROOT = os.path.realpath(os.environ["PROBE_SOURCE_ROOT"])
ROOT = os.path.realpath(os.environ["PROBE_ROOT"])
RECORDS = []
COUNTS = {}
OUTCOMES = {}
_EXIT = unittest.case._AssertRaisesContext.__exit__


def _rel(path, base):
    return os.path.relpath(os.path.realpath(path), base).replace(os.sep, "/")


def _inside(path, base):
    real = os.path.realpath(path)
    return real == base or real.startswith(base + os.sep)


def _frames(tb):
    out = []
    while tb is not None:
        code = tb.tb_frame.f_code
        out.append({"path": code.co_filename, "function": code.co_qualname, "line": tb.tb_lineno})
        tb = tb.tb_next
    return out


def _frame(entry):
    if entry is None:
        return None
    inside = _inside(entry["path"], PACKAGE)
    return {"file": _rel(entry["path"], SOURCE_ROOT if inside else ROOT), "inside_package": inside,
            "function": entry["function"], "line": entry["line"]}


def _caller():
    """The innermost frame of the current stack in a file of the copy outside the package."""
    frame = sys._getframe(2)
    while frame is not None:
        path = frame.f_code.co_filename
        if _inside(path, ROOT) and not _inside(path, PACKAGE):
            return f"{_rel(path, ROOT)}:{frame.f_lineno}"
        frame = frame.f_back
    return None


def _exit(self, exc_type, exc_value, tb):
    test = os.environ.get("PYTEST_CURRENT_TEST", "").rsplit(" (", 1)[0]
    index = COUNTS.get(test, 0)
    COUNTS[test] = index + 1
    frames = _frames(tb) if tb is not None else []
    package = [f for f in frames if _inside(f["path"], PACKAGE)]
    expected = self.expected if isinstance(self.expected, tuple) else (self.expected,)
    RECORDS.append({
        "test": test,
        "index": index,
        "where": _caller(),
        "expected": [f"{c.__module__}.{c.__qualname__}" for c in expected],
        "raised": exc_type is not None,
        "class": f"{exc_type.__module__}.{exc_type.__qualname__}" if exc_type is not None else None,
        "message": str(exc_value) if exc_value is not None else None,
        "innermost": _frame(frames[-1] if frames else None),
        "innermost_in_package": _frame(package[-1] if package else None),
    })
    return _EXIT(self, exc_type, exc_value, tb)


unittest.case._AssertRaisesContext.__exit__ = _exit


def pytest_runtest_logreport(report):
    seen = OUTCOMES.setdefault(report.nodeid, [])
    seen.append(report.outcome)


def pytest_sessionfinish(session, exitstatus):
    outcomes = {}
    for nodeid, seen in OUTCOMES.items():
        outcomes[nodeid] = ("failed" if "failed" in seen else "skipped" if "skipped" in seen
                            else "passed")
    with open(os.environ["PROBE_OUT"], "w", encoding="utf-8") as handle:
        json.dump({"records": RECORDS, "outcomes": outcomes, "exitstatus": int(exitstatus)},
                  handle, indent=1, sort_keys=True)
        handle.write("\n")
'''


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel_to_source(subject: dict, rel: str) -> str:
    root = subject.get("source_root", ".")
    return rel if root in (".", "") else f"{root}/{rel}"


def published(path: Path) -> str:
    """A path as written into the published output: relative to the experiment directory."""
    try:
        return os.path.relpath(path.resolve(), EXPERIMENT).replace(os.sep, "/")
    except ValueError:
        return path.name


def check_lines(checks: dict) -> dict[str, dict[int, str]]:
    """file -> line -> check id, from the line ranges of the raise statements."""
    out: dict[str, dict[int, str]] = {}
    for c in checks["checks"]:
        for a, z in c["lines"]:
            for line in range(a, z + 1):
                out.setdefault(c["file"], {})[line] = c["id"]
    return out


def site_check(lines: dict[str, dict[int, str]], frame: dict | None) -> str | None:
    if not frame or not frame.get("inside_package"):
        return None
    return lines.get(frame["file"], {}).get(frame["line"])


def fresh_dir(work: Path, name: str) -> Path:
    """An empty directory <work>/<name>; only a directory inside the work folder is removed."""
    dest = (work / name).resolve()
    if work.resolve() not in dest.parents:
        raise SystemExit(f"refusing to remove {dest}: not inside the work folder")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    return dest


def make_copy(subject: dict, clone: Path, dest: Path, with_variants: bool) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in subject["copy"]:
        src = clone / item
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=ignore)
        else:
            (dest / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / item)
    if with_variants:
        (dest / VARIANT_DIR).mkdir()
        for f in variant_files():
            shutil.copy2(f, dest / VARIANT_DIR / f.name)


def variant_files() -> list[Path]:
    return sorted(VARIANTS.glob("test_*.py"))


def copy_problems(subject: dict, checks: dict, blocks: dict, dest: Path, with_variants: bool) -> list[str]:
    problems = []
    for rel, digest in checks["sha256"].items():
        if sha256(dest / rel_to_source(subject, rel)) != digest:
            problems.append(f"{dest.name}: {rel} differs from checks.json")
    for rel, digest in blocks["test_files_sha256"].items():
        if sha256(dest / rel) != digest:
            problems.append(f"{dest.name}: {rel} differs from blocks.json")
    if with_variants:
        for f in variant_files():
            if sha256(dest / VARIANT_DIR / f.name) != sha256(f):
                problems.append(f"{dest.name}: {VARIANT_DIR}/{f.name} differs from the published file")
    return problems


def run_env(python: Path, **extra: str) -> dict[str, str]:
    env = {
        "PATH": f"{python.parent}:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.update(extra)
    return env


def pytest_call(python: Path, subject: dict, cwd: Path, paths: list[str], plugins: list[str],
                pythonpath: list[Path], log: Path, offline_out: Path, extra_env: dict | None = None,
                extra_args: list[str] | None = None) -> dict:
    cmd = [str(python), "-m", "pytest", "-q", *subject.get("pytest_args", []), "-p", "reach_offline"]
    for plugin in plugins:
        cmd += ["-p", plugin]
    cmd += ["--rootdir=.", "--tb=native", "-rfE", *(extra_args or []), *paths]
    src = subject.get("source_root", ".")
    path_parts = [str(p) for p in pythonpath] + ([str(cwd / src)] if src not in (".", "") else [])
    env = run_env(python, PYTHONPATH=os.pathsep.join(path_parts), OFFLINE_OUT=str(offline_out),
                  **(extra_env or {}))
    if offline_out.exists():
        offline_out.unlink()
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=3600)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    refused = load_json(offline_out) if offline_out.exists() else None
    tail = [line for line in proc.stdout.splitlines() if line.strip()]
    # pytest's last line without its duration, so that the output does not depend on the timing
    summary = re.sub(r" in [0-9.]+s( \([0-9:]+\))?$", "", tail[-1].strip("= ")) if tail else ""
    return {"returncode": proc.returncode, "summary": summary,
            "refused_attempts": None if refused is None else refused["attempts"]}


def junit_outcomes(path: Path, root: Path) -> dict[str, str]:
    """test id (file::class::name) -> passed, failed, error or skipped."""
    out: dict[str, str] = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        classname, name = case.get("classname", ""), case.get("name", "")
        parts = classname.split(".")
        # classname is dotted module path plus class; the file is the module path
        test_id = f"{classname}::{name}"
        for i in range(len(parts), 0, -1):
            candidate = "/".join(parts[:i]) + ".py"
            if (root / candidate).is_file():
                test_id = "::".join([candidate, *parts[i:], name])
                break
        status = "passed"
        for child in case:
            if child.tag in ("failure", "error"):
                status = "failed" if child.tag == "failure" else "error"
                break
            if child.tag == "skipped":
                status = "skipped"
        if test_id in out and out[test_id] != status:
            status = "failed"
        out[test_id] = status
    return out


def judge_record(rec: dict | None, lines, expected_class: str, expected_check: str,
                 expected_where: str | None) -> tuple[dict, list[str]]:
    """The reading of 1 recorded execution and the problems found with it."""
    problems = []
    if rec is None:
        return {"recorded": False}, ["no execution recorded"]
    check = site_check(lines, rec["innermost_in_package"])
    row = {
        "recorded": True,
        "where": rec["where"],
        "class": rec["class"],
        "message": rec["message"],
        "innermost_frame": rec["innermost"],
        "raise_site": rec["innermost_in_package"],
        "check": check,
        "expected_check": expected_check,
    }
    if expected_where is not None and rec["where"] != expected_where:
        problems.append(f"executed at {rec['where']}, expected {expected_where}")
    if rec["class"] != expected_class:
        problems.append(f"caught {rec['class']}, expected {expected_class}")
    if rec["innermost"] != rec["innermost_in_package"]:
        problems.append("the innermost frame of the traceback is not the innermost frame inside the package")
    if check != expected_check:
        problems.append(f"raise site belongs to {check}, expected {expected_check}")
    return row, problems


# -- recorder run on a derived subject ------------------------------------------

DERIVED_NAME = "joserfc-repaired"


def derived_subject(subject: dict) -> dict:
    derived = json.loads(json.dumps(subject))
    derived["name"] = DERIVED_NAME
    derived.pop("commit", None)
    derived["copy"] = [*subject["copy"], VARIANT_DIR]
    derived["tests"] = sorted([*subject["tests"], *(f"{VARIANT_DIR}/{f.name}" for f in variant_files())])
    derived["suite_runs"] = [{"name": r["name"], "paths": [*r["paths"], VARIANT_DIR]}
                             for r in subject["suite_runs"]]
    return derived


def recorder_section(subject, checks, blocks, clone, python, work, probe_rows) -> tuple[dict, list[str]]:
    problems: list[str] = []
    root = fresh_dir(work, "derived")
    clone_copy = root / "clone"
    clone_copy.mkdir()
    make_copy(subject, clone, clone_copy, with_variants=True)
    defs = root / "defs"
    defs.mkdir()
    derived = derived_subject(subject)
    dump(defs / "subject.json", derived)
    rwork = root / "work"
    cmd = [sys.executable, "-I", "-B", str(TOOLKIT / "reach" / "run.py"), "define", "targets", "baseline",
           "--subject", str(defs / "subject.json"), "--defs", str(defs), "--work", str(rwork),
           "--clone", str(clone_copy), "--python", str(python)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200,
                          env=dict(os.environ, PYTHONHASHSEED="0"))
    (work / "logs").mkdir(parents=True, exist_ok=True)
    (work / "logs" / "recorder-run.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    section = {"runner_returncode": proc.returncode,
               "derived_subject_differs_in": ["name", "commit (removed)", "copy (+ tests_repaired)",
                                              "tests (+ the 3 variant files)",
                                              "suite_runs (+ tests_repaired in each)"]}
    if proc.returncode != 0:
        return section, [f"the runner exited with {proc.returncode} (see the log of the recorder run)"]
    dchecks, dblocks = load_json(defs / "checks.json"), load_json(defs / "blocks.json")
    dtargets = load_json(defs / "targets.json")
    if dchecks["checks"] != checks["checks"]:
        problems.append("the checks of the derived subject differ from checks.json")
    original_files = set(blocks["test_files_sha256"])
    if [b for b in dblocks["blocks"] if b["file"] in original_files] != blocks["blocks"]:
        problems.append("the blocks of the original test files differ from blocks.json")
    new_blocks = [b for b in dblocks["blocks"] if b["file"].startswith(VARIANT_DIR + "/")]
    original_targets = {t["key"]: t["target"] for t in load_json(SUBJECT_DIR / "targets.json")["blocks"]}
    derived_targets = {t["key"]: t["target"] for t in dtargets["blocks"]}
    changed_targets = sorted(k for k in original_targets if derived_targets.get(k) != original_targets[k])
    section["original_blocks_with_another_target"] = changed_targets
    if changed_targets:
        problems.append(f"{len(changed_targets)} original blocks get another target in the derived subject")
    target_of = {t["key"]: t for t in dtargets["blocks"]}
    records = [load_json(rwork / "records" / f"{n}.json") for n in ("base-1", "base-2")]
    refused = load_json(rwork / "records" / "refused.json")
    suite = load_json(rwork / "records" / "suite.json")
    section["suite_without_recorder"] = {"summary": suite["summary"], "failures": suite["failures"],
                                         "not_collected": suite["not_collected"],
                                         "refused_attempts": suite["refused"]["attempts"]}
    section["recorder_refused_attempts"] = {k: (v or {}).get("attempts") for k, v in sorted(refused.items())}
    if suite["refused"]["attempts"] != 0 or any((v or {}).get("attempts") != 0 for v in refused.values()):
        problems.append("a run of the derived subject made an attempt to reach another machine")
    if suite["failures"] or suite["not_collected"]:
        problems.append("the suite run of the derived subject has failures or files not collected")

    def case_of(record, block, index):
        found = [c for c in record["cases"] if c["block"] == block and c["index"] == index]
        return found[0] if len(found) == 1 else None

    rows = []
    for case, probe in zip(CASES, probe_rows):
        vblock = [b for b in new_blocks if b["test"] == case["variant_test"].split("::")[-1]]
        for kind, block, expected in (("original", case["original_block"], probe["original"]["check"]),
                                      ("variant", vblock[0]["key"] if len(vblock) == 1 else None,
                                       probe["variant"]["check"])):
            row = {"kind": kind, "block": block}
            if block is None:
                problems.append(f"{case['variant_test']}: its block is not found exactly 1 time in the "
                                "derived blocks.json")
                rows.append(row)
                continue
            got = [case_of(r, block, 0) for r in records]
            row["included"] = next((b["included"] for b in dblocks["blocks"] if b["key"] == block), None)
            row["deciding_check"] = [g["site"]["check"] if g and g.get("site") else None for g in got]
            row["fired"] = [g["fired"] if g else None for g in got]
            row["check_result"] = [g["check_result"] if g else None for g in got]
            t = target_of.get(block)
            row["rule_target"] = t.get("target") if t else None
            row["rule_basis"] = t.get("basis") if t else None
            row["rule_tier"] = t.get("tier") if t else None
            if None in got:
                problems.append(f"{block}: not recorded exactly 1 time in each baseline record")
            elif row["deciding_check"][0] != row["deciding_check"][1]:
                problems.append(f"{block}: the 2 baseline records give different deciding checks")
            elif row["deciding_check"][0] != expected:
                problems.append(f"{block}: recorded deciding check {row['deciding_check'][0]}, probe {expected}")
            rows.append(row)
    section["blocks"] = rows
    section["new_blocks"] = len(new_blocks)
    return section, problems


# -- main -----------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--python")
    parser.add_argument("--clone")
    parser.add_argument("--work", default=str(EXPERIMENT / "work" / "repaired" / "verify"))
    parser.add_argument("--out", default=str(HERE / "verify.json"))
    parser.add_argument("--no-recorder", action="store_true")
    args = parser.parse_args(argv)

    subject = load_json(SUBJECT_DIR / "subject.json")
    checks = load_json(SUBJECT_DIR / "checks.json")
    blocks = load_json(SUBJECT_DIR / "blocks.json")
    local = load_json(TOOLKIT / "work" / "joserfc" / "local.json") if not (args.python and args.clone) else {}
    python = Path(args.python or local["python"]).absolute()
    clone = Path(args.clone or local["clone"]).resolve()
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    lines = check_lines(checks)
    problems: dict[str, list[str]] = {k: [] for k in SENTINELS}

    # S1: the clone
    git_env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True,
                          env=git_env).stdout.strip()
    if head != subject["commit"]:
        problems["S1"].append(f"clone at {head or '?'}, not {subject['commit']}")
    dirty = subprocess.run(["git", "-C", str(clone), "status", "--porcelain", "--untracked-files=all",
                            "--ignored", "--", *subject["copy"]], capture_output=True, text=True, env=git_env)
    extra = [ln for ln in dirty.stdout.splitlines()
             if ln.strip() and "__pycache__/" not in ln and not ln.endswith(".pyc") and ".pytest_cache/" not in ln]
    if dirty.returncode != 0 or extra:
        problems["S1"].append(f"copied paths not clean: {extra[:5] or dirty.stderr.strip()[:200]}")

    # the toolkit's own `verify` step; its work folder (only local.json) is ours
    tool_verify = subprocess.run(
        [sys.executable, "-I", "-B", str(TOOLKIT / "reach" / "run.py"), "verify",
         "--subject", str(SUBJECT_DIR / "subject.json"), "--work", str(work / "toolkit-verify"),
         "--clone", str(clone), "--python", str(python)],
        capture_output=True, text=True, timeout=600)
    (work / "logs").mkdir(parents=True, exist_ok=True)
    (work / "logs" / "toolkit-verify.log").write_text(tool_verify.stdout + tool_verify.stderr, encoding="utf-8")
    if tool_verify.returncode != 0:
        problems["S1"].append(f"the toolkit's verify step failed: {tool_verify.stderr.strip()[-300:]}")

    interpreter = subprocess.run([str(python), "-I", "-c",
                                  "import platform, sys, pytest; print(platform.python_implementation(), "
                                  "sys.version.split()[0], 'pytest', pytest.__version__)"],
                                 capture_output=True, text=True).stdout.strip()

    plugin_dir = fresh_dir(work, "plugin")
    (plugin_dir / "repaired_probe.py").write_text(PROBE.lstrip(), encoding="utf-8")

    # 1. probe run
    probe_copy = fresh_dir(work, "copy-probe")
    make_copy(subject, clone, probe_copy, with_variants=True)
    problems["S2"] += copy_problems(subject, checks, blocks, probe_copy, True)
    probe_out = work / "probe.json"
    if probe_out.exists():
        probe_out.unlink()
    paths = [c["original_test"] for c in CASES] + [c["variant_test"] for c in CASES]
    src_root = probe_copy / subject.get("source_root", ".")
    probe_call = pytest_call(python, subject, probe_copy, paths, ["repaired_probe"], [GUARD, plugin_dir],
                             work / "logs" / "probe.log", work / "probe.offline.json",
                             extra_env={"PROBE_OUT": str(probe_out), "PROBE_ROOT": str(probe_copy),
                                        "PROBE_SOURCE_ROOT": str(src_root),
                                        "PROBE_PACKAGE": str(src_root / subject["package"])})
    problems["S2"] += copy_problems(subject, checks, blocks, probe_copy, True)
    probe = load_json(probe_out) if probe_out.exists() else {"records": [], "outcomes": {}}
    if not probe_out.exists():
        problems["S3"].append("the probe run wrote no record")

    def records_of(test: str) -> list[dict]:
        return [r for r in probe["records"] if r["test"] == test]

    rows = []
    for case in CASES:
        orig_recs = records_of(case["original_test"])
        at = [r for r in orig_recs if r["index"] == case["original_index"]]
        orig_row, p = judge_record(at[0] if len(at) == 1 else None, lines, case["expected_class"],
                                   case["deciding"], case["original_where"])
        orig_row["index"] = case["original_index"]
        orig_row["block"] = case["original_block"]
        orig_row["test_outcome"] = probe["outcomes"].get(case["original_test"])
        problems["S3"] += [f"{case['original_block']}: {x}" for x in p]
        var_recs = records_of(case["variant_test"])
        var_row, p = judge_record(var_recs[0] if len(var_recs) == 1 else None, lines, case["expected_class"],
                                  case["target"], None)
        if len(var_recs) != 1:
            p.append(f"{len(var_recs)} executions recorded, expected 1")
        var_row["test"] = case["variant_test"]
        var_row["test_outcome"] = probe["outcomes"].get(case["variant_test"])
        if var_row["test_outcome"] != "passed":
            p.append(f"the variant test {var_row['test_outcome'] or 'did not run'}")
        problems["S4"] += [f"{case['variant_test']}: {x}" for x in p]
        rows.append({"original": orig_row, "variant": var_row, "target": case["target"],
                     "deciding_check_of_the_original": case["deciding"],
                     "original_pass": orig_row["test_outcome"] == "passed",
                     "variant_pass": var_row["test_outcome"] == "passed"})

    # 2. whole suite with and without the variants
    suite_paths = [p for run in subject["suite_runs"] for p in run["paths"]]
    whole = {}
    for name, with_variants in (("with_variants", True), ("without_variants", False)):
        dest = fresh_dir(work, f"copy-whole-{name}")
        root = dest / "root"
        root.mkdir()
        make_copy(subject, clone, root, with_variants)
        problems["S2"] += copy_problems(subject, checks, blocks, root, with_variants)
        junit = dest / "junit.xml"
        outcomes_file = dest / "outcomes.json"
        call = pytest_call(python, subject, root, suite_paths + ([VARIANT_DIR] if with_variants else []), [],
                           [GUARD], work / "logs" / f"whole-{name}.log", dest / "offline.json",
                           extra_env={"OUTCOMES_OUT": str(outcomes_file)},
                           extra_args=[f"--junitxml={junit}"])
        problems["S2"] += copy_problems(subject, checks, blocks, root, with_variants)
        seen = load_json(outcomes_file) if outcomes_file.exists() else None
        results = junit_outcomes(junit, root) if junit.exists() else {}
        whole[name] = {"call": call, "results": results, "seen": seen}
    w, wo = whole["with_variants"], whole["without_variants"]
    passing_w = {t for t, s in w["results"].items() if s == "passed"}
    passing_wo = {t for t, s in wo["results"].items() if s == "passed"}
    variant_ids = {c["variant_test"] for c in CASES}
    if w["call"]["returncode"] != 0:
        problems["S5"].append(f"whole suite with variants exited with {w['call']['returncode']}")
    if w["seen"] is None or w["seen"]["failed_tests"] or w["seen"]["failed_collectors"]:
        problems["S5"].append("whole suite with variants: failed tests or collectors, or no outcome file")
    bad = sorted(t for t, s in w["results"].items() if s in ("failed", "error"))
    if bad:
        problems["S5"].append(f"failed or erroneous tests with variants: {bad[:5]}")
    if not w["results"] or passing_w != passing_wo | variant_ids:
        problems["S5"].append(
            f"passing with variants minus passing without: {sorted(passing_w - passing_wo)}; "
            f"passing without that do not pass with: {sorted(passing_wo - passing_w)}")
    if wo["call"]["returncode"] != 0:
        problems["S5"].append(f"whole suite without variants exited with {wo['call']['returncode']}")

    # S6
    calls = {"probe": probe_call, "whole_with_variants": w["call"], "whole_without_variants": wo["call"]}
    for name, call in calls.items():
        if call["refused_attempts"] != 0:
            problems["S6"].append(f"{name}: refused attempts {call['refused_attempts']}")

    # 3. recorder run
    recorder = None
    if args.no_recorder:
        problems["S7"] = []
    else:
        recorder, p = recorder_section(subject, checks, blocks, clone, python, work, rows)
        problems["S7"] += p

    def count(results, status):
        return sum(1 for s in results.values() if s == status)

    out = {
        "subject": {"name": subject["name"], "version": subject["version"], "commit": subject["commit"],
                    "clone_head": head, "interpreter": interpreter,
                    "toolkit_verify_returncode": tool_verify.returncode},
        "definitions": {"checks": published(SUBJECT_DIR / "checks.json"),
                        "blocks": published(SUBJECT_DIR / "blocks.json"),
                        "offline_module": published(GUARD / "reach_offline.py")},
        "environment": {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8",
                        "LC_ALL": "C.UTF-8", "pytest_args": subject.get("pytest_args", [])},
        "raise_site_rule": "innermost frame of the traceback of the exception that reached assertRaises; "
                           "its file relative to the source root and its line, looked up in the line "
                           "ranges of the checks",
        "cases": rows,
        "probe_run": {k: probe_call[k] for k in ("returncode", "summary", "refused_attempts")},
        "whole_suite": {
            name: {"returncode": whole[name]["call"]["returncode"],
                   "summary": whole[name]["call"]["summary"],
                   "refused_attempts": whole[name]["call"]["refused_attempts"],
                   "tests": len(whole[name]["results"]),
                   "passed": count(whole[name]["results"], "passed"),
                   "failed": count(whole[name]["results"], "failed"),
                   "error": count(whole[name]["results"], "error"),
                   "skipped": count(whole[name]["results"], "skipped")}
            for name in whole},
        "whole_suite_passing_added_by_variants": sorted(passing_w - passing_wo),
        "whole_suite_passing_lost_with_variants": sorted(passing_wo - passing_w),
        "recorder": recorder,
        "sentinels": {k: {"statement": SENTINELS[k],
                          "held": not problems[k] if not (k == "S7" and args.no_recorder) else None,
                          "problems": problems[k]}
                      for k in SENTINELS},
    }
    dump(Path(args.out), out)
    failed = [k for k, v in out["sentinels"].items() if v["held"] is False]
    for case in rows:
        print(f"{case['original']['block']}: {case['original'].get('check')} | "
              f"{case['variant']['test'].split('::')[-1]}: {case['variant'].get('check')} "
              f"({case['variant'].get('test_outcome')})")
    print("whole suite:", {n: out["whole_suite"][n]["summary"] for n in whole})
    print("sentinels:", {k: v["held"] for k, v in out["sentinels"].items()})
    if failed:
        print("sentinels that do not hold:", failed, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
