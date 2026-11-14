"""Validate the toolkit on PyJWT 2.15.1 against the reference experiment.

    <venv>/bin/python -I validate_pyjwt.py

Reads the reference experiment ../mutation-adequacy-pyjwt/ (checks.json,
cases.json, generated/cases.csv, generated/deletions.csv) read-only, and this
toolkit's subjects/pyjwt/ and generated/pyjwt/ outputs, and writes
generated/pyjwt/VALIDATION.md. It changes no definition of the toolkit.

PyJWT is the development subject of the toolkit: the target rule was revised
after its first version had been compared with the hand labels of the
reference experiment (section 4 says how). The agreement reported here is
therefore not an independent validation of the rule.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

E = Path(__file__).resolve().parent
sys.path.insert(0, str(E))


P = E.parent / "mutation-adequacy-pyjwt"
DEFS = E / "subjects" / "pyjwt"
GEN = E / "generated" / "pyjwt"
WORK = E / "work" / "pyjwt"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    p_checks = load(P / "checks.json")
    p_cases = load(P / "cases.json")
    checks = load(DEFS / "checks.json")
    blocks = load(DEFS / "blocks.json")
    targets = load(DEFS / "targets.json")
    out: list[str] = ["# Validation on PyJWT 2.15.1", "",
                      "Reference: `../mutation-adequacy-pyjwt/` (`checks.json`, `cases.json`, "
                      "`generated/cases.csv`, `generated/deletions.csv`), read-only. Check ids are "
                      "mapped through (function, raise numbers); the reference numbers raise statements "
                      "from 0, this toolkit from 1, so 1 is added to the reference numbers.", ""]
    results = {}

    # -- 1. checks ----------------------------------------------------------------------
    ours = {(c["function"], tuple(c["raise_numbers"])): c for c in checks["checks"]}
    p_sig = {c["id"]: (c["function"], tuple(k + 1 for k in c["raises"])) for c in p_checks["checks"]}
    p_to_ours = {pid: ours[s]["id"] for pid, s in p_sig.items() if s in ours}
    p_mut = {p_sig[c["id"]] for c in p_checks["checks"] if c["mutated"]}
    p_ext = {p_sig[c["id"]] for c in p_checks["checks"] if not c["mutated"]}
    our_sub = {k for k, c in ours.items() if c["role"] == "subject"}
    our_sub_reach = {k for k, c in ours.items() if c["role"] == "subject" and c["reachable"]}
    our_obs_reach = {k for k, c in ours.items() if c["role"] == "observed" and c["reachable"]}
    only_ours = sorted(our_sub - p_mut)
    only_ref = sorted(p_mut - our_sub)
    ext_missing = sorted(p_ext - our_obs_reach)
    class_diff = [(pid, c["class"], ours[p_sig[pid]]["class_name"]) for pid, c in
                  ((c["id"], c) for c in p_checks["checks"]) if p_sig[pid] in ours
                  and ours[p_sig[pid]]["class_name"] != c["class"]]
    results["checks"] = {"reference": len(p_mut), "ours_subject_files": len(our_sub),
                         "ours_subject_files_reachable": len(our_sub_reach), "common": len(p_mut & our_sub),
                         "only_ours": only_ours, "only_reference": only_ref,
                         "external_found": len(p_ext) - len(ext_missing), "external_missing": ext_missing}
    out += ["## 1. Checks", "",
            f"- Reference checks in `jwt/api_jws.py` and `jwt/api_jwt.py`: {len(p_mut)}.",
            f"- Toolkit checks in the 2 files: {len(our_sub)} ({len(our_sub_reach)} reachable).",
            f"- Equal as (function, raise numbers): {len(p_mut & our_sub)}; only in the toolkit: "
            f"{len(only_ours)}; only in the reference: {len(only_ref)}.",
            f"- Classes differ on {len(class_diff)} common checks.",
            f"- Reference external checks in `jwt/algorithms.py` found among the observed file's reachable "
            f"checks: {len(p_ext) - len(ext_missing)} of {len(p_ext)} (the toolkit finds "
            f"{len(our_obs_reach)} reachable checks there).", ""]
    if only_ours:
        out += ["Checks only in the toolkit (the reference lists their functions as outside the subject, "
                "since they only encode; the toolkit marks them reachable because `PyJWS._load` calls "
                "`jwt.encode(\"utf-8\")` on its `jwt` argument, and the name rule `X.f` resolves `encode` "
                "to `PyJWS.encode`; `PyJWS.encode` is then reachable, and from it `PyJWT.encode` and "
                "`PyJWT._encode_payload`):", ""]
        out += [f"- `{ours[k]['id']}` {ours[k]['class']} `{ours[k]['template']}`, raise numbers "
                f"{list(k[1])}, reachable: {ours[k]['reachable']}" for k in only_ours]
        out.append("")
    if only_ref or ext_missing or class_diff:
        out += [f"- only in the reference: {only_ref}", f"- external missing: {ext_missing}",
                f"- class differences: {class_diff}", ""]
    out += ["Toolkit reachable checks of `jwt/algorithms.py` that the reference does not list as "
            "external checks: " + ", ".join(f"`{ours[k]['id']}`" for k in sorted(our_obs_reach - p_ext))
            + ". No case reaches them at baseline unless listed under 3.", ""]

    # -- 2. blocks ------------------------------------------------------------------------
    def bkey(file: str, test: str, k: int) -> tuple:
        return (Path(file).name, test, k)
    p_inc = {bkey(b["file"], b["test"], b["k"]): b for b in p_cases["blocks"] if b["included"]}
    o_inc = {bkey(b["file"], b["test"], b["k"]): b for b in blocks["blocks"] if b["included"]}
    o_all = {bkey(b["file"], b["test"], b["k"]): b for b in blocks["blocks"]}
    b_only_ours = sorted(set(o_inc) - set(p_inc))
    b_only_ref = sorted(set(p_inc) - set(o_inc))
    resolved = [b["key"] for b in blocks["blocks"] if b["included"] and b["expected_resolution"] != "direct"]
    results["blocks"] = {"reference": len(p_inc), "ours": len(o_inc), "common": len(set(p_inc) & set(o_inc)),
                         "only_ours": b_only_ours, "only_reference": b_only_ref}
    out += ["## 2. Blocks", "",
            f"- Reference included blocks: {len(p_inc)} (of {p_cases['counts']['raises_blocks']} "
            f"`with pytest.raises` blocks, {p_cases['counts']['decode_blocks']} calling a decode function).",
            f"- Toolkit included blocks: {len(o_inc)} (of {blocks['counts']['blocks']} blocks, "
            f"{blocks['counts']['entry_point_blocks']} with an entry-point call; the toolkit also counts "
            f"the 3 callable-form `pytest.raises` uses of the suite, none of which is included).",
            f"- Equal as (file, test, k): {len(set(p_inc) & set(o_inc))}; only in the toolkit: "
            f"{len(b_only_ours)}; only in the reference: {len(b_only_ref)}.",
            f"- Blocks whose expected class was read through a local assignment in the test: "
            f"{', '.join('`' + k + '`' for k in resolved) or 'none'}.", ""]
    for k in b_only_ours + b_only_ref:
        b = o_all.get(k)
        out.append(f"- {k}: toolkit {'included' if k in o_inc else 'excluded ' + str(b and b['exclusion'])}")
    if b_only_ours or b_only_ref:
        out.append("")

    # map reference block key -> toolkit block key
    ref_to_ours = {b["key"]: o_all[bkey(b["file"], b["test"], b["k"])]["key"]
                   for b in p_cases["blocks"] if bkey(b["file"], b["test"], b["k"]) in o_all}

    # -- 3. sites -------------------------------------------------------------------------
    base = load(WORK / "records" / "base-1.json")
    o_cases = {f"{c['test']}|{c['block']}|{c['index']}": c for c in base["cases"] if c["included"]}
    p_rows = read_csv(P / "generated" / "cases.csv")
    site_equal, site_diff, missing = 0, [], []
    for r in p_rows:
        node, pkey, occ = r["case"].split("|")
        okey = f"{node}|{ref_to_ours.get(pkey)}|{occ}"
        c = o_cases.get(okey)
        if c is None:
            missing.append(r["case"])
            continue
        want = p_to_ours.get(r["baseline_site"], f"(unmapped {r['baseline_site']})") if r["baseline_site"] else None
        got = (c.get("site") or {}).get("check")
        if want == got:
            site_equal += 1
        else:
            site_diff.append((r["case"], want, got))
    extra_cases = len(o_cases) - (len(p_rows) - len(missing))
    results["sites"] = {"reference_cases": len(p_rows), "toolkit_cases": len(o_cases), "equal": site_equal,
                        "different": site_diff, "missing": missing}
    out += ["## 3. Sites", "",
            f"- Reference baseline cases: {len(p_rows)}; toolkit baseline cases: {len(o_cases)}; "
            f"reference cases absent from the toolkit record: {len(missing)}; toolkit cases not in the "
            f"reference: {extra_cases}.",
            f"- Baseline site check equal (check level, segments ignored): {site_equal} of {len(p_rows)}; "
            f"different: {len(site_diff)}.", ""]
    out += [f"- different: `{a}`: reference {b}, toolkit {c}" for a, b, c in site_diff]
    out += [f"- missing: `{m}`" for m in missing]
    if site_diff or missing:
        out.append("")

    # -- 4. targets -----------------------------------------------------------------------
    t_by_key = {t["key"]: t for t in targets["blocks"]}

    def table(tmap: dict) -> tuple[Counter, list, dict]:
        conf: Counter = Counter()
        diffs = []
        by_basis: dict[str, Counter] = {}
        for b in p_cases["blocks"]:
            if not b["included"]:
                continue
            okey = ref_to_ours.get(b["key"])
            t = tmap.get(okey, {})
            rule = t.get("target")
            label = b.get("label", {})
            if "by_param" in label:
                hand = {v: p_to_ours.get(x["target"]) for v, x in label["values"].items()}
                hand_set = set(hand.values())
            else:
                hand = p_to_ours.get(label["target"]) if label.get("target") else None
                hand_set = {hand} if hand else set()
            if rule and hand_set:
                cell = "both, equal" if hand_set == {rule} else "both, different"
                if cell == "both, different":
                    diffs.append((b["test"], b["key"], hand, rule, t.get("basis")))
            elif rule:
                cell = "rule only"
            elif hand_set:
                cell = "hand only"
            else:
                cell = "neither"
            conf[cell] += 1
            basis = t.get("basis") or f"none: {t.get('reason')}"
            by_basis.setdefault(basis, Counter())[cell] += 1
        return conf, diffs, by_basis

    conf, diffs, by_basis = table(t_by_key)
    cells = ["both, equal", "both, different", "rule only", "hand only", "neither"]
    results["targets"] = {"confusion": {c: conf.get(c, 0) for c in cells},
                          "hand_labelled": p_cases["counts"]["labelled_blocks"],
                          "rule_targets": sum(1 for t in targets["blocks"] if t["target"])}
    out += ["## 4. Targets", "",
            f"Rule `{targets['rule_version']}`. Version 1 of the rule was written without the hand "
            "labels and gave 37 equal, 1 different, 1 rule only, 31 hand only and 9 neither. Version 2 "
            "was written after that comparison: an assertion that a message with a placeholder cannot "
            "satisfy now excludes the check, and a check whose literal message text satisfies an "
            "assertion is preferred before the name of the test is read. "
            f"Reference hand labels: {p_cases['counts']['labelled_blocks']} of "
            f"{p_cases['counts']['included_blocks']} included blocks; rule targets: "
            f"{results['targets']['rule_targets']} of {len(targets['blocks'])}. Unit: the included block "
            "(the block in `test_decode_raises_clean_error_if_claim_is_non_numeric_type` has 1 hand label "
            "per value of its `claim` parameter; it counts as equal only if all 3 equal the rule's target).",
            "", "| Cell | Blocks |", "|---|---|"]
    out += [f"| {c} | {conf.get(c, 0)} |" for c in cells]
    out += ["", "By basis of the rule:", "", "| Basis or reason | " + " | ".join(cells) + " |",
            "|---|" + "---|" * len(cells)]
    for basis in sorted(by_basis):
        out.append(f"| {basis} | " + " | ".join(str(by_basis[basis].get(c, 0)) for c in cells) + " |")
    out += ["", "Both labelled, different:", ""]
    out += [f"- `{t}` (`{k}`): hand {h}, rule `{r}` ({bs})" for t, k, h, r, bs in diffs]
    hand_only, rule_only = [], []
    for b in p_cases["blocks"]:
        if b["included"]:
            t = t_by_key.get(ref_to_ours.get(b["key"]), {})
            lab = b.get("label", {})
            has = "by_param" in lab or lab.get("target")
            if has and not t.get("target"):
                hand_only.append((b["test"], lab.get("target") or "by parameter", t.get("reason"),
                                  [s["check"] for s in t.get("scores", [])[:2]]))
            if not has and t.get("target"):
                rule_only.append(f"- `{b['test']}`: rule `{t['target']}` ({t['basis']}); hand: "
                           f"{lab.get('reason')}")
    out += ["", "Rule only (no hand label):", ""] + rule_only
    out += ["", "Hand only (the rule gives no target):", ""]
    out += [f"- `{t}`: hand {h}; rule: {r}; top candidates {c}" for t, h, r, c in hand_only]
    out.append("")

    # -- 5. deletions ---------------------------------------------------------------------
    p_del = {r["check"]: r for r in read_csv(P / "generated" / "deletions.csv") if r["reached"] == "yes"}
    o_del = {r["check"]: r for r in read_csv(GEN / "deletions.csv")}
    agree = Counter()
    del_diff = []
    side = []
    mapped = {p_to_ours[pid]: pid for pid in p_del}
    for pid, r in sorted(p_del.items()):
        oid = p_to_ours.get(pid)
        o = o_del.get(oid)
        if o is None:
            del_diff.append((pid, oid, "not deleted by the toolkit"))
            continue
        for ref_col, our_col in (("O_V", "O_V"), ("O_V^fc", "O_Vfc"), ("O_C", "O_C")):
            if r[ref_col] == o[our_col]:
                agree[our_col] += 1
            else:
                del_diff.append((pid, oid, f"{our_col}: reference {r[ref_col]}, toolkit {o[our_col]}"))
        side.append((pid, oid, r["O_T"], o["O_T"], r["O_S"], o["O_S"], o["suite"]))
    extra_del = sorted(set(o_del) - set(mapped))
    hidden_ref = {c: sum(1 for r in p_del.values() if r[c] == "no") for c in ("O_V", "O_V^fc", "O_C", "O_T", "O_S")}
    hidden_our = {c: sum(1 for r in o_del.values() if r[c] == "no") for c in ("O_V", "O_Vfc", "O_C", "O_T", "O_S", "suite")}
    results["deletions"] = {"reference_reached": len(p_del), "toolkit": len(o_del), "agree": dict(agree),
                            "differences": del_diff, "extra": extra_del}
    out += ["## 5. Deletions", "",
            f"- Reference reached checks deleted: {len(p_del)}; toolkit deletions: {len(o_del)}; "
            f"toolkit deletions not in the reference set: {len(extra_del)}.",
            f"- Agreement on detection: O_V {agree['O_V']} of {len(p_del)}, O_Vfc {agree['O_Vfc']} of "
            f"{len(p_del)}, O_C {agree['O_C']} of {len(p_del)}.",
            f"- Not detected, reference: {json.dumps(hidden_ref)}; toolkit: {json.dumps(hidden_our)}.", ""]
    out += [f"- difference: `{a}` (`{b}`): {c}" for a, b, c in del_diff]
    if del_diff:
        out.append("")
    summ = load(GEN / "summary.json")
    failed = [x for x in summ["sentinels"] if not x["pass"]]
    out += ["Sentinels of `analyse.py`: " + ("all pass." if not failed else "; ".join(
        f"FAIL {x['name']} ({x['detail']})" for x in failed)), ""]
    out += ["O_T and O_S, reported without comparison (O_T uses the rule's targets, O_S is the test's "
            "outcome here and the block's own assertions in the reference):", "",
            "| Check | Toolkit id | O_T ref | O_T toolkit | O_S ref | O_S toolkit | suite toolkit |",
            "|---|---|---|---|---|---|---|"]
    out += [f"| {a} | `{b}` | {c} | {d} | {e} | {f} | {g} |" for a, b, c, d, e, f, g in side]
    out.append("")

    # -- 6. unit tests ----------------------------------------------------------------------
    proc = subprocess.run([sys.executable, "-I", "-B", "-m", "pytest", str(E / "tests"), "-q",
                           "-p", "no:cacheprovider"], capture_output=True, text=True, cwd=str(E))
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    summary_line = re.sub(r" in [0-9.]+s", "", tail[-1].strip("= ")) if tail else ""
    results["unit_tests"] = {"returncode": proc.returncode, "summary": summary_line}
    out += ["## 6. Unit tests", "", f"`tests/` on the synthetic package: {summary_line} "
            f"(return code {proc.returncode}).", ""]

    (GEN / "VALIDATION.md").write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(json.dumps({k: (v if k != "targets" else v["confusion"]) for k, v in results.items()},
                     default=str)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
