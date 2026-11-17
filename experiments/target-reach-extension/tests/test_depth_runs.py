"""Unit tests of ../nested-depth/depth_runs.py on a synthetic package named `jwt`.

The package is written into a temporary folder; it is not PyJWT, and these
tests decode no header of the study. Its `decode` reads the nesting of the
header and, by it, raises at the line of a check (1 array), raises a
RecursionError at another line (2), returns (3), ends its own process by a
signal (4) or sleeps past the time limit (5). Each case runs the child of the
script in a fresh interpreter, as a depth run does.
"""
from __future__ import annotations

import argparse
import platform
import resource
import sys
from pathlib import Path

import pytest

from conftest import load

depth = load("x_depth_runs", "nested-depth/depth_runs.py")

API_JWS = '''\
import json
import os
import signal
import time


class DecodeError(Exception):
    pass


def nesting(value):
    n = 0
    while isinstance(value, list):
        n, value = n + 1, (value[0] if value else None)
    return n


def load(header_data):
    try:
        header = json.loads(header_data)
    except (ValueError, RecursionError) as e:
        raise DecodeError(f"Invalid header string: {e}") from e
    n = nesting(header)
    if n == 2:
        raise RecursionError("synthetic")
    if n == 3:
        return {"alg": "HS256"}
    if n == 4:
        os.kill(os.getpid(), signal.SIGKILL)
    if n == 5:
        time.sleep(60)
    if not isinstance(header, dict):
        raise DecodeError("Invalid header string: must be a json object")
    return header
'''
API_JWT = '''\
import base64

from .api_jws import load


def decode(token, key, algorithms):
    part = token.split(".")[0]
    return load(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
'''
UTILS = '''\
import base64


def base64url_encode(data):
    return base64.urlsafe_b64encode(data).replace(b"=", b"")
'''
LINES = API_JWS.splitlines()
CHECK_LINE = LINES.index('        raise DecodeError("Invalid header string: must be a json object")') + 1
OTHER_LINE = LINES.index('        raise RecursionError("synthetic")') + 1
INDEX = {("jwt/api_jws.py", CHECK_LINE): "api_jws.load#2"}
EARLIER = {("jwt/api_jws.py", CHECK_LINE): "jws.header-object"}


@pytest.fixture
def copy(tmp_path) -> Path:
    root = tmp_path / "copy"
    (root / "jwt").mkdir(parents=True)
    (root / "jwt" / "__init__.py").write_text("from .api_jwt import decode\n", encoding="utf-8")
    (root / "jwt" / "api_jws.py").write_text(API_JWS, encoding="utf-8")
    (root / "jwt" / "api_jwt.py").write_text(API_JWT, encoding="utf-8")
    (root / "jwt" / "utils.py").write_text(UTILS, encoding="utf-8")
    return root


def run(copy: Path, n: int, timeout: float = 30.0, stack_kib: int = depth.STACK_KIB):
    args = argparse.Namespace(timeout=timeout, stack_kib=stack_kib)
    return depth.one_run(Path(sys.executable), platform.python_version(), copy, "released", n, args, INDEX, EARLIER)


def settings_hold(row: dict, stack_kib: int = depth.STACK_KIB) -> None:
    assert row["implementation"] == "CPython" and row["python"] == platform.python_version()
    assert row["recursion_limit"] == 1000 and row["json_c_scanner"] is True
    assert row["stack_limit_kib"] == stack_kib and row["stack_kib_asked"] == stack_kib


def test_rejected_by_a_check(copy):
    row, problems = run(copy, 1)
    assert problems == []
    assert row["outcome"] == "rejected by a check" and row["returncode"] == 0 and row["decoded"] is False
    assert row["check"] == "api_jws.load#2" and row["check_earlier_study"] == "jws.header-object"
    assert row["raise_site"] == {"file": "jwt/api_jws.py", "line": CHECK_LINE, "function": "load", "in": "copy"}
    assert row["exception"] == "jwt.api_jws.DecodeError"
    assert row["message"] == "Invalid header string: must be a json object" and row["cause"] is None
    settings_hold(row)


def test_exception_outside_the_checks(copy):
    row, problems = run(copy, 2)
    assert problems == []
    assert row["outcome"] == "exception outside the checks" and row["check"] is None
    assert row["exception"] == "builtins.RecursionError" and row["raise_site"]["line"] == OTHER_LINE
    assert row["innermost_frame"] == row["raise_site"]


def test_accepted(copy):
    row, problems = run(copy, 3)
    assert problems == [] and row["outcome"] == "accepted" and row["decoded"] is True
    assert row["value_type"] == "dict" and row["check"] is None


def test_interpreter_failed_keeps_the_settings(copy):
    row, problems = run(copy, 4)
    assert problems == []
    assert row["outcome"] == "interpreter failed" and row["returncode"] == -9 and row["signal"] == "SIGKILL"
    assert "decoded" not in row
    settings_hold(row)


def test_timed_out_keeps_the_settings(copy):
    row, problems = run(copy, 5, timeout=3.0)
    assert problems == []
    assert row["outcome"] == "timed out" and row["returncode"] is None and row["wall_seconds"] >= 3.0
    settings_hold(row)


def test_stack_limit_0_keeps_the_callers(copy):
    soft, _hard = resource.getrlimit(resource.RLIMIT_STACK)
    row, problems = run(copy, 1, stack_kib=0)
    assert problems == [] and row["stack_kib_asked"] is None
    assert row["stack_limit_kib"] == (None if soft == resource.RLIM_INFINITY else soft // 1024)


def test_another_interpreter_version_is_a_problem(copy):
    args = argparse.Namespace(timeout=30.0, stack_kib=depth.STACK_KIB)
    row, problems = depth.one_run(Path(sys.executable), "3.0.0", copy, "released", 3, args, INDEX, EARLIER)
    assert row["outcome"] == "accepted"
    assert problems == [f"N6: {sys.executable} is CPython {platform.python_version()}, not CPython 3.0.0"]


def test_child_rows():
    settings = b'{"python": "3.12.3", "depth": 5}\nnoise\n'
    assert depth.child_rows(settings) == ({"python": "3.12.3", "depth": 5}, None)
    both = '{"python": "3.12.3"}\n{"python": "3.12.3", "decoded": false}\n'
    assert depth.child_rows(both) == ({"python": "3.12.3"}, {"python": "3.12.3", "decoded": False})
    assert depth.child_rows(None) == (None, None)


def test_signal_name():
    assert depth.signal_name(0) is None and depth.signal_name(1) is None
    assert depth.signal_name(-11) == "SIGSEGV" and depth.signal_name(-200) == "signal 200"


def write_clone(root: Path, api_jws: str) -> Path:
    (root / "jwt").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "jwt" / "api_jws.py").write_text(api_jws, encoding="utf-8")
    (root / "jwt" / "__pycache__").mkdir()
    (root / "jwt" / "__pycache__" / "api_jws.cpython-312.pyc").write_bytes(b"")
    (root / "tests" / "test_x.py").write_text("", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    return root


def test_make_copy_edits_1_clause(tmp_path):
    source = "def f():\n    try:\n        pass\n" + depth.RELEASED + "        raise\n"
    clone = write_clone(tmp_path / "clone", source)
    released = depth.make_copy(clone, tmp_path / "a", "released")
    assert released.read_text(encoding="utf-8") == source
    assert not (tmp_path / "a" / "jwt" / "__pycache__").exists() and (tmp_path / "a" / "tests" / "test_x.py").exists()
    before = depth.make_copy(clone, tmp_path / "b", "before-fix")
    assert before.read_text(encoding="utf-8") == source.replace(depth.RELEASED, depth.BEFORE_FIX)
    twice = write_clone(tmp_path / "twice", source + depth.RELEASED)
    with pytest.raises(SystemExit, match="N4"):
        depth.make_copy(twice, tmp_path / "c", "before-fix")


def test_site_problems(tmp_path):
    lines = [""] * 380
    for number, statement in depth.LINES.items():
        lines[number - 1] = "        " + statement
    path = tmp_path / "api_jws.py"
    path.write_text("\n".join(lines), encoding="utf-8")
    assert depth.site_problems(path) == []
    lines[373] = "        pass"
    path.write_text("\n".join(lines), encoding="utf-8")
    assert [p[:15] for p in depth.site_problems(path)] == ["N3: line 374 of"]
