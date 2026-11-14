"""Unit and end-to-end tests of the toolkit on the synthetic package in fixture/toy."""

from __future__ import annotations

import csv
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from reach.blocks import enumerate_blocks
from reach.checks import (enumerate_checks, load_subject, module_label, normalise_parts, read_source,
                          template_parts)
from reach.delete import delete_check
from reach.analyse import Run
from reach.report import e5_stated, expectations, sentinels_not_holding
from reach.run import (GUARD, INTERPRETER_PROBE, SUMMARY, environment_problems, interpreter_problem,
                       junit_outcomes, whole_run)
from reach.study import firing, firing_checks, left_out_reason, study_cases
from reach.scope import scope
from reach.targets import ASSERTION_TIER, compute_targets, text_verdict, tokens

E = Path(__file__).resolve().parents[1]
FIXTURE = E / "tests" / "fixture"
CLONE = FIXTURE / "toy"
SUBJECT = FIXTURE / "subject.json"
WORK = E / "work" / "unit-tests"


@pytest.fixture(scope="module")
def defs():
    subject = load_subject(SUBJECT)
    checks = enumerate_checks(subject, CLONE)
    blocks = enumerate_blocks(subject, CLONE, checks)
    targets = compute_targets(blocks, checks)
    return subject, checks, blocks, targets


def by_id(checks):
    return {c["id"]: c for c in checks["checks"]}


def test_definitions_are_plain_data(defs):
    # no value needs a fallback encoder, so the files are the same in every run
    for doc in defs:
        json.dumps(doc)


def test_tokens():
    assert tokens("test_decode_raises_InvalidAudienceError") == ["decode", "invalid", "audience"]
    assert tokens("claims a b is HS256") == ["claim", "hs256"]
    assert tokens("PyJWT payload's") == ["py", "jwt", "payload"]


def test_templates():
    import ast
    parse = lambda s: ast.parse(s, mode="eval").body  # noqa: E731
    assert normalise_parts(template_parts(parse('f"bad {x} value"'))) == ["bad ", None, " value"]
    assert normalise_parts(template_parts(parse('"a %s b %%" % x'))) == ["a ", None, " b %"]
    assert normalise_parts(template_parts(parse('"x {} y {{z}}".format(v)'))) == ["x ", None, " y {z}"]
    assert normalise_parts(template_parts(parse("msg"))) == [None]


def test_checks(defs):
    _, checks, _, _ = defs
    c = by_id(checks)
    assert len(checks["checks"]) == 10
    sub = [x for x in checks["checks"] if x["role"] == "subject"]
    assert len(sub) == 9
    assert {x["class"] for x in sub if x["reachable"]} == {"FormatError", "PolicyError", "ClaimMissing"}
    assert sum(x["class"] == "PolicyError" for x in sub) == 4
    assert sum(x["class"] == "FormatError" for x in sub) == 4
    assert c["core._check_claims#3"]["raise_numbers"] == [3, 4]
    assert c["core._check_version#1"]["template"] == "unknown version {*}"
    assert c["core._parse#3"]["guards"] == ["except ValueError as err"]
    assert c["core.encode#1"]["reachable"] is False
    assert c["keys.load_key#1"]["role"] == "observed" and c["keys.load_key#1"]["reachable"]
    assert [(o["function"], o["reason"]) for o in checks["other_raises"]] == [("_check_signature", "bare raise")]
    assert checks["classes"]["ClaimMissing"]["init_attrs"] == {"claim": 0}


def test_blocks(defs):
    _, _, blocks, _ = defs
    b = {x["key"].split("::", 1)[1]: x for x in blocks["blocks"]}
    assert blocks["counts"] == {"blocks": 18, "included": 16, "entry_point_blocks": 17}
    assert b["test_lookup_error_passes_through#0"]["exclusion"] == ["expects LookupError"]
    assert b["test_encode_rejects_list#0"]["exclusion"] == ["no entry-point call"]
    assert b["test_three_parts_needed#0"]["form"] == "call"
    assert b["TestToy.test_bad_json_regex_callable#0"]["form"] == "call"
    assert b["TestToy.test_bad_json_regex_callable#0"]["match"] == "json"
    assert b["test_audience_mismatch#0"]["post"] == [["str_eq", "audience mismatch"]]
    assert b["test_missing_audience_claim#0"]["post"] == [["attr_eq", "claim", "aud"]]
    assert b["test_unknown_key#0"]["post"] == [["match", "unknown key"]]
    assert b["TestToy.test_non_string_token#0"]["post"] == [["str_eq", "token must be a string"]]
    assert b["TestToy.test_audience_in_message#0"]["post"] == [["str_in", "audience"]]
    assert b["test_signature_twice#1"]["k"] == 1


def test_targets(defs):
    _, _, _, targets = defs
    t = {x["key"].split("::", 1)[1]: x for x in targets["blocks"]}
    expect = {
        # the pattern is found in 1 literal message; the placeholder template stays possible
        "test_non_string_token#0": ("core._parse#1", "assert-literal"),
        "test_three_parts_needed#0": ("core._parse#2", "name"),
        # the other 2 messages have no placeholder and do not hold the text
        "test_bad_json_body#0": ("core._parse#3", "assert"),
        "test_versions_loop#0": ("core._check_version#1", "name"),
        "test_audience_mismatch#0": ("core._check_claims#2", "assert-literal"),
        "test_missing_audience_claim#0": ("core._check_claims#1", "class"),
        "test_expired#0": ("core._check_claims#3", "assert-literal"),
        "test_signature_with_revoked_key#0": ("core._check_signature#1", "name"),
        "test_signature_twice#0": ("core._check_signature#1", "assert-literal"),
        "test_signature_twice#1": ("core._check_signature#1", "name"),
        "test_unknown_key#0": ("keys.load_key#1", "assert-literal"),
        "TestToy.test_non_string_token#0": ("core._parse#1", "assert"),
        "TestToy.test_three_parts_callable#0": ("core._parse#2", "name"),
        "TestToy.test_bad_json_regex#0": ("core._parse#3", "assert"),
        "TestToy.test_bad_json_regex_callable#0": ("core._parse#3", "assert"),
        "TestToy.test_audience_in_message#0": ("core._check_claims#2", "assert-literal"),
    }
    assert set(t) == set(expect)
    for key, (target, basis) in expect.items():
        assert (t[key]["target"], t[key]["basis"]) == (target, basis), key
        assert t[key]["tier"] == ("assertion" if basis in ASSERTION_TIER else "name"), key
    assert targets["counts"] == {"assert": 4, "assert-literal": 6, "class": 1, "name": 5}
    mismatch = t["test_audience_mismatch#0"]
    # a check whose class overrides __str__ is never excluded by a text assertion
    assert "core._check_claims#1" in mismatch["C_assert"]
    # a template with a placeholder is excluded when the whole text cannot fit it
    assert "core._check_version#1" in mismatch["excluded"]
    # ... and stays possible when the assertion reads only a part of the text
    assert "core._check_version#1" in t["TestToy.test_audience_in_message#0"]["C_assert"]
    assert mismatch["C_pos"] == ["core._check_claims#2"]


def check(template_parts, cls="E", **extra):
    base = {"class": cls, "template_parts": template_parts,
            "has_placeholder": any(p is None for p in template_parts),
            "has_keywords": False, "n_positional": [1], "literal_args": []}
    base.update(extra)
    return base


def test_text_verdicts():
    classes = {"E": {"bases": ["Exception"], "defines": [], "init_attrs": {}},
               "Odd": {"bases": ["E"], "defines": ["__str__"], "init_attrs": {}}}
    plain = check(["key is missing"])
    opened = check(["bad value ", None, " in header"])
    bare = check([None])
    v = lambda c, kind, value: text_verdict(c, kind, value, classes)  # noqa: E731
    assert v(plain, "str_eq", "key is missing") == "yes"
    assert v(plain, "str_eq", "key is") == "no"
    assert v(plain, "str_in", "missing") == "yes"
    assert v(plain, "str_in", "absent") == "no"
    assert v(plain, "match", "is m.ssing") == "yes"
    assert v(plain, "match", "^missing") == "no"
    assert v(opened, "str_eq", "bad value 7 in header") == "yes"
    assert v(opened, "str_eq", "bad header") == "no"
    assert v(opened, "str_in", "in header") == "yes"
    assert v(opened, "str_in", "seven") == "maybe"      # the placeholder may hold it
    assert v(opened, "match", "bad value") == "yes"
    assert v(opened, "match", "seven") == "maybe"
    assert v(opened, "match", "bad value .* in") == "yes"
    assert v(opened, "match", ".") == "maybe"            # a pattern the placeholder alone satisfies
    assert v(opened, "match", "(") == "maybe"            # not a valid pattern
    assert v(bare, "str_eq", "anything") == "maybe"
    assert v(bare, "str_in", "anything") == "maybe"
    # the text of the exception is not its argument: nothing is decided
    assert v(check(["key is missing"], cls="Odd"), "str_eq", "other") == "maybe"
    assert v(check(["key is missing"], n_positional=[2]), "str_in", "other") == "maybe"
    assert v(check(["key is missing"], has_keywords=True), "match", "other") == "maybe"


def package(tmp_path, source, tests=None):
    pkg = tmp_path / "vb"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .core import verify\n", encoding="utf-8")
    (pkg / "core.py").write_text(source, encoding="utf-8")
    if tests is not None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_vb.py").write_text(tests, encoding="utf-8")
    return {"name": "vb", "package": "vb", "source_root": ".", "subject_files": ["vb/core.py"],
            "observed_files": [], "entry_points": ["verify"], "rejection_bases": ["ValueError"],
            "tests": ["tests"]}


def test_variable_raise_and_builtin_base(tmp_path):
    subject = package(tmp_path, """
class Malformed(ValueError):
    pass


def verify(token):
    if not token:
        raise ValueError("empty token")
    exc = Malformed("bad token: " + token)
    if token.startswith("x"):
        raise exc
    err = ValueError("one")
    err = ValueError("two")
    if token == "y":
        raise err
    if token == "z":
        raise KeyError(token)
    try:
        int(token)
    except TypeError as caught:
        raise caught
    return token
""")
    doc = enumerate_checks(subject, tmp_path)
    c = by_id(doc)
    assert sorted(c) == ["core.verify#1", "core.verify#2"]
    assert (c["core.verify#1"]["class"], c["core.verify#1"]["template"]) == ("ValueError", "empty token")
    # raise exc, where the function binds exc once, from a call of a rejection class
    assert (c["core.verify#2"]["class"], c["core.verify#2"]["template"]) == ("Malformed", "bad token: {*}")
    assert c["core.verify#2"]["via_variable"] == ["exc"]
    assert doc["rejection_classes"] == ["Malformed"]
    # a name bound twice, a class outside the rejection base, and a re-raise are not checks
    assert [(o["class"], o["reason"]) for o in doc["other_raises"]] == [
        ("err", "not a rejection class"), ("KeyError", "not a rejection class"),
        ("caught", "re-raise of a bound exception")]


def test_message_given_by_keyword(tmp_path):
    subject = package(tmp_path, """
class ProtocolError(ValueError):
    def __init__(self, description=None, request=None):
        super().__init__(description)


class Narrow(ProtocolError):
    pass


def verify(request):
    if request is None:
        raise ProtocolError(description="Missing request.", request=request)
    if request == "":
        raise Narrow(description="Empty request.", request=request)
    if request == "x":
        raise Narrow(request=request)
    if request == "y":
        raise Narrow(request=request, description="Late %s." % request)
    return request
""")
    c = by_id(enumerate_checks(subject, tmp_path))
    assert [(k, v["class"], v["template"]) for k, v in sorted(c.items())] == [
        ("core.verify#1", "ProtocolError", "Missing request."),
        ("core.verify#2", "Narrow", "Empty request."),
        ("core.verify#3", "Narrow", ""),
        ("core.verify#4", "Narrow", "Late {*}.")]
    assert c["core.verify#1"]["literal_args"] == [{"pos": {}, "kw": {"description": "Missing request."}}]
    assert c["core.verify#3"]["literal_args"] == [{"pos": {}, "kw": {}}]


def test_scope():
    draft = {k: v for k, v in load_subject(SUBJECT).items()
             if k not in ("subject_files", "observed_files", "tests")}
    draft["test_directories"] = ["tests"]
    subject = scope(draft, CLONE)
    assert subject["subject_files"] == ["toyverify/__init__.py", "toyverify/core.py",
                                        "toyverify/errors.py", "toyverify/keys.py"]
    assert subject["tests"] == ["tests/test_pytest_style.py", "tests/test_unittest_style.py"]
    assert subject["observed_files"] == [] and "test_directories" not in subject


def test_module_label():
    subject = {"package": "a.b"}
    assert module_label(subject, "a/b/jwt.py") == "jwt"
    assert module_label(subject, "a/b/crypt/rsa.py") == "crypt.rsa"
    assert module_label(subject, "a/c/jwt.py") == "a.c.jwt"
    assert module_label({"package": "jwt"}, "jwt/api_jws.py") == "api_jws"


def test_last_definition_of_a_test_wins(tmp_path):
    subject = package(tmp_path, "def verify(token):\n    raise ValueError('no')\n", tests="""
import pytest
from vb import verify


def test_twice():
    with pytest.raises(ValueError, match="first"):
        verify("a")


def test_twice():  # noqa: F811
    with pytest.raises(ValueError):
        verify("b")
    with pytest.raises(ValueError):
        verify("c")
""")
    checks = enumerate_checks(subject, tmp_path)
    blocks = enumerate_blocks(subject, tmp_path, checks)
    assert [(b["key"], b["match"]) for b in blocks["blocks"]] == [
        ("tests/test_vb.py::test_twice#0", None), ("tests/test_vb.py::test_twice#1", None)]


def test_byte_order_mark(tmp_path):
    source = """
def verify(token):
    if not token:
        raise ValueError("empty token")
    return token
"""
    subject = package(tmp_path, source)
    plain = enumerate_checks(subject, tmp_path)["checks"]
    path = tmp_path / "vb" / "core.py"
    path.write_text(source, encoding="utf-8-sig")
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    marked = enumerate_checks(subject, tmp_path)["checks"]
    assert [(c["id"], c["lines"]) for c in marked] == [(c["id"], c["lines"]) for c in plain]
    out, _ = delete_check(read_source(path), marked[0])
    assert "empty token" not in out and "pass" in out


def test_junit_outcomes(tmp_path):
    path = tmp_path / "r.xml"
    path.write_text("""<?xml version="1.0"?><testsuites><testsuite>
<testcase classname="tests.test_a.TestA" name="test_one"/>
<testcase classname="tests.test_a.TestA" name="test_two"><failure message="x">boom</failure></testcase>
<testcase classname="tests.test_a" name="test_three"><skipped message="s"/></testcase>
<testcase classname="" name="tests.test_b"><error message="collection failure">e</error></testcase>
<testcase classname="tests.test_a" name="test_same"/>
<testcase classname="tests.test_a" name="test_same"><error message="teardown">e</error></testcase>
</testsuite></testsuites>""", encoding="utf-8")
    assert junit_outcomes(path, "all") == {
        "all|tests.test_a.TestA::test_one": "passed", "all|tests.test_a.TestA::test_two": "failed",
        "all|tests.test_a::test_three": "skipped", "all|::tests.test_b": "failed",
        "all|tests.test_a::test_same": "failed"}


def test_suite_summary():
    text = "tests/test_a.py ....\n======= 76 passed, 1 warning in 2.11s =======\nsome warning line\n"
    assert SUMMARY.findall(text)[-1] == "76 passed, 1 warning"
    assert SUMMARY.findall("3 failed, 310 passed in 12.02s (0:00:12)\n")[-1] == "3 failed, 310 passed"
    assert SUMMARY.findall("no tests ran in 0.01s\n") == []
    # an item of 2 words, as pytest 9 prints for subtests
    assert SUMMARY.findall("310 passed, 91 subtests passed in 6.54s\n")[-1] == "310 passed, 91 subtests passed"
    assert SUMMARY.findall("==== 1 failed, 2 passed, 3 subtests failed, 4 subtests passed in 0.50s ====\n") == [
        "1 failed, 2 passed, 3 subtests failed, 4 subtests passed"]


def test_delete(defs):
    _, checks, _, _ = defs
    c = by_id(checks)
    source = (CLONE / "toyverify" / "core.py").read_text(encoding="utf-8")
    out, changed = delete_check(source, c["core._check_signature#1"])
    assert len(out.splitlines()) == len(source.splitlines())
    assert "signature mismatch" not in out
    assert changed[0]["lines"] == c["core._check_signature#1"]["lines"][0]
    out, _ = delete_check(source, c["core._check_claims#3"])
    assert "token expired" not in out


def rows(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as handle:
        return {r["check"]: r for r in csv.DictReader(handle)}


def test_end_to_end():
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "defs").mkdir(parents=True)
    shutil.copy(SUBJECT, WORK / "defs" / "subject.json")
    subject = str(WORK / "defs" / "subject.json")
    run = [sys.executable, "-I", str(E / "reach" / "run.py")]
    common = ["--subject", subject, "--work", str(WORK / "work")]
    subprocess.run(run + ["define", "targets", "verify", "baseline", "deletions", "whole-baseline",
                          "whole-deletions"] + common +
                   ["--clone", str(CLONE), "--python", sys.executable], check=True, capture_output=True)
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py")] + common +
                          ["--out", str(WORK / "out")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads((WORK / "out" / "summary.json").read_text(encoding="utf-8"))
    assert all(s["pass"] for s in summary["sentinels"]) and len(summary["sentinels"]) == 7
    assert summary["counts"]["cases"] == 18          # 16 blocks; 1 parametrized and 1 looped block run twice
    assert summary["counts"]["cases_reaching_target"] == 17
    record = json.loads((WORK / "work" / "records" / "base-1.json").read_text(encoding="utf-8"))
    forms = {(c["api"], c["form"]) for c in record["cases"]}
    assert forms == {("pytest", "with"), ("pytest", "call"), ("unittest", "with"), ("unittest", "call")}
    revoked = [c for c in record["cases"] if "revoked_key" in c["block"]][0]
    assert revoked["site"]["kind"] == "outside checks" and revoked["site"]["check"] is None
    lookup = [c for c in record["cases"] if "lookup_error" in c["block"]][0]
    assert lookup["included"] is False and "site" not in lookup
    d = rows(WORK / "out" / "deletions.csv")
    # every case of the version check moves to the signature check, of the same class
    assert (d["core._check_version#1"]["O_V"], d["core._check_version#1"]["O_C"],
            d["core._check_version#1"]["O_T"], d["core._check_version#1"]["O_S"]) == ("no", "no", "yes", "no")
    # without the type check the package fails with a non-rejection exception
    assert (d["core._parse#1"]["O_V"], d["core._parse#1"]["O_Vfc"]) == ("yes", "no")
    # the recorder lets a test go on after a block that failed its own check: without the
    # signature check both blocks of test_signature_twice run, and neither raises
    assert d["core._check_signature#1"]["moved_to"] == "no exception x2"
    assert d["core._check_signature#1"]["cases_withheld"] == "0"
    deleted = json.loads((WORK / "work" / "records" / "deletions" / "core._check_signature-1.json")
                         .read_text(encoding="utf-8"))
    twice = [t for t in deleted["tests"] if t["nodeid"].endswith("::test_signature_twice")][0]
    assert [f["result"] for f in twice["failed_blocks"]] == ["failed", "failed"]
    assert twice["call"]["outcome"] == "passed"      # pytest's own outcome; the analysis reads failed_blocks
    assert d["core._check_signature#1"]["O_S"] == "yes"
    with (WORK / "out" / "flags.csv").open(encoding="utf-8") as handle:
        flags = list(csv.DictReader(handle))
    assert [(f["test"], f["tier"], f["target"]) for f in flags] == [
        ("test_signature_with_revoked_key", "name", "core._check_signature#1")]
    assert flags[0]["deciding_check"].startswith("outside checks")
    # pinning: without the version check both cases of test_versions_loop are rejected by the
    # signature check with the same class, and the test, which asserts the class only, passes
    with (WORK / "out" / "pinning.csv").open(encoding="utf-8") as handle:
        pinning = list(csv.DictReader(handle))
    passing = [r for r in pinning if r["test_passes"] == "yes"]
    assert {(r["deleted_check"], r["asserts"], r["what_the_case_does"]) for r in passing} == {
        ("core._check_version#1", "class only", "same class, another check")}
    assert len(pinning) == 16 and len(passing) == 2
    p = summary["counts"]["pinning"]
    assert (p["cases"], p["test_passes"], p["class_only"], p["message"]) == (
        16, 2, {"cases": 5, "test_passes": 2}, {"cases": 11, "test_passes": 0})
    assert summary["counts"]["deletions_not_detected"] == {
        "O_V": 1, "O_Vfc": 5, "O_C": 1, "O_T": 0, "O_S": 1, "suite": 1, "whole suite": 1}
    # the whole suite, run without the recorder, misses the same deletion
    assert [k for k, r in d.items() if r["whole_suite"] == "no"] == ["core._check_version#1"]
    # the packed records give the same analysis, and packing twice gives the same bytes
    packs = []
    for name in ("pack-1", "pack-2"):
        subprocess.run(run + ["pack"] + common + ["--out", str(WORK / name)], check=True, capture_output=True)
        packs.append((WORK / name / "records.tar.xz").read_bytes())
    assert packs[0] == packs[1]
    with tarfile.open(WORK / "pack-1" / "records.tar.xz") as tar:
        names = tar.getnames()
        tar.extractall(WORK / "unpacked", filter="data")
    assert "records/base-1.json" in names and not [n for n in names if n.endswith(".xml")]
    again = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py"), "--subject", subject,
                            "--work", str(WORK / "unpacked"), "--out", str(WORK / "out-2")],
                           capture_output=True, text=True)
    assert again.returncode == 0, again.stdout + again.stderr
    for name in ("summary.json", "cases.csv", "deletions.csv", "pinning.csv", "flags.csv", "checks.csv"):
        assert (WORK / "out" / name).read_bytes() == (WORK / "out-2" / name).read_bytes(), name
    # a message text that differs between the unmodified runs is counted and fails no sentinel;
    # a class that differs fails the first sentinel
    assert summary["counts"]["cases_message_text_differs_between_unmodified_runs"] == 0
    second = WORK / "unpacked" / "records" / "base-2.json"
    doc = json.loads(second.read_text(encoding="utf-8"))
    doc["cases"][0]["message"] += " at 12:00"
    second.write_text(json.dumps(doc), encoding="utf-8")
    again = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py"), "--subject", subject,
                            "--work", str(WORK / "unpacked"), "--out", str(WORK / "out-3")],
                           capture_output=True, text=True)
    assert again.returncode == 0, again.stdout + again.stderr
    third = json.loads((WORK / "out-3" / "summary.json").read_text(encoding="utf-8"))
    assert third["counts"]["cases_message_text_differs_between_unmodified_runs"] == 1
    doc["cases"][0]["class"] = "builtins.KeyError"
    second.write_text(json.dumps(doc), encoding="utf-8")
    again = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py"), "--subject", subject,
                            "--work", str(WORK / "unpacked"), "--out", str(WORK / "out-4")],
                           capture_output=True, text=True)
    assert again.returncode == 1
    fourth = json.loads((WORK / "out-4" / "summary.json").read_text(encoding="utf-8"))
    assert [s["pass"] for s in fourth["sentinels"]] == [False, True, True, True, True, True, True]
    assert summary["whole_suite"]["counts"]["unstable"] == 0
    assert summary["counts"]["deletions_time_limit"] == 0


LOOP_CORE = '''
class LoopError(Exception):
    pass


def decode(text):
    end = _find_end(text)
    if text[:end] != "ok":
        raise LoopError("content is not ok")
    return text[:end]


def _find_end(text):
    pos = 0
    while True:
        nxt = text.find(";", pos)
        if nxt < 0:
            raise LoopError("terminator missing")
        if nxt > 0 and text[nxt - 1] != "!":
            return nxt
        pos = nxt + 1
'''

LOOP_TESTS = '''
import pytest
from loopy.core import LoopError, decode


def test_accepts():
    assert decode("ok;") == "ok"


def test_terminator_missing():
    with pytest.raises(LoopError, match="terminator missing"):
        decode("ok")


def test_content():
    with pytest.raises(LoopError, match="content is not ok"):
        decode("no;")
'''


def test_time_limit():
    """A deletion after which a test never ends: the run exceeds the time limit twice
    and the deletion counts as detected under every oracle, with and without the recorder."""
    root = E / "work" / "unit-tests-loop"
    if root.exists():
        shutil.rmtree(root)
    clone = root / "clone"
    (clone / "loopy").mkdir(parents=True)
    (clone / "tests").mkdir()
    (clone / "loopy" / "__init__.py").write_text("", encoding="utf-8")
    (clone / "loopy" / "core.py").write_text(LOOP_CORE, encoding="utf-8")
    (clone / "tests" / "test_loop.py").write_text(LOOP_TESTS, encoding="utf-8")
    (clone / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (root / "defs").mkdir()
    subject = {"name": "loopy", "version": "0", "repository": None, "commit": None,
               "distribution": "loopy-fixture", "package": "loopy", "source_root": ".",
               "subject_files": ["loopy/core.py"], "observed_files": [], "entry_points": ["decode"],
               "rejection_bases": ["LoopError"], "tests": ["tests"],
               "pytest_args": ["-p", "no:cacheprovider"], "copy": ["loopy", "tests", "pyproject.toml"],
               "python": sys.version.split()[0], "suite_runs": [{"name": "all", "paths": ["tests"]}]}
    path = root / "defs" / "subject.json"
    path.write_text(json.dumps(subject), encoding="utf-8")
    run = [sys.executable, "-I", str(E / "reach" / "run.py")]
    common = ["--subject", str(path), "--work", str(root / "work")]
    subprocess.run(run + ["define", "targets", "baseline", "whole-baseline"] + common +
                   ["--clone", str(clone), "--python", sys.executable], check=True, capture_output=True)
    records = root / "work" / "records"
    limit = json.loads((records / "timeout.json").read_text(encoding="utf-8"))
    assert limit == {"rule": "max(60 s, 10 x the slower baseline run)", "timeout_seconds": 60.0}
    whole = json.loads((records / "whole" / "base.json").read_text(encoding="utf-8"))
    assert whole["timeout_seconds"] == 60.0 and whole["counts"]["passing in both"] == 3
    # the test does not wait for 4 limits of 60 s: it shortens both limits in the records
    limit["timeout_seconds"] = 3.0
    (records / "timeout.json").write_text(json.dumps(limit), encoding="utf-8")
    whole["timeout_seconds"] = 3.0
    (records / "whole" / "base.json").write_text(json.dumps(whole), encoding="utf-8")
    subprocess.run(run + ["deletions", "whole-deletions"] + common, check=True, capture_output=True)
    no_record = json.loads((records / "deletions" / "no-record.json").read_text(encoding="utf-8"))
    assert no_record == {"core._find_end#1": {"returncode": [None, None], "timed_out": [True, True]}}
    wd = json.loads((records / "whole" / "deletions.json").read_text(encoding="utf-8"))
    assert (wd["core._find_end#1"]["timed_out"], wd["core._find_end#1"]["runs"],
            wd["core._find_end#1"]["detected"]) == (True, 2, True)
    assert (wd["core.decode#1"]["timed_out"], wd["core.decode#1"]["runs"]) == (False, 1)
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py")] + common +
                          ["--out", str(root / "out")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads((root / "out" / "summary.json").read_text(encoding="utf-8"))
    assert all(s["pass"] for s in summary["sentinels"]) and len(summary["sentinels"]) == 7
    c = summary["counts"]
    assert (c["deletions"], c["deletions_time_limit"]) == (2, 1)
    assert summary["lists"]["deletions_time_limit"] == ["core._find_end#1"]
    assert summary["whole_suite"]["deletions_time_limit"] == ["core._find_end#1"]
    assert c["pinning"]["cases_not_counted_time_limit"] == 1 and c["pinning"]["cases"] == 1
    d = rows(root / "out" / "deletions.csv")
    line = d["core._find_end#1"]
    assert line["run"] == "time limit" and line["whole_suite"] == "yes"
    assert {line[o] for o in ("O_V", "O_Vfc", "O_C", "O_T", "O_S", "suite")} == {"yes"}
    # a run that gives no record for another reason fails a sentinel
    no_record["core._find_end#1"]["timed_out"] = [True, False]
    (records / "deletions" / "no-record.json").write_text(json.dumps(no_record), encoding="utf-8")
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py")] + common +
                          ["--out", str(root / "out-2")], capture_output=True, text=True)
    assert proc.returncode == 1
    failed = json.loads((root / "out-2" / "summary.json").read_text(encoding="utf-8"))["sentinels"]
    assert [s["name"] for s in failed if not s["pass"]] == [
        "every deletion run gave a record or exceeded the time limit 2 times"]


WRAP_CORE = '''
class WrapError(Exception):
    pass


def decode(parts):
    """The first part that passes; a rejection when none does."""
    for part in parts:
        try:
            return _check_part(part)
        except WrapError:
            continue
    raise WrapError("no part accepted")


def _check_part(part):
    if len(part) > 4:
        raise WrapError("part too long")
    if not part:
        raise WrapError("part is empty")
    return part
'''

WRAP_TESTS = '''
import pytest
from wrappy.core import WrapError, decode


def test_accepts():
    assert decode(["toolong", "ok"]) == "ok"


def test_part_too_long():
    with pytest.raises(WrapError):
        decode(["toolong"])


def test_nothing_given():
    with pytest.raises(WrapError, match="no part accepted"):
        decode([])
'''


def test_fired_checks():
    """A handler replaces the exception of the check a test describes: the check fires,
    another check decides, the case is a flag whose target fires, and the check that
    fires and never decides is deleted too."""
    root = E / "work" / "unit-tests-wrap"
    if root.exists():
        shutil.rmtree(root)
    clone = root / "clone"
    (clone / "wrappy").mkdir(parents=True)
    (clone / "tests").mkdir()
    (clone / "wrappy" / "__init__.py").write_text("", encoding="utf-8")
    (clone / "wrappy" / "core.py").write_text(WRAP_CORE, encoding="utf-8")
    (clone / "tests" / "test_wrap.py").write_text(WRAP_TESTS, encoding="utf-8")
    (clone / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (root / "defs").mkdir()
    subject = {"name": "wrappy", "version": "0", "repository": None, "commit": None,
               "distribution": "wrappy-fixture", "package": "wrappy", "source_root": ".",
               "subject_files": ["wrappy/core.py"], "observed_files": [], "entry_points": ["decode"],
               "rejection_bases": ["WrapError"], "tests": ["tests"],
               "pytest_args": ["-p", "no:cacheprovider"], "copy": ["wrappy", "tests", "pyproject.toml"],
               "python": sys.version.split()[0], "suite_runs": [{"name": "all", "paths": ["tests"]}]}
    path = root / "defs" / "subject.json"
    path.write_text(json.dumps(subject), encoding="utf-8")
    run = [sys.executable, "-I", str(E / "reach" / "run.py")]
    common = ["--subject", str(path), "--work", str(root / "work")]
    subprocess.run(run + ["define", "targets", "baseline", "deletions", "whole-baseline",
                          "whole-deletions"] + common +
                   ["--clone", str(clone), "--python", sys.executable], check=True, capture_output=True)
    records = root / "work" / "records"
    base = json.loads((records / "base-1.json").read_text(encoding="utf-8"))
    assert base["fired_recorded"] is True
    seen = {c["block"]: ((c["site"] or {}).get("check"), c["fired"]) for c in base["cases"] if c["included"]}
    assert seen == {
        "tests/test_wrap.py::test_part_too_long#0": ("core.decode#1", ["core._check_part#1", "core.decode#1"]),
        "tests/test_wrap.py::test_nothing_given#0": ("core.decode#1", ["core.decode#1"])}
    manifest = json.loads((records / "deletions" / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(k for k in manifest if not k.startswith("_")) == ["core._check_part#1", "core.decode#1"]
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py")] + common +
                          ["--out", str(root / "out")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads((root / "out" / "summary.json").read_text(encoding="utf-8"))
    assert all(s["pass"] for s in summary["sentinels"]) and len(summary["sentinels"]) == 7
    counts = summary["counts"]
    assert (counts["cases"], counts["cases_with_target"], counts["cases_reaching_target"],
            counts["flags"], counts["flags_target_fires"]) == (2, 2, 1, 1, 1)
    assert (counts["cases_target_fires"], counts["cases_another_check_fires_too"]) == (2, 1)
    assert (counts["checks_deciding"], counts["checks_firing"],
            counts["checks_firing_and_never_deciding"]) == (1, 2, 1)
    assert (counts["deletions"], counts["deletions_of_deciding_checks"],
            counts["deletions_of_checks_that_fire_and_never_decide"]) == (2, 1, 1)
    assert summary["lists"]["deletions_of_checks_that_fire_and_never_decide"] == ["core._check_part#1"]
    assert set(counts["deletions_breaking_an_inclusion"].values()) == {0}
    with (root / "out" / "flags.csv").open(encoding="utf-8") as handle:
        flags = list(csv.DictReader(handle))
    assert [(f["target"], f["deciding_check"], f["basis"], f["target_fired"],
             f["own_test_without_target"]) for f in flags] == [
        ("core._check_part#1", "core.decode#1", "name", "yes", "fails")]
    assert counts["cases_with_target_by_outcome"] == {
        "decided by the target": 1,
        "decided by the target; own test without the target: fails": 1,
        "the target fires and another check decides": 1,
        "the target fires and another check decides; own test without the target: fails": 1}
    deleted = rows(root / "out" / "deletions.csv")
    # without the check, the part passes: no rejection, and the test of the accepted part fails too
    assert (deleted["core._check_part#1"]["O_V"], deleted["core._check_part#1"]["whole_suite"]) == ("yes", "yes")
    assert (deleted["core._check_part#1"]["cases_decided"], deleted["core._check_part#1"]["cases_fired"]) == ("0", "1")
    assert deleted["core._check_part#1"]["fires_instead"] == "no other check x1"
    assert deleted["core.decode#1"]["fires_instead"] == "no other check x2"
    # the deciding check is missing from what fired: the sentinel that ties the 2 mechanisms fails alone
    for name in ("base-1.json", "base-2.json", "deletions/_control.json"):
        doc = json.loads((records / name).read_text(encoding="utf-8"))
        for c in doc["cases"]:
            if c["included"] and c["block"].endswith("test_nothing_given#0"):
                c["fired"] = []
        (records / name).write_text(json.dumps(doc), encoding="utf-8")
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py")] + common +
                          ["--out", str(root / "out-2")], capture_output=True, text=True)
    assert proc.returncode == 1
    failed = json.loads((root / "out-2" / "summary.json").read_text(encoding="utf-8"))["sentinels"]
    assert [s["name"] for s in failed if not s["pass"]] == [
        "the check that decides a case is among the checks that fire in it"]


GAP_CORE = '''
class GapError(Exception):
    pass


def decode(part):
    if len(part) > 8:
        raise GapError("part too long")
    if not part.isalnum():
        raise GapError("part has a bad character")
    return part
'''

GAP_TESTS = '''
import pytest
from gappy.core import GapError, decode


def test_accepts():
    assert decode("abc") == "abc"


def test_long_part():
    with pytest.raises(GapError):
        decode("x y" * 9)
'''

GAP_WITNESS = '''# deleted check: core.decode#1
import pytest
from gappy.core import GapError, decode


def test_long_part_alone():
    with pytest.raises(GapError):
        decode("x" * 99)
'''

GAP_SKIPPED_WITNESS = '''# deleted check: core.decode#1
import pytest
from gappy.core import GapError, decode


def test_long_part_skipped():
    try:
        decode("x" * 99)
    except GapError:
        return
    pytest.skip("accepted")
'''

GAP_NO_WITNESS = '''# deleted check: core.decode#2
import pytest
from gappy.core import GapError, decode


def test_long_part_again():
    with pytest.raises(GapError):
        decode("x y" * 9)
'''


def test_undetected_deletion_and_witness():
    """The only negative test gives an input that 2 checks reject: the deletion of the
    first is detected by no test, the table of undetected deletions shows what rejects
    instead, and a witness test with an input that only the first check rejects holds."""
    root = E / "work" / "unit-tests-gap"
    if root.exists():
        shutil.rmtree(root)
    clone = root / "clone"
    (clone / "gappy").mkdir(parents=True)
    (clone / "tests").mkdir()
    (clone / "gappy" / "__init__.py").write_text("", encoding="utf-8")
    (clone / "gappy" / "core.py").write_text(GAP_CORE, encoding="utf-8")
    (clone / "tests" / "test_gap.py").write_text(GAP_TESTS, encoding="utf-8")
    (clone / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (root / "defs").mkdir()
    (root / "witnesses").mkdir()
    (root / "witnesses" / "test_long_part_alone.py").write_text(GAP_WITNESS, encoding="utf-8")
    (root / "witnesses" / "test_long_part_again.py").write_text(GAP_NO_WITNESS, encoding="utf-8")
    (root / "witnesses" / "test_long_part_skipped.py").write_text(GAP_SKIPPED_WITNESS, encoding="utf-8")
    subject = {"name": "gappy", "version": "0", "repository": None, "commit": None,
               "distribution": "gappy-fixture", "package": "gappy", "source_root": ".",
               "subject_files": ["gappy/core.py"], "observed_files": [], "entry_points": ["decode"],
               "rejection_bases": ["GapError"], "tests": ["tests"],
               "pytest_args": ["-p", "no:cacheprovider"], "copy": ["gappy", "tests", "pyproject.toml"],
               "python": sys.version.split()[0], "suite_runs": [{"name": "all", "paths": ["tests"]}]}
    path = root / "defs" / "subject.json"
    path.write_text(json.dumps(subject), encoding="utf-8")
    run = [sys.executable, "-I", str(E / "reach" / "run.py")]
    common = ["--subject", str(path), "--work", str(root / "work")]
    subprocess.run(run + ["define", "targets", "baseline", "deletions", "whole-baseline",
                          "whole-deletions", "witness"] + common +
                   ["--clone", str(clone), "--python", sys.executable,
                    "--witnesses", str(root / "witnesses")], check=True, capture_output=True)
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py")] + common +
                          ["--out", str(root / "out")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads((root / "out" / "summary.json").read_text(encoding="utf-8"))
    assert all(s["pass"] for s in summary["sentinels"])
    counts = summary["counts"]
    assert (counts["cases"], counts["cases_reaching_target"], counts["flags"], counts["deletions"]) == (1, 1, 0, 1)
    assert counts["deletions_not_detected"] == {"O_V": 1, "O_Vfc": 1, "O_C": 1, "O_T": 0, "O_S": 1,
                                                "suite": 1, "whole suite": 1}
    assert set(counts["deletions_breaking_an_inclusion"].values()) == {0}
    with (root / "out" / "undetected.csv").open(encoding="utf-8") as handle:
        undetected = list(csv.DictReader(handle))
    assert [(u["deleted_check"], u["block"], u["baseline_decided_by"], u["baseline_message"], u["status"],
             u["class"].rsplit(".", 1)[-1], u["decided_by"], u["message"], u["fires_now_and_not_before"])
            for u in undetected] == [
        ("core.decode#1", "tests/test_gap.py::test_long_part#0", "core.decode#1", "part too long", "observed",
         "GapError", "core.decode#2", "part has a bad character", "core.decode#2")]
    # the first witness holds; the second gives an input that the check after it still rejects;
    # the third is skipped without the check, and a test that does not fail is no witness
    witnesses = summary["witnesses"]
    assert {name: (w["check"], w["holds"]) for name, w in witnesses.items()} == {
        "test_long_part_alone.py": ("core.decode#1", True),
        "test_long_part_again.py": ("core.decode#2", False),
        "test_long_part_skipped.py": ("core.decode#1", False)}
    # tests of the file, passing on the unmodified copy, failing and not passing without the check
    assert {name: (w["tests"], w["tests_passing_on_the_unmodified_copy"], w["tests_failing_without_the_check"],
                   w["tests_not_passing_without_the_check"]) for name, w in witnesses.items()} == {
        "test_long_part_alone.py": (1, 1, 1, 1),
        "test_long_part_again.py": (1, 1, 0, 0),
        "test_long_part_skipped.py": (1, 1, 0, 1)}
    shown = witnesses["test_long_part_alone.py"]["failure_messages_without_the_check"]
    assert [message.startswith("Failed: DID NOT RAISE") for message in shown.values()] == [True]
    assert witnesses["test_long_part_skipped.py"]["failure_messages_without_the_check"] == {}
    text = (root / "out" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "| `test_long_part_skipped.py` | `core.decode#1` | no | 1 | 1 | 0 | 1 |" in text
    assert "- `test_long_part_alone.py`, `test_long_part_alone`: `Failed: DID NOT RAISE" in text
    records = json.loads((root / "work" / "records" / "witnesses.json").read_text(encoding="utf-8"))
    assert records["test_long_part_skipped.py"]["deleted"] == {
        "witness|_witness.test_long_part_skipped::test_long_part_skipped": "skipped"}
    # the record keeps the message of the failure: the input is accepted without the check
    kept = records["test_long_part_alone.py"]["deleted_failures"]
    assert list(kept) == ["witness|_witness.test_long_part_alone::test_long_part_alone"]
    assert list(kept.values())[0].startswith("Failed: DID NOT RAISE")  # the rest depends on the pytest version
    assert records["test_long_part_again.py"]["deleted_failures"] == {}
    assert records["test_long_part_alone.py"]["unmodified"] == {
        "witness|_witness.test_long_part_alone::test_long_part_alone": "passed"}
    assert records["test_long_part_alone.py"]["deleted"] == {
        "witness|_witness.test_long_part_alone::test_long_part_alone": "failed"}
    assert len(records["test_long_part_alone.py"]["sha256"]) == 64
    # the table across subjects reads the summary and decides the 5 expectations
    (root / "generated" / "gappy").mkdir(parents=True)
    shutil.copy2(root / "out" / "summary.json", root / "generated" / "gappy" / "summary.json")
    subprocess.run([sys.executable, "-I", str(E / "reach" / "report.py"), "--held-out", "gappy",
                    "--generated", str(root / "generated")], check=True, capture_output=True)
    report = json.loads((root / "generated" / "report.json").read_text(encoding="utf-8"))
    assert {k: (e["status"], e["counts"]) for k, e in report["subjects"]["gappy"]["expectations"].items()} == {
        "E1": ("held", "1 of 1"), "E2": ("not held", "0 of 1"), "E3": ("not held", "0 of 1"),
        "E4": ("not held", "0 of 1"), "E5": ("held", "1 of 1")}
    assert report["held_out_expectations"] == {
        "gappy": {"held": 2, "not held": 3, "not applicable": 0, "not stated": 0, "no verdict": 0}}
    assert report["sentinels_that_do_not_hold"] == {}
    text = (root / "generated" / "REPORT.md").read_text(encoding="utf-8")
    assert "| E3 | The whole suite detects every deletion of a deciding check. | not held (0 of 1) |" in text
    assert "- gappy: held 2, not held 3, not applicable 0, not stated 0, no verdict 0" in text



# -- the rules that the runner and the analysis share --------------------------------


def toy(name: str, package: str, core: str, tests: str, base: str):
    """A synthetic library under work/<name>: (root, clone, subject path, run command, common arguments)."""
    root = E / "work" / name
    if root.exists():
        shutil.rmtree(root)
    clone = root / "clone"
    (clone / package).mkdir(parents=True)
    (clone / "tests").mkdir()
    (clone / package / "__init__.py").write_text("", encoding="utf-8")
    (clone / package / "core.py").write_text(core, encoding="utf-8")
    (clone / "tests" / f"test_{package}.py").write_text(tests, encoding="utf-8")
    (clone / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (root / "defs").mkdir()
    subject = {"name": package, "version": "0", "repository": None, "commit": None,
               "distribution": f"{package}-fixture", "package": package, "source_root": ".",
               "subject_files": [f"{package}/core.py"], "observed_files": [], "entry_points": ["decode"],
               "rejection_bases": [base], "tests": ["tests"],
               "pytest_args": ["-p", "no:cacheprovider"], "copy": [package, "tests", "pyproject.toml"],
               "python": sys.version.split()[0], "suite_runs": [{"name": "all", "paths": ["tests"]}]}
    path = root / "defs" / "subject.json"
    path.write_text(json.dumps(subject), encoding="utf-8")
    run = [sys.executable, "-I", str(E / "reach" / "run.py")]
    common = ["--subject", str(path), "--work", str(root / "work")]
    return root, clone, path, run, common


def analysis(root: Path, common: list[str], out: str):
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py")] + common +
                          ["--out", str(root / out)], capture_output=True, text=True)
    return proc, json.loads((root / out / "summary.json").read_text(encoding="utf-8"))


def failing(summary: dict) -> list[str]:
    return [s["name"] for s in summary["sentinels"] if not s["pass"]]


def test_interpreter_problem():
    """`verify` asks for CPython in the version of the subject, not for the version number alone."""
    assert interpreter_problem("CPython 3.12.3", "3.12.3") is None
    assert interpreter_problem("CPython 3.12.3", None) is None
    assert interpreter_problem("PyPy 3.12.3", "3.12.3") == "the interpreter is PyPy 3.12.3, not CPython 3.12.3"
    assert interpreter_problem("CPython 3.12.4", "3.12.3") == "the interpreter is CPython 3.12.4, not CPython 3.12.3"
    assert interpreter_problem("", "3.12.3") == "the interpreter is unknown, not CPython 3.12.3"
    reported = subprocess.run([sys.executable, "-I", "-c", INTERPRETER_PROBE], capture_output=True,
                              text=True, check=True).stdout.strip()
    assert reported == f"{platform.python_implementation()} {sys.version.split()[0]}"


def test_study_predicate():
    def case(**fields):
        return dict({"test": "t.py::test_a", "block": "t.py::test_a#0", "index": 0, "included": True,
                     "raised": True, "check_result": "accepted", "rejection": True,
                     "class": "pkg.Rejected", "site": {"check": "core.f#1"}, "fired": ["core.g#1", "core.f#1"]},
                    **fields)
    assert left_out_reason(case()) is None
    assert left_out_reason(case(raised=False)) == "no exception"
    assert left_out_reason(case(check_result="failed")) == "the block does not accept the exception (failed)"
    assert left_out_reason(case(rejection=False)) == "not a rejection class (pkg.Rejected)"
    assert firing(case()) == {"core.f#1", "core.g#1"}
    assert firing(case(site=None, fired=["core.g#1"])) == {"core.g#1"}
    assert firing(case(site={"check": None}, fired=None)) == set()
    record = {"cases": [
        case(),
        case(index=1, check_result="failed", site={"check": "core.h#1"}, fired=["core.h#1"]),  # left out
        case(index=2, included=False, site={"check": "core.k#1"}, fired=["core.k#1"]),         # not included
        case(index=3, site=None, fired=["core.m#1"])]}
    assert sorted(study_cases(record)) == ["t.py::test_a|t.py::test_a#0|0", "t.py::test_a|t.py::test_a#0|3"]
    # a check that fires only in a case that is left out, or only in a block that is not included, is not deleted
    assert firing_checks(record) == {"core.f#1", "core.g#1", "core.m#1"}


def test_status_of_a_case_that_did_not_run():
    def run(**test):
        return Run({"cases": [], "tests": [dict({"nodeid": "t"}, **test)]})
    passed = {"outcome": "passed", "stop": None, "stop_is_assertion": None}
    assertion = {"outcome": "failed", "stop": "AssertionError", "stop_is_assertion": True}
    crash = {"outcome": "failed", "stop": "TypeError", "stop_is_assertion": False}
    skip = {"outcome": "skipped", "stop": "Skipped", "stop_is_assertion": False}
    block = [{"block": "t#0", "result": "failed"}]
    status = lambda **test: run(**test).status("t|t#1|0", "t")  # noqa: E731
    assert Run({"cases": [], "tests": []}).status("t|t#1|0", "t") == "crashed"       # no record of the test
    assert status(setup=passed, call=passed) == "missing"                              # ended without the case
    assert status(setup=passed, call=assertion) == "withheld"
    assert status(setup=passed, call=crash) == "crashed"
    assert status(setup=assertion) == "withheld"                                       # a fixture's assertion
    assert status(setup=crash) == "crashed"
    assert status(setup={}) == "crashed"                                               # the run died in the setup
    assert status(setup=passed, call=skip) == "missing"                                # a skip is no failure
    assert status(setup=skip) == "missing"
    assert status(setup=passed, call=passed, failed_blocks=block) == "missing"
    assert status(setup=passed, call=crash, failed_blocks=block) == "withheld"
    assert status(setup=passed, call=skip, failed_blocks=block) == "withheld"
    # failed subtests: a subtest ends its own body and the test goes on, so the
    # test's own call has no stop (the subtests fixture turns its outcome into failed)
    asserted = {"stop": "builtins.AssertionError", "stop_is_assertion": True}
    crashed = {"stop": "builtins.KeyError", "stop_is_assertion": False}
    unnamed = {"stop": None, "stop_is_assertion": None}
    turned = {"outcome": "failed", "stop": None, "stop_is_assertion": None}
    sub = lambda *stops, **test: status(subtests_failed=len(stops), subtest_stops=list(stops), **test)  # noqa: E731
    assert sub(crashed, setup=passed, call=passed) == "crashed"
    assert sub(crashed, crashed, setup=passed, call=turned) == "crashed"
    assert sub(asserted, setup=passed, call=passed) == "withheld"
    assert sub(crashed, asserted, setup=passed, call=turned) == "withheld"
    assert sub(unnamed, setup=passed, call=passed) == "withheld"
    assert status(setup=passed, call=passed, subtests_failed=1) == "withheld"          # a record without the stops
    assert sub(crashed, setup=passed, call=assertion) == "withheld"                    # the test's own stop decides
    assert sub(asserted, setup=passed, call=crash) == "crashed"
    assert sub(crashed, setup=passed, call=skip) == "crashed"                          # a failed subtest, then a skip
    assert sub(asserted, setup=passed, call=skip) == "withheld"
    assert sub(crashed, setup=passed, call=passed, failed_blocks=block) == "withheld"
    # the test's own outcome: a failed block or a failed subtest is a failure
    assert run(setup=passed, call=passed, teardown=passed).passed("t")
    assert not run(setup=passed, call=passed, failed_blocks=block).passed("t")
    assert not run(setup=passed, call=passed, subtests_failed=1).passed("t")
    assert not run(setup=passed, call=passed, subtests_failed=1).ok("t")
    assert run(setup=passed, call=passed, subtests_failed=0).passed("t")
    assert run(setup=passed, call=skip).ok("t") and not run(setup=passed, call=skip).passed("t")


def test_expectation_rules():
    base = {"not detected, deciding checks": {"O_V": 2, "whole suite": 0},
            "deletions of deciding checks": 5, "cases with a target": 4,
            "outcomes": {"decided by the target": 3}, "deciding checks: O_C detects and O_V does not": 1,
            "pinning": {"class-only cases": 6, "class-only, test passes": 0},
            "included blocks": 10, "included blocks, class-only": 9}
    e = expectations(base)
    assert {k: v["status"] for k, v in e.items()} == {
        "E1": "held", "E2": "held", "E3": "held", "E4": "held", "E5": "not held"}
    assert (e["E1"]["counts"], e["E3"]["counts"], e["E4"]["counts"], e["E5"]["counts"]) == (
        "2 of 5", "5 of 5", "1 of 4", "0 of 6")
    # E5 is stated when at least 9 of every 10 included blocks assert the class alone
    assert e5_stated(base) and not e5_stated(dict(base, **{"included blocks, class-only": 8}))
    assert e5_stated({"included blocks": 73, "included blocks, class-only": 66})
    assert not e5_stated({"included blocks": 73, "included blocks, class-only": 65})
    assert not e5_stated({"included blocks": 0, "included blocks, class-only": 0})
    not_stated = expectations(dict(base, **{"included blocks, class-only": 8}))["E5"]
    assert not_stated == {"status": "not stated", "counts": "8 of 10 included blocks assert the class alone"}
    # an expectation with 0 units to decide on is not applicable
    empty = expectations(dict(base, **{"deletions of deciding checks": 0, "cases with a target": 0,
                                       "not detected, deciding checks": {"O_V": 0, "whole suite": 0},
                                       "deciding checks: O_C detects and O_V does not": 0,
                                       "outcomes": {"decided by the target": 0},
                                       "pinning": {"class-only cases": 0, "class-only, test passes": 0}}))
    assert {v["status"] for v in empty.values()} == {"not applicable"}
    # a subject in which a sentinel does not hold gets no verdict on any expectation
    held = [{"name": f"sentinel {i}", "pass": True} for i in range(1, 8)]
    assert sentinels_not_holding({"sentinels": held}) == []
    broken = [dict(s, **{"pass": s["name"] not in ("sentinel 2", "sentinel 4")}) for s in held]
    against = sentinels_not_holding({"sentinels": broken})
    assert against == ["2: sentinel 2", "4: sentinel 4"]
    assert expectations(base, against) == {
        k: {"status": "no verdict", "counts": "sentinels 2, 4 do not hold"} for k in ("E1", "E2", "E3", "E4", "E5")}
    assert expectations(base, against[1:])["E3"] == {"status": "no verdict", "counts": "sentinel 4 does not hold"}
    short = sentinels_not_holding({"sentinels": held[:6]})
    assert short == ["the summary holds 6 sentinels, not 7"]
    assert expectations(base, short)["E1"] == {"status": "no verdict", "counts": short[0]}


def test_junit_outcome_of_a_failed_subtest(tmp_path):
    """Without the recorder, a test whose subtest fails does not count as passed."""
    if int(pytest.__version__.split(".")[0]) < 9:
        pytest.skip("subtests are part of pytest from version 9")
    (tmp_path / "test_sub.py").write_text('''
import unittest


def test_fixture_fails(subtests):
    for i in range(3):
        with subtests.test(i=i):
            assert i != 1


def test_fixture_passes(subtests):
    for i in range(3):
        with subtests.test(i=i):
            assert i < 3


class TestCase(unittest.TestCase):
    def test_method_fails(self):
        for i in range(3):
            with self.subTest(i=i):
                self.assertNotEqual(i, 1)

    def test_method_passes(self):
        for i in range(3):
            with self.subTest(i=i):
                self.assertLess(i, 3)
''', encoding="utf-8")
    xml = tmp_path / "out.xml"
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir=.",
                    f"--junitxml={xml}", "test_sub.py"], cwd=tmp_path, capture_output=True, text=True)
    assert junit_outcomes(xml, "all") == {
        "all|test_sub::test_fixture_fails": "failed", "all|test_sub::test_fixture_passes": "passed",
        "all|test_sub.TestCase::test_method_fails": "failed",
        "all|test_sub.TestCase::test_method_passes": "passed"}


class FakeContext:
    """What whole_run reads of a Context."""

    def __init__(self, root: Path, runs: list[dict]) -> None:
        self.subject = {"suite_runs": runs, "pytest_args": ["-p", "no:cacheprovider"]}
        self.records = root / "records"
        self.python = Path(sys.executable)
        self.entries: list[dict] = []

    def pythonpath(self, copy: Path, recorder: bool) -> str:
        return str(GUARD)

    def env(self, **extra: str) -> dict[str, str]:
        return dict(os.environ, **extra)

    def timing(self, entry: dict) -> None:
        self.entries.append(entry)


def test_whole_suite_limit_is_for_all_suite_runs(tmp_path):
    """2 suite runs of 1.5 s each under a limit of 2.5 s: the second gets what the first left."""
    for name in ("a", "b"):
        (tmp_path / name).mkdir()
        (tmp_path / name / f"test_{name}.py").write_text(
            "import time\n\n\ndef test_slow():\n    time.sleep(1.5)\n", encoding="utf-8")
    runs = [{"name": "a", "paths": ["a"]}, {"name": "b", "paths": ["b"]}]
    ctx = FakeContext(tmp_path, runs)
    result = whole_run(ctx, "unit", tmp_path, timeout=2.5)
    assert result["timed_out"] is True and result["seconds"] < 4.5
    assert "b|b.test_b::test_slow" not in result["outcomes"]
    result = whole_run(ctx, "unit", tmp_path, timeout=60.0)
    assert result["timed_out"] is False
    assert result["outcomes"] == {"a|a.test_a::test_slow": "passed", "b|b.test_b::test_slow": "passed"}
    assert result["refused"] == {"attempts": 0, "tests": {}}


LATE_CORE = '''
class LateError(Exception):
    pass


def decode(parts):
    """The first part that passes; a rejection when none does."""
    for part in parts:
        try:
            return _check_part(part)
        except LateError:
            continue
    raise _rejection()


def _rejection():
    return LateError("no part accepted")


def _check_part(part):
    if len(part) > 4:
        raise LateError("part too long")
    return part
'''

LATE_TESTS = '''
import pytest
from latey.core import LateError, decode


def test_accepts():
    assert decode(["toolong", "ok"]) == "ok"


def test_part_too_long():
    with pytest.raises(LateError):
        decode(["toolong"])
'''


def test_target_fires_and_no_check_decides():
    """The check a test describes fires, a handler drops its exception, and a raise
    statement that is no check rejects: the 4th outcome of a case with a target. The
    same library shows what the steps refuse: an analysis without the whole suite,
    definitions of another subject.json, records of an earlier run."""
    root, clone, path, run, common = toy("unit-tests-late", "latey", LATE_CORE, LATE_TESTS, "LateError")
    where = ["--clone", str(clone), "--python", sys.executable]
    subprocess.run(run + ["define", "targets", "verify", "baseline", "deletions"] + common + where,
                   check=True, capture_output=True)
    records = root / "work" / "records"
    # without the records of the whole suite a sentinel fails, the table of undetected
    # deletions is empty and the report across subjects refuses the summary
    proc, early = analysis(root, common, "out-early")
    assert proc.returncode == 1
    assert [i for i, s in enumerate(early["sentinels"], 1) if not s["pass"]] == [6]
    assert failing(early) == ["the whole suite ran on every deletion copy, and on the control copy it ends "
                              "with its results and loses no test that passes in both unmodified runs"]
    assert "whole suite" not in early["lists"]["deletions_not_detected"]
    assert (root / "out-early" / "undetected.csv").read_text(encoding="utf-8").count("\n") == 1
    (root / "generated" / "latey").mkdir(parents=True)
    shutil.copy2(root / "out-early" / "summary.json", root / "generated" / "latey" / "summary.json")
    report = subprocess.run([sys.executable, "-I", str(E / "reach" / "report.py"), "--held-out", "latey",
                             "--generated", str(root / "generated")], capture_output=True, text=True)
    assert report.returncode != 0 and "no records of the whole suite" in report.stderr
    # definitions that were written from another subject.json are refused
    subject = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(dict(subject, entry_points=["decode", "other"])), encoding="utf-8")
    proc = subprocess.run(run + ["verify"] + common + where, capture_output=True, text=True)
    assert proc.returncode != 0 and "another subject.json" in proc.stderr
    path.write_text(json.dumps(subject), encoding="utf-8")
    subprocess.run(run + ["verify", "whole-baseline", "whole-deletions"] + common + where,
                   check=True, capture_output=True)
    # a record that no step names is not packed, and the deletion step removes what an earlier one left
    (records / "stray.json").write_text("{}", encoding="utf-8")
    (records / "deletions" / "stale-9.json").write_text("{}", encoding="utf-8")
    subprocess.run(run + ["pack"] + common + ["--out", str(root / "pack")], check=True, capture_output=True)
    with tarfile.open(root / "pack" / "records.tar.xz") as tar:
        names = sorted(tar.getnames())
    assert names == ["records/base-1.json", "records/base-2.json", "records/deletions/_control.json",
                     "records/deletions/core._check_part-1.json", "records/deletions/manifest.json",
                     "records/deletions/no-record.json", "records/deletions/refused.json",
                     "records/deletions/repeated.json",
                     "records/refused.json", "records/suite.json", "records/timeout.json",
                     "records/whole/base.json", "records/whole/deletions.json"]
    subprocess.run(run + ["deletions"] + common + where, check=True, capture_output=True)
    assert not (records / "deletions" / "stale-9.json").exists()
    (records / "stray.json").unlink()
    proc, summary = analysis(root, common, "out")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert failing(summary) == [] and len(summary["sentinels"]) == 7
    counts = summary["counts"]
    assert (counts["cases"], counts["cases_with_target"], counts["cases_reaching_target"],
            counts["cases_target_fires"], counts["flags"]) == (1, 1, 0, 1, 1)
    assert counts["cases_with_target_by_outcome"] == {
        "the target fires and no check decides": 1,
        "the target fires and no check decides; own test without the target: fails": 1}
    assert (counts["checks_deciding"], counts["checks_firing"], counts["deletions"]) == (0, 1, 1)
    with (root / "out" / "flags.csv").open(encoding="utf-8") as handle:
        flags = list(csv.DictReader(handle))
    assert [(f["target"], f["target_fired"]) for f in flags] == [("core._check_part#1", "yes")]
    assert flags[0]["deciding_check"].startswith("other raise")
    # the lists of the sensitivity analysis are split as the main ones are
    assert summary["lists"]["deletions_not_detected_withheld_as_failing"] == {
        "O_V": [], "O_Vfc": [], "O_C": [], "O_T": ["core._check_part#1"]}
    assert counts["deletions_not_detected_withheld_as_failing_of_deciding_checks"] == {
        "O_V": 0, "O_Vfc": 0, "O_C": 0, "O_T": 0}
    # the report: no deciding check was deleted, so E1 to E3 have 0 units
    shutil.copy2(root / "out" / "summary.json", root / "generated" / "latey" / "summary.json")
    subprocess.run([sys.executable, "-I", str(E / "reach" / "report.py"), "--held-out", "latey",
                    "--generated", str(root / "generated")], check=True, capture_output=True)
    report = json.loads((root / "generated" / "report.json").read_text(encoding="utf-8"))
    assert {k: e["status"] for k, e in report["subjects"]["latey"]["expectations"].items()} == {
        "E1": "not applicable", "E2": "not applicable", "E3": "not applicable", "E4": "held",
        "E5": "not applicable"}
    assert report["subjects"]["latey"]["facts"]["outcomes"]["the target fires and no check decides"] == 1
    # without targets.json the analysis stops and writes nothing
    shutil.copytree(root / "defs", root / "defs-2")
    (root / "defs-2" / "targets.json").unlink()
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py")] + common +
                          ["--defs", str(root / "defs-2"), "--out", str(root / "out-none")],
                          capture_output=True, text=True)
    assert proc.returncode != 0 and "targets.json" in proc.stderr and not (root / "out-none").exists()
    # the control copy gave no record 2 times: `pack` packs the other records, and the
    # analysis of the packed records writes its outputs and names the reason in sentinel 1
    (records / "deletions" / "_control.json").unlink()
    (records / "deletions" / "no-record.json").write_text(json.dumps(
        {"_control": {"timed_out": [True, True], "returncode": [None, None]}}), encoding="utf-8")
    subprocess.run(run + ["pack"] + common + ["--out", str(root / "pack-2")], check=True, capture_output=True)
    with tarfile.open(root / "pack-2" / "records.tar.xz") as tar:
        names = sorted(tar.getnames())
        tar.extractall(root / "unpacked", filter="data")
    assert "records/deletions/_control.json" not in names
    assert "records/deletions/no-record.json" in names and "records/deletions/core._check_part-1.json" in names
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "analyse.py"), "--subject", str(path),
                           "--work", str(root / "unpacked"), "--out", str(root / "out-control")],
                          capture_output=True, text=True)
    assert proc.returncode == 1
    lost = json.loads((root / "out-control" / "summary.json").read_text(encoding="utf-8"))["sentinels"]
    assert [(i, s["detail"]) for i, s in enumerate(lost, 1) if not s["pass"]] == [
        (1, "the control copy gave no record")]
    # a record that a step must have written and that no-record.json does not name is still an error
    (records / "deletions" / "no-record.json").write_text("{}", encoding="utf-8")
    proc = subprocess.run(run + ["pack"] + common + ["--out", str(root / "pack-3")], capture_output=True, text=True)
    assert proc.returncode != 0 and "records absent: ['deletions/_control.json']" in proc.stderr


MARK_CORE = '''
class MarkError(Exception):
    pass


def decode(part):
    if part == "odd":
        raise MarkError("part is odd")
    if len(part) > 4:
        raise MarkError("part too long")
    return part
'''

MARK_TESTS = '''
import pytest
from markey.core import MarkError, decode


def test_accepts():
    assert decode("ok") == "ok"


def test_part_too_long():
    with pytest.raises(MarkError):
        decode("toolong")


@pytest.mark.xfail
def test_odd_part():
    with pytest.raises(MarkError, match="never said"):
        decode("odd")
'''


def test_case_left_out_gives_no_deletion():
    """A block that does not accept its exception at baseline gives no case of the
    study, and a check that fires in that block alone is not deleted. Such a block
    passes only in a test with an expected-failure mark; the toolkit has no rule
    for that mark, and the sentinel on the baseline outcomes stops the analysis."""
    root, clone, path, run, common = toy("unit-tests-mark", "markey", MARK_CORE, MARK_TESTS, "MarkError")
    subprocess.run(run + ["define", "targets", "baseline", "deletions", "whole-baseline",
                          "whole-deletions"] + common + ["--clone", str(clone), "--python", sys.executable],
                   check=True, capture_output=True)
    records = root / "work" / "records"
    base = json.loads((records / "base-1.json").read_text(encoding="utf-8"))
    odd = [c for c in base["cases"] if c["block"].endswith("test_odd_part#0")][0]
    assert (odd["included"], odd["raised"], odd["check_result"], odd["fired"]) == (
        True, True, "assertion", ["core.decode#1"])   # the pattern does not match
    manifest = json.loads((records / "deletions" / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(manifest) == ["core.decode#2"]
    proc, summary = analysis(root, common, "out")
    assert proc.returncode == 1
    assert [i for i, s in enumerate(summary["sentinels"], 1) if not s["pass"]] == [2]
    assert failing(summary) == ["in the baseline recorder run every test passes or is skipped, every test "
                                "file is collected, and the tests deselected are the expected baseline "
                                "failures"]
    counts = summary["counts"]
    assert (counts["cases_of_included_blocks"], counts["cases_left_out"], counts["cases"]) == (2, 1, 1)
    assert counts["cases_left_out_by_reason"] == {"the block does not accept the exception": 1}
    assert (counts["checks_firing"], counts["deletions"]) == (1, 1)


NET_CORE = '''
class NetError(Exception):
    pass


def decode(part):
    if len(part) > 4:
        raise NetError("part too long")
    return part
'''

NET_TESTS = '''
import socket

import pytest
from netty.core import NetError, decode


def test_accepts():
    assert decode("ok") == "ok"


def test_part_too_long():
    with pytest.raises(NetError):
        decode("toolong")


def test_lookup():
    with pytest.raises(OSError):
        socket.getaddrinfo("name.invalid", 80)
    socket.getaddrinfo("localhost", 80)


def test_connect():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(OSError):
            sock.connect(("192.0.2.1", 9))
        with pytest.raises(OSError):
            sock.connect_ex(("192.0.2.1", 9))
        sock.connect_ex(("127.0.0.1", 9))
'''


def test_outside_connections_are_refused_and_counted():
    """Every pytest call of the study loads the offline module: a connection attempt
    to an address that is not a loopback address, or a lookup of a host name, is
    refused, and the number of attempts is in the records of every kind of run."""
    root, clone, path, run, common = toy("unit-tests-net", "netty", NET_CORE, NET_TESTS, "NetError")
    subprocess.run(run + ["define", "targets", "baseline", "deletions", "whole-baseline",
                          "whole-deletions", "pack"] + common +
                   ["--clone", str(clone), "--python", sys.executable, "--out", str(root / "pack")],
                   check=True, capture_output=True)
    records = root / "work" / "records"

    def read(name: str):
        return json.loads((records / name).read_text(encoding="utf-8"))

    tests = {"tests/test_netty.py::test_connect": 2, "tests/test_netty.py::test_lookup": 1}
    count = {"attempts": 3, "tests": tests}
    whole_count = {"attempts": 3, "tests": {f"all|{k}": v for k, v in tests.items()}}
    assert read("suite.json")["summary"] == "4 passed"
    assert read("suite.json")["refused"] == count
    assert read("refused.json") == {"base-1": count, "base-2": count}
    assert read("deletions/refused.json") == {"_control": count, "core.decode#1": count}
    assert read("whole/base.json")["refused"] == [whole_count, whole_count]
    assert {k: v["refused"] for k, v in read("whole/deletions.json").items()} == {
        "_control": whole_count, "core.decode#1": whole_count}
    assert not list(records.rglob("*.offline.tmp"))
    with tarfile.open(root / "pack" / "records.tar.xz") as tar:
        names = tar.getnames()
    assert "records/refused.json" in names and "records/deletions/refused.json" in names
    proc, summary = analysis(root, common, "out")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert summary["refused_connection_attempts"] == {
        "suite_run": 3, "baseline_recorder_runs": [3, 3],
        "deletion_recorder_runs": {"runs": 2, "runs_without_a_count": 0, "runs_with_attempts": 2,
                                   "minimum": 3, "maximum": 3},
        "whole_suite_baseline_runs": [3, 3],
        "whole_suite_deletion_runs": {"runs": 2, "runs_without_a_count": 0, "runs_with_attempts": 2,
                                      "minimum": 3, "maximum": 3},
        "witness_runs": 0,
        "tests": sorted(list(tests) + [f"all|{k}" for k in tests])}
    text = (root / "out" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "suite run 3; recorder runs at baseline [3, 3]" in text
    assert "- `all|tests/test_netty.py::test_lookup`" in text


EXACT_CORE = '''
class ExactError(Exception):
    pass


def decode(text):
    if len(text) > 20:
        raise ExactError("part too long")
    return text.split(".")
'''

EXACT_TESTS = '''
import pytest
from exacty.core import ExactError, decode


def test_accepts():
    assert decode("ab.cd") == ["ab", "cd"]


def test_part():
    assert decode("ab") == ["no"]


def test_part_too_long():
    with pytest.raises(ExactError):
        decode("a" * 40)


@pytest.mark.parametrize("text", ["bad input", "bad input again"])
def test_text(text):
    assert text != "bad input"
    with pytest.raises(ExactError):
        decode("a" * 40)
'''

EXACT_BROKEN = '''
import module_that_is_not_there


def test_never_collected():
    assert module_that_is_not_there
'''


def test_expected_failures_are_deselected_by_their_exact_names():
    """A test that fails without the recorder is deselected by its exact node id: a
    test whose id begins with the same text, or shares it up to a space, stays. A
    test file that cannot be collected does not stop the run without the recorder.
    Without the records of the deletions, the sentinels on them do not hold."""
    root, clone, path, run, common = toy("unit-tests-exact", "exacty", EXACT_CORE, EXACT_TESTS, "ExactError")
    (clone / "tests" / "test_broken.py").write_text(EXACT_BROKEN, encoding="utf-8")
    where = ["--clone", str(clone), "--python", sys.executable]
    subprocess.run(run + ["define", "targets", "baseline"] + common + where, check=True, capture_output=True)
    records = root / "work" / "records"
    suite = json.loads((records / "suite.json").read_text(encoding="utf-8"))
    failures = ["tests/test_exacty.py::test_part", "tests/test_exacty.py::test_text[bad input]"]
    assert (suite["failures"], suite["not_collected"]) == (failures, ["tests/test_broken.py"])
    assert suite["summary"] == "2 failed, 3 passed, 1 error"
    base = json.loads((records / "base-1.json").read_text(encoding="utf-8"))
    assert base["deselected"] == failures and base["collect_errors"] == []
    kept = ["tests/test_exacty.py::test_accepts", "tests/test_exacty.py::test_part_too_long",
            "tests/test_exacty.py::test_text[bad input again]"]
    assert sorted(t["nodeid"] for t in base["tests"]) == kept
    assert sorted(c["test"] for c in base["cases"] if c["included"]) == kept[1:]
    proc, early = analysis(root, common, "out-early")
    assert proc.returncode == 1
    assert [i for i, s in enumerate(early["sentinels"], 1) if not s["pass"]] == [1, 3, 4, 6, 7]
    subprocess.run(run + ["deletions", "whole-baseline", "whole-deletions"] + common + where,
                   check=True, capture_output=True)
    proc, summary = analysis(root, common, "out")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert failing(summary) == [] and len(summary["sentinels"]) == 7
    assert summary["expected_baseline_failures"] == failures
    assert summary["test_files_not_collected"] == ["tests/test_broken.py"]
    assert (summary["counts"]["cases"], summary["counts"]["deletions"]) == (2, 1)
    assert summary["counts"]["deletions_not_detected"]["O_V"] == 0
    # a baseline record whose deselected tests are not the expected failures fails sentinel 2 alone
    for name in ("base-1.json", "base-2.json", "deletions/_control.json"):
        doc = json.loads((records / name).read_text(encoding="utf-8"))
        doc["deselected"] = failures[:1]
        (records / name).write_text(json.dumps(doc), encoding="utf-8")
    proc, odd = analysis(root, common, "out-2")
    assert proc.returncode == 1
    assert [i for i, s in enumerate(odd["sentinels"], 1) if not s["pass"]] == [2]


DIE_CORE = '''
class DieError(Exception):
    pass


def decode(text):
    if len(text) > 20:
        raise DieError("part too long")
    if not text:
        raise DieError("part empty")
    return text.split(".")
'''

DIE_TESTS = '''
import os
import sys

import pytest
from diey.core import DieError, decode

MARK = "died-here.txt"


def dies(under_recorder):
    # ends the interpreter at once, 1 time per copy, in the kind of run named
    if ("reach.recorder" in sys.modules) == under_recorder and not os.path.exists(MARK):
        open(MARK, "w").close()
        os._exit(7)


def test_accepts():
    assert decode("ab.cd") == ["ab", "cd"]


def test_part_too_long():
    with pytest.raises(DieError):
        decode("a" * 40)


def test_part_empty():
    with pytest.raises(DieError):
        decode("")


def test_long_part_ends_the_recorder_run():
    try:
        decode("a" * 40)
    except DieError:
        return
    dies(under_recorder=True)
    raise AssertionError("accepted")


def test_empty_part_ends_the_plain_run():
    try:
        decode("")
    except DieError:
        return
    dies(under_recorder=False)
    raise AssertionError("accepted")
'''


def test_a_run_without_result_is_repeated_on_a_fresh_copy():
    """A run that ends without its record, or a whole-suite run of which a pytest call
    leaves no result file, is repeated 1 time on a fresh copy. The test that ends the
    interpreter leaves a file in its copy and would not end it again there, so 2 ends
    show 2 copies. A recorder run without a record 2 times fails sentinel 4, and the
    report gives the library no verdict; a whole-suite run without result file 2 times
    counts as detected."""
    root, clone, path, run, common = toy("unit-tests-die", "diey", DIE_CORE, DIE_TESTS, "DieError")
    subprocess.run(run + ["define", "targets", "baseline", "deletions", "whole-baseline",
                          "whole-deletions", "pack"] + common +
                   ["--clone", str(clone), "--python", sys.executable, "--out", str(root / "pack")],
                   check=True, capture_output=True)
    records = root / "work" / "records"

    def read(name: str):
        return json.loads((records / name).read_text(encoding="utf-8"))

    assert sorted(read("deletions/manifest.json")) == ["core.decode#1", "core.decode#2"]
    assert read("deletions/no-record.json") == {
        "core.decode#1": {"returncode": [7, 7], "timed_out": [False, False]}}
    assert read("deletions/repeated.json") == {
        "core.decode#1": {"returncode": 7, "timed_out": False, "refused": None}}
    assert not (records / "deletions" / "core.decode-1.json").exists()
    whole = read("whole/deletions.json")
    assert {k: (v["detected"], v["runs"], v["timed_out"], v["no_result"]) for k, v in whole.items()} == {
        "_control": (False, 1, False, []), "core.decode#1": (True, 1, False, []),
        "core.decode#2": (True, 2, False, ["all"])}
    assert whole["core.decode#2"]["first_run"] == {"timed_out": False, "no_result": ["all"], "refused": None}
    assert (whole["core.decode#1"]["tests_not_passing"], whole["core.decode#2"]["tests_not_passing"]) == (2, 0)
    with tarfile.open(root / "pack" / "records.tar.xz") as tar:
        assert "records/deletions/repeated.json" in tar.getnames()
    proc, summary = analysis(root, common, "out")
    assert proc.returncode == 1
    assert [i for i, s in enumerate(summary["sentinels"], 1) if not s["pass"]] == [4]
    counts = summary["counts"]
    assert (counts["deletions"], counts["deletions_without_record"], counts["deletion_runs_repeated"],
            counts["deletions_time_limit"]) == (2, 1, 1, 0)
    assert summary["lists"]["deletions_without_record"] == ["core.decode#1"]
    assert summary["lists"]["deletion_runs_repeated"] == ["core.decode#1"]
    assert summary["whole_suite"]["deletions_no_result"] == ["core.decode#2"]
    assert summary["whole_suite"]["runs_repeated"] == ["core.decode#2"]
    assert summary["whole_suite"]["deletions_time_limit"] == []
    # the deletion without a record is in no list of undetected deletions, and its case is counted apart
    assert summary["lists"]["deletions_not_detected"]["O_V"] == []
    pin = counts["pinning"]
    assert (pin["cases"], pin["cases_not_counted_no_record"], pin["cases_not_counted_time_limit"],
            pin["cases_not_counted_no_deciding_check"], pin["cases_not_counted_deciding_check_not_deleted"]) == (
        1, 1, 0, 0, 0)
    assert rows(root / "out" / "deletions.csv")["core.decode#1"]["run"] == "no record"
    text = (root / "out" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "sentinel 4 does not hold): 1." in text
    assert "because the first run gave no record: `core.decode#1`." in text
    assert "(detected by the whole suite): `core.decode#2`." in text
    # the report: no verdict on any expectation
    (root / "generated" / "diey").mkdir(parents=True)
    shutil.copy2(root / "out" / "summary.json", root / "generated" / "diey" / "summary.json")
    proc = subprocess.run([sys.executable, "-I", str(E / "reach" / "report.py"), "--held-out", "diey",
                           "--generated", str(root / "generated")], capture_output=True, text=True)
    assert proc.returncode == 1
    report = json.loads((root / "generated" / "report.json").read_text(encoding="utf-8"))
    assert {k: (e["status"], e["counts"]) for k, e in report["subjects"]["diey"]["expectations"].items()} == {
        k: ("no verdict", "sentinel 4 does not hold") for k in ("E1", "E2", "E3", "E4", "E5")}
    assert report["held_out_expectations"] == {
        "diey": {"held": 0, "not held": 0, "not applicable": 0, "not stated": 0, "no verdict": 5}}
    text = (root / "generated" / "REPORT.md").read_text(encoding="utf-8")
    assert "| E3 | The whole suite detects every deletion of a deciding check. | no verdict (sentinel 4 " \
           "does not hold) |" in text
    assert ("Sentinels that do not hold: diey: 4: every deletion run gave a record or exceeded the time "
            "limit 2 times.") in text


def test_environment_and_clone_are_verified(tmp_path):
    """`verify` compares the packages of the interpreter with requirements.txt, and
    it refuses a clone whose copied paths hold a file that is not of the commit."""
    import importlib.metadata as metadata

    pins = sorted({f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions()
                   if d.metadata["Name"].lower() != "pip"})
    assert len(pins) > 1
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("# the environment\n\n" + "\n".join(pins) + "\n", encoding="utf-8")
    python = Path(sys.executable)
    assert environment_problems(python, requirements) == []
    requirements.write_text("\n".join(pins[1:]) + "\n", encoding="utf-8")
    name, version = pins[0].split("==")
    assert len(environment_problems(python, requirements)) == 1
    assert environment_problems(python, requirements)[0].endswith(
        f"=={version} is installed and not in requirements.txt")
    requirements.write_text("\n".join([f"{name}==0.0.0.1"] + pins[1:]) + "\n", encoding="utf-8")
    assert [p.split(";")[1] for p in environment_problems(python, requirements)] == [f" installed: {version}"]
    requirements.write_text("\n".join(pins + ["not-there-at-all==1", "loose>=2"]) + "\n", encoding="utf-8")
    assert environment_problems(python, requirements) == [
        "requirements.txt: `loose>=2` is no pin `name==version`",
        "requirements.txt pins not-there-at-all==1; installed: None"]

    root, clone, path, run, common = toy("unit-tests-verify", "exacty", EXACT_CORE, EXACT_TESTS, "ExactError")
    git = ["git", "-C", str(clone), "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid"]
    subprocess.run(git + ["init", "-q"], check=True, capture_output=True)
    subprocess.run(git + ["add", "--", "exacty", "tests", "pyproject.toml"], check=True, capture_output=True)
    subprocess.run(git + ["commit", "-q", "-m", "fixture"], check=True, capture_output=True)
    head = subprocess.run(git + ["rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    subject = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(dict(subject, commit=head)), encoding="utf-8")
    (root / "defs" / "requirements.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
    where = ["--clone", str(clone), "--python", sys.executable]

    def verify():
        return subprocess.run(run + ["verify"] + common + where, capture_output=True, text=True)

    subprocess.run(run + ["define"] + common + where, check=True, capture_output=True)
    assert verify().returncode == 0, verify().stderr
    # files that a copy leaves out, and files outside the copied paths, do not count
    (clone / "notes.txt").write_text("outside the copied paths\n", encoding="utf-8")
    (clone / "tests" / "__pycache__").mkdir()
    (clone / "tests" / "__pycache__" / "test_exacty.cpython-312.pyc").write_bytes(b"\0")
    assert verify().returncode == 0, verify().stderr
    # an untracked file of a copied path would be in every copy
    extra = clone / "exacty" / "extra.py"
    extra.write_text("VALUE = 1\n", encoding="utf-8")
    proc = verify()
    assert proc.returncode != 0 and "hold files that are not those of the commit: ?? exacty/extra.py" in proc.stderr
    extra.unlink()
    # so would a file that git ignores
    (clone / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (clone / "tests" / "debug.log").write_text("left by a run\n", encoding="utf-8")
    proc = verify()
    assert proc.returncode != 0 and "!! tests/debug.log" in proc.stderr
    (clone / "tests" / "debug.log").unlink()
    assert verify().returncode == 0
    # the environment is not the one of requirements.txt
    (root / "defs" / "requirements.txt").write_text("\n".join(pins[1:]) + "\n", encoding="utf-8")
    proc = verify()
    assert proc.returncode != 0 and "is installed and not in requirements.txt" in proc.stderr
