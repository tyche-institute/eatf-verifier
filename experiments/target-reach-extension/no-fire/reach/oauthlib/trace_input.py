"""The part that the scripts 6.py to 10.py of this folder share: a fresh copy, a tracer, and the record of 1 input.

Each script <n>.py holds the input for the check in row <n> of
`../../sample.csv` (rows 6 to 10 are the 5 sampled checks of oauthlib) and
calls `main(<n>, build)`, where `build` imports from the copy and returns the
1 call of an entry point. Run it from any folder with the environment of the
first study:

    ../../../../target-reach/work/venvs/oauthlib/bin/python -I -B <n>.py

Below, T is `../../../../target-reach` (the toolkit of the first study) and X
is `../../..` (the folder of PROTOCOL.md). `main` does, in this order:

1. reads row <n> of the sample and the definition of its check in
   `T/subjects/oauthlib/checks.json` (raise statements, class, function);
2. checks the interpreter: CPython in the version of `subject.json`, from the
   environment `T/work/venvs/oauthlib`;
3. checks the clone `T/work/src/oauthlib`: at the commit of `subject.json`,
   and no changed, untracked or ignored file in the paths that a copy takes,
   with the git commands of `verify` in `T/reach/run.py` (lines 211-226), which
   change nothing (`GIT_OPTIONAL_LOCKS=0`);
4. makes a fresh copy of the release in `X/work/reach/oauthlib/copy/<n>`: the
   paths `copy` of `subject.json`, without `__pycache__`, `*.pyc` and
   `.pytest_cache`, as `make_copy` of `T/reach/run.py` makes it (lines
   310-322), and checks the SHA-256 of every subject file against
   `checks.json`, as `make_copy_check` does (lines 325-330);
5. puts the copy first on `sys.path`, imports the package from it and calls
   `build`; nothing of the package, of its dependencies or of its tests is
   changed, patched or replaced;
6. makes the 1 call of the entry point with a tracer on (`sys.monitoring`,
   Python 3.12): LINE events record every line of the package that executes
   during the call, and RAISE events every exception raised in, or passing
   through, a frame of the package. A RAISE event is a firing of the check
   under the test of `on_raise` in `T/reach/recorder.py` (lines 237-270): its
   instruction is `RAISE_VARARGS`, its line is a line of a raise statement of
   the check, and the class of the exception has the check's class name;
7. takes the exception that reaches the caller and its raise site, the
   innermost frame of its traceback inside the package directory, as `site`
   of `T/reach/recorder.py` takes it (lines 194-210), with the check whose
   raise statement holds that line;
8. writes `<n>.record.json` beside the script and prints 1 line.

The check is reached by the input when a line of 1 of its raise statements
executes during the call (`PROTOCOL.md`, section 4.4). The exit status is 0
when the check is reached and 1 when it is not; another failure stops the
script with a message and writes no record.
"""

from __future__ import annotations

import csv
import dis
import hashlib
import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
X = HERE.parents[2]
ROOT = X.parents[1]  # the root of the repository; the record gives paths relative to it
T = X.parent / "target-reach"
LIBRARY = "oauthlib"
SUBJECT = T / "subjects" / LIBRARY / "subject.json"
CHECKS = T / "subjects" / LIBRARY / "checks.json"
SAMPLE = X / "no-fire" / "sample.csv"
CLONE = T / "work" / "src" / LIBRARY
VENV = T / "work" / "venvs" / LIBRARY
WORK = X / "work" / "reach" / LIBRARY
RAISE_VARARGS = dis.opmap["RAISE_VARARGS"]
LEFT_OUT = re.compile(r"(^|/)(__pycache__|\.pytest_cache)/|\.pyc$")  # T/reach/run.py, line 222
TOOL_IDS = (3, 4)  # ids that no standard tool claims, as in T/reach/recorder.py, line 218


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def qualname(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def from_root(path) -> str:
    """A path of the machine relative to the root of the repository, when it is inside it."""
    absolute = os.path.abspath(path)
    root = os.path.abspath(ROOT)
    return os.path.relpath(absolute, root) if absolute.startswith(root + os.sep) else absolute


def sample_row(row: int) -> dict:
    with SAMPLE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not 1 <= row <= len(rows) or rows[row - 1]["library"] != LIBRARY:
        raise SystemExit(f"row {row} of {SAMPLE} is no row of {LIBRARY}")
    return rows[row - 1]


def check_interpreter(subject: dict) -> dict:
    found = {"executable": from_root(sys.executable), "prefix": from_root(sys.prefix),
             "implementation": platform.python_implementation(), "version": platform.python_version(),
             "isolated": bool(sys.flags.isolated), "dont_write_bytecode": bool(sys.dont_write_bytecode),
             # -I ignores every PYTHON* variable, PYTHONHASHSEED among them: string hashing is randomized
             "hash_randomization": bool(sys.flags.hash_randomization),
             # the names of the variables of the process (their values aside) and the locale
             "environment_variables": sorted(os.environ),
             "locale": {name: os.environ.get(name) for name in ("LANG", "LC_ALL")}}
    if (Path(sys.prefix).resolve() != VENV.resolve() or found["implementation"] != "CPython"
            or found["version"] != subject["python"]):
        raise SystemExit(f"run this script with {VENV}/bin/python, CPython {subject['python']}; found {found}")
    return found


def check_clone(subject: dict) -> dict:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    head = subprocess.run(["git", "-C", str(CLONE), "rev-parse", "HEAD"],
                          capture_output=True, text=True, env=env).stdout.strip()
    status = subprocess.run(["git", "-C", str(CLONE), "status", "--porcelain", "--untracked-files=all",
                             "--ignored", "--", *subject["copy"]], capture_output=True, text=True, env=env)
    extra = [line for line in status.stdout.splitlines() if line.strip() and not LEFT_OUT.search(line[3:])]
    if head != subject["commit"] or status.returncode != 0 or extra:
        raise SystemExit(f"the clone {CLONE} is at {head or '?'}, not {subject['commit']}, "
                         f"or its copied paths hold other files: {extra[:5]} {status.stderr.strip()[:200]}")
    return {"path": from_root(CLONE), "head": head, "copied_paths_clean": True}


def fresh_copy(row: int, subject: dict, checks: dict) -> Path:
    if subject.get("source_root", ".") not in (".", ""):
        raise SystemExit("this helper takes a subject whose source root is the clone root")
    dest = WORK / "copy" / str(row)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in subject["copy"]:
        src = CLONE / item
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=ignore)
        else:
            (dest / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / item)
    differ = [rel for rel, digest in checks["sha256"].items() if sha256(dest / rel) != digest]
    if differ:
        raise SystemExit(f"copy {dest}: {differ[:5]} differ from {CHECKS}")
    return dest


class Tracer:
    """The LINE and RAISE events of the package during 1 call."""

    def __init__(self, src_root: Path, package: str, check: dict, checks: dict) -> None:
        self.src_root = os.path.realpath(src_root)
        self.pkg_dir = os.path.realpath(os.path.join(self.src_root, *package.split(".")))
        self.check = check
        self.at_line: dict[tuple[str, int], str] = {}
        for c in checks["checks"]:
            for (a, z) in c["lines"]:
                for line in range(a, z + 1):
                    self.at_line.setdefault((c["file"], line), c["id"])
        self.files: dict[str, str | None] = {}
        self.lines: dict[str, dict[str, set[int]]] = {}
        self.raises: list[dict] = []
        self.tool: int | None = None

    def rel(self, filename: str) -> str | None:
        """The path of a file of the package relative to the source root; None outside it."""
        if filename not in self.files:
            path = os.path.realpath(filename)
            self.files[filename] = (os.path.relpath(path, self.src_root).replace(os.sep, "/")
                                    if path.startswith(self.pkg_dir + os.sep) else None)
        return self.files[filename]

    def on_line(self, code, line: int):
        rel = self.rel(code.co_filename)
        if rel is None:
            return sys.monitoring.DISABLE
        self.lines.setdefault(rel, {}).setdefault(code.co_qualname, set()).add(line)
        return None

    def on_raise(self, code, offset: int, exception: BaseException):
        rel = self.rel(code.co_filename)
        if rel is None:
            return None
        frame = sys._getframe(1)
        line = frame.f_lineno if frame.f_code is code else None
        op = code.co_code[offset]  # the bytecode without instrumentation; `offset` is in bytes
        check = self.at_line.get((rel, line)) if line is not None else None
        self.raises.append({
            "file": rel, "function": code.co_qualname, "line": line, "instruction": dis.opname[op],
            "exception": qualname(type(exception)), "check_at_line": check,
            "firing_of_the_check": (check == self.check["id"] and op == RAISE_VARARGS
                                    and type(exception).__name__ == self.check["class_name"]),
        })
        return None

    def start(self) -> None:
        mon = sys.monitoring
        for tool in TOOL_IDS:
            try:
                mon.use_tool_id(tool, "reach-reading")
            except ValueError:
                continue
            self.tool = tool
            break
        if self.tool is None:
            raise SystemExit("no free sys.monitoring tool id")
        mon.register_callback(self.tool, mon.events.LINE, self.on_line)
        mon.register_callback(self.tool, mon.events.RAISE, self.on_raise)
        mon.set_events(self.tool, mon.events.LINE | mon.events.RAISE)

    def stop(self) -> None:
        mon = sys.monitoring
        mon.set_events(self.tool, 0)
        mon.register_callback(self.tool, mon.events.LINE, None)
        mon.register_callback(self.tool, mon.events.RAISE, None)
        mon.free_tool_id(self.tool)


def raise_site(exc: BaseException, tracer: Tracer) -> tuple[list[dict], dict | None]:
    """The frames of the traceback, and the innermost of them inside the package."""
    frames, inner = [], None
    tb = exc.__traceback__
    while tb is not None:
        code = tb.tb_frame.f_code
        rel = tracer.rel(code.co_filename)
        entry = {"file": rel if rel is not None else f"{Path(code.co_filename).name} (outside the package)",
                 "function": code.co_qualname, "line": tb.tb_lineno}
        frames.append(entry)
        if rel is not None:
            inner = dict(entry, check=tracer.at_line.get((rel, tb.tb_lineno)))
        tb = tb.tb_next
    return frames, inner


def main(row: int, build: Callable[[], dict]) -> int:
    started = utc()
    subject, checks = load(SUBJECT), load(CHECKS)
    drawn = sample_row(row)
    check = next((c for c in checks["checks"] if c["id"] == drawn["check"]), None)
    if check is None or check["file"] != drawn["file"] or check["function"] != drawn["function"]:
        raise SystemExit(f"row {row}: {drawn['check']} is not in {CHECKS} as the sample has it")
    interpreter = check_interpreter(subject)
    clone = check_clone(subject)
    copy = fresh_copy(row, subject, checks)

    sys.path.insert(0, str(copy))
    package = importlib.import_module(subject["package"])
    if not os.path.realpath(package.__file__).startswith(os.path.realpath(copy) + os.sep):
        raise SystemExit(f"{subject['package']} was imported from {package.__file__}, not from {copy}")
    spec = build()
    method = spec["entry_point"]
    func = getattr(method, "__func__", method)
    if func.__name__ not in subject["entry_points"]:
        raise SystemExit(f"{func.__qualname__} has no name of an entry point of {SUBJECT}")
    tracer = Tracer(copy, subject["package"], check, checks)
    entry_file = tracer.rel(func.__code__.co_filename)
    if entry_file is None:
        raise SystemExit(f"{func.__qualname__} is no function of the copy")

    call_started = utc()
    tracer.start()
    try:
        value, caught = spec["call"](), None
    except BaseException as exc:  # noqa: BLE001 - the record keeps what reaches the caller
        value, caught = None, exc
    finally:
        tracer.stop()
    call_ended = utc()

    raise_lines = [line for (a, z) in check["lines"] for line in range(a, z + 1)]
    in_function = tracer.lines.get(check["file"], {}).get(check["function"], set())
    executed = [line for line in raise_lines if line in in_function]
    source = (copy / check["file"]).read_text(encoding="utf-8").splitlines()
    exception = None
    if caught is not None:
        frames, site = raise_site(caught, tracer)
        exception = {"class": qualname(type(caught)), "error": getattr(caught, "error", None),
                     "description": getattr(caught, "description", None),
                     "status_code": getattr(caught, "status_code", None), "message": str(caught)[:500],
                     "raise_site": site, "traceback": frames}
    validator = spec.get("validator")
    record = {
        "library": LIBRARY,
        "row": row,
        "check": check["id"],
        "check_definition": {
            "file": check["file"], "function": check["function"], "class": check["class"],
            "class_name": check["class_name"], "template": check["template"],
            "raise_statements": check["lines"],
            "raise_source": {str(line): source[line - 1].strip() for line in raise_lines},
            "file_sha256_in_copy": sha256(copy / check["file"]),
        },
        "entry_point": {
            "name": func.__name__, "qualname": func.__qualname__, "file": entry_file,
            "line": func.__code__.co_firstlineno,
            "called_on": qualname(type(method.__self__)) if hasattr(method, "__self__") else None,
        },
        "input": spec["input"],
        "settings": spec["settings"],
        "facts": spec.get("facts", {}),
        "validator_calls": getattr(validator, "calls", None) if validator is not None else None,
        "interpreter": interpreter,
        "clone": clone,
        "copy": {"path": from_root(copy), "paths": subject["copy"], "subject_files_checked": len(checks["sha256"]),
                 "package_imported_from": from_root(os.path.realpath(package.__file__))},
        "times": {"started": started, "call_started": call_started, "call_ended": call_ended, "ended": utc()},
        "outcome": "raised" if caught is not None else "returned",
        "returned": None if caught is not None else repr(value)[:300],
        "exception": exception,
        "lines_executed": {f: {fn: sorted(ls) for fn, ls in sorted(fns.items())}
                           for f, fns in sorted(tracer.lines.items())},
        "raise_events": tracer.raises,
        "raise_lines_executed": executed,
        "fired": any(r["firing_of_the_check"] for r in tracer.raises),
        "decides": bool(exception and exception["raise_site"]
                        and exception["raise_site"]["check"] == check["id"]),
        "result": "reached" if executed else "not reached by this input",
    }
    out = HERE / f"{row}.record.json"
    out.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    site = exception["raise_site"] if exception else None
    print(f"row {row}, {check['id']}: {record['result']} (raise lines executed {executed}, fired "
          f"{record['fired']}); the call {record['outcome']}"
          + (f" {exception['class']} at {site['file']}:{site['line']}" if site else "")
          + f"; record {out.name}")
    return 0 if executed else 1
