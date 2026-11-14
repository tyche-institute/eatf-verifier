#!/usr/bin/env python3
"""Write generated/SUMMARY.md and generated/SHA256SUMS.

Reads only the four JSON summaries that the analysis scripts wrote
(subsumption.json, shared-operators.json, label-sensitivity.json,
handler-variant.json). It computes nothing new about the subjects: every
number in SUMMARY.md is copied from one of those files, or is a ratio or a
sum of numbers copied from them. Run it after the four analysis scripts:

    python3 -I summarise.py

It stops when a JSON summary records a failed sentinel.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE / "generated"

SUBJECTS = ("python", "typescript", "pyjwt")
ORACLES = ("O_V", "O_V^fc", "O_C", "O_T", "O_S")


def load(name: str):
    with open(GEN / name, encoding="utf-8") as handle:
        return json.load(handle)


def pct(part: int, whole: int) -> str:
    if whole == 0:
        return "n/a"
    return f"{100.0 * part / whole:.1f}%"


def failed(value) -> bool:
    """True when a recorded sentinel value does not read as passed."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, str):
        if value in ("pass", "passed"):
            return False
        left, sep, right = value.partition(" = ")
        return not (sep and left == right)
    if isinstance(value, dict):
        if "result" in value and isinstance(value["result"], str):
            return failed(value["result"])
        if "passed" in value:
            return failed(value["passed"])
        return any(failed(v) for v in value.values())
    if isinstance(value, list):
        return any(failed(v) for v in value)
    return False


def sentinel_count(value) -> int:
    if isinstance(value, dict):
        if "result" in value or "passed" in value:
            return 1
        return sum(sentinel_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(sentinel_count(v) for v in value)
    return 1


def section_a(a: dict) -> list[str]:
    out = ["## A. Subsuming mutants", ""]
    out.append(
        "A killed mutant is minimal under an oracle when no killed mutant has a "
        "kill set strictly inside its own. The gap is the set of mutants killed "
        "under O_C and not under O_V."
    )
    out += [
        "",
        "| Subject | Gap | Kills O_C | Gap / kills | Minimal under O_C | Minimal gap "
        "| Minimal gap / minimal | Distinct minimal kill sets | With a gap mutant |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in SUBJECTS:
        g = a["subjects"][s]["gap"]
        out.append(
            f"| {s} | {g['gap']} | {g['killed_O_C']} | {pct(g['gap'], g['killed_O_C'])} "
            f"| {g['minimal_O_C']} | {g['minimal_gap']} "
            f"| {pct(g['minimal_gap'], g['minimal_O_C'])} "
            f"| {g['distinct_minimal_kill_sets_O_C']} "
            f"| {g['distinct_minimal_kill_sets_with_gap']} |"
        )
    out += [
        "",
        "Which check decides, over all gap mutants and over the minimal ones:",
        "",
        "| Subject | Set | Mutants | Earlier | Later | Same | No defined code | Mixed |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in SUBJECTS:
        d = a["subjects"][s]["directions"]
        rows = [("all gap", "all_gap"), ("minimal gap", "minimal_gap")]
        if "all_gap_without_code_literal" in d:
            rows += [
                ("all gap, no code literal", "all_gap_without_code_literal"),
                ("minimal gap, no code literal", "minimal_gap_without_code_literal"),
            ]
        for label, key in rows:
            v = d[key]
            get = lambda *names: sum(v.get(n, 0) for n in names)  # noqa: E731
            out.append(
                f"| {s} | {label} | {sum(v.values())} "
                f"| {get('earlier guard', 'earlier check')} "
                f"| {get('later guard', 'later check')} "
                f"| {get('same guard', 'same check')} "
                f"| {get('no defined code')} | {get('mixed')} |"
            )
    out += ["", "Kill sets per subject and oracle:", "",
            "| Subject | Oracle | Killed | Distinct kill sets | Minimal | Distinct minimal kill sets |",
            "|---|---|---|---|---|---|"]
    for s in SUBJECTS:
        for o in ORACLES:
            v = a["subjects"][s]["oracles"].get(o)
            if v is None:
                continue
            out.append(
                f"| {s} | {o} | {v['killed']} | {v['distinct_kill_sets']} "
                f"| {v['minimal']} | {v['distinct_minimal_kill_sets']} |"
            )
    out += ["", "Spread:", ""]
    for s in SUBJECTS:
        sp = a["subjects"][s]["spread"]
        out.append(
            f"- {s}: {sp['units_with_gap']} {sp['unit']} hold a gap mutant, "
            f"{sp['units_with_minimal_gap']} a minimal gap mutant."
        )
    out += ["", "Details: `subsumption.md`, `subsumption.csv`, `subsumption.json`.", ""]
    return out


def section_b(b: dict) -> list[str]:
    out = ["## B. Operator classes that both tools have", ""]
    out.append(
        "The Python port was mutated by mutmut 3.8.1, the TypeScript port by "
        "StrykerJS 9.6.1. Shared classes are those of the table fixed in "
        "PROTOCOL.md; the last row of each port holds the operators outside it."
    )
    for variant in ("all mutants", "without code-literal mutants"):
        out += [
            "",
            f"{variant[0].upper()}{variant[1:]}:",
            "",
            "| Port | Group | Mutants | Kills O_V | Kills O_C | Gap | Later guard | Later-guard share |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for port in ("python", "typescript"):
            for group in ("all operators", "shared classes", "outside the table"):
                rows = [
                    r for r in b["rows"]
                    if r["variant"] == variant and r["port"] == port and r["group"] == group
                ]
                if len(rows) != 1:
                    sys.exit(f"shared-operators.json: {len(rows)} rows for {variant}/{port}/{group}")
                r = rows[0]
                out.append(
                    f"| {port} | {group} | {r['mutants']} | {r['killed_O_V']} "
                    f"| {r['killed_O_C']} | {r['gap']} | {r['gap_later_guard']} "
                    f"| {pct(r['gap_later_guard'], r['gap'])} |"
                )
    out += ["", "Details: `shared-operators.md`, `shared-operators.csv`, `shared-operators.json`.", ""]
    return out


def section_c(c: dict) -> list[str]:
    out = ["## C. Labels that rest on a test's name", ""]
    out.append(
        "A block left out of a label set is a block without a target. The first "
        "row is the second study as deposited."
    )
    out += [
        "",
        "| Label set | Labelled blocks | Blocks left out | Cases with target "
        "| P1: O_T holds | Reached deletions undetected under O_T | kills(O_T) "
        "| kills(O_C) | O_T and not O_C | O_C and not O_T | P5 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in c["label_sets"]:
        out.append(
            f"| {s['label_set']} | {s['labelled_blocks']} | {len(s['blocks_left_out'])} "
            f"| {s['cases_with_target']} "
            f"| {s['P1_O_T_holds']} of {s['cases_with_target']} "
            f"| {len(s['deletions_undetected_O_T'])} of {s['reached_deletions']} "
            f"| {s['kills_O_T']} | {s['kills_O_C']} "
            f"| {len(s['O_T_not_O_C'])} | {len(s['O_C_not_O_T'])} "
            f"| {s['P5_cases'] - len(s['P5_failing'])} of {s['P5_cases']} |"
        )
    out += ["", "Details: `label-sensitivity.md`, `label-sensitivity.csv`, `label-sensitivity.json`.", ""]
    return out


def section_d(d: dict) -> list[str]:
    out = ["## D. A second way to delete a check that sits in a handler", ""]
    hc = d["handler_checks"]
    fc = d["fail_closed_only_deletions"]
    out.append(
        f"Of the {d['reached_checks']} reached checks, {hc['count']} have a raise "
        f"statement inside an `except` handler. Of the {fc['count']} deletions that "
        f"O_V detects and O_V^fc does not, {fc['of_which_handler_checks']} are handler "
        f"checks. Variant R replaces a raise statement in a handler by a bare `raise`. "
        f"{d['runs']['recorder_runs']} recorder runs."
    )
    flips = 0
    pairs = 0
    classes = {"original": {}, "R": {}}
    changed = {"original": 0, "R": 0}
    for check in hc["checks"]:
        entry = d["checks"][check]
        for o in ORACLES:
            pairs += 1
            if entry["original"][o] != entry["R"][o]:
                flips += 1
        for variant in ("original", "R"):
            changed[variant] += entry[variant]["cases_changed"]
            for name, n in entry[variant]["changed_case_classes"].items():
                classes[variant][name] = classes[variant].get(name, 0) + n
    out += [
        "",
        f"Detection verdicts that differ between the two variants: {flips} of "
        f"{pairs} (handler checks x oracles).",
        "",
        "| Oracle | Undetected among the reached checks, original | With the handler checks by variant R |",
        "|---|---|---|",
    ]
    for o in ORACLES:
        v = d["reached_checks_together"][o]
        out.append(f"| {o} | {v['undetected_original']} | {v['undetected_with_R']} |")
    out += ["", "What the changed cases raise, summed over the handler checks:", ""]
    for variant, title in (("original", "original (`pass`)"), ("R", "variant R (bare `raise`)")):
        parts = ", ".join(
            f"{name} {n}" for name, n in sorted(classes[variant].items(), key=lambda kv: (-kv[1], kv[0]))
        )
        out.append(f"- {title}: {changed[variant]} changed cases: {parts}.")
    out += ["", "Details: `handler-variant.md`, `handler-variant.csv`, `handler-variant-cases.csv`, `handler-variant.json`.", ""]
    return out


def main() -> int:
    a = load("subsumption.json")
    b = load("shared-operators.json")
    c = load("label-sensitivity.json")
    d = load("handler-variant.json")

    counts = {}
    for name, doc in (("A", a), ("B", b), ("C", c), ("D", d)):
        if failed(doc["sentinels"]):
            sys.exit(f"analysis {name}: a sentinel is recorded as failed; no summary written")
        counts[name] = sentinel_count(doc["sentinels"])

    lines = [
        "# Robustness of the mutation-adequacy results: summary",
        "",
        "Written by `summarise.py` from the four JSON summaries in this folder; "
        "it adds no number of its own. All four analyses are **exploratory and "
        "post hoc**: they were defined after the results of both studies were "
        "known and carry no prediction (`../PROTOCOL.md`, with its dated "
        "deviations).",
        "",
    ]
    lines += section_a(a) + section_b(b) + section_c(c) + section_d(d)
    lines += [
        "## Sentinels",
        "",
        "Recorded as passed in the JSON summaries: "
        + ", ".join(f"{name} {n}" for name, n in counts.items())
        + ".",
        "",
    ]
    (GEN / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")

    sums = []
    for path in sorted(GEN.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (GEN / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(f"SUMMARY.md written; SHA256SUMS lists {len(sums)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
