#!/usr/bin/env python3
"""Where PyJWT 2.15.1 rejects the token of its nested-header test, by Python version.

The test `test_decode_deeply_nested_header_throws_decode_error` in
`tests/test_api_jws.py` builds a token whose header is 1000 nested JSON arrays
and expects `DecodeError` with a message matching "Invalid header". It was
added in upstream commit 0657369, which made the JSON check of `PyJWS._load`
(`jws.header-json` in ../checks.json) catch `RecursionError` as well as
`ValueError`.

On the Python that runs it, this script makes the test's decode call with the
token built as the test builds it, and reports where the library rejects it.
Where pytest is installed, it also runs the test itself, as ../run_s2.py runs
the suite. It does both twice: on PyJWT as released (variant `released`)
and on a copy whose JSON check catches `ValueError` only, as before 0657369
(variant `before-fix`). Each decode runs in its own interpreter, in a copy of
`jwt/`, `tests/` and `pyproject.toml`; the clone is never changed.

    python3 -I -B nested_header.py PYJWT_CLONE

prints one JSON object per variant, one per line.
"""
import importlib.util
import json
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
SITES = {374: "jws.header-json", 377: "jws.header-object"}   # ../checks.json, lines at COMMIT
TEST = "tests/test_api_jws.py::TestJWS::test_decode_deeply_nested_header_throws_decode_error"
PYTEST = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:randomly",
          "--rootdir=.", "--tb=native"]                       # as in ../run_s2.py
# As ../run_s2.py runs pytest: in the copy, so that `jwt` is the copy's, without -I, in this environment.
ENV = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
       "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}


def observe(copy: Path, variant: str) -> dict:
    sys.path.insert(0, str(copy))
    import jwt                                   # noqa: E402  (the copy, checked below)
    from jwt.api_jws import PyJWS
    from jwt.exceptions import DecodeError
    from jwt.utils import base64url_encode
    if not Path(jwt.__file__).resolve().is_relative_to(copy.resolve()):
        raise SystemExit(f"jwt imported from {jwt.__file__}, not from the copy")

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
    clone = Path(sys.argv[1]).resolve()
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    if head != COMMIT:
        raise SystemExit(f"clone at {head}, not at {COMMIT}")
    has_pytest = importlib.util.find_spec("pytest") is not None
    for variant in ("released", "before-fix"):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp)
            ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
            shutil.copytree(clone / "jwt", copy / "jwt", ignore=ignore)
            shutil.copytree(clone / "tests", copy / "tests", ignore=ignore)
            shutil.copy2(clone / "pyproject.toml", copy / "pyproject.toml")
            if variant == "before-fix":
                path = copy / "jwt" / "api_jws.py"
                src = path.read_text(encoding="utf-8")
                if src.count(RELEASED) != 1:
                    raise SystemExit("the JSON check's except clause is not where expected")
                path.write_text(src.replace(RELEASED, BEFORE_FIX), encoding="utf-8")
            done = subprocess.run([sys.executable, "-I", "-B", __file__, "--child", str(copy), variant],
                                  capture_output=True, text=True)
            if done.returncode:
                raise SystemExit(done.stderr)
            row = json.loads(done.stdout)
            if has_pytest:
                import pytest
                run = subprocess.run([sys.executable, *PYTEST, TEST], cwd=copy, env=ENV,
                                     capture_output=True, text=True)
                row["pytest"] = {"version": pytest.__version__,
                                 "test": "passed" if run.returncode == 0 else f"failed (exit {run.returncode})"}
            else:
                row["pytest"] = None
            print(json.dumps(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
