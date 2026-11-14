"""Which mutants lie at which check, and what the cases that describe a check do to them.

    python3 -I -B mutants/at_check.py --subject NAME_OR_SUBJECT_JSON
        [--cases TSV] [--extra-tests DIR] [--work DIR] [--out DIR] [--clone DIR]

Reads the definitions of the subject (checks.json beside subject.json), the
subject files of the clone, mutants.csv, and the outputs of analyse_mutants.py
in <out> (runs.jsonl.xz, cases.csv.xz) with the baseline records under <work>.
Writes into <out>: check-spans.csv and at-check.csv, and with --cases
described-cases.csv and described-cases.json; SHA256SUMS is written again.
Every output is sorted and holds no time.

The span of a check: the lines of each of its raise statements, and the lines
of the innermost guard of each. That guard is the test of the enclosing `if`
statement (the raise may stand in its body or in its `else` part), or the
header of the enclosing `except` clause (from `except` to the end of the
exception type).
The guard is found as the toolkit finds it (reach.checks.guard_of). A check
whose raise statements stand under no `if` and no `except` has only its raise
lines. Conditions further out, and the statements that compute what a guard
reads, are not part of the span.

A mutant is at a check when at least 1 of the lines it changes lies in the
span of the check. The deletion of a check changes the lines of its raise
statements, so it is at its check. A mutant can be at several checks.

--cases TSV: a tab-separated file with the header `case`, `described`, `kind`,
`variant`. `case` is the key of a case as cases.csv writes it. `described` is
the id of the check that the case is said to describe. `kind` is free text
(for instance `shadowed` or `comparison`). `variant` is empty, or names 1 test
of the extra tests (the end of its id), the repaired variant of the case's
test. For each row the program reports, for the mutants of mutmut at the
described check, at the check that decides the case in the unmodified
library, and at the described check and not at the deciding check:

    mutants          how many
    suite            killed by the whole suite (a test, a time limit or an error)
    O_C, O_S         detected by the case under O_C; the case's own test does
                     not pass in the recorder run
    own              killed by the case's own test in the whole-suite run
    unique           killed by the case's own test and by no other test
    variant          the variant does not pass on the mutant copy, in a
                     completed run of the extra tests

and the same for the deletion of each of the 2 checks. A unique kill: the
tests of the whole suite that kill the mutant are 1 test (a test that runs in
several suite runs is 1 test). With --extra-tests DIR the runs of that folder
are read (the folder gives the digest under which run_mutants.py kept them).

The expectations M1 to M3 of ../PROTOCOL.md speak of "a mutant at a check".
Section 4.3 of the protocol says "Counts of mutants are of tool mutants; the
deletions are counted apart." and also "the deletion of a check is at that
check". The phrase therefore has 2 readings:

    tool_mutants                 (reading T) a tool mutant at the check
    tool_mutants_and_deletions   (reading TD) a tool mutant at the check, or
                                 the deletion of the check

The key "expectations" of described-cases.json uses reading TD. The key
"expectations_by_reading" gives M1 to M3 under both readings. A row is
shadowed when its described check is not its deciding check. M1 and M2 cover
the shadowed rows, and M3 covers the shadowed rows that have a variant:

    M1  per case, the unique kills of its test at the deciding check; the
        tests with at least 1; "held" when such a test exists
    M2  per case, the mutants at the described check and not at the deciding
        check that the case detects under O_C; the cases with at least 1;
        "held" when no case has one
    M3  per row, the mutants at the described check that the variant kills,
        and whether that is at least 1 (first sentence). Also whether the
        described check fires in no case of the baseline (the second sentence
        applies), and if so, whether the whole suite does not kill its
        deletion and the variant does. "held" when every row holds

A status is "not applicable" when it has 0 rows. The program exits with status
1 when the member "tool_mutants_and_deletions" does not reproduce the key
"expectations".
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (DELETION, default_out, default_work, functions, junit_key, load_json,  # noqa: E402
                    local_settings, need_python_312, read_packed, rel_to_source, subject_paths)
from analyse_mutants import csv_text, parse_lines, yn  # noqa: E402
from materialize import ranges  # noqa: E402
from reach.analyse import Run  # noqa: E402
from reach.checks import guard_of, own_nodes, parents_of  # noqa: E402
from reach.study import left_out_reason  # noqa: E402

GROUPS = ("described", "deciding", "described_not_deciding")


def check_span(fn: ast.AST, lines: list[list[int]]) -> dict:
    """The span of a check in its function `fn`, from the lines of its raise
    statements: {"raise": [lines], "guard": [lines], "kinds": [if, except]}."""
    raises = {(n.lineno, n.end_lineno): n for n in own_nodes(fn, ast.Raise)}
    parents = parents_of(fn)
    out = {"raise": set(), "guard": set(), "kinds": set()}
    for a, z in sorted(tuple(x) for x in lines):
        node = raises.get((a, z))
        if node is None:
            raise SystemExit(f"no raise statement on lines {a}-{z}")
        out["raise"] |= set(range(a, z + 1))
        g = guard_of(node, parents, fn)
        if isinstance(g, ast.If):
            out["guard"] |= set(range(g.test.lineno, g.test.end_lineno + 1))
            out["kinds"].add("if")
        elif isinstance(g, ast.ExceptHandler):
            last = g.type.end_lineno if g.type is not None else g.lineno
            out["guard"] |= set(range(g.lineno, max(g.lineno, last) + 1))
            out["kinds"].add("except")
    return {k: sorted(v) for k, v in out.items()}


def spans_of(checks: list[dict], sources: dict[str, str]) -> dict[str, dict]:
    """Check id -> span, for the checks whose file is in `sources`."""
    trees = {f: functions(ast.parse(text)) for f, text in sources.items()}
    out = {}
    for c in checks:
        if c["file"] in trees:
            try:
                out[c["id"]] = check_span(trees[c["file"]][c["function"]], c["lines"])
            except SystemExit as e:
                raise SystemExit(f"{c['id']}: {e}")
    return out


def part_of(changed: list[int], span: dict) -> str | None:
    """raise, guard, `raise and guard`, or None when no changed line is in the span."""
    r = bool(set(changed) & set(span["raise"]))
    g = bool(set(changed) & set(span["guard"]))
    return "raise and guard" if r and g else "raise" if r else "guard" if g else None


def attribution(rows: list[dict], checks: dict[str, dict], spans: dict[str, dict]) -> list[list]:
    """Rows of at-check.csv: mutant, operator, check, part."""
    by_file = defaultdict(list)
    for cid in sorted(spans):
        by_file[checks[cid]["file"]].append(cid)
    out = []
    for r in rows:
        changed = parse_lines(r["changed_lines"])
        for cid in by_file.get(r["file"], []):
            part = part_of(changed, spans[cid])
            if part:
                out.append([r["mutant"], r["operator"], cid, part])
    return sorted(out)


def test_name(key: str) -> str:
    """A junit key without the name of its suite run."""
    return key.split("|", 1)[1]


READINGS = {"tool_mutants": False, "tool_mutants_and_deletions": True}


def status(rows: int, held: bool) -> str:
    return "not applicable" if rows == 0 else "held" if held else "not held"


def expectations_under(results: list[dict], with_deletions: bool) -> dict:
    """M1 to M3 for the entries of described-cases.json, counting the deletion
    of a check as a mutant at that check when `with_deletions` is true. Only
    shadowed rows enter: all of them for M1 and M2, those with a variant for M3."""
    def add(flag) -> int:
        return int(with_deletions and bool(flag))

    shadowed = [e for e in results if e["described_check"] != e["deciding_check"]]
    m1 = {}
    for e in shadowed:
        dd = e["deletions"]["deciding"]
        m1[e["case"]] = e["mutants"]["deciding"]["unique"] + add(dd and dd["unique"])
    m1_tests = sorted({e["test"] for e in shadowed if m1[e["case"]] >= 1})
    m2 = {}
    for e in shadowed:
        dl = e["deletions"]["described"]
        m2[e["case"]] = e["mutants"]["described_not_deciding"]["O_C"] + add(dl and dl["O_C"])
    m2_cases = sorted(k for k, v in m2.items() if v >= 1)
    m3 = []
    for e in shadowed:
        if e["variant"] is None:
            continue
        dl = e["deletions"]["described"]
        kills = e["mutants"]["described"]["variant"] + add(dl and dl["variant"])
        applies = e["described_fires_in_a_baseline_case"] is False and dl is not None
        second = (not dl["suite"] and bool(dl["variant"])) if applies else None
        first = kills >= 1
        m3.append({"case": e["case"], "variant_kills_at_the_described_check": kills,
                   "first_sentence_holds": first, "second_sentence_applies": applies,
                   "second_sentence_holds": second, "holds": first and (second if applies else True)})
    return {
        "M1": {"unique_kills_at_the_deciding_check": m1, "tests_with_at_least_1": m1_tests,
               "status": status(len(m1), bool(m1_tests))},
        "M2": {"O_C_detections_at_the_described_check_only": m2, "cases_with_at_least_1": m2_cases,
               "status": status(len(m2), not m2_cases)},
        "M3": {"rows": m3, "status": status(len(m3), all(r["holds"] for r in m3))},
    }


def as_expectations(member: dict) -> dict:
    """A member of expectations_by_reading in the form of the key "expectations"."""
    return {
        "M1_tests_with_a_unique_kill_at_the_deciding_check": member["M1"]["tests_with_at_least_1"],
        "M1_cases": member["M1"]["unique_kills_at_the_deciding_check"],
        "M2_cases_that_detect_a_mutant_at_the_described_check_only": member["M2"]["cases_with_at_least_1"],
        "M3_variants": [{"case": r["case"], "holds": r["holds"]} for r in member["M3"]["rows"]],
    }


def main(argv: list[str]) -> int:
    need_python_312()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subject", required=True)
    parser.add_argument("--cases")
    parser.add_argument("--extra-tests")
    parser.add_argument("--work")
    parser.add_argument("--out")
    parser.add_argument("--clone")
    args = parser.parse_args(argv)
    subject_path, subject = subject_paths(args.subject)
    name = subject["name"]
    work = Path(args.work).resolve() if args.work else default_work(name)
    out = Path(args.out).resolve() if args.out else default_out(name)
    clone, _ = local_settings(name, args.clone, "unused")
    checks = {c["id"]: c for c in load_json(subject_path.parent / "checks.json")["checks"]}
    with (out / "mutants.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {r["mutant"]: r for r in rows}
    files = sorted({r["file"] for r in rows})
    sources = {f: (clone / rel_to_source(subject, f)).read_bytes().decode("utf-8") for f in files}
    spans = spans_of(list(checks.values()), sources)
    at_rows = attribution(rows, checks, spans)
    at: dict[str, set] = defaultdict(set)          # check -> mutants of mutmut at it
    for mid, operator, cid, _ in at_rows:
        if operator != DELETION:
            at[cid].add(mid)
    deletion_of = {r["check"]: r["mutant"] for r in rows if r["operator"] == DELETION}
    placed = {(mid, cid) for mid, _, cid, _ in at_rows}
    problems = [f"{r['mutant']}: the deletion of {r['check']} is not at its check" for r in rows
                if r["operator"] == DELETION and (r["mutant"], r["check"]) not in placed]
    span_rows = [[cid, checks[cid]["file"], checks[cid]["function"], ranges(s["raise"]), " ".join(s["kinds"]),
                  ranges(s["guard"]), len(at[cid]), deletion_of.get(cid, "")] for cid, s in sorted(spans.items())]
    written = {
        "check-spans.csv": csv_text(["check", "file", "function", "raise_lines", "guard", "guard_lines",
                                     "mutants_at_the_check", "deletion"], span_rows),
        "at-check.csv": csv_text(["mutant", "operator", "check", "part"], at_rows),
    }
    summary = statuses = None
    if args.cases:
        written.update(described(args, out, work, subject, checks, by_id, at, deletion_of))
        doc = json.loads(written["described-cases.json"])
        summary = doc["expectations"]
        statuses = {reading: {m: member[m]["status"] for m in ("M1", "M2", "M3")}
                    for reading, member in doc["expectations_by_reading"].items()}
        if as_expectations(doc["expectations_by_reading"]["tool_mutants_and_deletions"]) != summary:
            problems.append("expectations_by_reading.tool_mutants_and_deletions does not reproduce expectations")
    for fname, text in written.items():
        (out / fname).write_text(text, encoding="utf-8")
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
            for p in sorted(out.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    tool_at = len({m for ms in at.values() for m in ms})
    print(f"at_check: {name}: {len(spans)} checks in {len(files)} files; {tool_at} of "
          f"{sum(1 for r in rows if r['operator'] != DELETION)} mutants of mutmut are at a check; "
          f"{len(deletion_of)} deletions" + (f"; expectations {json.dumps(summary)}" if summary else "")
          + (f"; statuses by reading {json.dumps(statuses, sort_keys=True)}" if statuses else ""))
    for p in problems[:10]:
        print(f"  problem: {p}")
    return 1 if problems else 0


def described(args, out: Path, work: Path, subject: dict, checks: dict, by_id: dict, at: dict,
              deletion_of: dict) -> dict[str, str]:
    """described-cases.csv and described-cases.json for the rows of --cases."""
    with Path(args.cases).open(encoding="utf-8", newline="") as handle:
        wanted = list(csv.DictReader(handle, delimiter="\t"))
    if not wanted or set(wanted[0]) != {"case", "described", "kind", "variant"}:
        raise SystemExit("--cases: the header case, described, kind, variant is needed")
    base_raw = load_json(work / "records" / "base-1.json")
    base = Run(base_raw)
    study = {k for k, c in base.cases.items() if left_out_reason(c) is None}
    passing = set(load_json(work / "records" / "whole" / "base.json")["passing"])
    run_names = [x["name"] for x in subject["suite_runs"]]
    runs = {}
    for line in read_packed(out / "runs.jsonl").splitlines():
        r = json.loads(line)
        runs[r["mutant"]] = r
    digest, extra_tests = None, []
    if args.extra_tests:
        from run_mutants import extra_digest
        digest = extra_digest(Path(args.extra_tests).resolve())
        extra_tests = load_json(work / "extra" / digest / "base.json")["passing"]
    keys = {w["case"] for w in wanted}
    detected: dict[tuple[str, str], dict] = {}
    for r in csv.DictReader(io.StringIO(read_packed(out / "cases.csv"))):
        if r["case"] in keys:
            detected[(r["mutant"], r["case"])] = r
    fired_recorded = bool(base_raw.get("fired_recorded"))
    mutated_files = {r["file"] for r in by_id.values()}
    fired_anywhere = {cid for c in base.cases.values() for cid in c.get("fired", [])}

    def suite_killed(mid: str) -> bool | None:
        r = runs.get(mid)
        if r is None:
            return None
        return True if r["whole"] in ("timeout", "error") else bool(r["whole_not_passing"])

    def killers(mid: str) -> set[str]:
        r = runs.get(mid)
        return set(r["whole_not_passing"]) if r and r["whole"] == "completed" else set()

    def variant_kills(mid: str, variant: str | None) -> bool | None:
        if variant is None:
            return None
        x = (runs.get(mid, {}).get("extra") or {}).get(digest)
        if x is None:
            return None
        return x["status"] == "completed" and variant in x["not_passing"]

    def counts(mids: list[str], case: str, own: set[str], variant: str | None) -> dict:
        own_names = {test_name(t) for t in own}
        c = {"mutants": len(mids), "suite": 0, "O_C": 0, "O_S": 0, "own": 0, "unique": 0,
             "variant": None if variant is None else 0, "unique_kills": [], "variant_kills": []}
        for m in mids:
            c["suite"] += bool(suite_killed(m))
            d = detected.get((m, case), {})
            c["O_C"] += d.get("O_C") == "yes"
            c["O_S"] += d.get("O_S") == "yes"
            ks = killers(m)
            c["own"] += bool(ks & own)
            if ks and {test_name(t) for t in ks} <= own_names:
                c["unique"] += 1
                c["unique_kills"].append(m)
            if variant_kills(m, variant):
                c["variant"] += 1
                c["variant_kills"].append(m)
        return c

    results, table = [], []
    for w in wanted:
        k, described_check, variant = w["case"], w["described"], (w["variant"] or None)
        if k not in study:
            raise SystemExit(f"--cases: {k} is no case of the study")
        if described_check not in checks:
            raise SystemExit(f"--cases: {described_check} is no check of the subject")
        if variant is not None:
            ids = [t for t in extra_tests if t == variant or t.endswith(variant)]
            if len(ids) != 1:
                raise SystemExit(f"--cases: {variant} names {len(ids)} extra tests that pass unmodified")
            variant = ids[0]
        b = base.cases[k]
        deciding = (b.get("site") or {}).get("check")
        own = {junit_key(b["test"], n) for n in run_names} & passing
        groups = {"described": sorted(at.get(described_check, set())),
                  "deciding": sorted(at.get(deciding, set())) if deciding else [],
                  "described_not_deciding": sorted(at.get(described_check, set())
                                                   - (at.get(deciding, set()) if deciding else set()))}
        entry = {"case": k, "kind": w["kind"], "test": b["test"], "own_test_in_whole_suite": sorted(own),
                 "described_check": described_check, "deciding_check": deciding,
                 "described_file_mutated": checks[described_check]["file"] in mutated_files,
                 "deciding_file_mutated": bool(deciding) and checks[deciding]["file"] in mutated_files,
                 "described_fires_in_a_baseline_case": (described_check in fired_anywhere) if fired_recorded else None,
                 "variant": variant, "mutants": {}, "deletions": {}}
        for g in GROUPS:
            entry["mutants"][g] = counts(groups[g], k, own, variant)
        for label, cid in (("described", described_check), ("deciding", deciding)):
            mid = deletion_of.get(cid) if cid else None
            if mid is None:
                entry["deletions"][label] = None
                continue
            c = counts([mid], k, own, variant)
            entry["deletions"][label] = {"mutant": mid, "suite": bool(c["suite"]), "O_C": bool(c["O_C"]),
                                         "O_S": bool(c["O_S"]), "own": bool(c["own"]), "unique": bool(c["unique"]),
                                         "variant": None if variant is None else bool(c["variant"])}
        dd, dl = entry["deletions"]["deciding"], entry["deletions"]["described"]
        entry["unique_kills_at_the_deciding_check"] = entry["mutants"]["deciding"]["unique"] + bool(dd and dd["unique"])
        same = described_check == deciding
        entry["O_C_detections_at_the_described_check_only"] = None if same else (
            entry["mutants"]["described_not_deciding"]["O_C"] + bool(dl and dl["O_C"]))
        entry["variant_kills_at_the_described_check"] = None if variant is None else (
            entry["mutants"]["described"]["variant"] + bool(dl and dl["variant"]))
        results.append(entry)
        row = [k, w["kind"], described_check, deciding or "", variant or ""]
        for g in GROUPS:
            c = entry["mutants"][g]
            row += [c["mutants"], c["suite"], c["O_C"], c["O_S"], c["own"], c["unique"], c["variant"]]
        for label in ("described", "deciding"):
            d = entry["deletions"][label]
            row += ["", "", "", "", "", "", ""] if d is None else [
                d["mutant"], yn(d["suite"]), yn(d["O_C"]), yn(d["O_S"]), yn(d["own"]), yn(d["unique"]),
                yn(d["variant"])]
        row += [yn(entry["described_fires_in_a_baseline_case"])]
        table.append(row)
    shadowed = [e for e in results if e["described_check"] != e["deciding_check"]]
    with_variant = [e for e in shadowed if e["variant"] is not None]
    m3_rows = []
    for e in with_variant:
        dl = e["deletions"]["described"]
        ok = e["variant_kills_at_the_described_check"] >= 1
        if e["described_fires_in_a_baseline_case"] is False and dl is not None:
            ok = ok and not dl["suite"] and bool(dl["variant"])
        m3_rows.append({"case": e["case"], "holds": ok})
    expectations = {
        "M1_tests_with_a_unique_kill_at_the_deciding_check":
            sorted({e["test"] for e in shadowed if e["unique_kills_at_the_deciding_check"] >= 1}),
        "M1_cases": {e["case"]: e["unique_kills_at_the_deciding_check"] for e in shadowed},
        "M2_cases_that_detect_a_mutant_at_the_described_check_only":
            sorted(e["case"] for e in shadowed if e["O_C_detections_at_the_described_check_only"]),
        "M3_variants": m3_rows,
    }
    header = ["case", "kind", "described_check", "deciding_check", "variant"]
    for g in GROUPS:
        header += [f"{g}_{x}" for x in ("mutants", "suite", "O_C", "O_S", "own", "unique", "variant")]
    for label in ("described", "deciding"):
        header += [f"deletion_{label}_{x}" for x in ("mutant", "suite", "O_C", "O_S", "own", "unique", "variant")]
    header += ["described_fires_in_a_baseline_case"]
    doc = {"subject": {k: subject.get(k) for k in ("name", "version", "commit")},
           "extra_tests_digest": digest, "cases": results, "expectations": expectations,
           "expectations_by_reading": {reading: expectations_under(results, flag)
                                       for reading, flag in sorted(READINGS.items())}}
    return {"described-cases.csv": csv_text(header, table),
            "described-cases.json": json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"}


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
