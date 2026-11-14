"""Unit tests of nested_header.py on small synthetic packages.

    PYTHON -I -B -m pytest -q -p no:cacheprovider test_nested_header.py

with an interpreter that has pytest.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("nested_header", HERE / "nested_header.py")
nh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nh)


def api_jws(tmp_path: Path, replace: dict | None = None) -> Path:
    """A synthetic jwt/api_jws.py whose lines 372, 374 and 377 hold the statements of LINES."""
    lines = [f"# filler {i}" for i in range(1, 400)]
    for number, statement in {**nh.LINES, **(replace or {})}.items():
        lines[number - 1] = "        " + statement
    path = tmp_path / "api_jws.py"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_sites_hold(tmp_path):
    assert nh.site_problems(api_jws(tmp_path)) == []


def test_site_moved_is_reported(tmp_path):
    problems = nh.site_problems(api_jws(tmp_path, {377: "pass"}))
    assert len(problems) == 1 and problems[0].startswith("S2: line 377")


def test_short_file_is_reported(tmp_path):
    path = tmp_path / "api_jws.py"
    path.write_text("x = 1\n", encoding="utf-8")
    assert len(nh.site_problems(path)) == 3


@pytest.mark.parametrize("text, expected", [
    (".                                                                        [100%]\n1 passed in 0.02s\n", "passed"),
    ("F\n=== 1 failed in 0.10s ===\n", "failed"),
    ("1 passed, 1 warning in 0.02s\n", None),
    ("2 passed in 0.02s\n", None),
    ("no tests ran in 0.01s\n", None),
    ("1 error in 0.01s\n", None),
    ("", None),
])
def test_summary(text, expected):
    assert nh.summary(text) == expected


def test_guard_is_found():
    assert (nh.GUARD / "reach_offline.py").is_file()


def run_synthetic(tmp_path: Path, body: str) -> tuple[str, dict | None]:
    """Runs 1 synthetic test with the script's pytest arguments and environment."""
    pkg = tmp_path / "pkg"
    (pkg / "tests").mkdir(parents=True)
    (pkg / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "tests" / "test_one.py").write_text(body, encoding="utf-8")
    offline = tmp_path / "offline.json"
    run = subprocess.run([sys.executable, *nh.PYTEST, "tests/test_one.py"], cwd=pkg,
                         env=nh.env(nh.GUARD, offline), capture_output=True, text=True)
    doc = json.loads(offline.read_text(encoding="utf-8")) if offline.exists() else None
    return nh.summary(run.stdout), doc


def test_guard_counts_an_outside_connection(tmp_path):
    outcome, doc = run_synthetic(tmp_path, (
        "import socket\n"
        "def test_connect():\n"
        "    s = socket.socket()\n"
        "    try:\n"
        "        s.connect(('192.0.2.1', 9))\n"
        "    except OSError:\n"
        "        pass\n"
        "    finally:\n"
        "        s.close()\n"))
    assert outcome == "passed"
    assert doc is not None and doc["attempts"] == 1


def test_guard_counts_zero_without_connection(tmp_path):
    outcome, doc = run_synthetic(tmp_path, "def test_nothing():\n    assert 1 + 1 == 2\n")
    assert outcome == "passed"
    assert doc == {"attempts": 0, "first": [], "tests": {}}


def test_failing_synthetic_test_is_failed(tmp_path):
    outcome, doc = run_synthetic(tmp_path, "def test_no():\n    assert False\n")
    assert outcome == "failed" and doc["attempts"] == 0


def test_wrong_commit_stops(tmp_path, monkeypatch, capsys):
    class Done:
        stdout = "0" * 40 + "\n"
    monkeypatch.setattr(nh.subprocess, "run", lambda *a, **k: Done())
    monkeypatch.setattr(nh.sys, "argv", ["nested_header.py", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        nh.main()
    assert str(exc.value).startswith("S1: clone at " + "0" * 40)
    assert capsys.readouterr().out == ""

