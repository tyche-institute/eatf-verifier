"""Tests of the recorder plugin on small packages built under tmp_path.

Each test writes a package `vb` and a test package `tt`, derives checks.json and
blocks.json with the static modules, runs the subject's tests under pytest with
`-p reach.recorder` (the interpreter that runs this file) and reads the record.
The tests about pytest's own behaviour (subtests, phases, deselection) are meant
to pass under every pytest version the toolkit supports.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from reach.blocks import enumerate_blocks
from reach.checks import enumerate_checks

E = Path(__file__).resolve().parents[1]

CORE = '''
class Bad(ValueError):
    pass


class Worse(Bad):
    pass


def describe(x):
    if x == "loop":
        raise Bad("cannot describe")
    return repr(x)


def verify(token):
    if not isinstance(token, str):
        raise Bad("token must be a string")
    if token == "inner":
        raise Bad(describe("loop"))
    if token == "multi":
        raise Bad(
            "multi " + describe("loop"))
    if token == "from":
        try:
            int(token)
        except ValueError as err:
            raise Bad("not a number") from err
    if token == "named":
        e = Worse("named")
        raise e
    if token == "split":
        raise Bad(
            "split over lines"
        )
    if token == "builtin":
        raise ValueError("plain value error")
    return token
'''


def run_recorder(tmp_path: Path, tests: dict[str, str], args: tuple = (), paths: tuple = ("tt",),
                 patch_checks=None, core: str = CORE, ini: str = "[pytest]\n"):
    """Runs the tests in `tests` (file name -> source) with the recorder; returns
    (the pytest process, the record, checks.json)."""
    (tmp_path / "vb").mkdir()
    (tmp_path / "vb" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "vb" / "core.py").write_text(core, encoding="utf-8")
    (tmp_path / "tt").mkdir()
    (tmp_path / "tt" / "__init__.py").write_text("", encoding="utf-8")
    for name, source in tests.items():
        (tmp_path / "tt" / name).write_text(textwrap.dedent(source), encoding="utf-8")
    (tmp_path / "pytest.ini").write_text(ini, encoding="utf-8")
    subject = {"name": "vb", "package": "vb", "source_root": ".", "subject_files": ["vb/core.py"],
               "observed_files": [], "entry_points": ["verify"], "rejection_bases": ["ValueError"],
               "tests": ["tt"]}
    checks = enumerate_checks(subject, tmp_path)
    blocks = enumerate_blocks(subject, tmp_path, checks)
    if patch_checks is not None:
        patch_checks(checks)
    defs = tmp_path / "defs"
    defs.mkdir()
    for name, doc in (("subject", subject), ("checks", checks), ("blocks", blocks)):
        (defs / f"{name}.json").write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "record.json"
    env = {"PATH": f"{Path(sys.executable).parent}{os.pathsep}/usr/bin{os.pathsep}/bin",
           "HOME": os.environ.get("HOME", str(tmp_path)), "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": f"{E}{os.pathsep}{tmp_path}", "REACH_SUBJECT": str(defs / "subject.json"),
           "REACH_CHECKS": str(defs / "checks.json"), "REACH_BLOCKS": str(defs / "blocks.json"),
           "REACH_OUT": str(out), "REACH_ROOT": str(tmp_path)}
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir=.",
                           "-rA", "-p", "reach.recorder", *args, *paths],
                          cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
    assert out.exists(), proc.stdout + proc.stderr
    return proc, json.loads(out.read_text(encoding="utf-8")), checks


def check_id(checks: dict, function: str, template: str) -> str:
    found = [c["id"] for c in checks["checks"] if c["function"] == function and c["template"] == template]
    assert len(found) == 1, (function, template, [(c["function"], c["template"]) for c in checks["checks"]])
    return found[0]


def node_entries(record: dict) -> dict[str, dict]:
    return {t["nodeid"]: t for t in record["tests"]}


def cases_of(record: dict, test: str) -> list[dict]:
    return [c for c in record["cases"] if c["test"] == test]


# -- subtests -------------------------------------------------------------------------

SUBTESTS = '''
import unittest

import pytest

from vb.core import Bad, verify


class TestUnit(unittest.TestCase):
    def test_subtest_fails_first(self):
        with self.subTest("fails"):
            self.assertEqual(1, 2)
        with self.subTest("passes"):
            pass

    def test_subtest_fails_last(self):
        with self.subTest("passes"):
            pass
        with self.subTest("fails"):
            self.assertEqual(1, 2)

    def test_block_in_subtest(self):
        for value in (1, 2):
            with self.subTest(value=value):
                with self.assertRaises(Bad):
                    verify(value)

    def test_subtest_crashes_then_another_asserts(self):
        with self.subTest("crashes"):
            {}["k"]
        with self.subTest("asserts"):
            self.assertEqual(1, 2)


def test_fixture_subtest_fails(subtests):
    with subtests.test("fails"):
        assert 1 == 2
    with subtests.test("passes"):
        pass


def test_fixture_subtest_crashes(subtests):
    with subtests.test("crashes"):
        {}["k"]


def test_fixture_subtests_pass_then_test_fails(subtests):
    with subtests.test("passes"):
        pass
    assert 1 == 2


def test_fixture_block_in_subtest(subtests):
    for value in (1, 2):
        with subtests.test(value=value):
            with pytest.raises(Bad):
                verify(value)


@pytest.fixture
def checked_at_teardown(subtests):
    yield
    with subtests.test("at teardown"):
        assert 1 == 2


def test_subtest_in_fixture_teardown(checked_at_teardown):
    pass
'''


def test_subtests_keep_the_test_reports(tmp_path):
    proc, record, _ = run_recorder(tmp_path, {"test_sub.py": SUBTESTS})
    t = node_entries(record)
    unit = "tt/test_sub.py::TestUnit::"

    def phase(nodeid, when):
        return t[nodeid][when]

    # a failed unittest subtest: the test's own call report passes (pytest counts the
    # test as passed and the subtest as failed); the record counts the failed subtest
    for name in ("test_subtest_fails_first", "test_subtest_fails_last"):
        assert phase(unit + name, "call") == {"outcome": "passed", "stop": None, "stop_is_assertion": None}
        assert t[unit + name]["subtests_failed"] == 1
    # the subtests fixture: pytest turns the test's own call report into "failed"
    name = "tt/test_sub.py::test_fixture_subtest_fails"
    assert phase(name, "call") == {"outcome": "failed", "stop": None, "stop_is_assertion": None}
    assert t[name]["subtests_failed"] == 1
    name = "tt/test_sub.py::test_fixture_subtests_pass_then_test_fails"
    assert phase(name, "call") == {"outcome": "failed", "stop": "builtins.AssertionError",
                                   "stop_is_assertion": True}
    assert t[name]["subtests_failed"] == 0
    # a subtest reported after the test's call (in a fixture's teardown) does not
    # replace the call entry
    name = "tt/test_sub.py::test_subtest_in_fixture_teardown"
    assert phase(name, "call") == {"outcome": "passed", "stop": None, "stop_is_assertion": None}
    assert phase(name, "teardown")["outcome"] == "passed"
    assert t[name]["subtests_failed"] == 1
    # a block inside a subtest is a normal case
    for name in (unit + "test_block_in_subtest", "tt/test_sub.py::test_fixture_block_in_subtest"):
        cs = cases_of(record, name)
        assert [(c["index"], c["check_result"], c["raised"], c["depth"]) for c in cs] == [
            (0, "accepted", True, 1), (1, "accepted", True, 1)], name
        assert t[name]["subtests_failed"] == 0
        assert phase(name, "call")["outcome"] == "passed"
    for entry in t.values():
        assert set(entry) >= {"setup", "call", "teardown", "subtests_failed"}, entry
    # what stopped each failed subtest, in the order of the reports
    asserted = {"stop": "builtins.AssertionError", "stop_is_assertion": True}
    crashed = {"stop": "builtins.KeyError", "stop_is_assertion": False}
    stops = {k.split("::")[-1]: v.get("subtest_stops") for k, v in t.items()}
    assert stops == {
        "test_subtest_fails_first": [asserted],
        "test_subtest_fails_last": [asserted],
        "test_block_in_subtest": None,
        "test_subtest_crashes_then_another_asserts": [crashed, asserted],
        "test_fixture_subtest_fails": [asserted],
        "test_fixture_subtest_crashes": [crashed],
        "test_fixture_subtests_pass_then_test_fails": None,
        "test_fixture_block_in_subtest": None,
        "test_subtest_in_fixture_teardown": [asserted],
    }
    assert t[unit + "test_subtest_crashes_then_another_asserts"]["subtests_failed"] == 2


# -- a firing is a RAISE_VARARGS --------------------------------------------------------

PASS_THROUGH = '''
import pytest

from vb.core import Bad, verify


@pytest.mark.parametrize("token", [1, "inner", "multi", "from", "named", "split"])
def test_fires(token):
    with pytest.raises(Bad):
        verify(token)
'''


def test_pass_through_is_not_a_firing(tmp_path):
    proc, record, checks = run_recorder(tmp_path, {"test_pass.py": PASS_THROUGH})
    describe = check_id(checks, "describe", "cannot describe")
    own = {
        "1": check_id(checks, "verify", "token must be a string"),
        "from": check_id(checks, "verify", "not a number"),
        "named": check_id(checks, "verify", "named"),
        "split": check_id(checks, "verify", "split over lines"),
    }
    fired = {c["test"].split("[")[1].rstrip("]"): c["fired"] for c in record["cases"]}
    # the exception of `describe` passes through the raise statement of the check
    # in `verify` (its arguments, on 1 line or on the 2nd line): that check did not fire
    assert fired["inner"] == [describe]
    assert fired["multi"] == [describe]
    # raise X(...), raise X(...) from e, raise name and a multi-line raise X(...) count
    for token, cid in own.items():
        assert fired[token] == [cid], token
    for c in record["cases"]:
        assert c["fired_other_threads"] == [] and c["depth"] == 1


# -- threads ----------------------------------------------------------------------------

THREADS = '''
import threading

import pytest

from vb.core import Bad, verify


def call(token):
    try:
        verify(token)
    except Bad:
        pass


def in_thread(token):
    t = threading.Thread(target=call, args=(token,))
    t.start()
    t.join()


def test_other_thread_only():
    with pytest.raises(Bad):
        in_thread(1)
        verify("split")


def test_both_threads():
    with pytest.raises(Bad):
        in_thread("split")
        verify("split")


def test_same_thread():
    with pytest.raises(Bad):
        verify(1)


def block_in_thread():
    def work():
        with pytest.raises(Bad):
            verify(1)
    t = threading.Thread(target=work)
    t.start()
    t.join()


def test_block_in_another_thread():
    with pytest.raises(Bad):
        block_in_thread()
        verify("split")
'''


def test_firings_in_other_threads(tmp_path):
    proc, record, checks = run_recorder(tmp_path, {"test_threads.py": THREADS})
    first = check_id(checks, "verify", "token must be a string")
    split = check_id(checks, "verify", "split over lines")
    seen = {c["test"].split("::")[1]: (c["fired"], c["fired_other_threads"]) for c in record["cases"]
            if c["test"].split("::")[1] != "test_block_in_another_thread"}
    assert seen == {"test_other_thread_only": ([first, split], [first]),
                    "test_both_threads": ([split], []),
                    "test_same_thread": ([first], [])}
    # a block entered in another thread while a block is open: neither is nested in
    # its own thread, and the firing inside the other thread counts in both
    both = sorted((c["where"], c["depth"], c["fired"], c["fired_other_threads"])
                  for c in record["cases"] + record["unmatched"]
                  if c.get("test", "").endswith("test_block_in_another_thread"))
    assert [b[1:] for b in both] == [(1, [first], []), (1, [first, split], [first])], both


# -- nested blocks ----------------------------------------------------------------------

NESTED = '''
import pytest

from vb.core import Bad, verify


def test_nested():
    with pytest.raises(Bad):
        with pytest.raises(Bad):
            verify(1)
'''


def test_nested_blocks_have_a_depth(tmp_path):
    proc, record, checks = run_recorder(tmp_path, {"test_nested.py": NESTED})
    first = check_id(checks, "verify", "token must be a string")
    cs = {c["block"].split("::")[1]: c for c in record["cases"]}
    outer, inner = cs["test_nested#0"], cs["test_nested#1"]
    assert (inner["depth"], inner["raised"], inner["check_result"], inner["fired"]) == (2, True, "accepted", [first])
    # the inner block swallows the exception: the outer block sees none and fails,
    # although the check fired while it was open
    assert (outer["depth"], outer["raised"], outer["check_result"], outer["fired"]) == (1, False, "failed", [first])
    assert [f["block"] for f in node_entries(record)["tt/test_nested.py::test_nested"]["failed_blocks"]] == [
        outer["block"]]


# -- tests collected again through an import --------------------------------------------

DEFINING = '''
import unittest

import pytest

from vb.core import Bad, verify


class TestUnit(unittest.TestCase):
    def test_unit(self):
        with self.assertRaises(Bad):
            verify(1)


class TestPlain:
    def test_plain(self):
        with pytest.raises(Bad):
            verify(1)


def test_function():
    with pytest.raises(Bad):
        verify(1)
'''

IMPORTING = '''
from tt.test_a import TestPlain, TestUnit, test_function


class TestSub(TestUnit):
    pass
'''


def test_tests_collected_again_are_deselected(tmp_path):
    proc, record, _ = run_recorder(tmp_path, {"test_a.py": DEFINING, "test_b.py": IMPORTING})
    assert record["collected_again"] == [
        {"nodeid": "tt/test_b.py::TestPlain::test_plain", "defined_in": "tt.test_a"},
        {"nodeid": "tt/test_b.py::TestUnit::test_unit", "defined_in": "tt.test_a"},
        {"nodeid": "tt/test_b.py::test_function", "defined_in": "tt.test_a"}]
    # the defining module's tests run 1 time; the subclass of the importing module runs
    assert sorted(node_entries(record)) == ["tt/test_a.py::TestPlain::test_plain", "tt/test_a.py::TestUnit::test_unit",
                                        "tt/test_a.py::test_function", "tt/test_b.py::TestSub::test_unit"]
    assert sorted(c["test"] for c in record["cases"]) == sorted(node_entries(record))
    assert record["imported_kept"] == []
    assert "4 passed, 3 deselected" in proc.stdout, proc.stdout


def test_tests_stay_when_the_defining_module_is_not_collected(tmp_path):
    proc, record, _ = run_recorder(tmp_path, {"test_a.py": DEFINING, "test_b.py": IMPORTING},
                                   paths=("tt/test_b.py",))
    assert record["collected_again"] == []
    assert sorted(node_entries(record)) == ["tt/test_b.py::TestPlain::test_plain", "tt/test_b.py::TestSub::test_unit",
                                        "tt/test_b.py::TestUnit::test_unit", "tt/test_b.py::test_function"]
    # the copies that stay are listed; the subclass of the importing module is no copy
    assert record["imported_kept"] == [
        {"nodeid": "tt/test_b.py::TestPlain::test_plain", "defined_in": "tt.test_a"},
        {"nodeid": "tt/test_b.py::TestUnit::test_unit", "defined_in": "tt.test_a"},
        {"nodeid": "tt/test_b.py::test_function", "defined_in": "tt.test_a"}]
    assert "4 passed" in proc.stdout and "deselected" not in proc.stdout, proc.stdout


DEFINING_TWO = '''
import pytest

from vb.core import Bad, verify


class TestPlain:
    def test_one(self):
        with pytest.raises(Bad):
            verify(1)

    def test_two(self):
        with pytest.raises(Bad):
            verify(1)


@pytest.mark.parametrize("value", [1, 2])
def test_function(value):
    with pytest.raises(Bad):
        verify(value)
'''

IMPORTING_TWO = '''
from tt.test_a import TestPlain, test_function
'''


def test_a_copy_stays_when_its_test_is_deselected_in_the_defining_module(tmp_path):
    proc, record, _ = run_recorder(tmp_path, {"test_a.py": DEFINING_TWO, "test_b.py": IMPORTING_TWO},
                                   args=("--deselect", "tt/test_a.py::TestPlain::test_two",
                                         "--deselect", "tt/test_a.py::test_function[2]"))
    # a copy is deselected test by test, not class by class
    assert record["collected_again"] == [
        {"nodeid": "tt/test_b.py::TestPlain::test_one", "defined_in": "tt.test_a"},
        {"nodeid": "tt/test_b.py::test_function[1]", "defined_in": "tt.test_a"}]
    assert record["imported_kept"] == [
        {"nodeid": "tt/test_b.py::TestPlain::test_two", "defined_in": "tt.test_a"},
        {"nodeid": "tt/test_b.py::test_function[2]", "defined_in": "tt.test_a"}]
    # every test runs 1 time: in the defining module or, when it is deselected there, as the copy
    assert sorted(node_entries(record)) == [
        "tt/test_a.py::TestPlain::test_one", "tt/test_a.py::test_function[1]",
        "tt/test_b.py::TestPlain::test_two", "tt/test_b.py::test_function[2]"]
    assert "4 passed, 4 deselected" in proc.stdout, proc.stdout


# -- rejection classes by identity ------------------------------------------------------

IDENTITY = '''
import pytest

from vb.core import Bad, verify


class ValueError(Exception):  # a class with a rejection base's name, of the test module
    pass


def test_package_class():
    with pytest.raises(Bad):
        verify(1)


def test_builtin_class():
    with pytest.raises(Exception):
        verify("builtin")


def test_local_class():
    with pytest.raises(Exception):
        raise ValueError("local")
'''


def rejection_by_test(record: dict) -> dict[str, bool]:
    return {c["test"].split("::")[1]: c["rejection"] for c in record["cases"] + record["unmatched"]
            if c.get("raised")}


def test_rejection_by_name_without_the_key(tmp_path):
    proc, record, _ = run_recorder(tmp_path, {"test_id.py": IDENTITY})
    assert rejection_by_test(record) == {"test_package_class": True, "test_builtin_class": True,
                                         "test_local_class": False}


def test_rejection_by_module_and_qualname(tmp_path):
    def patch(checks):
        checks["rejection_bases"] = [{"name": "Bad", "kind": "class", "module": "vb.core", "qualname": "Bad"}]
        for c in checks["checks"]:  # a longer label; the bare name is class_name
            c["class_name"] = c["class"]
            c["class"] = f"vb.core.{c['class']}"
    proc, record, checks = run_recorder(tmp_path, {"test_id.py": IDENTITY}, patch_checks=patch)
    assert rejection_by_test(record) == {"test_package_class": True, "test_builtin_class": False,
                                         "test_local_class": False}
    first = check_id(checks, "verify", "token must be a string")
    assert [c["fired"] for c in record["cases"] if c["test"].endswith("test_package_class")] == [[first]]


def test_builtin_rejection_base_by_identity(tmp_path):
    def patch(checks):
        checks["rejection_bases"] = [{"name": "ValueError", "kind": "builtin", "module": "builtins",
                                      "qualname": "ValueError"}]
    proc, record, _ = run_recorder(tmp_path, {"test_id.py": IDENTITY}, patch_checks=patch)
    assert rejection_by_test(record) == {"test_package_class": True, "test_builtin_class": True,
                                         "test_local_class": False}


# -- the phase that stops a test --------------------------------------------------------

PHASES = '''
import pytest

from vb.core import Bad, verify


@pytest.fixture
def asserting():
    assert 1 == 2


@pytest.fixture
def skipping():
    pytest.skip("no backend")


@pytest.fixture
def failing_teardown():
    yield
    assert 1 == 2


def test_fixture_assertion(asserting):
    with pytest.raises(Bad):
        verify(1)


def test_fixture_skip(skipping):
    with pytest.raises(Bad):
        verify(1)


def test_skip_before_block():
    pytest.skip("not today")
    with pytest.raises(Bad):
        verify(1)


@pytest.mark.xfail(reason="known")
def test_xfail_marker():
    assert 1 == 2
    with pytest.raises(Bad):
        verify(1)


def test_xfail_call():
    pytest.xfail("known")
    with pytest.raises(Bad):
        verify(1)


@pytest.mark.xfail(reason="known", strict=True)
def test_xpass_strict():
    with pytest.raises(Bad):
        verify(1)


def test_teardown_assertion(failing_teardown):
    with pytest.raises(Bad):
        verify(1)
'''


def test_phase_entries_tell_the_stops_apart(tmp_path):
    proc, record, _ = run_recorder(tmp_path, {"test_phases.py": PHASES})
    t = {k.split("::")[1]: v for k, v in node_entries(record).items()}
    ok = {"outcome": "passed", "stop": None, "stop_is_assertion": None}
    skipped = {"outcome": "skipped", "stop": "builtins.Skipped", "stop_is_assertion": False}
    assert t["test_fixture_assertion"]["setup"] == {"outcome": "failed", "stop": "builtins.AssertionError",
                                                    "stop_is_assertion": True}
    assert t["test_fixture_skip"]["setup"] == skipped
    assert t["test_skip_before_block"]["setup"] == ok
    assert t["test_skip_before_block"]["call"] == skipped
    assert t["test_xfail_marker"]["call"] == {"outcome": "skipped", "stop": "builtins.AssertionError",
                                              "stop_is_assertion": True, "xfail": True}
    # pytest.xfail() raises XFailed, a subclass of pytest's Failed: only `xfail` tells it
    # from a failed assertion
    assert t["test_xfail_call"]["call"] == {"outcome": "skipped", "stop": "_pytest.outcomes.XFailed",
                                            "stop_is_assertion": True, "xfail": True}
    assert t["test_xpass_strict"]["call"] == {"outcome": "failed", "stop": None, "stop_is_assertion": None}
    assert t["test_teardown_assertion"]["call"] == ok
    assert t["test_teardown_assertion"]["teardown"] == {"outcome": "failed", "stop": "builtins.AssertionError",
                                                        "stop_is_assertion": True}
    # a phase that does not run has no entry
    for name in ("test_fixture_assertion", "test_fixture_skip"):
        assert "call" not in t[name], t[name]
    assert {c["test"].split("::")[1] for c in record["cases"]} == {"test_xpass_strict", "test_teardown_assertion"}
    with open(tmp_path / "phases.json", "w", encoding="utf-8") as handle:  # the exact record, for reading
        json.dump(t, handle, indent=1, sort_keys=True)


# -- forms ------------------------------------------------------------------------------

FORMS = '''
import contextlib
import unittest

import pytest

from vb.core import Bad, verify


def raises_in_helper(token):
    with pytest.raises(Bad):
        verify(token)


@pytest.fixture
def checked_in_fixture():
    with pytest.raises(Bad):
        verify(1)
    return True


def test_with():
    with pytest.raises(Bad):
        verify(1)


def test_with_match():
    with pytest.raises(Bad, match="string"):
        verify(1)


def test_callable():
    pytest.raises(Bad, verify, 1)


def test_helper():
    raises_in_helper(1)
    raises_in_helper("split")


def test_fixture(checked_in_fixture):
    assert checked_in_fixture


@pytest.mark.parametrize("token", [1, "split"])
def test_parametrized(token):
    with pytest.raises(Bad):
        verify(token)


def test_two_items():
    with contextlib.nullcontext(), pytest.raises(Bad):
        verify(1)


def test_raises_group():
    with pytest.RaisesGroup(Bad):
        raise ExceptionGroup("group", [Bad("in a group")])


def test_raises_exc():
    with pytest.RaisesExc(Bad):
        verify(1)


class TestUnit(unittest.TestCase):
    def test_assert_raises_with(self):
        with self.assertRaises(Bad):
            verify(1)

    def test_assert_raises_call(self):
        self.assertRaises(Bad, verify, 1)

    def test_assert_raises_regex_with(self):
        with self.assertRaisesRegex(Bad, "string"):
            verify(1)

    def test_assert_raises_regex_call(self):
        self.assertRaisesRegex(Bad, "string", verify, 1)
'''


def test_forms(tmp_path):
    proc, record, checks = run_recorder(tmp_path, {"test_forms.py": FORMS})
    first = check_id(checks, "verify", "token must be a string")
    split = check_id(checks, "verify", "split over lines")
    assert "14 passed" in proc.stdout, proc.stdout
    seen = sorted((c["test"].split("::", 1)[1], c["block"].split("::")[1], c["index"], c["api"], c["form"],
                   c["included"], c["check_result"], tuple(c["fired"] or ()) if c["included"] else None)
                  for c in record["cases"])
    assert seen == [
        ("TestUnit::test_assert_raises_call", "TestUnit.test_assert_raises_call#0", 0, "unittest", "call",
         True, "accepted", (first,)),
        ("TestUnit::test_assert_raises_regex_call", "TestUnit.test_assert_raises_regex_call#0", 0, "unittest",
         "call", True, "accepted", (first,)),
        ("TestUnit::test_assert_raises_regex_with", "TestUnit.test_assert_raises_regex_with#0", 0, "unittest",
         "with", True, "accepted", (first,)),
        ("TestUnit::test_assert_raises_with", "TestUnit.test_assert_raises_with#0", 0, "unittest", "with",
         True, "accepted", (first,)),
        ("test_callable", "test_callable#0", 0, "pytest", "call", True, "accepted", (first,)),
        # a block in a fixture is a block of the fixture function, run in the test's setup
        ("test_fixture", "checked_in_fixture#0", 0, "pytest", "with", True, "accepted", (first,)),
        # a block in a helper is a block of the helper, 1 case per use in the test
        ("test_helper", "raises_in_helper#0", 0, "pytest", "with", True, "accepted", (first,)),
        ("test_helper", "raises_in_helper#0", 1, "pytest", "with", True, "accepted", (split,)),
        ("test_parametrized[1]", "test_parametrized#0", 0, "pytest", "with", True, "accepted", (first,)),
        ("test_parametrized[split]", "test_parametrized#0", 0, "pytest", "with", True, "accepted", (split,)),
        ("test_two_items", "test_two_items#0", 0, "pytest", "with", True, "accepted", (first,)),
        ("test_with", "test_with#0", 0, "pytest", "with", True, "accepted", (first,)),
        ("test_with_match", "test_with_match#0", 0, "pytest", "with", True, "accepted", (first,)),
    ]
    # pytest.RaisesGroup and pytest.RaisesExc are not wrapped: nothing is recorded for them
    assert record["unmatched"] == []
    assert all(t["call"]["outcome"] == "passed" and not t.get("failed_blocks") for t in record["tests"])


ASYNC = '''
import pytest

from vb.core import Bad, verify


@pytest.mark.asyncio
async def test_async_block():
    with pytest.raises(Bad):
        verify(1)
'''


def test_async_form(tmp_path):
    pytest.importorskip("pytest_asyncio")
    proc, record, checks = run_recorder(tmp_path, {"test_async.py": ASYNC})
    first = check_id(checks, "verify", "token must be a string")
    assert "1 passed" in proc.stdout, proc.stdout
    assert [(c["block"].split("::")[1], c["included"], c["check_result"], c["fired"], c["depth"])
            for c in record["cases"]] == [("test_async_block#0", True, "accepted", [first], 1)]
