"""Unit and end-to-end tests of the trace part on the synthetic package in fixture/toytrace.

The package rejects with checks that the closure by name does not reach: a
method called through getattr with a computed name (`Checks.check_sig`) and a
function imported under another name (`check_expiry` as `_expiry`). It also
holds a generator consumed inside the entry point (`parts`) and 1 consumed
after the entry point returned (`lazy_parts`), a function run in another
thread (`threaded_check`), a recursive function (`walk`), coroutines run by
`asyncio.run` (`_acheck`, `_ainner`), a nested function (`decode.inner`), a
lambda, a property setter (`Box.value~2`), a method named like the entry
point (`Codec.decode`) and a function called both inside the entry point and,
after an exception unwound through it, directly (`util`).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

import analyse3
import rule3
import trace_run
from plugin import Tracer
from reach.blocks import enumerate_blocks
from reach.checks import enumerate_checks, load_json
from reach.targets import compute_targets

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture"
CLONE = FIXTURE / "toytrace"
TESTS = ["test_ok", "test_bad_signature", "test_expired_token", "test_empty_part", "test_too_deep",
         "test_negative_box", "test_async_rejected", "test_lazy_outside", "test_unwinding_then_direct_call",
         "test_codec_own_name", "test_thread", "test_environment_replaced"]


@pytest.fixture(scope="module")
def traced(tmp_path_factory):
    root = tmp_path_factory.mktemp("trace")
    defs = root / "defs"
    defs.mkdir()
    shutil.copyfile(FIXTURE / "subject.json", defs / "subject.json")
    subject = load_json(defs / "subject.json")
    checks = enumerate_checks(subject, CLONE)
    blocks = enumerate_blocks(subject, CLONE, checks)
    (defs / "checks.json").write_text(json.dumps(checks), encoding="utf-8")
    (defs / "blocks.json").write_text(json.dumps(blocks), encoding="utf-8")
    (defs / "targets.json").write_text(rule3.serialize(compute_targets(blocks, checks)), encoding="utf-8")
    base = root / "base.json"
    base.write_text(json.dumps({"passing": sorted(f"all|tests.test_toytrace::{t}" for t in TESTS),
                                "counts": {"passing in both": len(TESTS)}}), encoding="utf-8")
    out = root / "out"
    code = trace_run.main(["--subject", str(defs / "subject.json"), "--clone", str(CLONE),
                           "--python", sys.executable, "--work", str(root / "work"), "--out", str(out),
                           "--base", str(base), "--repeats", "2"])
    reach = load_json(out / "reach.json")
    return {"code": code, "reach": reach, "defs": defs, "out": out, "checks": checks, "blocks": blocks}


def fn(reach, file, function):
    rows = [f for f in reach["functions"] if f["file"] == file and f["function"] == function]
    return rows[0] if rows else None


def test_sentinels_hold(traced):
    assert traced["code"] == 0
    assert all(s["pass"] for s in traced["reach"]["sentinels"])
    assert traced["reach"]["outcomes"]["traced"] == {"passed": len(TESTS)}


def test_entry_point_itself_and_same_name_method(traced):
    r = traced["reach"]
    assert fn(r, "tracepkg/core.py", "decode")["entry_points"] == ["decode"]
    # a method named like the entry point counts as running under that name
    assert fn(r, "tracepkg/core.py", "Codec.decode")["entry_points"] == ["decode"]


def test_getattr_dispatch_and_alias(traced):
    r, checks = traced["reach"], {c["id"]: c for c in traced["checks"]["checks"]}
    assert not checks["core.Checks.check_sig#1"]["reachable"]
    assert not checks["helpers.check_expiry#1"]["reachable"]
    assert fn(r, "tracepkg/core.py", "Checks.check_sig")["entry_points"] == ["decode"]
    assert fn(r, "tracepkg/helpers.py", "check_expiry")["entry_points"] == ["decode"]


def test_generators(traced):
    r = traced["reach"]
    assert fn(r, "tracepkg/core.py", "parts")["entry_points"] == ["decode"]
    # created inside the entry point, first run after it returned
    lazy = fn(r, "tracepkg/helpers.py", "lazy_parts")
    assert lazy["entry_points"] == [] and lazy["starts"] == 1
    assert lazy["tests_under_none"] == ["tests/test_toytrace.py::test_lazy_outside"]


def test_thread(traced):
    t = fn(traced["reach"], "tracepkg/helpers.py", "threaded_check")
    # the entry point runs in the thread that started the worker, not in the worker
    assert t["entry_points"] == [] and t["starts_other_threads"] == t["starts"] > 0


def test_recursion(traced):
    w = fn(traced["reach"], "tracepkg/core.py", "walk")
    assert w["entry_points"] == ["decode"] and w["starts_under_none"] == 0
    assert w["starts"] > len(TESTS)


def test_coroutines(traced):
    r = traced["reach"]
    assert fn(r, "tracepkg/core.py", "_acheck")["entry_points"] == ["decode"]
    assert fn(r, "tracepkg/core.py", "_ainner")["entry_points"] == ["decode"]


def test_unwinding(traced):
    u = fn(traced["reach"], "tracepkg/helpers.py", "util")
    assert u["entry_points"] == ["decode"]
    # the direct calls of 2 tests: after an exception unwound through decode, and inside a
    # test that replaces os.environ.get; Codec.decode is itself an entry-point frame
    assert u["starts_under_none"] == 2
    assert u["tests_under_none"] == ["tests/test_toytrace.py::test_unwinding_then_direct_call",
                                     "tests/test_toytrace.py::test_environment_replaced"]


def test_plugin_leaves_replaced_functions_alone(traced):
    """The fixture holds a test that replaces os.environ.get and counts its calls: it passes
    under the plugin, and no recorded test id is the replaced value or empty inside a test."""
    r = traced["reach"]
    assert r["outcomes"]["traced"] == {"passed": len(TESTS)}
    ids = {t for f in r["functions"] for t in f["tests_under_none"]}
    ids |= {t for f in r["functions"] for t in f["first_test_per_entry_point"].values()}
    assert ids and all(t.startswith("tests/test_toytrace.py::test_") for t in ids)
    assert [s for s in r["sentinels"] if s["name"].startswith("T-files")][0]["pass"]


def test_nested_lambda_property(traced):
    r = traced["reach"]
    assert fn(r, "tracepkg/core.py", "decode.inner")["entry_points"] == ["decode"]
    assert fn(r, "tracepkg/core.py", "Box.value~2")["entry_points"] == ["decode"]
    assert fn(r, "tracepkg/core.py", "Box.value") is None  # the getter never runs
    lambdas = [u for u in r["unmapped"] if u["name"] == "<lambda>"]
    assert len(lambdas) == 1 and lambdas[0]["entry_points"] == ["decode"]
    assert lambdas[0]["reason"].startswith("a lambda")


def test_function_index_first_lines():
    subject = load_json(FIXTURE / "subject.json")
    index, other = trace_run.function_index(subject, CLONE, ["tracepkg/core.py", "tracepkg/helpers.py"])
    by_qual = {(k[0], v): k[1] for k, v in index.items()}
    src = (CLONE / "tracepkg" / "core.py").read_text().splitlines()
    # a decorated definition starts at its first decorator, as co_firstlineno does
    assert src[by_qual[("tracepkg/core.py", "Box.value")] - 1].strip() == "@property"
    assert src[by_qual[("tracepkg/core.py", "Box.value~2")] - 1].strip() == "@value.setter"
    assert any(k[2] == "looped" and "does not list" in v for k, v in other.items())


def test_rule3_targets(traced):
    out = traced["out"]
    code = rule3.main(["--subject", str(traced["defs"] / "subject.json"), "--out", str(out)])
    assert code == 0
    t2 = {b["key"].split("::", 1)[1]: b for b in load_json(traced["defs"] / "targets.json")["blocks"]}
    t3_doc = load_json(out / "targets.json")
    t3 = {b["key"].split("::", 1)[1]: b for b in t3_doc["blocks"]}
    assert t3_doc["rule_version"] == "reach-target-rule/3"
    assert t3_doc["variant"]["rule_code"] == "reach-target-rule/2"
    assert t2["test_bad_signature#0"]["target"] is None
    assert t2["test_bad_signature#0"]["reason"] == "no reachable check of the expected class"
    assert t3["test_bad_signature#0"]["target"] == "core.Checks.check_sig#1"
    assert t2["test_expired_token#0"]["target"] is None
    assert t3["test_expired_token#0"]["target"] == "helpers.check_expiry#1"
    # by name already: unchanged
    assert t2["test_negative_box#0"]["target"] == t3["test_negative_box#0"]["target"] == "core.Box.value~2#1"
    rows = (out / "checks-reachability.csv").read_text().splitlines()
    assert "core.Checks.check_sig#1,tracepkg/core.py,Checks.check_sig,subject,no,yes,yes,decode" in rows


def test_rule3_empty_set_is_rule2(traced):
    blocks, checks = traced["blocks"], traced["checks"]
    assert rule3.serialize(rule3.rule3_targets(blocks, checks, {})) == \
        (traced["defs"] / "targets.json").read_text(encoding="utf-8")
    # the widened copy changes only `reachable`, and leaves the input as it was
    before = json.dumps(checks, sort_keys=True)
    wide = rule3.widened(checks, {("tracepkg/core.py", "Checks.check_sig"): ["decode"]})
    assert json.dumps(checks, sort_keys=True) == before
    diff = [(a["id"], a["reachable"], b["reachable"]) for a, b in zip(checks["checks"], wide["checks"])
            if a != b]
    assert diff == [("core.Checks.check_sig#1", False, True)]


def test_tracer_in_process(tmp_path):
    """The callback on its own: a generator, recursion and a thread, without pytest."""
    pkg = tmp_path / "pkg.py"
    pkg.write_text(
        "import threading\n"
        "def verify(n):\n"
        "    return rec(n)\n"
        "def rec(n):\n"
        "    return 0 if n == 0 else rec(n - 1)\n"
        "def gen():\n"
        "    yield helper()\n"
        "def helper():\n"
        "    return 1\n"
        "def in_thread():\n"
        "    t = threading.Thread(target=helper)\n"
        "    t.start(); t.join()\n"
        "def verify_threaded():\n"
        "    in_thread()\n", encoding="utf-8")
    ns: dict = {}
    code = compile(pkg.read_text(), str(pkg), "exec")
    tracer = Tracer(str(tmp_path), ["pkg.py"], ["verify", "verify_threaded"])
    tracer.start()
    try:
        exec(code, ns)
        ns["verify"](2)
        g = ns["gen"]()
        next(g)                # first start outside any entry point
        ns["verify_threaded"]()
    finally:
        tracer.stop()
    doc = {c["qualname"]: c for c in tracer.document()["codes"]}
    assert doc["rec"]["entry_points"] == ["verify"] and doc["rec"]["starts"] == 3
    assert doc["gen"]["entry_points"] == []
    assert doc["helper"]["entry_points"] == [] and doc["helper"]["starts"] == 2
    assert doc["helper"]["starts_other_threads"] == 1
    assert doc["in_thread"]["entry_points"] == ["verify_threaded"]
    assert "<module>" not in doc     # a module body is no function code


def test_transitions():
    assert analyse3.transition("", "") == "no target under either"
    assert analyse3.transition("", "a#1") == "gained a target"
    assert analyse3.transition("a#1", "") == "lost a target"
    assert analyse3.transition("a#1", "a#1") == "same target"
    assert analyse3.transition("a#1", "b#1") == "changed target"


def test_tier_counts():
    rows = [{"target_rule2": "a", "tier_rule2": "name", "decides_rule2": "no"},
            {"target_rule2": "b", "tier_rule2": "assertion", "decides_rule2": "yes"},
            {"target_rule2": "", "tier_rule2": "", "decides_rule2": ""}]
    c = analyse3.tier_counts(rows, "2")
    assert c["all"] == {"cases_with_a_target": 2, "decided_by_the_target": 1, "not_decided_flags": 1}
    assert c["name"]["not_decided_flags"] == 1 and c["assertion"]["not_decided_flags"] == 0


def test_fired_functions(tmp_path):
    rec = tmp_path
    case = {"included": True, "fired": ["m.f#1"], "site": {"check": "m.g#1"}}
    for name in ("base-1.json", "base-2.json"):
        (rec / name).write_text(json.dumps({"cases": [case, {"included": False, "fired": ["m.h#1"]}]}))
    checks = {"checks": [{"id": "m.f#1", "file": "m.py", "function": "f"},
                         {"id": "m.g#1", "file": "m.py", "function": "g"},
                         {"id": "m.h#1", "file": "m.py", "function": "h"}]}
    reach = {"functions": [{"file": "m.py", "function": "f", "entry_points": ["v"], "starts_under_none": 0,
                            "starts": 1, "starts_other_threads": 0, "tests_under_none": []},
                           {"file": "m.py", "function": "g", "entry_points": [], "starts_under_none": 2,
                            "starts": 2, "starts_other_threads": 0, "tests_under_none": ["t::a"]}]}
    rows, ok, tally = analyse3.fired_functions("x", rec, checks, reach)
    assert ok and tally == {"started only under no entry point": 1, "under an entry point": 1}
    assert rows[1][0] == "m.g#1" and "t::a" in rows[1][-1]
    # a fired check whose function never started does not hold
    reach["functions"] = reach["functions"][:1]
    _, ok, tally = analyse3.fired_functions("x", rec, checks, reach)
    assert not ok and tally["function not started"] == 1
