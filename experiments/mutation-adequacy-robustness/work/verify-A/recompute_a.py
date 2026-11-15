#!/usr/bin/env python3
"""Independent recomputation of analysis A (subsuming mutants).

Reads only files of the two finished studies and writes recomputed-a.json next
to this script. Kill sets are rebuilt from each study's outcomes.jsonl with
the study's own kill rule, then cross-checked against the deposited per-mutant
kill columns.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[2]  # experiments/
S1 = EXP / "mutation-adequacy"
S2 = EXP / "mutation-adequacy-pyjwt"
T = "<T>"  # the element that is not a case


def die(msg: str) -> None:
    sys.exit(f"SENTINEL FAILED: {msg}")


def minimal_info(ks: dict[str, frozenset]) -> dict:
    """ks: killed mutant -> nonempty kill set."""
    distinct = set(ks.values())
    minimal_sets = {a for a in distinct if not any(b < a for b in distinct)}
    minimal = {m for m, s in ks.items() if s in minimal_sets}
    return {"killed": len(ks), "distinct": len(distinct), "minimal": minimal,
            "distinct_minimal": len(minimal_sets), "minimal_sets": minimal_sets, "ks": ks}


# ---------------------------------------------------------------- study 1
def study1() -> dict:
    cases = json.loads((S1 / "work" / "cases.json").read_text())["cases"]
    lines = [json.loads(l) for l in (S1 / "generated" / "outcomes.jsonl").read_text().splitlines()]
    order = lines[0]["case_order"]
    if order != [c["id"] for c in cases]:
        die("study 1 case order")
    exp = {c["id"]: c for c in cases}
    states = {(x["port"], x["id"]): x["states"] for x in lines[1:]}
    rows = list(csv.DictReader((S1 / "generated" / "mutants.csv").open()))
    summary = json.loads((S1 / "generated" / "summary.json").read_text())
    gapdir = {(r["port"], r["id"]): r["direction"]
              for r in csv.DictReader((S1 / "generated" / "gap-directions.csv").open())}

    def parse(s):
        if s.startswith("!"):
            return ("exc", None, None)
        v, c = s.split("|")
        return ("ok", v == "T", None if c == "-" else c)

    def holds(o, cid, st):
        kind, v, code = st
        e = exp[cid]
        if kind == "exc":
            return o == "O_V_fc" and e["expected_valid"] is False
        if o in ("O_V", "O_V_fc"):
            return v == e["expected_valid"]
        if o == "O_C":
            return (v, code) == (e["expected_valid"], e["expected_code"])
        if o == "O_T":
            return code == e["target_code"]
        raise ValueError(o)

    out = {}
    for port in ("python", "typescript"):
        base = [parse(s) for s in states[(port, "baseline")]]
        for cid, st in zip(order, base):
            if st[0] != "ok" or (st[1], st[2]) != (exp[cid]["expected_valid"], exp[cid]["expected_code"]):
                die(f"study 1 {port} baseline differs from expectation on {cid}")
        S = {o: {cid for cid, st in zip(order, base) if holds(o, cid, st)} for o in ("O_V", "O_C", "O_T")}
        mine = [r for r in rows if r["port"] == port]
        kill = {o: {} for o in ("O_V", "O_C", "O_T")}
        crosscheck_diff = []
        for r in mine:
            key = (port, r["id"])
            if r["tool_status"] in ("timeout", "segfault", "Timeout"):
                for o in kill:
                    kill[o][r["id"]] = frozenset({T})
                continue
            if key not in states:
                if r["tool_status"] in ("no tests", "NoCoverage", "survived", "Survived"):
                    continue
                for o in kill:  # killed by the tool, no record: uncredited
                    kill[o][r["id"]] = frozenset({T})
                continue
            obs = [parse(s) for s in states[key]]
            raised = any(st[0] == "exc" for st in obs)
            for o in kill:
                by = frozenset(cid for cid, st in zip(order, obs) if cid in S[o] and not holds(o, cid, st))
                if by:
                    kill[o][r["id"]] = by
                elif raised:
                    kill[o][r["id"]] = frozenset({T})
                deposited = frozenset(r[f"by_{o}"].split()) if r[f"by_{o}"] else frozenset()
                if (by != deposited) or ((r["id"] in kill[o]) != (r[f"killed_{o}"] == "true")):
                    crosscheck_diff.append((o, r["id"]))
        if crosscheck_diff:
            die(f"study 1 {port}: recomputed kill sets differ from mutants.csv: {crosscheck_diff[:5]}")
        res = {}
        for o in kill:
            if sum(1 for s in kill[o].values() if s) != summary["totals"][port][f"killed_{o}"]:
                die(f"study 1 {port} {o}: kills differ from summary.json")
            res[o] = minimal_info(kill[o])
        region = {r["id"]: r["region"] for r in mine}
        res["_gap"] = sorted(m for m in kill["O_C"] if m not in kill["O_V"])
        res["_dir"] = {m: gapdir[(port, m)] for m in res["_gap"]}
        res["_spread"] = region
        res["_lit"] = {r["id"]: r["code_literal"] == "true" for r in mine}
        out[port] = res
    return out


# ---------------------------------------------------------------- study 2
def study2() -> dict:
    lines = [json.loads(l) for l in (S2 / "generated" / "outcomes.jsonl").read_text().splitlines()]
    head = lines[0]
    fields = head["fields"]
    cases = head["cases"]
    summary = json.loads((S2 / "generated" / "summary.json").read_text())
    rows = {r["key"]: r for r in csv.DictReader((S2 / "generated" / "mutants.csv").open())}

    def rec(obs):
        d = dict(zip(fields, obs))
        return d

    def post_ok(spec, d, params):
        msg = d["message"]
        k = spec[0]
        if k == "str_eq":
            return msg == spec[1]
        if k == "str_in":
            return msg is not None and spec[1] in msg
        if k == "str_in_param":
            return msg is not None and str(params[spec[1]]) in msg
        if k == "attr_eq":
            assert spec[1] == "claim"
            return d["claim"] == spec[2]
        if k == "cause_isinstance":
            mro = d["cause_mro"] or []
            return any(q == spec[1] or q.split(".")[-1] == spec[1] for q in mro)
        die(f"unknown post {spec}")

    def holds(o, c, d):
        raised = d["outcome"] == "raised"
        if o == "O_V":
            return raised and bool(d["pyjwt_error"])
        if o == "O_V^fc":
            return raised
        if o == "O_C":
            return raised and d["class"] == c["B"]
        if o == "O_T":
            return (raised and c["target"] is not None and d["site_check"] == c["target"]
                    and (c["segment"] is None or d["site_segment"] == c["segment"]))
        if o == "O_S":
            return d["real"] == "ok" and all(post_ok(s, d, c["params"]) for s in c["post"])
        raise ValueError(o)

    oracles = ("O_V", "O_V^fc", "O_C", "O_T", "O_S")
    base = [rec(c["baseline"]) for c in cases]
    S = {o: {i for i, c in enumerate(cases) if base[i]["status"] == "observed" and holds(o, c, base[i])}
         for o in oracles}
    kill = {o: {} for o in oracles}
    diffs = []
    for x in lines[1:]:
        if x["set"] != "mutant":
            continue
        key = x["run"]
        if x["state"] != "ran":
            for o in oracles:
                kill[o][key] = frozenset({T})
            continue
        obs = [base[i] if v is None else rec(v) for i, v in enumerate(x["cases"])]
        crashed = any(d["status"] == "crashed" for d in obs)
        for o in oracles:
            by = frozenset(cases[i]["case"] for i, d in enumerate(obs) if i in S[o] and (
                d["status"] == "crashed" or (d["status"] == "observed" and not holds(o, cases[i], d))))
            if by:
                kill[o][key] = by
            elif crashed:
                kill[o][key] = frozenset({T})
            r = rows[key]
            if (key in kill[o]) != (r[o] == "yes") or len(by) != int(r[f"{o} cases"] or 0):
                diffs.append((o, key))
    if diffs:
        die(f"study 2: recomputed kills differ from mutants.csv: {diffs[:5]}")
    subject = [k for k, r in rows.items() if r["subject"] == "yes"]
    ran = {x["run"] for x in lines[1:] if x["set"] == "mutant"}
    if set(subject) != ran:
        die("study 2: subject mutants and mutant runs differ")
    res = {}
    for o in oracles:
        if sum(1 for s in kill[o].values() if s) != summary["totals"][o]["killed"]:
            die(f"study 2 {o}: kills differ from summary.json")
        res[o] = minimal_info(kill[o])
    res["_gap"] = sorted(m for m in kill["O_C"] if m not in kill["O_V"])

    def direction(moves):
        kinds = sorted({p.rsplit(" ", 1)[0] for p in moves.split("; ") if p})
        return kinds

    res["_dir"] = {m: direction(rows[m]["moves"]) for m in res["_gap"]}
    res["_runs"] = {m: {p.rsplit(" ", 1)[0]: int(p.rsplit(" ", 1)[1]) for p in rows[m]["moves"].split("; ") if p}
                    for m in res["_gap"]}
    res["_spread"] = {k: rows[k]["function"] for k in subject}
    res["_lit"] = {k: rows[k]["exception_argument"] == "yes" for k in subject}
    return res


def report(name, res, oracles, unit):
    out = {"per_oracle": {}}
    for o in oracles:
        r = res[o]
        out["per_oracle"][o] = {"killed": r["killed"], "distinct_kill_sets": r["distinct"],
                                "minimal": len(r["minimal"]), "distinct_minimal_kill_sets": r["distinct_minimal"],
                                "minimal_with_T": sum(1 for s in r["minimal_sets"] if T in s),
                                "kill_set_T_mutants": sum(1 for s in r["ks"].values() if T in s)}
    gap = set(res["_gap"])
    mc = res["O_C"]["minimal"]
    gmin = gap & mc
    msets_with_gap = {res["O_C"]["ks"][m] for m in gmin}
    out["gap"] = {"G": len(gap), "kills_O_C": res["O_C"]["killed"],
                  "minimal_O_C": len(mc), "minimal_in_G": len(gmin), "distinct_minimal_sets_with_G": len(msets_with_gap), "distinct_minimal_sets_O_C": res["O_C"]["distinct_minimal"]}
    out["_gmin"] = sorted(gmin)
    if isinstance(next(iter(res["_dir"].values())), list):
        lab = lambda v: v[0] if len(v) == 1 else "mixed(" + "+".join(v) + ")"
        out["directions_all_G"] = dict(sorted(Counter(lab(res["_dir"][m]) for m in gap).items()))
        out["directions_minimal_G"] = dict(sorted(Counter(lab(res["_dir"][m]) for m in gmin).items()))
        out["mutants_with_minimal_G"] = dict(sorted(Counter(k for m in gmin for k in res["_dir"][m]).items()))
        out["case_runs_minimal_G"] = dict(sorted(sum((Counter(res["_runs"][m]) for m in gmin), Counter()).items()))
        out["case_runs_all_G"] = dict(sorted(sum((Counter(res["_runs"][m]) for m in gap), Counter()).items()))
        out["mutants_with_all_G"] = dict(sorted(Counter(k for m in gap for k in res["_dir"][m]).items()))
    else:
        out["directions_all_G"] = dict(sorted(Counter(res["_dir"][m] for m in gap).items()))
        out["directions_minimal_G"] = dict(sorted(Counter(res["_dir"][m] for m in gmin).items()))
        out["directions_minimal_G_without_literal"] = dict(sorted(
            Counter(res["_dir"][m] for m in gmin if not res["_lit"][m]).items()))
        out["directions_all_G_without_literal"] = dict(sorted(
            Counter(res["_dir"][m] for m in gap if not res["_lit"][m]).items()))
    out["spread"] = {"unit": unit, "with_gap": len({res["_spread"][m] for m in gap}),
                     "with_minimal_gap": len({res["_spread"][m] for m in gmin}),
                     "units_gap": sorted({res["_spread"][m] for m in gap}),
                     "units_minimal_gap": sorted({res["_spread"][m] for m in gmin})}
    out["gap"]["minimal_in_G_literal"] = sum(1 for m in gmin if res["_lit"][m])
    return out


def main():
    s1 = study1()
    s2 = study2()
    result = {}
    for port in ("python", "typescript"):
        result[port] = report(port, s1[port], ("O_V", "O_C", "O_T"), "guard region")
    result["pyjwt"] = report("pyjwt", s2, ("O_V", "O_V^fc", "O_C", "O_T", "O_S"), "function")
    # distinct minimal kill sets under O_C holding a gap mutant
    for name, res in (("python", s1["python"]), ("typescript", s1["typescript"]), ("pyjwt", s2)):
        pass
    (HERE / "recomputed-a.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in result.items()},
                     indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
