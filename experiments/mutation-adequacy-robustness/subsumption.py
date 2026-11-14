#!/usr/bin/env python3
"""Analysis A of PROTOCOL.md: subsuming mutants.

    python3 -I experiments/mutation-adequacy-robustness/subsumption.py

Reads only deposited files of the two finished studies and writes
generated/subsumption.csv, generated/subsumption.json and
generated/subsumption.md. Nothing of either subject is run, and no file of
either study is changed.

Kill sets, by each study's own kill rule:

- Verifier (both ports): the cases credited under each oracle are the columns
  by_O_V, by_O_C and by_O_T of ../mutation-adequacy/generated/mutants.csv,
  which that study's analysis wrote from its kill rule. As a consistency
  check, by_O_V and by_O_C are derived again from generated/outcomes.jsonl.
- PyJWT: the credited cases are recomputed from
  ../mutation-adequacy-pyjwt/generated/outcomes.jsonl with the functions
  `holds`, `evaluate` and `moves` of that study's analyse_s2.py, imported
  read-only (no bytecode is written next to it).

A mutant killed without a credited case has the kill set {T}, where T is
one element that is not a case.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY1 = HERE.parent / "mutation-adequacy"
STUDY2 = HERE.parent / "mutation-adequacy-pyjwt"
GENERATED = HERE / "generated"
T = "T"  # the one element of the kill set of a mutant killed without a credited case

PORTS = ("python", "typescript")
SUBJECTS = ("python", "typescript", "pyjwt")
ORACLES_1 = ("O_V", "O_C", "O_T")
ORACLES_2 = ("O_V", "O_V_fc", "O_C", "O_T", "O_S")
NAMES = {"O_V": "O_V", "O_V_fc": "O_V^fc", "O_C": "O_C", "O_T": "O_T", "O_S": "O_S"}
PYJWT_DIRECTION = {"later": "later check", "earlier": "earlier check", "no check": "no check",
                   "no exception": "no exception", "crashed": "crashed", "withheld": "withheld",
                   "missing": "missing", "unordered": "unordered"}


class SentinelError(SystemExit):
    pass


def fail(message: str) -> None:
    raise SentinelError(f"SENTINEL FAILED: {message}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def share(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


# -- subsumption ------------------------------------------------------------------

def subsumption(kill_sets: dict[str, frozenset]) -> dict:
    """kill_sets: mutant -> nonempty kill set, for the killed mutants only."""
    distinct = set(kill_sets.values())
    minimal_sets = {k for k in distinct if not any(other < k for other in distinct)}
    minimal = sorted(m for m, k in kill_sets.items() if k in minimal_sets)
    return {"killed": len(kill_sets), "kill_sets": len(distinct), "minimal": minimal,
            "minimal_sets": minimal_sets,
            "uncredited": sum(1 for k in kill_sets.values() if k == frozenset({T}))}


# -- verifier ------------------------------------------------------------------------

def verifier() -> dict:
    rows = read_csv(STUDY1 / "generated" / "mutants.csv")
    summary = load_json(STUDY1 / "generated" / "summary.json")
    gap_rows = read_csv(STUDY1 / "generated" / "gap-directions.csv")
    lines = (STUDY1 / "generated" / "outcomes.jsonl").read_text(encoding="utf-8").splitlines()
    order = json.loads(lines[0])["case_order"]
    states = {}
    for line in lines[1:]:
        x = json.loads(line)
        states[(x["port"], x["id"])] = x["states"]
    sentinels, out = {}, {}
    for p in PORTS:
        # the mutants the study's analysis scores: those with a kill decision
        scored = [r for r in rows if r["port"] == p and r["killed_O_C"] in ("true", "false")]
        if len(scored) != summary["totals"][p]["scored"]:
            fail(f"{p}: {len(scored)} scored mutants, the study reports {summary['totals'][p]['scored']}")
        kill_sets = {o: {} for o in ORACLES_1}
        for r in scored:
            for o in ORACLES_1:
                credited = r[f"by_{o}"].split()
                killed = r[f"killed_{o}"] == "true"
                if credited and not killed:
                    fail(f"{p} {r['id']}: cases credited under {o} but not killed")
                if killed:
                    kill_sets[o][r["id"]] = frozenset(credited) if credited else frozenset({T})
        # protocol sentinel: nonempty kill sets equal the study's killed counts
        for o in ORACLES_1:
            n, reported = len(kill_sets[o]), summary["totals"][p][f"killed_{o}"]
            sentinels[f"{p} {o}: nonempty kill sets = killed in summary.json"] = f"{n} = {reported}"
            if n != reported:
                fail(f"{p} {o}: {n} mutants with a nonempty kill set, summary.json reports {reported} killed")

        # consistency: by_O_V and by_O_C again from outcomes.jsonl. S_O_V and S_O_C are
        # all 25 cases (P1 of the study), and the expected state is the baseline state.
        per_port = summary["predictions"]["P1"]["per_port"][p]
        if per_port["O_V"] != len(order) or per_port["O_C"] != len(order):
            fail(f"{p}: S_O_V or S_O_C is not every case; the outcomes cross-check does not apply")
        base = states[(p, "baseline")]
        mismatch = 0
        checked = 0
        for r in scored:
            seen = states.get((p, r["id"]))
            if seen is None:
                continue
            checked += 1
            by_c = [c for c, a, b in zip(order, base, seen) if a != b]
            by_v = [c for c, a, b in zip(order, base, seen) if b.startswith("!") or a[0] != b[0]]
            if by_c != r["by_O_C"].split() or by_v != r["by_O_V"].split():
                mismatch += 1
        sentinels[f"{p}: by_O_V and by_O_C equal outcomes.jsonl ({checked} records)"] = (
            "pass" if mismatch == 0 else f"{mismatch} differ")
        if mismatch:
            fail(f"{p}: {mismatch} mutants whose credited cases differ from outcomes.jsonl")

        # the gap and its directions, from the study's own gap-directions.csv
        gap = {m for m in kill_sets["O_C"] if m not in kill_sets["O_V"]}
        mine = {g["id"]: g for g in gap_rows if g["port"] == p}
        if set(mine) != gap:
            fail(f"{p}: gap-directions.csv lists {len(mine)} mutants, the kill sets give {len(gap)}")
        region = {r["id"]: r["region"] for r in scored}
        out[p] = {
            "mutants": len(scored),
            "kill_sets": kill_sets,
            "gap": gap,
            "direction": {m: mine[m]["direction"] for m in gap},
            "code_literal": {m: mine[m]["code_literal"] == "true" for m in gap},
            "unit": {m: region[m] for m in gap},
            "unit_name": "guard regions",
            "oracles": ORACLES_1,
        }
    return {"subjects": out, "sentinels": sentinels}


# -- PyJWT ----------------------------------------------------------------------------

def import_analyse_s2():
    sys.dont_write_bytecode = True  # never write __pycache__ into the study
    spec = importlib.util.spec_from_file_location("analyse_s2_readonly", STUDY2 / "analyse_s2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pyjwt() -> dict:
    a2 = import_analyse_s2()
    summary = load_json(STUDY2 / "generated" / "summary.json")
    rows = read_csv(STUDY2 / "generated" / "mutants.csv")
    lines = (STUDY2 / "generated" / "outcomes.jsonl").read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    fields = header["fields"]
    if fields[0] != "status" or fields[-2:] != ["site_check", "site_segment"]:
        fail(f"outcomes.jsonl: unexpected fields {fields}")
    rec_fields = fields[1:-2]
    if tuple(rec_fields) != a2.OBSERVED_FIELDS:
        fail("outcomes.jsonl fields differ from analyse_s2.OBSERVED_FIELDS")

    def record(obs: list) -> tuple[str, dict | None]:
        if obs[0] != "observed":
            return obs[0], None
        rec = dict(zip(rec_fields, obs[1:-2]))
        rec["site"] = {"check": obs[-2], "segment": obs[-1]}
        return "observed", rec

    order, cases, base_cases = [], {}, {}
    for c in header["cases"]:
        cid = c["case"]
        order.append(cid)
        kind, rec = record(c["baseline"])
        if kind != "observed":
            fail(f"baseline case {cid} not observed")
        cases[cid] = {**{k: c[k] for k in ("test", "key", "occurrence", "expected", "B", "target", "segment",
                                            "labelled", "site", "site_segment", "post", "params")},
                      "cid": cid, "message": rec["message"]}
        base_cases[cid] = (kind, rec)
    s = {o: {cid for cid, (kind, rec) in base_cases.items() if a2.holds(o, cases[cid], rec)} for o in ORACLES_2}
    sentinels = {}
    for o in ORACLES_2:
        n, reported = len(s[o]), summary["cases"]["S"][NAMES[o]]
        if n != reported:
            fail(f"PyJWT S_{o}: {n} cases, summary.json reports {reported}")
    sentinels["pyjwt: applicable sets S_O equal summary.json"] = "pass"

    runs = {}
    for line in lines[1:]:
        x = json.loads(line)
        if x["set"] != "mutant":
            continue
        if x["state"] != "ran":
            runs[x["run"]] = {"state": x["state"], "cases": {}}
            continue
        status = {}
        for cid, obs in zip(order, x["cases"]):
            status[cid] = base_cases[cid] if obs is None else record(obs)
        runs[x["run"]] = {"state": "ran", "cases": status}

    subject = [r for r in rows if r["subject"] == "yes"]
    if {r["key"] for r in subject} != set(runs):
        fail("the subject mutants of mutants.csv and the mutant runs of outcomes.jsonl differ")
    kill_sets = {o: {} for o in ORACLES_2}
    move_of, mismatch = {}, 0
    for r in subject:
        state = runs[r["key"]]
        verdict = a2.evaluate(state, s, cases, oracles=ORACLES_2)
        for o in ORACLES_2:
            v = verdict[o]
            if (r[NAMES[o]] == "yes") != v["killed"] or int(r[f"{NAMES[o]} cases"]) != len(v["cases"]):
                mismatch += 1
            if v["killed"]:
                kill_sets[o][r["key"]] = frozenset(v["cases"]) if v["cases"] else frozenset({T})
        mv = a2.moves(state, cases)
        text = "; ".join(f"{k} {n}" for k, n in sorted(mv.items()) if k not in ("same", "observed"))
        if text != r["moves"]:
            mismatch += 1
        move_of[r["key"]] = Counter({k: n for k, n in mv.items() if k != "same" and n})
    sentinels["pyjwt: recomputed kills, credited counts and moves equal mutants.csv"] = (
        "pass" if mismatch == 0 else f"{mismatch} differ")
    if mismatch:
        fail(f"PyJWT: {mismatch} kill decisions, credited counts or moves differ from mutants.csv")
    for o in ORACLES_2:
        n, reported = len(kill_sets[o]), summary["totals"][NAMES[o]]["killed"]
        sentinels[f"pyjwt {NAMES[o]}: nonempty kill sets = killed in summary.json"] = f"{n} = {reported}"
        if n != reported:
            fail(f"PyJWT {o}: {n} mutants with a nonempty kill set, summary.json reports {reported} killed")

    gap = {m for m in kill_sets["O_C"] if m not in kill_sets["O_V"]}
    by_set = summary["moves"]["by_set"]["O_C - O_V"]
    case_runs, with_kind = Counter(), Counter()
    for m in gap:
        case_runs.update(move_of[m])
        with_kind.update(move_of[m].keys())
    if (len(gap) != summary["gaps"]["O_C - O_V"] or len(gap) != by_set["mutants"]
            or dict(case_runs) != by_set["case_runs"] or dict(with_kind) != by_set["mutants_with"]):
        fail("PyJWT: the gap or its moves differ from summary.json moves.by_set['O_C - O_V']")
    sentinels["pyjwt: gap and its moves equal summary.json"] = "pass"

    def label(m: str) -> str:
        kinds = sorted(move_of[m])
        if not kinds:
            return "same check"
        return PYJWT_DIRECTION[kinds[0]] if len(kinds) == 1 else "mixed"

    function = {r["key"]: r["function"] for r in subject}
    return {"subjects": {"pyjwt": {
        "mutants": len(subject),
        "kill_sets": kill_sets,
        "gap": gap,
        "direction": {m: label(m) for m in gap},
        "moves": {m: move_of[m] for m in gap},
        "unit": {m: function[m] for m in gap},
        "unit_name": "functions",
        "oracles": ORACLES_2,
    }}, "sentinels": sentinels}


# -- report ----------------------------------------------------------------------------

def counts(items) -> dict:
    return dict(sorted(Counter(items).items()))


def main() -> int:
    v, j = verifier(), pyjwt()
    subjects = {**v["subjects"], **j["subjects"]}
    sentinels = {**v["sentinels"], **j["sentinels"]}
    result, csv_rows = {}, []
    for subj in SUBJECTS:
        x = subjects[subj]
        oracles, sub = {}, {}
        for o in x["oracles"]:
            sub[o] = subsumption(x["kill_sets"][o])
            r = sub[o]
            oracles[NAMES[o]] = {
                "killed": r["killed"], "distinct_kill_sets": r["kill_sets"],
                "minimal": len(r["minimal"]), "distinct_minimal_kill_sets": len(r["minimal_sets"]),
                "uncredited_kills": r["uncredited"],
            }
            csv_rows.append({
                "row": "oracle", "subject": subj, "oracle": NAMES[o], "mutants": x["mutants"],
                "killed": r["killed"], "distinct_kill_sets": r["kill_sets"], "minimal": len(r["minimal"]),
                "distinct_minimal_kill_sets": len(r["minimal_sets"]), "uncredited_kills": r["uncredited"],
                "gap": "", "gap_share_of_killed": "", "minimal_gap": "", "minimal_gap_share_of_minimal": "",
                "minimal_kill_sets_with_gap": "", "gap_units": "", "minimal_gap_units": "",
            })
        c = sub["O_C"]
        gap = x["gap"]
        minimal_c = set(c["minimal"])
        min_gap = sorted(gap & minimal_c)
        sets_with_gap = {x["kill_sets"]["O_C"][m] for m in min_gap}
        units_gap = sorted({x["unit"][m] for m in gap})
        units_min = sorted({x["unit"][m] for m in min_gap})
        gap_entry = {
            "gap": len(gap), "killed_O_C": c["killed"], "gap_share_of_killed_O_C": share(len(gap), c["killed"]),
            "minimal_O_C": len(minimal_c), "minimal_gap": len(min_gap),
            "minimal_gap_share_of_minimal_O_C": share(len(min_gap), len(minimal_c)),
            "distinct_minimal_kill_sets_O_C": len(c["minimal_sets"]),
            "distinct_minimal_kill_sets_with_gap": len(sets_with_gap),
            "minimal_gap_mutants": min_gap,
        }
        csv_rows.append({
            "row": "gap", "subject": subj, "oracle": "O_C not O_V", "mutants": x["mutants"],
            "killed": c["killed"], "distinct_kill_sets": c["kill_sets"], "minimal": len(minimal_c),
            "distinct_minimal_kill_sets": len(c["minimal_sets"]), "uncredited_kills": c["uncredited"],
            "gap": len(gap), "gap_share_of_killed": gap_entry["gap_share_of_killed_O_C"],
            "minimal_gap": len(min_gap), "minimal_gap_share_of_minimal": gap_entry["minimal_gap_share_of_minimal_O_C"],
            "minimal_kill_sets_with_gap": len(sets_with_gap), "gap_units": len(units_gap),
            "minimal_gap_units": len(units_min),
        })
        directions = {"all_gap": counts(x["direction"][m] for m in gap),
                      "minimal_gap": counts(x["direction"][m] for m in min_gap)}
        if "code_literal" in x:
            directions["all_gap_without_code_literal"] = counts(
                x["direction"][m] for m in gap if not x["code_literal"][m])
            directions["minimal_gap_without_code_literal"] = counts(
                x["direction"][m] for m in min_gap if not x["code_literal"][m])
            directions["code_literal"] = {"all_gap": sum(x["code_literal"][m] for m in gap),
                                          "minimal_gap": sum(x["code_literal"][m] for m in min_gap)}
        if "moves" in x:
            for name, keys in (("all_gap", sorted(gap)), ("minimal_gap", min_gap)):
                runs, with_kind = Counter(), Counter()
                for m in keys:
                    runs.update(x["moves"][m])
                    with_kind.update(x["moves"][m].keys())
                directions[f"moves_{name}"] = {
                    "case_runs": dict(sorted(runs.items())),
                    "mutants_with": dict(sorted(with_kind.items()))}
        result[subj] = {
            "scored_mutants": x["mutants"], "oracles": oracles, "gap": gap_entry, "directions": directions,
            "spread": {"unit": x["unit_name"], "units_with_gap": len(units_gap),
                       "units_with_minimal_gap": len(units_min), "gap_units": units_gap,
                       "minimal_gap_units": units_min,
                       "gap_by_unit": counts(x["unit"][m] for m in gap),
                       "minimal_gap_by_unit": counts(x["unit"][m] for m in min_gap)},
        }

    GENERATED.mkdir(exist_ok=True)
    order = {s: i for i, s in enumerate(SUBJECTS)}
    oracle_rank = {n: i for i, n in enumerate(["O_V", "O_V^fc", "O_C", "O_T", "O_S", "O_C not O_V"])}
    csv_rows.sort(key=lambda r: (r["row"] != "oracle", order[r["subject"]], oracle_rank[r["oracle"]]))
    with (GENERATED / "subsumption.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(csv_rows)
    document = {
        "schema": "urn:eatf:experiment:mutation-adequacy-robustness:subsumption:1",
        "analysis": "A. Subsuming mutants (PROTOCOL.md); exploratory and post hoc",
        "uncredited_element": T,
        "sources": {"python": "../mutation-adequacy/generated", "typescript": "../mutation-adequacy/generated",
                    "pyjwt": "../mutation-adequacy-pyjwt/generated"},
        "subjects": result,
        "sentinels": sentinels,
    }
    (GENERATED / "subsumption.json").write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    (GENERATED / "subsumption.md").write_text(render(result, sentinels), encoding="utf-8")
    print(render(result, sentinels))
    print("sentinels: pass")
    return 0


def render(result: dict, sentinels: dict) -> str:
    out = ["# A. Subsuming mutants", "",
           "Exploratory and post hoc (PROTOCOL.md, analysis A). A killed mutant is minimal under an oracle "
           "when no killed mutant has a kill set strictly inside its own; a mutant killed without a credited "
           "case has the kill set {T}. Generated by `subsumption.py`; every number is in `subsumption.json`.",
           "", "## Kill sets per subject and oracle", "",
           "| Subject | Oracle | Mutants | Killed | Distinct kill sets | Minimal | Distinct minimal kill sets | Kill set {T} |",
           "|---|---|---|---|---|---|---|---|"]
    for subj, x in result.items():
        for o, r in x["oracles"].items():
            out.append(f"| {subj} | {o} | {x['scored_mutants']} | {r['killed']} | {r['distinct_kill_sets']} | "
                       f"{r['minimal']} | {r['distinct_minimal_kill_sets']} | {r['uncredited_kills']} |")
    out += ["", "## Verdict-only gap (killed under O_C, not under O_V) over minimal mutants", "",
            "| Subject | Gap | Killed O_C | Gap / O_C | Minimal O_C | Minimal gap | Minimal gap / minimal O_C | "
            "Distinct minimal kill sets O_C | Of them with a gap mutant |",
            "|---|---|---|---|---|---|---|---|---|"]
    for subj, x in result.items():
        g = x["gap"]
        out.append(f"| {subj} | {g['gap']} | {g['killed_O_C']} | {pct(g['gap_share_of_killed_O_C'])} | "
                   f"{g['minimal_O_C']} | {g['minimal_gap']} | {pct(g['minimal_gap_share_of_minimal_O_C'])} | "
                   f"{g['distinct_minimal_kill_sets_O_C']} | {g['distinct_minimal_kill_sets_with_gap']} |")
    out += ["", "## Which check decides, gap mutants against minimal gap mutants", "",
            "Directions as each study classified them: verifier from `gap-directions.csv` (one label per "
            "mutant, `mixed` when its cases moved in different directions); PyJWT from the moves of each "
            "mutant (`same check` when no raise site moved, `mixed` when sites moved in different "
            "directions).", "",
            "| Subject | Set | Mutants | Directions |", "|---|---|---|---|"]
    for subj, x in result.items():
        d = x["directions"]
        for key in ("all_gap", "minimal_gap", "all_gap_without_code_literal", "minimal_gap_without_code_literal"):
            if key in d:
                text = ", ".join(f"{k} {n}" for k, n in d[key].items()) or "none"
                out.append(f"| {subj} | {key.replace('_', ' ')} | {sum(d[key].values())} | {text} |")
    out += ["", "PyJWT, raise-site moves over the gap (as in the study's `moves.by_set`):", ""]
    d = result["pyjwt"]["directions"]
    for key in ("moves_all_gap", "moves_minimal_gap"):
        out.append(f"- {key.removeprefix('moves_').replace('_', ' ')}: case runs "
                   + ", ".join(f"{k} {n}" for k, n in d[key]["case_runs"].items())
                   + "; mutants with at least one: "
                   + ", ".join(f"{k} {n}" for k, n in d[key]["mutants_with"].items()))
    out += ["", "## Spread", "", "| Subject | Unit | Units with a gap mutant | Units with a minimal gap mutant |",
            "|---|---|---|---|"]
    for subj, x in result.items():
        sp = x["spread"]
        out.append(f"| {subj} | {sp['unit']} | {sp['units_with_gap']} | {sp['units_with_minimal_gap']} |")
    out += ["", "## Sentinels", ""]
    for k, val in sentinels.items():
        out.append(f"- {k}: {val}")
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
