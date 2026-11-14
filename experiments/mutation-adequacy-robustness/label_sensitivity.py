"""Analysis C of PROTOCOL.md: labels that rest on a test's name.

    python3 -I label_sensitivity.py

Reads only deposited files of the PyJWT study (../mutation-adequacy-pyjwt/):
cases.json (the basis of every label), checks.json (the function of each
target check), generated/outcomes.jsonl (every case's observation in every
run), and, for the reproduction sentinel, generated/summary.json,
deletions.csv, mutants.csv and p5.csv. Writes generated/label-sensitivity.csv,
.json and .md in this folder.

O_T and O_C are scored by the study's own functions (`holds`, `evaluate`,
`target_of` of analyse_s2.py, imported read-only without writing bytecode).
A block left out of a label set is a block without a target. The row for
"all" must reproduce the study's numbers; otherwise the script stops.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent / "mutation-adequacy-pyjwt"
STUDY_GEN = STUDY / "generated"
OUT = HERE / "generated"


def fail(message: str) -> None:
    raise SystemExit(f"label_sensitivity.py: SENTINEL FAILED: {message}")


def load_study_module():
    """Import analyse_s2.py without writing __pycache__ into the study."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("analyse_s2_readonly", STUDY / "analyse_s2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load_study_module()

CASES_JSON = json.loads((STUDY / "cases.json").read_text(encoding="utf-8"))
CHECKS_JSON = json.loads((STUDY / "checks.json").read_text(encoding="utf-8"))
CHECK_BY_ID = {c["id"]: c for c in CHECKS_JSON["checks"]}
INCLUDED = {b["key"]: b for b in CASES_JSON["blocks"] if b["included"]}

# PROTOCOL.md, C: the three label sets, selected by the recorded basis alone.
LABEL_SETS = (
    ("all", lambda basis: True),
    ("without name-only", lambda basis: not basis.startswith("name:")),
    ("without any name", lambda basis: "name:" not in basis),
)


def label_values(block: dict) -> list[tuple[str | None, dict]]:
    """Each target-bearing entry of a block's label: (parameter value, entry).
    A block labelled per parameter value has one entry per value."""
    label = block["label"]
    if "by_param" in label:
        return [(v, e) for v, e in sorted(label["values"].items())]
    return [(None, label)]


def entry_for(block: dict, params: dict) -> dict:
    label = block["label"]
    if "by_param" in label:
        return label["values"][params[label["by_param"]]]
    return label


def observation_to_rec(obs: list, fields: list[str]) -> tuple[str, dict | None]:
    if obs[0] != "observed":
        return obs[0], None
    values = dict(zip(fields[1:], obs[1:]))
    rec = {k: values[k] for k in ("outcome", "class", "pyjwt_error", "message", "claim", "cause_mro", "real")}
    rec["site"] = {"check": values["site_check"], "segment": values["site_segment"]}
    return "observed", rec


def read_outcomes():
    lines = (STUDY_GEN / "outcomes.jsonl").read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    fields = header["fields"]
    order = [c["case"] for c in header["cases"]]
    base_obs = {c["case"]: c["baseline"] for c in header["cases"]}
    runs = []
    for line in lines[1:]:
        entry = json.loads(line)
        if entry["state"] == "ran":
            cases = {}
            for cid, obs in zip(order, entry["cases"]):
                cases[cid] = observation_to_rec(base_obs[cid] if obs is None else obs, fields)
            state = {"state": "ran", "cases": cases}
        else:
            state = {"state": entry["state"], "cases": {}}
        runs.append((entry["run"], entry["set"], state))
    return header, fields, order, base_obs, runs


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    header, fields, order, base_obs, runs = read_outcomes()
    summary = json.loads((STUDY_GEN / "summary.json").read_text(encoding="utf-8"))
    deletion_rows = {r["check"]: r for r in read_csv(STUDY_GEN / "deletions.csv")}
    mutant_rows = {r["key"]: r for r in read_csv(STUDY_GEN / "mutants.csv")}
    p5_rows = {r["case"]: r for r in read_csv(STUDY_GEN / "p5.csv")}

    base_state = {"state": "ran", "cases": {cid: observation_to_rec(base_obs[cid], fields) for cid in order}}
    meta = {c["case"]: c for c in header["cases"]}

    # Sentinel: the label recomputed from cases.json equals the study's for every case.
    for cid in order:
        m = meta[cid]
        target, segment = A.target_of(INCLUDED[m["key"]], m["params"])
        if (target, segment, target is not None) != (m["target"], m["segment"], m["labelled"]):
            fail(f"target of {cid} recomputed from cases.json differs from outcomes.jsonl")
    labelled_blocks_all = sum(1 for b in INCLUDED.values() if any(e.get("target") for _, e in label_values(b)))
    if labelled_blocks_all != CASES_JSON["counts"]["labelled_blocks"]:
        fail(f"{labelled_blocks_all} labelled blocks, cases.json counts {CASES_JSON['counts']['labelled_blocks']}")

    mutants = [(name, st) for name, kind, st in runs if kind == "mutant"]
    deletions = {name: st for name, kind, st in runs if kind == "deletion"}
    subject_keys = sorted(k for k, r in mutant_rows.items() if r["subject"] == "yes")
    if sorted(name for name, _ in mutants) != subject_keys:
        fail("mutant runs in outcomes.jsonl do not match the subject mutants of mutants.csv")
    reached = sorted({meta[cid]["site"] for cid in order if meta[cid]["site"]} & set(deletions))
    if len(reached) != summary["checks"]["reached"]:
        fail(f"{len(reached)} reached checks, the study reports {summary['checks']['reached']}")

    nested_case = [m["case"] for m in summary["predictions"]["P1"]["O_T_misses"]]
    p3_named = sorted(summary["predictions"]["P3"]["killed_O_T_not_O_C"])

    # O_C does not depend on labels.
    cases_all = {cid: {"B": meta[cid]["B"], "labelled": meta[cid]["labelled"], "target": meta[cid]["target"],
                       "segment": meta[cid]["segment"], "params": meta[cid]["params"], "post": meta[cid]["post"],
                       "message": None} for cid in order}
    s_c = {cid for cid, (k, rec) in base_state["cases"].items() if k == "observed" and A.holds("O_C", cases_all[cid], rec)}
    oc_kill = {}
    for key, st in mutants:
        oc_kill[key] = A.evaluate(st, {"O_C": s_c}, cases_all, oracles=("O_C",))["O_C"]["killed"]
    kills_c = {k for k, v in oc_kill.items() if v}
    bad = [k for k in subject_keys if (k in kills_c) != (mutant_rows[k]["O_C"] == "yes")]
    if bad:
        fail(f"O_C recomputed differs from mutants.csv for {len(bad)} mutants, e.g. {bad[0]}")

    results = []
    for set_name, keep in LABEL_SETS:
        left_out_blocks, kept_blocks = [], 0
        for key in sorted(INCLUDED):
            entries = [(v, e) for v, e in label_values(INCLUDED[key]) if e.get("target")]
            if not entries:
                continue
            kept = [v for v, e in entries if keep(e["basis"])]
            dropped = [v for v, e in entries if not keep(e["basis"])]
            if kept:
                kept_blocks += 1
            if dropped:
                left_out_blocks.append({"block": key, "values_left_out": [v for v in dropped if v is not None],
                                        "whole_block": not kept,
                                        "basis": sorted({e["basis"] for v, e in entries if v in dropped})})
        cases = {}
        for cid in order:
            m = meta[cid]
            labelled = bool(m["labelled"]) and keep(entry_for(INCLUDED[m["key"]], m["params"])["basis"])
            cases[cid] = dict(cases_all[cid], labelled=labelled,
                              target=m["target"] if labelled else None,
                              segment=m["segment"] if labelled else None)
        labelled = sorted(cid for cid in order if cases[cid]["labelled"])
        s_t = {cid for cid in labelled if A.holds("O_T", cases[cid], base_state["cases"][cid][1])}
        p1_misses = sorted(set(labelled) - s_t)
        s = {"O_T": s_t}

        verdict = {key: A.evaluate(st, s, cases, oracles=("O_T",))["O_T"] for key, st in mutants}
        kills_t = {k for k, v in verdict.items() if v["killed"]}
        del_undetected = sorted(d for d in reached
                                if not A.evaluate(deletions[d], s, cases, oracles=("O_T",))["O_T"]["killed"])
        t_not_c = sorted(kills_t - kills_c)
        c_not_t = sorted(kills_c - kills_t)

        p5 = []
        for cid in sorted(s_t):
            check = CHECK_BY_ID[cases[cid]["target"]]
            if not check["mutated"]:
                continue
            own = [k for k in subject_keys if mutant_rows[k]["function"] == check["function"]
                   and cid in verdict[k]["cases"]]
            p5.append({"case": cid, "target": check["id"], "function": check["function"], "kills_O_T": len(own)})
        p5_failing = sorted(r["case"] for r in p5 if r["kills_O_T"] == 0)

        targets_in_set = sorted({cases[cid]["target"] for cid in labelled})
        res = {
            "label_set": set_name,
            "labelled_blocks": kept_blocks,
            "blocks_left_out": left_out_blocks,
            "cases_with_target": len(labelled),
            "target_checks": targets_in_set,
            "P1_O_T_holds": len(s_t),
            "P1_O_T_fails_on": p1_misses,
            "reached_deletions": len(reached),
            "deletions_undetected_O_T": del_undetected,
            "kills_O_T": len(kills_t),
            "kills_O_C": len(kills_c),
            "O_T_not_O_C": t_not_c,
            "O_C_not_O_T": c_not_t,
            "P5_cases": len(p5),
            "P5_failing": p5_failing,
            "P5_rows": p5,
            "named_findings": {
                "nested_header_case": {cid: {"labelled": cases[cid]["labelled"],
                                             "O_T_fails": cid in p1_misses} for cid in nested_case},
                "P3_mutants_remaining": [k for k in p3_named if k in t_not_c],
                "P3_mutants_lost": [k for k in p3_named if k not in t_not_c],
                "O_T_not_O_C_new": [k for k in t_not_c if k not in p3_named],
            },
            "_kills_t": kills_t,
            "_verdict": verdict,
        }
        results.append(res)

    # Sentinel: the row for "all" reproduces the study.
    r = results[0]
    sm = summary
    checks_ = [
        ("labelled blocks", r["labelled_blocks"], CASES_JSON["counts"]["labelled_blocks"]),
        ("cases with a target", r["cases_with_target"], sm["cases"]["labelled"]),
        ("P1: O_T holds", r["P1_O_T_holds"], sm["cases"]["S"]["O_T"]),
        ("P1: O_T fails on", r["P1_O_T_fails_on"], sorted(m["case"] for m in sm["predictions"]["P1"]["O_T_misses"])),
        ("deletions of reached checks undetected under O_T", r["deletions_undetected_O_T"],
         sorted(d for d, v in sm["deletions"].items() if v["reached"] and not v["O_T"])),
        ("deletions undetected under O_T, deletions.csv", r["deletions_undetected_O_T"],
         sorted(d for d, row in deletion_rows.items() if row["reached"] == "yes" and row["O_T"] == "no")),
        ("kills(O_T)", r["kills_O_T"], sm["totals"]["O_T"]["killed"]),
        ("kills(O_C)", r["kills_O_C"], sm["totals"]["O_C"]["killed"]),
        ("O_T and not O_C", r["O_T_not_O_C"], p3_named),
        ("O_T and not O_C, count", len(r["O_T_not_O_C"]), sm["gaps"]["O_T - O_C"]),
        ("O_C and not O_T, count", len(r["O_C_not_O_T"]), sm["gaps"]["O_C - O_T"]),
        ("P5 cases", r["P5_cases"], sm["predictions"]["P5"]["cases"]),
        ("P5 failing", r["P5_failing"], sorted(sm["predictions"]["P5"]["failing"])),
        ("P5 per case, p5.csv", {x["case"]: x["kills_O_T"] for x in r["P5_rows"]},
         {c: int(row["kills_O_T"]) for c, row in p5_rows.items()}),
        ("O_T per mutant, mutants.csv", sorted(r["_kills_t"]),
         sorted(k for k in subject_keys if mutant_rows[k]["O_T"] == "yes")),
        ("O_T killing cases per mutant, mutants.csv",
         {k: len(r["_verdict"][k]["cases"]) for k in subject_keys},
         {k: int(mutant_rows[k]["O_T cases"]) for k in subject_keys}),
    ]
    sentinels = []
    for name, got, want in checks_:
        if got != want:
            fail(f"row 'all' does not reproduce the study: {name}: got {got!r}, study {want!r}")
        sentinels.append({"sentinel": f"all reproduces the study: {name}", "result": "pass"})
    sentinels = [{"sentinel": "targets recomputed from cases.json equal outcomes.jsonl for every case", "result": "pass"},
                 {"sentinel": "subject mutant runs equal the subject mutants of mutants.csv", "result": "pass"},
                 {"sentinel": "reached checks equal the study's count", "result": "pass"},
                 {"sentinel": "O_C recomputed equals mutants.csv for every subject mutant", "result": "pass"},
                 *sentinels]

    write(results, sentinels, len(subject_keys))
    print((OUT / "label-sensitivity.md").read_text(encoding="utf-8"))
    print("sentinels: pass")
    return 0


def short(cid: str) -> str:
    return cid.split("|")[1]


def write(results: list[dict], sentinels: list[dict], n_mutants: int) -> None:
    OUT.mkdir(exist_ok=True)
    rows = []
    for r in results:
        nf = r["named_findings"]
        nested = next(iter(nf["nested_header_case"].values()))
        rows.append({
            "label_set": r["label_set"],
            "labelled_blocks": r["labelled_blocks"],
            "blocks_left_out": len(r["blocks_left_out"]),
            "cases_with_target": r["cases_with_target"],
            "P1_O_T_holds": r["P1_O_T_holds"],
            "P1_O_T_fails": len(r["P1_O_T_fails_on"]),
            "reached_deletions": r["reached_deletions"],
            "deletions_undetected_O_T": len(r["deletions_undetected_O_T"]),
            "kills_O_T": r["kills_O_T"],
            "kills_O_C": r["kills_O_C"],
            "O_T_not_O_C": len(r["O_T_not_O_C"]),
            "O_C_not_O_T": len(r["O_C_not_O_T"]),
            "P5_cases": r["P5_cases"],
            "P5_holding": r["P5_cases"] - len(r["P5_failing"]),
            "nested_header_labelled": "yes" if nested["labelled"] else "no",
            "nested_header_O_T_fails": "yes" if nested["O_T_fails"] else "no",
            "P3_named_mutants_remaining": len(nf["P3_mutants_remaining"]),
            "undetected_deletions": " ".join(r["deletions_undetected_O_T"]),
        })
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (OUT / "label-sensitivity.csv").write_text(buf.getvalue(), encoding="utf-8")

    public = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
    doc = {
        "schema": "urn:eatf:experiment:mutation-adequacy-robustness-label-sensitivity:1",
        "analysis": "C",
        "inputs": ["../mutation-adequacy-pyjwt/cases.json", "../mutation-adequacy-pyjwt/checks.json",
                   "../mutation-adequacy-pyjwt/generated/outcomes.jsonl",
                   "../mutation-adequacy-pyjwt/generated/summary.json",
                   "../mutation-adequacy-pyjwt/generated/deletions.csv",
                   "../mutation-adequacy-pyjwt/generated/mutants.csv",
                   "../mutation-adequacy-pyjwt/generated/p5.csv"],
        "selection": {"all": "every labelled block",
                      "without name-only": "drop label entries whose basis begins with 'name:'",
                      "without any name": "drop label entries whose basis contains 'name:'"},
        "subject_mutants": n_mutants,
        "label_sets": public,
        "sentinels": sentinels,
    }
    (OUT / "label-sensitivity.json").write_text(
        json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    out = ["# Analysis C: labels that rest on a test's name", "",
           "Generated by `label_sensitivity.py` from the deposited files of `../mutation-adequacy-pyjwt/`. "
           "Exploratory and post hoc. A block left out of a label set is a block without a target; "
           f"O_T and O_C are scored by the study's own rule over its {n_mutants} subject mutants.", "",
           "| Label set | Labelled blocks | Cases with target | P1: O_T holds | Reached deletions undetected under O_T "
           "| kills(O_T) | O_T and not O_C | O_C and not O_T | P5 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        out.append(f"| {row['label_set']} | {row['labelled_blocks']} | {row['cases_with_target']} | "
                   f"{row['P1_O_T_holds']} of {row['cases_with_target']} | "
                   f"{row['deletions_undetected_O_T']} of {row['reached_deletions']} | {row['kills_O_T']} | "
                   f"{row['O_T_not_O_C']} | {row['O_C_not_O_T']} | {row['P5_holding']} of {row['P5_cases']} |")
    out.append("")
    for r in results:
        nf = r["named_findings"]
        out += [f"## {r['label_set']}", ""]
        if r["blocks_left_out"]:
            out.append("Blocks left out: " + "; ".join(
                f"`{b['block']}`" + (f" (values {', '.join(b['values_left_out'])})" if b["values_left_out"] else "")
                for b in r["blocks_left_out"]) + ".")
        else:
            out.append("Blocks left out: none.")
        out.append("")
        out.append("- P1, O_T fails on: " + (", ".join(f"`{short(c)}`" for c in r["P1_O_T_fails_on"]) or "none") + ".")
        for cid, v in nf["nested_header_case"].items():
            out.append(f"- Nested-header test `{short(cid)}`: "
                       + ("labelled, O_T fails: the finding survives." if v["O_T_fails"] else
                          ("labelled, O_T holds." if v["labelled"] else "left out: the finding does not arise.")))
        out.append("- Reached deletions undetected under O_T: "
                   + (", ".join(r["deletions_undetected_O_T"]) or "none") + ".")
        out.append(f"- The 7 mutants killed under O_T and not O_C in the study: {len(nf['P3_mutants_remaining'])} remain"
                   + (": " + ", ".join(f"`{k}`" for k in nf["P3_mutants_remaining"]) if nf["P3_mutants_remaining"] else "")
                   + (f"; lost: " + ", ".join(f"`{k}`" for k in nf["P3_mutants_lost"]) if nf["P3_mutants_lost"] else "")
                   + ".")
        if nf["O_T_not_O_C_new"]:
            out.append("- New mutants killed under O_T and not O_C: " + ", ".join(f"`{k}`" for k in nf["O_T_not_O_C_new"]) + ".")
        out.append("- Mutants killed under O_C and not O_T: " + (", ".join(f"`{k}`" for k in r["O_C_not_O_T"]) or "none") + ".")
        out.append("- P5, failing cases: " + (", ".join(f"`{short(c)}`" for c in r["P5_failing"]) or "none") + ".")
        out.append("")
    out += ["## Sentinels", ""] + [f"- {s['sentinel']}: {s['result']}" for s in sentinels] + [""]
    (OUT / "label-sensitivity.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
