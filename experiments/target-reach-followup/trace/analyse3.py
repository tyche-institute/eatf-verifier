"""The analysis of the toolkit under rule `reach-target-rule/3`, from the deposited records.

    python3 -I -B trace/analyse3.py --subjects pyjwt pyjwt-package jwcrypto [--work DIR] [--out DIR]

For each subject:

1. Unpacks `../target-reach/generated/<name>/records.tar.xz` into a fresh
   folder of the work directory (`work/trace/<name>/deposited/`).
2. Builds 2 derived definition folders in the work directory, each holding
   subject.json, checks.json and blocks.json of `../target-reach/subjects/<name>/`
   unchanged, and a targets.json: the deposited one of rule 2
   (`defs-rule2/`) and the one of rule 3 that `rule3.py` wrote
   (`defs-rule3/`).
3. Runs `../target-reach/reach/analyse.py` unchanged on both: rule 2 into the
   work directory (`analysis-rule2/`), rule 3 into
   `generated/trace/<name>/analysis/`.
4. Writes `generated/trace/<name>/compare.csv`, `fired-functions.csv` and
   `COMPARE.md`, and, over all the subjects named, `generated/trace/COMPARE.md`
   and `generated/trace/compare.json`.

checks.json stays unchanged in both folders, so the columns of the analysis
that read the field `reachable` of a check (`checks.csv`, column
`reachable`; the counts `checks_reachable` and
`checks_deciding_not_statically_reachable` of `summary.json`) give the
reachability by name under both rules. Only the targets differ.

Sentinels (the outputs are written, then the program exits with an error
when 1 does not hold, for any subject):

    T2   every check that fires in a case of an included block in either
         deposited baseline recorder record (`base-1.json`, `base-2.json`)
         lies in a function that started under an entry point in the trace,
         or is listed in fired-functions.csv with the reason; a fired check
         whose function did not start at all in the traced run does not hold
    T4   the analysis under rule 3 passes the 7 sentinels of analyse.py
    R2   the analysis under rule 2, run here from the deposited records,
         writes files equal byte for byte to `../target-reach/generated/<name>/`
         (every file that analyse.py writes, SHA256SUMS aside, which also
         lists records.tar.xz)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import subprocess
import sys
import tarfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
E = EXP.parent / "target-reach"
if str(E) not in sys.path:
    sys.path.insert(0, str(E))

from reach.checks import load_json  # noqa: E402
from reach.study import firing  # noqa: E402

ANALYSIS_FILES = ("SUMMARY.md", "summary.json", "cases.csv", "checks.csv", "deletions.csv", "flags.csv",
                  "pinning.csv", "undetected.csv")
TRANSITIONS = ("same target", "changed target", "gained a target", "lost a target", "no target under either")
TIERS = ("assertion", "name")


def csv_text(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def fresh_dir(path: Path, inside: Path) -> Path:
    """An empty folder at `path`, which must lie inside `inside`."""
    path = path.resolve()
    if inside.resolve() not in path.parents:
        raise SystemExit(f"refusing to replace {path}: not inside {inside}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def unpack(name: str, dest: Path) -> None:
    with tarfile.open(E / "generated" / name / "records.tar.xz", "r:xz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.name.startswith("/") or ".." in Path(member.name).parts:
                raise SystemExit(f"unexpected member {member.name!r} in the deposited records")
        tar.extractall(dest, filter="data")


def defs_folder(name: str, dest: Path, targets: Path) -> None:
    src = E / "subjects" / name
    for f in ("subject.json", "checks.json", "blocks.json"):
        shutil.copyfile(src / f, dest / f)
    shutil.copyfile(targets, dest / "targets.json")


def run_analysis(defs: Path, work: Path, out: Path, log: Path) -> int:
    cmd = [sys.executable, "-I", "-B", str(E / "reach" / "analyse.py"), "--subject", str(defs / "subject.json"),
           "--defs", str(defs), "--work", str(work), "--out", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return proc.returncode


def transition(t2: str, t3: str) -> str:
    if not t2 and not t3:
        return "no target under either"
    if not t2:
        return "gained a target"
    if not t3:
        return "lost a target"
    return "same target" if t2 == t3 else "changed target"


def tier_counts(rows: list[dict], rule: str) -> dict:
    out = {}
    for tier in TIERS + ("all",):
        sel = [r for r in rows if r[f"target_rule{rule}"] and (tier == "all" or r[f"tier_rule{rule}"] == tier)]
        decided = sum(1 for r in sel if r[f"decides_rule{rule}"] == "yes")
        out[tier] = {"cases_with_a_target": len(sel), "decided_by_the_target": decided,
                     "not_decided_flags": len(sel) - decided}
    return out


def fired_functions(name: str, rec: Path, checks_doc: dict, reach_doc: dict) -> tuple[list[list], bool, dict]:
    checks = {c["id"]: c for c in checks_doc["checks"]}
    fns = {(f["file"], f["function"]): f for f in reach_doc["functions"]}
    cases = Counter()
    for record in ("base-1.json", "base-2.json"):
        for case in load_json(rec / record)["cases"]:
            if case["included"]:
                for cid in firing(case):
                    cases[cid] += 1
    rows, ok = [], True
    tally = Counter()
    for cid in sorted(cases):
        c = checks.get(cid)
        if c is None:
            rows.append([cid, "", "", cases[cid], "no", "", "", "the check is not in checks.json"])
            ok = False
            tally["not in checks.json"] += 1
            continue
        f = fns.get((c["file"], c["function"]))
        if f is None:
            reason = "the function did not start in the traced run"
            ok = False
            tally["function not started"] += 1
            rows.append([cid, c["file"], c["function"], cases[cid], "no", "", "", reason])
        elif f["entry_points"]:
            tally["under an entry point"] += 1
            rows.append([cid, c["file"], c["function"], cases[cid], "yes", " ".join(f["entry_points"]),
                         f["starts_under_none"], ""])
        else:
            tally["started only under no entry point"] += 1
            tests = "; ".join(t for t in f["tests_under_none"])
            reason = ("the function started only with no entry-point frame of the subject on the stack of "
                      f"its thread ({f['starts']} starts, {f['starts_other_threads']} in another thread); "
                      f"tests of the first starts: {tests}")
            rows.append([cid, c["file"], c["function"], cases[cid], "no", "", f["starts_under_none"], reason])
    return rows, ok, dict(sorted(tally.items()))


def same_files(a: Path, b: Path) -> list[str]:
    """The analysis files that differ between 2 folders."""
    return [f for f in ANALYSIS_FILES if not (a / f).exists() or not (b / f).exists()
            or (a / f).read_bytes() != (b / f).read_bytes()]


def one_subject(name: str, work_root: Path, out_root: Path) -> dict:
    work = work_root / name
    work.mkdir(parents=True, exist_ok=True)
    out = out_root / name
    targets3 = out / "targets.json"
    reach_doc = load_json(out / "reach.json")
    deposited = fresh_dir(work / "deposited", work_root)
    unpack(name, deposited)
    d2, d3 = fresh_dir(work / "defs-rule2", work_root), fresh_dir(work / "defs-rule3", work_root)
    defs_folder(name, d2, E / "subjects" / name / "targets.json")
    defs_folder(name, d3, targets3)
    a2 = fresh_dir(work / "analysis-rule2", work_root)
    code2 = run_analysis(d2, deposited, a2, work / "analysis-rule2.log")
    a3 = out / "analysis"
    if a3.exists():
        fresh_dir(a3, out_root)
    code3 = run_analysis(d3, deposited, a3, work / "analysis-rule3.log")
    differ = same_files(a2, E / "generated" / name)
    s3 = load_json(a3 / "summary.json")
    s2 = load_json(a2 / "summary.json")

    # -- per case -------------------------------------------------------------------
    c2 = {(r["block"], r["index"], r["test_node"]): r for r in read_csv(E / "generated" / name / "cases.csv")}
    c3 = {(r["block"], r["index"], r["test_node"]): r for r in read_csv(a3 / "cases.csv")}
    if set(c2) != set(c3):
        raise SystemExit(f"{name}: the 2 analyses hold different cases")
    rows = []
    for k in sorted(c2):
        r2, r3 = c2[k], c3[k]
        rows.append({"block": k[0], "index": k[1], "test_node": k[2],
                     "target_rule2": r2["target"], "basis_rule2": r2["basis"], "tier_rule2": r2["tier"],
                     "decides_rule2": r2["reaches_target"] if r2["target"] else "",
                     "target_rule3": r3["target"], "basis_rule3": r3["basis"], "tier_rule3": r3["tier"],
                     "decides_rule3": r3["reaches_target"] if r3["target"] else "",
                     "baseline_site": r2["baseline_site"],
                     "transition": transition(r2["target"], r3["target"])})
    header = list(rows[0].keys()) if rows else []
    (out / "compare.csv").write_text(csv_text(header, [list(r.values()) for r in rows]), encoding="utf-8")

    # -- per block (every included block, with or without a case) ---------------------
    t2 = {b["key"]: b for b in load_json(E / "subjects" / name / "targets.json")["blocks"]}
    t3 = {b["key"]: b for b in load_json(targets3)["blocks"]}
    block_transitions = Counter(transition(t2[k]["target"], t3[k]["target"]) for k in sorted(t2))

    fired_rows, t2_ok, fired_tally = fired_functions(name, deposited / "records", load_json(d3 / "checks.json"),
                                                     reach_doc)
    (out / "fired-functions.csv").write_text(
        csv_text(["check", "file", "function", "case_executions_fired", "started_under_an_entry_point",
                  "entry_points", "starts_under_no_entry_point", "reason"], fired_rows), encoding="utf-8")

    decided_moves = Counter()
    for r in rows:
        if r["transition"] in ("changed target", "gained a target", "lost a target"):
            decided_moves[f"{r['decides_rule2'] or 'no target'} -> {r['decides_rule3'] or 'no target'}"] += 1
    result = {
        "subject": name,
        "reachability": load_json(targets3)["variant"]["reachability"],
        "case_transitions": {t: sum(1 for r in rows if r["transition"] == t) for t in TRANSITIONS},
        "decides_rule2_to_rule3_for_moved_cases": dict(sorted(decided_moves.items())),
        "block_transitions": {t: block_transitions.get(t, 0) for t in TRANSITIONS},
        "rule2": tier_counts(rows, "2"),
        "rule3": tier_counts(rows, "3"),
        "fired_checks": fired_tally,
        "trace_counts": reach_doc["counts"],
        "seconds": reach_doc["seconds"],
        "sentinels": [
            {"name": "T2: every fired check lies in a function that started under an entry point, or is "
                     "listed with the reason", "pass": t2_ok},
            {"name": "T4: the analysis under rule 3 passes the 7 sentinels of analyse.py", "pass": code3 == 0,
             "detail": [x["name"] for x in s3["sentinels"] if not x["pass"]]},
            {"name": "R2: the analysis under rule 2 from the deposited records reproduces the deposited "
                     "outputs", "pass": code2 == 0 and not differ, "detail": differ},
        ],
        "rule_versions": [s2["rule_version"], s3["rule_version"]],
    }
    (out / "COMPARE.md").write_text(compare_md([result]), encoding="utf-8")
    return result


def compare_md(results: list[dict]) -> str:
    lines = ["# Targets under rule 2 and rule 3", "",
             "Rule 2 is `reach-target-rule/2` of the toolkit. Rule 3 runs the same code with a check "
             "reachable when it is reachable by name or its function started under an entry point in "
             "the traced run of the whole suite on the unmodified copy (`reach.json`). The cases are "
             "those of the deposited records; nothing about a case is re-run. A case is decided by its "
             "target when the raise site of its exception is the target; a case with a target that its "
             "target does not decide is a flag.", ""]
    lines += ["## Reachability of the checks", "",
              "| Subject | Checks | By name | By execution | Both | By name only | By execution only | Neither |",
              "|---|---|---|---|---|---|---|---|"]
    for r in results:
        x = r["reachability"]
        lines.append(f"| {r['subject']} | {x['checks']} | {x['reachable_by_name']} | {x['reachable_by_execution']} | "
                     f"{x['reachable_by_both']} | {x['reachable_by_name_only']} | "
                     f"{x['reachable_by_execution_only']} | {x['reachable_by_neither']} |")
    lines += ["", "## Transitions", "",
              "| Subject | Unit | " + " | ".join(t.capitalize() for t in TRANSITIONS) + " |",
              "|---|---|" + "---|" * len(TRANSITIONS)]
    for r in results:
        for unit, key in (("cases", "case_transitions"), ("included blocks", "block_transitions")):
            lines.append(f"| {r['subject']} | {unit} | " + " | ".join(str(r[key][t]) for t in TRANSITIONS) + " |")
    lines += ["", "## Cases with a target, per tier", "",
              "| Subject | Rule | Tier | Cases with a target | Decided by the target | Not decided (flags) |",
              "|---|---|---|---|---|---|"]
    for r in results:
        for rule in ("2", "3"):
            for tier in TIERS + ("all",):
                x = r[f"rule{rule}"][tier]
                lines.append(f"| {r['subject']} | {rule} | {tier} | {x['cases_with_a_target']} | "
                             f"{x['decided_by_the_target']} | {x['not_decided_flags']} |")
    lines += ["", "## Cases whose target differs", ""]
    for r in results:
        moves = r["decides_rule2_to_rule3_for_moved_cases"]
        lines.append(f"- {r['subject']}: " + ("; ".join(f"decided {k}: {v}" for k, v in moves.items())
                                               if moves else "none"))
    lines += ["", "## Fired checks and the trace", "",
              "Every check that fires in a case of an included block in either deposited baseline record, "
              "by where its function started in the trace (`fired-functions.csv`):", ""]
    for r in results:
        lines.append(f"- {r['subject']}: " + "; ".join(f"{k}: {v}" for k, v in r["fired_checks"].items()))
    lines += ["", "## Where the field `reachable` is read", "",
              "In the toolkit, the field `reachable` of a check is read by `reach/targets.py` (the "
              "candidates of the rule), by `reach/analyse.py` (column `reachable` of `checks.csv`, counts "
              "`checks_reachable` and `checks_deciding_not_statically_reachable`), by `reach/report.py` "
              "(the row \"checks reachable\"), by `recompute/second.py` and `recompute/compare.py` (the "
              "reachable checks counted), by `validate_pyjwt.py` and by `reach/run.py` (a count printed "
              "by `define`). The deletions (`reach/run.py`, `reached_checks`) take the checks that fire "
              "in a case of the study, from `reach/study.py`, and do not read it. The analysis under "
              "rule 3 keeps checks.json unchanged, so those columns and counts give the reachability by "
              "name; only the targets, and what derives from them, differ.", ""]
    lines += ["## Sentinels", ""]
    for r in results:
        for s in r["sentinels"]:
            detail = f" ({s['detail']})" if s.get("detail") else ""
            lines.append(f"- {r['subject']}: {'pass' if s['pass'] else 'FAIL'}: {s['name']}{detail}")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="analysis under reach-target-rule/3")
    parser.add_argument("--subjects", nargs="+", required=True)
    parser.add_argument("--work")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    work_root = Path(args.work).resolve() if args.work else EXP / "work" / "trace"
    out_root = Path(args.out).resolve() if args.out else EXP / "generated" / "trace"
    results = [one_subject(name, work_root, out_root) for name in args.subjects]
    (out_root / "COMPARE.md").write_text(compare_md(results), encoding="utf-8")
    (out_root / "compare.json").write_text(json.dumps(results, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    failed = [(r["subject"], s["name"].split(":")[0]) for r in results for s in r["sentinels"] if not s["pass"]]
    for r in results:
        print(f"analyse3 {r['subject']}: cases {json.dumps(r['case_transitions'])}; "
              f"flags rule 2 {r['rule2']['all']['not_decided_flags']}, rule 3 {r['rule3']['all']['not_decided_flags']}")
    print(f"sentinels that do not hold: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
