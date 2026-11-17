#!/usr/bin/env python3
"""The interpreter sweep of the screened libraries: their negative tests on CPython 3.9 to 3.14.

    python3 -I -B versions.py [--dry] [--libraries NAME ...] [--interpreters VERSION ...]
                              [--interpreter VERSION=PYTHON ...] [--env VERSION=PYTHON ...]
                              [--support both|requires-python] [--select functions|files]
                              [--clone NAME=DIR ...] [--subjects DIR] [--pypi DIR] [--no-fetch]
                              [--only-binary] [--work DIR] [--out DIR] [--toolkit DIR] [--generated DIR]

Section 4.6 of ../PROTOCOL.md. For each library of --libraries (default the 7 of
its section 3.3, in rank order) and each interpreter of --interpreters (default
CPython 3.9.25, 3.10.20, 3.11.15, 3.12.3, 3.13.14 and 3.14.6) that the release
declares it supports, the script makes an environment, selects the tests that
hold the included blocks of the library's blocks.json, runs them on a fresh
copy of the release with the toolkit of ../../target-reach/ (its module
reach/run.py, imported, whose functions are called unchanged), and records
the outcome of each test and the message of each failure; on 3.12 and later it
also makes the 2 recorder runs of the toolkit's baseline and records, for each
case, the deciding check and the fired checks. The definitions of a library
(subject.json, checks.json, blocks.json, requirements.txt) are read from
--subjects/NAME/ (default subjects/ next to this file) when the script runs.

1. Support. From the metadata of the release, https://pypi.org/pypi/DIST/VERSION/json
   (DIST and VERSION of subject.json), cached as --pypi/DIST-VERSION.json:
   `info.requires_python` and the classifiers `Programming Language :: Python :: 3.N`.
   Rule `both` (default): the interpreter is admitted by Requires-Python and,
   when the release lists at least 1 such classifier, its minor version is
   listed. Rule `requires-python`: it is admitted by Requires-Python. Both
   verdicts are recorded; an interpreter that the rule excludes is listed and
   not run.
2. Environment. The pins `name==version` of requirements.txt. A pin is kept
   when at least 1 file of that release that is not yanked admits the
   interpreter (the `requires_python` of the files in
   https://pypi.org/pypi/NAME/json, cached as --pypi/NAME.json); otherwise it is
   replaced by the latest final release (the highest version with no pre-,
   dev- or local part and no epoch) that has such a file, and the replacement
   is listed. A clause of Requires-Python that cannot be read is ignored, as
   pip ignores an invalid Requires-Python. The pins go to
   --work/NAME/py-VERSION/requirements.txt; the environment --work/NAME/env-VERSION
   is made by `uv venv -p PYTHON ENV` and `uv pip install -p ENV/bin/python -r`
   that file (with --only-binary, `--only-binary :all:` too); uv resolves the
   dependencies, and every package it adds is listed. --env VERSION=PYTHON uses
   an existing environment instead. Checks: E1 every pin is installed at its
   version; E2 the library's distribution is not installed (the probe of
   `verify`, ../../target-reach/reach/run.py lines 244-257); E3 the
   interpreter reports CPython VERSION (INTERPRETER_PROBE, run.py line 264);
   E4 on the interpreter of subject.json, the environment passes
   `environment_problems` with the library's own requirements.txt (run.py
   lines 279-305).
3. Clone. Once per library: the clone (--clone NAME=DIR, default the `clone` of
   ../work/NAME/local.json) is at the commit of subject.json, its copied paths
   hold no other file, and its subject files and test files have the digests of
   checks.json and blocks.json: the checks of `verify` (run.py lines 210-235)
   without its interpreter and environment checks, which step 2 makes for each
   interpreter.
4. Selection. Each interpreter collects the tests: `pytest --collect-only` on a
   fresh copy (run.py `make_copy`, lines 310-322) with the pytest call of the
   toolkit's suite run (`pytest_command`, lines 333-345) on the test files of
   subject.json. With --select functions (default), the selection is, for each
   included block, the collected tests whose node id without its parameters is
   FILE::CLASS::FUNCTION of the block (nested classes split at "."); when none
   is, the collected tests of the file whose function has the block's function
   name (a test that a class inherits); when none is either, the collected
   tests of the file whose function calls the block's function by name,
   directly or through other functions of the file (a block in a helper
   method). The selection is passed to pytest as the sorted node ids without
   their parameters; a block that none of the 3 resolves is listed. With
   --select files, the selection is the test files of subject.json, as the
   toolkit's baseline runs them; the tests resolved as above are still flagged.
5. Run. The toolkit's `suite` (run.py lines 379-414) on a Context whose subject
   has the selection in place of `tests` (in memory only; no file changes),
   with `--junitxml` added to its pytest call. The outcome of each collected
   test is passed, failed, error or skipped, from the XML file (failed when 1 of
   its entries holds a failure, else error when 1 holds an error), or absent;
   the message is that of its first failure or error (`junit_failures`, run.py
   lines 654-664). On 3.12 and later, then, as the toolkit's `baseline` (run.py
   lines 417-431): base-1 and base-2, each a recorder run (`recorder_run`, lines
   348-372) on a fresh copy, time limit 3600 s, which deselects the tests that
   failed in the suite run; node ids of files that the suite run could not
   collect are left out of these runs. From each record, the cases of the study
   (`study_cases`, ../../target-reach/reach/study.py lines 28-31), each with the
   check at its raise site (the deciding check) and its fired checks (`firing`,
   lines 34-42).
6. Comparison. Each interpreter against the 3.12.3 run: the tests whose outcome
   differs; from 3.13 on, the cases of base-1 whose deciding check differs or that
   only 1 of the 2 runs holds. Within an interpreter, the cases whose deciding
   check differs between base-1 and base-2. The 3.12.3 run against base-1 of the
   main baseline (--generated/NAME/records.tar.xz, from `pack`), the same way.

Outputs in --out (default versions/ next to this file): NAME.json (all of the
above, by interpreter), interpreters.csv, outcomes.csv and cases.csv. Logs,
copies and records go to --work, which no git repository may hold (section 4 of
../PROTOCOL.md; the default ../work/screened-versions/ is for --dry). Exit status
1 when an interpreter that the rule admits did not give its runs.

--dry prints, for each library and interpreter, the support verdicts, the pins
and replacements (from the cached metadata only: nothing is fetched), the
commands that make the environment, the node ids of the included blocks as
blocks.json gives them (the collection resolves them at run time), and the
pytest calls and environment variables of the collection, the suite run and
the recorder runs, as the toolkit's Context builds them. It makes no
environment, copy or run.
"""
from __future__ import annotations

import argparse
import ast
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent                      # target-reach-extension/screened
EXTENSION = HERE.parent
TOOLKIT = EXTENSION.parent / "target-reach"
WORK = EXTENSION / "work" / "screened-versions"
PYTHONS = EXTENSION / "work" / "pythons"
LIBRARIES = ("paramiko", "pycryptodome", "scramp", "ecdsa", "python-jose", "supabase-auth", "service-identity")
INTERPRETERS = {
    "3.9.25": PYTHONS / "cpython-3.9.25-linux-x86_64-gnu" / "bin" / "python3.9",
    "3.10.20": PYTHONS / "cpython-3.10.20-linux-x86_64-gnu" / "bin" / "python3.10",
    "3.11.15": PYTHONS / "cpython-3.11.15-linux-x86_64-gnu" / "bin" / "python3.11",
    "3.12.3": Path("/usr/bin/python3.12"),
    "3.13.14": PYTHONS / "cpython-3.13.14-linux-x86_64-gnu" / "bin" / "python3.13",
    "3.14.6": PYTHONS / "cpython-3.14.6-linux-x86_64-gnu" / "bin" / "python3.14",
}
CONTROL = "3.12.3"
RECORDER_FROM = (3, 12)                                     # sys.monitoring
RECORDER_TIMEOUT = 3600                                      # run.py baseline, line 423
PYPI = "https://pypi.org/pypi"
MESSAGE = 300
# the probe of verify, run.py lines 244-250
DISTRIBUTION_PROBE = ("import importlib.metadata as m, importlib.util as u, sys\n"
                      "dist, module = sys.argv[1], sys.argv[2]\n"
                      "try:\n    m.distribution(dist); print('distribution installed')\n"
                      "except m.PackageNotFoundError:\n    pass\n"
                      "try:\n    found = u.find_spec(module) is not None\n"
                      "except ModuleNotFoundError:\n    found = False\n"
                      "if found:\n    print('module importable')\n")
# the probe of environment_problems, run.py lines 293-294
PACKAGES_PROBE = ("import importlib.metadata as m, json\n"
                  "print(json.dumps(sorted([d.metadata['Name'] or '', d.version] for d in m.distributions())))\n")


# -- versions and Requires-Python ---------------------------------------------------------

CLAUSE = re.compile(r"(===|==|!=|~=|<=|>=|<|>)\s*(\S+)")
FINAL = re.compile(r"(\d+(?:\.\d+)*)(?:\.post(\d+))?")


def release(text: str) -> tuple[int, ...] | None:
    m = re.match(r"\d+(?:\.\d+)*", text)
    return tuple(int(x) for x in m.group(0).split(".")) if m else None


def pad(a: tuple[int, ...], n: int) -> tuple[int, ...]:
    return a + (0,) * (n - len(a))


def admits(spec: str | None, version: str) -> bool:
    """Whether a Requires-Python specifier admits the final version `version` (X.Y.Z).
    Clauses: ==, !=, <=, >=, <, >, ~= and ===, with .* after == and !=; a clause
    that cannot be read is ignored."""
    if not spec or not spec.strip():
        return True
    have = release(version)
    for raw in spec.split(","):
        raw = raw.strip()
        if not raw:
            continue
        m = CLAUSE.fullmatch(raw)
        if m is None:
            continue
        op, target = m.groups()
        if op == "===":
            if version != target:
                return False
            continue
        star = target.endswith(".*")
        want = release(target[:-2] if star else target)
        if want is None:
            continue
        exact = re.fullmatch(r"\d+(?:\.\d+)*", target[:-2] if star else target) is not None
        n = max(len(have), len(want))
        h, w = pad(have, n), pad(want, n)
        if op in ("==", "!="):
            same = have[:len(want)] == want if star else (exact and h == w)
            if (op == "==") != same:
                return False
        elif op == "~=":
            if len(want) < 2 or h < w or have[:len(want) - 1] != want[:-1]:
                return False
        elif not {"<": h < w, "<=": h <= w, ">": h > w, ">=": h >= w}[op]:
            return False
    return True


def version_key(v: str) -> tuple:
    m = FINAL.fullmatch(v)
    rel = tuple(int(x) for x in m.group(1).split("."))
    return pad(rel, 8) + (int(m.group(2)) if m.group(2) else -1,)


def support(info: dict, version: str) -> dict:
    """The verdicts of both rules for 1 interpreter, from the `info` of the release's metadata."""
    rp = info.get("requires_python") or None
    minors = sorted({c.split("::")[-1].strip() for c in info.get("classifiers") or []
                     if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c.strip())},
                    key=lambda m: tuple(int(x) for x in m.split(".")))
    minor = ".".join(version.split(".")[:2])
    by_rp = admits(rp, version)
    listed = (minor in minors) if minors else None
    return {"requires_python": rp, "classifier_minor_versions": minors, "admitted_by_requires_python": by_rp,
            "listed_in_classifiers": listed, "both": by_rp and listed is not False, "requires-python": by_rp}


def read_pins(path: Path) -> list[tuple[str, str]]:
    """The pins `name==version` of a requirements file, as environment_problems reads them."""
    pins = []
    if not path.exists():
        return pins
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"([A-Za-z0-9._-]+)==(\S+)", line)
        if m is None:
            raise SystemExit(f"{path}: `{line}` is no pin `name==version`")
        pins.append((m.group(1), m.group(2)))
    return pins


def files_admit(files: list[dict], version: str) -> bool:
    return any(not f.get("yanked") and admits(f.get("requires_python"), version) for f in files)


def effective_pins(pins: list[tuple[str, str]], projects: dict[str, dict | None], version: str,
                   canonical) -> tuple[list[tuple[str, str]], list[dict], list[str]]:
    """The pins for 1 interpreter, the replacements and the problems (step 2)."""
    out, replaced, problems = [], [], []
    for name, pinned in pins:
        project = projects.get(canonical(name))
        if project is None:
            problems.append(f"{name}: no metadata")
            out.append((name, pinned))
            continue
        releases = project.get("releases") or {}
        files = releases.get(pinned)
        if files is None:
            same = [v for v in releases if FINAL.fullmatch(v) and FINAL.fullmatch(pinned)
                    and version_key(v) == version_key(pinned)]
            files = releases[same[0]] if same else None
        if not files:
            problems.append(f"{name}=={pinned}: no file of this release in the metadata")
            out.append((name, pinned))
            continue
        if files_admit(files, version):
            out.append((name, pinned))
            continue
        candidates = [v for v, fs in releases.items() if FINAL.fullmatch(v) and fs and files_admit(fs, version)]
        if not candidates:
            problems.append(f"{name}: no final release admits Python {version}")
            out.append((name, pinned))
            continue
        best = max(candidates, key=version_key)
        rps = sorted({str(f.get("requires_python")) for f in files if not f.get("yanked")})
        replaced.append({"package": name, "pinned": pinned, "pinned_requires_python": rps, "replacement": best,
                         "replacement_requires_python": sorted({str(f.get("requires_python"))
                                                                for f in releases[best] if not f.get("yanked")})})
        out.append((name, best))
    return out, replaced, problems


# -- metadata ------------------------------------------------------------------------------

def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def metadata(pypi: Path, canon: str, version: str | None, fetch: bool) -> tuple[dict | None, Path, str]:
    """The JSON of PyPI for a project (version None) or a release, from the cache or fetched into it."""
    path = pypi / (f"{canon}-{version}.json" if version else f"{canon}.json")
    url = f"{PYPI}/{canon}/{version}/json" if version else f"{PYPI}/{canon}/json"
    if not path.exists():
        if not fetch:
            return None, path, url
        pypi.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "versions.py", "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        with (pypi / "fetched.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"url": url, "path": path.name, "time": now(),
                                     "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}) + "\n")
    return json.loads(path.read_text(encoding="utf-8")), path, url


# -- tests and blocks ------------------------------------------------------------------------

def block_targets(blocks: dict) -> list[dict]:
    """1 entry per included block: its key, file, classes, function and the node id of its function."""
    out = []
    for b in blocks["blocks"]:
        if not b["included"]:
            continue
        classes = b["test_class"].split(".") if b.get("test_class") else []
        out.append({"block": b["key"], "file": b["file"], "classes": classes, "function": b["test"],
                    "nodeid": "::".join([b["file"], *classes, b["test"]])})
    return out


def base_id(nodeid: str) -> str:
    """A node id without its parameters."""
    return nodeid.split("[", 1)[0]


def qualname(nodeid: str) -> tuple[str, str]:
    parts = base_id(nodeid).split("::")
    return parts[0], ".".join(parts[1:])


def calls_by_function(source: bytes) -> dict[str, set[str]]:
    """Qualified name of each function of a file (Class.function) -> the names it calls
    (f(...), self.f(...), x.y.f(...)), nested functions included."""
    out: dict[str, set[str]] = {}

    def visit(node, prefix: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, prefix + [child.name])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = set()
                for n in ast.walk(child):
                    if isinstance(n, ast.Call):
                        if isinstance(n.func, ast.Name):
                            calls.add(n.func.id)
                        elif isinstance(n.func, ast.Attribute):
                            calls.add(n.func.attr)
                out[".".join(prefix + [child.name])] = calls

    visit(ast.parse(source), [])
    return out


def callers(graph: dict[str, set[str]], name: str) -> set[str]:
    """The functions of a file that call `name`, directly or through other functions of the file."""
    names, found = {name}, set()
    while True:
        new = {q for q, calls in graph.items() if q not in found and calls & names}
        if not new:
            return found
        found |= new
        names |= {q.rsplit(".", 1)[-1] for q in new}


def resolve(targets: list[dict], collected: list[str], sources: dict[str, bytes]) -> tuple[list[str], list[dict]]:
    """The selection of --select functions (step 4): sorted node ids without parameters,
    and for each block how it was resolved and to which tests."""
    by_file: dict[str, list[str]] = {}
    for nodeid in collected:
        by_file.setdefault(qualname(nodeid)[0], []).append(nodeid)
    graphs: dict[str, dict] = {}
    selection, how = set(), []
    for t in targets:
        tests = [n for n in by_file.get(t["file"], []) if base_id(n) == t["nodeid"]]
        rule = "node id"
        if not tests:
            tests = [n for n in by_file.get(t["file"], []) if qualname(n)[1].rsplit(".", 1)[-1] == t["function"]]
            rule = "same function name in another class"
        if not tests and t["file"] in sources:
            if t["file"] not in graphs:
                graphs[t["file"]] = calls_by_function(sources[t["file"]])
            found = callers(graphs[t["file"]], t["function"])
            simple = {q.rsplit(".", 1)[-1] for q in found}
            tests = [n for n in by_file.get(t["file"], []) if qualname(n)[1] in found]
            tests = tests or [n for n in by_file.get(t["file"], []) if qualname(n)[1].rsplit(".", 1)[-1] in simple]
            rule = "caller"
        if not tests:
            rule = "none"
        how.append({"block": t["block"], "nodeid": t["nodeid"], "rule": rule, "tests": sorted(tests)})
        selection |= {base_id(n) for n in tests}
    return sorted(selection), how


def collected_ids(text: str, copy: Path) -> list[str]:
    """The node ids that `pytest -q --collect-only` prints, 1 per line."""
    out = []
    for line in text.splitlines():
        line = line.rstrip()
        if "::" not in line or line.startswith(("ERROR", "FAILED", "=")):
            continue
        if (copy / line.split("::", 1)[0]).is_file():
            out.append(line)
    return out


def junit_key(nodeid: str) -> str:
    """The `classname::name` of a node id in pytest's junit XML file
    (`mangle_test_address` of _pytest/junitxml.py)."""
    path, bracket, params = nodeid.partition("[")
    names = path.split("::")
    names[0] = re.sub(r"\.py$", "", names[0].replace("/", "."))
    names[-1] += bracket + params
    return f"{'.'.join(names[:-1])}::{names[-1]}"


def junit_cases(path: Path) -> dict[str, str]:
    """classname::name -> passed, failed, error or skipped, from 1 junit XML file."""
    rank = {"passed": 0, "skipped": 1, "error": 2, "failed": 3}
    out: dict[str, str] = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        key = f"{case.get('classname')}::{case.get('name')}"
        tags = {child.tag for child in case}
        result = ("failed" if "failure" in tags else "error" if "error" in tags
                  else "skipped" if "skipped" in tags else "passed")
        if key in out and out[key] != result:
            result = max(out[key], result, key=rank.get)
        out[key] = result
    return out


# -- the toolkit ---------------------------------------------------------------------------------

def load_toolkit(toolkit: Path):
    sys.path.insert(0, str(toolkit))
    import reach.run as rm
    import reach.study as study
    expect = (toolkit / "reach" / "run.py").resolve()
    if Path(rm.__file__).resolve() != expect:
        raise SystemExit(f"the toolkit module is {rm.__file__}, not {expect}")
    return rm, study


def make_context(rm, subject_path: Path, work: Path, clone: Path, python: Path):
    return rm.Context(argparse.Namespace(subject=str(subject_path), defs=str(subject_path.parent), work=str(work),
                                         clone=str(clone), python=str(python), workers=1, out=None,
                                         witnesses=None))


class JunitCall:
    """Within `with`, the toolkit's pytest_command adds --junitxml=<.xml> while .xml is set."""

    def __init__(self, rm) -> None:
        self.rm, self.original, self.xml = rm, rm.pytest_command, None

    def __enter__(self):
        self.rm.pytest_command = self
        return self

    def __exit__(self, *exc) -> None:
        self.rm.pytest_command = self.original

    def __call__(self, ctx, recorder: bool) -> list[str]:
        cmd = self.original(ctx, recorder)
        return cmd + [f"--junitxml={self.xml}"] if self.xml else cmd


def collect_env(rm, ctx, dest: Path) -> dict:
    """The environment of the suite run, with the guard's counts written to the logs."""
    return ctx.env(PYTHONPATH=ctx.pythonpath(dest, recorder=False),
                   OFFLINE_OUT=str(ctx.logs / "collect.offline.tmp"))


def binary_sha256(path: str | Path) -> str | None:
    real = Path(path).resolve()
    return hashlib.sha256(real.read_bytes()).hexdigest() if real.is_file() else None


def suite_env(rm, ctx, dest: Path) -> dict:
    """The environment of the toolkit's suite run (run.py lines 383-391)."""
    return ctx.env(PYTHONPATH=ctx.pythonpath(dest, recorder=False),
                   OFFLINE_OUT=str(ctx.records / "suite.offline.tmp"),
                   OUTCOMES_OUT=str(ctx.records / "suite.outcomes.tmp"))


def recorder_env(rm, ctx, dest: Path, name: str) -> dict:
    """The environment of the toolkit's recorder run (run.py lines 349-353)."""
    out = ctx.records / f"{name}.json"
    return ctx.env(PYTHONPATH=ctx.pythonpath(dest, recorder=True), REACH_SUBJECT=str(ctx.subject_path),
                   REACH_CHECKS=str(ctx.checks_path), REACH_BLOCKS=str(ctx.blocks_path),
                   REACH_OUT=str(out), REACH_ROOT=str(dest), REACH_SUITE=str(ctx.records / "suite.json"),
                   OFFLINE_OUT=str(out.with_name(out.stem + ".offline.tmp")))


def clone_problems(rm, ctx) -> list[str]:
    """Step 3: the checks of verify on the clone (run.py lines 210-235)."""
    problems = []
    commit = ctx.subject.get("commit")
    if commit:
        git_env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
        head = subprocess.run(["git", "-C", str(ctx.clone), "rev-parse", "HEAD"], capture_output=True,
                              text=True, env=git_env).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(ctx.clone), "status", "--porcelain", "--untracked-files=all",
                                "--ignored", "--", *ctx.subject["copy"]], capture_output=True, text=True,
                               env=git_env)
        if head != commit:
            problems.append(f"clone is at {head or '?'}, not {commit}")
        left_out = re.compile(r"(^|/)(__pycache__|\.pytest_cache)/|\.pyc$")
        extra = [ln for ln in dirty.stdout.splitlines() if ln.strip() and not left_out.search(ln[3:])]
        if dirty.returncode != 0 or extra:
            problems.append("the copied paths of the clone hold files that are not those of the commit: "
                            f"{('; '.join(extra) or dirty.stderr.strip())[:200]}")
    checks, blocks = rm.load_json(ctx.checks_path), rm.load_json(ctx.blocks_path)
    if checks["subject"] != {k: ctx.subject[k] for k in sorted(ctx.subject)}:
        problems.append("checks.json was written from another subject.json")
    for rel, digest in checks["sha256"].items():
        if rm.sha256(ctx.clone / rm.rel_to_source(ctx.subject, rel)) != digest:
            problems.append(f"{rel}: SHA-256 differs from checks.json")
    for rel, digest in blocks["test_files_sha256"].items():
        if rm.sha256(ctx.clone / rel) != digest:
            problems.append(f"{rel}: SHA-256 differs from blocks.json")
    return problems


def installed(python: Path) -> dict[str, str] | None:
    found = subprocess.run([str(python), "-I", "-c", PACKAGES_PROBE], capture_output=True, text=True, cwd="/")
    if found.returncode != 0:
        return None
    return {name: version for name, version in json.loads(found.stdout)}


def env_problems(rm, ctx, python: Path, pins: list[tuple[str, str]], version: str,
                 own_requirements: Path) -> tuple[list[str], dict]:
    """E1 to E4 of step 2, and the packages added to the pins."""
    problems = []
    reported = subprocess.run([str(python), "-I", "-c", rm.INTERPRETER_PROBE], capture_output=True,
                              text=True).stdout.strip()
    problem = rm.interpreter_problem(reported, version)
    if problem:
        problems.append(f"E3: {problem}")
    have = installed(python)
    added = {}
    if have is None:
        problems.append("E1: the packages of the environment cannot be listed")
    else:
        canon = {rm.canonical(n): v for n, v in have.items()}
        for name, pinned in pins:
            if canon.get(rm.canonical(name)) != pinned:
                problems.append(f"E1: {name}=={pinned} pinned; installed: {canon.get(rm.canonical(name))}")
        pinned_names = {rm.canonical(n) for n, _ in pins} | {"pip"}
        added = {n: v for n, v in sorted(have.items()) if rm.canonical(n) not in pinned_names}
    first = Path(ctx.subject["subject_files"][0]).with_suffix("")
    module = ".".join(first.parts[:-1] if first.name == "__init__" else first.parts)
    found = subprocess.run([str(python), "-I", "-c", DISTRIBUTION_PROBE, ctx.subject["distribution"], module],
                           capture_output=True, text=True, cwd="/", env=ctx.env())
    if found.returncode != 0 or found.stdout.strip():
        problems.append(f"E2: {ctx.subject['distribution']} is installed in the environment "
                        f"({found.stdout.strip() or found.stderr.strip()[-200:]})")
    if version == ctx.subject.get("python") and own_requirements.exists():
        problems += [f"E4: {p}" for p in rm.environment_problems(python, own_requirements)]
    return problems, added


# -- 1 library on 1 interpreter ------------------------------------------------------------

def make_env(uv: str, interpreter: Path, env_dir: Path, requirements: Path, only_binary: bool,
             log: Path) -> tuple[list[list[str]], str | None]:
    cmds = [[uv, "venv", "--quiet", "-p", str(interpreter), str(env_dir)],
            [uv, "pip", "install", "--quiet", "-p", str(env_dir / "bin" / "python"), "-r", str(requirements),
             *(["--only-binary", ":all:"] if only_binary else [])]]
    if not read_pins(requirements):
        cmds = cmds[:1]
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as handle:
        for cmd in cmds:
            handle.write(f"$ {' '.join(cmd)}\n")
            handle.flush()
            done = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, text=True)
            if done.returncode != 0:
                return cmds, f"`{' '.join(cmd[:3])}` exited with status {done.returncode} (see {log})"
    return cmds, None


def collect(rm, ctx, dest: Path) -> tuple[list[str], int, str]:
    rm.make_copy(ctx, dest)
    ctx.logs.mkdir(parents=True, exist_ok=True)
    cmd = rm.pytest_command(ctx, False) + ["--collect-only"]
    done = subprocess.run(cmd, cwd=dest, env=collect_env(rm, ctx, dest), capture_output=True, text=True,
                          timeout=3600)
    text = done.stdout + done.stderr
    (ctx.logs / "collect.log").write_text(text, encoding="utf-8")
    ids = collected_ids(done.stdout, dest)
    shutil.rmtree(dest)
    found = rm.SUMMARY.findall(text)
    return ids, done.returncode, found[-1] if found else ""


def case_rows(study, record: dict) -> dict[str, dict]:
    out = {}
    for key, case in study.study_cases(record).items():
        site = case.get("site") or {}
        out[key] = {"test": case["test"], "block": case["block"], "index": case["index"],
                    "check": site.get("check"), "file": site.get("file"), "line": site.get("line"),
                    "class": case.get("class"), "message": str(case.get("message"))[:MESSAGE],
                    "fired": sorted(study.firing(case))}
    return out


def run_interpreter(rm, study, ctx, version: str, targets: list[dict], select: str) -> dict:
    """Steps 4 and 5 for 1 interpreter whose environment passed step 2."""
    result: dict = {}
    sources = {f: (ctx.clone / f).read_bytes() for f in {t["file"] for t in targets} if (ctx.clone / f).is_file()}
    ids, code, summary = collect(rm, ctx, ctx.copies / "collect")
    result["collect"] = {"returncode": code, "summary": summary, "collected": len(ids)}
    selection, how = resolve(targets, ids, sources)
    negative = sorted({n for h in how for n in h["tests"]})
    result["blocks"] = how
    result["unresolved_blocks"] = [h["block"] for h in how if h["rule"] == "none"]
    if select == "functions":
        tests = selection
    else:
        tests = list(ctx.subject["tests"])
    result["selection"] = tests
    if not tests:
        result["error"] = "no test selected"
        return result
    ctx.subject = dict(ctx.subject, tests=tests)                 # in memory only
    xml = ctx.records / "xml" / "suite.xml"
    xml.parent.mkdir(parents=True, exist_ok=True)
    if xml.exists():
        xml.unlink()
    with JunitCall(rm) as call:
        call.xml = xml
        try:
            rm.suite(ctx)
        except SystemExit as e:
            result["error"] = f"suite: {e}"
            return result
        call.xml = None
        suite = rm.load_json(ctx.records / "suite.json")
        result["suite"] = suite
        try:
            by_key = junit_cases(xml)
            messages = rm.junit_failures(xml, "suite", ctx.copies / "suite")
        except (OSError, ET.ParseError) as e:
            result["error"] = f"suite: no junit XML file ({e})"
            return result
        known = {junit_key(n): n for n in ids}
        chosen = set(tests)
        result["outcomes"] = {n: by_key.get(junit_key(n), "absent") for n in ids
                              if select == "files" or base_id(n) in chosen}
        result["negative_tests"] = negative
        result["messages"] = {known[k.split("|", 1)[1]]: m for k, m in messages.items()
                              if k.split("|", 1)[1] in known}
        result["junit_entries_without_node_id"] = sorted(k for k in by_key if k not in known)
        if tuple(int(x) for x in version.split(".")[:2]) < RECORDER_FROM:
            return result
        skip = set(suite.get("not_collected", []))
        kept = [t for t in tests if t.split("::", 1)[0] not in skip]
        if not kept:
            result["error"] = "no test left for the recorder runs"
            return result
        ctx.subject = dict(ctx.subject, tests=kept)
        runs = {}
        for name in ("base-1", "base-2"):
            dest = ctx.copies / name
            rm.make_copy(ctx, dest)
            entry = rm.recorder_run(ctx, name, dest, ctx.records / f"{name}.json", timeout=RECORDER_TIMEOUT)
            runs[name] = entry
            if entry["timed_out"] or not entry["record"]:
                result["error"] = f"{name}: no record"
                result["recorder_runs"] = runs
                return result
        result["recorder_runs"] = runs
        records = {name: rm.load_json(ctx.records / f"{name}.json") for name in runs}
        result["cases"] = {name: case_rows(study, r) for name, r in records.items()}
        result["deselected"] = records["base-1"].get("deselected", [])
        a, b = result["cases"]["base-1"], result["cases"]["base-2"]
        result["base_runs_differ"] = sorted(k for k in set(a) | set(b)
                                            if (a.get(k) or {}).get("check") != (b.get(k) or {}).get("check"))
    return result


def checks_differ(ca: dict, cb: dict) -> dict[str, list]:
    """The cases whose deciding check differs between 2 sets of cases, or that only 1 of them holds."""
    return {k: [(ca.get(k) or {}).get("check"), (cb.get(k) or {}).get("check")] for k in sorted(set(ca) | set(cb))
            if k not in ca or k not in cb or ca[k].get("check") != cb[k].get("check")}


def compare(results: dict[str, dict], main: dict | None = None) -> None:
    """Step 6. `main` is the main baseline of main_baseline(); its cases are set beside the control's."""
    control = results.get(CONTROL, {})
    for version, r in results.items():
        if version == CONTROL or "outcomes" not in r or "outcomes" not in control:
            continue
        a, b = control["outcomes"], r["outcomes"]
        r["outcomes_differ_from_control"] = {n: [a.get(n), b.get(n)] for n in sorted(set(a) | set(b))
                                             if a.get(n) != b.get(n)}
        if "cases" in r and "cases" in control:
            r["cases_differ_from_control"] = checks_differ(control["cases"]["base-1"], r["cases"]["base-1"])
    if main is not None and "cases" in control and "cases" in main:
        control["cases_differ_from_main_baseline"] = checks_differ(control["cases"]["base-1"], main["cases"])


def main_baseline(study, generated: Path, name: str) -> dict:
    """The cases of base-1 of the library's main baseline: records/base-1.json of
    <generated>/NAME/records.tar.xz, the file that the toolkit's `pack` writes."""
    import tarfile
    path = generated / name / "records.tar.xz"
    if not path.is_file():
        return {"source": str(path), "error": "no such file"}
    try:
        with tarfile.open(path) as tar:
            record = json.loads(tar.extractfile("records/base-1.json").read().decode("utf-8"))
    except (KeyError, tarfile.TarError, json.JSONDecodeError) as e:
        return {"source": str(path), "error": f"records/base-1.json unreadable: {e}"}
    cases = case_rows(study, record)
    return {"source": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "case_count": len(cases),
            "cases": cases}


def git_holder(path: Path) -> str | None:
    """The git folder of the repository that holds `path` (or its nearest existing parent), or None."""
    probe = path.resolve()
    while not probe.exists():
        probe = probe.parent
    done = subprocess.run(["git", "-C", str(probe), "rev-parse", "--absolute-git-dir"], capture_output=True,
                          text=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return done.stdout.strip() or str(probe) if done.returncode == 0 else None


# -- main ------------------------------------------------------------------------------------

def pairs(values: list[str] | None, what: str) -> dict[str, str]:
    out = {}
    for value in values or []:
        key, sep, path = value.partition("=")
        if not sep:
            raise SystemExit(f"{what} takes KEY=PATH, not {value!r}")
        out[key] = path
    return out


def write_tables(out: Path, docs: list[dict]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rows_i, rows_o, rows_c = [], [], []
    for doc in docs:
        for version, r in doc["interpreters"].items():
            sup = r["support"]
            rows_i.append({"library": doc["library"], "python": version,
                           "requires_python": sup["requires_python"],
                           "classifier_minor_versions": " ".join(sup["classifier_minor_versions"]),
                           "admitted_by_requires_python": sup["admitted_by_requires_python"],
                           "listed_in_classifiers": sup["listed_in_classifiers"], "run": r["planned"],
                           "replacements": "; ".join(f"{x['package']} {x['pinned']}->{x['replacement']}"
                                                     for x in r.get("replacements", [])),
                           "added": "; ".join(f"{n}=={v}" for n, v in r.get("added", {}).items()),
                           "collected": (r.get("collect") or {}).get("collected"),
                           "selected": len(r.get("selection", [])),
                           "unresolved_blocks": len(r.get("unresolved_blocks", [])),
                           "suite_returncode": (r.get("suite") or {}).get("returncode"),
                           "summary": (r.get("suite") or {}).get("summary"),
                           "cases_base_1": len((r.get("cases") or {}).get("base-1", {})) if "cases" in r else None,
                           "outcomes_differ_from_control": len(r.get("outcomes_differ_from_control", {})),
                           "cases_differ_from_control": len(r.get("cases_differ_from_control", {})),
                           "cases_differ_from_main_baseline": len(r["cases_differ_from_main_baseline"])
                           if "cases_differ_from_main_baseline" in r else None,
                           "error": r.get("error")})
            negative = set(r.get("negative_tests", []))
            for nodeid, outcome in sorted(r.get("outcomes", {}).items()):
                rows_o.append({"library": doc["library"], "python": version, "test": nodeid,
                               "negative": "yes" if nodeid in negative else "no", "outcome": outcome,
                               "message": r.get("messages", {}).get(nodeid, "")})
            main_checks = (doc.get("main_baseline") or {}).get("checks") if version == CONTROL else None
            for run, cases in sorted((r.get("cases") or {}).items()):
                for key, c in sorted(cases.items()):
                    beside = main_checks.get(key) if main_checks is not None and run == "base-1" else None
                    rows_c.append({"library": doc["library"], "python": version, "run": run, "case": key,
                                   "deciding_check": c["check"], "line": c["line"], "class": c["class"],
                                   "message": c["message"], "fired": " ".join(c["fired"]),
                                   "main_baseline_check": beside})
    for name, rows in (("interpreters.csv", rows_i), ("outcomes.csv", rows_o), ("cases.csv", rows_c)):
        if not rows:
            continue
        with (out / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--libraries", nargs="+", default=list(LIBRARIES))
    parser.add_argument("--interpreters", nargs="+", default=list(INTERPRETERS))
    parser.add_argument("--interpreter", action="append", help="VERSION=PYTHON: the base interpreter")
    parser.add_argument("--env", action="append", help="VERSION=PYTHON: an existing environment")
    parser.add_argument("--support", choices=("both", "requires-python"), default="both")
    parser.add_argument("--select", choices=("functions", "files"), default="functions")
    parser.add_argument("--clone", action="append", help="NAME=DIR")
    parser.add_argument("--subjects", default=str(HERE / "subjects"))
    parser.add_argument("--pypi", default=str(WORK / "pypi"))
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--only-binary", action="store_true")
    parser.add_argument("--work", default=str(WORK))
    parser.add_argument("--out", default=str(HERE / "versions"))
    parser.add_argument("--toolkit", default=str(TOOLKIT))
    parser.add_argument("--generated", default=str(HERE / "generated"))
    args = parser.parse_args(argv)
    if not args.dry and git_holder(Path(args.work)):
        raise SystemExit(f"--work {args.work} is held by the git repository {git_holder(Path(args.work))}: "
                         "importing some libraries from a copy runs git there (../PROTOCOL.md, section 4)")
    rm, study = load_toolkit(Path(args.toolkit).resolve())
    interpreters = {**{k: str(v) for k, v in INTERPRETERS.items()}, **pairs(args.interpreter, "--interpreter")}
    envs, clones = pairs(args.env, "--env"), pairs(args.clone, "--clone")
    subjects, work, pypi = Path(args.subjects).resolve(), Path(args.work).resolve(), Path(args.pypi).resolve()
    fetch = not (args.no_fetch or args.dry)
    uv = shutil.which("uv") or "uv"
    uv_version = None
    if not args.dry:
        uv_version = subprocess.run([uv, "--version"], capture_output=True, text=True).stdout.strip()
        print(f"uv: {uv} {uv_version}", flush=True)
    docs, failed = [], []
    for name in args.libraries:
        subject_path = subjects / name / "subject.json"
        subject = rm.load_json(subject_path)
        if name in clones:
            clone = Path(clones[name]).resolve()
        else:
            local = EXTENSION / "work" / name / "local.json"
            clone = Path(rm.load_json(local)["clone"]) if local.exists() else None
            if clone is None:
                raise SystemExit(f"{name}: no --clone and no {local}")
        targets = block_targets(rm.load_json(subjects / name / "blocks.json"))
        info, info_path, info_url = metadata(pypi, rm.canonical(subject["distribution"]), subject["version"], fetch)
        if info is None:
            print(f"{name}: no metadata of the release at {info_path} ({info_url}); nothing planned", flush=True)
            failed.append(f"{name}: no metadata of the release")
            continue
        own = subjects / name / "requirements.txt"
        pins = read_pins(own)
        projects = {}
        for pin, _ in pins:
            data, _, url = metadata(pypi, rm.canonical(pin), None, fetch)
            projects[rm.canonical(pin)] = data
        doc = {"library": name, "version": subject["version"], "commit": subject.get("commit"),
               "clone": str(clone), "support_rule": args.support, "select": args.select, "uv": uv_version,
               "release_metadata": {"path": str(info_path), "url": info_url,
                                    "sha256": hashlib.sha256(info_path.read_bytes()).hexdigest()},
               "interpreters": {}}
        lib_problems: list[str] = []
        if not args.dry:
            probe_ctx = make_context(rm, subject_path, work / name / "clone-check", clone,
                                     Path(interpreters.get(CONTROL, sys.executable)))
            lib_problems = clone_problems(rm, probe_ctx)
            doc["clone_problems"] = lib_problems
        print(f"{name} {subject['version']}: release metadata {info_path.name}; {len(pins)} pins; "
              f"{len(targets)} included blocks" + (f"; clone: {'; '.join(lib_problems)}" if lib_problems else ""),
              flush=True)
        for version in args.interpreters:
            sup = support(info["info"], version)
            r: dict = {"support": sup, "planned": bool(sup[args.support]), "interpreter": interpreters[version],
                       "interpreter_sha256": binary_sha256(interpreters[version])}
            doc["interpreters"][version] = r
            if not r["planned"]:
                print(json.dumps({"library": name, "python": version, "planned": False, "support": sup}), flush=True)
                continue
            pins_v, replaced, pin_problems = effective_pins(pins, projects, version, rm.canonical)
            r.update(pins=[f"{n}=={v}" for n, v in pins_v], replacements=replaced, pin_problems=pin_problems)
            base = work / name / f"py-{version}"
            env_dir = work / name / f"env-{version}"
            python = Path(envs[version]).absolute() if version in envs else env_dir / "bin" / "python"
            r["environment"] = str(python)
            ctx = make_context(rm, subject_path, base, clone, python)
            if args.dry:
                collect_cmd = rm.pytest_command(ctx, False) + ["--collect-only"]   # the test files of subject.json
                tests = sorted({t["nodeid"] for t in targets}) if args.select == "functions" else ctx.subject["tests"]
                ctx.subject = dict(ctx.subject, tests=tests)                     # in memory only
                cmds = ([] if version in envs else
                        [[uv, "venv", "--quiet", "-p", interpreters[version], str(env_dir)],
                         [uv, "pip", "install", "--quiet", "-p", str(python), "-r", str(base / "requirements.txt"),
                          *(["--only-binary", ":all:"] if args.only_binary else [])]])
                plan = {"library": name, "python": version, "planned": True, "support": sup,
                        "interpreter": interpreters[version], "pins": r["pins"], "replacements": replaced,
                        "pin_problems": pin_problems, "environment_commands": cmds,
                        "block_node_ids": sorted({t["nodeid"] for t in targets}),
                        "collect": {"cmd": collect_cmd,
                                    "cwd": str(ctx.copies / "collect"),
                                    "env": collect_env(rm, ctx, ctx.copies / "collect")},
                        "suite": {"cmd": rm.pytest_command(ctx, False) +
                                  [f"--junitxml={ctx.records / 'xml' / 'suite.xml'}"],
                                  "cwd": str(ctx.copies / "suite"), "env": suite_env(rm, ctx, ctx.copies / "suite")}}
                if tuple(int(x) for x in version.split(".")[:2]) >= RECORDER_FROM:
                    plan["recorder"] = {n: {"cmd": rm.pytest_command(ctx, True), "cwd": str(ctx.copies / n),
                                            "env": recorder_env(rm, ctx, ctx.copies / n, n),
                                            "timeout": RECORDER_TIMEOUT} for n in ("base-1", "base-2")}
                print(json.dumps(plan), flush=True)
                continue
            if lib_problems:
                r["error"] = "clone: " + "; ".join(lib_problems)
                failed.append(f"{name} {version}: {r['error']}")
                continue
            if pin_problems:
                r["error"] = "pins: " + "; ".join(pin_problems)
                failed.append(f"{name} {version}: {r['error']}")
                continue
            base.mkdir(parents=True, exist_ok=True)
            reqs = base / "requirements.txt"
            reqs.write_text("".join(f"{n}=={v}\n" for n, v in pins_v), encoding="utf-8")
            if version not in envs and not python.exists():
                cmds, error = make_env(uv, Path(interpreters[version]), env_dir, reqs, args.only_binary,
                                       base / "logs" / "environment.log")
                r["environment_commands"] = cmds
                if error:
                    r["error"] = f"environment: {error}"
                    failed.append(f"{name} {version}: {r['error']}")
                    continue
            problems, added = env_problems(rm, ctx, python, pins_v, version, own)
            r["added"], r["environment_problems"] = added, problems
            if problems:
                r["error"] = "environment: " + "; ".join(problems)
                failed.append(f"{name} {version}: {r['error']}")
                continue
            for old in (ctx.records, ctx.copies):
                if old.exists():
                    shutil.rmtree(old)
            r.update(run_interpreter(rm, study, ctx, version, targets, args.select))
            shutil.rmtree(ctx.copies, ignore_errors=True)             # the records and logs stay
            if r.get("error"):
                failed.append(f"{name} {version}: {r['error']}")
            print(json.dumps({"library": name, "python": version, "error": r.get("error"),
                              "summary": (r.get("suite") or {}).get("summary"),
                              "cases": {k: len(v) for k, v in (r.get("cases") or {}).items()}}), flush=True)
        if not args.dry:
            baseline = main_baseline(study, Path(args.generated).resolve(), name)
            compare(doc["interpreters"], baseline)
            doc["main_baseline"] = {k: v for k, v in baseline.items() if k != "cases"}
            if "cases" in baseline:
                doc["main_baseline"]["checks"] = {k: c["check"] for k, c in baseline["cases"].items()}
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        docs.append(doc)
    if not args.dry and docs:
        write_tables(Path(args.out), docs)
    for line in failed:
        print(line, file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
