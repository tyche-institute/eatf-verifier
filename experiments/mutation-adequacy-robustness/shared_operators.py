#!/usr/bin/env python3
"""Analysis B of PROTOCOL.md: operator classes that both mutation tools have.

Reads the deposited files of the first study (../mutation-adequacy/generated/:
mutants.csv, operators.csv, gap-directions.csv) and writes
generated/shared-operators.csv, .json and .md. Nothing of either subject is run
and no file of the first study is changed.

    python3 -I experiments/mutation-adequacy-robustness/shared_operators.py

Reading of the protocol, as implemented:

- Subject mutants are the scored tool mutants of the first study: every row of
  mutants.csv whose kill under O_C is recorded as true or false. Excluded
  mutants (no recorded kill) are counted and left out, as in that study.
- A gap mutant is a subject mutant killed under O_C and not under O_V. Its
  direction is the one recorded in gap-directions.csv.
- The rows "all operators" and "shared classes" are given for all mutants, as
  the protocol asks, and, as a supplement, without the mutants that only change
  a failure-code literal, the subset on which the first study made its
  comparison of directions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent / "mutation-adequacy"
STUDY_GEN = STUDY / "generated"
GENERATED = HERE / "generated"
INPUTS = ("mutants.csv", "operators.csv", "gap-directions.csv")

PORTS = ("python", "typescript")
TOOLS = {"python": "mutmut 3.8.1", "typescript": "StrykerJS 9.6.1"}

# The correspondence table of PROTOCOL.md, section B, copied as fixed there.
CLASSES = (
    ("operator replacement",
     {"python": ("swap_op",),
      "typescript": ("ArithmeticOperator", "EqualityOperator", "LogicalOperator",
                     "UnaryOperator", "AssignmentOperator")}),
    ("boolean literal and negation",
     {"python": ("name", "remove_unary_ops"), "typescript": ("BooleanLiteral",)}),
    ("string literal",
     {"python": ("string",), "typescript": ("StringLiteral",)}),
    ("method swap",
     {"python": ("symmetric_string_methods_swap", "unsymmetrical_string_methods_swap"),
      "typescript": ("MethodExpression",)}),
)
# Operators that PROTOCOL.md lists as having no counterpart in the other tool.
NO_COUNTERPART = {
    "python": ("arg_removal", "assignment", "augmented_assignment", "number", "keywords", "if_exp"),
    "typescript": ("ConditionalExpression", "BlockStatement", "ArrayDeclaration", "ObjectLiteral",
                   "ArrowFunction", "OptionalChaining", "Regex", "UpdateOperator"),
}

# Directions as the first study names them; "mixed" is the label it gives a
# mutant whose changed cases have more than one direction.
DIRECTIONS = ("later guard", "same guard", "earlier guard", "no defined code", "mixed")
VARIANTS = ("all mutants", "without code-literal mutants")
SHARED = "shared classes"
ALL = "all operators"
OUTSIDE = "outside the table"


def fail(message: str) -> None:
    sys.stderr.write(f"SENTINEL FAILED: {message}\n")
    raise SystemExit(1)


def read_csv(name: str) -> list[dict[str, str]]:
    path = STUDY_GEN / name
    if not path.is_file():
        fail(f"input {path.relative_to(HERE.parent)} is missing")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def flag(value: str, where: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    fail(f"{where}: expected true or false, found {value!r}")
    raise AssertionError


def share(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def main() -> None:
    mutant_rows = read_csv("mutants.csv")
    operator_rows = read_csv("operators.csv")
    gap_rows = read_csv("gap-directions.csv")

    class_of: dict[tuple[str, str], str] = {}
    for name, ops in CLASSES:
        for p in PORTS:
            for op in ops[p]:
                if (p, op) in class_of:
                    fail(f"{op} is in two classes of the table")
                class_of[(p, op)] = name
    for p in PORTS:
        for op in NO_COUNTERPART[p]:
            if (p, op) in class_of:
                fail(f"{op} is both in the table and in the list without counterpart")

    # subject mutants ------------------------------------------------------------------
    subject: dict[str, list[dict]] = {p: [] for p in PORTS}
    excluded = Counter()
    seen_ids: set[tuple[str, str]] = set()
    for r in mutant_rows:
        p = r["port"]
        if p not in PORTS:
            fail(f"mutants.csv: unknown port {p!r}")
        if r["tool"] != TOOLS[p]:
            fail(f"mutants.csv: {r['id']} was made by {r['tool']!r}, not {TOOLS[p]}")
        if (p, r["id"]) in seen_ids:
            fail(f"mutants.csv: duplicate mutant {p} {r['id']}")
        seen_ids.add((p, r["id"]))
        if r["killed_O_C"] == "" and r["killed_O_V"] == "":
            excluded[p] += 1
            continue
        where = f"mutants.csv {p} {r['id']}"
        subject[p].append({
            "id": r["id"], "operator": r["operator"],
            "code_literal": flag(r["code_literal"], where),
            "O_V": flag(r["killed_O_V"], where), "O_C": flag(r["killed_O_C"], where),
        })

    # every observed operator must be placed by the protocol's lists
    unplaced = sorted({(p, m["operator"]) for p in PORTS for m in subject[p]
                       if (p, m["operator"]) not in class_of
                       and m["operator"] not in NO_COUNTERPART[p]})
    if unplaced:
        fail(f"operators neither in the table nor in the list without counterpart: {unplaced}")

    # gap mutants and their directions ---------------------------------------------------
    direction_of: dict[tuple[str, str], str] = {}
    for g in gap_rows:
        key = (g["port"], g["id"])
        if key in direction_of:
            fail(f"gap-directions.csv: duplicate row {key}")
        if g["direction"] not in DIRECTIONS:
            fail(f"gap-directions.csv: unknown direction {g['direction']!r} for {key}")
        direction_of[key] = g["direction"]

    sentinels: dict[str, dict] = {}

    # Sentinel 1: per-operator and per-port totals reproduce operators.csv
    expected_ops = {(o["port"], o["operator"]): o for o in operator_rows}
    mismatches = []
    computed_ops = {}
    for p in PORTS:
        for op in sorted({m["operator"] for m in subject[p]}):
            rr = [m for m in subject[p] if m["operator"] == op]
            computed_ops[(p, op)] = {
                "mutants": len(rr), "code_literal": sum(m["code_literal"] for m in rr),
                "killed_O_V": sum(m["O_V"] for m in rr), "killed_O_C": sum(m["O_C"] for m in rr)}
    for key in sorted(set(expected_ops) | set(computed_ops)):
        e, c = expected_ops.get(key), computed_ops.get(key)
        if e is None or c is None:
            mismatches.append({"port": key[0], "operator": key[1],
                               "missing_in": "operators.csv" if e is None else "mutants.csv"})
            continue
        for field in ("mutants", "code_literal", "killed_O_V", "killed_O_C"):
            if int(e[field]) != c[field]:
                mismatches.append({"port": key[0], "operator": key[1], "field": field,
                                   "operators_csv": int(e[field]), "computed": c[field]})
    port_totals = {}
    for p in PORTS:
        mine = [o for o in operator_rows if o["port"] == p]
        expected = {f: sum(int(o[f]) for o in mine) for f in ("mutants", "killed_O_V", "killed_O_C")}
        computed = {"mutants": len(subject[p]), "killed_O_V": sum(m["O_V"] for m in subject[p]),
                    "killed_O_C": sum(m["O_C"] for m in subject[p])}
        port_totals[p] = {"operators_csv": expected, "computed": computed}
        if expected != computed:
            mismatches.append({"port": p, "field": "port totals", "operators_csv": expected,
                               "computed": computed})
    sentinels["1_totals_reproduce_operators_csv"] = {
        "passed": not mismatches, "port_totals": port_totals, "mismatches": mismatches}
    if mismatches:
        fail(f"totals do not reproduce operators.csv: {mismatches}")

    # Sentinel 2: the gap of mutants.csv is exactly the mutant set of gap-directions.csv,
    # with the same operator and code-literal flag, and gives its counts by direction
    problems = []
    gap_counts = {}
    for p in PORTS:
        computed_gap = {m["id"] for m in subject[p] if m["O_C"] and not m["O_V"]}
        listed = {i for q, i in direction_of if q == p}
        if computed_gap != listed:
            problems.append({"port": p, "only_in_mutants_csv": sorted(computed_gap - listed),
                             "only_in_gap_directions_csv": sorted(listed - computed_gap)})
        by_id = {m["id"]: m for m in subject[p]}
        for g in gap_rows:
            if g["port"] != p or g["id"] not in by_id:
                continue
            m = by_id[g["id"]]
            if g["operator"] != m["operator"] or flag(g["code_literal"], "gap-directions.csv") != m["code_literal"]:
                problems.append({"port": p, "id": g["id"], "field": "operator or code_literal"})
        expected = dict(sorted(Counter(g["direction"] for g in gap_rows if g["port"] == p).items()))
        computed = dict(sorted(Counter(direction_of[(p, i)] for i in computed_gap
                                       if (p, i) in direction_of).items()))
        gap_counts[p] = {"gap_directions_csv": {"gap": sum(expected.values()), **expected},
                         "computed": {"gap": len(computed_gap), **computed}}
        if gap_counts[p]["gap_directions_csv"] != gap_counts[p]["computed"]:
            problems.append({"port": p, "field": "gap counts", **gap_counts[p]})
    sentinels["2_gap_reproduces_gap_directions_csv"] = {
        "passed": not problems, "gap_counts": gap_counts, "mismatches": problems}
    if problems:
        fail(f"gap does not reproduce gap-directions.csv: {problems}")

    # tables -------------------------------------------------------------------------------
    def counts(rr: list[dict], p: str) -> dict:
        gap = [m for m in rr if m["O_C"] and not m["O_V"]]
        by_dir = Counter(direction_of[(p, m["id"])] for m in gap)
        row = {"mutants": len(rr), "killed_O_V": sum(m["O_V"] for m in rr),
               "killed_O_C": sum(m["O_C"] for m in rr), "gap": len(gap)}
        for d in DIRECTIONS:
            row[f"gap_{d.replace(' ', '_')}"] = by_dir.get(d, 0)
        row["later_guard_share"] = share(by_dir.get("later guard", 0), len(gap))
        return row

    groups = [(ALL, None), (SHARED, None)] + [(name, name) for name, _ in CLASSES] + [(OUTSIDE, None)]
    out_rows = []
    for variant in VARIANTS:
        for p in PORTS:
            pool = [m for m in subject[p] if variant == VARIANTS[0] or not m["code_literal"]]
            for label, cls in groups:
                if label == ALL:
                    rr, ops = pool, sorted({m["operator"] for m in pool})
                elif label == SHARED:
                    rr = [m for m in pool if (p, m["operator"]) in class_of]
                    ops = sorted(op for (q, op) in class_of if q == p)
                elif label == OUTSIDE:
                    rr = [m for m in pool if (p, m["operator"]) not in class_of]
                    ops = sorted(NO_COUNTERPART[p])
                else:
                    rr = [m for m in pool if class_of.get((p, m["operator"])) == cls]
                    ops = sorted(op for (q, op), c in class_of.items() if q == p and c == cls)
                out_rows.append({"variant": variant, "port": p, "tool": TOOLS[p], "group": label,
                                 "operators": " ".join(ops), **counts(rr, p)})

    # Sentinel 3: the shared classes and the rest add up to all operators
    additive = []
    for variant in VARIANTS:
        for p in PORTS:
            mine = {r["group"]: r for r in out_rows if r["variant"] == variant and r["port"] == p}
            for field in ("mutants", "killed_O_V", "killed_O_C", "gap",
                          *(f"gap_{d.replace(' ', '_')}" for d in DIRECTIONS)):
                parts = sum(mine[name][field] for name, _ in CLASSES)
                if parts != mine[SHARED][field] or mine[SHARED][field] + mine[OUTSIDE][field] != mine[ALL][field]:
                    additive.append({"variant": variant, "port": p, "field": field})
    sentinels["3_classes_add_up"] = {"passed": not additive, "mismatches": additive}
    if additive:
        fail(f"class rows do not add up: {additive}")

    # operators of the table without any mutant in this subject
    present = {(p, m["operator"]) for p in PORTS for m in subject[p]}
    absent = {p: sorted([op for (q, op) in class_of if q == p and (q, op) not in present]
                        + [op for op in NO_COUNTERPART[p] if (p, op) not in present]) for p in PORTS}

    # outputs ------------------------------------------------------------------------------
    GENERATED.mkdir(exist_ok=True)
    fields = list(out_rows[0])
    with (GENERATED / "shared-operators.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for r in out_rows:
            writer.writerow({k: "" if v is None else v for k, v in r.items()})

    def pick(variant: str, p: str, group: str) -> dict:
        return next(r for r in out_rows if r["variant"] == variant and r["port"] == p and r["group"] == group)

    headline = {variant: {p: {g: {"gap": pick(variant, p, g)["gap"],
                                  "later_guard": pick(variant, p, g)["gap_later_guard"],
                                  "later_guard_share": pick(variant, p, g)["later_guard_share"]}
                              for g in (ALL, SHARED)} for p in PORTS} for variant in VARIANTS}
    summary = {
        "analysis": "B. Operator classes that both tools have (PROTOCOL.md)",
        "exploratory_post_hoc": True,
        "inputs": {f"../mutation-adequacy/generated/{n}":
                   hashlib.sha256((STUDY_GEN / n).read_bytes()).hexdigest() for n in INPUTS},
        "definitions": {
            "subject_mutants": "scored tool mutants of the first study (kill under O_C recorded)",
            "gap": "subject mutants killed under O_C and not under O_V",
            "direction": "as recorded in gap-directions.csv of the first study",
            "later_guard_share": "gap mutants with direction 'later guard' / gap mutants",
            "variants": {"all mutants": "as the protocol asks",
                         "without code-literal mutants": "supplement: the subset on which the "
                                                         "first study compared directions"},
        },
        "correspondence_table": {name: {p: list(ops[p]) for p in PORTS} for name, ops in CLASSES},
        "no_counterpart": {p: list(NO_COUNTERPART[p]) for p in PORTS},
        "excluded_mutants": {p: excluded.get(p, 0) for p in PORTS},
        "listed_operators_without_mutants": absent,
        "headline": headline,
        "rows": out_rows,
        "sentinels": sentinels,
    }
    with (GENERATED / "shared-operators.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    md = ["# Analysis B: operator classes that both tools have", "",
          "Exploratory and post hoc (PROTOCOL.md, section B). Input: the deposited `mutants.csv`, "
          "`operators.csv` and `gap-directions.csv` of `../mutation-adequacy/`. The Python port was "
          "mutated by mutmut 3.8.1 and the TypeScript port by StrykerJS 9.6.1. A gap mutant is "
          "killed under O_C and not under O_V; its direction is the one the first study recorded.", "",
          "Shared classes, as fixed in the protocol:", "",
          "| Class | mutmut 3.8.1 | StrykerJS 9.6.1 |", "|---|---|---|"]
    for name, ops in CLASSES:
        md.append(f"| {name} | {', '.join(f'`{o}`' for o in ops['python'])} | "
                  f"{', '.join(f'`{o}`' for o in ops['typescript'])} |")
    md += [""]
    for p in PORTS:
        if absent[p]:
            md.append(f"Listed operators with no mutant in the {p} port: "
                      f"{', '.join(f'`{o}`' for o in absent[p])}.")
    md.append("")
    head = ("| Port | Group | Mutants | Kills O_V | Kills O_C | Gap | Later guard | Same guard | "
            "Earlier guard | No defined code | Mixed | Later-guard share |")
    for variant in VARIANTS:
        title = ("All mutants" if variant == VARIANTS[0]
                 else "Without the mutants that only change a failure-code literal (supplement)")
        md += [f"## {title}", "", head, "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for p in PORTS:
            for label, _ in groups:
                r = pick(variant, p, label)
                md.append(f"| {p} | {label} | {r['mutants']} | {r['killed_O_V']} | {r['killed_O_C']} | "
                          f"{r['gap']} | {r['gap_later_guard']} | {r['gap_same_guard']} | "
                          f"{r['gap_earlier_guard']} | {r['gap_no_defined_code']} | {r['gap_mixed']} | "
                          f"{pct(r['later_guard_share'])} |")
        md.append("")
    md += ["## Sentinels", ""]
    for name, s in sentinels.items():
        md.append(f"- `{name}`: {'passed' if s['passed'] else 'FAILED'}")
    md.append("")
    (GENERATED / "shared-operators.md").write_text("\n".join(md), encoding="utf-8")

    for variant in VARIANTS:
        for p in PORTS:
            for g in (ALL, SHARED):
                h = headline[variant][p][g]
                print(f"{variant} | {p} | {g}: gap {h['gap']}, later guard {h['later_guard']} "
                      f"({pct(h['later_guard_share'])})")
    print("all sentinels passed")


if __name__ == "__main__":
    main()
