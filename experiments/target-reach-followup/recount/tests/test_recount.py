"""The recount on a synthetic deposit of 1 toy subject: 5 cases, 5 checks.

Case c1 is decided by its target m.f#1. Case c2 is decided by m.g#1 and has no
target. Case c3 is decided by m.h#1 and its target m.f#1 does not fire there.
Case c4 is decided by a raise of a class held in a parameter. Case c5 runs
under another test file, is decided by m.f#1 and has the target m.g#1. So
m.f#1 is a targeted deciding check, m.g#1 is a target only of a case it does
not decide, m.h#1 is the target of no case, and m.k#1 fires and never
decides."""

from __future__ import annotations

import csv
import io
import json
import tarfile
from pathlib import Path


import recount

CASE_COLS = ["block", "index", "test_node", "expected", "asserts", "baseline_class", "baseline_site",
             "target", "basis", "tier", "reaches_target", "fired", "target_fired", "own_test_without_target"]
CHECK_COLS = ["check", "file", "role", "function", "class", "template", "in_handler", "reachable", "decides",
              "cases_decided", "blocks_targeting", "cases_fired"]
DEL_COLS = ["check", "in_handler", "O_V", "O_Vfc", "O_C", "O_T", "O_S", "suite", "whole_suite"]
FLAG_COLS = ["block", "index", "test", "basis", "tier", "target", "target_template", "deciding_check",
             "deciding_template", "target_fired", "own_test_without_target"]
PIN_COLS = ["block", "index", "test_node", "asserts", "deleted_check", "baseline_class", "status", "class",
            "site", "what_the_case_does", "test_passes"]

OTHER = "other raise (p/u.py:5 raise cls())"

CASES = [
    # block, test_node, site, target, tier, fired, asserts
    ("t.py::test_a#0", "t.py::test_a", "m.f#1", "m.f#1", "assertion", ["m.f#1"], "class only"),
    ("t.py::test_b#0", "t.py::test_b", "m.g#1", "", "", ["m.g#1", "m.k#1"], "class only"),
    ("t.py::test_c#0", "t.py::test_c", "m.h#1", "m.f#1", "name", ["m.h#1"], "message"),
    ("t.py::test_d#0", "t.py::test_d", OTHER, "", "", [], "class only"),
    ("t.py::test_e#0", "u.py::test_e", "m.f#1", "m.g#1", "name", ["m.f#1"], "class only"),
]

#           O_V    O_Vfc  O_C    O_T    O_S    suite  whole
DELETIONS = {
    "m.f#1": ["yes", "yes", "yes", "yes", "yes", "yes", "yes"],
    "m.g#1": ["no", "no", "yes", "no", "yes", "yes", "yes"],
    "m.h#1": ["yes", "no", "yes", "no", "yes", "yes", "no"],
    "m.k#1": ["yes", "no", "yes", "no", "yes", "yes", "yes"],
}
IN_HANDLER = {"m.f#1": "no", "m.g#1": "yes", "m.h#1": "no", "m.k#1": "yes", "m.z#1": "yes"}

FLAGS_MD = """# toy: reading of the flags

| Case | Target | Decided by | Target fires | Own test without the target | Class |
|---|---|---|---|---|---|
| `test_c#0` (`t.py:3`) | `m.f#1` | `m.h#1` | no | fails | C |
| `test_e#0` (block at `t.py:9`, run under `u.py`) | `m.g#1` | `m.f#1` | no | passes | A |

Counts: A 1, B 0, C 1, D 0.
"""


def write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def summary() -> dict:
    return {"counts": {
        "cases": 5, "cases_with_target": 3,
        "cases_with_target_by_outcome": {"decided by the target": 1, "the target does not fire": 2},
        "flags": 2, "checks_deciding": 3, "deletions_of_deciding_checks": 3,
        "deletions_not_detected_of_deciding_checks":
            {"O_V": 1, "O_Vfc": 2, "O_C": 0, "O_T": 2, "O_S": 0, "suite": 0, "whole suite": 1},
        "deletions_not_detected":
            {"O_V": 1, "O_Vfc": 3, "O_C": 0, "O_T": 3, "O_S": 0, "suite": 0, "whole suite": 1},
        "reached_targets": 1, "reached_targets_deletion_not_detected_O_T": 0,
        "checks_firing_and_never_deciding": 1, "deletions_of_checks_that_fire_and_never_decide": 1,
        "cases_by_site_kind": {"check": 4, "other raise": 1},
        "cases_with_target_by_tier": {"assertion": 1, "name": 2},
        "flags_by_tier": {"name": 2},
        "deletions_in_handler": 2,
        "pinning": {"cases": 4, "cases_not_counted_no_deciding_check": 1,
                    "cases_not_counted_deciding_check_not_deleted": 0, "test_passes": 1,
                    "class_only": {"cases": 3, "test_passes": 1}},
    }}


def build(root: Path, summary_doc: dict | None = None, flags_md: str = FLAGS_MD) -> Path:
    src = root / "source"
    g = src / "generated" / "toy"
    s = src / "subjects" / "toy"
    rd = src / "readings" / "toy"
    for d in (g, s, rd):
        d.mkdir(parents=True)
    cases, records, flags, pins = [], [], [], []
    for block, node, site, target, tier, fired, asserts in CASES:
        row = {"block": block, "index": 0, "test_node": node, "asserts": asserts, "baseline_class": "m.E",
               "baseline_site": site, "target": target, "tier": tier, "basis": tier and "x"}
        if target:
            tf = "yes" if target in fired else "no"
            row.update(target_fired=tf, own_test_without_target="fails" if node.startswith("t.py") else "passes")
        cases.append(row)
        is_check = site.startswith("m.")
        records.append({"block": block, "index": 0, "test": node, "included": True, "raised": True,
                        "rejection": True, "check_result": "accepted", "class": "m.E", "fired": fired,
                        "site": ({"kind": "check", "check": site, "file": "p/m.py", "line": 1, "source": None}
                                 if is_check else
                                 {"kind": "other raise", "check": None, "file": "p/u.py", "line": 5,
                                  "source": "raise cls()"})})
        if target and target != site:
            flags.append({"block": block, "index": 0, "test": node.split("::")[-1], "tier": tier,
                          "target": target, "deciding_check": site, "target_fired": row["target_fired"],
                          "own_test_without_target": row["own_test_without_target"]})
        if is_check:
            passes = "yes" if block == "t.py::test_e#0" else "no"
            pins.append({"block": block, "index": 0, "test_node": node, "asserts": asserts, "deleted_check": site,
                         "status": "observed", "class": "m.E" if passes == "yes" else "",
                         "site": "m.h#1" if passes == "yes" else "no exception",
                         "what_the_case_does": "same class, another check" if passes == "yes" else "no exception",
                         "test_passes": passes})
    # A record that is not a case of the study.
    records.append({"block": "t.py::test_x#0", "index": 0, "test": "t.py::test_x", "included": False,
                    "raised": True, "rejection": False, "check_result": "accepted", "fired": []})
    decided = {"m.f#1": 2, "m.g#1": 1, "m.h#1": 1}
    checks = [{"check": c, "role": "subject", "in_handler": IN_HANDLER[c],
               "decides": "yes" if c in decided else "no", "cases_decided": decided.get(c, 0)}
              for c in ["m.f#1", "m.g#1", "m.h#1", "m.k#1", "m.z#1"]]
    dels = [{"check": c, "in_handler": IN_HANDLER[c],
             **dict(zip(["O_V", "O_Vfc", "O_C", "O_T", "O_S", "suite", "whole_suite"], v))}
            for c, v in DELETIONS.items()]
    write_csv(g / "cases.csv", CASE_COLS, cases)
    write_csv(g / "checks.csv", CHECK_COLS, checks)
    write_csv(g / "deletions.csv", DEL_COLS, dels)
    write_csv(g / "flags.csv", FLAG_COLS, flags)
    write_csv(g / "pinning.csv", PIN_COLS, pins)
    (g / "summary.json").write_text(json.dumps(summary_doc or summary()))
    data = json.dumps({"cases": records}).encode()
    with tarfile.open(g / "records.tar.xz", "w:xz") as tar:
        info = tarfile.TarInfo("records/base-1.json")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    blocks = [{"key": c[0], "match": "bad" if c[6] == "message" else None, "match_unparsed": None,
               "post": [], "post_unparsed": []} for c in CASES]
    (s / "blocks.json").write_text(json.dumps({"blocks": blocks}))
    (s / "targets.json").write_text(json.dumps(
        {"blocks": [{"key": c[0], "target": c[3] or None, "tier": c[4] or None} for c in CASES]}))
    (s / "checks.json").write_text(json.dumps({"other_raises": [
        {"file": "p/u.py", "line": 5, "reason": "not a rejection class", "class_resolved": "?cls",
         "guard": "x"}]}))
    (rd / "FLAGS.md").write_text(flags_md)
    totals = root / "totals.json"
    totals.write_text(json.dumps({"cases": 5, "cases_with_target": 3, "cases_decided_by_target": 1,
                                  "flags": 2, "checks_deciding": 3,
                                  "not_detected": {"O_V": 1, "O_Vfc": 2, "O_C": 0, "O_T": 2,
                                                   "whole suite": 1}}))
    return src


def run(tmp_path: Path, src: Path) -> tuple[int, dict]:
    out = tmp_path / "out"
    code = recount.main(["--source", str(src), "--work", str(tmp_path / "work"), "--out", str(out),
                         "--subjects", "toy", "--held-out", "toy",
                         "--held-out-totals", str(tmp_path / "totals.json")])
    return code, json.loads((out / "recount.json").read_text())


def test_counts_on_a_consistent_deposit(tmp_path):
    code, doc = run(tmp_path, build(tmp_path))
    assert doc["sentinels_failed"] == 0, [s for s in doc["sentinels"] if not s["holds"]]
    assert code == 0
    r = doc["subjects"]["toy"]
    i1 = r["item1_ot_denominator"]
    assert i1["targeted_deciding"]["list"] == ["m.f#1"]
    assert i1["target_of_no_case"]["list"] == ["m.h#1"]
    assert i1["target_only_of_cases_not_decided"]["list"] == ["m.g#1"]
    assert i1["targeted_deciding"]["not_detected"]["O_T"] == 0
    assert i1["target_of_no_case"]["not_detected"] == {
        "O_V": 0, "O_Vfc": 1, "O_C": 0, "O_T": 1, "O_S": 0, "suite": 0, "whole suite": 1}
    assert r["item2_fire_never_decide"]["list"] == ["m.k#1"]
    assert r["item2_fire_never_decide"]["not_detected"]["O_Vfc"] == 1
    i3 = r["item3_non_check_sites"]
    assert [(x["file"], x["line"], x["statement"], x["listed_class"]) for x in i3["cases"]] == [
        ("p/u.py", 5, "raise cls()", "?cls")]
    assert i3["pinning_denominators"]["cases_of_the_study"] == 5
    assert i3["pinning_denominators"]["pinning_rows"] == 4
    t = r["item4_flags"]["tiers"]
    assert t["name"] == {"cases_with_target": 2, "decided_by_target": 0, "flags": 2,
                         "flags_by_class": {"A": 1, "B": 0, "C": 1, "D": 0}}
    assert t["assertion"]["decided_by_target"] == 1
    passes = r["item4_flags"]["flags_own_test_passes_without_deciding_check"]
    assert [(x["block"], x["reading_class"], x["site_after_deletion"]) for x in passes] == [
        ("t.py::test_e#0", "A", "m.h#1")]
    assert r["item4_flags"]["class_C_own_test_passes_without_deciding_check"] == []
    i6 = r["item6_in_handler"]
    assert (i6["checks"], i6["deciding"], i6["cases_decided"], i6["deleted"]) == (3, 1, 1, 2)
    md = (tmp_path / "out" / "RECOUNT.md").read_text()
    assert "/tmp" not in md and str(tmp_path) not in md


def test_a_wrong_deposited_count_fails_after_writing(tmp_path):
    bad = summary()
    bad["counts"]["deletions_not_detected_of_deciding_checks"]["O_T"] = 1
    code, doc = run(tmp_path, build(tmp_path, summary_doc=bad))
    assert code == 1
    failed = [s["sentinel"] for s in doc["sentinels"] if not s["holds"]]
    assert "summary.json: deletions of deciding checks not detected by O_T" in failed
    assert (tmp_path / "out" / "RECOUNT.md").exists()


def test_a_wrong_class_count_in_the_reading_fails(tmp_path):
    code, doc = run(tmp_path, build(tmp_path, flags_md=FLAGS_MD.replace("Counts: A 1, B 0, C 1",
                                                                         "Counts: A 0, B 0, C 2")))
    assert code == 1
    assert any("Counts:" in s["sentinel"] for s in doc["sentinels"] if not s["holds"])


def test_a_flag_without_a_row_fails(tmp_path):
    md = "\n".join(l for l in FLAGS_MD.splitlines() if "test_e#0" not in l) + "\n"
    code, doc = run(tmp_path, build(tmp_path, flags_md=md.replace("A 1, B 0, C 1", "A 0, B 0, C 1")))
    assert code == 1
    assert any("every flag has exactly 1 row" in s["sentinel"] for s in doc["sentinels"] if not s["holds"])


def test_wrong_held_out_totals_fail(tmp_path):
    src = build(tmp_path)
    (tmp_path / "totals.json").write_text(json.dumps({"cases": 6}))
    out = tmp_path / "out"
    code = recount.main(["--source", str(src), "--work", str(tmp_path / "work"), "--out", str(out),
                         "--subjects", "toy", "--held-out", "toy",
                         "--held-out-totals", str(tmp_path / "totals.json")])
    assert code == 1


def test_parse_labels_with_an_index_and_another_test_file():
    rows, counts = recount.parse_flags_md(
        "| Case | Target | Decided by | Target fires | Own test without the target | Class |\n"
        "|---|---|---|---|---|---|\n"
        "| `K.test_x#2 [11]` (`tests/a.py:84`) | `a` | `b` | no | fails | C |\n"
        "| `K2.test_y#0` (block at `tests/b.py:300`, run under `tests/c.py`) | `a` | `b` | no | passes | A |\n"
        "\nCounts: A 1, B 0, C 1, D 0.\n")
    assert counts == {"A": 1, "B": 0, "C": 1, "D": 0}
    assert (rows[0]["test_node"], rows[0]["k"], rows[0]["index"]) == ("tests/a.py::K::test_x", 2, 11)
    assert (rows[1]["test_node"], rows[1]["block_file"]) == ("tests/c.py::K2::test_y", "tests/b.py")
