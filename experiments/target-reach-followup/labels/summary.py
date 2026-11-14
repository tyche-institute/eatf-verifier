"""Summarize the per-library outputs of analyse_labels.py over several libraries.

    python3 -I -B labels/summary.py [--generated generated/labels] \
        [--names google-auth oauthlib authlib joserfc] [--out generated/labels]

Default paths are relative to the folder target-reach-followup; a path given
on the command line is read as given. Nothing is run on the libraries.

Inputs, for each name in --names, in <generated>/<name>/: counts.json,
agreement.csv, outcomes.csv, rule-vs-label.csv and, when it exists,
first-reading.csv (the columns are described in labels/README.md).

Outputs: <out>/summary.json and <out>/SUMMARY.md, with the values below for
each library and for the libraries together ("together").

Definitions:

- Blocks: the rows of agreement.csv are the included blocks; a block is
  labeled by both readings when both label cells are filled. The 4
  agreement categories partition these blocks; the blocks with the same
  label are those of "same check" and "both none".
- Agreement statistics, over the blocks labeled by both readings, in 2
  forms: "labels" (each distinct label text of agreement.csv is a category)
  and "check_or_none" (the 2 categories "names a check" and "none"). For n
  items, the values are:
    - observed agreement p_o = equal / n;
    - expected agreement p_e = the sum over the categories of
      n1(k) * n2(k) / n^2, where n1(k) and n2(k) count the uses of category
      k by reading 1 and by reading 2;
    - kappa = (p_o - p_e) / (1 - p_e), null when p_e is 1 or n is 0.
  Each value is given as an exact fraction and as a float rounded to 4
  places. Together, the items are the
  blocks of all libraries and a label text is 1 category whatever its
  library. The variant "labels_qualified_by_library" prefixes each label
  text, "none" included, with its library; it is a variant, not the result.
- Cases: the rows of rule 2 in rule-vs-label.csv. The agreed label of a case
  is its label cell: a check id, "none", or empty (no agreed label). The
  outcomes are those of outcomes.csv; the shadowed outcome is "label does
  not fire and decides once the deciding check is deleted".
- Program against label, for each rule of rule-vs-label.csv, per tier and
  for all tiers: the count per category and the cases with a target. Of
  those, the cases with an agreed label (a check or none) are split into
  the cases whose target equals the agreed label and the cases whose target
  is not the agreed label ("target differs from label" plus "label none").
- First reading, from first-reading.csv, per class and in total, in 6
  categories that do not overlap (FIRST_CATEGORIES). A flag whose agreed
  label names a check while no described check is given falls in none of
  them and makes the partition check fail. For each flag, whether the
  agreed label equals its rule-2 target.
- Expectations L1 to L3 of section 2 of PROTOCOL.md, with their units:
    - L1: the class-A flags of joserfc. A unit holds when label_1 and
      label_2 of first-reading.csv both equal the rule-2 target.
    - L2: the class-C flags whose agreed label names a check. A unit holds
      when the agreed label differs from the rule-2 target.
    - L3: the cases of outcomes.csv whose deciding check is their rule-2
      target. A unit holds when the label is the target.
    - "L3, rule 3": the same as L3 with the rule-3 target. It is a
      supplement and not part of the expectations of the protocol.
  Status: "held" when every unit holds, "not held" when 1 does not, "not
  applicable" with 0 units.

Checks, each named in summary.json with whether it holds:

- the categories sum to the blocks, cases or flags that they partition;
- per library and together, the equal label texts of the agreement
  statistics "labels" equal the blocks of "same check" and "both none".
  Section 4.1 of PROTOCOL.md calls 2 labels the same after the values of a
  by-parameter label are sorted, while the statistics compare raw texts.
- the per-library agreement categories and statistics equal counts.json;
- the per-library case counts, outcomes, rule categories and first-reading
  counts equal counts.json;
- first-reading.csv and outcomes.csv agree with rule-vs-label.csv on the
  targets and labels of their cases.

In SUMMARY.md, the character | in a table cell is written as \\| so that a
case key does not split the cell.

Exit status: 0 when every check holds, 1 when a check does not hold (the
outputs are written first), 2 on bad input (a missing file or column, or
unreadable JSON).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLLOWUP = HERE.parent

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from analyse_labels import AGREEMENT, CATEGORIES, OUTCOMES, TIERS  # noqa: E402
from labelslib import NONE  # noqa: E402

MISSING = "label missing"
DECIDED = OUTCOMES[0]
SHADOWED = OUTCOMES[3]
FIRST_CATEGORIES = [
    "agreed label equals the described check",
    "agreed label names another check than the described one",
    "agreed label none, described check given",
    "agreed label none, no described check given",
    "no agreed label, described check given",
    "no agreed label, no described check given",
]
L1_SUBJECT = "joserfc"
DEFAULT_NAMES = ["google-auth", "oauthlib", "authlib", "joserfc"]

COLUMNS = {
    "agreement.csv": ["block", "label_1", "label_2", "category"],
    "outcomes.csv": ["block", "index", "test_node", "label", "deciding", "outcome"],
    "rule-vs-label.csv": ["rule", "block", "index", "test_node", "target", "tier", "label", "category"],
    "first-reading.csv": ["block", "index", "test_node", "class", "target", "described_first",
                          "label_1", "label_2", "agreed_label"],
}


class BadInput(Exception):
    pass


# -- input ---------------------------------------------------------------------------

def read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise BadInput(f"{path.parent.name}/{path.name}: missing")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in COLUMNS[path.name] if c not in (reader.fieldnames or [])]
        if missing:
            raise BadInput(f"{path.parent.name}/{path.name}: columns missing: {', '.join(missing)}")
        return list(reader)


def read_library(folder: Path) -> dict:
    counts_path = folder / "counts.json"
    if not counts_path.is_file():
        raise BadInput(f"{folder.name}/counts.json: missing")
    try:
        counts = json.loads(counts_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BadInput(f"{folder.name}/counts.json: not JSON ({exc.msg})") from None
    first = folder / "first-reading.csv"
    return {"counts": counts,
            "agreement": read_rows(folder / "agreement.csv"),
            "outcomes": read_rows(folder / "outcomes.csv"),
            "rules": read_rows(folder / "rule-vs-label.csv"),
            "first": read_rows(first) if first.is_file() else None}


def case_key(row: dict) -> str:
    return f"{row['test_node']}|{row['block']}|{row['index']}"


# -- statistics ----------------------------------------------------------------------

def frac(value: Fraction | None) -> dict | None:
    if value is None:
        return None
    return {"numerator": value.numerator, "denominator": value.denominator,
            "value": round(float(value), 4)}


def agreement_statistics(pairs: list[tuple[str, str]]) -> dict:
    """Observed agreement, expected agreement and Cohen's kappa of 2 readings."""
    n = len(pairs)
    first = Counter(a for a, _ in pairs)
    second = Counter(b for _, b in pairs)
    cats = set(first) | set(second)
    equal = sum(1 for a, b in pairs if a == b)
    if n == 0:
        return {"items": 0, "categories": 0, "equal": 0, "observed": None, "expected": None,
                "kappa": None}
    p_o = Fraction(equal, n)
    p_e = sum((Fraction(first[k] * second[k], n * n) for k in cats), Fraction(0))
    kappa = None if p_e == 1 else (p_o - p_e) / (1 - p_e)
    return {"items": n, "categories": len(cats), "equal": equal, "observed": frac(p_o),
            "expected": frac(p_e), "kappa": frac(kappa)}


def check_or_none(text: str) -> str:
    return NONE if text == NONE else "names a check"


def labeled_pairs(rows: list[dict]) -> list[tuple[str, str]]:
    return [(r["label_1"], r["label_2"]) for r in rows if r["label_1"] and r["label_2"]]


# -- per library ---------------------------------------------------------------------

def blocks_part(rows: list[dict]) -> dict:
    cats = Counter(r["category"] for r in rows)
    out = {"included": len(rows),
           "labeled_by_both": len(labeled_pairs(rows)),
           "categories": {c: cats.get(c, 0) for c in AGREEMENT},
           "same_label": cats.get("same check", 0) + cats.get("both none", 0)}
    if cats.get(MISSING):
        out["label_missing"] = cats[MISSING]
    other = sorted(set(cats) - set(AGREEMENT) - {MISSING})
    if other:
        out["unknown_categories"] = {c: cats[c] for c in other}
    return out


def label_kind(label: str) -> str:
    if not label:
        return "no agreed label"
    return NONE if label == NONE else "check"


def cases_part(rules: list[dict], outcomes: list[dict]) -> dict:
    rule2 = [r for r in rules if r["rule"] == "rule 2"]
    kinds = Counter(label_kind(r["label"]) for r in rule2)
    oc = Counter(r["outcome"] for r in outcomes)
    out = {"cases": len(rule2),
           "agreed_label_check": kinds.get("check", 0),
           "agreed_label_none": kinds.get(NONE, 0),
           "no_agreed_label": kinds.get("no agreed label", 0),
           "outcome_rows": len(outcomes),
           "outcomes": {o: oc.get(o, 0) for o in OUTCOMES},
           "decided_by_its_label": oc.get(DECIDED, 0),
           "shadowed": oc.get(SHADOWED, 0)}
    other = sorted(set(oc) - set(OUTCOMES))
    if other:
        out["unknown_outcomes"] = {o: oc[o] for o in other}
    return out


def derived(cats: Counter, with_target: int) -> dict:
    equals = cats.get("target equals label", 0)
    differs = cats.get("target differs from label", 0)
    label_none = cats.get("label none", 0)
    return {"categories": {c: cats.get(c, 0) for c in CATEGORIES},
            "with_target": with_target,
            "with_target_and_agreed_label": equals + differs + label_none,
            "target_equals_label": equals,
            "target_is_not_the_agreed_label": differs + label_none,
            "target_differs_from_label": differs,
            "target_while_label_none": label_none}


def rules_part(rules: list[dict]) -> dict:
    out = {}
    for rule in sorted({r["rule"] for r in rules}):
        rows = [r for r in rules if r["rule"] == rule]
        tiers = {}
        for tier in TIERS + sorted({r["tier"] for r in rows} - set(TIERS)):
            sel = [r for r in rows if r["tier"] == tier]
            tiers[tier] = derived(Counter(r["category"] for r in sel), sum(1 for r in sel if r["target"]))
        all_ = derived(Counter(r["category"] for r in rows), sum(1 for r in rows if r["target"]))
        all_["cases"] = len(rows)
        unknown = sorted({r["category"] for r in rows} - set(CATEGORIES))
        out[rule] = {"by_tier": tiers, "all": all_, "unknown_categories": unknown}
    return out


def first_category(agreed: str, described: str) -> str | None:
    if agreed == "":
        return FIRST_CATEGORIES[4] if described else FIRST_CATEGORIES[5]
    if agreed == NONE:
        return FIRST_CATEGORIES[2] if described else FIRST_CATEGORIES[3]
    if not described:
        return None
    return FIRST_CATEGORIES[0] if agreed == described else FIRST_CATEGORIES[1]


def first_part(first: list[dict] | None) -> dict | None:
    if first is None:
        return None
    by_class: dict[str, Counter] = {}
    target_by_class: dict[str, Counter] = {}
    flags = []
    for r in first:
        cat = first_category(r["agreed_label"], r["described_first"])
        if not r["agreed_label"]:
            eq_target = "no agreed label"
        else:
            eq_target = "yes" if r["target"] and r["agreed_label"] == r["target"] else "no"
        by_class.setdefault(r["class"], Counter())[cat or "unclassified"] += 1
        target_by_class.setdefault(r["class"], Counter())[eq_target] += 1
        flags.append({"case": case_key(r), "class": r["class"], "target": r["target"],
                      "described_check": r["described_first"], "agreed_label": r["agreed_label"],
                      "category": cat or "unclassified", "agreed_label_equals_target": eq_target})
    return {"flags": len(first), "by_class": {k: cat_dict(v) for k, v in sorted(by_class.items())},
            "agreed_label_equals_target_by_class": {k: tgt_dict(v) for k, v in sorted(target_by_class.items())},
            "rows": sorted(flags, key=lambda f: f["case"])}


def cat_dict(c: Counter) -> dict:
    out = {k: c.get(k, 0) for k in FIRST_CATEGORIES}
    if c.get("unclassified"):
        out["unclassified"] = c["unclassified"]
    return out


def tgt_dict(c: Counter) -> dict:
    return {k: c.get(k, 0) for k in ("yes", "no", "no agreed label")}


def status(units: list[dict]) -> str:
    if not units:
        return "not applicable"
    return "held" if all(u["holds"] for u in units) else "not held"


def expectation(units: list[dict]) -> dict:
    units = sorted(units, key=lambda u: u["case"])
    return {"units": len(units), "hold": sum(1 for u in units if u["holds"]),
            "not_holding": [u["case"] for u in units if not u["holds"]],
            "status": status(units), "unit_rows": units}


def expectations_part(name: str, lib: dict) -> dict:
    targets: dict[str, dict[str, str]] = {}
    for r in lib["rules"]:
        targets.setdefault(r["rule"], {})[case_key(r)] = r["target"]
    first = lib["first"] or []
    l1 = [{"case": case_key(r), "target": r["target"], "label_1": r["label_1"], "label_2": r["label_2"],
           "holds": bool(r["target"]) and r["label_1"] == r["target"] and r["label_2"] == r["target"]}
          for r in first if name == L1_SUBJECT and r["class"] == "A"]
    l2 = [{"case": case_key(r), "target": r["target"], "agreed_label": r["agreed_label"],
           "holds": r["agreed_label"] != r["target"]}
          for r in first if r["class"] == "C" and label_kind(r["agreed_label"]) == "check"]
    out = {"L1": expectation(l1), "L2": expectation(l2)}
    for title, rule in (("L3", "rule 2"), ("L3, rule 3", "rule 3")):
        units = []
        if rule in targets:
            for r in lib["outcomes"]:
                k = case_key(r)
                t = targets[rule].get(k, "")
                if t and r["deciding"] == t and label_kind(r["label"]) == "check":
                    units.append({"case": k, "target": t, "label": r["label"], "holds": r["label"] == t})
        out[title] = expectation(units)
        out[title]["rule_present"] = rule in targets
    out["L3, rule 3"]["note"] = "supplement with rule-3 targets; not part of the expectations of the protocol"
    return out


# -- together ------------------------------------------------------------------------

def add_counts(dicts: list[dict]) -> dict:
    """Sum nested dicts of integers key by key; values that are not integers or dicts are left out."""
    out: dict = {}
    nested: dict[str, list[dict]] = {}
    for d in dicts:
        for k, v in d.items():
            if isinstance(v, bool):
                continue
            if isinstance(v, int):
                out[k] = out.get(k, 0) + v
            elif isinstance(v, dict):
                nested.setdefault(k, []).append(v)
    for k, v in nested.items():
        out[k] = add_counts(v)
    return out


def together_expectation(per: dict, title: str) -> dict:
    units = []
    for name in per:
        units += [dict(u, case=f"{name}: {u['case']}") for u in per[name]["expectations"][title]["unit_rows"]]
    out = expectation(units)
    if title == "L3, rule 3":
        out["note"] = "supplement with rule-3 targets; not part of the expectations of the protocol"
    return out


# -- checks --------------------------------------------------------------------------

EQUAL_TEXTS_CHECK = ("equal label texts of the statistics \"labels\" equal the blocks of \"same check\" and "
                     "\"both none\", per library and together")


def equal_texts_problem(where: str, part: dict) -> str | None:
    """A problem text when the equal label texts used for kappa differ from the blocks with the same label."""
    equal = part["agreement_statistics"]["labels"]["equal"]
    cats = part["blocks"]["categories"]
    same = cats.get("same check", 0) + cats.get("both none", 0)
    if equal == same:
        return None
    return f"{where}: {equal} equal label texts, {same} blocks of \"same check\" and \"both none\""


def make_checks(libs: dict, per: dict, together: dict | None = None) -> list[dict]:
    checks = {
        "agreement categories sum to the blocks labeled by both readings, and with label missing to the "
        "included blocks": [],
        "case kinds sum to the cases": [],
        "outcomes sum to the cases with an agreed label that names a check": [],
        "rule categories sum to the cases, in each tier and for all tiers": [],
        "first-reading categories sum to the flags": [],
        "agreement categories equal counts.json": [],
        "agreement statistics equal counts.json": [],
        "case counts, outcomes, rule categories and first-reading counts equal counts.json": [],
        "first-reading.csv and outcomes.csv agree with rule-vs-label.csv": [],
        EQUAL_TEXTS_CHECK: [],
    }
    names = list(checks)
    for name, lib in libs.items():
        p = per[name]
        c = lib["counts"]
        b = p["blocks"]
        if sum(b["categories"].values()) != b["labeled_by_both"]:
            checks[names[0]].append(f"{name}: {sum(b['categories'].values())} in the 4 categories, "
                                    f"{b['labeled_by_both']} blocks labeled by both readings")
        if b["labeled_by_both"] + b.get("label_missing", 0) != b["included"] or b.get("unknown_categories"):
            checks[names[0]].append(f"{name}: categories do not cover the {b['included']} included blocks")
        cs = p["cases"]
        if cs["agreed_label_check"] + cs["agreed_label_none"] + cs["no_agreed_label"] != cs["cases"]:
            checks[names[1]].append(f"{name}: case kinds do not sum to {cs['cases']}")
        if sum(cs["outcomes"].values()) != cs["agreed_label_check"] or cs.get("unknown_outcomes") \
                or cs["outcome_rows"] != cs["agreed_label_check"]:
            checks[names[2]].append(f"{name}: {sum(cs['outcomes'].values())} outcomes, "
                                    f"{cs['agreed_label_check']} cases with a check")
        for rule, v in p["rules"].items():
            if v["unknown_categories"]:
                checks[names[3]].append(f"{name}: {rule}: unknown categories {v['unknown_categories']}")
            if sum(v["all"]["categories"].values()) != cs["cases"] or v["all"]["cases"] != cs["cases"]:
                checks[names[3]].append(f"{name}: {rule}: categories do not sum to {cs['cases']}")
            tier_sum = sum(sum(t["categories"].values()) for t in v["by_tier"].values())
            if tier_sum != cs["cases"]:
                checks[names[3]].append(f"{name}: {rule}: tiers sum to {tier_sum}, not {cs['cases']}")
        fr = p["first_reading"]
        if fr is not None:
            s = sum(sum(v.get(k, 0) for k in FIRST_CATEGORIES) for v in fr["by_class"].values())
            if s != fr["flags"]:
                checks[names[4]].append(f"{name}: {s} flags in the 6 categories, {fr['flags']} flags")
        # against counts.json
        ca = c.get("agreement", {})
        mine = dict(b["categories"])
        if b.get("label_missing"):
            mine[MISSING] = b["label_missing"]
        if {k: v for k, v in ca.items() if v} != {k: v for k, v in mine.items() if v}:
            checks[names[5]].append(f"{name}: {mine} here, {ca} in counts.json")
        for form in ("labels", "check_or_none"):
            st = p["agreement_statistics"][form]
            ref = c.get("agreement_statistics", {}).get(form)
            if ref is None:
                checks[names[6]].append(f"{name}: counts.json has no statistics {form}")
                continue
            for k in ("items", "categories", "equal"):
                if st[k] != ref.get(k):
                    checks[names[6]].append(f"{name}: {form} {k}: {st[k]} here, {ref.get(k)} in counts.json")
            for k in ("observed", "expected", "kappa"):
                here = st[k]["value"] if st[k] else None
                if here != ref.get(k):
                    checks[names[6]].append(f"{name}: {form} {k}: {here} here, {ref.get(k)} in counts.json")
        bad = checks[names[7]]
        for here, there in (("cases", "cases"), ("agreed_label_check", "cases_with_agreed_label_check"),
                            ("agreed_label_none", "cases_with_agreed_label_none"),
                            ("no_agreed_label", "cases_without_agreed_label")):
            if there in c and c[there] != cs[here]:
                bad.append(f"{name}: {there}: {cs[here]} here, {c[there]} in counts.json")
        for o, v in c.get("outcomes", {}).items():
            if cs["outcomes"].get(o, 0) != v:
                bad.append(f"{name}: outcome {o}: {cs['outcomes'].get(o, 0)} here, {v} in counts.json")
        for rule, v in c.get("rule_vs_label", {}).items():
            mine_r = p["rules"].get(rule)
            if mine_r is None:
                bad.append(f"{name}: {rule} in counts.json, no rows in rule-vs-label.csv")
                continue
            if {k: x for k, x in v["all"].items() if x} != {k: x for k, x in mine_r["all"]["categories"].items() if x}:
                bad.append(f"{name}: {rule} all tiers differ from counts.json")
            for tier, row in v.get("by_tier", {}).items():
                got = mine_r["by_tier"].get(tier, {}).get("categories", {})
                if {k: x for k, x in row.items() if x} != {k: x for k, x in got.items() if x}:
                    bad.append(f"{name}: {rule} tier {tier} differs from counts.json")
        if fr is not None and "first_reading" in c and "agreed_label_equals_described" in c["first_reading"]:
            tot = Counter()
            for v in fr["by_class"].values():
                tot.update(v)
            ref = c["first_reading"]
            mine_f = {"flags": fr["flags"],
                      "agreed_label_equals_described": tot[FIRST_CATEGORIES[0]],
                      "agreed_label_differs_from_described": tot[FIRST_CATEGORIES[1]] + tot[FIRST_CATEGORIES[2]],
                      "not_compared": tot[FIRST_CATEGORIES[3]] + tot[FIRST_CATEGORIES[4]]
                      + tot[FIRST_CATEGORIES[5]] + tot["unclassified"]}
            for k, v in mine_f.items():
                if ref.get(k) != v:
                    bad.append(f"{name}: first_reading {k}: {v} here, {ref.get(k)} in counts.json")
        # consistency between files
        rv: dict[tuple[str, str], dict] = {(r["rule"], case_key(r)): r for r in lib["rules"]}
        for r in lib["first"] or []:
            k = case_key(r)
            ref = rv.get(("rule 2", k))
            if ref is None:
                checks[names[8]].append(f"{name}: flag {k} has no rule-2 row")
            elif ref["target"] != r["target"] or ref["label"] != r["agreed_label"]:
                checks[names[8]].append(f"{name}: flag {k}: target or agreed label differs from rule-vs-label.csv")
        for r in lib["outcomes"]:
            ref = rv.get(("rule 2", case_key(r)))
            if ref is None or ref["label"] != r["label"]:
                checks[names[8]].append(f"{name}: outcome row {case_key(r)}: label differs from rule-vs-label.csv")
        problem = equal_texts_problem(name, p)
        if problem:
            checks[EQUAL_TEXTS_CHECK].append(problem)
    if together is not None:
        problem = equal_texts_problem("together", together)
        if problem:
            checks[EQUAL_TEXTS_CHECK].append(problem)
    return [{"name": k, "holds": not v, "problems": v[:50], "problems_total": len(v)} for k, v in checks.items()]


# -- summary -------------------------------------------------------------------------

def summarize(libs: dict) -> dict:
    per = {}
    for name, lib in libs.items():
        pairs = labeled_pairs(lib["agreement"])
        per[name] = {
            "blocks": blocks_part(lib["agreement"]),
            "agreement_statistics": {
                "labels": agreement_statistics(pairs),
                "check_or_none": agreement_statistics([(check_or_none(a), check_or_none(b)) for a, b in pairs])},
            "cases": cases_part(lib["rules"], lib["outcomes"]),
            "rules": rules_part(lib["rules"]),
            "first_reading": first_part(lib["first"]),
            "expectations": expectations_part(name, lib),
        }
    pooled = [pair for lib in libs.values() for pair in labeled_pairs(lib["agreement"])]
    qualified = [(f"{n}: {a}", f"{n}: {b}") for n, lib in libs.items() for a, b in labeled_pairs(lib["agreement"])]
    texts: dict[str, set] = {}
    for n, lib in libs.items():
        for a, b in labeled_pairs(lib["agreement"]):
            for t in (a, b):
                if t != NONE:
                    texts.setdefault(t, set()).add(n)
    shared = {t: sorted(ns) for t, ns in sorted(texts.items()) if len(ns) > 1}
    tog_blocks = add_counts([p["blocks"] for p in per.values()])
    tog_cases = add_counts([{k: v for k, v in p["cases"].items() if k != "unknown_outcomes"} for p in per.values()])
    rules = sorted({r for p in per.values() for r in p["rules"]})
    tog_rules = {}
    for rule in rules:
        have = [n for n in per if rule in per[n]["rules"]]
        tiers = {}
        for tier in sorted({t for n in have for t in per[n]["rules"][rule]["by_tier"]},
                           key=lambda t: (TIERS.index(t) if t in TIERS else len(TIERS), t)):
            tiers[tier] = add_counts([per[n]["rules"][rule]["by_tier"][tier] for n in have
                                      if tier in per[n]["rules"][rule]["by_tier"]])
        tog_rules[rule] = {"libraries": have, "by_tier": tiers,
                           "all": add_counts([per[n]["rules"][rule]["all"] for n in have])}
    with_first = [n for n in per if per[n]["first_reading"] is not None]
    classes = sorted({k for n in with_first for k in per[n]["first_reading"]["by_class"]})
    tog_first = {
        "libraries": with_first,
        "flags": sum(per[n]["first_reading"]["flags"] for n in with_first),
        "by_class": {k: add_counts([per[n]["first_reading"]["by_class"][k] for n in with_first
                                    if k in per[n]["first_reading"]["by_class"]]) for k in classes},
        "agreed_label_equals_target_by_class": {
            k: add_counts([per[n]["first_reading"]["agreed_label_equals_target_by_class"][k] for n in with_first
                           if k in per[n]["first_reading"]["agreed_label_equals_target_by_class"]])
            for k in classes},
    }
    together = {
        "blocks": tog_blocks,
        "agreement_statistics": {
            "labels": agreement_statistics(pooled),
            "check_or_none": agreement_statistics([(check_or_none(a), check_or_none(b)) for a, b in pooled])},
        "agreement_statistics_variant": {
            "labels_qualified_by_library": agreement_statistics(qualified),
            "note": "variant, not the result: each label text, none included, is qualified by its library"},
        "label_texts_other_than_none_in_2_or_more_libraries": shared,
        "cases": tog_cases,
        "rules": tog_rules,
        "first_reading": tog_first,
        "expectations": {t: together_expectation(per, t) for t in ("L1", "L2", "L3", "L3, rule 3")},
    }
    return {"libraries": per, "together": together, "checks": make_checks(libs, per, together)}


# -- SUMMARY.md ----------------------------------------------------------------------

def fmt_frac(f: dict | None) -> str:
    if f is None:
        return "no value"
    return f"{f['numerator']}/{f['denominator']} = {f['value']}"


def cell(value) -> str:
    """The text of 1 table cell; | is escaped, since it splits a cell even inside a code span."""
    return str(value).replace("|", "\\|")


def table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(cell(h) for h in header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(cell(x) for x in r) + " |" for r in rows]
    return out


def render(s: dict) -> str:
    per, tog = s["libraries"], s["together"]
    cols = list(per) + ["together"]
    allv = dict(per, together=tog)
    L = ["# Labels by reading: summary over the libraries", "",
         f"Libraries: {', '.join(per)}. Every value is read from the outputs of `analyse_labels.py` in the "
         "folder of each library; nothing is run again.", "",
         "## Blocks", "",
         "Included blocks, the blocks labeled by both readings and the 4 agreement categories of section 4.1 "
         "of the protocol. The blocks with the same label are those of the first 2 categories.", ""]
    rows = [["included blocks"] + [allv[c]["blocks"]["included"] for c in cols],
            ["labeled by both readings"] + [allv[c]["blocks"]["labeled_by_both"] for c in cols]]
    rows += [[k] + [allv[c]["blocks"]["categories"].get(k, 0) for c in cols] for k in AGREEMENT]
    rows.append(["same label in both readings"] + [allv[c]["blocks"]["same_label"] for c in cols])
    L += table(["Blocks"] + cols, rows)
    L += ["", "## Agreement statistics", "",
          "Observed agreement, agreement expected by chance and Cohen's kappa over the blocks labeled by both "
          "readings, as exact fractions and rounded to 4 places. Together, a label text is 1 category in "
          "every library, so `none` is 1 category.", ""]
    rows = []
    for form, title in (("labels", "each label text"), ("check_or_none", "names a check, or none")):
        for c in cols:
            st = allv[c]["agreement_statistics"][form]
            rows.append([title, c, st["items"], st["categories"], st["equal"], fmt_frac(st["observed"]),
                         fmt_frac(st["expected"]), fmt_frac(st["kappa"])])
    v = tog["agreement_statistics_variant"]["labels_qualified_by_library"]
    rows.append(["variant: each label text qualified by its library", "together", v["items"], v["categories"],
                 v["equal"], fmt_frac(v["observed"]), fmt_frac(v["expected"]), fmt_frac(v["kappa"])])
    L += table(["Categories", "Library", "Items", "Categories used", "Equal", "Observed", "Expected",
                "Kappa"], rows)
    shared = tog["label_texts_other_than_none_in_2_or_more_libraries"]
    L += ["", "The last row is a variant and not the result. "
          + (f"{len(shared)} label texts other than `none` occur in 2 or more libraries: "
             + "; ".join(f"`{t}` ({', '.join(ns)})" for t, ns in shared.items()) + "."
             if shared else "No label text other than `none` occurs in 2 libraries, so the variant differs "
                            "from the result only through the category `none`.")]
    L += ["", "## Cases", "",
          "Cases of the study by their agreed label, and the outcome of each case whose agreed label names a "
          "check. A shadowed case has the outcome \"" + SHADOWED + "\".", ""]
    rows = [[t] + [allv[c]["cases"][k] for c in cols] for t, k in
            (("cases", "cases"), ("agreed label names a check", "agreed_label_check"),
             ("agreed label none", "agreed_label_none"), ("no agreed label", "no_agreed_label"))]
    rows += [[f"outcome: {o}"] + [allv[c]["cases"]["outcomes"].get(o, 0) for c in cols] for o in OUTCOMES]
    L += table(["Cases"] + cols, rows)
    for rule in tog["rules"]:
        L += ["", f"## {rule} against the agreed label", "",
              "Cases per tier of the target and category. Of the cases with a target, those with an agreed "
              "label (a check or none) are split into target equals label and target is not the agreed label "
              "(the target differs, or the agreed label is none).", ""]
        rows = []
        for c in cols:
            r = allv[c]["rules"].get(rule)
            if r is None:
                continue
            for tier, t in list(r["by_tier"].items()) + [("all", r["all"])]:
                rows.append([c, tier] + [t["categories"].get(k, 0) for k in CATEGORIES]
                            + [t["with_target"], t["with_target_and_agreed_label"],
                               f"{t['target_is_not_the_agreed_label']} of {t['with_target_and_agreed_label']}"])
        L += table(["Library", "Tier"] + CATEGORIES + ["with target", "with target and agreed label",
                                                       "target is not the agreed label"], rows)
    L += ["", "## First reading of the flags", "",
          "Each flag of the first study in 1 of 6 categories, by the agreed label and the described check of "
          "the first reading. A flag whose agreed label names a check while no check is described fits no "
          "category and fails a check.", ""]
    rows = []
    for c in cols:
        fr = allv[c]["first_reading"]
        if fr is None:
            continue
        for cls, v in fr["by_class"].items():
            t = fr["agreed_label_equals_target_by_class"][cls]
            rows.append([c, cls] + [v.get(k, 0) for k in FIRST_CATEGORIES]
                        + [v.get("unclassified", 0), t["yes"], t["no"], t["no agreed label"]])
    L += table(["Library", "Class"] + FIRST_CATEGORIES
               + ["in no category", "agreed label equals rule-2 target", "agreed label is not the rule-2 target",
                  "no agreed label"], rows)
    L += ["", "## Expectations L1 to L3", "",
          "Units and status of the expectations of section 2 of the protocol. L3 with rule-3 targets is a "
          "supplement and not part of the expectations of the protocol.", ""]
    rows = []
    for title in ("L1", "L2", "L3", "L3, rule 3"):
        for c in cols:
            e = allv[c]["expectations"][title]
            rows.append([title, c, e["units"], e["hold"], e["units"] - e["hold"], e["status"],
                         "; ".join(f"`{k}`" for k in e["not_holding"]) or "-"])
    L += table(["Expectation", "Library", "Units", "Hold", "Do not hold", "Status", "Units that do not hold"],
               rows)
    L += ["", "## Checks", "", "Each check of the program and whether it holds.", ""]
    L += table(["Check", "Holds"], [[c["name"], "yes" if c["holds"] else "no"] for c in s["checks"]])
    for c in s["checks"]:
        L += [f"- {c['name']}: {p}" for p in c["problems"][:10]]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--generated", default=None)
    ap.add_argument("--names", nargs="+", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    gen = Path(a.generated) if a.generated else FOLLOWUP / "generated" / "labels"
    out = Path(a.out) if a.out else FOLLOWUP / "generated" / "labels"
    names = a.names or DEFAULT_NAMES
    if len(set(names)) != len(names) or "together" in names:
        print("summary: names must be distinct and not 'together'", file=sys.stderr)
        return 2
    try:
        libs = {n: read_library(gen / n) for n in names}
    except BadInput as exc:
        print(f"summary: bad input: {exc}", file=sys.stderr)
        return 2
    s = summarize(libs)
    doc = {"arguments": {"generated": a.generated or "generated/labels", "names": names,
                         "out": a.out or "generated/labels"}, **s}
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    (out / "SUMMARY.md").write_text(render(s), encoding="utf-8")
    failed = [c["name"] for c in s["checks"] if not c["holds"]]
    print(f"summary: {len(names)} libraries; checks not holding: {len(failed)}")
    for f in failed:
        print(f"  {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
