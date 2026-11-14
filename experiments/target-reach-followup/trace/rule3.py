"""Targets under rule `reach-target-rule/3`: the code of rule 2 on a widened reachability.

    python3 -I -B trace/rule3.py --subject ../target-reach/subjects/<name>/subject.json
                                 [--reach generated/trace/<name>/reach.json] [--out DIR]

Reads checks.json, blocks.json and targets.json beside subject.json, and
reach.json written by `trace_run.py`. A check is *reachable by name* when
checks.json marks it reachable (`reach/checks.py`, unchanged). It is
*reachable by execution* when its function ("file" and "function" of
checks.json) started under an entry point in the traced whole-suite run
(reach.json, `functions[*].entry_points` not empty). Under rule 3 a check is
reachable when it is reachable by name or by execution. The rule itself is
`compute_targets` of `../target-reach/reach/targets.py`, called unchanged on a
copy of checks.json in which only the field `reachable` of the checks is
replaced.

Writes into `--out` (default `generated/trace/<name>/`):

    targets.json                 the output of compute_targets, serialized as
                                 `reach/run.py` serializes targets.json, with
                                 `rule_version` "reach-target-rule/3" and a
                                 field `variant` that names the rule code,
                                 the reachability and the digest of reach.json
    checks-reachability.csv      check, file, function, role, reachable by
                                 name, by execution, under rule 3, and the
                                 entry points under which its function
                                 started

Sentinel T1 (outputs are written, then the program exits with an error when
it does not hold): with an empty execution set, the same code gives
targets.json of the toolkit byte for byte, after the same serialization.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
E = EXP.parent / "target-reach"
if str(E) not in sys.path:
    sys.path.insert(0, str(E))

from reach.checks import load_json  # noqa: E402
from reach.targets import RULE_VERSION, compute_targets  # noqa: E402

VARIANT = "reach-target-rule/3"


def serialize(doc: dict) -> str:
    """As reach/run.py dump() writes a definition file."""
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def executed_functions(reach_doc: dict | None) -> dict[tuple[str, str], list[str]]:
    """(file, function) -> entry-point names, for the functions that started under
    at least 1 entry point."""
    if reach_doc is None:
        return {}
    return {(f["file"], f["function"]): list(f["entry_points"])
            for f in reach_doc["functions"] if f["entry_points"]}


def widened(checks_doc: dict, executed: dict) -> dict:
    """A copy of checks.json in which a check is reachable when it is reachable by
    name or its function started under an entry point. Nothing else changes."""
    doc = copy.deepcopy(checks_doc)
    for c in doc["checks"]:
        c["reachable"] = bool(c["reachable"]) or (c["file"], c["function"]) in executed
    return doc


def rule3_targets(blocks_doc: dict, checks_doc: dict, executed: dict) -> dict:
    return compute_targets(blocks_doc, widened(checks_doc, executed))


def reachability_rows(checks_doc: dict, executed: dict) -> list[list]:
    rows = []
    for c in checks_doc["checks"]:
        by_name = bool(c["reachable"])
        names = executed.get((c["file"], c["function"]), [])
        rows.append([c["id"], c["file"], c["function"], c["role"], "yes" if by_name else "no",
                     "yes" if names else "no", "yes" if (by_name or names) else "no", " ".join(names)])
    return rows


def counts(rows: list[list]) -> dict:
    name = [r[4] == "yes" for r in rows]
    exe = [r[5] == "yes" for r in rows]
    return {"checks": len(rows),
            "reachable_by_name": sum(name),
            "reachable_by_execution": sum(exe),
            "reachable_by_both": sum(a and b for a, b in zip(name, exe)),
            "reachable_by_name_only": sum(a and not b for a, b in zip(name, exe)),
            "reachable_by_execution_only": sum(b and not a for a, b in zip(name, exe)),
            "reachable_by_neither": sum(not a and not b for a, b in zip(name, exe)),
            "reachable_under_rule_3": sum(a or b for a, b in zip(name, exe))}


def csv_text(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="targets under reach-target-rule/3")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--reach")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    subject_path = Path(args.subject).resolve()
    defs = subject_path.parent
    name = load_json(subject_path)["name"]
    out = Path(args.out).resolve() if args.out else EXP / "generated" / "trace" / name
    reach_path = Path(args.reach).resolve() if args.reach else out / "reach.json"
    checks_doc = load_json(defs / "checks.json")
    blocks_doc = load_json(defs / "blocks.json")
    deposited = (defs / "targets.json").read_text(encoding="utf-8")

    # T1: the empty execution set gives the deposited targets.json
    empty = serialize(rule3_targets(blocks_doc, checks_doc, {}))
    t1 = empty == deposited

    reach_bytes = reach_path.read_bytes()
    reach_doc = json.loads(reach_bytes)
    if reach_doc["subject"] != name:
        raise SystemExit(f"{reach_path} is the trace of {reach_doc['subject']}, not of {name}")
    executed = executed_functions(reach_doc)
    unknown = sorted(set(executed) - {(f["file"], f["function"]) for f in checks_doc["functions"]})
    doc = rule3_targets(blocks_doc, checks_doc, executed)
    assert doc["rule_version"] == RULE_VERSION
    rows = reachability_rows(checks_doc, executed)
    doc["rule_version"] = VARIANT
    doc["variant"] = {
        "name": VARIANT,
        "rule_code": RULE_VERSION,
        "reachable": "reachable by name (checks.json) or the function started under an entry point "
                     "in the traced whole-suite run (reach.json)",
        "reach_json_sha256": hashlib.sha256(reach_bytes).hexdigest(),
        "reachability": counts(rows),
    }
    sentinels = [
        {"name": "T1: with an empty execution set the rule gives targets.json of the toolkit byte for byte",
         "pass": t1},
        {"name": "every function of reach.json is a function of checks.json", "pass": not unknown,
         "detail": [list(k) for k in unknown]},
    ]
    doc["variant"]["sentinels"] = sentinels
    out.mkdir(parents=True, exist_ok=True)
    (out / "targets.json").write_text(serialize(doc), encoding="utf-8")
    (out / "checks-reachability.csv").write_text(
        csv_text(["check", "file", "function", "role", "reachable_by_name", "reachable_by_execution",
                  "reachable_rule_3", "entry_points"], rows), encoding="utf-8")
    failed = [s["name"].split(":")[0] for s in sentinels if not s["pass"]]
    with_target = sum(1 for b in doc["blocks"] if b["target"])
    print(f"rule3 {name}: {json.dumps(counts(rows), sort_keys=True)}; {with_target} included blocks with "
          f"a target; sentinels that do not hold: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
