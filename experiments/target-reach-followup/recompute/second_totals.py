"""Cross-library totals of the second computation, for the 4 held-out libraries.

    python3 -I -B recompute/second_totals.py [--out-dir recompute/out] \
        [--names google-auth oauthlib authlib joserfc] --out recompute/out/second_totals.json

Inputs: for each name, `<out-dir>/<name>/second_labels.json` (written by
`recompute/second_labels.py`) and `<out-dir>/<name>/second_rule3.json`
(written by `recompute/second_rule3.py`). Nothing else is read.

Output (`--out`): 1 JSON file with sorted keys, 2-space indentation, no
absolute path and no time stamp. The paths are recorded as given. The
program prints 1 summary line. Groups, with the sections of PROTOCOL.md:

- `agreement` (section 4.1, 'Agreement'): included blocks, the 4 agreement
  categories, the observed agreement and Cohen's kappa per library (copied)
  and for the 4 libraries together (pooled).
- `cases` (section 4.1, 'Outcome of a case ...' and 'shadowed'): cases of the
  study, cases by agreed label, outcomes, shadowed cases.
- `program_vs_label` (section 4.1, 'Program against label'): per rule, per
  tier and for all tiers, the 6 categories and the derived counts.
- `first_reading` (section 4.1, 'First reading'): the flags per class and in
  total, in the 6 categories of `second_labels.py`.
- `expectations_labels` (section 2, L1, L2, L3).
- `rules` (section 4.2, 'Analysis', and the note on the rule in section 2):
  cases with a target, decided and not decided by it, per tier; transitions.
- `expectations_rule` (section 2, T1, T2, T3, stated for joserfc).
- `checks`: every consistency check, true when it holds.

Definitions:

- Pooled observed agreement: the blocks on which the 2 readings give the
  same category, divided by the included blocks of the 4 libraries.
- Pooled Cohen's kappa: (po - pe) / (1 - pe), where pe is the sum over the
  categories of the share of reading A times the share of reading B, both
  taken over the pooled blocks. Kappa has no value when pe is 1.
- Form by label text: a label is its text, as `second_labels.py` writes it in
  its marginal counts (a by-parameter label with its values sorted). The
  protocol says "every distinct label text as a category", so equal texts
  form 1 category across libraries: the text `none` is 1 category for the 4
  libraries, and so is a check identifier that occurs in 2 libraries.
- Variant by library: a label is the pair (library, text), so the text `none`
  of 4 libraries gives 4 categories.
- Form "names a check" and "none": the 2 categories of `second_labels.py`.
- Each value is given as an exact fraction and as a float rounded to 4 places.
- Tier of a case under a rule: `assertion` or `name` when the rule gives the
  block a target, `no target` otherwise.
- Target is not the label: the category "target differs from agreed label"
  plus the category "target given, agreed label none".
- A case is decided by its target when its deciding check is the target.
- Missing agreed label: no agreed label, or a by-parameter label that does
  not resolve in the case.
- Shadowed: outcome 7 under the agreed label; the union with the class-A
  cases of the first reading is given apart, as section 4.1 includes them.
- An expectation holds when every unit holds; it is "not applicable" with no
  unit. Overall status of L1 to L3 pools the units of the 4 libraries.
- T1 holds when the flags of joserfc under rule 3 are 10 or fewer and fewer
  than under rule 2. T2 holds when every class-A case of joserfc, taken from
  the first reading in `second_labels.json`, has the same target under both
  rules. T3 holds when at least 85% of the joserfc cases with a rule-3 target
  are decided by it.

Per-library counts are recomputed from the per-case tables of the 2 inputs
and compared with the counts that the inputs state; a difference is a
failed check.

Exit status: 0 when every check holds; 1 when 1 check does not hold (the
output is written first); 2 on bad input.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

NAMES = ("google-auth", "oauthlib", "authlib", "joserfc")
NONE = "none"
NO_AGREED = "(no agreed label)"
UNRESOLVED = "(by-param label does not resolve)"
AGREEMENT = ("same check", "both none", "1 check and 1 none", "2 different checks")
PVL = ("target equals agreed label", "target differs from agreed label",
       "target given, agreed label none", "no target, agreed label names a check",
       "both none", "no agreed label")
FIRST = ("agreed label equals described check", "agreed label differs from described check",
         "agreed label none, described check given", "agreed label names a check, no described check",
         "agreed label none, no described check", "no agreed label")
OUTCOMES = ("1 decided by its label", "2 label fires and another check decides",
            "3 label fires and no check decides", "4 label does not fire and no check decides",
            "5 deciding check not deleted or record missing",
            "6 label does not fire; case not observed on the copy without the deciding check",
            "7 label does not fire and decides once the deciding check is deleted",
            "8 label does not fire and does not decide then either", "fired checks not recorded")
TIERS = ("assertion", "name", "no target")
TRANS = ("gains a target", "keeps its target", "changes its target", "loses its target",
         "no target under either rule")
SHADOW = OUTCOMES[6]


class InputError(Exception):
    """An input is missing or malformed."""


class Checks:
    """Named consistency checks; each records whether it holds."""

    def __init__(self) -> None:
        self.results: dict[str, bool] = {}

    def eq(self, name: str, a, b) -> None:
        self.results[name] = self.results.get(name, True) and a == b

    def true(self, name: str, cond: bool) -> None:
        self.results[name] = self.results.get(name, True) and bool(cond)

    def failed(self) -> list[str]:
        return sorted(k for k, v in self.results.items() if not v)


def load(path: Path):
    if not path.is_file():
        raise InputError(f"missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise InputError(f"not readable as JSON: {path}: {exc}") from exc


def frac(f: Fraction | None) -> dict | None:
    if f is None:
        return None
    return {"numerator": f.numerator, "denominator": f.denominator, "value": round(float(f), 4)}


def kappa_from_marginals(agree: int, n: int, ma: dict, mb: dict) -> dict:
    """Observed agreement and kappa from the agreeing units and the marginal counts."""
    out = {"units": n, "agreeing_units": agree, "categories": len(set(ma) | set(mb))}
    if n == 0:
        out.update(observed_agreement=None, expected_agreement=None, kappa=None, kappa_note="no units")
        return out
    po = Fraction(agree, n)
    pe = sum((Fraction(ma.get(k, 0) * mb.get(k, 0), n * n) for k in set(ma) | set(mb)), Fraction(0))
    out.update(observed_agreement=frac(po), expected_agreement=frac(pe))
    if pe == 1:
        out.update(kappa=None, kappa_note="expected agreement is 1: kappa has no value")
    else:
        out["kappa"] = frac((po - pe) / (1 - pe))
    return out


def stated_fraction(text) -> Fraction | None:
    if text is None:
        return None
    num, _, den = str(text).partition("/")
    return Fraction(int(num), int(den))


def status(units: int, holding: int) -> str:
    if units == 0:
        return "not applicable"
    return "held" if holding == units else "not held"


def label_kind(lab: str) -> str:
    if lab in (NO_AGREED, UNRESOLVED):
        return "missing"
    return "none" if lab == NONE else "names a check"


def pvl_category(target, lab: str) -> str:
    if lab in (NO_AGREED, UNRESOLVED):
        return PVL[5]
    if target and lab != NONE:
        return PVL[0] if target == lab else PVL[1]
    if target:
        return PVL[2]
    if lab != NONE:
        return PVL[3]
    return PVL[4]


def first_category(lab: str, desc) -> str:
    if lab in (NO_AGREED, UNRESOLVED):
        return FIRST[5]
    if lab == NONE:
        return FIRST[2] if desc else FIRST[4]
    if not desc:
        return FIRST[3]
    return FIRST[0] if lab == desc else FIRST[1]


def zero(keys) -> dict:
    return {k: 0 for k in keys}


def add_into(total: dict, part: dict) -> None:
    for k, v in part.items():
        total[k] = total.get(k, 0) + v


def compute(args) -> tuple[dict, Checks]:
    ck = Checks()
    out_dir = Path(args.out_dir)
    labels, rule3 = {}, {}
    for name in args.names:
        labels[name] = load(out_dir / name / "second_labels.json")
        rule3[name] = load(out_dir / name / "second_rule3.json")
    try:
        result = _compute(args, labels, rule3, ck)
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise InputError(f"an input lacks an expected field or has a malformed value: "
                         f"{type(exc).__name__}: {exc}") from exc
    return result, ck


def _compute(args, labels: dict, rule3: dict, ck: Checks) -> dict:
    names = list(args.names)
    out: dict = {"inputs": {"out_dir": args.out_dir, "names": names,
                            "files": [f"{args.out_dir}/{n}/{f}" for n in names
                                      for f in ("second_labels.json", "second_rule3.json")]},
                 "protocol": "PROTOCOL.md, sections 2 (L1, L2, L3, T1, T2, T3), 4.1 and 4.2"}

    # ---- 1. agreement ------------------------------------------------------------------
    per_lib, pooled_cats = {}, zero(AGREEMENT)
    agree_text = agree_names = units = 0
    m_text = ({}, {})
    m_qual = ({}, {})
    m_names = ({}, {})
    texts_by_lib: dict[str, set] = {}
    for n in names:
        d = labels[n]
        a = d["agreement"]
        inc = d["inputs"]["included blocks"]
        cats = {k: a["categories"]["counts"][k] for k in AGREEMENT}
        ck.eq(f"agreement categories sum to the included blocks ({n})", sum(cats.values()), inc)
        tx, nm = a["every_label_text_as_a_category"], a["names_a_check_or_none"]
        ck.eq(f"text-form units equal the included blocks ({n})", tx["units"], inc)
        ck.eq(f"names-form units equal the included blocks ({n})", nm["units"], inc)
        for side, key in ((0, "marginals_reading_A"), (1, "marginals_reading_B")):
            ck.eq(f"text-form marginals sum to the included blocks ({n}, {key})", sum(tx[key].values()), inc)
            ck.eq(f"names-form marginals sum to the included blocks ({n}, {key})", sum(nm[key].values()), inc)
            for t, c in tx[key].items():
                m_text[side][t] = m_text[side].get(t, 0) + c
                m_qual[side][f"{n}\t{t}"] = c
            for t, c in nm[key].items():
                m_names[side][t] = m_names[side].get(t, 0) + c
        texts_by_lib[n] = set(tx["marginals_reading_A"]) | set(tx["marginals_reading_B"])
        # with no by-parameter label, equal texts are exactly 'same check' plus 'both none'
        no_byparam = all(d["readings"][r]["blocks_labeled_by_param"] == 0 for r in ("A", "B"))
        if no_byparam:
            ck.eq(f"text-form agreement equals same check plus both none ({n})",
                  tx["agree"], cats[AGREEMENT[0]] + cats[AGREEMENT[1]])
            ck.eq(f"names-form agreement equals the categories other than 1 check and 1 none ({n})",
                  nm["agree"], inc - cats[AGREEMENT[2]])
        own_t = kappa_from_marginals(tx["agree"], inc, tx["marginals_reading_A"], tx["marginals_reading_B"])
        own_n = kappa_from_marginals(nm["agree"], inc, nm["marginals_reading_A"], nm["marginals_reading_B"])
        for form, own, st in (("text", own_t, tx), ("names", own_n, nm)):
            ck.eq(f"observed agreement recomputed equals the stated one ({n}, {form})",
                  own["observed_agreement"] and Fraction(own["observed_agreement"]["numerator"],
                                                         own["observed_agreement"]["denominator"]),
                  stated_fraction(st.get("observed_agreement_fraction")))
            ck.eq(f"kappa recomputed equals the stated one ({n}, {form})",
                  own["kappa"] and Fraction(own["kappa"]["numerator"], own["kappa"]["denominator"]),
                  stated_fraction(st.get("kappa_fraction")))
        per_lib[n] = {"included_blocks": inc, "categories": cats,
                      "every_label_text_as_a_category": own_t, "names_a_check_or_none": own_n}
        add_into(pooled_cats, cats)
        agree_text += tx["agree"]
        agree_names += nm["agree"]
        units += inc
    ck.eq("pooled agreement categories sum to the pooled blocks", sum(pooled_cats.values()), units)
    shared = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for t in sorted((texts_by_lib[a] & texts_by_lib[b]) - {NONE}):
                shared.setdefault(t, []).append(f"{a} and {b}")
    out["agreement"] = {
        "per_library": per_lib,
        "pooled": {
            "included_blocks": units,
            "categories": pooled_cats,
            "every_label_text_as_a_category": kappa_from_marginals(agree_text, units, *m_text),
            "every_label_text_qualified_by_library_variant": kappa_from_marginals(agree_text, units, *m_qual),
            "names_a_check_or_none": kappa_from_marginals(agree_names, units, *m_names),
            "names_a_check_or_none_marginals": {"reading_A": dict(sorted(m_names[0].items())),
                                                "reading_B": dict(sorted(m_names[1].items()))},
        },
        "label_texts_other_than_none_in_2_libraries": len(shared),
        "label_texts_other_than_none_in_2_libraries_list": {k: v for k, v in sorted(shared.items())},
        "none_is_1_category_across_libraries_in_the_text_form": True,
    }

    # ---- 2. cases ----------------------------------------------------------------------
    case_tot = {"cases_of_the_study": 0, "agreed_label_names_a_check": 0, "agreed_label_none": 0,
                "agreed_label_missing": 0, "agreed_label_missing_by_param_unresolved": 0}
    outc_tot = zero(OUTCOMES)
    shadow_ids, shadow_union = [], []
    case_per_lib = {}
    for n in names:
        d = labels[n]
        rows = d["cases"]
        ck.eq(f"cases of the study equal the per-case rows ({n})", d["inputs"]["cases of the study"], len(rows))
        kinds = Counter(label_kind(r["labels"]["agreed"]) for r in rows.values())
        unres = sum(1 for r in rows.values() if r["labels"]["agreed"] == UNRESOLVED)
        outc = zero(OUTCOMES)
        for key, r in rows.items():
            lab = r["labels"]["agreed"]
            o = r["outcomes"]["agreed"]
            if label_kind(lab) == "names a check":
                ck.true(f"every case whose agreed label names a check has an outcome ({n})", o in outc)
                if o in outc:
                    outc[o] += 1
            else:
                ck.true(f"no outcome without an agreed label naming a check ({n})", o is None)
            if o == OUTCOMES[0]:
                ck.eq(f"outcome 1 means the label is the deciding check ({n})", lab, r["deciding_check"])
        ck.eq(f"outcomes sum to the cases whose agreed label names a check ({n})",
              sum(outc.values()), kinds["names a check"])
        ck.eq(f"case partition by agreed label sums to the cases ({n})", sum(kinds.values()), len(rows))
        stated = d["outcomes"]["agreed"]["outcomes"]["counts"]
        ck.eq(f"outcomes recomputed equal the stated ones ({n})", {k: stated.get(k, 0) for k in OUTCOMES}, outc)
        sb = d["outcomes"]["agreed"]["cases_by_label"]
        ck.eq(f"cases by agreed label recomputed equal the stated ones ({n})",
              (sb.get("names a check", 0), sb.get(NONE, 0), sb.get(NO_AGREED, 0) + sb.get(UNRESOLVED, 0)),
              (kinds["names a check"], kinds["none"], kinds["missing"]))
        sh = sorted(k for k, r in rows.items() if r["outcomes"]["agreed"] == SHADOW)
        class_a = sorted(k for k, f in d["first_reading"].get("per_flag", {}).items() if f["class"] == "A")
        union = sorted(set(sh) | set(class_a))
        ck.eq(f"shadowed cases recomputed equal the stated ones ({n})", sh, d["shadowed"]["by_agreed_label_ids"])
        ck.eq(f"shadowed union recomputed equals the stated one ({n})", union,
              sorted(d["shadowed"]["shadowed_cases_with_sources"]))
        case_per_lib[n] = {"cases_of_the_study": len(rows), "agreed_label_names_a_check": kinds["names a check"],
                           "agreed_label_none": kinds["none"], "agreed_label_missing": kinds["missing"],
                           "agreed_label_missing_by_param_unresolved": unres, "outcomes": outc,
                           "shadowed_by_agreed_label": len(sh), "shadowed_by_agreed_label_ids": sh,
                           "class_a_cases_of_the_first_reading": len(class_a),
                           "shadowed_or_class_a": len(union), "shadowed_or_class_a_ids": union}
        case_tot["cases_of_the_study"] += len(rows)
        case_tot["agreed_label_names_a_check"] += kinds["names a check"]
        case_tot["agreed_label_none"] += kinds["none"]
        case_tot["agreed_label_missing"] += kinds["missing"]
        case_tot["agreed_label_missing_by_param_unresolved"] += unres
        add_into(outc_tot, outc)
        shadow_ids += [f"{n}: {k}" for k in sh]
        shadow_union += [f"{n}: {k}" for k in union]
    ck.eq("pooled case partition by agreed label sums to the pooled cases",
          case_tot["agreed_label_names_a_check"] + case_tot["agreed_label_none"] + case_tot["agreed_label_missing"],
          case_tot["cases_of_the_study"])
    ck.eq("pooled outcomes sum to the pooled cases whose agreed label names a check",
          sum(outc_tot.values()), case_tot["agreed_label_names_a_check"])
    out["cases"] = {"per_library": case_per_lib,
                    "pooled": dict(case_tot, outcomes=outc_tot,
                                   shadowed_by_agreed_label=len(shadow_ids),
                                   shadowed_by_agreed_label_ids=sorted(shadow_ids),
                                   shadowed_or_class_a=len(shadow_union),
                                   shadowed_or_class_a_ids=sorted(shadow_union))}

    # ---- cross-file consistency of cases and targets -------------------------------------
    for n in names:
        lrows, rrows = labels[n]["cases"], rule3[n]["cases"]
        ck.eq(f"the 2 inputs hold the same cases ({n})", sorted(lrows), sorted(rrows))
        for k in set(lrows) & set(rrows):
            lr, rr = lrows[k], rrows[k]
            ck.eq(f"the 2 inputs give the same deciding check ({n})", lr["deciding_check"], rr["deciding_check"])
            for lk, rk in (("rule 2", "rule2"), ("rule 3", "rule3")):
                ck.eq(f"the 2 inputs give the same {lk} target ({n})", lr[lk]["target"], rr[rk]["target"])
                lt = lr[lk]["tier"] if lr[lk]["target"] else "no target"
                ck.eq(f"the 2 inputs give the same {lk} tier ({n})", lt, rr[rk]["tier"])

    # ---- 3. program against label ----------------------------------------------------------
    pvl_out = {}
    for lk in ("rule 2", "rule 3"):
        pooled = {t: zero(PVL) for t in TIERS + ("all tiers",)}
        libs = {}
        for n in names:
            per = {t: zero(PVL) for t in TIERS + ("all tiers",)}
            for r in labels[n]["cases"].values():
                info = r[lk]
                tier = info["tier"] if info["target"] else "no target"
                cat = pvl_category(info["target"], r["labels"]["agreed"])
                per[tier][cat] += 1
                per["all tiers"][cat] += 1
            st = labels[n]["program_vs_label"][lk]
            ck.eq(f"program against label recomputed equals the stated counts ({n}, {lk}, all tiers)",
                  per["all tiers"], {k: st["per_case"]["counts"][k] for k in PVL})
            for t in TIERS:
                stated_t = st["per_case_by_tier"].get(t, {"counts": zero(PVL)})["counts"]
                ck.eq(f"program against label recomputed equals the stated counts ({n}, {lk}, {t})",
                      per[t], {k: stated_t[k] for k in PVL})
            ck.eq(f"program against label tiers sum to all tiers ({n}, {lk})",
                  {k: sum(per[t][k] for t in TIERS) for k in PVL}, per["all tiers"])
            ck.eq(f"program against label sums to the cases ({n}, {lk})",
                  sum(per["all tiers"].values()), len(labels[n]["cases"]))
            ck.eq(f"no target tier holds only categories without a target ({n}, {lk})",
                  per["no target"][PVL[0]] + per["no target"][PVL[1]] + per["no target"][PVL[2]], 0)
            libs[n] = {t: {"categories": per[t], **_derived(per[t], labels[n]["cases"], lk, t)} for t in per}
            for t in per:
                add_into(pooled[t], per[t])
        pooled_out = {}
        for t in pooled:
            pooled_out[t] = {"categories": pooled[t],
                             **_derived_sum([libs[n][t] for n in names])}
            ck.eq(f"pooled program against label: target cases split into agreed and missing ({lk}, {t})",
                  pooled_out[t]["cases_with_a_target"],
                  pooled_out[t]["cases_with_a_target_and_an_agreed_label"]
                  + pooled_out[t]["cases_with_a_target_and_no_agreed_label"])
            ck.eq(f"pooled program against label: agreed target cases split into equal and not ({lk}, {t})",
                  pooled_out[t]["cases_with_a_target_and_an_agreed_label"],
                  pooled_out[t]["target_equals_label"] + pooled_out[t]["target_is_not_the_label"])
        ck.eq(f"pooled program against label sums to the pooled cases ({lk})",
              sum(pooled["all tiers"].values()), case_tot["cases_of_the_study"])
        pvl_out[lk] = {"per_library": libs, "pooled": pooled_out}
    out["program_vs_label"] = pvl_out

    # ---- 4. first reading ----------------------------------------------------------------
    fr_lib, fr_pool = {}, {}
    for n in names:
        fr = labels[n]["first_reading"]
        per = {}
        for k, f in fr.get("per_flag", {}).items():
            row = labels[n]["cases"].get(k)
            ck.true(f"every flag of the first reading is a case of the study ({n})", row is not None)
            if row is None:
                continue
            ck.eq(f"agreed label of a flag equals the agreed label of its case ({n})",
                  f["agreed_label"], row["labels"]["agreed"])
            cat = first_category(row["labels"]["agreed"], f["described_check"])
            ck.eq(f"first-reading category recomputed equals the stated one ({n})", cat, f["category"])
            per.setdefault(f["class"], zero(FIRST))[cat] += 1
        stated = {c: {k: v["counts"][k] for k in FIRST} for c, v in fr.get("categories_by_class", {}).items()}
        ck.eq(f"first-reading categories by class recomputed equal the stated ones ({n})", per, stated)
        ck.eq(f"first-reading rows equal the flags counted ({n})", fr.get("rows", 0),
              sum(sum(v.values()) for v in per.values()))
        total = zero(FIRST)
        for v in per.values():
            add_into(total, v)
        fr_lib[n] = {"by_class": per, "total": total, "flags": sum(total.values())}
        for c, v in per.items():
            add_into(fr_pool.setdefault(c, zero(FIRST)), v)
    fr_total = zero(FIRST)
    for v in fr_pool.values():
        add_into(fr_total, v)
    out["first_reading"] = {"per_library": fr_lib,
                            "pooled": {"by_class": dict(sorted(fr_pool.items())), "total": fr_total,
                                       "flags": sum(fr_total.values()),
                                       "flags_by_class": {c: sum(v.values()) for c, v in sorted(fr_pool.items())}}}

    # ---- 5. L1, L2, L3 ---------------------------------------------------------------------
    exp_lib, exp_pool = {}, {e: [0, 0] for e in ("L1", "L2", "L3")}
    for n in names:
        d = labels[n]
        rows = d["cases"]
        flags = d["first_reading"].get("per_flag", {})
        l1u = l1h = 0
        for k, f in flags.items():
            if f["class"] != "A":
                continue
            l1u += 1
            r = rows.get(k)
            t = f["rule 2 target"]
            if r is not None and t is not None and all(r["labels"][x] == t for x in ("A", "B")):
                l1h += 1
        l2u = l2h = 0
        for k, f in flags.items():
            if f["class"] != "C":
                continue
            r = rows.get(k)
            lab = r["labels"]["agreed"] if r else NO_AGREED
            if label_kind(lab) != "names a check":
                continue
            l2u += 1
            if lab != r["rule 2"]["target"]:
                l2h += 1
        l3u = l3h = 0
        for r in rows.values():
            t = r["rule 2"]["target"]
            lab = r["labels"]["agreed"]
            if not t or r["deciding_check"] != t or label_kind(lab) != "names a check":
                continue
            l3u += 1
            if lab == t:
                l3h += 1
        mine = {"L1": (l1u, l1h), "L2": (l2u, l2h), "L3": (l3u, l3h)}
        exp_lib[n] = {}
        for e, (u, h) in mine.items():
            se = d["expectations"][e]
            ck.eq(f"{e} recomputed equals the stated units and holding ({n})", (u, h),
                  (se["units"], se.get("holding", 0)))
            ck.eq(f"{e} recomputed status equals the stated status ({n})", status(u, h), se["status"])
            exp_lib[n][e] = {"units": u, "holding": h, "status": status(u, h)}
            exp_pool[e][0] += u
            exp_pool[e][1] += h
    out["expectations_labels"] = {
        "per_library": exp_lib,
        "overall": {e: {"units": u, "holding": h, "status": status(u, h)} for e, (u, h) in exp_pool.items()},
        "note": "L1 is stated for joserfc only; the other libraries have no class-A flag and no unit.",
    }

    # ---- 6. rules ------------------------------------------------------------------------
    rules_out = {}
    for rk in ("rule2", "rule3"):
        libs, pooled = {}, {t: [0, 0] for t in ("assertion", "name", "all tiers")}
        for n in names:
            rows = rule3[n]["cases"]
            per = {t: [0, 0] for t in ("assertion", "name", "all tiers")}
            for r in rows.values():
                info = r[rk]
                if not info["target"]:
                    ck.eq(f"a case without a target is not decided ({n}, {rk})", info["decides"], False)
                    continue
                dec = info["target"] == r["deciding_check"]
                ck.eq(f"decides equals target is the deciding check ({n}, {rk})", info["decides"], dec)
                for t in (info["tier"], "all tiers"):
                    per[t][0] += 1
                    per[t][1] += int(dec)
            st = rule3[n]["counts"][rk]
            ck.eq(f"rule counts recomputed equal the stated ones ({n}, {rk}, all tiers)",
                  (per["all tiers"][0], per["all tiers"][1]),
                  (st["cases_with_a_target"], st["decided_by_the_target"]))
            ck.eq(f"rule counts: decided plus not decided equal cases with a target ({n}, {rk})",
                  st["decided_by_the_target"] + st["not_decided_by_the_target"], st["cases_with_a_target"])
            for t in ("assertion", "name"):
                ck.eq(f"rule counts recomputed equal the stated ones ({n}, {rk}, {t})",
                      tuple(per[t]), (st["by_tier"][t]["cases_with_a_target"],
                                      st["by_tier"][t]["decided_by_the_target"]))
            ck.eq(f"rule tiers sum to all tiers ({n}, {rk})",
                  [per["assertion"][i] + per["name"][i] for i in (0, 1)], per["all tiers"])
            libs[n] = {t: _rule_cell(v) for t, v in per.items()}
            for t in per:
                pooled[t][0] += per[t][0]
                pooled[t][1] += per[t][1]
        rules_out[rk] = {"per_library": libs, "pooled": {t: _rule_cell(v) for t, v in pooled.items()}}
    trans_lib, trans_pool = {}, {t: [0, 0, 0] for t in TRANS}
    for n in names:
        rows = rule3[n]["cases"]
        per = {t: [0, 0, 0] for t in TRANS}
        for r in rows.values():
            a, z = r["rule2"]["target"], r["rule3"]["target"]
            if a is None and z is None:
                tr = TRANS[4]
            elif a is None:
                tr = TRANS[0]
            elif z is None:
                tr = TRANS[3]
            else:
                tr = TRANS[1] if a == z else TRANS[2]
            ck.eq(f"transition recomputed equals the stated one ({n})", tr, r["transition"])
            per[tr][0] += 1
            per[tr][1] += int(bool(a) and a == r["deciding_check"])
            per[tr][2] += int(bool(z) and z == r["deciding_check"])
        st = rule3[n]["transitions"]["cases"]
        for t in TRANS:
            ck.eq(f"transition counts recomputed equal the stated ones ({n}, {t})", per[t],
                  [st[t]["count"], st[t]["decided_by_the_rule2_target"], st[t]["decided_by_the_rule3_target"]])
            for i in range(3):
                trans_pool[t][i] += per[t][i]
        ck.eq(f"transitions sum to the cases ({n})", sum(v[0] for v in per.values()), len(rows))
        ck.eq(f"gain, keep and change sum to rule-3 cases with a target ({n})",
              per[TRANS[0]][0] + per[TRANS[1]][0] + per[TRANS[2]][0],
              rules_out["rule3"]["per_library"][n]["all tiers"]["cases_with_a_target"])
        ck.eq(f"keep, change and lose sum to rule-2 cases with a target ({n})",
              per[TRANS[1]][0] + per[TRANS[2]][0] + per[TRANS[3]][0],
              rules_out["rule2"]["per_library"][n]["all tiers"]["cases_with_a_target"])
        trans_lib[n] = {t: _trans_cell(v) for t, v in per.items()}
    rules_out["transitions"] = {"per_library": trans_lib,
                                "pooled": {t: _trans_cell(v) for t, v in trans_pool.items()}}
    ck.eq("pooled transitions sum to the pooled cases", sum(v[0] for v in trans_pool.values()),
          case_tot["cases_of_the_study"])
    out["rules"] = rules_out

    # ---- T1, T2, T3 ------------------------------------------------------------------------
    texp = {}
    for n in names:
        r2 = rules_out["rule2"]["per_library"][n]["all tiers"]
        r3 = rules_out["rule3"]["per_library"][n]["all tiers"]
        class_a = sorted(k for k, f in labels[n]["first_reading"].get("per_flag", {}).items() if f["class"] == "A")
        rows = rule3[n]["cases"]
        keep = [k for k in class_a if k in rows and rows[k]["rule2"]["target"]
                and rows[k]["rule2"]["target"] == rows[k]["rule3"]["target"]]
        w3, d3 = r3["cases_with_a_target"], r3["decided_by_the_target"]
        texp[n] = {
            "T1": {"rule2_flags": r2["not_decided_by_the_target"], "rule3_flags": r3["not_decided_by_the_target"],
                   "rule2_flags_equal_stated_60": r2["not_decided_by_the_target"] == 60,
                   "holds": r3["not_decided_by_the_target"] <= 10
                   and r3["not_decided_by_the_target"] < r2["not_decided_by_the_target"]},
            "T2": {"class_a_cases": len(class_a), "keep_their_target": len(keep), "class_a_ids": class_a,
                   "holds": (len(keep) == len(class_a)) if class_a else None},
            "T3": {"rule3_decided": frac(Fraction(d3, w3)) if w3 else None, "rule3_decided_count": d3,
                   "rule3_with_a_target": w3,
                   "rule2_decided": frac(Fraction(r2["decided_by_the_target"], r2["cases_with_a_target"]))
                   if r2["cases_with_a_target"] else None,
                   "rule2_equal_stated_71_of_131": (r2["decided_by_the_target"], r2["cases_with_a_target"])
                   == (71, 131),
                   "holds": (d3 * 100 >= 85 * w3) if w3 else None},
        }
        st = rule3[n]["expectations"]
        ck.eq(f"T1 recomputed equals the stated verdict ({n})", texp[n]["T1"]["holds"], st["T1"]["holds"])
        ck.eq(f"T3 recomputed equals the stated verdict ({n})", texp[n]["T3"]["holds"], st["T3"]["holds"])
        if st["T2"].get("class_a_cases_given"):
            ck.eq(f"T2 recomputed equals the stated verdict ({n})", texp[n]["T2"]["holds"], st["T2"]["holds"])
    stated_for = "joserfc"
    out["expectations_rule"] = {
        "stated_for": stated_for,
        "status": ({e: ("held" if texp[stated_for][e]["holds"] else "not held")
                    if texp[stated_for][e]["holds"] is not None else "not applicable"
                    for e in ("T1", "T2", "T3")} if stated_for in texp else "joserfc not among the names"),
        "per_library_quantities": texp,
        "note": "T1, T2 and T3 are stated for joserfc; the quantities of the other libraries are descriptive.",
    }
    out["checks"] = dict(sorted(ck.results.items()))
    out["checks_failed"] = ck.failed()
    return out


def _derived(cats: dict, rows: dict, lk: str, tier: str) -> dict:
    with_target = cats[PVL[0]] + cats[PVL[1]] + cats[PVL[2]]
    no_agreed_with_target = sum(
        1 for r in rows.values()
        if r[lk]["target"] and r["labels"]["agreed"] in (NO_AGREED, UNRESOLVED)
        and (tier == "all tiers" or r[lk]["tier"] == tier))
    return {"cases_with_a_target": with_target + no_agreed_with_target,
            "cases_with_a_target_and_no_agreed_label": no_agreed_with_target,
            "cases_with_a_target_and_an_agreed_label": with_target,
            "target_equals_label": cats[PVL[0]],
            "target_is_not_the_label": cats[PVL[1]] + cats[PVL[2]],
            "target_is_not_the_label_another_check": cats[PVL[1]],
            "target_is_not_the_label_agreed_label_none": cats[PVL[2]]}


def _derived_sum(cells: list[dict]) -> dict:
    keys = [k for k in cells[0] if k != "categories"] if cells else []
    return {k: sum(c[k] for c in cells) for k in keys}


def _rule_cell(v: list[int]) -> dict:
    return {"cases_with_a_target": v[0], "decided_by_the_target": v[1], "not_decided_by_the_target": v[0] - v[1]}


def _trans_cell(v: list[int]) -> dict:
    return {"count": v[0], "decided_by_the_rule2_target": v[1], "decided_by_the_rule3_target": v[2]}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Cross-library totals of the second computation.")
    ap.add_argument("--out-dir", default="recompute/out")
    ap.add_argument("--names", nargs="+", default=list(NAMES))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if len(set(args.names)) != len(args.names):
        print("second_totals: a name is given 2 times", file=sys.stderr)
        return 2
    try:
        data, ck = compute(args)
    except InputError as exc:
        print(f"second_totals: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    ag = data["agreement"]["pooled"]
    tx, nm = ag["every_label_text_as_a_category"], ag["names_a_check_or_none"]

    def v(x):
        return "none" if x is None else f"{x['value']:.4f}"
    print(f"second_totals: {len(args.names)} libraries, {ag['included_blocks']} blocks, "
          f"{data['cases']['pooled']['cases_of_the_study']} cases; pooled kappa by text {v(tx['kappa'])}, "
          f"by names a check {v(nm['kappa'])}; checks {len(ck.results)}, failed {len(ck.failed())}")
    for name in ck.failed():
        print(f"second_totals: check does not hold: {name}", file=sys.stderr)
    return 1 if ck.failed() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
