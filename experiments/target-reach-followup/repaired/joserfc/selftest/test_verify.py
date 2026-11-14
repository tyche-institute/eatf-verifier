"""Unit and end-to-end tests of verify.py on small synthetic packages.

    <env with pytest>/bin/python -B -m pytest -q -p no:cacheprovider \
        --basetemp=work/repaired/selftest-tmp repaired/joserfc/selftest
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

import verify

TOY = {
    "src/toy/__init__.py": """\
        class ToyError(Exception):
            pass


        def size_check(value):
            if len(value) > 4:
                raise ToyError("too long")


        def item_check(value):
            if "x" in value:
                raise ToyError(
                    "no x"
                )


        def verify_value(value, callback=None):
            size_check(value)
            item_check(value)
            if callback is not None:
                callback(value)
            return value
        """,
    "tests/test_toy.py": """\
        from unittest import TestCase

        from toy import ToyError, verify_value


        def _helper(value):
            raise ToyError("from the test")


        class TestToy(TestCase):
            def test_two_blocks(self):
                self.assertRaises(ToyError, verify_value, "abcdefx")
                with self.assertRaises(ToyError):
                    verify_value("ax")

            def test_outside(self):
                self.assertRaises(ToyError, verify_value, "a", _helper)

            def test_not_raised(self):
                self.assertRaises(ToyError, verify_value, "a")
        """,
}

TOY_CHECKS = {"checks": [
    {"id": "size_check#1", "file": "toy/__init__.py", "lines": [[7, 7]]},
    {"id": "item_check#1", "file": "toy/__init__.py", "lines": [[12, 14]]},
]}


def make_toy(root: Path) -> None:
    for rel, text in TOY.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding="utf-8")


def run_probe(tmp_path: Path) -> dict:
    root = tmp_path / "root"
    make_toy(root)
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "repaired_probe.py").write_text(verify.PROBE.lstrip(), encoding="utf-8")
    out = tmp_path / "probe.json"
    subject = {"pytest_args": ["-p", "no:cacheprovider"], "source_root": "src"}
    call = verify.pytest_call(Path(sys.executable), subject, root, ["tests"], ["repaired_probe"],
                              [verify.GUARD, plugin], tmp_path / "probe.log", tmp_path / "offline.json",
                              extra_env={"PROBE_OUT": str(out), "PROBE_ROOT": str(root),
                                         "PROBE_SOURCE_ROOT": str(root / "src"),
                                         "PROBE_PACKAGE": str(root / "src" / "toy")})
    doc = json.loads(out.read_text(encoding="utf-8"))
    doc["call"] = call
    return doc


def test_check_lines_and_site():
    lines = verify.check_lines(TOY_CHECKS)
    assert lines["toy/__init__.py"][13] == "item_check#1"
    assert verify.site_check(lines, {"file": "toy/__init__.py", "line": 7, "inside_package": True}) \
        == "size_check#1"
    assert verify.site_check(lines, {"file": "toy/__init__.py", "line": 8, "inside_package": True}) is None
    assert verify.site_check(lines, {"file": "toy/__init__.py", "line": 7, "inside_package": False}) is None
    assert verify.site_check(lines, None) is None


def test_probe_records_each_block(tmp_path):
    doc = run_probe(tmp_path)
    assert doc["call"]["refused_attempts"] == 0
    recs = {(r["test"].split("::")[-1], r["index"]): r for r in doc["records"]}
    assert set(recs) == {("test_two_blocks", 0), ("test_two_blocks", 1), ("test_outside", 0),
                         ("test_not_raised", 0)}
    first = recs[("test_two_blocks", 0)]
    assert first["where"] == "tests/test_toy.py:12"
    assert first["class"] == "toy.ToyError"
    assert first["innermost"] == {"file": "toy/__init__.py", "function": "size_check",
                                  "inside_package": True, "line": 7}
    assert first["innermost"] == first["innermost_in_package"]
    second = recs[("test_two_blocks", 1)]
    assert second["where"] == "tests/test_toy.py:13"  # the with statement, on exit
    assert second["innermost"]["function"] == "item_check"
    assert second["innermost"]["line"] == 12
    outside = recs[("test_outside", 0)]
    assert outside["innermost"] == {"file": "tests/test_toy.py", "function": "_helper",
                                    "inside_package": False, "line": 7}
    assert outside["innermost_in_package"]["function"] == "verify_value"
    assert recs[("test_not_raised", 0)]["raised"] is False
    assert doc["outcomes"]["tests/test_toy.py::TestToy::test_two_blocks"] == "passed"
    assert doc["outcomes"]["tests/test_toy.py::TestToy::test_not_raised"] == "failed"


def test_judge_record(tmp_path):
    doc = run_probe(tmp_path)
    lines = verify.check_lines(TOY_CHECKS)
    recs = {(r["test"].split("::")[-1], r["index"]): r for r in doc["records"]}
    row, problems = verify.judge_record(recs[("test_two_blocks", 1)], lines, "toy.ToyError",
                                        "item_check#1", "tests/test_toy.py:13")
    assert problems == [] and row["check"] == "item_check#1"
    _, problems = verify.judge_record(recs[("test_two_blocks", 1)], lines, "toy.ToyError",
                                      "size_check#1", "tests/test_toy.py:14")
    assert len(problems) == 2
    _, problems = verify.judge_record(recs[("test_two_blocks", 0)], lines, "toy.OtherError",
                                      "size_check#1", None)
    assert problems == ["caught toy.ToyError, expected toy.OtherError"]
    row, problems = verify.judge_record(recs[("test_outside", 0)], lines, "toy.ToyError",
                                        "size_check#1", None)
    assert row["check"] is None
    assert any("innermost frame" in p for p in problems)
    _, problems = verify.judge_record(None, lines, "toy.ToyError", "size_check#1", None)
    assert problems == ["no execution recorded"]


def test_junit_outcomes(tmp_path):
    root = tmp_path / "root"
    (root / "tests" / "sub").mkdir(parents=True)
    (root / "tests" / "sub" / "test_a.py").write_text("", encoding="utf-8")
    xml = tmp_path / "junit.xml"
    xml.write_text(
        '<testsuites><testsuite>'
        '<testcase classname="tests.sub.test_a.TestA" name="test_ok"/>'
        '<testcase classname="tests.sub.test_a.TestA" name="test_bad"><failure message="x"/></testcase>'
        '<testcase classname="tests.sub.test_a" name="test_skip"><skipped/></testcase>'
        '<testcase classname="tests.sub.test_a.TestA" name="test_twice"/>'
        '<testcase classname="tests.sub.test_a.TestA" name="test_twice"><error/></testcase>'
        '</testsuite></testsuites>', encoding="utf-8")
    got = verify.junit_outcomes(xml, root)
    assert got == {"tests/sub/test_a.py::TestA::test_ok": "passed",
                   "tests/sub/test_a.py::TestA::test_bad": "failed",
                   "tests/sub/test_a.py::test_skip": "skipped",
                   "tests/sub/test_a.py::TestA::test_twice": "failed"}


def test_derived_subject_differs_in_5_fields():
    subject = {"name": "s", "commit": "abc", "copy": ["src", "tests"], "tests": ["tests/b.py", "tests/a.py"],
               "suite_runs": [{"name": "all", "paths": ["tests"]}], "package": "s", "python": "3.12.3"}
    derived = verify.derived_subject(subject)
    changed = {k for k in set(subject) | set(derived) if subject.get(k) != derived.get(k)}
    assert changed == {"name", "commit", "copy", "tests", "suite_runs"}
    assert "commit" not in derived
    assert derived["copy"] == ["src", "tests", "tests_repaired"]
    assert derived["suite_runs"] == [{"name": "all", "paths": ["tests", "tests_repaired"]}]
    names = [f"tests_repaired/{f.name}" for f in verify.variant_files()]
    assert len(names) == 4
    assert derived["tests"] == sorted(["tests/a.py", "tests/b.py", *names])
    assert subject["copy"] == ["src", "tests"]


def test_fresh_dir_stays_in_work(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    d = verify.fresh_dir(work, "copy-x")
    (d / "f").write_text("1", encoding="utf-8")
    d = verify.fresh_dir(work, "copy-x")
    assert list(d.iterdir()) == []
    with pytest.raises(SystemExit):
        verify.fresh_dir(work, "../outside")
    assert not (tmp_path / "outside").exists()
