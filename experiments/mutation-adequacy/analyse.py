#!/usr/bin/env python3
"""Score the mutation-adequacy run under the oracles fixed in PROTOCOL.md.

Reads work/ (written by run_experiment.py) and writes the tracked results to
generated/: one row per tool mutant, the guard deletions, per-region,
per-case and per-operator tables, the predictions with their verdicts, the
sentinels, and SHA256SUMS. No definition from the protocol is changed here.
A refuted prediction is printed as refuted.

    experiments/mutation-adequacy/work/venv/bin/python experiments/mutation-adequacy/analyse.py

Reading of the kill rule, as implemented (PROTOCOL.md, "Oracles"):

- A mutant that raises on any case is killed under O_V, O_C and O_T. The
  raising case is credited with the kill only when it is in S_O. Under O_V^fc
  the exception is read as a rejection instead, so it kills only through a
  case in S_O whose expected verdict is acceptance.
- Timeouts are taken from the tool and kill under every oracle; they are
  credited to no case. So are load failures.
- A result the harness recorded as `MalformedResult(...)` is an exception.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
WORK = HERE / "work"
OUT = WORK / "outcomes"
GENERATED = HERE / "generated"
PORTS = ("python", "typescript")
ORACLES = ("O_V", "O_V_fc", "O_C", "O_T")
NAIVE = ("naive-remove-receipt-signature", "naive-empty-timestamp")
REFINED = ("refined-remove-receipt-signature", "refined-empty-timestamp")
PY_SUBJECT = ["eatf_verifier/verifier.py", "eatf_verifier/overt.py", "eatf_verifier/tsa.py"]
SOURCES = ["PROTOCOL.md", "guard-regions.json", "cases.py", "harness_py.py", "harness-ts.mjs",
           "deletions.py", "delete-ts.mjs", "run_experiment.py", "analyse.py", "mutmut.toml",
           "stryker/stryker.config.json", "stryker/build-sandbox.sh", "stryker/package.json",
           "stryker/package-lock.json"]

MUTMUT_STATUS = {1: "killed", 3: "killed", 0: "survived", 5: "no tests", 33: "no tests",
                 36: "timeout", 24: "timeout", -24: "timeout", 152: "timeout", 255: "timeout",
                 -11: "segfault", -9: "segfault"}
TOOL_CLASS = {"killed": "killed", "timeout": "killed", "segfault": "killed",
              "survived": "survived", "no tests": "survived",
              "Killed": "killed", "Timeout": "killed", "RuntimeError": "killed",
              "Survived": "survived", "NoCoverage": "survived"}
TIMEOUTS = {"timeout", "segfault", "Timeout"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


REGIONS = load_json(HERE / "guard-regions.json")
GUARDS = list(REGIONS["guards"])
ALL_CODES = {code for meta in REGIONS["guards"].values() for code in meta["codes"]}
CASES = load_json(WORK / "cases.json")["cases"]
CASE_IDS = [c["id"] for c in CASES]
BY_ID = {c["id"]: c for c in CASES}
INVOCATION = {c["id"]: (c["package_sha256"], c["signer_pin"]) for c in CASES}
TWINS = {cid: {d for d in CASE_IDS if INVOCATION[d] == INVOCATION[cid]} for cid in CASE_IDS}


def region_of(port: str, rel: str, line: int | None) -> str:
    if line is None:
        return "unplaced"
    for start, end, name in REGIONS["files"][port][rel]["regions"]:
        if start <= line <= end:
            return name
    raise SystemExit(f"line {line} of {rel} is in no region")


def outcomes_of(path: Path) -> dict | None:
    if not path.exists():
        return None
    data = load_json(path)
    if data.get("load_error"):
        return {"load_error": data["load_error"]}
    seen = {o["id"]: o for o in data["outcomes"]}
    if list(seen) != CASE_IDS:
        raise SystemExit(f"{path}: the record does not cover the 25 cases in order")
    return {"outcomes": seen, "seconds": data.get("seconds")}


# -- oracles ---------------------------------------------------------------------

def holds(oracle: str, case: dict, seen: dict) -> bool:
    if seen["exception"] is not None:
        return oracle == "O_V_fc" and case["expected_valid"] is False
    if oracle in ("O_V", "O_V_fc"):
        return seen["valid"] == case["expected_valid"]
    if oracle == "O_C":
        return (seen["valid"], seen["code"]) == (case["expected_valid"], case["expected_code"])
    if oracle == "O_T":
        return seen["code"] == case["target_code"]
    raise ValueError(oracle)


def state(seen: dict) -> str:
    if seen["exception"] is not None:
        return f"!{seen['exception']}"
    return f"{'T' if seen['valid'] else 'F'}|{seen['code'] or '-'}"


def applicable(baseline: dict) -> dict[str, set[str]]:
    return {o: {cid for cid in CASE_IDS if holds(o, BY_ID[cid], baseline[cid])} for o in ORACLES}


def score(record: dict | None, tool_status: str, s: dict[str, set[str]],
          suite: list[str] = CASE_IDS) -> dict:
    """Kills under each oracle, and the cases credited with each kill."""
    tool_class = TOOL_CLASS.get(tool_status, "excluded")
    every = {o: True for o in ORACLES}
    nobody = {o: [] for o in ORACLES}
    if tool_class == "excluded":
        return {"killed": {o: None for o in ORACLES}, "by": nobody, "basis": "excluded"}
    if tool_status in TIMEOUTS:
        return {"killed": every, "by": nobody, "basis": "tool timeout"}
    if record is None:
        if tool_class == "killed":
            return {"killed": every, "by": nobody, "basis": "tool, no record"}
        return {"killed": {o: False for o in ORACLES}, "by": nobody, "basis": "not executed"}
    if "load_error" in record:
        return {"killed": every, "by": nobody, "basis": "load error"}
    seen = record["outcomes"]
    raised = any(seen[cid]["exception"] is not None for cid in suite)
    killed, by = {}, {}
    for o in ORACLES:
        by[o] = [cid for cid in suite if cid in s[o] and not holds(o, BY_ID[cid], seen[cid])]
        killed[o] = bool(by[o]) or (raised and o != "O_V_fc")
    return {"killed": killed, "by": by, "basis": "record"}


# -- mutant classification ---------------------------------------------------------

def code_literal_change(original: str, mutated: str) -> bool:
    """True when the one changed line differs from the original only inside a
    string literal that spells a failure code."""
    for m in re.finditer(r"""(["'])([A-Z][A-Z0-9_]+)\1""", original):
        if m.group(2) not in ALL_CODES:
            continue
        i, j = m.span()
        tail = len(original) - j
        if (len(mutated) >= i + tail and original[:i] == mutated[:i]
                and original[j:] == mutated[len(mutated) - tail:]):
            return True
    return False


def mutmut_operators(project: Path) -> dict[str, str]:
    """The mutmut operator behind each mutant.

    mutmut 3.8.1 does not store operator names. This re-enumerates its
    mutations with its own visitor and operator table, each operator wrapped so
    that it tags what it yields, and names the mutants as mutmut does. Each
    re-created mutant function is compared with the one mutmut wrote, so a
    label is returned only when the two are the same code."""
    import libcst as cst
    import mutmut.mutation.file_mutation as fm
    from mutmut.mutation.diff_apply import read_functions_from_index, read_mutant_function
    from mutmut.mutation.trampoline_templates import mangle_function_name
    from mutmut.utils.format_utils import get_mutant_name

    tags: dict[int, str] = {}

    def tagged(name, fn):
        def wrapper(node):
            for out in fn(node):
                tags[id(out)] = name
                yield out
        return wrapper

    saved = fm.mutation_operators
    fm.mutation_operators = [(t, tagged(fn.__name__.removeprefix("operator_"), fn)) for t, fn in saved]
    previous = Path.cwd()
    os.chdir(project)
    labels: dict[str, str] = {}
    render = cst.Module(body=[]).code_for_node
    try:
        for rel in PY_SUBJECT:
            code = (project / rel).read_text(encoding="utf-8")
            module, mutations, _, _ = fm.create_mutations(rel, code, None, None)
            grouped = fm.group_by_top_level_node(mutations)
            owners = []
            for statement in module.body:
                if isinstance(statement, cst.FunctionDef):
                    owners.append((statement, None))
                elif isinstance(statement, cst.ClassDef) and isinstance(statement.body, cst.IndentedBlock):
                    owners += [(m, statement.name.value) for m in statement.body.body
                               if isinstance(m, cst.FunctionDef)]
            mutants_module = None
            for fn, class_name in owners:
                mangled = mangle_function_name(name=fn.name.value, class_name=class_name) + "__mutmut"
                for i, mutation in enumerate(grouped.get(fn, ()), start=1):
                    key = get_mutant_name(Path(rel), f"{mangled}_{i}")
                    mine = fm.deep_replace(fn, mutation.original_node, mutation.mutated_node)
                    found = read_functions_from_index(key, rel)
                    if found is not None:
                        theirs = found[1]
                    else:
                        if mutants_module is None:
                            mutants_module = cst.parse_module((project / "mutants" / rel).read_text())
                        theirs = read_mutant_function(mutants_module, key)
                    # the index returns the mutant under its original name; compare bodies
                    same = dict(name=fn.name, leading_lines=[])
                    if render(mine.with_changes(**same)) != render(theirs.with_changes(**same)):
                        raise SystemExit(f"re-created mutant {key} differs from mutmut's")
                    labels[key] = tags[id(mutation.mutated_node)]
    finally:
        fm.mutation_operators = saved
        os.chdir(previous)
    return labels


# -- tool mutants ------------------------------------------------------------------

def python_mutants(s: dict[str, set[str]]) -> list[dict]:
    operators = mutmut_operators(WORK / "py")
    rows = []
    for m in load_json(WORK / "python-mutants.json"):
        status = MUTMUT_STATUS.get(m["exit_code"], f"exit {m['exit_code']}")
        record = outcomes_of(OUT / "python-mutmut" / f"{m['id']}.json")
        literal = (len(m["original"]) == 1 and len(m["mutated"]) == 1
                   and code_literal_change(m["original"][0], m["mutated"][0]))
        rows.append({
            "port": "python", "tool": "mutmut 3.8.1", "id": m["id"], "file": m["file"],
            "line": m["line"], "region": region_of("python", m["file"], m["line"]),
            "operator": operators[m["id"]], "code_literal": literal, "tool_status": status,
            "tool_class": TOOL_CLASS.get(status, "excluded"),
            "original": " ".join(x.strip() for x in m["original"]),
            "mutated": " ".join(x.strip() for x in m["mutated"]),
            "record": record, **score(record, status, s),
        })
    if len(operators) != len(rows):
        raise SystemExit(f"{len(operators)} operator labels for {len(rows)} mutmut mutants")
    return rows


def typescript_mutants(s: dict[str, set[str]]) -> list[dict]:
    report = load_json(WORK / "stryker" / "mutation.json")
    rows = []
    for rel, entry in sorted(report["files"].items()):
        lines = (REPO_ROOT / rel).read_text(encoding="utf-8").split("\n")
        for m in entry["mutants"]:
            # Stryker positions are 1-based; the end column is exclusive.
            start, end = m["location"]["start"], m["location"]["end"]
            if start["line"] == end["line"]:
                original = lines[start["line"] - 1][start["column"] - 1:end["column"] - 1]
            else:
                original = "\n".join([lines[start["line"] - 1][start["column"] - 1:],
                                      *lines[start["line"]:end["line"] - 1],
                                      lines[end["line"] - 1][:end["column"] - 1]])
            status = m["status"]
            record = outcomes_of(OUT / "typescript-stryker" / f"{m['id']}.json")
            literal = (m["mutatorName"] == "StringLiteral" and len(original) > 2
                       and original[0] == original[-1] and original[0] in "\"'"
                       and original[1:-1] in ALL_CODES)
            rows.append({
                "port": "typescript", "tool": "StrykerJS 9.6.1", "id": m["id"], "file": rel,
                "line": start["line"], "region": region_of("typescript", rel, start["line"]),
                "operator": m["mutatorName"], "code_literal": literal, "tool_status": status,
                "tool_class": TOOL_CLASS.get(status, "excluded"),
                "original": " ".join(original.split()),
                "mutated": " ".join(m.get("replacement", "").split()),
                "record": record, **score(record, status, s),
            })
    return rows


# -- helpers -------------------------------------------------------------------------

def kills(rows: list[dict], oracle: str) -> set[str]:
    return {r["id"] for r in rows if r["killed"][oracle]}


def scored(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["tool_class"] != "excluded"]


def share(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def write_csv(name: str, rows: list[dict]) -> None:
    with (GENERATED / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def flag(value) -> str:
    return "" if value is None else str(value).lower()


# -- analysis --------------------------------------------------------------------------

def main() -> int:
    GENERATED.mkdir(exist_ok=True)
    baseline = {p: outcomes_of(OUT / p / "baseline.json")["outcomes"] for p in PORTS}
    s = {p: applicable(baseline[p]) for p in PORTS}
    rejected_t = {p: [c for c in CASE_IDS if BY_ID[c]["expected_valid"] is False and c in s[p]["O_T"]]
                  for p in PORTS}
    verdicts: dict[str, dict] = {}
    sentinels: dict[str, object] = {}

    # Sentinel 1 is checked by run_experiment.py, which compares both baselines
    # with the deposited CSV files and stops on a difference.
    sentinels["1_baseline_matches_deposit"] = "checked by run_experiment.py baseline"

    # P1 ---------------------------------------------------------------------------------
    per_port = {p: {"O_V": len(s[p]["O_V"]), "O_C": len(s[p]["O_C"]), "O_T": len(s[p]["O_T"]),
                    "O_T_fails_on": sorted(set(CASE_IDS) - s[p]["O_T"])} for p in PORTS}
    parity = sum(state(baseline["python"][c]) == state(baseline["typescript"][c]) for c in CASE_IDS)
    verdicts["P1"] = {
        "held": all(x["O_V"] == 25 and x["O_C"] == 25 and x["O_T"] == 23
                    and x["O_T_fails_on"] == sorted(NAIVE) for x in per_port.values()) and parity == 25,
        "per_port": per_port, "cross_port_agreement": f"{parity}/25",
    }

    # guard deletions: P2, P3 ---------------------------------------------------------------
    replaced = load_json(WORK / "deletion" / "replaced.json")
    deletion_rows, deletion_case_rows = [], []
    control_ok, detected, changed_by, raised_by = {}, {p: {} for p in PORTS}, {p: {} for p in PORTS}, {}
    for p in PORTS:
        control = outcomes_of(OUT / f"{p}-deletion" / "control.json")["outcomes"]
        control_ok[p] = all(state(control[c]) == state(baseline[p][c]) for c in CASE_IDS)
        raised_by[p] = {}
        for g in GUARDS:
            seen = outcomes_of(OUT / f"{p}-deletion" / f"{g}.json")["outcomes"]
            result = score({"outcomes": seen}, "survived", s[p])
            detected[p][g] = result["killed"]
            changed = [c for c in CASE_IDS if state(seen[c]) != state(baseline[p][c])]
            changed_by[p][g] = changed
            raised_by[p][g] = [c for c in CASE_IDS if seen[c]["exception"] is not None]
            deletion_rows.append({
                "port": p, "guard": g, "statements_replaced": len(replaced[p][g]),
                "replaced_lines": " ".join(str(r["line"]) for r in replaced[p][g]),
                **{f"detected_{o}": flag(result["killed"][o]) for o in ORACLES},
                "cases_changed": len(changed), "changed": " ".join(changed),
                "raised": " ".join(raised_by[p][g]),
            })
            for c in CASE_IDS:
                deletion_case_rows.append({"port": p, "guard": g, "case": c,
                                           "baseline": state(baseline[p][c]), "deleted": state(seen[c]),
                                           "changed": flag(c in changed)})
    sentinels["deletion_control_equals_baseline"] = control_ok

    expect_undetected_v = {"3-metadata", "4-canonical-form", "5-digest", "8a-overt-crosscheck"}
    p2 = {}
    for p in PORTS:
        undetected = {o: sorted(g for g in GUARDS if not detected[p][g][o]) for o in ORACLES}
        only_exception = (bool(changed_by[p]["2-required-entries"])
                          and set(changed_by[p]["2-required-entries"]) <= set(raised_by[p]["2-required-entries"]))
        p2[p] = {**{f"undetected_{o}": undetected[o] for o in ORACLES},
                 "2_changes_only_through_exceptions": only_exception,
                 "held": (set(undetected["O_V"]) == expect_undetected_v
                          and set(undetected["O_V_fc"]) == expect_undetected_v | {"2-required-entries"}
                          and not undetected["O_C"] and not undetected["O_T"] and only_exception)}
    verdicts["P2"] = {"held": all(x["held"] for x in p2.values()), "per_port": p2}

    p3 = {}
    for p in PORTS:
        own = {c: c in changed_by[p][BY_ID[c]["target_guard"]] for c in rejected_t[p]}
        naive_own = {c: c in changed_by[p][BY_ID[c]["target_guard"]] for c in NAIVE}
        naive_8a = {c: c in changed_by[p]["8a-overt-crosscheck"] for c in NAIVE}
        p3[p] = {"rejected_cases_on_which_O_T_holds": len(rejected_t[p]),
                 "changed_by_deleting_own_target_guard": sum(own.values()),
                 "not_changed": sorted(c for c, v in own.items() if not v),
                 "naive_changed_by_deleting_own_target_guard": naive_own,
                 "naive_changed_by_deleting_8a": naive_8a,
                 "held": (len(rejected_t[p]) == 21 and all(own.values())
                          and not any(naive_own.values()) and all(naive_8a.values()))}
    verdicts["P3"] = {"held": all(x["held"] for x in p3.values()), "per_port": p3}

    # tool mutants ---------------------------------------------------------------------------
    mutants = {"python": python_mutants(s["python"]), "typescript": typescript_mutants(s["typescript"])}

    disagreements = {}
    for p in PORTS:
        disagreements[p] = {
            "tool_status_differs_from_O_C": [r["id"] for r in mutants[p] if r["basis"] == "record"
                                             and (r["tool_class"] == "killed") != r["killed"]["O_C"]],
            "killed_by_tool_without_record": [r["id"] for r in mutants[p] if r["basis"] == "tool, no record"],
            "survived_without_record": [r["id"] for r in mutants[p] if r["basis"] == "not executed"
                                        and r["tool_status"] not in ("no tests", "NoCoverage")],
        }
    sentinels["2_tool_status_equals_O_C"] = disagreements
    sentinels["3_subsets"] = {p: {"O_V_in_O_C": kills(scored(mutants[p]), "O_V") <= kills(scored(mutants[p]), "O_C"),
                                  "O_T_in_O_C": kills(scored(mutants[p]), "O_T") <= kills(scored(mutants[p]), "O_C")}
                              for p in PORTS}

    # P4 --------------------------------------------------------------------------------------
    p4 = {}
    for p in PORTS:
        rows = scored(mutants[p])
        kc, kv = kills(rows, "O_C"), kills(rows, "O_V")
        nolit = [r for r in rows if not r["code_literal"]]
        kc2, kv2 = kills(nolit, "O_C"), kills(nolit, "O_V")
        p4[p] = {"killed_O_C": len(kc), "killed_O_V": len(kv), "gap": len(kc - kv),
                 "gap_share": share(len(kc - kv), len(kc)),
                 "code_literal_mutants": len(rows) - len(nolit),
                 "without_code_literal_mutants": {"killed_O_C": len(kc2), "killed_O_V": len(kv2),
                                                  "gap": len(kc2 - kv2),
                                                  "gap_share": share(len(kc2 - kv2), len(kc2))},
                 "held": kv < kc and len(kc - kv) >= 0.10 * len(kc)}
    verdicts["P4"] = {"held": all(x["held"] for x in p4.values()), "per_port": p4}

    # P5 --------------------------------------------------------------------------------------
    p5 = {}
    for p in PORTS:
        rows = scored(mutants[p])
        a = {c: sorted(r["id"] for r in rows if r["region"] == BY_ID[c]["target_guard"]
                       and (c in r["by"]["O_V"] or c in r["by"]["O_C"])) for c in NAIVE}
        b = {c: sum(1 for r in rows if r["region"] == BY_ID[c]["target_guard"] and c in r["by"]["O_C"])
             for c in rejected_t[p]}
        p5[p] = {"a_naive_kills_in_own_target_region": a,
                 "b_O_C_kills_in_own_target_region": b,
                 "b_cases_without_any": sorted(c for c, n in b.items() if n == 0),
                 "held": not any(a.values()) and all(n >= 1 for n in b.values())}
    verdicts["P5"] = {"held": all(x["held"] for x in p5.values()), "per_port": p5}

    # tables -----------------------------------------------------------------------------------
    totals, region_rows, case_rows, operator_rows, suites = {}, [], [], [], {}
    gap_rows, gap_directions = [], {}
    guard_of = {code: g for g in GUARDS for code in REGIONS["guards"][g]["codes"]}
    for p in PORTS:
        rows, live = mutants[p], scored(mutants[p])
        totals[p] = {
            "generated": len(rows), "excluded": len(rows) - len(live), "scored": len(live),
            "tool_statuses": dict(sorted(Counter(r["tool_status"] for r in rows).items())),
            "bases": dict(sorted(Counter(r["basis"] for r in rows).items())),
            "code_literal_mutants": sum(r["code_literal"] for r in live),
            "malformed_result_records": sum(1 for r in live if r["record"] and "outcomes" in r["record"]
                                            and any((o["exception"] or "").startswith("MalformedResult")
                                                    for o in r["record"]["outcomes"].values())),
            "O_T_kills_only_through_an_uncredited_exception": sum(
                1 for r in live if r["killed"]["O_T"] and not r["by"]["O_T"] and r["basis"] == "record"),
            **{f"killed_{o}": len(kills(live, o)) for o in ORACLES},
            **{f"survived_{o}": len(live) - len(kills(live, o)) for o in ORACLES},
            **{f"score_{o}": share(len(kills(live, o)), len(live)) for o in ORACLES},
        }
        by_region = defaultdict(list)
        for r in live:
            by_region[r["region"]].append(r)
        for region in [*GUARDS, "13-tsa-pin", "shared"]:
            rr = by_region.get(region, [])
            region_rows.append({"port": p, "region": region, "mutants": len(rr),
                                **{f"killed_{o}": len(kills(rr, o)) for o in ORACLES},
                                **{f"score_{o}": pct(share(len(kills(rr, o)), len(rr))) for o in ORACLES}})
        by_op = defaultdict(list)
        for r in live:
            by_op[r["operator"]].append(r)
        for op, rr in sorted(by_op.items()):
            operator_rows.append({"port": p, "operator": op, "mutants": len(rr),
                                  "code_literal": sum(r["code_literal"] for r in rr),
                                  **{f"killed_{o}": len(kills(rr, o)) for o in ORACLES}})
        for c in CASE_IDS:
            g = BY_ID[c]["target_guard"]
            row = {"port": p, "case": c, "source": BY_ID[c]["source"], "target_guard": g or "",
                   "same_invocation_as": " ".join(sorted(TWINS[c] - {c}))}
            for o in ORACLES:
                credited = [r for r in live if c in r["by"][o]]
                row[f"kills_{o}"] = len(credited)
                row[f"unique_{o}"] = sum(1 for r in credited if set(r["by"][o]) == {c})
                row[f"unique_distinct_{o}"] = sum(1 for r in credited if set(r["by"][o]) <= TWINS[c])
                row[f"in_target_region_{o}"] = sum(1 for r in credited if g and r["region"] == g)
            case_rows.append(row)

        # exploratory, beyond the protocol's list: suite-level kills without the
        # naive or without the refined path-shadowing cases (RQ-M3)
        suites[p] = {}
        for name, suite in (("all 25", CASE_IDS),
                            ("without the 2 naive", [c for c in CASE_IDS if c not in NAIVE]),
                            ("without the 2 refined", [c for c in CASE_IDS if c not in REFINED])):
            again = [score(r["record"], r["tool_status"], s[p], suite) for r in live]
            suites[p][name] = {o: sum(1 for x in again if x["killed"][o]) for o in ORACLES}

        # exploratory, added after the results were seen (PROTOCOL.md, deviation 7):
        # for every mutant killed under O_C but not under O_V, the guard that now
        # decides each case whose code changed, against the guard that decided it
        # on the unmutated program
        for r in live:
            if not (r["killed"]["O_C"] and not r["killed"]["O_V"]):
                continue
            if not (r["record"] and "outcomes" in r["record"]):
                raise SystemExit(f"{r['id']}: a verdict-only gap mutant without a record")
            changed = []
            for c in CASE_IDS:
                before, after = baseline[p][c], r["record"]["outcomes"][c]
                if state(before) == state(after):
                    continue
                if after["exception"] is not None or after["valid"] != before["valid"]:
                    raise SystemExit(f"{r['id']}: a verdict-only gap mutant changed a verdict or raised")
                was, now = guard_of[before["code"]], guard_of.get(after["code"])
                changed.append((c, before["code"], after["code"],
                                "no defined code" if now is None
                                else "later guard" if GUARDS.index(now) > GUARDS.index(was)
                                else "earlier guard" if GUARDS.index(now) < GUARDS.index(was)
                                else "same guard"))
            directions = sorted({d for *_, d in changed})
            gap_rows.append({"port": p, "id": r["id"], "region": r["region"], "operator": r["operator"],
                             "code_literal": flag(r["code_literal"]),
                             "direction": directions[0] if len(directions) == 1 else "mixed",
                             "cases": " ".join(c for c, *_ in changed),
                             "codes": " ".join(f"{a}>{b or '-'}" for _, a, b, _ in changed)})
        mine = [g for g in gap_rows if g["port"] == p]
        plain = [g for g in mine if g["code_literal"] == "false"]
        gap_directions[p] = {
            "gap_mutants": len(mine),
            "all": dict(sorted(Counter(g["direction"] for g in mine).items())),
            "without_code_literal_mutants": dict(sorted(Counter(g["direction"] for g in plain).items())),
            "operators_without_code_literal_mutants": {
                d: dict(sorted(Counter(g["operator"] for g in plain if g["direction"] == d).items()))
                for d in sorted({g["direction"] for g in plain})},
        }

    codes = {}
    for p, files in (("python", [f"lib-python/{f}" for f in PY_SUBJECT]),
                     ("typescript", ["lib/src/verifier.ts", "lib/src/overt.ts", "lib/src/tsa.ts"])):
        text = "".join((REPO_ROOT / f).read_text(encoding="utf-8") for f in files)
        defined = sorted(c for c in ALL_CODES if f'"{c}"' in text)
        reached = sorted({baseline[p][c]["code"] for c in CASE_IDS} - {None})
        codes[p] = {"defined": defined, "reached": reached,
                    "never_reached": sorted(set(defined) - set(reached))}

    # outputs ------------------------------------------------------------------------------------
    mutant_rows, outcome_lines = [], [json.dumps({"case_order": CASE_IDS})]
    for p in PORTS:
        outcome_lines.append(json.dumps({"port": p, "id": "baseline",
                                         "states": [state(baseline[p][c]) for c in CASE_IDS]},
                                        separators=(",", ":")))
        for r in mutants[p]:
            mutant_rows.append({
                "port": p, "tool": r["tool"], "id": r["id"], "file": r["file"], "line": r["line"],
                "region": r["region"], "operator": r["operator"], "code_literal": flag(r["code_literal"]),
                "tool_status": r["tool_status"], "basis": r["basis"],
                **{f"killed_{o}": flag(r["killed"][o]) for o in ORACLES},
                **{f"by_{o}": " ".join(r["by"][o]) for o in ("O_V", "O_C", "O_T")},
                "original": r["original"], "mutated": r["mutated"],
            })
            if r["record"] and "outcomes" in r["record"]:
                outcome_lines.append(json.dumps(
                    {"port": p, "id": r["id"], "states": [state(r["record"]["outcomes"][c]) for c in CASE_IDS]},
                    separators=(",", ":")))
    write_csv("mutants.csv", mutant_rows)
    write_csv("deletions.csv", deletion_rows)
    write_csv("deletion-cases.csv", deletion_case_rows)
    write_csv("regions.csv", region_rows)
    write_csv("cases.csv", case_rows)
    write_csv("operators.csv", operator_rows)
    write_csv("gap-directions.csv", gap_rows)
    (GENERATED / "outcomes.jsonl").write_text("\n".join(outcome_lines) + "\n", encoding="utf-8")

    def run(cmd: list[str]) -> str:
        return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()

    environment = {
        "python": platform.python_version(),
        "node": run(["node", "--version"]),
        "typescript": run(["node", "lib/node_modules/typescript/bin/tsc", "--version"]),
        "mutmut": run([str(WORK / "venv" / "bin" / "python"), "-c",
                       "import importlib.metadata as m; print(m.version('mutmut'))"]),
        "stryker": load_json(HERE / "stryker" / "node_modules" / "@stryker-mutator" / "core"
                             / "package.json")["version"],
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "subject_commit": REGIONS["subject"]["commit"],
        "experiment_sources_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in SOURCES},
    }
    (GENERATED / "environment.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    summary = {
        "schema": "urn:eatf:experiment:mutation-adequacy-results:1",
        "subject_commit": REGIONS["subject"]["commit"],
        "suite": {"named_cases": len(CASES), "distinct_invocations": len(set(INVOCATION.values())),
                  "distinct_packages": len({c["package_sha256"] for c in CASES}),
                  "rejected_named": sum(1 for c in CASES if not c["expected_valid"]),
                  "rejected_distinct": len({INVOCATION[c["id"]] for c in CASES if not c["expected_valid"]})},
        "totals": totals,
        "predictions": verdicts,
        "sentinels": sentinels,
        "exploratory": {"suite_level_kills": suites, "codes": codes, "gap_directions": gap_directions},
    }
    (GENERATED / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    freeze = WORK / "pip-freeze.txt"
    if freeze.exists():
        (GENERATED / "pip-freeze.txt").write_text(freeze.read_text(encoding="utf-8"), encoding="utf-8")
    report = render(summary, deletion_rows, region_rows, case_rows)
    (GENERATED / "SUMMARY.md").write_text(report, encoding="utf-8")
    files = sorted(f for f in GENERATED.iterdir() if f.is_file() and f.name != "SHA256SUMS")
    (GENERATED / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in files), encoding="ascii")
    print(report)

    ok = (all(control_ok.values())
          and all(not any(d.values()) for d in disagreements.values())
          and all(all(x.values()) for x in sentinels["3_subsets"].values()))
    print("sentinels:", "pass" if ok else "FAIL")
    return 0 if ok else 1


def render(summary: dict, deletion_rows: list[dict], region_rows: list[dict], case_rows: list[dict]) -> str:
    t, v, suite = summary["totals"], summary["predictions"], summary["suite"]
    out = ["# Mutation adequacy: results", "",
           f"Subject eatf-verifier v0.5.0 (`{summary['subject_commit'][:10]}`). Suite: "
           f"{suite['named_cases']} named cases, {suite['distinct_invocations']} distinct "
           f"(package, invocation) pairs, {suite['distinct_packages']} distinct packages; "
           f"{suite['rejected_named']} rejected named cases, {suite['rejected_distinct']} distinct.",
           "", "Generated by `analyse.py`; every number below is in `summary.json` or a CSV here.",
           "", "## Predictions", ""]
    for name, verdict in v.items():
        out.append(f"- {name}: {'held' if verdict['held'] else 'REFUTED'}")
    out += ["", "## Tool mutants", "",
            "| Port | Generated | Excluded | Scored | Killed O_V | Killed O_V^fc | Killed O_C | Killed O_T |",
            "|---|---|---|---|---|---|---|---|"]
    for p in PORTS:
        x = t[p]
        out.append(f"| {p} | {x['generated']} | {x['excluded']} | {x['scored']} | "
                   + " | ".join(f"{x[f'killed_{o}']} ({pct(x[f'score_{o}'])})" for o in ORACLES) + " |")
    p4 = v["P4"]["per_port"]
    out += ["", "## Verdict-only gap (P4)", "",
            "| Port | Killed O_C | Killed O_V | Gap | Gap / O_C | Code-literal mutants | Gap without them | Share without them |",
            "|---|---|---|---|---|---|---|---|"]
    for p in PORTS:
        x, y = p4[p], p4[p]["without_code_literal_mutants"]
        out.append(f"| {p} | {x['killed_O_C']} | {x['killed_O_V']} | {x['gap']} | {pct(x['gap_share'])} | "
                   f"{x['code_literal_mutants']} | {y['gap']} | {pct(y['gap_share'])} |")
    out += ["", "## Guard deletions (P2, P3): detected?", "",
            "| Port | Guard | Statements | O_V | O_V^fc | O_C | O_T | Cases changed |",
            "|---|---|---|---|---|---|---|---|"]
    for r in deletion_rows:
        out.append(f"| {r['port']} | {r['guard']} | {r['statements_replaced']} | "
                   + " | ".join("yes" if r[f"detected_{o}"] == "true" else "no" for o in ORACLES)
                   + f" | {r['cases_changed']} |")
    out += ["", "## Regions", "",
            "| Port | Region | Mutants | O_V | O_V^fc | O_C | O_T |", "|---|---|---|---|---|---|---|"]
    for r in region_rows:
        out.append(f"| {r['port']} | {r['region']} | {r['mutants']} | "
                   + " | ".join(f"{r[f'killed_{o}']} ({r[f'score_{o}']})" for o in ORACLES) + " |")
    out += ["", "## Cases (O_C)", "",
            "| Port | Case | Kills | Unique | Unique, twins merged | In own target region |",
            "|---|---|---|---|---|---|"]
    for r in case_rows:
        out.append(f"| {r['port']} | {r['case']} | {r['kills_O_C']} | {r['unique_O_C']} | "
                   f"{r['unique_distinct_O_C']} | {r['in_target_region_O_C']} |")
    out += ["", "## Exploratory: suite-level kills without the naive or refined cases", "",
            "| Port | Suite | O_V | O_V^fc | O_C | O_T |", "|---|---|---|---|---|---|"]
    for p, rows in summary["exploratory"]["suite_level_kills"].items():
        for name, k in rows.items():
            out.append(f"| {p} | {name} | " + " | ".join(str(k[o]) for o in ORACLES) + " |")
    gd = summary["exploratory"]["gap_directions"]
    kinds = sorted({d for x in gd.values() for d in x["all"]})
    out += ["", "## Exploratory: the guard that decides instead, for the verdict-only gap", "",
            "Mutants killed under O_C but not under O_V. For each case whose code changed: a later "
            "guard, an earlier guard or the same guard now decides it, or the code returned is none "
            "of the codes the verifier defines. Rows: all gap mutants, then without code-literal "
            "mutants. One row per mutant is in `gap-directions.csv`.", "",
            "| Port | Mutants | " + " | ".join(kinds) + " |", "|---|---|" + "---|" * len(kinds)]
    for p, x in gd.items():
        for label, key in (("all", "all"), ("without code literals", "without_code_literal_mutants")):
            out.append(f"| {p}, {label} | {sum(x[key].values())} | "
                       + " | ".join(str(x[key].get(d, 0)) for d in kinds) + " |")
    out += ["", "Operators of the gap mutants without code literals, by direction:", ""]
    for p, x in gd.items():
        for d, ops in x["operators_without_code_literal_mutants"].items():
            out.append(f"- {p}, {d}: " + ", ".join(f"{op} {n}" for op, n in ops.items()))
    out += ["", "## Sentinels and prediction details", "", "```json",
            json.dumps({"sentinels": summary["sentinels"],
                        "P1": v["P1"], "P2": v["P2"], "P3": v["P3"], "P5": v["P5"]}, indent=2),
            "```", ""]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
