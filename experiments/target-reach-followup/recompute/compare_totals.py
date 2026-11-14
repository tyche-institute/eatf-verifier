"""Compare the cross-library totals of recompute/second_totals.py with the
first outputs: the summary.json of labels/summary.py and the compare.json of
trace/analyse3.py, the latter summed over the libraries.

    python3 -I -B recompute/compare_totals.py \
        [--totals recompute/out/second_totals.json] \
        [--summary generated/labels/summary.json] \
        [--trace generated/trace/compare.json] [--trace-dir generated/trace] \
        [--second-dir recompute/out] \
        [--names google-auth oauthlib authlib joserfc] [--json differences.json]

Default paths are relative to the folder target-reach-followup; a path given
on the command line is read as given.

Inputs:

- --totals: the output of recompute/second_totals.py.
- --summary: the output of labels/summary.py. Its part "together" holds the
  totals over the libraries; its part "libraries" holds the same values per
  library.
- --trace: the output of trace/analyse3.py, a list with 1 entry per subject.
  Only the entries of --names are read, and their counts are summed.
- --trace-dir: the folder of the per-subject compare.csv of analyse3.py. It
  is read for T2 only (the transition of the class-A cases of joserfc).
- --second-dir: the folder of the per-library outputs of
  recompute/second_labels.py, read as <second-dir>/<name>/second_labels.json.
  Its parts "expectations" and "first_reading" give the identifiers of the
  units and the category of each flag.

Compared values, for the libraries together ("pooled") and, where both
sides hold them, for each library:

- Blocks and agreement categories. The agreement statistics in the 2
  forms, every label text as a category and names a check or none, and,
  pooled only, the variant with the label qualified by its library. For
  each: units, categories, agreeing units, and observed agreement, expected
  agreement and kappa, each as an exact fraction and as the value rounded
  to 4 places. Pooled only, the label texts other than none that are used
  in 2 or more libraries.
- Cases: the counts by agreed label, the outcomes, the shadowed cases.
- Program against label, for rule 2 and rule 3, for all tiers and each
  tier: the count per category and the derived counts.
- First reading: flags, flags per class, the count per category per class
  and in total.
- L1, L2 and L3, overall and per library: units, units that hold, status.
- From second_labels.json, per library and pooled, for L1, L2, L3 and the
  supplement "L3, rule 3": the set of unit cases and the set of cases that
  do not hold, as sets of case keys. Pooled, a key is prefixed with its
  library, as in summary.json. For "L3, rule 3" also the units, the units
  that hold and the status.
- From second_labels.json, per unit:
    - L1: whether it holds, the rule-2 target and the 2 labels as an
      unordered pair;
    - L2: whether it holds, the rule-2 target and the agreed label;
    - L3 and "L3, rule 3": the target and the agreed label of each unit
      that does not hold.
- From second_labels.json, per flag of the first reading: the set of
  flags, and for each flag its class, its category, its rule-2 target, its
  agreed label, its described check and whether the agreed label equals the
  rule-2 target. From the last, per class, per library and pooled, the
  counts against agreed_label_equals_target_by_class of summary.json.
- From compare.json, summed over --names and for each library: for rule 2
  and rule 3, for all tiers and the assertion and name tiers, the cases
  with a target, the cases decided by the target and the flags. Also the
  case transitions between the rules, with the cases decided by the rule-2
  target and by the rule-3 target.
- T1 and T3, per library: the flags under both rules, the cases decided by
  the target and the cases with a target, and the fractions.
- T2 for joserfc: the class-A cases (against the class-A flags of
  summary.json) and how many keep their target (transition "same target" in
  compare.csv).

Definitions:

- The 2 sides name categories differently. NAME_MAP below maps every name of
  the second output to the name or names of the first outputs. When several
  first names map to 1 second name, the first counts are summed. A name on
  either side that the table does not map is a difference. A mapped name
  that 1 side does not write counts as 0 (summary.py writes "unclassified"
  only when it occurs).
- The category of 1 flag is compared through the same entries of NAME_MAP:
  the first name is mapped to the 1 second name whose entry holds it. A
  category name on either side that the table does not map is a difference.
- An exact fraction is compared in lowest terms as "numerator/denominator".
- compare.json gives the decided counts of a transition only for the cases
  that change, gain or lose a target ("decides_rule2_to_rule3_for_moved_cases",
  keys "<rule-2 decides> -> <rule-3 decides>", where "no target" means no
  target). The decided counts of the cases that keep their target are
  derived: the decided cases of the rule minus the decided moved cases. The
  cases without a target under either rule are decided by no target, by
  definition.

Values that 1 side does not hold are listed under "not compared", with the
reason.

Output: "compared N, agree N, differ N", each value not compared and each
difference on 1 line; with --json, the same as JSON. Exit status: 0 when no
compared value differs, 1 when a compared value differs, 2 on bad input (a
missing file, unreadable JSON or CSV, a missing key, or a name of --names
that an input does not hold).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from fractions import Fraction
from pathlib import Path

DEFAULT_NAMES = ["google-auth", "oauthlib", "authlib", "joserfc"]
T_SUBJECT = "joserfc"

# The 1 table of names: group -> list of (second name, [first names]). Several first names in 1 entry are summed.
NAME_MAP = {
    # agreement categories: second_totals agreement.pooled.categories -> summary together.blocks.categories
    "agreement category": [
        ("same check", ["same check"]),
        ("both none", ["both none"]),
        ("1 check and 1 none", ["1 check and 1 none"]),
        ("2 different checks", ["2 different checks"]),
    ],
    # agreement forms: second form -> summary form
    "agreement form": [
        ("every_label_text_as_a_category", ["agreement_statistics.labels"]),
        ("names_a_check_or_none", ["agreement_statistics.check_or_none"]),
        ("every_label_text_qualified_by_library_variant",
         ["agreement_statistics_variant.labels_qualified_by_library"]),
    ],
    # fields of an agreement form
    "agreement field": [
        ("units", ["items"]),
        ("categories", ["categories"]),
        ("agreeing_units", ["equal"]),
        ("observed_agreement", ["observed"]),
        ("expected_agreement", ["expected"]),
        ("kappa", ["kappa"]),
    ],
    # case counts: second cases.pooled -> summary together.cases
    "case count": [
        ("cases_of_the_study", ["cases"]),
        ("agreed_label_names_a_check", ["agreed_label_check"]),
        ("agreed_label_none", ["agreed_label_none"]),
        ("agreed_label_missing", ["no_agreed_label"]),
        ("shadowed_by_agreed_label", ["shadowed"]),
    ],
    # outcomes: second cases.pooled.outcomes -> summary together.cases.outcomes
    "outcome": [
        ("1 decided by its label", ["decided by its label"]),
        ("2 label fires and another check decides", ["label fires and another check decides"]),
        ("3 label fires and no check decides", ["label fires and no check decides"]),
        ("4 label does not fire and no check decides", ["label does not fire and no check decides"]),
        ("5 deciding check not deleted or record missing", ["deciding check not deleted or record missing"]),
        ("6 label does not fire; case not observed on the copy without the deciding check",
         ["label does not fire; case not observed on the copy without the deciding check"]),
        ("7 label does not fire and decides once the deciding check is deleted",
         ["label does not fire and decides once the deciding check is deleted"]),
        ("8 label does not fire and does not decide then either",
         ["label does not fire and does not decide then either"]),
        ("fired checks not recorded", ["fired checks not recorded"]),
    ],
    # program against label, category per case: second -> summary rules[...].categories
    "program against label category": [
        ("target equals agreed label", ["target equals label"]),
        ("target differs from agreed label", ["target differs from label"]),
        ("target given, agreed label none", ["label none"]),
        ("no target, agreed label names a check", ["no target"]),
        ("both none", ["target and label none"]),
        ("no agreed label", ["no agreed label"]),
    ],
    # program against label, derived counts: second -> summary (the entry "with_target - ..." is derived)
    "program against label count": [
        ("cases_with_a_target", ["with_target"]),
        ("cases_with_a_target_and_an_agreed_label", ["with_target_and_agreed_label"]),
        ("cases_with_a_target_and_no_agreed_label", ["with_target - with_target_and_agreed_label"]),
        ("target_equals_label", ["target_equals_label"]),
        ("target_is_not_the_label", ["target_is_not_the_agreed_label"]),
        ("target_is_not_the_label_another_check", ["target_differs_from_label"]),
        ("target_is_not_the_label_agreed_label_none", ["target_while_label_none"]),
    ],
    # tiers: second -> summary (rules[...].by_tier, "all")
    "tier": [
        ("all tiers", ["all"]),
        ("assertion", ["assertion"]),
        ("name", ["name"]),
        ("no target", ["none"]),
    ],
    # first-reading categories: second first_reading.pooled -> summary together.first_reading.by_class
    "first-reading category": [
        ("agreed label equals described check", ["agreed label equals the described check"]),
        ("agreed label differs from described check",
         ["agreed label names another check than the described one"]),
        ("agreed label none, described check given", ["agreed label none, described check given"]),
        ("agreed label none, no described check", ["agreed label none, no described check given"]),
        ("agreed label names a check, no described check", ["unclassified"]),
        ("no agreed label", ["no agreed label, described check given", "no agreed label, no described check given"]),
    ],
    # expectations: second expectations_labels -> summary expectations
    "expectation": [("L1", ["L1"]), ("L2", ["L2"]), ("L3", ["L3"])],
    "expectation field": [("units", ["units"]), ("holding", ["hold"]), ("status", ["status"])],
    # expectations with case keys: second_labels expectations -> summary expectations
    "expectation with case keys": [("L1", ["L1"]), ("L2", ["L2"]), ("L3", ["L3"]),
                                   ("L3_with_rule_3_targets_supplementary", ["L3, rule 3"])],
    # rule counts: second rules.rule2|rule3.pooled -> compare.json rule2|rule3
    "rule": [("rule2", ["rule2"]), ("rule3", ["rule3"])],
    "rule tier": [("all tiers", ["all"]), ("assertion", ["assertion"]), ("name", ["name"])],
    "rule count": [
        ("cases_with_a_target", ["cases_with_a_target"]),
        ("decided_by_the_target", ["decided_by_the_target"]),
        ("not_decided_by_the_target", ["not_decided_flags"]),
    ],
    # case transitions: second rules.transitions.pooled -> compare.json case_transitions
    "transition": [
        ("keeps its target", ["same target"]),
        ("changes its target", ["changed target"]),
        ("gains a target", ["gained a target"]),
        ("loses its target", ["lost a target"]),
        ("no target under either rule", ["no target under either"]),
    ],
}


# Per flag, a first-reading category of summary.json -> the 1 second name whose entry holds it.
FIRST_TO_SECOND_CATEGORY = {f: s for s, fs in NAME_MAP["first-reading category"] for f in fs}
assert len(FIRST_TO_SECOND_CATEGORY) == sum(len(fs) for _, fs in NAME_MAP["first-reading category"])


class BadInput(Exception):
    pass


class Comparison:
    def __init__(self) -> None:
        self.compared = 0
        self.agree = 0
        self.differences: list[dict] = []
        self.not_compared: list[str] = []

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
            self.differences.append({"value": name, "second": sorted(s - f), "first": sorted(f - s),
                                     "note": "members only in 1 side"})

    def unmapped(self, name: str, side: str, key: str) -> None:
        self.compared += 1
        self.differences.append({"value": name, "second": key if side == "second" else None,
                                 "first": key if side == "first" else None,
                                 "note": f"name of the {side} side not in NAME_MAP"})

    def mapped_counts(self, name: str, group: str, second: dict, first: dict) -> None:
        """Compare 2 dicts of counts through NAME_MAP[group]; unmapped names on either side are differences."""
        known_second = {s for s, _ in NAME_MAP[group]}
        known_first = {f for _, fs in NAME_MAP[group] for f in fs}
        for k in sorted(set(second) - known_second):
            self.unmapped(f"{name}: '{k}'", "second", k)
        for k in sorted(set(first) - known_first):
            self.unmapped(f"{name}: '{k}'", "first", k)
        for s, fs in NAME_MAP[group]:
            self.value(f"{name}: '{s}'", second.get(s, 0), sum(first.get(f, 0) for f in fs))


def frac_text(v) -> str | None:
    if v is None:
        return None
    f = Fraction(v["numerator"], v["denominator"])
    return f"{f.numerator}/{f.denominator}"


def value_of(v):
    return None if v is None else v.get("value")


def get_path(doc: dict, dotted: str):
    for part in dotted.split("."):
        doc = doc[part]
    return doc


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BadInput(f"cannot read {path}: {exc.strerror}") from exc
    except ValueError as exc:
        raise BadInput(f"unreadable JSON in {path}: {exc}") from exc


def agreement_part(cmp: Comparison, where: str, s_agr: dict, f_lib: dict, forms: list) -> None:
    """Blocks, agreement categories and the agreement forms of 1 part (pooled or 1 library)."""
    cmp.value(f"{where}: included blocks", s_agr["included_blocks"], f_lib["blocks"]["included"])
    cmp.value(f"{where}: blocks labeled by both readings (units of the text form)",
              s_agr["every_label_text_as_a_category"]["units"], f_lib["blocks"]["labeled_by_both"])
    cmp.value(f"{where}: blocks with the same label (agreeing units of the text form)",
              s_agr["every_label_text_as_a_category"]["agreeing_units"], f_lib["blocks"]["same_label"])
    cmp.mapped_counts(f"{where}: agreement category", "agreement category", s_agr["categories"],
                      f_lib["blocks"]["categories"])
    for sform, (fpath,) in NAME_MAP["agreement form"]:
        if sform not in forms:
            continue
        s, f = s_agr[sform], get_path(f_lib, fpath)
        for sfield, (ffield,) in NAME_MAP["agreement field"]:
            label = f"{where} {sform}: {sfield}"
            if sfield in ("observed_agreement", "expected_agreement", "kappa"):
                cmp.value(f"{label} (exact fraction)", frac_text(s.get(sfield)), frac_text(f.get(ffield)))
                cmp.value(f"{label} (4 places)", value_of(s.get(sfield)), value_of(f.get(ffield)))
            else:
                cmp.value(label, s[sfield], f[ffield])


def cases_part(cmp: Comparison, where: str, sc: dict, fc: dict) -> None:
    for s, (f,) in NAME_MAP["case count"]:
        cmp.value(f"{where} cases: {s}", sc[s], fc[f])
    cmp.value(f"{where} cases: outcome rows (sum of the outcomes)", sum(sc["outcomes"].values()), fc["outcome_rows"])
    cmp.value(f"{where} cases: decided by its label", sc["outcomes"]["1 decided by its label"],
              fc["decided_by_its_label"])
    cmp.mapped_counts(f"{where} outcome", "outcome", sc["outcomes"], fc["outcomes"])


def pvl_part(cmp: Comparison, where: str, rule: str, sp: dict, fr: dict) -> None:
    """Program against label of 1 rule: categories and derived counts per tier and for all tiers."""
    cmp.value(f"{where} {rule}: cases (sum of the categories, all tiers)",
              sum(sp["all tiers"]["categories"].values()), fr["all"]["cases"])
    known = {s for s, _ in NAME_MAP["tier"]}
    for t in sorted(set(sp) - known):
        cmp.unmapped(f"{where} {rule}: tier '{t}'", "second", t)
    known_f = {f for _, fs in NAME_MAP["tier"] for f in fs}
    for t in sorted((set(fr["by_tier"]) | {"all"}) - known_f):
        cmp.unmapped(f"{where} {rule}: tier '{t}'", "first", t)
    for st, (ft,) in NAME_MAP["tier"]:
        s = sp.get(st)
        f = fr["all"] if ft == "all" else fr["by_tier"].get(ft)
        if s is None or f is None:
            cmp.not_compared.append(f"{where} {rule} tier {st}: in second {s is not None}, in first {f is not None}")
            continue
        cmp.mapped_counts(f"{where} {rule} {st}: category", "program against label category",
                          s["categories"], f["categories"])
        for sk, (fk,) in NAME_MAP["program against label count"]:
            if fk == "with_target - with_target_and_agreed_label":
                fv = f["with_target"] - f["with_target_and_agreed_label"]
            else:
                fv = f[fk]
            cmp.value(f"{where} {rule} {st}: {sk}", s[sk], fv)


def first_part(cmp: Comparison, where: str, sf: dict, ff: dict) -> None:
    cmp.value(f"{where} first reading: flags", sf["flags"], ff["flags"])
    for c in sorted(set(sf["by_class"]) | set(ff["by_class"])):
        if c not in sf["by_class"] or c not in ff["by_class"]:
            cmp.value(f"{where} first reading: class {c} present", c in sf["by_class"], c in ff["by_class"])
            continue
        s_flags = sf["flags_by_class"][c] if "flags_by_class" in sf else sum(sf["by_class"][c].values())
        cmp.value(f"{where} first reading: flags of class {c}", s_flags, sum(ff["by_class"][c].values()))
        cmp.mapped_counts(f"{where} first reading class {c}", "first-reading category", sf["by_class"][c],
                          ff["by_class"][c])
    total_first: dict[str, int] = {}
    for c in ff["by_class"].values():
        for k, n in c.items():
            total_first[k] = total_first.get(k, 0) + n
    cmp.mapped_counts(f"{where} first reading total", "first-reading category", sf["total"], total_first)


def compare_labels_totals(cmp: Comparison, tot: dict, summ: dict, names: list[str]) -> None:
    tog = summ["together"]
    all_forms = [s for s, _ in NAME_MAP["agreement form"]]
    agreement_part(cmp, "pooled", tot["agreement"]["pooled"], tog, all_forms)
    for n in names:
        agreement_part(cmp, n, tot["agreement"]["per_library"][n], summ["libraries"][n], all_forms[:2])
    agr = tot["agreement"]
    cmp.value("pooled: label texts other than none in 2 or more libraries (count)",
              agr["label_texts_other_than_none_in_2_libraries"],
              len(tog["label_texts_other_than_none_in_2_or_more_libraries"]))
    cmp.set("pooled: label texts other than none in 2 or more libraries (set)",
            agr["label_texts_other_than_none_in_2_libraries_list"],
            tog["label_texts_other_than_none_in_2_or_more_libraries"])
    cmp.not_compared.append("marginals of the names form (pooled) and of both forms (per library): summary.json "
                            "holds no marginals")
    cases_part(cmp, "pooled", tot["cases"]["pooled"], tog["cases"])
    for n in names:
        cases_part(cmp, n, tot["cases"]["per_library"][n], summ["libraries"][n]["cases"])
    cmp.not_compared.append("cases agreed_label_missing_by_param_unresolved, shadowed_or_class_a, "
                            "class_a_cases_of_the_first_reading and the shadowed case ids: summary.json holds no "
                            "counterpart")
    for rule in ("rule 2", "rule 3"):
        pvl_part(cmp, "pooled", rule, tot["program_vs_label"][rule]["pooled"], tog["rules"][rule])
        for n in names:
            pvl_part(cmp, n, rule, tot["program_vs_label"][rule]["per_library"][n], summ["libraries"][n]["rules"][rule])
    first_part(cmp, "pooled", tot["first_reading"]["pooled"], tog["first_reading"])
    for n in names:
        ff = summ["libraries"][n]["first_reading"]
        if ff is None:
            cmp.not_compared.append(f"{n} first reading: summary.json holds none")
            continue
        first_part(cmp, n, tot["first_reading"]["per_library"][n], ff)
    se = tot["expectations_labels"]
    for sl, (fl,) in NAME_MAP["expectation"]:
        for sk, (fk,) in NAME_MAP["expectation field"]:
            cmp.value(f"{sl} overall: {sk}", se["overall"][sl][sk], tog["expectations"][fl][fk])
        for n in names:
            for sk, (fk,) in NAME_MAP["expectation field"]:
                cmp.value(f"{sl} {n}: {sk}", se["per_library"][n][sl][sk],
                          summ["libraries"][n]["expectations"][fl][fk])
    cmp.not_compared.append("summary.json 'L3, rule 3' (supplement) in second_totals.json: second_totals.json "
                            "does not total it; it is compared per library and pooled from second_labels.json")


def second_units(sl: str, e: dict) -> tuple[set, set]:
    """Unit cases and cases that do not hold of 1 expectation of second_labels.json."""
    units = set(e["units_ids"])
    if sl in ("L1", "L2"):
        return units, units - set(e["holding_ids"])
    return units, set(e["not_holding"])


def eq_target(agreed, target) -> str:
    """Whether the agreed label equals the rule-2 target, in the words of summary.py."""
    if not agreed:
        return "no agreed label"
    return "yes" if target and agreed == target else "no"


def expectation_ids_part(cmp: Comparison, n: str, s_exp: dict, f_exp: dict) -> None:
    """Unit sets, sets of units that do not hold and per-unit values of 1 library."""
    for sl, (fl,) in NAME_MAP["expectation with case keys"]:
        e, f = s_exp[sl], f_exp[fl]
        units, not_holding = second_units(sl, e)
        rows = {u["case"]: u for u in f["unit_rows"]}
        cmp.set(f"{fl} {n}: unit cases", units, rows)
        cmp.set(f"{fl} {n}: cases that do not hold", not_holding, f["not_holding"])
        if sl == "L3_with_rule_3_targets_supplementary":
            for sk, (fk,) in NAME_MAP["expectation field"]:
                cmp.value(f"{fl} {n}: {sk}", e[sk], f[fk])
        if sl in ("L1", "L2"):
            detail = e["detail"]
            cmp.set(f"{fl} {n}: cases of the detail against the unit cases", detail, rows)
            for k in sorted(set(detail) & set(rows)):
                d, u = detail[k], rows[k]
                cmp.value(f"{fl} {n} {k}: holds", d["holds"], u["holds"])
                cmp.value(f"{fl} {n} {k}: rule-2 target", d["rule 2 target"], u["target"])
                if sl == "L1":
                    cmp.value(f"{fl} {n} {k}: labels of the 2 readings (unordered)", sorted(d["labels"].values()),
                              sorted([u["label_1"], u["label_2"]]))
                else:
                    cmp.value(f"{fl} {n} {k}: agreed label", d["agreed label"], u["agreed_label"])
        else:
            for k in sorted(set(e["not_holding"]) & set(rows)):
                d, u = e["not_holding"][k], rows[k]
                cmp.value(f"{fl} {n} {k}: target", d["target"], u["target"])
                cmp.value(f"{fl} {n} {k}: agreed label", d["agreed label"], u["label"])


def first_flags_part(cmp: Comparison, n: str, per_flag: dict, ff: dict | None) -> dict:
    """Per-flag values of 1 library; returns the counts per class of whether the agreed label equals the target."""
    counts: dict[str, dict[str, int]] = {}
    for f in per_flag.values():
        c = counts.setdefault(f["class"], {"yes": 0, "no": 0, "no agreed label": 0})
        c[eq_target(f["agreed_label"], f["rule 2 target"])] += 1
    if ff is None:
        cmp.set(f"{n} first reading: flags (summary.json holds no first reading)", per_flag, [])
        return counts
    rows = {r["case"]: r for r in ff["rows"]}
    cmp.set(f"{n} first reading: flags", per_flag, rows)
    known_second = {s for s, _ in NAME_MAP["first-reading category"]}
    for k in sorted(set(per_flag) & set(rows)):
        s, r = per_flag[k], rows[k]
        where = f"{n} first reading {k}"
        cmp.value(f"{where}: class", s["class"], r["class"])
        if s["category"] not in known_second:
            cmp.unmapped(f"{where}: category '{s['category']}'", "second", s["category"])
        elif r["category"] not in FIRST_TO_SECOND_CATEGORY:
            cmp.unmapped(f"{where}: category '{r['category']}'", "first", r["category"])
        else:
            cmp.value(f"{where}: category", s["category"], FIRST_TO_SECOND_CATEGORY[r["category"]])
        cmp.value(f"{where}: rule-2 target", s["rule 2 target"], r["target"])
        cmp.value(f"{where}: agreed label", s["agreed_label"] or "", r["agreed_label"])
        cmp.value(f"{where}: described check", s["described_check"] or "", r["described_check"])
        cmp.value(f"{where}: agreed label equals the rule-2 target",
                  eq_target(s["agreed_label"], s["rule 2 target"]), r["agreed_label_equals_target"])
    cmp.value(f"{n} first reading: agreed label equals the rule-2 target, per class", counts,
              ff["agreed_label_equals_target_by_class"])
    return counts


def compare_second_labels(cmp: Comparison, summ: dict, names: list[str], second_dir: Path) -> None:
    """Case keys of the expectations and the per-flag first reading, from second_labels.json of each library."""
    tog = summ["together"]
    pooled_units: dict[str, set] = {}
    pooled_not: dict[str, set] = {}
    pooled_count: dict[str, list] = {}
    pooled_eq: dict[str, dict[str, int]] = {}
    for n in names:
        sl_doc = read_json(second_dir / n / "second_labels.json")
        if sl_doc.get("subject") != n:
            raise BadInput(f"{second_dir / n / 'second_labels.json'} is the output of {sl_doc.get('subject')!r}, "
                           f"not {n!r}")
        s_exp = sl_doc["expectations"]
        expectation_ids_part(cmp, n, s_exp, summ["libraries"][n]["expectations"])
        for sl, (fl,) in NAME_MAP["expectation with case keys"]:
            units, not_holding = second_units(sl, s_exp[sl])
            pooled_units.setdefault(fl, set()).update(f"{n}: {k}" for k in units)
            pooled_not.setdefault(fl, set()).update(f"{n}: {k}" for k in not_holding)
            acc = pooled_count.setdefault(fl, [0, 0])
            acc[0] += s_exp[sl]["units"]
            acc[1] += s_exp[sl]["holding"]
        counts = first_flags_part(cmp, n, sl_doc["first_reading"]["per_flag"], summ["libraries"][n]["first_reading"])
        for c, v in counts.items():
            acc = pooled_eq.setdefault(c, {"yes": 0, "no": 0, "no agreed label": 0})
            for k, x in v.items():
                acc[k] += x
    for _, (fl,) in NAME_MAP["expectation with case keys"]:
        f = tog["expectations"][fl]
        cmp.set(f"{fl} pooled: unit cases", pooled_units[fl], [u["case"] for u in f["unit_rows"]])
        cmp.set(f"{fl} pooled: cases that do not hold", pooled_not[fl], f["not_holding"])
        if fl == "L3, rule 3":
            units, holding = pooled_count[fl]
            st = "not applicable" if units == 0 else "held" if units == holding else "not held"
            cmp.value(f"{fl} pooled: units", units, f["units"])
            cmp.value(f"{fl} pooled: holding", holding, f["hold"])
            cmp.value(f"{fl} pooled: status", st, f["status"])
    cmp.value("pooled first reading: agreed label equals the rule-2 target, per class", pooled_eq,
              tog["first_reading"]["agreed_label_equals_target_by_class"])
    cmp.not_compared.append("the target and the agreed label of the units of L3 and 'L3, rule 3' that hold: "
                            "second_labels.json holds only their case keys")
    cmp.not_compared.append("second_labels.json first_reading.per_flag fields deciding_check and "
                            "agreed_label_outcome: summary.json rows hold no counterpart")
    cmp.not_compared.append("second_labels.json expectations fields class_c_flags, "
                            "class_c_flags_without_an_agreed_label_naming_a_check and readings_compared: "
                            "summary.json holds no counterpart")
    cmp.not_compared.append("the list 'checks' of summary.json and the lists 'checks' and 'checks_failed' of "
                            "second_totals.json: each holds the checks of its own program on its own inputs, "
                            "with no counterpart on the other side")


def sum_trace(trace: list, names: list[str]) -> dict:
    """compare.json entries of names, summed key by key."""
    by = {e["subject"]: e for e in trace}
    missing = [n for n in names if n not in by]
    if missing:
        raise BadInput(f"compare.json has no entry for {', '.join(missing)}")
    out = {"rule2": {}, "rule3": {}, "case_transitions": {}, "decides_rule2_to_rule3_for_moved_cases": {}}
    for n in names:
        e = by[n]
        for r in ("rule2", "rule3"):
            for tier, v in e[r].items():
                acc = out[r].setdefault(tier, {})
                for k, x in v.items():
                    acc[k] = acc.get(k, 0) + x
        for part in ("case_transitions", "decides_rule2_to_rule3_for_moved_cases"):
            for k, x in e[part].items():
                out[part][k] = out[part].get(k, 0) + x
    return out


def moved_decided(moves: dict) -> dict:
    """Decided counts per transition from the keys '<rule-2 decides> -> <rule-3 decides>'."""
    res = {t: {"count": 0, "rule2": 0, "rule3": 0} for t in ("changed target", "gained a target", "lost a target")}
    bad = []
    for k, n in moves.items():
        parts = [x.strip() for x in k.split("->")]
        ok = len(parts) == 2 and all(p in ("yes", "no", "no target") for p in parts)
        if not ok or parts[0] == parts[1] == "no target":
            bad.append(k)
            continue
        a, b = parts
        t = "gained a target" if a == "no target" else "lost a target" if b == "no target" else "changed target"
        res[t]["count"] += n
        res[t]["rule2"] += n if a == "yes" else 0
        res[t]["rule3"] += n if b == "yes" else 0
    res["unknown keys"] = bad
    return res


def trace_part(cmp: Comparison, where: str, s_rules: dict, s_trans: dict, tr: dict) -> None:
    """Rule counts per tier and the transitions with their decided counts of 1 part (pooled or 1 library)."""
    for sr, (fr,) in NAME_MAP["rule"]:
        sp = s_rules[sr]
        known = {s for s, _ in NAME_MAP["rule tier"]}
        for t in sorted(set(sp) - known):
            cmp.unmapped(f"{where} trace {sr}: tier '{t}'", "second", t)
        known_f = {f for _, fs in NAME_MAP["rule tier"] for f in fs}
        for t in sorted(set(tr[fr]) - known_f):
            cmp.unmapped(f"{where} trace {sr}: tier '{t}'", "first", t)
        for st, (ft,) in NAME_MAP["rule tier"]:
            for sk, (fk,) in NAME_MAP["rule count"]:
                cmp.value(f"{where} trace {sr} {st}: {sk}", sp[st][sk], tr[fr].get(ft, {}).get(fk))
    cmp.mapped_counts(f"{where} trace transition: count", "transition", {k: v["count"] for k, v in s_trans.items()},
                      tr["case_transitions"])
    md = moved_decided(tr["decides_rule2_to_rule3_for_moved_cases"])
    for k in md["unknown keys"]:
        cmp.unmapped(f"{where} trace moved-case key '{k}'", "first", k)
    for s_name, (f_name,) in NAME_MAP["transition"]:
        if f_name in md:
            cmp.value(f"{where} trace transition '{s_name}': count (sum of the moved-case keys)",
                      s_trans[s_name]["count"], md[f_name]["count"])
            cmp.value(f"{where} trace transition '{s_name}': decided by the rule-2 target",
                      s_trans[s_name]["decided_by_the_rule2_target"], md[f_name]["rule2"])
            cmp.value(f"{where} trace transition '{s_name}': decided by the rule-3 target",
                      s_trans[s_name]["decided_by_the_rule3_target"], md[f_name]["rule3"])
    moved = ("changed target", "gained a target", "lost a target")
    for r, key in (("rule2", "decided_by_the_rule2_target"), ("rule3", "decided_by_the_rule3_target")):
        cmp.value(f"{where} trace transition 'keeps its target': {key} (derived)", s_trans["keeps its target"][key],
                  tr[r]["all"]["decided_by_the_target"] - sum(md[t][r] for t in moved))
        cmp.value(f"{where} trace transition 'no target under either rule': {key} (0 by definition)",
                  s_trans["no target under either rule"][key], 0)


def compare_trace_totals(cmp: Comparison, tot: dict, summ: dict, trace: list, names: list[str],
                         trace_dir: Path) -> None:
    rules = tot["rules"]
    trace_part(cmp, "pooled", {r: rules[r]["pooled"] for r in ("rule2", "rule3")}, rules["transitions"]["pooled"],
               sum_trace(trace, names))
    for n in names:
        trace_part(cmp, n, {r: rules[r]["per_library"][n] for r in ("rule2", "rule3")},
                   rules["transitions"]["per_library"][n], sum_trace(trace, [n]))
    by = {e["subject"]: e for e in trace}
    plq = tot["expectations_rule"]["per_library_quantities"]
    for n in names:
        q, e = plq[n], by[n]
        cmp.value(f"T1 {n}: rule-2 flags", q["T1"]["rule2_flags"], e["rule2"]["all"]["not_decided_flags"])
        cmp.value(f"T1 {n}: rule-3 flags", q["T1"]["rule3_flags"], e["rule3"]["all"]["not_decided_flags"])
        cmp.value(f"T3 {n}: rule-3 decided", q["T3"]["rule3_decided_count"], e["rule3"]["all"]["decided_by_the_target"])
        cmp.value(f"T3 {n}: rule-3 cases with a target", q["T3"]["rule3_with_a_target"],
                  e["rule3"]["all"]["cases_with_a_target"])
        for r, key in (("rule3", "rule3_decided"), ("rule2", "rule2_decided")):
            wt = e[r]["all"]["cases_with_a_target"]
            fv = None if wt == 0 else {"numerator": e[r]["all"]["decided_by_the_target"], "denominator": wt}
            cmp.value(f"T3 {n}: {key} (exact fraction)", frac_text(q["T3"][key]), frac_text(fv))
    if T_SUBJECT not in names:
        cmp.not_compared.append(f"T2: {T_SUBJECT} is not among the names")
    else:
        t2 = plq[T_SUBJECT]["T2"]
        csv_path = trace_dir / T_SUBJECT / "compare.csv"
        try:
            with csv_path.open(encoding="utf-8", newline="") as fh:
                rows = {f"{r['test_node']}|{r['block']}|{r['index']}": r for r in csv.DictReader(fh)}
        except OSError as exc:
            raise BadInput(f"cannot read {csv_path}: {exc.strerror}") from exc
        except KeyError as exc:
            raise BadInput(f"missing column in {csv_path}: {exc}") from exc
        ids = t2["class_a_ids"]
        fa = summ["libraries"][T_SUBJECT]["first_reading"]
        cmp.value(f"T2 {T_SUBJECT}: class-A cases against the class-A flags of summary.json",
                  t2["class_a_cases"], sum(fa["by_class"].get("A", {}).values()))
        cmp.set(f"T2 {T_SUBJECT}: class-A case set against the class-A rows of summary.json", ids,
                [r["case"] for r in fa["rows"] if r["class"] == "A"])
        cmp.value(f"T2 {T_SUBJECT}: class-A cases found in compare.csv", len(ids), sum(1 for k in ids if k in rows))
        cmp.value(f"T2 {T_SUBJECT}: class-A cases that keep their target", t2["keep_their_target"],
                  sum(1 for k in ids if k in rows and rows[k]["transition"] == "same target"))
    cmp.not_compared.append("T1, T2 and T3 statuses (holds): no first output holds them as data; trace/README.md "
                            "states them in prose")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--totals", type=Path, default=Path("recompute/out/second_totals.json"))
    ap.add_argument("--summary", type=Path, default=Path("generated/labels/summary.json"))
    ap.add_argument("--trace", type=Path, default=Path("generated/trace/compare.json"))
    ap.add_argument("--trace-dir", type=Path, default=Path("generated/trace"))
    ap.add_argument("--second-dir", type=Path, default=Path("recompute/out"))
    ap.add_argument("--names", nargs="+", default=DEFAULT_NAMES)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    cmp = Comparison()
    try:
        tot, summ, trace = read_json(a.totals), read_json(a.summary), read_json(a.trace)
        for n in a.names:
            if n not in summ["libraries"] or n not in tot["expectations_labels"]["per_library"]:
                raise BadInput(f"no entry for {n} in summary.json or second_totals.json")
        if sorted(tot["inputs"]["names"]) != sorted(a.names):
            raise BadInput(f"second_totals.json totals {tot['inputs']['names']}, not {a.names}")
        if sorted(summ["arguments"]["names"]) != sorted(a.names):
            raise BadInput(f"summary.json totals {summ['arguments']['names']}, not {a.names}")
        compare_labels_totals(cmp, tot, summ, a.names)
        compare_trace_totals(cmp, tot, summ, trace, a.names, a.trace_dir)
        compare_second_labels(cmp, summ, a.names, a.second_dir)
    except BadInput as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        print(f"bad input: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"compared {cmp.compared}, agree {cmp.agree}, differ {len(cmp.differences)}")
    for s in cmp.not_compared:
        print(f"  not compared: {s}")
    for d in cmp.differences:
        note = f" ({d['note']})" if d.get("note") else ""
        print(f"  DIFFER {d['value']}: second {json.dumps(d['second'], sort_keys=True)}, "
              f"first {json.dumps(d['first'], sort_keys=True)}{note}")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"arguments": {"totals": str(a.totals), "summary": str(a.summary),
                                                    "trace": str(a.trace), "trace_dir": str(a.trace_dir),
                                                    "second_dir": str(a.second_dir),
                                                    "names": a.names},
                                      "compared": cmp.compared, "agree": cmp.agree,
                                      "differ": len(cmp.differences), "not_compared": cmp.not_compared,
                                      "differences": cmp.differences, "name_map": NAME_MAP},
                                     indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if cmp.differences else 0


if __name__ == "__main__":
    sys.exit(main())
