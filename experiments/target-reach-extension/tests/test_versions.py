"""Unit and end-to-end tests of ../screened/versions.py on synthetic metadata and the toolkit's toy package."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys

import pytest
from packaging.specifiers import SpecifierSet

from conftest import T, TOY, load

versions = load("x_versions", "screened/versions.py")
rm, study = versions.load_toolkit(T)

INTERPRETERS = ["3.9.25", "3.10.20", "3.11.15", "3.12.3", "3.13.14", "3.14.6"]
CLASSIFIERS = [f"Programming Language :: Python :: 3.{m}" for m in range(9, 14)] + [
    "Programming Language :: Python :: 3 :: Only"]


def files(version, rp, yanked=False):
    return [{"filename": f"toydep-{version}-py3-none-any.whl", "requires_python": rp, "yanked": yanked}]


TOYDEP = {"info": {"name": "toydep"},
          "releases": {"1.5": files("1.5", ">=3.8"), "1.6rc1": files("1.6rc1", None),
                       "1.9": files("1.9", ">=3.8", yanked=True), "2.0": files("2.0", ">=3.10"),
                       "0.9": files("0.9", "<3.9")}}


@pytest.mark.parametrize("spec", [">=3.9", ">=3.10", "<3.11", ">3.9", "<=3.12", "==3.9.*", "!=3.10.*",
                                  "~=3.9", "~=3.9.1", "==3.12.3", "!=3.12.3", ">=3.8, <4", ">= 3.9,!=3.11.*",
                                  "!=2.7.*, !=3.0.*, !=3.1.*, >=2.7", "==3.13", ">3.13.14", ">=3.6.0b1"])
def test_admits_agrees_with_packaging(spec):
    for version in INTERPRETERS:
        assert versions.admits(spec, version) == SpecifierSet(spec).contains(version), (spec, version)


def test_admits_ignores_what_it_cannot_read():
    assert versions.admits(None, "3.9.25") and versions.admits("", "3.9.25")
    assert versions.admits(">=3.6.*", "3.9.25") and versions.admits("python3", "3.14.6")


def test_support_rules():
    info = {"requires_python": ">=3.9", "classifiers": CLASSIFIERS}
    s = versions.support(info, "3.14.6")
    assert s["admitted_by_requires_python"] and s["listed_in_classifiers"] is False
    assert not s["both"] and s["requires-python"]
    assert versions.support(info, "3.13.14")["both"]
    bare = versions.support({"requires_python": ">=3.10"}, "3.14.6")
    assert bare["listed_in_classifiers"] is None and bare["both"]
    assert not versions.support({"requires_python": ">=3.10"}, "3.9.25")["both"]


def test_effective_pins_replace_and_list():
    projects = {"toydep": TOYDEP, "other": None}
    pins, replaced, problems = versions.effective_pins([("toydep", "2.0")], projects, "3.9.25", rm.canonical)
    assert pins == [("toydep", "1.5")] and problems == []         # 1.6rc1 is a pre-release, 1.9 is yanked
    assert replaced == [{"package": "toydep", "pinned": "2.0", "pinned_requires_python": [">=3.10"],
                         "replacement": "1.5", "replacement_requires_python": [">=3.8"]}]
    assert versions.effective_pins([("toydep", "2.0")], projects, "3.10.20", rm.canonical)[:2] == ([("toydep", "2.0")], [])
    _, _, problems = versions.effective_pins([("Other", "1.0"), ("toydep", "3.0")], projects, "3.12.3", rm.canonical)
    assert problems == ["Other: no metadata", "toydep==3.0: no file of this release in the metadata"]
    late = {"toydep": {"releases": {"2.0": files("2.0", ">=3.15")}}}
    assert versions.effective_pins([("toydep", "2.0")], late, "3.14.6", rm.canonical)[2] == [
        "toydep: no final release admits Python 3.14.6"]


SOURCE = b'''
import unittest

def helper_outside():
    pass

class Base:
    def test_inherited(self):
        pass

class A(unittest.TestCase):
    def _check(self, x):
        pass

    def _via(self):
        self._check(2)

    def test_one(self):
        self._check(1)

    def test_two(self):
        pass

    def test_three(self):
        self._via()

class B(Base, unittest.TestCase):
    pass

def test_mod(p):
    pass

def _unused():
    pass
'''


def target(function, classes=()):
    return {"block": f"t.py::{'.'.join([*classes, function])}#0", "file": "t.py", "classes": list(classes),
            "function": function, "nodeid": "::".join(["t.py", *classes, function])}


def test_resolve_node_ids_inherited_tests_and_helpers():
    collected = ["t.py::A::test_one", "t.py::A::test_two", "t.py::A::test_three", "t.py::B::test_inherited",
                 "t.py::test_mod[1]", "t.py::test_mod[2]"]
    targets = [target("_check", ["A"]), target("test_inherited", ["Base"]), target("test_mod"),
               target("_unused"), target("test_two", ["A"])]
    selection, how = versions.resolve(targets, collected, {"t.py": SOURCE})
    rules = {h["block"]: (h["rule"], h["tests"]) for h in how}
    assert rules["t.py::A._check#0"] == ("caller", ["t.py::A::test_one", "t.py::A::test_three"])
    assert rules["t.py::Base.test_inherited#0"] == ("same function name in another class", ["t.py::B::test_inherited"])
    assert rules["t.py::test_mod#0"] == ("node id", ["t.py::test_mod[1]", "t.py::test_mod[2]"])
    assert rules["t.py::_unused#0"] == ("none", [])
    assert selection == ["t.py::A::test_one", "t.py::A::test_three", "t.py::A::test_two", "t.py::B::test_inherited",
                         "t.py::test_mod"]


def test_junit_key_is_that_of_pytest():
    from _pytest.junitxml import mangle_test_address
    for nodeid in ["tests/test_a.py::test_x", "tests/sub/test_b.py::C::D::test_y[1-a b]", "t.py::test_z[x::y]"]:
        names = mangle_test_address(nodeid)
        assert versions.junit_key(nodeid) == f"{'.'.join(names[:-1])}::{names[-1]}"


def test_junit_cases(tmp_path):
    path = tmp_path / "r.xml"
    path.write_text('<testsuites><testsuite>'
                    '<testcase classname="t" name="ok"/>'
                    '<testcase classname="t" name="bad"><failure message="m"/></testcase>'
                    '<testcase classname="t" name="err"><error message="e"/></testcase>'
                    '<testcase classname="t" name="skip"><skipped/></testcase>'
                    '<testcase classname="t" name="twice"/>'
                    '<testcase classname="t" name="twice"><error message="teardown"/></testcase>'
                    '</testsuite></testsuites>', encoding="utf-8")
    assert versions.junit_cases(path) == {"t::ok": "passed", "t::bad": "failed", "t::err": "error",
                                          "t::skip": "skipped", "t::twice": "error"}


def test_collected_ids(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    text = ("tests/test_a.py::test_x\ntests/test_a.py::C::test_y[a b]\nERROR tests/test_b.py::x - boom\n"
            "nofile.py::test_z\n\n3 tests collected in 0.01s\n")
    assert versions.collected_ids(text, tmp_path) == ["tests/test_a.py::test_x", "tests/test_a.py::C::test_y[a b]"]


def write_pypi(root):
    root.mkdir(parents=True, exist_ok=True)
    info = {"info": {"name": "toyverify", "version": "0", "requires_python": ">=3.9", "classifiers": CLASSIFIERS}}
    (root / "toyverify-0.json").write_text(json.dumps(info), encoding="utf-8")
    (root / "toydep.json").write_text(json.dumps(TOYDEP), encoding="utf-8")
    return root


def test_dry_plan(tmp_path, subjects_copy, capsys):
    (subjects_copy / "toy" / "requirements.txt").write_text("toydep==2.0\n", encoding="utf-8")
    pypi = write_pypi(tmp_path / "pypi")
    code = versions.main(["--dry", "--libraries", "toy", "--subjects", str(subjects_copy), "--pypi", str(pypi),
                          "--clone", f"toy={TOY}", "--work", str(tmp_path / "work"), "--out", str(tmp_path / "out")])
    assert code == 0
    plans = {p["python"]: p for p in (json.loads(x) for x in capsys.readouterr().out.splitlines() if x.startswith("{"))}
    assert list(plans) == INTERPRETERS
    assert not plans["3.14.6"]["planned"] and all(plans[v]["planned"] for v in INTERPRETERS[:5])
    assert plans["3.9.25"]["pins"] == ["toydep==1.5"] and plans["3.10.20"]["pins"] == ["toydep==2.0"]
    assert "recorder" in plans["3.12.3"] and "recorder" in plans["3.13.14"] and "recorder" not in plans["3.11.15"]
    p = plans["3.12.3"]
    assert p["collect"]["cmd"][-2:] == ["tests", "--collect-only"]
    assert p["suite"]["cmd"][-1].startswith("--junitxml=") and p["suite"]["cmd"][-2] == p["block_node_ids"][-1]
    assert p["recorder"]["base-1"]["cmd"][-len(p["block_node_ids"]):] == p["block_node_ids"]
    assert not (tmp_path / "out").exists() and not (tmp_path / "pypi" / "fetched.jsonl").exists()
    assert not (tmp_path / "work" / "toy" / "env-3.12.3").exists()


class FakeRun:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, *args, **kwargs):
        self.calls.append({"cmd": cmd, "cwd": str(kwargs.get("cwd")), "env": kwargs.get("env")})
        return subprocess.CompletedProcess(cmd, 0, "", "")


def test_dry_environments_are_those_of_the_toolkit(tmp_path, toy_subjects, monkeypatch):
    ctx = versions.make_context(rm, toy_subjects / "toy" / "subject.json", tmp_path / "work", TOY,
                                tmp_path / "env" / "bin" / "python")
    fake = FakeRun()
    proxy = type("P", (), {"run": staticmethod(fake), "TimeoutExpired": subprocess.TimeoutExpired})()
    monkeypatch.setattr(rm, "subprocess", proxy)
    with pytest.raises(SystemExit, match="did not reach its end"):
        rm.suite(ctx)
    rm.recorder_run(ctx, "base-1", tmp_path / "copy", ctx.records / "base-1.json", 60)
    suite_call, recorder_call = fake.calls
    assert suite_call == {"cmd": rm.pytest_command(ctx, False), "cwd": str(ctx.copies / "suite"),
                          "env": versions.suite_env(rm, ctx, ctx.copies / "suite")}
    assert recorder_call == {"cmd": rm.pytest_command(ctx, True), "cwd": str(tmp_path / "copy"),
                             "env": versions.recorder_env(rm, ctx, tmp_path / "copy", "base-1")}


@pytest.mark.parametrize("select", ["functions", "files"])
def test_run_on_the_toy(tmp_path, toy_subjects, select):
    pypi = write_pypi(tmp_path / "pypi")
    out = tmp_path / "out"
    code = versions.main(["--libraries", "toy", "--interpreters", "3.12.3", "--env", f"3.12.3={sys.executable}",
                          "--subjects", str(toy_subjects), "--pypi", str(pypi), "--no-fetch", "--select", select,
                          "--clone", f"toy={TOY}", "--work", str(tmp_path / "work"), "--out", str(out)])
    assert code == 0
    doc = json.loads((out / "toy.json").read_text(encoding="utf-8"))
    r = doc["interpreters"]["3.12.3"]
    assert doc["clone_problems"] == [] and r["environment_problems"] == [] and r.get("error") is None
    assert r["unresolved_blocks"] == [] and r["negative_tests"]
    assert set(r["outcomes"].values()) <= {"passed", "failed", "error", "skipped"}
    assert set(r["negative_tests"]) <= set(r["outcomes"])
    if select == "files":
        assert r["selection"] == ["tests"]
        assert len(r["outcomes"]) == r["collect"]["collected"]
    checks = {c["id"] for c in rm.load_json(toy_subjects / "toy" / "checks.json")["checks"]}
    cases = r["cases"]["base-1"]
    assert cases and r["base_runs_differ"] == []
    assert {c["check"] for c in cases.values()} <= checks | {None}
    assert all(c["test"] in r["outcomes"] for c in cases.values())
    with (out / "interpreters.csv").open(newline="", encoding="utf-8") as handle:
        row, = list(csv.DictReader(handle))
    assert row["python"] == "3.12.3" and row["error"] == "" and int(row["cases_base_1"]) == len(cases)
    assert not (tmp_path / "work" / "toy" / "py-3.12.3" / "copies").exists()
    main = versions.main_baseline(study, tmp_path / "generated", "toy")
    assert main["error"] == "no such file" and doc["main_baseline"]["error"] == "no such file"
    assert row["cases_differ_from_main_baseline"] == ""
    record = rm.load_json(tmp_path / "work" / "toy" / "py-3.12.3" / "records" / "base-1.json")
    pack(tmp_path / "generated" / "toy" / "records.tar.xz", record)
    main = versions.main_baseline(study, tmp_path / "generated", "toy")
    assert main["case_count"] == len(cases) and main["cases"] == cases
    versions.compare(doc["interpreters"], main)
    assert r["cases_differ_from_main_baseline"] == {}
    key = sorted(cases)[0]
    for case in record["cases"]:
        if study.case_key(case) == key:
            case["site"] = dict(case.get("site") or {}, check="another#1")
    pack(tmp_path / "generated" / "toy" / "records.tar.xz", record)
    versions.compare(doc["interpreters"], versions.main_baseline(study, tmp_path / "generated", "toy"))
    assert r["cases_differ_from_main_baseline"] == {key: [cases[key]["check"], "another#1"]}


def pack(path, record) -> None:
    """A records.tar.xz that holds records/base-1.json, as the toolkit's `pack` writes it."""
    import io
    import tarfile
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(record).encode("utf-8")
    with tarfile.open(path, "w:xz") as tar:
        info = tarfile.TarInfo("records/base-1.json")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


def test_checks_differ():
    a = {"t|b|0": {"check": "x#1"}, "t|b|1": {"check": None}, "t|c|0": {"check": "y#1"}}
    b = {"t|b|0": {"check": "x#1"}, "t|b|1": {"check": "z#1"}, "t|d|0": {"check": None}}
    assert versions.checks_differ(a, b) == {"t|b|1": [None, "z#1"], "t|c|0": ["y#1", None], "t|d|0": [None, None]}


def test_a_work_folder_in_a_git_repository_is_refused(tmp_path):
    from conftest import X
    assert versions.git_holder(X / "work" / "no-such-folder") is not None
    assert versions.git_holder(tmp_path / "a" / "b") is None
    with pytest.raises(SystemExit, match="held by the git repository"):
        versions.main(["--libraries", "toy", "--work", str(X / "work" / "no-such-folder")])
    assert not (X / "work" / "no-such-folder").exists()


# The pins of ../work/tests-venv, the environment of these tests (README.md, "Tests of the scripts").
SWEEP_PINS = "pytest==9.2.0\niniconfig==2.3.1\npackaging==26.3\npluggy==1.7.0\nPygments==2.21.0\n"


@pytest.mark.skipif(os.environ.get("SWEEP_TOY") != "1",
                    reason="SWEEP_TOY=1 runs it: uv environments on the 6 interpreters, metadata from PyPI")
def test_sweep_of_the_toy_on_6_interpreters(tmp_path, subjects_copy):
    """The sweep with the options of the protocol on the toy: environments made by uv from wheels on
    the 6 interpreters of ../work/pythons and /usr/bin/python3.12, the metadata of the pins fetched
    from PyPI, recorder runs on 3.12 and later."""
    (subjects_copy / "toy" / "requirements.txt").write_text(SWEEP_PINS, encoding="utf-8")
    pypi = tmp_path / "pypi"
    pypi.mkdir()
    info = {"info": {"name": "toyverify", "version": "0", "requires_python": ">=3.9", "classifiers": CLASSIFIERS}}
    (pypi / "toyverify-0.json").write_text(json.dumps(info), encoding="utf-8")
    out = tmp_path / "out"
    code = versions.main(["--libraries", "toy", "--support", "requires-python", "--only-binary",
                          "--subjects", str(subjects_copy), "--pypi", str(pypi), "--clone", f"toy={TOY}",
                          "--work", str(tmp_path / "work"), "--out", str(out),
                          "--generated", str(tmp_path / "generated")])
    doc = json.loads((out / "toy.json").read_text(encoding="utf-8"))
    runs = doc["interpreters"]                                  # NAME.json sorts its keys
    for version in INTERPRETERS:
        r = runs[version]
        print(version, json.dumps({"error": r.get("error"), "replacements": r.get("replacements"),
                                   "added": r.get("added"), "summary": (r.get("suite") or {}).get("summary"),
                                   "cases": {k: len(v) for k, v in (r.get("cases") or {}).items()}}))
    assert {v: r.get("error") for v, r in runs.items() if r.get("error")} == {} and code == 0
    assert sorted(runs) == sorted(INTERPRETERS) and all(r["planned"] for r in runs.values())
    assert "pytest" in {x["package"] for x in runs["3.9.25"]["replacements"]}
    assert runs["3.12.3"]["replacements"] == [] and runs["3.12.3"]["environment_problems"] == []
    for version in INTERPRETERS[:3]:
        assert "cases" not in runs[version]
    for version in INTERPRETERS[3:]:
        assert runs[version]["cases"]["base-1"] and runs[version]["base_runs_differ"] == []
    for version in INTERPRETERS[4:]:
        assert runs[version]["cases_differ_from_control"] == {}
    for version in INTERPRETERS[:3] + INTERPRETERS[4:]:
        assert runs[version]["outcomes_differ_from_control"] == {}
    assert sorted(p.name for p in pypi.iterdir()) == sorted(
        ["fetched.jsonl", "toyverify-0.json", "pytest.json", "iniconfig.json", "packaging.json", "pluggy.json",
         "pygments.json"])
