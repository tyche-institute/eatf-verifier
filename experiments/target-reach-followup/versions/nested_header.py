#!/usr/bin/env python3
"""Where PyJWT 2.15.1 rejects the token of its nested-header test, by Python version.

Adapted from ../../mutation-adequacy-pyjwt/version-check/nested_header.py
(called "the earlier script" below). The decode call, the token, the two
variants, the copy of `jwt/`, `tests/` and `pyproject.toml`, the commit check
and the output keys are those of the earlier script. The differences:

1. The pytest call loads the offline guard of the toolkit, as
   ../../target-reach/reach/run.py does: the folder
   ../../target-reach/guard is put on PYTHONPATH and pytest gets
   `-p reach_offline`; the guard writes its count of refused outside
   connections to a file named by OFFLINE_OUT.
2. The environment of the pytest call is that of run.py: PATH starts with
   the folder of the interpreter, HOME is inherited (the earlier script set
   HOME=/tmp and PATH=/usr/bin:/bin).
3. The `pytest` object of each row has one more key, `offline_refused`, the
   number of refused attempts. Every other key and value format is unchanged.
4. Sentinels. After all rows are printed, the program exits with status 1
   when one of these does not hold, and names it on standard error:
   S1  the clone is at COMMIT (the earlier script also refuses to run);
   S2  in each copy, the lines of SITES and the line of the `json.loads` call
       hold the expected statements, so that a line number names the check;
   S3  `jwt` is imported from the copy (the earlier script also checks it);
   S4  the variant edit replaces exactly 1 except clause;
   S5  each pytest call reports exactly 1 test, passed or failed, and no error;
   S6  each pytest call ends with the guard's file written and 0 refused
       attempts;
   S7  the pytest outcome agrees with the direct decode: passed exactly when
       `assertion_holds` is true;
   S8  when --expect VERSION is given, the interpreter's version is VERSION.
   S1, S3 and S4 stop the program at once, as in the earlier script.

    python3 -I -B nested_header.py PYJWT_CLONE [--expect VERSION]

prints one JSON object per variant, one per line.
"""
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

COMMIT = "7d5ef55e42ce42221f58dc49943e92ccad1fa66a"   # PyJWT 2.15.1
RELEASED = "        except (ValueError, RecursionError) as e:\n"
BEFORE_FIX = "        except ValueError as e:\n"
SITES = {374: "jws.header-json", 377: "jws.header-object"}   # checks.json of the earlier study, lines at COMMIT
# The statement expected on each line of jwt/api_jws.py at COMMIT (sentinel S2).
LINES = {372: 'header: dict[str, Any] = json.loads(header_data)',
         374: 'raise DecodeError(f"Invalid header string: {e}") from e',
         377: 'raise DecodeError("Invalid header string: must be a json object")'}
TEST = "tests/test_api_jws.py::TestJWS::test_decode_deeply_nested_header_throws_decode_error"
PYTEST = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:randomly",
          "-p", "reach_offline", "--rootdir=.", "--tb=native"]
GUARD = Path(__file__).resolve().parents[2] / "target-reach" / "guard"


def env(guard: Path, offline: Path) -> dict:
    """The environment of the pytest call, as in run.py's Context.env."""
    return {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
            "HOME": os.environ.get("HOME", "/tmp"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(guard), "OFFLINE_OUT": str(offline)}


def site_problems(api_jws: Path) -> list:
    """Sentinel S2: the lines named by LINES hold the expected statements."""
    lines = api_jws.read_text(encoding="utf-8").splitlines()
    out = []
    for number, statement in sorted(LINES.items()):
        found = lines[number - 1].strip() if number <= len(lines) else None
        if found != statement:
            out.append(f"S2: line {number} of {api_jws.name} is {found!r}, expected {statement!r}")
    return out


def summary(text: str) -> str | None:
    """Sentinel S5: 'passed' or 'failed' when the pytest output reports exactly
    1 test with that outcome and no other outcome; otherwise None."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    last = lines[-1].strip().strip("=").strip()
    last = re.sub(r"\s+in\s+[\d.]+s(\s+\([^)]*\))?$", "", last)
    if last == "1 passed":
        return "passed"
    if last == "1 failed":
        return "failed"
    return None


def observe(copy: Path, variant: str) -> dict:
    sys.path.insert(0, str(copy))
    import jwt                                   # noqa: E402  (the copy, checked below)
    from jwt.api_jws import PyJWS
    from jwt.exceptions import DecodeError
    from jwt.utils import base64url_encode
    if not Path(jwt.__file__).resolve().is_relative_to(copy.resolve()):
        raise SystemExit(f"S3: jwt imported from {jwt.__file__}, not from the copy")

    # As in the test, tests/test_api_jws.py lines 634-645 at COMMIT.
    nested_header = b"[" * 1000 + b"]" * 1000
    example_jws = ".".join(
        (
            base64url_encode(nested_header).decode(),
            "eyJoZWxsbyI6ICJ3b3JsZCJ9",
            "tvagLDLoaiJKxOKqpBXSEGy7SYSifZhjntgm9ctpyj8",
        )
    )

    try:
        json_loads = f"parses, to a {type(json.loads(nested_header)).__name__}"
    except RecursionError:
        json_loads = "RecursionError"

    out = {"python": platform.python_version(), "implementation": platform.python_implementation(),
           "variant": variant, "json_c_scanner": json.scanner.c_make_scanner is not None,
           "recursion_limit": sys.getrecursionlimit(), "json_loads": json_loads}
    try:
        PyJWS().decode(example_jws, "secret", algorithms=["HS256"])
        out.update(exception=None, raise_site=None, check=None, assertion_holds=False)
    except Exception as e:                       # noqa: BLE001  (every outcome is recorded)
        frames = [f for f in traceback.extract_tb(e.__traceback__)
                  if Path(f.filename).resolve().is_relative_to(copy.resolve())]
        last = frames[-1] if frames else None
        out.update(exception=type(e).__name__, message=str(e)[:60],
                   raise_site=f"jwt/{Path(last.filename).name}:{last.lineno}" if last else None,
                   check=SITES.get(last.lineno) if last and last.filename.endswith("api_jws.py") else None,
                   assertion_holds=isinstance(e, DecodeError)
                   and re.search("Invalid header", str(e)) is not None)
    return out


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        print(json.dumps(observe(Path(sys.argv[2]), sys.argv[3])))
        return 0
    args = sys.argv[1:]
    expect = None
    if "--expect" in args:
        i = args.index("--expect")
        expect = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        raise SystemExit("usage: nested_header.py PYJWT_CLONE [--expect VERSION]")
    clone = Path(args[0]).resolve()
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    if head != COMMIT:
        raise SystemExit(f"S1: clone at {head}, not at {COMMIT}")
    if not (GUARD / "reach_offline.py").is_file():
        raise SystemExit(f"the offline guard is not at {GUARD}")
    problems = []
    if expect is not None and platform.python_version() != expect:
        problems.append(f"S8: interpreter is {platform.python_version()}, expected {expect}")
    has_pytest = importlib.util.find_spec("pytest") is not None
    for variant in ("released", "before-fix"):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "copy"
            ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
            shutil.copytree(clone / "jwt", copy / "jwt", ignore=ignore)
            shutil.copytree(clone / "tests", copy / "tests", ignore=ignore)
            shutil.copy2(clone / "pyproject.toml", copy / "pyproject.toml")
            path = copy / "jwt" / "api_jws.py"
            if variant == "before-fix":
                src = path.read_text(encoding="utf-8")
                if src.count(RELEASED) != 1:
                    raise SystemExit("S4: the JSON check's except clause is not where expected")
                path.write_text(src.replace(RELEASED, BEFORE_FIX), encoding="utf-8")
            problems += [f"{variant}: {p}" for p in site_problems(path)]
            done = subprocess.run([sys.executable, "-I", "-B", __file__, "--child", str(copy), variant],
                                  capture_output=True, text=True)
            if done.returncode:
                raise SystemExit(done.stderr)
            row = json.loads(done.stdout)
            if has_pytest:
                import pytest
                offline = Path(tmp) / "offline.json"
                run = subprocess.run([sys.executable, *PYTEST, TEST], cwd=copy, env=env(GUARD, offline),
                                     capture_output=True, text=True)
                outcome = summary(run.stdout)
                if outcome is None:
                    problems.append(f"{variant}: S5: pytest did not report exactly 1 test: "
                                    f"{run.stdout.strip().splitlines()[-1:] or run.stderr[-200:]}")
                refused = json.loads(offline.read_text(encoding="utf-8"))["attempts"] \
                    if offline.exists() else None
                if refused != 0:
                    problems.append(f"{variant}: S6: offline guard file "
                                    f"{'missing' if refused is None else f'counts {refused} refused attempts'}")
                if outcome is not None and (outcome == "passed") != (run.returncode == 0):
                    problems.append(f"{variant}: S5: pytest exit {run.returncode} with summary {outcome}")
                if outcome is not None and (outcome == "passed") != row["assertion_holds"]:
                    problems.append(f"{variant}: S7: pytest {outcome}, assertion_holds {row['assertion_holds']}")
                row["pytest"] = {"version": pytest.__version__,
                                 "test": "passed" if run.returncode == 0 else f"failed (exit {run.returncode})",
                                 "offline_refused": refused}
            else:
                row["pytest"] = None
            print(json.dumps(row), flush=True)
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
