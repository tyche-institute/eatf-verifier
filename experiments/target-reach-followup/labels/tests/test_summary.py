"""Tests of summary.py on small synthetic per-library outputs written to a temporary folder."""

from __future__ import annotations

import csv
import json
import re
from fractions import Fraction
from pathlib import Path

import analyse_labels
import summary

R2, R3 = "rule 2", "rule 3"
DECIDED = "decided by its label"
SHADOWED = "label does not fire and decides once the deciding check is deleted"


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def zero(keys):
    return {k: 0 for k in keys}


def rule_counts(by_tier: dict) -> dict:
    tiers = {t: dict(zero(analyse_labels.CATEGORIES), **by_tier.get(t, {})) for t in analyse_labels.TIERS}
    total = zero(analyse_labels.CATEGORIES)
    for row in tiers.values():
        for k, v in row.items():
            total[k] += v
    return {"all": total, "by_tier": tiers}


def node(i: str) -> str:
    return f"tests/test_x.py::test_{i}"


def write_joserfc(folder: Path) -> None:
    """4 blocks, 1 per agreement category; 7 cases; 7 flags in all 6 categories."""
    folder.mkdir(parents=True)
    agreement = [["B1", "a#1", "a#1", "same check"], ["B2", "none", "none", "both none"],
                 ["B3", "a#1", "none", "1 check and 1 none"], ["B4", "a#1", "b#1", "2 different checks"]]
    write_csv(folder / "agreement.csv", ["block", "label_1", "label_2", "category"], agreement)
    # case: (block, index, rule-2 target, tier, rule-3 target, tier, agreed label, cat 2, cat 3)
    cases = [
        ("B1", "0", "a#1", "assertion", "a#1", "name", "a#1", "target equals label", "target equals label"),
        ("B1", "1", "q#1", "assertion", "a#1", "name", "a#1", "target differs from label", "target equals label"),
        ("B1", "2", "r#1", "name", "a#1", "name", "a#1", "target differs from label", "target equals label"),
        ("B2", "0", "n#1", "name", "", "none", "none", "label none", "target and label none"),
        ("B2", "1", "", "none", "", "none", "none", "target and label none", "target and label none"),
        ("B3", "0", "", "none", "", "none", "", "no agreed label", "no agreed label"),
        ("B4", "0", "", "none", "", "none", "", "no agreed label", "no agreed label"),
    ]
    rows = []
    for b, i, t2, tier2, t3, tier3, lab, c2, c3 in cases:
        rows.append([R2, b, i, node(b + i), t2, tier2, lab, c2])
        rows.append([R3, b, i, node(b + i), t3, tier3, lab, c3])
    write_csv(folder / "rule-vs-label.csv",
              ["rule", "block", "index", "test_node", "target", "tier", "label", "category"], rows)
    outcomes = [["B1", "0", node("B10"), "a#1", "a#1", "yes", DECIDED, "observed", "", "no"],
                ["B1", "1", node("B11"), "a#1", "q#1", "no", SHADOWED, "observed", "a#1", "yes"],
                ["B1", "2", node("B12"), "a#1", "a#1", "yes", DECIDED, "observed", "", "no"]]
    write_csv(folder / "outcomes.csv",
              ["block", "index", "test_node", "label", "deciding", "label_fired", "outcome",
               "status_without_deciding", "site_without_deciding", "label_fires_without_deciding"], outcomes)
    # flag: block, index, class, target, described, label_1, label_2, agreed
    flags = [("B1", "0", "C", "a#1", "a#1", "a#1", "a#1", "a#1"),       # equals described; L2 fails
             ("B1", "1", "A", "q#1", "a#1", "a#1", "a#1", "a#1"),       # equals described; L1 fails
             ("B1", "2", "C", "r#1", "b#1", "a#1", "a#1", "a#1"),       # another check; L2 holds
             ("B2", "0", "C", "n#1", "d#1", "none", "none", "none"),    # none, described
             ("B2", "1", "C", "", "", "none", "none", "none"),          # none, no described
             ("B3", "0", "C", "", "d#1", "a#1", "none", ""),            # no agreed, described
             ("B4", "0", "C", "", "", "a#1", "b#1", "")]                # no agreed, no described
    first = []
    for b, i, cls, t, d, l1, l2, ag in flags:
        cmp_ = ("yes" if ag == d else "no") if ag and d else ""
        first.append([b, i, node(b + i), cls, t, "x#9", d, l1, l2, ag, cmp_])
    write_csv(folder / "first-reading.csv",
              ["block", "index", "test_node", "class", "target", "deciding_check", "described_first",
               "label_1", "label_2", "agreed_label", "agreed_equals_described"], first)
    pairs = [(r[1], r[2]) for r in agreement]
    counts = {
        "agreement": {"same check": 1, "both none": 1, "1 check and 1 none": 1, "2 different checks": 1},
        "agreement_statistics": {
            "labels": analyse_labels.kappa(pairs),
            "check_or_none": analyse_labels.kappa([("none" if a == "none" else "check",
                                                    "none" if b == "none" else "check") for a, b in pairs])},
        "cases": 7, "cases_with_agreed_label_check": 3, "cases_with_agreed_label_none": 2,
        "cases_without_agreed_label": 2,
        "outcomes": dict(zero(analyse_labels.OUTCOMES), **{DECIDED: 2, SHADOWED: 1}),
        "rule_vs_label": {
            R2: rule_counts({"assertion": {"target equals label": 1, "target differs from label": 1},
                             "name": {"target differs from label": 1, "label none": 1},
                             "none": {"target and label none": 1, "no agreed label": 2}}),
            R3: rule_counts({"name": {"target equals label": 3},
                             "none": {"target and label none": 2, "no agreed label": 2}})},
        "first_reading": {"flags": 7, "agreed_label_equals_described": 2,
                          "agreed_label_differs_from_described": 2, "not_compared": 3},
    }
    (folder / "counts.json").write_text(json.dumps(counts), encoding="utf-8")


def write_other(folder: Path) -> None:
    """2 blocks with the same label: expected agreement 1; no first reading."""
    folder.mkdir(parents=True)
    agreement = [["Y1", "a#1", "a#1", "same check"], ["Y2", "a#1", "a#1", "same check"]]
    write_csv(folder / "agreement.csv", ["block", "label_1", "label_2", "category"], agreement)
    write_csv(folder / "rule-vs-label.csv",
              ["rule", "block", "index", "test_node", "target", "tier", "label", "category"],
              [[R2, "Y1", "0", node("Y10"), "a#1", "name", "a#1", "target equals label"],
               [R3, "Y1", "0", node("Y10"), "a#1", "name", "a#1", "target equals label"]])
    write_csv(folder / "outcomes.csv",
              ["block", "index", "test_node", "label", "deciding", "label_fired", "outcome",
               "status_without_deciding", "site_without_deciding", "label_fires_without_deciding"],
              [["Y1", "0", node("Y10"), "a#1", "a#1", "yes", DECIDED, "", "", ""]])
    pairs = [(r[1], r[2]) for r in agreement]
    counts = {
        "agreement": {"same check": 2, "both none": 0, "1 check and 1 none": 0, "2 different checks": 0},
        "agreement_statistics": {"labels": analyse_labels.kappa(pairs),
                                 "check_or_none": analyse_labels.kappa([("check", "check")] * 2)},
        "cases": 1, "cases_with_agreed_label_check": 1, "cases_with_agreed_label_none": 0,
        "cases_without_agreed_label": 0,
        "outcomes": dict(zero(analyse_labels.OUTCOMES), **{DECIDED: 1}),
        "rule_vs_label": {R2: rule_counts({"name": {"target equals label": 1}}),
                          R3: rule_counts({"name": {"target equals label": 1}})},
        "first_reading": {"flags": 0, "transcription": "absent"},
    }
    (folder / "counts.json").write_text(json.dumps(counts), encoding="utf-8")


def run(tmp_path: Path) -> tuple[int, dict]:
    gen = tmp_path / "gen"
    if not gen.exists():
        write_joserfc(gen / "joserfc")
        write_other(gen / "other")
    out = tmp_path / "out"
    code = summary.main(["--generated", str(gen), "--names", "joserfc", "other", "--out", str(out)])
    doc = json.loads((out / "summary.json").read_text(encoding="utf-8")) if (out / "summary.json").exists() else {}
    return code, doc


def as_fraction(f: dict | None):
    return None if f is None else Fraction(f["numerator"], f["denominator"])


def test_blocks_and_kappa(tmp_path):
    code, doc = run(tmp_path)
    assert code == 0, [c for c in doc["checks"] if not c["holds"]]
    j = doc["libraries"]["joserfc"]
    assert j["blocks"]["categories"] == {"same check": 1, "both none": 1, "1 check and 1 none": 1,
                                         "2 different checks": 1}
    assert j["blocks"]["same_label"] == 2 and j["blocks"]["labeled_by_both"] == 4
    st = j["agreement_statistics"]["labels"]
    # reading 1: a a a none, reading 2: a none b none; p_o 1/2, p_e (3*1 + 1*2)/16 = 5/16
    assert as_fraction(st["observed"]) == Fraction(1, 2)
    assert as_fraction(st["expected"]) == Fraction(5, 16)
    assert as_fraction(st["kappa"]) == Fraction(3, 11) and st["kappa"]["value"] == 0.2727
    st = j["agreement_statistics"]["check_or_none"]
    assert (as_fraction(st["observed"]), as_fraction(st["expected"]), as_fraction(st["kappa"])) == \
        (Fraction(3, 4), Fraction(1, 2), Fraction(1, 2))
    # expected agreement 1: kappa has no value
    o = doc["libraries"]["other"]["agreement_statistics"]
    assert as_fraction(o["labels"]["expected"]) == 1 and o["labels"]["kappa"] is None
    assert o["check_or_none"]["kappa"] is None
    # together: 6 items, a#1 is 1 category in both libraries
    t = doc["together"]
    st = t["agreement_statistics"]["labels"]
    assert (st["items"], st["equal"]) == (6, 4)
    assert as_fraction(st["expected"]) == Fraction(17, 36) and as_fraction(st["kappa"]) == Fraction(7, 19)
    st = t["agreement_statistics"]["check_or_none"]
    assert as_fraction(st["expected"]) == Fraction(11, 18) and as_fraction(st["kappa"]) == Fraction(4, 7)
    v = t["agreement_statistics_variant"]["labels_qualified_by_library"]
    assert as_fraction(v["expected"]) == Fraction(1, 4) and as_fraction(v["kappa"]) == Fraction(5, 9)
    assert t["label_texts_other_than_none_in_2_or_more_libraries"] == {"a#1": ["joserfc", "other"]}
    assert t["blocks"]["categories"]["same check"] == 3


def test_cases_rules_and_first_reading(tmp_path):
    code, doc = run(tmp_path)
    assert code == 0
    j = doc["libraries"]["joserfc"]
    assert (j["cases"]["cases"], j["cases"]["agreed_label_check"], j["cases"]["agreed_label_none"],
            j["cases"]["no_agreed_label"]) == (7, 3, 2, 2)
    assert j["cases"]["decided_by_its_label"] == 2 and j["cases"]["shadowed"] == 1
    a = j["rules"][R2]["all"]
    assert (a["with_target"], a["with_target_and_agreed_label"], a["target_equals_label"],
            a["target_is_not_the_agreed_label"]) == (4, 4, 1, 3)
    assert j["rules"][R2]["by_tier"]["name"]["target_is_not_the_agreed_label"] == 2
    fr = j["first_reading"]["by_class"]
    assert fr["C"] == {k: 1 for k in summary.FIRST_CATEGORIES}
    assert fr["A"][summary.FIRST_CATEGORIES[0]] == 1
    tgt = j["first_reading"]["agreed_label_equals_target_by_class"]
    assert tgt["C"] == {"yes": 1, "no": 3, "no agreed label": 2}
    assert doc["libraries"]["other"]["first_reading"] is None
    assert doc["together"]["cases"]["cases"] == 8


def test_expectations(tmp_path):
    _, doc = run(tmp_path)
    e = doc["libraries"]["joserfc"]["expectations"]
    assert (e["L1"]["units"], e["L1"]["status"], e["L1"]["not_holding"]) == \
        (1, "not held", [f"{node('B11')}|B1|1"])
    assert (e["L2"]["units"], e["L2"]["hold"], e["L2"]["status"]) == (2, 1, "not held")
    assert e["L2"]["not_holding"] == [f"{node('B10')}|B1|0"]
    assert (e["L3"]["units"], e["L3"]["hold"], e["L3"]["not_holding"]) == (2, 1, [f"{node('B11')}|B1|1"])
    assert (e["L3, rule 3"]["units"], e["L3, rule 3"]["status"]) == (2, "held")
    o = doc["libraries"]["other"]["expectations"]
    assert o["L1"]["status"] == "not applicable" and o["L3"]["status"] == "held"
    t = doc["together"]["expectations"]
    assert (t["L3"]["units"], t["L3"]["status"]) == (3, "not held")


def check_holds(doc: dict, prefix: str) -> bool:
    return next(c for c in doc["checks"] if c["name"].startswith(prefix))["holds"]


def test_partition_failure_exit_1(tmp_path):
    gen = tmp_path / "gen"
    write_joserfc(gen / "joserfc")
    write_other(gen / "other")
    path = gen / "joserfc" / "outcomes.csv"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(lines[:-1]), encoding="utf-8")            # 2 outcome rows for 3 cases
    counts = json.loads((gen / "joserfc" / "counts.json").read_text(encoding="utf-8"))
    counts["outcomes"][DECIDED] = 1
    (gen / "joserfc" / "counts.json").write_text(json.dumps(counts), encoding="utf-8")
    code, doc = run(tmp_path)
    assert code == 1
    assert not check_holds(doc, "outcomes sum")
    assert check_holds(doc, "case counts")


def test_unclassified_flag_exit_1(tmp_path):
    gen = tmp_path / "gen"
    write_joserfc(gen / "joserfc")
    write_other(gen / "other")
    path = gen / "joserfc" / "first-reading.csv"
    text = path.read_text(encoding="utf-8").replace(",C,r#1,x#9,b#1,", ",C,r#1,x#9,,")
    path.write_text(text, encoding="utf-8")
    code, doc = run(tmp_path)
    assert code == 1 and not check_holds(doc, "first-reading categories")


def test_bad_input_exit_2(tmp_path):
    gen = tmp_path / "gen"
    write_other(gen / "other")
    assert summary.main(["--generated", str(gen), "--names", "other", "missing",
                         "--out", str(tmp_path / "out")]) == 2


UNESCAPED_BAR = re.compile(r"(?<!\\)\|")


def test_table_rows_have_the_cells_of_their_header(tmp_path):
    code, _ = run(tmp_path)
    assert code == 0
    text = (tmp_path / "out" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "\\|B1\\|1" in text                                     # a case key with escaped |
    tables, current = [], []
    for line in text.splitlines():
        if line.startswith("|"):
            current.append(line)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    assert len(tables) >= 6
    for rows in tables:
        header = len(UNESCAPED_BAR.split(rows[0]))
        for row in rows[1:]:
            assert len(UNESCAPED_BAR.split(row)) == header, row


def test_equal_texts_differ_from_same_label_blocks_exit_1(tmp_path):
    """A by-parameter label whose values come in another order: same label for section 4.1, unequal texts."""
    gen = tmp_path / "gen"
    write_joserfc(gen / "joserfc")
    write_other(gen / "other")
    path = gen / "joserfc" / "agreement.csv"
    text = path.read_text(encoding="utf-8").replace(
        "B1,a#1,a#1,same check", 'B1,"by-param p: 1=a#1; 2=b#1","by-param p: 2=b#1; 1=a#1",same check')
    path.write_text(text, encoding="utf-8")
    with path.open(encoding="utf-8", newline="") as handle:
        pairs = [(r["label_1"], r["label_2"]) for r in csv.DictReader(handle)]
    counts_path = gen / "joserfc" / "counts.json"
    counts = json.loads(counts_path.read_text(encoding="utf-8"))
    counts["agreement_statistics"] = {
        "labels": analyse_labels.kappa(pairs),
        "check_or_none": analyse_labels.kappa([("none" if a == "none" else "check",
                                                "none" if b == "none" else "check") for a, b in pairs])}
    counts_path.write_text(json.dumps(counts), encoding="utf-8")
    code, doc = run(tmp_path)
    assert code == 1
    failed = [c for c in doc["checks"] if not c["holds"]]
    assert [c["name"] for c in failed] == [summary.EQUAL_TEXTS_CHECK]
    assert failed[0]["problems"] == [
        'joserfc: 1 equal label texts, 2 blocks of "same check" and "both none"',
        'together: 3 equal label texts, 4 blocks of "same check" and "both none"']
