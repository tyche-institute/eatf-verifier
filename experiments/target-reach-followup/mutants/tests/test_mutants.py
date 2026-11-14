"""Unit and end-to-end tests of materialize.py, run_mutants.py, analyse_mutants.py and at_check.py.

The end-to-end test uses the synthetic package of the toolkit
(../../target-reach/tests/fixture/toy, read only) as its subject, and needs an
interpreter in whose environment mutmut 3.8.1 is importable: the environment
of the reference study (../../mutation-adequacy-pyjwt/work/venv), or the one
that the variable MUTMUT_PYTHON names. Run the tests with an interpreter that
has pytest.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from analyse_mutants import case_detection, mutant_detection, parse_lines, score_counts, whole_killed
from at_check import as_expectations, attribution, check_span, expectations_under, part_of, spans_of
from common import DELETION, EXPERIMENT, REFERENCE, TOOLKIT, functions, junit_key, read_packed, split_lines
from materialize import Problem, deletion_mutants, place
from reach.analyse import Run, oracles

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
FIXTURE = TOOLKIT / "tests" / "fixture"
CLONE = FIXTURE / "toy"
WORK = EXPERIMENT / "work" / "mutants" / "unit-tests"
MUTMUT_PYTHON = Path(os.environ.get("MUTMUT_PYTHON", REFERENCE / "work" / "venv" / "bin" / "python"))


# -- placing a mutated function ----------------------------------------------------------------------

def test_place_same_number_of_lines():
    o = "import os\n\ndef f(x):\n    return x + 1\n\nZ = 1\n"
    m = "import os\n\ndef f(x):\n    return x - 1\n\nZ = 1\n"
    text, changed, padding = place(o, m, 3, 4)
    assert text == m and changed == [4] and padding == 0


def test_place_pads_a_shorter_mutation_with_blank_lines():
    o = "def f():\n    y = g(1,\n          2)\n    return y\nZ = 1\n"
    m = "def f():\n    y = g(1, 3)\n    return y\nZ = 1\n"
    text, changed, padding = place(o, m, 1, 4)
    assert len(split_lines(text)) == len(split_lines(o)) and padding == 1
    assert split_lines(text)[3] == "    return y\n" and changed == [2, 3]
    compile(text, "x", "exec")


def test_place_continues_a_backslash_line():
    o = "def f():\n    y = a(1,\n          2) + \\\n        3\n    return y\n"
    m = "def f():\n    y = a(1, 2) - \\\n        3\n    return y\n"
    text, changed, padding = place(o, m, 1, 5)
    assert split_lines(text)[2] == "\\\n" and padding == 1 and changed == [2, 3]
    compile(text, "x", "exec")
    ns = {"a": lambda u, v: u + v}
    exec(text, ns)
    assert ns["f"]() == 0


def test_place_refuses_a_longer_mutation_and_a_change_outside():
    o = "def f():\n    return (1, 2)\n"
    m = "def f():\n    return (1,\n            3)\n"
    with pytest.raises(Problem):
        place(o, m, 1, 2)
    with pytest.raises(Problem):
        place("X = 1\ndef f():\n    return 1\n", "X = 2\ndef f():\n    return 2\n", 2, 3)


def test_split_lines_keeps_a_form_feed_inside_a_line():
    assert split_lines("a\x0cb\nc") == ["a\x0cb\n", "c"]


def test_junit_key():
    assert junit_key("tests/test_x.py::TestA::test_b[1-2]", "all") == "all|tests.test_x.TestA::test_b[1-2]"
    assert junit_key("pkg/tests.py::test_c", "run") == "run|pkg.tests::test_c"


def test_parse_lines():
    assert parse_lines("3;5-7") == [3, 5, 6, 7]


# -- deletions and the span of a check ---------------------------------------------------------------

GUARDS = '''\
class E(Exception):
    pass


def f(a, b):
    if (a > 1 and
            b > 2):
        raise E("first")
    if a:
        x = 1
    else:
        raise E(
            "second"
        )
    try:
        g(a)
    except (KeyError,
            ValueError) as err:
        raise E("third") from err
    for i in range(a):
        raise E("fourth")
    if b: raise E("fifth")
    raise E("sixth")
'''


def guard_checks():
    lines = {"f#1": [[8, 8]], "f#2": [[12, 14]], "f#3": [[19, 19]], "f#4": [[21, 21]], "f#5": [[22, 22]],
             "f#6": [[23, 23]]}
    return [{"id": cid, "file": "pkg/m.py", "function": "f", "lines": ls} for cid, ls in lines.items()]


def test_check_span():
    fn = functions(ast.parse(GUARDS))["f"]
    assert check_span(fn, [[8, 8]]) == {"raise": [8], "guard": [6, 7], "kinds": ["if"]}
    # a raise in the else part: the test of the same if
    assert check_span(fn, [[12, 14]]) == {"raise": [12, 13, 14], "guard": [9], "kinds": ["if"]}
    # an except clause: its header, to the end of the exception type
    assert check_span(fn, [[19, 19]]) == {"raise": [19], "guard": [17, 18], "kinds": ["except"]}
    # under a loop only, and under nothing: the raise lines alone
    assert check_span(fn, [[21, 21]]) == {"raise": [21], "guard": [], "kinds": []}
    assert check_span(fn, [[23, 23]]) == {"raise": [23], "guard": [], "kinds": []}
    # an if with its body on the same line
    assert check_span(fn, [[22, 22]]) == {"raise": [22], "guard": [22], "kinds": ["if"]}
    # a check of 2 raise statements
    assert check_span(fn, [[8, 8], [19, 19]]) == {"raise": [8, 19], "guard": [6, 7, 17, 18],
                                                  "kinds": ["except", "if"]}
    with pytest.raises(SystemExit):
        check_span(fn, [[9, 9]])


def test_part_of_and_attribution():
    span = {"raise": [8], "guard": [6, 7], "kinds": ["if"]}
    assert part_of([7], span) == "guard" and part_of([8], span) == "raise"
    assert part_of([7, 8], span) == "raise and guard" and part_of([9], span) is None
    checks = {c["id"]: c for c in guard_checks()}
    spans = spans_of(list(checks.values()), {"pkg/m.py": GUARDS})
    assert sorted(spans) == sorted(checks)
    rows = [{"mutant": "M00001", "file": "pkg/m.py", "operator": "x", "changed_lines": "7"},
            {"mutant": "M00002", "file": "pkg/m.py", "operator": "x", "changed_lines": "10"},
            {"mutant": "M00003", "file": "pkg/m.py", "operator": "x", "changed_lines": "22"},
            {"mutant": "M00004", "file": "pkg/other.py", "operator": "x", "changed_lines": "8"},
            {"mutant": "D00001", "file": "pkg/m.py", "operator": DELETION, "changed_lines": "12-14"}]
    assert attribution(rows, checks, spans) == [
        ["D00001", DELETION, "f#2", "raise"], ["M00001", "x", "f#1", "guard"],
        ["M00003", "x", "f#5", "raise and guard"]]


def test_deletion_mutants(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text(GUARDS, encoding="utf-8")
    subject = {"source_root": "."}
    rows, texts, problems, per_file = deletion_mutants(tmp_path, ["pkg/m.py"], subject, guard_checks())
    assert problems == [] and per_file == {"pkg/m.py": 6}
    assert [r["mutant"] for r in rows] == [f"D{n:05d}" for n in range(1, 7)]
    assert [r["check"] for r in rows] == ["f#1", "f#2", "f#3", "f#4", "f#5", "f#6"]
    assert [r["changed_lines"] for r in rows] == ["8", "12-14", "19", "21", "22", "23"]
    assert all(r["operator"] == DELETION and r["function_lines"] == "5-23" and r["mutated"] == "pass"
               for r in rows)
    assert rows[1]["original"] == 'raise E( "second" )'
    for mid, text in texts.items():
        assert len(split_lines(text)) == len(split_lines(GUARDS))
        compile(text, "m.py", "exec")
    assert split_lines(texts["D00002"])[11:14] == ["        pass\n", "\n", "\n"]
    assert split_lines(texts["D00005"])[21] == "    if b: pass\n"
    # a check whose raise statement is not where checks.json says fails S1
    wrong = [dict(guard_checks()[0], lines=[[9, 9]])]
    rows, texts, problems, _ = deletion_mutants(tmp_path, ["pkg/m.py"], subject, wrong)
    assert len(problems) == 1 and texts == {}


def entry(case, test, described, deciding, variant, tool, dl, dd, fires):
    """An entry of described-cases.json with the fields that the expectations read."""
    groups = ("described", "deciding", "described_not_deciding")
    return {"case": case, "test": test, "described_check": described, "deciding_check": deciding,
            "variant": variant, "described_fires_in_a_baseline_case": fires,
            "mutants": {g: dict(tool[g]) for g in groups}, "deletions": {"described": dl, "deciding": dd}}


def deletion(**flags):
    d = {"mutant": "D00001", "suite": False, "O_C": False, "O_S": False, "own": False, "unique": False,
         "variant": False}
    d.update(flags)
    return d


def test_expectations_under_the_2_readings():
    zero = {"unique": 0, "O_C": 0, "variant": 0}
    # row a: the variant kills only the deletion of the described check, which fires in no baseline case
    a = entry("a", "t::a", "c#2", "c#1", "v_a", {"described": zero, "deciding": zero, "described_not_deciding": zero},
              deletion(variant=True), deletion(unique=True), False)
    # row b: the variant kills 2 tool mutants at the described check; the case detects 1 under O_C
    b = entry("b", "t::b", "c#3", "c#1", "v_b",
              {"described": {"unique": 0, "O_C": 1, "variant": 2}, "deciding": zero,
               "described_not_deciding": {"unique": 0, "O_C": 1, "variant": 2}},
              deletion(suite=True, variant=True, O_C=True), deletion(), True)
    # row c: a comparison row, the described check decides the case
    c = entry("c", "t::c", "c#1", "c#1", None, {"described": zero, "deciding": zero, "described_not_deciding": zero},
              deletion(), deletion(), True)
    t = expectations_under([a, b, c], False)
    td = expectations_under([a, b, c], True)
    assert t["M1"] == {"unique_kills_at_the_deciding_check": {"a": 0, "b": 0}, "tests_with_at_least_1": [],
                       "status": "not held"}
    assert td["M1"] == {"unique_kills_at_the_deciding_check": {"a": 1, "b": 0}, "tests_with_at_least_1": ["t::a"],
                        "status": "held"}
    assert t["M2"]["O_C_detections_at_the_described_check_only"] == {"a": 0, "b": 1}
    assert td["M2"]["O_C_detections_at_the_described_check_only"] == {"a": 0, "b": 2}
    assert t["M2"]["status"] == td["M2"]["status"] == "not held"
    assert [r["case"] for r in t["M3"]["rows"]] == ["a", "b"]
    ra, rb = t["M3"]["rows"]
    assert (ra["variant_kills_at_the_described_check"], ra["first_sentence_holds"], ra["second_sentence_applies"],
            ra["second_sentence_holds"], ra["holds"]) == (0, False, True, True, False)
    assert (rb["variant_kills_at_the_described_check"], rb["second_sentence_applies"],
            rb["second_sentence_holds"], rb["holds"]) == (2, False, None, True)
    assert t["M3"]["status"] == "not held"
    ra, rb = td["M3"]["rows"]
    assert (ra["variant_kills_at_the_described_check"], ra["holds"]) == (1, True)
    assert (rb["variant_kills_at_the_described_check"], rb["holds"]) == (3, True)
    assert td["M3"]["status"] == "held"
    # the second sentence fails when the whole suite already kills the deletion
    a2 = dict(a, deletions={"described": deletion(variant=True, suite=True), "deciding": deletion()})
    assert expectations_under([a2], True)["M3"]["rows"][0]["holds"] is False
    # no row: not applicable
    none = expectations_under([c], True)
    assert [none[m]["status"] for m in ("M1", "M2", "M3")] == ["not applicable"] * 3
    assert as_expectations(td) == {
        "M1_tests_with_a_unique_kill_at_the_deciding_check": ["t::a"], "M1_cases": {"a": 1, "b": 0},
        "M2_cases_that_detect_a_mutant_at_the_described_check_only": ["b"],
        "M3_variants": [{"case": "a", "holds": True}, {"case": "b", "holds": True}]}


def test_m3_leaves_out_a_row_that_is_not_shadowed():
    zero = {"unique": 0, "O_C": 0, "variant": 0}
    # row d: the described check decides the case, and the row has a variant that kills a mutant at it
    d = entry("d", "t::d", "c#4", "c#4", "v_d",
              {"described": {"unique": 0, "O_C": 0, "variant": 1}, "deciding": zero, "described_not_deciding": zero},
              deletion(variant=True), deletion(), False)
    # row e: shadowed, with a variant that kills nothing at the described check
    e = entry("e", "t::e", "c#5", "c#1", "v_e", {"described": zero, "deciding": zero, "described_not_deciding": zero},
              deletion(suite=True), deletion(), True)
    for flag in (False, True):
        x = expectations_under([d, e], flag)
        assert [r["case"] for r in x["M3"]["rows"]] == ["e"] and x["M3"]["status"] == "not held"
        assert list(x["M1"]["unique_kills_at_the_deciding_check"]) == ["e"]
        assert list(x["M2"]["O_C_detections_at_the_described_check_only"]) == ["e"]
        alone = expectations_under([d], flag)
        assert alone["M3"] == {"rows": [], "status": "not applicable"}
    assert as_expectations(expectations_under([d, e], True))["M3_variants"] == [{"case": "e", "holds": False}]


# -- scoring -------------------------------------------------------------------------------------------

def record(cases, tests):
    return {"cases": cases, "tests": tests}


def case(test, raised=True, cls="E", check="c#1", rejection=True):
    return {"test": test, "block": f"{test}#0", "index": 0, "included": True, "raised": raised,
            "rejection": rejection, "class": cls, "site": {"check": check}, "check_result": "accepted"}


def passed(nodeid):
    return {"nodeid": nodeid, "setup": {"outcome": "passed"}, "call": {"outcome": "passed"}}


def failed(nodeid):
    return {"nodeid": nodeid, "setup": {"outcome": "passed"}, "call": {"outcome": "failed"}}


def test_case_detection_follows_the_deletion_rules():
    base = Run(record([case("t::a"), case("t::b")], [passed("t::a"), passed("t::b"), passed("t::c")]))
    key_a = "t::a|t::a#0|0"
    base_or = oracles(base.cases[key_a], base.cases[key_a], "c#1")
    # the check moves: O_T detects, O_V and O_C do not; the test still passes
    run = Run(record([case("t::a", check="c#2"), case("t::b")], [passed("t::a"), passed("t::b"), failed("t::c")]))
    d = case_detection("completed", run, base, key_a, base_or, "c#1")
    assert (d["status"], d["O_V"], d["O_C"], d["O_T"], d["O_S"]) == ("observed", False, False, True, False)
    m = mutant_detection("completed", run, base, sorted(base.cases), {
        k: case_detection("completed", run, base, k, oracles(base.cases[k], base.cases[k], "c#1"), "c#1")
        for k in base.cases})
    assert (m["O_T"], m["O_S"], m["suite"]) == (True, False, True)
    # the recorder run exceeded its limit 2 times: detected under every oracle
    d = case_detection("timeout", None, base, key_a, base_or, None)
    assert d["O_V"] and d["O_S"] and d["O_T"] is None
    # no record 2 times: no value
    d = case_detection("error", None, base, key_a, base_or, "c#1")
    assert d["O_V"] is None and d["status"] == "no record"


def test_whole_killed_and_score():
    assert whole_killed({"status": "timeout", "lost": []}) is True
    assert whole_killed({"status": "error", "lost": []}) is True
    assert whole_killed({"status": "completed", "lost": []}) is False
    s = score_counts({"M1": {"t1"}, "M2": set(), "M3": set(), "M4": set()},
                     {"M1": "completed", "M2": "completed", "M3": "timeout", "M4": "error"})
    assert (s["killed"], s["killed_by_a_test"], s["timeouts"], s["errors"], s["survived"]) == (3, 1, 1, 1, 1)


# -- end to end on the synthetic package -------------------------------------------------------------------

def rows(path):
    if not path.exists():
        return list(csv.DictReader(io.StringIO(read_packed(path))))
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run_ok(cmd, **kw):
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    return proc


@pytest.mark.skipif(not MUTMUT_PYTHON.exists(), reason="no interpreter with mutmut 3.8.1")
def test_end_to_end():
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "defs").mkdir(parents=True)
    shutil.copy(FIXTURE / "subject.json", WORK / "defs" / "subject.json")
    subject = str(WORK / "defs" / "subject.json")
    py = [sys.executable, "-I", "-B"]
    # the toolkit's own baseline of the synthetic package is the deposit for S3
    e_common = ["--subject", subject, "--work", str(WORK / "e-work")]
    run_ok(py + [str(TOOLKIT / "reach" / "run.py"), "define", "targets", "verify", "baseline",
                 "whole-baseline"] + e_common + ["--clone", str(CLONE), "--python", sys.executable])
    subprocess.run(py + [str(TOOLKIT / "reach" / "analyse.py")] + e_common + ["--out", str(WORK / "deposit")],
                   capture_output=True)
    shutil.copy(WORK / "e-work" / "records" / "whole" / "base.json", WORK / "deposit" / "whole-base.json")

    common = ["--subject", subject, "--clone", str(CLONE), "--work", str(WORK / "work")]
    out = WORK / "out"
    run_ok(py + [str(TOOLS / "materialize.py"), "--files", "toyverify/core.py", "--mutmut-python",
                 str(MUTMUT_PYTHON), "--out", str(out)] + common)
    every = rows(out / "mutants.csv")
    assert every and all(m["file"] == "toyverify/core.py" for m in every)
    mutants = [m for m in every if m["operator"] != DELETION]
    deletions = [m for m in every if m["operator"] == DELETION]
    materialized = json.loads((out / "materialize.json").read_text(encoding="utf-8"))
    assert all(s["pass"] for s in materialized["sentinels"])
    # 1 deletion per check of the file, each at the lines of its raise statements
    toy_checks = [c for c in json.loads((WORK / "defs" / "checks.json").read_text(encoding="utf-8"))["checks"]
                  if c["file"] == "toyverify/core.py"]
    assert len(deletions) == len(toy_checks) == materialized["check_deletions"] > 0
    assert sorted(d["check"] for d in deletions) == sorted(c["id"] for c in toy_checks)
    assert materialized["mutants"] == len(mutants) > 0
    run_ok(py + [str(TOOLS / "run_mutants.py"), "--python", sys.executable, "--workers", "4"] + common)
    analyse = py + [str(TOOLS / "analyse_mutants.py"), "--out", str(out), "--deposited", str(WORK / "deposit")] + common
    run_ok(analyse)
    score = json.loads((out / "score.json").read_text(encoding="utf-8"))
    assert all(s["pass"] for s in score["sentinels"]) and [s["name"] for s in score["sentinels"]] == [
        "S1", "S2", "S3", "S4"]
    w = score["whole_suite"]
    assert w["mutants"] == len(mutants) == w["killed"] + w["survived"]
    assert w["killed"] == w["killed_by_a_test"] + w["timeouts"] + w["errors"]
    dscore = score["check_deletions"]
    assert dscore["mutants"] == len(deletions) == dscore["killed"] + dscore["survived"]
    runs = [json.loads(x) for x in read_packed(out / "runs.jsonl").splitlines()]
    assert not (out / "runs.jsonl").exists() and not (out / "cases.csv").exists()
    assert [r["mutant"] for r in runs] == sorted(m["mutant"] for m in every)
    case_rows = rows(out / "cases.csv")
    assert len(case_rows) == len(every) * score["cases"]
    # every kill counted per test is a kill of the whole suite
    per_test = rows(out / "per-test.csv")
    tool_ids = {m["mutant"] for m in mutants}
    killers = {t for r in runs for t in r["whole_not_passing"]}
    assert {r["test"] for r in per_test} == killers
    assert sum(int(r["kills"]) for r in per_test) == sum(
        len(r["whole_not_passing"]) for r in runs if r["mutant"] in tool_ids)
    assert sum(int(r["check_deletions_killed"]) for r in per_test) == sum(
        len(r["whole_not_passing"]) for r in runs if r["mutant"] not in tool_ids)
    assert sum(int(r["unique_kills"]) for r in per_test) == score["mutants_killed_by_exactly_1_test"]
    # the deletion of a check that decides a case is detected by that case under O_T
    oracle_rows = {r["mutant"]: r for r in rows(out / "oracles.csv")}
    assert all(oracle_rows[d["mutant"]]["check"] == d["check"] for d in deletions)

    # deterministic: a second analysis writes the same files
    sums = (out / "SHA256SUMS").read_text(encoding="utf-8")
    run_ok(analyse)
    assert (out / "SHA256SUMS").read_text(encoding="utf-8") == sums

    # leaving out every killing test leaves only timeouts and errors killed
    (WORK / "all-killers.txt").write_text("\n".join(sorted(killers)) + "\n", encoding="utf-8")
    run_ok(analyse + ["--without-tests", f"@{WORK / 'all-killers.txt'}"])
    score = json.loads((out / "score.json").read_text(encoding="utf-8"))
    assert score["without_tests"]["killed"] == w["timeouts"] + w["errors"]

    # targets from a file override the target-dependent columns only
    keys = sorted({r["case"] for r in case_rows})
    (WORK / "targets.tsv").write_text("".join(f"{k}\t\n" for k in keys), encoding="utf-8")
    run_ok(analyse + ["--targets-file", str(WORK / "targets.tsv")])
    again = rows(out / "cases.csv")
    assert all(r["O_T"] in ("", "yes") for r in again)
    assert [(r["O_V"], r["O_S"]) for r in again] == [(r["O_V"], r["O_S"]) for r in case_rows]

    # extra tests: a third run per mutant; a test that always passes kills nothing
    extra = WORK / "extra"
    extra.mkdir()
    (extra / "test_more.py").write_text(
        "from toyverify.core import decode\n\n\ndef test_trivial():\n    assert True\n\n\n"
        "def test_import():\n    assert callable(decode)\n", encoding="utf-8")
    run_ok(py + [str(TOOLS / "run_mutants.py"), "--python", sys.executable, "--workers", "4",
                 "--extra-tests", str(extra)] + common)
    run_ok(analyse + ["--extra-tests", str(extra), "--replace", f"{sorted(killers)[0]}=test_trivial"])
    score = json.loads((out / "score.json").read_text(encoding="utf-8"))
    x = score["extra_tests"]
    assert len(x["extra_tests_passing_in_both_unmodified_runs"]) == 2
    assert x["with_extra_tests"]["killed"] >= w["killed"]
    rep = x["replacements"][0]
    assert rep["killed"] <= x["with_extra_tests"]["killed"]
    assert x["check_deletions"]["with_extra_tests"]["killed"] >= dscore["killed"]

    # at_check: every deletion is at its check; a case, its deciding check and a variant that kills nothing
    base = json.loads((WORK / "work" / "records" / "base-1.json").read_text(encoding="utf-8"))
    decided = sorted((c for c in base["cases"] if c["included"] and (c.get("site") or {}).get("check")
                      and c["site"]["file"] == "toyverify/core.py"),
                     key=lambda c: (c["test"], c["block"], c["index"]))
    assert decided
    c0 = decided[0]
    other = sorted(c["id"] for c in toy_checks if c["id"] != c0["site"]["check"])[0]
    key = f"{c0['test']}|{c0['block']}|{c0['index']}"
    (WORK / "cases.tsv").write_text(
        "case\tdescribed\tkind\tvariant\n"
        f"{key}\t{c0['site']['check']}\tcomparison\ttest_trivial\n"
        f"{key}\t{other}\tshadowed\t\n", encoding="utf-8")
    at = py + [str(TOOLS / "at_check.py"), "--out", str(out), "--cases", str(WORK / "cases.tsv"),
               "--extra-tests", str(extra)] + common
    run_ok(at)
    spans = rows(out / "check-spans.csv")
    assert sorted(s["check"] for s in spans) == sorted(c["id"] for c in toy_checks)
    placed = rows(out / "at-check.csv")
    assert {(d["mutant"], d["check"]) for d in deletions} <= {(p["mutant"], p["check"]) for p in placed}
    assert sum(int(s["mutants_at_the_check"]) for s in spans) == sum(1 for p in placed if p["operator"] != DELETION)
    doc = json.loads((out / "described-cases.json").read_text(encoding="utf-8"))
    first, second = doc["cases"]
    assert first["described_check"] == first["deciding_check"] == c0["site"]["check"]
    assert first["mutants"]["described"] == first["mutants"]["deciding"]
    assert first["mutants"]["described_not_deciding"]["mutants"] == 0
    assert first["variant"].endswith("test_trivial") and first["variant_kills_at_the_described_check"] == 0
    # the deletion of the deciding check moves or removes the rejection: the whole suite kills it here
    assert first["deletions"]["deciding"]["mutant"] in {d["mutant"] for d in deletions}
    assert second["described_check"] == other and second["O_C_detections_at_the_described_check_only"] is not None
    # M3 covers shadowed rows with a variant only: the comparison row with a variant does not enter
    assert doc["expectations"]["M3_variants"] == []
    # the 2 readings: tool mutants alone, and tool mutants with the deletion of the check
    by_reading = doc["expectations_by_reading"]
    assert sorted(by_reading) == ["tool_mutants", "tool_mutants_and_deletions"]
    assert as_expectations(by_reading["tool_mutants_and_deletions"]) == doc["expectations"]
    t_m3, td_m3 = by_reading["tool_mutants"]["M3"], by_reading["tool_mutants_and_deletions"]["M3"]
    assert t_m3 == td_m3 == {"rows": [], "status": "not applicable"}
    assert first["mutants"]["described"]["variant"] == 0
    # the shadowed row: under reading TD each count adds the deletion of its check
    t_m1 = by_reading["tool_mutants"]["M1"]["unique_kills_at_the_deciding_check"]
    td_m1 = by_reading["tool_mutants_and_deletions"]["M1"]["unique_kills_at_the_deciding_check"]
    assert list(t_m1) == [key] and t_m1[key] == second["mutants"]["deciding"]["unique"]
    assert td_m1[key] - t_m1[key] == int(second["deletions"]["deciding"]["unique"])
    t_m2 = by_reading["tool_mutants"]["M2"]["O_C_detections_at_the_described_check_only"]
    td_m2 = by_reading["tool_mutants_and_deletions"]["M2"]["O_C_detections_at_the_described_check_only"]
    assert td_m2[key] - t_m2[key] == int(second["deletions"]["described"]["O_C"])
    sums = (out / "SHA256SUMS").read_text(encoding="utf-8")
    assert "at-check.csv" in sums and "described-cases.json" in sums
    run_ok(at)
    assert (out / "SHA256SUMS").read_text(encoding="utf-8") == sums
