"""Compare the output of recompute/second_labels.py with the outputs of
labels/analyse_labels.py for 1 subject.

    python3 -I -B recompute/compare_labels.py --second second_labels.json \
        --first-dir generated/labels/<name> \
        --subject ../target-reach/subjects/<name>/subject.json \
        [--shadowed generated/mutants/<name>/shadowed.csv] \
        [--summary generated/labels/summary.json] [--json differences.json]

`--first-dir` holds counts.json, agreement.csv, outcomes.csv,
rule-vs-label.csv, rule-vs-label-blocks.csv and, when a first reading was
given, first-reading.csv. `--subject` gives checks.json, from which the check
ids are read (the column `deciding` of outcomes.csv names a raise site that is
not a check by a text, not by an id). `--shadowed` is the shadowed.csv of
mutants/cases_file.py, which takes its labels source from outcomes.csv.
`--summary` is the summary.json of labels/summary.py; its entry
libraries[<subject>] gives the expectations L1, L2 and L3 (and the
supplement "L3, rule 3"), the exact fractions of the agreement statistics
and the count of shadowed cases.

Besides the values of the first outputs, the script checks values inside the
second output against each other. Each float field of the agreement
statistics ("observed_agreement", "expected_agreement", "kappa") is compared
with its own fraction rounded to 9 places, the rounding of second_labels.py.
Each count of shadowed cases ("shadowed_cases_count", "by_agreed_label",
"by_rule_2_target_in_place_of_the_label", "by_reading") is compared with the
size of its set. The units of L1, L2 and L3 are compared with their id
lists. The float fields are also compared, rounded to 4 places, with
counts.json.

TABLE below names each compared value of the second output and its place in
the first outputs. Sets are compared as sets and per-item tables per item.
A value that 1 side does not hold for this run (for example rule 3 when only
1 side was given rule-3 targets, or L1 to L3 without --summary) is not
compared and is named in the output under "not compared".

The name tables below (OUTCOME_MAP, PVL_CASE_MAP, PVL_BLOCK_MAP, FIRST_MAP,
EXPECTATION_MAP, AGREEMENT_CATEGORIES, RULES and CASES_BY_LABEL) hold the
names that the second output and the first outputs may use. Where the 2
sides name a value differently, the table maps each second name to its first
name. A name on either side that its table does not map is a difference. It counts as 1 compared
value and names the table, the side, the name and, for a name of 1 case or
flag, the case key.

The script prints "compared N, agree N, differ N", each value not compared
and each difference, with both values (for sets: the members only in 1 of
them). Exit status:
- 0 when no compared value differs;
- 1 when a compared value differs or a name is not in its name table;
- 2 on bad input (a missing file, unreadable JSON or CSV, or a missing key
  or column).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from fractions import Fraction
from pathlib import Path

NONE = "none"
NO_AGREED = "(no agreed label)"
UNRESOLVED = "(by-param label does not resolve)"
NOT_A_CHECK = "(raise site is not a check)"

# second_labels.py outcome keys -> analyse_labels.py outcome texts
OUTCOME_MAP = {
    "1 decided by its label": "decided by its label",
    "2 label fires and another check decides": "label fires and another check decides",
    "3 label fires and no check decides": "label fires and no check decides",
    "4 label does not fire and no check decides": "label does not fire and no check decides",
    "5 deciding check not deleted or record missing": "deciding check not deleted or record missing",
    "6 label does not fire; case not observed on the copy without the deciding check":
        "label does not fire; case not observed on the copy without the deciding check",
    "7 label does not fire and decides once the deciding check is deleted":
        "label does not fire and decides once the deciding check is deleted",
    "8 label does not fire and does not decide then either":
        "label does not fire and does not decide then either",
    "fired checks not recorded": "fired checks not recorded",
}
# program against label, per case: second category -> first category
PVL_CASE_MAP = {
    "target equals agreed label": "target equals label",
    "target differs from agreed label": "target differs from label",
    "target given, agreed label none": "label none",
    "no target, agreed label names a check": "no target",
    "both none": "target and label none",
    "no agreed label": "no agreed label",
}
# program against label, per block: second category -> first cell
PVL_BLOCK_MAP = {
    "target equals agreed label": "both, equal",
    "target differs from agreed label": "both, different",
    "target given, agreed label none": "rule only",
    "no target, agreed label names a check": "label only",
    "both none": "neither",
    "no agreed label": "no agreed label",
}
# first reading: second category -> column agreed_equals_described of first-reading.csv
FIRST_MAP = {
    "agreed label equals described check": "yes",
    "agreed label differs from described check": "no",
    "agreed label none, described check given": "no",
    "agreed label names a check, no described check": "",
    "agreed label none, no described check": "",
    "no agreed label": "",
}
FIRST_COUNT_MAP = {"yes": "agreed_label_equals_described", "no": "agreed_label_differs_from_described",
                   "": "not_compared"}
TIER_OF_NO_TARGET = {"second": "no target", "first": "none"}
# expectations: second_labels.py key -> summary.json libraries[<subject>].expectations key
EXPECTATION_MAP = {
    "L1": "L1",
    "L2": "L2",
    "L3": "L3",
    "L3_with_rule_3_targets_supplementary": "L3, rule 3",
}
# float fields of the agreement statistics: second float field, second fraction field, counts.json key,
# summary.json key (exact fraction as numerator and denominator)
FLOAT_FIELDS = [
    ("observed_agreement", "observed_agreement_fraction", "observed", "observed"),
    ("expected_agreement", "expected_agreement_fraction", "expected", "expected"),
    ("kappa", "kappa_fraction", "kappa", "kappa"),
]
SHADOWED_OUTCOME = "label does not fire and decides once the deciding check is deleted"
# agreement categories of 2 readings, the same names on both sides
AGREEMENT_CATEGORIES = ("same check", "both none", "1 check and 1 none", "2 different checks")
# the rules of program against label, the same names on both sides
RULES = ("rule 2", "rule 3")
# keys of outcomes.agreed.cases_by_label of the second output
CASES_BY_LABEL = ("names a check", NONE, NO_AGREED, UNRESOLVED)

# The explicit table: name of the compared value -> (place in the second output, place in the first
# outputs). The functions below build each value from these places.
TABLE = [
    ("cases of the study (set of case keys)",
     "cases (keys)", "rule-vs-label.csv, rows of rule 2 (test_node|block|index)"),
    ("number of cases of the study", "inputs['cases of the study']", "counts.json cases"),
    ("cases with an agreed label naming a check", "outcomes.agreed.cases_by_label['names a check']",
     "counts.json cases_with_agreed_label_check"),
    ("cases with agreed label none", "outcomes.agreed.cases_by_label['none']",
     "counts.json cases_with_agreed_label_none"),
    ("cases without an agreed label", "outcomes.agreed.cases_by_label[no agreed label + unresolved]",
     "counts.json cases_without_agreed_label"),
    ("reading i: blocks / check / none / by-param", "readings.A|B.blocks*",
     "counts.json labels[<file i>].blocks_labeled|label_check|label_none|label_by_param"),
    ("included blocks", "inputs['included blocks']", "agreement.csv (rows)"),
    ("agreement category per block (set per category)", "agreement.categories.ids[<category>]",
     "agreement.csv category"),
    ("agreement count per category", "agreement.categories.counts", "counts.json agreement"),
    ("blocks with an agreed label naming a check (set)",
     "agreement.blocks_with_an_agreed_label_naming_a_check_ids",
     "agreement.csv: same check (2 files) or single with label_1 not none"),
    ("blocks with agreed label none (set)", "agreement.blocks_with_agreed_label_none_ids",
     "agreement.csv: both none (2 files) or single with label_1 none"),
    ("labels per block of each reading", "cases[*].labels.A|B (per block, first case)",
     "agreement.csv label_1, label_2 (cases of blocks without a by-param label)"),
    ("kappa, every label text and names a check or none: units, categories, agree, observed, "
     "expected, kappa (4 decimals)",
     "agreement.every_label_text_as_a_category | names_a_check_or_none",
     "counts.json agreement_statistics.labels | check_or_none"),
    ("outcome count per outcome", "outcomes.agreed.outcomes.counts", "counts.json outcomes"),
    ("outcome per case", "cases[*].outcomes.agreed", "outcomes.csv outcome"),
    ("cases with an outcome (set)", "cases[*] with outcomes.agreed", "outcomes.csv (rows)"),
    ("agreed label per case with an outcome", "cases[*].labels.agreed", "outcomes.csv label"),
    ("deciding check per case with an outcome", "cases[*].deciding_check", "outcomes.csv deciding"),
    ("label fired per case with an outcome", "label in cases[*].fired or label = deciding check",
     "outcomes.csv label_fired"),
    ("shadowed by the agreed label (set)", "shadowed.by_agreed_label_ids",
     "outcomes.csv rows with outcome 'label does not fire and decides once the deciding check is deleted'"),
    ("rule r per case: target, tier, label, category", "cases[*]['rule r'], cases[*].labels.agreed, "
     "program_vs_label['rule r'].per_case.ids", "rule-vs-label.csv"),
    ("rule r per case: count per category", "program_vs_label['rule r'].per_case.counts",
     "counts.json rule_vs_label['rule r'].all"),
    ("rule r per case: count per tier and category", "program_vs_label['rule r'].per_case_by_tier",
     "counts.json rule_vs_label['rule r'].by_tier"),
    ("rule r per block: target, tier, basis, cell", "program_vs_label['rule r'].per_block.ids "
     "(+ the target file through cases)", "rule-vs-label-blocks.csv"),
    ("rule r per block: count per cell", "program_vs_label['rule r'].per_block.counts",
     "counts.json rule_vs_label_blocks['rule r'].all"),
    ("rule r per block: count per basis and cell", "program_vs_label['rule r'].per_block_by_basis",
     "counts.json rule_vs_label_blocks['rule r'].by_basis (rows 'none: <reason>' summed)"),
    ("first reading: flags", "first_reading.rows", "counts.json first_reading.flags"),
    ("first reading: counts equal / differ / not compared", "first_reading.categories.counts (mapped)",
     "counts.json first_reading"),
    ("first reading per flag: class, described, target, deciding, label A, label B, agreed, equal",
     "first_reading.per_flag, cases[*].labels",
     "first-reading.csv (a deciding_check that is no check id stands for a raise site that is no check)"),
    ("shadowed rows (case, described, source)", "shadowed.shadowed_cases_with_sources and "
     "first_reading_class_a_rows", "shadowed.csv of mutants/cases_file.py (with --shadowed)"),
    ("kappa float fields against their own fractions (inside the second output)",
     "agreement.<form>.observed_agreement | expected_agreement | kappa",
     "round(<same form>.<field>_fraction, 9) of the second output"),
    ("kappa float fields, 4 places", "round(agreement.<form>.<float field>, 4)",
     "counts.json agreement_statistics.<form>.observed | expected | kappa"),
    ("kappa exact fractions", "agreement.<form>.<field>_fraction",
     "summary.json libraries[<subject>].agreement_statistics.<form>.<field> numerator/denominator "
     "(with --summary)"),
    ("shadowed counts against the size of their sets (inside the second output)",
     "shadowed.shadowed_cases_count | by_agreed_label | by_rule_2_target_in_place_of_the_label | by_reading",
     "len(shadowed_cases_with_sources | by_agreed_label_ids | ..._ids | by_reading[*].ids)"),
    ("shadowed cases against the first side", "shadowed.shadowed_cases_count and its case set; "
     "shadowed.by_agreed_label",
     "distinct cases of shadowed.csv (with --shadowed); counts.json outcomes['" + SHADOWED_OUTCOME + "']; "
     "summary.json libraries[<subject>].cases.shadowed (with --summary)"),
    ("expectations L1, L2, L3 and the supplement L3 with rule-3 targets: units, units that hold, status, "
     "unit cases, cases that do not hold", "expectations[<L>]",
     "summary.json libraries[<subject>].expectations[<L>] units | hold | status | unit_rows | not_holding "
     "(with --summary)"),
    ("expectations: units and holding against their id lists (inside the second output)",
     "expectations[<L>].units | holding", "len(units_ids), len(holding_ids) or units - len(not_holding)"),
    ("names not in a name table (1 difference per name, either side)",
     "outcome, category, cell, rule and expectation names of the second output",
     "outcome, category, cell, rule and expectation names of the first outputs"),
]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class Comparison:
    def __init__(self) -> None:
        self.compared = 0
        self.agree = 0
        self.differences: list[dict] = []
        self.skipped: list[str] = []  # values not compared, with the reason

    def value(self, name: str, second, first) -> None:
        self.compared += 1
        if second == first:
            self.agree += 1
        else:
            self.differences.append({"value": name, "second": second, "first": first})

    def set(self, name: str, second, first) -> None:
        s, f = set(second), set(first)
        self.compared += 1
        if s == f:
            self.agree += 1
        else:
            self.differences.append({"value": name, "set": True, "sizes": [len(s), len(f)],
                                     "only_second": sorted(s - f), "only_first": sorted(f - s)})

    def unmapped(self, name: str, table: str, side: str, key) -> None:
        """A name of 1 side that its name table does not map: 1 compared value, 1 difference."""
        self.compared += 1
        self.differences.append({"value": name, "second": key if side == "second" else None,
                                 "first": key if side == "first" else None,
                                 "note": f"name of the {side} side not in {table}"})

    def unmapped_keys(self, name: str, table: str, side: str, keys, known) -> None:
        """Each name in keys that is not in known is a difference."""
        for k in sorted(set(keys) - set(known)):
            self.unmapped(f"{name}: '{k}'", table, side, k)

    def mapped(self, name: str, table_name: str, table: dict, key, default=None):
        """table[key] for a name of the second output; a name the table lacks is a difference."""
        if key in table:
            return table[key]
        self.unmapped(f"{name}: '{key}'", table_name, "second", key)
        return default

    def table(self, name: str, second: dict, first: dict) -> None:
        """Per item: the key sets, then each item present in both."""
        self.set(f"{name}: items", second.keys(), first.keys())
        for k in sorted(set(second) & set(first)):
            self.value(f"{name}: {k}", second[k], first[k])


def lab_out(lab: str | None) -> str:
    """A label of the second output as the first outputs write it."""
    if lab is None or lab in (NO_AGREED, UNRESOLVED):
        return ""
    return lab


def round4(frac: str | None):
    return None if frac is None else round(float(Fraction(frac)), 4)


def frac_text(value) -> str | None:
    """An exact fraction as 'numerator/denominator' in lowest terms; None stays None."""
    if value is None:
        return None
    if isinstance(value, dict):
        f = Fraction(value["numerator"], value["denominator"])
    else:
        f = Fraction(value)
    return f"{f.numerator}/{f.denominator}"


def compare(sec: dict, first_dir: Path, check_ids: set, shadowed_csv: Path | None,
            summary_lib: dict | None = None) -> Comparison:
    cmp = Comparison()
    counts = json.loads((first_dir / "counts.json").read_text(encoding="utf-8"))
    agreement_rows = read_csv(first_dir / "agreement.csv")
    outcome_rows = read_csv(first_dir / "outcomes.csv")
    rvl_rows = read_csv(first_dir / "rule-vs-label.csv")
    rvlb_rows = read_csv(first_dir / "rule-vs-label-blocks.csv")
    cases = sec["cases"]
    two = sec["inputs"]["readings"] == 2

    def key(r: dict) -> str:
        return f"{r['test_node']}|{r['block']}|{r['index']}"

    # -- cases --
    rule2_rows = [r for r in rvl_rows if r["rule"] == "rule 2"]
    cmp.set("cases of the study (set of case keys)", cases.keys(), [key(r) for r in rule2_rows])
    cmp.value("number of cases of the study", sec["inputs"]["cases of the study"], counts["cases"])
    by_label = sec["outcomes"]["agreed"]["cases_by_label"]
    cmp.unmapped_keys("cases by agreed label", "CASES_BY_LABEL", "second", by_label, CASES_BY_LABEL)
    cmp.value("cases with an agreed label naming a check", by_label.get("names a check", 0),
              counts["cases_with_agreed_label_check"])
    cmp.value("cases with agreed label none", by_label.get(NONE, 0), counts["cases_with_agreed_label_none"])
    cmp.value("cases without an agreed label", by_label.get(NO_AGREED, 0) + by_label.get(UNRESOLVED, 0),
              counts["cases_without_agreed_label"])

    # -- readings --
    names = ["A", "B"][:sec["inputs"]["readings"]]
    files = counts["labels_files"]
    if len(files) != len(names):
        cmp.value("number of labels files", len(names), len(files))
    for n, f in zip(names, files):
        r, c = sec["readings"][n], counts["labels"][f]
        cmp.value(f"reading {n} ({f}): blocks", r["blocks"], c["blocks_labeled"])
        cmp.value(f"reading {n} ({f}): labeled with a check", r["blocks_labeled_with_a_check"], c["label_check"])
        cmp.value(f"reading {n} ({f}): labeled none", r["blocks_labeled_none"], c["label_none"])
        cmp.value(f"reading {n} ({f}): labeled by-param", r["blocks_labeled_by_param"], c["label_by_param"])

    # -- agreement --
    cmp.value("included blocks", sec["inputs"]["included blocks"], len(agreement_rows))
    ag = sec["agreement"]
    if two:
        cats = ag["categories"]
        cmp.unmapped_keys("agreement: category ids", "AGREEMENT_CATEGORIES", "second", cats["ids"],
                          AGREEMENT_CATEGORIES)
        cmp.unmapped_keys("agreement: category counts", "AGREEMENT_CATEGORIES", "second", cats["counts"],
                          AGREEMENT_CATEGORIES)
        cmp.unmapped_keys("agreement: counts.json agreement", "AGREEMENT_CATEGORIES", "first",
                          counts["agreement"], AGREEMENT_CATEGORIES)
        cmp.unmapped_keys("agreement: agreement.csv category", "AGREEMENT_CATEGORIES", "first",
                          [r["category"] for r in agreement_rows], AGREEMENT_CATEGORIES)
        for cat in AGREEMENT_CATEGORIES:
            cmp.set(f"agreement: blocks '{cat}'", cats["ids"][cat],
                    [r["block"] for r in agreement_rows if r["category"] == cat])
            cmp.value(f"agreement: count '{cat}'", cats["counts"][cat], counts["agreement"].get(cat, 0))
        first_check = [r["block"] for r in agreement_rows if r["category"] == "same check"]
        first_none = [r["block"] for r in agreement_rows if r["category"] == "both none"]
    else:
        cmp.value("agreement: every row 'single'", True, all(r["category"] == "single" for r in agreement_rows))
        first_check = [r["block"] for r in agreement_rows if r["label_1"] and r["label_1"] != NONE]
        first_none = [r["block"] for r in agreement_rows if r["label_1"] == NONE]
    cmp.set("blocks with an agreed label naming a check", ag["blocks_with_an_agreed_label_naming_a_check_ids"],
            first_check)
    cmp.set("blocks with agreed label none", ag["blocks_with_agreed_label_none_ids"], first_none)
    # labels of each reading per block, through the first case of each block whose label is not by-param
    first_labels = {r["block"]: [r["label_1"], r["label_2"]] for r in agreement_rows}
    sec_labels: dict[str, list] = {}
    for k in sorted(cases):
        row = cases[k]
        b = row["block"]
        if b in sec_labels or b not in first_labels:
            continue
        if any(first_labels[b][i].startswith("by-param ") for i in range(len(names))):
            continue
        sec_labels[b] = [lab_out(row["labels"][n]) for n in names]
    cmp.table("labels of each reading per block (blocks with a case)", sec_labels,
              {b: first_labels[b][:len(names)] for b in sec_labels})
    if two:
        st = counts.get("agreement_statistics", {})
        for sform, fform in (("every_label_text_as_a_category", "labels"), ("names_a_check_or_none", "check_or_none")):
            s, f = ag[sform], st.get(fform, {})
            cmp.value(f"kappa {fform}: units", s["units"], f.get("items"))
            cmp.value(f"kappa {fform}: categories", s["categories"], f.get("categories"))
            cmp.value(f"kappa {fform}: agree", s["agree"], f.get("equal"))
            cmp.value(f"kappa {fform}: observed", round4(s.get("observed_agreement_fraction")), f.get("observed"))
            cmp.value(f"kappa {fform}: expected", round4(s.get("expected_agreement_fraction")), f.get("expected"))
            cmp.value(f"kappa {fform}: kappa", round4(s.get("kappa_fraction")), f.get("kappa"))
            sum_st = summary_lib["agreement_statistics"].get(fform) if summary_lib is not None else None
            for ffield, frfield, ckey, skey in FLOAT_FIELDS:
                if ffield not in s:
                    cmp.skipped.append(f"kappa {fform}: {ffield}: the second output has no such field")
                    continue
                fl = s[ffield]
                cmp.value(f"kappa {fform}: {ffield} (float) against its own fraction rounded to 9 places",
                          fl, None if s.get(frfield) is None else round(float(Fraction(s[frfield])), 9))
                if ckey in f:
                    cmp.value(f"kappa {fform}: {ffield} (float) rounded to 4 places against counts.json",
                              None if fl is None else round(fl, 4), f[ckey])
                else:
                    cmp.skipped.append(f"kappa {fform}: {ffield} (float): counts.json has no '{ckey}'")
                if sum_st is None:
                    cmp.skipped.append(f"kappa {fform}: {frfield}: no summary.json entry for this subject "
                                       f"and form")
                elif skey not in sum_st:
                    cmp.skipped.append(f"kappa {fform}: {frfield}: summary.json has no '{skey}'")
                else:
                    cmp.value(f"kappa {fform}: {frfield} against summary.json (exact)",
                              frac_text(s.get(frfield)), frac_text(sum_st[skey]))
    else:
        cmp.skipped.append("kappa: 1 reading")

    # -- outcomes --
    oc = sec["outcomes"]["agreed"]["outcomes"]["counts"]
    cmp.unmapped_keys("outcome count", "OUTCOME_MAP", "second", oc, OUTCOME_MAP)
    cmp.unmapped_keys("outcome count (counts.json)", "OUTCOME_MAP", "first", counts["outcomes"],
                      OUTCOME_MAP.values())
    for sk, fk in OUTCOME_MAP.items():
        cmp.value(f"outcome count '{fk}'", oc.get(sk, 0), counts["outcomes"].get(fk, 0))
    # an outcome name the table lacks stays as it is, so that the case also differs in the table
    sec_out = {k: cmp.mapped(f"outcome per case {k}", "OUTCOME_MAP", OUTCOME_MAP, r["outcomes"]["agreed"],
                             r["outcomes"]["agreed"])
               for k, r in cases.items() if r["outcomes"]["agreed"]}
    first_out = {key(r): r["outcome"] for r in outcome_rows}
    cmp.table("outcome per case", sec_out, first_out)
    common = sorted(set(sec_out) & set(first_out))
    by_key = {key(r): r for r in outcome_rows}
    cmp.table("agreed label per case with an outcome", {k: cases[k]["labels"]["agreed"] for k in common},
              {k: by_key[k]["label"] for k in common})
    cmp.table("deciding check per case with an outcome",
              {k: cases[k]["deciding_check"] or NOT_A_CHECK for k in common},
              {k: by_key[k]["deciding"] if by_key[k]["deciding"] in check_ids else NOT_A_CHECK for k in common})

    def fired_text(row: dict) -> str:
        lab = row["labels"]["agreed"]
        return "yes" if lab in (row["fired"] or []) or lab == row["deciding_check"] else "no"
    cmp.table("label fired per case with an outcome", {k: fired_text(cases[k]) for k in common},
              {k: by_key[k]["label_fired"] for k in common})
    cmp.set("shadowed by the agreed label", sec["shadowed"]["by_agreed_label_ids"],
            [k for k, v in first_out.items()
             if v == "label does not fire and decides once the deciding check is deleted"])
    # counts of shadowed cases against the size of their sets (inside the second output) and the first side
    sh = sec["shadowed"]
    cmp.value("shadowed_cases_count against the size of shadowed_cases_with_sources",
              sh["shadowed_cases_count"], len(sh["shadowed_cases_with_sources"]))
    cmp.value("shadowed by_agreed_label against the size of by_agreed_label_ids",
              sh["by_agreed_label"], len(sh["by_agreed_label_ids"]))
    cmp.value("shadowed by_rule_2_target_in_place_of_the_label against the size of its ids",
              sh["by_rule_2_target_in_place_of_the_label"], len(sh["by_rule_2_target_in_place_of_the_label_ids"]))
    for n in sorted(sh["by_reading"]):
        cmp.value(f"shadowed by reading {n}: count against the size of its ids",
                  sh["by_reading"][n]["count"], len(sh["by_reading"][n]["ids"]))
    cmp.value("shadowed by_agreed_label against counts.json outcomes",
              sh["by_agreed_label"], counts["outcomes"].get(SHADOWED_OUTCOME, 0))
    cmp.skipped.append("shadowed by_rule_2_target_in_place_of_the_label and by_reading: no first counterpart "
                       "(compared only with the size of their sets)")

    # -- program against label --
    cmp.unmapped_keys("rule-vs-label.csv rule", "RULES", "first", [r["rule"] for r in rvl_rows], RULES)
    cmp.unmapped_keys("rule-vs-label-blocks.csv rule", "RULES", "first", [r["rule"] for r in rvlb_rows], RULES)
    for rule in RULES:
        f_rows = [r for r in rvl_rows if r["rule"] == rule]
        s_has = isinstance(sec["program_vs_label"].get(rule), dict)
        if not f_rows or not s_has:
            cmp.skipped.append(f"{rule}: given to the second script {s_has}, in the first outputs "
                               f"{bool(f_rows)}")
            continue
        pv = sec["program_vs_label"][rule]
        cmp.unmapped_keys(f"{rule} per case: category ids", "PVL_CASE_MAP", "second", pv["per_case"]["ids"],
                          PVL_CASE_MAP)
        cmp.unmapped_keys(f"{rule} per case: category counts", "PVL_CASE_MAP", "second",
                          pv["per_case"]["counts"], PVL_CASE_MAP)
        cmp.unmapped_keys(f"{rule} per case: counts.json rule_vs_label all", "PVL_CASE_MAP", "first",
                          counts["rule_vs_label"][rule]["all"], PVL_CASE_MAP.values())
        # a category name the table lacks stays as it is, so that its cases also differ in the table
        cat_of = {k: (PVL_CASE_MAP[c] if c in PVL_CASE_MAP else c)
                  for c, ids in pv["per_case"]["ids"].items() for k in ids}
        s_tab, f_tab = {}, {}
        for k, row in cases.items():
            t = row[rule]
            s_tab[k] = {"target": t["target"] or "", "tier": t["tier"] if t["target"] else "none",
                        "label": lab_out(row["labels"]["agreed"]), "category": cat_of.get(k)}
        for r in f_rows:
            f_tab[key(r)] = {"target": r["target"], "tier": r["tier"], "label": r["label"],
                             "category": r["category"]}
        cmp.table(f"{rule} per case", s_tab, f_tab)
        f_all = counts["rule_vs_label"][rule]["all"]
        for sc, fc in PVL_CASE_MAP.items():
            cmp.value(f"{rule} per case: count '{fc}'", pv["per_case"]["counts"][sc], f_all.get(fc, 0))
        s_tier = {}
        for tier, v in pv["per_case_by_tier"].items():
            ft = TIER_OF_NO_TARGET["first"] if tier == TIER_OF_NO_TARGET["second"] else tier
            s_tier[ft] = {cmp.mapped(f"{rule} per case: tier '{tier}': category", "PVL_CASE_MAP",
                                     PVL_CASE_MAP, c, c): n for c, n in v["counts"].items()}
        for tier, v in counts["rule_vs_label"][rule]["by_tier"].items():
            cmp.unmapped_keys(f"{rule} per case: counts.json by_tier '{tier}'", "PVL_CASE_MAP", "first", v,
                              PVL_CASE_MAP.values())
        f_tier = {t: v for t, v in counts["rule_vs_label"][rule]["by_tier"].items() if sum(v.values())}
        s_tier = {t: v for t, v in s_tier.items() if sum(v.values())}
        cmp.table(f"{rule} per case: counts by tier", s_tier, f_tier)
        # per block
        fb_rows = [r for r in rvlb_rows if r["rule"] == rule]
        cmp.unmapped_keys(f"{rule} per block: category ids", "PVL_BLOCK_MAP", "second", pv["per_block"]["ids"],
                          PVL_BLOCK_MAP)
        cmp.unmapped_keys(f"{rule} per block: category counts", "PVL_BLOCK_MAP", "second",
                          pv["per_block"]["counts"], PVL_BLOCK_MAP)
        cmp.unmapped_keys(f"{rule} per block: counts.json rule_vs_label_blocks all", "PVL_BLOCK_MAP", "first",
                          counts["rule_vs_label_blocks"][rule]["all"], PVL_BLOCK_MAP.values())
        cell_of = {b: (PVL_BLOCK_MAP[c] if c in PVL_BLOCK_MAP else c)
                   for c, ids in pv["per_block"]["ids"].items() for b in ids}
        tier_of = {b: t for t, v in pv["per_block_by_tier"].items() for ids in v["ids"].values() for b in ids}
        basis_of = {b: t for t, v in pv["per_block_by_basis"].items() for ids in v["ids"].values() for b in ids}
        target_of = {row["block"]: row[rule]["target"] or "" for row in cases.values()}
        s_btab, f_btab = {}, {}
        for b in cell_of:
            s_btab[b] = {"cell": cell_of[b],
                         "tier": "" if tier_of.get(b) == "no target" else tier_of.get(b),
                         "basis": "" if basis_of.get(b) == "no target" else basis_of.get(b)}
            if b in target_of:
                s_btab[b]["target"] = target_of[b]
        for r in fb_rows:
            f_btab[r["block"]] = {"cell": r["cell"], "tier": r["tier"], "basis": r["basis"]}
            if r["block"] in target_of:
                f_btab[r["block"]]["target"] = r["target"]
        cmp.table(f"{rule} per block", s_btab, f_btab)
        fb_all = counts["rule_vs_label_blocks"][rule]["all"]
        for sc, fc in PVL_BLOCK_MAP.items():
            cmp.value(f"{rule} per block: count '{fc}'", pv["per_block"]["counts"][sc], fb_all.get(fc, 0))
        s_basis = {}
        for basis, v in pv["per_block_by_basis"].items():
            s_basis[basis] = {cmp.mapped(f"{rule} per block: basis '{basis}': category", "PVL_BLOCK_MAP",
                                         PVL_BLOCK_MAP, c, c): n for c, n in v["counts"].items()}
        f_basis: dict[str, dict] = {}
        for basis, v in counts["rule_vs_label_blocks"][rule]["by_basis"].items():
            cmp.unmapped_keys(f"{rule} per block: counts.json by_basis '{basis}'", "PVL_BLOCK_MAP", "first", v,
                              PVL_BLOCK_MAP.values())
            b = "no target" if basis.startswith("none: ") else basis
            acc = f_basis.setdefault(b, {c: 0 for c in PVL_BLOCK_MAP.values()})
            for c, n in v.items():
                acc[c] = acc.get(c, 0) + n
        cmp.table(f"{rule} per block: counts by basis", s_basis, f_basis)

    # -- first reading --
    fpath = first_dir / "first-reading.csv"
    fr = sec["first_reading"]
    fc = counts.get("first_reading", {})
    if fr.get("given") and fpath.is_file():
        rows = read_csv(fpath)
        cmp.value("first reading: flags", fr["rows"], fc.get("flags"))
        mapped = {"yes": 0, "no": 0, "": 0}
        for c, n in fr["categories"]["counts"].items():
            m = cmp.mapped("first reading: category count", "FIRST_MAP", FIRST_MAP, c)
            if m is not None:
                mapped[m] += n
        for m, ck in FIRST_COUNT_MAP.items():
            cmp.value(f"first reading: {ck}", mapped[m], fc.get(ck))
        s_tab, f_tab = {}, {}
        for k, v in fr["per_flag"].items():
            row = cases.get(k, {})
            labs = [lab_out(row.get("labels", {}).get(n)) for n in names] + ([""] if len(names) == 1 else [])
            s_tab[k] = {"class": v["class"], "described": v["described_check"] or "",
                        "target": v["rule 2 target"] or "", "deciding": v["deciding_check"] or "",
                        "label_1": labs[0], "label_2": labs[1], "agreed": lab_out(v["agreed_label"]),
                        "equal": cmp.mapped(f"first reading per flag {k}: category", "FIRST_MAP", FIRST_MAP,
                                            v["category"])}
        for k in s_tab:
            if not s_tab[k]["deciding"]:
                s_tab[k]["deciding"] = NOT_A_CHECK
        for r in rows:
            # the transcription copies the raise site of flags.csv, a text when the site is no check
            dec = r["deciding_check"] if r["deciding_check"] in check_ids else NOT_A_CHECK
            f_tab[key(r)] = {"class": r["class"], "described": r["described_first"], "target": r["target"],
                             "deciding": dec, "label_1": r["label_1"], "label_2": r["label_2"],
                             "agreed": r["agreed_label"], "equal": r["agreed_equals_described"]}
        cmp.table("first reading per flag", s_tab, f_tab)
        cmp.skipped.append("first reading per flag: the category is compared only through the column "
                           "agreed_equals_described; 3 categories share the empty value and 2 share 'no'")
    else:
        cmp.skipped.append(f"first reading: given to the second script {bool(fr.get('given'))}, "
                           f"first-reading.csv present {fpath.is_file()}")

    # -- shadowed rows of mutants/cases_file.py --
    if shadowed_csv is not None:
        f_rows = read_csv(shadowed_csv)
        f_set = {(r["case"], r["described"], r["source"]) for r in f_rows}
        per: dict[tuple, set] = {}
        for k in sec["shadowed"]["by_agreed_label_ids"]:
            per.setdefault((k, cases[k]["labels"]["agreed"]), set()).add("labels")
        for k, v in sec["shadowed"]["first_reading_class_a_rows"].items():
            per.setdefault((k, v["rule 2 target"]), set()).add("first reading")
        s_set = {(k, d, " and ".join(x for x in ("labels", "first reading") if x in src))
                 for (k, d), src in per.items()}
        cmp.set("shadowed rows (case, described, source)", [" | ".join(x) for x in s_set],
                [" | ".join(x) for x in f_set])
        f_cases = {r["case"] for r in f_rows}
        cmp.value("shadowed_cases_count against the distinct cases of shadowed.csv",
                  sec["shadowed"]["shadowed_cases_count"], len(f_cases))
        cmp.set("shadowed cases (set) against the cases of shadowed.csv",
                sec["shadowed"]["shadowed_cases_with_sources"].keys(), f_cases)
    else:
        cmp.skipped.append("shadowed.csv of mutants/cases_file.py: not given")

    # -- summary.json of labels/summary.py: shadowed count and expectations L1, L2, L3 --
    if summary_lib is None:
        cmp.skipped.append("summary.json: not given or no entry for this subject; L1, L2, L3, the exact "
                           "kappa fractions and cases.shadowed are not compared")
        return cmp
    cmp.value("shadowed by_agreed_label against summary.json cases.shadowed",
              sec["shadowed"]["by_agreed_label"], summary_lib["cases"]["shadowed"])
    se, fe = sec.get("expectations", {}), summary_lib.get("expectations", {})
    cmp.unmapped_keys("expectations", "EXPECTATION_MAP", "second", se, EXPECTATION_MAP)
    cmp.unmapped_keys("expectations (summary.json)", "EXPECTATION_MAP", "first", fe, EXPECTATION_MAP.values())
    for sk, fk in EXPECTATION_MAP.items():
        if sk not in se or fk not in fe:
            cmp.skipped.append(f"{sk}: in the second output {sk in se}, in summary.json ('{fk}') {fk in fe}")
            continue
        s, f = se[sk], fe[fk]
        if "reason" in s:
            cmp.skipped.append(f"{sk}: the second output gives no units ({s['reason']})")
            continue
        cmp.value(f"{sk}: units", s["units"], f["units"])
        cmp.value(f"{sk}: units that hold", s["holding"], f["hold"])
        cmp.value(f"{sk}: status", s["status"], f["status"])
        units = set(s["units_ids"])
        if "holding_ids" in s:
            not_holding = units - set(s["holding_ids"])
            cmp.value(f"{sk}: holding against the size of holding_ids (second)", s["holding"], len(s["holding_ids"]))
        else:
            not_holding = set(s["not_holding"])
            cmp.value(f"{sk}: holding against units minus not_holding (second)", s["holding"],
                      s["units"] - len(not_holding))
        cmp.value(f"{sk}: units against the size of units_ids (second)", s["units"], len(units))
        cmp.set(f"{sk}: unit cases", units, [u["case"] for u in f["unit_rows"]])
        cmp.set(f"{sk}: cases that do not hold", not_holding, f["not_holding"])
    return cmp


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--second", required=True, type=Path)
    ap.add_argument("--first-dir", required=True, type=Path)
    ap.add_argument("--subject", required=True, type=Path)
    ap.add_argument("--shadowed", type=Path)
    ap.add_argument("--summary", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    try:
        sec = json.loads(a.second.read_text(encoding="utf-8"))
        checks = json.loads((a.subject.parent / "checks.json").read_text(encoding="utf-8"))
        check_ids = {c["id"] for c in checks["checks"]}
        summary_lib = None
        if a.summary is not None:
            summary_lib = json.loads(a.summary.read_text(encoding="utf-8"))["libraries"].get(sec.get("subject"))
        cmp = compare(sec, a.first_dir, check_ids, a.shadowed, summary_lib)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"bad input: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"{sec.get('subject')}: compared {cmp.compared}, agree {cmp.agree}, differ {len(cmp.differences)}")
    for s in cmp.skipped:
        print(f"  not compared: {s}")
    for d in cmp.differences:
        if d.get("set"):
            print(f"  DIFFER {d['value']}: sizes second {d['sizes'][0]}, first {d['sizes'][1]}")
            for x in d["only_second"]:
                print(f"    only in second: {x}")
            for x in d["only_first"]:
                print(f"    only in first: {x}")
        else:
            note = f" ({d['note']})" if d.get("note") else ""
            print(f"  DIFFER {d['value']}: second {json.dumps(d['second'], sort_keys=True)}, "
                  f"first {json.dumps(d['first'], sort_keys=True)}{note}")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"subject": sec.get("subject"), "compared": cmp.compared, "agree": cmp.agree,
                                      "differ": len(cmp.differences), "not_compared": cmp.skipped,
                                      "differences": cmp.differences, "table": TABLE},
                                     indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if cmp.differences else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
