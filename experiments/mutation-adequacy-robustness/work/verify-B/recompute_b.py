"""Independent recomputation of analysis B (operator classes both tools have).

Reads ../../../mutation-adequacy/generated/{mutants.csv,gap-directions.csv,summary.json}
relative to this file and writes recompute-b.json next to it.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[2] / "mutation-adequacy" / "generated"

CLASSES = {
    "python": {
        "operator replacement": ["swap_op"],
        "boolean literal and negation": ["name", "remove_unary_ops"],
        "string literal": ["string"],
        "method swap": ["symmetric_string_methods_swap", "unsymmetrical_string_methods_swap"],
    },
    "typescript": {
        "operator replacement": ["ArithmeticOperator", "EqualityOperator", "LogicalOperator",
                                 "UnaryOperator", "AssignmentOperator"],
        "boolean literal and negation": ["BooleanLiteral"],
        "string literal": ["StringLiteral"],
        "method swap": ["MethodExpression"],
    },
}
OUTSIDE = {
    "python": ["arg_removal", "assignment", "augmented_assignment", "number", "keywords", "if_exp"],
    "typescript": ["ConditionalExpression", "BlockStatement", "ArrayDeclaration", "ObjectLiteral",
                   "ArrowFunction", "OptionalChaining", "Regex", "UpdateOperator"],
}
DIRECTIONS = ["earlier guard", "later guard", "no defined code", "same guard"]
KILLED = {"killed", "timeout", "segfault", "Killed", "Timeout", "RuntimeError"}
SURVIVED = {"survived", "no tests", "Survived", "NoCoverage"}


def die(msg):
    sys.exit(f"sentinel failed: {msg}")


def tf(v, where):
    if v not in ("true", "false"):
        die(f"{where}: not a boolean: {v!r}")
    return v == "true"


def share(a, b):
    return None if b == 0 else round(a / b, 4)


def block(rows, gap):
    ids = {r["id"] for r in rows}
    g = [gap[i] for i in sorted(ids) if i in gap]
    out = {}
    for variant, sel in (("all", g), ("without_code_literal", [x for x in g if not x["lit"]])):
        sub = rows if variant == "all" else [r for r in rows if not r["lit"]]
        kv = sum(r["O_V"] for r in sub)
        kc = sum(r["O_C"] for r in sub)
        d = Counter(x["direction"] for x in sel)
        out[variant] = {
            "subject_mutants": len(sub),
            "killed_O_V": kv,
            "killed_O_C": kc,
            "gap_mutants": len(sel),
            "gap_by_direction": {k: d.get(k, 0) for k in DIRECTIONS},
            "later_guard_share_of_gap": share(d.get("later guard", 0), len(sel)),
        }
    return out


def main():
    rows = list(csv.DictReader(open(STUDY / "mutants.csv", newline="", encoding="utf-8")))
    gaps = list(csv.DictReader(open(STUDY / "gap-directions.csv", newline="", encoding="utf-8")))
    summary = json.load(open(STUDY / "summary.json", encoding="utf-8"))
    keys = [(r["port"], r["id"]) for r in rows]
    if len(set(keys)) != len(keys):
        die("duplicate mutant ids in mutants.csv")
    result = {}
    for port in ("python", "typescript"):
        mine = []
        excluded = 0
        for r in rows:
            if r["port"] != port:
                continue
            st = r["tool_status"]
            if st not in KILLED | SURVIVED:
                excluded += 1
                continue
            w = f"{port}/{r['id']}"
            mine.append({"id": r["id"], "op": r["operator"], "lit": tf(r["code_literal"], w),
                         "O_V": tf(r["killed_O_V"], w), "O_C": tf(r["killed_O_C"], w)})
        known = {o for ops in CLASSES[port].values() for o in ops} | set(OUTSIDE[port])
        unknown = sorted({m["op"] for m in mine} - known)
        if unknown:
            die(f"{port}: operators not in the protocol's lists: {unknown}")
        for m in mine:
            if m["O_V"] and not m["O_C"]:
                die(f"{port}/{m['id']}: killed under O_V but not under O_C")
        byid = {m["id"]: m for m in mine}
        gap = {}
        for g in gaps:
            if g["port"] != port:
                continue
            if g["id"] in gap:
                die(f"{port}/{g['id']}: duplicate gap row")
            if g["direction"] not in DIRECTIONS:
                die(f"{port}/{g['id']}: unknown direction {g['direction']!r}")
            m = byid.get(g["id"])
            if m is None:
                die(f"{port}/{g['id']}: gap row without a mutant")
            if m["op"] != g["operator"] or m["lit"] != tf(g["code_literal"], g["id"]):
                die(f"{port}/{g['id']}: operator or code-literal flag differs between files")
            gap[g["id"]] = {"direction": g["direction"], "lit": m["lit"]}
        expected_gap = {m["id"] for m in mine if m["O_C"] and not m["O_V"]}
        if expected_gap != set(gap):
            die(f"{port}: gap-directions.csv does not equal the O_C-not-O_V set of mutants.csv")
        # cross-check with the study's own summary
        t = summary["totals"][port]
        if (t["scored"], t["killed_O_V"], t["killed_O_C"], t["excluded"]) != (
                len(mine), sum(m["O_V"] for m in mine), sum(m["O_C"] for m in mine), excluded):
            die(f"{port}: totals differ from the study's summary.json")
        gd = summary["exploratory"]["gap_directions"][port]
        if gd["gap_mutants"] != len(gap) or gd["all"] != dict(sorted(Counter(
                x["direction"] for x in gap.values()).items())):
            die(f"{port}: gap directions differ from the study's summary.json")

        shared_ops = {o for ops in CLASSES[port].values() for o in ops}
        port_out = {
            "excluded": excluded,
            "all_operators": block(mine, gap),
            "shared_classes": block([m for m in mine if m["op"] in shared_ops], gap),
            "outside_classes": block([m for m in mine if m["op"] not in shared_ops], gap),
            "per_class": {c: block([m for m in mine if m["op"] in ops], gap)
                          for c, ops in sorted(CLASSES[port].items())},
            "operators_with_no_mutant": sorted(o for o in known if o not in {m["op"] for m in mine}),
        }
        result[port] = port_out
    out = HERE / "recompute-b.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
