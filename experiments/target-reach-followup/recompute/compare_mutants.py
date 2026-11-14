"""Compare the output of second_mutants.py with the outputs of the first programs (part "mutants").

    python3 -I -B recompute/compare_mutants.py --second SECOND.json --first DIR [--cases CASES.tsv]

`--second`: the JSON file written by recompute/second_mutants.py.
`--first`: the output folder of mutants/analyse_mutants.py and mutants/at_check.py
(score.json, oracles.csv, per-test.csv, per-case.csv, check-spans.csv, at-check.csv,
described-cases.json, described-cases.csv, runs.jsonl.xz, cases.csv.xz, mutants.csv).
`--cases`: the cases file written by mutants/cases_file.py (default: cases.tsv in
`--first` when it exists); its rows of kind "comparison" are compared with the
comparison cases that the second computation derives.
`--summary`: optional JSON file for the counts per comparison name.

The table MAP below names each compared value of the second output and its place in
the first outputs. Sets are compared as sets (the members found on 1 side only are
printed), per-item tables item by item. Values marked "derived" are computed here,
either from per-item values of the second output or from the raw first outputs
(oracles.csv, runs.jsonl.xz, cases.csv.xz, per-case.csv, at-check.csv, check-spans.csv,
the function, file and operator columns of mutants.csv, score.json), where no first output
states them.

Totals of the second output (comparison counts.totals):
- counts.tool_mutants and counts.deletions against "mutants" of score.json whole_suite
  and check_deletions;
- counts.tool_mutants_by_operator and counts.tool_mutants_by_file against "mutants" of
  each entry of score.json by_operator and by_file;
- counts.deletions_by_file, which no first output states, against the rows of mutants.csv
  of operator check_deletion counted per file (derived).
A table of counts is compared as a whole and counts as 1 compared value, like
recorder_runs and case_statuses.

Definitions used for the first side where it is derived:
- a tool mutant is in the function of a check when its file and function in
  mutants.csv equal the file and function of the check in check-spans.csv;
- a tool mutant is at a check when at-check.csv has a row for the pair;
- the kills of a mutant are its whole_not_passing tests in runs.jsonl when its
  whole-suite run is completed;
- a mutant is killed by its test when 1 of these keys is a whole-suite key of the
  test (per-case.csv own_test_in_whole_suite), and it is a unique kill of that test
  when every killing key names that test;
- the variant kills a mutant when its extra run is completed and lists the variant;
- a library value "killed" holds a mutant whose whole-suite run is not completed, or
  that a test not removed kills, or that an added extra test kills.

Expectations: M1, M2 and M3 of the second output (decided on tool mutants) are
compared with the member "tool_mutants" of expectations_by_reading in
described-cases.json, per row and by status. The deletion values of the second output
are compared with the member "tool_mutants_and_deletions": its per-row value minus the
value of "tool_mutants" is the deletion flag, and the per-row results and statuses
under that reading are derived from the second output. Only rows whose kind starts
with "shadowed" enter; M1 to M3 over rows of other kinds are reported as not compared.
The key "expectations" of described-cases.json is compared, field by field, with the
form that the member "tool_mutants_and_deletions" gives it (the relation that
mutants/at_check.py checks when it writes the file).

described-cases.csv: each cell is compared with the value of described-cases.json
that the table CSV_COLUMNS names for its column, row by row in the order of both files.
The values of described-cases.json are compared with the second output above, so each
cell is tied to the second output through the JSON file. A column that CSV_COLUMNS
does not name is listed as not compared.

Internal checks of the second output: each list that has a count beside it (a key
"<name>_count", a block {"ids", "count"} or a "counts" table) has that length.

Output: "compared N, agree N, differ N", the internal checks, the values that are not
compared with the reason, then each difference with both values.
Exit status 0 when no compared value differs and every internal check holds, 1
otherwise, 2 on a missing or malformed input.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import lzma
import sys
from collections import Counter
from pathlib import Path

ORACLES = ("O_V", "O_Vfc", "O_C", "O_T", "O_S")
CASE_ORACLES = ("O_V", "O_Vfc", "O_C", "O_T")
DELETION = "check_deletion"

# name of the comparison -> (place in the second output, place in the first outputs)
MAP = {
    "mutant.file/function/operator/check": ("per_mutant[m].file, function, operator, check",
                                            "oracles.csv: file, function, operator, check"),
    "mutant.recorder_status": ("per_mutant[m].recorder_status", "oracles.csv: recorder_run"),
    "mutant.detected": ("per_mutant[m].detected[O_V..O_S, suite]", "oracles.csv: O_V..O_S, suite"),
    "mutant.detected_withheld_as_failing": ("per_mutant[m].detected_withheld_as_failing",
                                            "oracles.csv: <oracle> withheld-as-failing"),
    "mutant.whole_suite_status": ("per_mutant[m].whole_suite_status", "oracles.csv: whole_suite_run"),
    "mutant.killed_by_suite": ("per_mutant[m].killed_by_suite", "oracles.csv: whole_suite_killed"),
    "mutant.killing_tests_count": ("len(per_mutant[m].killing_tests)", "oracles.csv: whole_suite_tests_killing"),
    "mutant.killing_tests": ("per_mutant[m].killing_tests (set)",
                             "runs.jsonl: whole_not_passing, without '<run>|' (set)"),
    "mutant.run_counts": ("per_mutant[m].recorder_runs, whole_suite_runs", "runs.jsonl: recorder_runs, whole_runs"),
    "mutant.extra_status": ("per_mutant[m].extra_status", "runs.jsonl: extra[digest].status"),
    "mutant.killing_extra_tests": ("per_mutant[m].killing_extra_tests (set)",
                                   "runs.jsonl: extra[digest].not_passing in a completed run (set)"),
    "at_check.tool": ("per_mutant[m].at_checks of tool mutants: (mutant, check, part) (set)",
                      "at-check.csv rows of tool mutants (set)"),
    "at_check.deletions": ("per_mutant[d].at_checks of deletions: (deletion, check) (set)",
                           "at-check.csv rows of operator check_deletion (set)"),
    "checks.set": ("checks (keys)", "check-spans.csv: check"),
    "checks.span": ("checks[c].raise_lines, union of guards[].lines, guard kinds, tool_mutants_at_count, deletion",
                    "check-spans.csv: raise_lines, guard_lines, guard, mutants_at_the_check, deletion"),
    "tests.set": ("tests (keys)", "per-test.csv: test without '<run>|'"),
    "tests.counts": ("tests[t].kills_count, unique_kills_count, deletions_killed_count, "
                     "unique_deletion_kills_checks, functions of unique_kills (derived)",
                     "per-test.csv: kills, unique_kills, check_deletions_killed, "
                     "check_deletions_killed_by_this_test_only, unique_kill_functions"),
    "score.whole_suite": ("library.tool_mutants: total, killed_by_the_whole_suite, by_kind, score, "
                          "score_without_error_mutants, error ids (derived from per_mutant)",
                          "score.json whole_suite"),
    "score.check_deletions": ("library.deletions: total, killed, by_kind, score; checks of the deletions not "
                              "killed; deletions with exactly 1 killing test (derived)",
                              "score.json check_deletions"),
    "score.unique": ("sum of tests[t].unique_kills_count; tests with kills_count > 0",
                     "score.json mutants_killed_by_exactly_1_test, tests_killing_at_least_1_mutant"),
    "score.mutant_level_oracles": ("counts.mutant_level_detection_tool_mutants / _deletions",
                                   "score.json mutant_level_oracles, check_deletions.mutant_level_oracles"),
    "score.run_statuses": ("per_mutant recorder_status / whole_suite_status of tool mutants (derived)",
                           "score.json recorder_runs, whole_suite_runs"),
    "score.cases": ("counts.cases_of_the_study", "score.json cases"),
    "counts.totals": ("counts.tool_mutants, deletions, tool_mutants_by_operator, tool_mutants_by_file, "
                      "deletions_by_file (each table as 1 value)",
                      "score.json whole_suite.mutants, check_deletions.mutants, by_operator[o].mutants, "
                      "by_file[f].mutants; mutants.csv rows of operator check_deletion counted per file "
                      "(derived)"),
    "score.case_statuses": ("sum of per_mutant[m].case_status over tool mutants, 'no record' x cases for a "
                            "recorder error (derived)", "score.json case_statuses"),
    "score.by_file/by_operator": ("per_mutant of tool mutants grouped (derived)", "score.json by_file, by_operator"),
    "score.without_tests": ("library.tool_mutants.killed_without_the_given_tests; killed minus that (set)",
                            "score.json without_tests: killed, killed_by_a_test, no_longer_killed"),
    "score.extra_tests": ("library.extra_digest, extra_tests, tool_mutants/deletions."
                          "killed_with_the_extra_tests_added, newly killed (set), mutants with a killing extra "
                          "test (derived)", "score.json extra_tests"),
    "score.replacement": ("per replacement, from per_mutant killing_tests and killing_extra_tests (derived)",
                          "score.json extra_tests.replacements[i]: killed, no_longer_killed, newly_killed"),
    "score.toolkit_deletions": ("input_checks.deletions_compared_with_the_toolkit_deposit",
                                "score.json check_deletions.toolkit_deletions"),
    "case.detection": ("rows.*[case].groups.tool_mutants_in_all_mutated_files: detected_by_the_case_under_O_C, "
                       "test_of_the_case_does_not_pass_in_the_recorder_run, recorder_run_without_a_value (sets)",
                       "cases.csv: tool mutants with O_C yes, O_S yes, status 'no record' (sets)"),
    "case.per_case": ("rows.*[case]: target_rule_2, deciding_check, test_whole_suite_keys; counts of O_C and "
                      "of the test not passing in all files, in the function of the deciding check and (target "
                      "= described) of the target; unique kills of its test",
                      "per-case.csv: target, deciding_check, own_test_in_whole_suite, O_C_kills*, O_S_kills*, "
                      "unique_kills"),
    "row.groups": ("rows.*[case][described].groups (3 groups of tool mutants): mutants, killed_by_suite, "
                   "detected O_C, test does not pass, killed_by_its_test, unique_kills_of_its_test (number and "
                   "set), killed_by_the_variant (number and set)",
                   "described-cases.json cases[].mutants.<group>: mutants, suite, O_C, O_S, own, unique, "
                   "unique_kills, variant, variant_kills"),
    "row.deletions": ("rows.*[case][described].groups.deletion_of_the_*_check: id, and each list non-empty",
                      "described-cases.json cases[].deletions.<described|deciding>"),
    "row.facts": ("rows.*: kind, deciding_check, variant, test_whole_suite_keys, "
                  "described_check_fires_in_a_recorded_case_of_the_baseline",
                  "described-cases.json cases[]: kind, deciding_check, variant, own_test_in_whole_suite, "
                  "described_fires_in_a_baseline_case"),
    "row.csv": ("described-cases.json cases[]: the value that CSV_COLUMNS names for each column (compared with "
                "the second output under row.groups, row.deletions, row.facts and row.rows)",
                "described-cases.csv: each cell; the columns, and the (case, described_check) of each row"),
    "row.rows": ("rows.shadowed + rows.other_kinds + rows.comparison: (case, described) present",
                 "described-cases.json cases[]: (case, described_check)"),
    "library.described": ("library.from_shadowed_rows/from_rows_of_other_kinds.described_checks[c][v]."
                          "not_killed_by_the_suite_and_killed_by_the_variant (set), deletion_killed_by_the_variant",
                          "described-cases.json described group variant_kills minus mutants killed in oracles.csv "
                          "(derived); deletions.described.variant"),
    "row.group_lists": ("rows.*[case][described].groups.<8 groups>: member lists mutants, killed_by_suite, "
                        "detected O_C, test does not pass, killed_by_its_test, unique_kills_of_its_test, "
                        "killed_by_the_variant, recorder_run_without_a_value (sets)",
                        "derived: at-check.csv / mutants.csv function columns / check-spans.csv deletion "
                        "(members), oracles.csv whole_suite_killed, cases.csv O_C, O_S, status 'no record', "
                        "runs.jsonl whole_not_passing and extra not_passing, per-case.csv deciding_check and "
                        "own_test_in_whole_suite"),
    "row.files": ("rows.*: described_check_in_mutated_files, deciding_check_in_mutated_files",
                  "described-cases.json cases[]: described_file_mutated, deciding_file_mutated"),
    "checks.members": ("checks[c].tool_mutants_at, tool_mutants_in_function (sets), function",
                       "derived: at-check.csv rows of check c; tool mutants of mutants.csv with the file and "
                       "function of c in check-spans.csv; check-spans.csv function"),
    "extra.kills": ("extra_tests[x].kills, deletions_killed (sets)",
                    "derived: runs.jsonl extra[digest].not_passing of a completed extra run"),
    "library.derived": ("library.tool_mutants/deletions: killed_by_the_whole_suite, not_killed, "
                        "killed_without_the_given_tests, killed_with_the_given_replacements (all together), "
                        "killed_with_the_extra_tests_added (sets); from_shadowed_rows and "
                        "from_rows_of_other_kinds: tests, replacements, killed_by_the_whole_suite, "
                        "killed_without_the_tests_that_hold_a_row, killed_with_each_such_test_replaced_by_its_"
                        "variant (sets); unique_kills_of_the_removed_tests (set); removal_check",
                        "derived: oracles.csv, runs.jsonl; the given tests from score.json without_tests."
                        "tests_left_out, the given replacements from score.json extra_tests.replacements, the "
                        "extra tests from score.json extra_tests.extra_tests, the rows from described-cases.json"),
    "expect.rows": ("expectations.M1/M2/M3.rows (cases of shadowed rows)",
                    "expectations_by_reading.tool_mutants M1/M2/M3 rows, restricted to rows of a shadowed kind"),
    "expect.T.M1": ("expectations.M1.rows[r]: number and set of unique_kills_of_its_test_at_the_deciding_check, "
                    "tool_mutants_at_the_deciding_check; tests of the rows with at least 1",
                    "expectations_by_reading.tool_mutants.M1: unique_kills_at_the_deciding_check, "
                    "tests_with_at_least_1; described-cases.json mutants.deciding: unique_kills, mutants"),
    "expect.T.M2": ("expectations.M2.rows[r]: number and set of detected_under_O_C_at_the_described_and_not_at_"
                    "the_deciding_check, recorder_runs_without_a_value, tool_mutants_at_the_described_and_not_at_"
                    "the_deciding_check; rows_with_such_a_detection",
                    "expectations_by_reading.tool_mutants.M2: O_C_detections_at_the_described_check_only, "
                    "cases_with_at_least_1; derived sets from at-check.csv and cases.csv; described-cases.json "
                    "mutants.described_not_deciding.mutants"),
    "expect.T.M3": ("expectations.M3.rows[r]: number and set of variant_kills_at_the_described_check, first part, "
                    "second part applies / holds, holds_for_this_row, tool_mutants_at_the_described_check, "
                    "whole_suite_kills_the_deletion, suite_with_the_variant_kills_the_deletion, "
                    "described_check_fires_in_a_recorded_case_of_the_baseline",
                    "expectations_by_reading.tool_mutants.M3.rows[]; described-cases.json mutants.described, "
                    "deletions.described, described_fires_in_a_baseline_case"),
    "expect.T.status": ("expectations.M1..M3.status", "expectations_by_reading.tool_mutants.M1..M3.status"),
    "expect.TD.deletion": ("expectations.M1.rows[r].deletion_of_the_deciding_check_is_a_unique_kill_of_its_test, "
                           "M2.rows[r].deletion_of_the_described_check_detected_under_O_C, "
                           "M3.rows[r].variant_kills_the_deletion_of_the_described_check (as 0 or 1)",
                           "expectations_by_reading: tool_mutants_and_deletions value minus tool_mutants value"),
    "expect.TD.result": ("derived from the second output: per-row values plus the deletion flag, the per-row "
                         "result of M3 and the statuses of M1 to M3 under that count",
                         "expectations_by_reading.tool_mutants_and_deletions: per-row values, M3 rows[].holds, "
                         "statuses"),
    "expect.key": ("described-cases.json expectations_by_reading.tool_mutants_and_deletions in the form of the key "
                   "'expectations': M1 tests with at least 1, M1 value per row, M2 cases with at least 1, M3 holds "
                   "per row (compared with the second output under expect.TD.result)",
                   "described-cases.json expectations: M1_tests_with_a_unique_kill_at_the_deciding_check, M1_cases, "
                   "M2_cases_that_detect_a_mutant_at_the_described_check_only, M3_variants"),
    "comparison_cases": ("cases_file.comparison_cases_derived (set)", "cases.tsv rows of kind 'comparison' (set)"),
    "shadowed_rows": ("cases_file.shadowed_rows: (case, described, kind, variant) (set)",
                      "cases.tsv rows whose kind starts with 'shadowed', variant resolved through "
                      "described-cases.json (set)"),
}

NO_EXPECTATION = "not compared: the protocol defines no expectation over these rows"

# values of the second output with no counterpart in the first outputs
STATIC_NOT_COMPARED = [
    ("checks[c].fires_in_a_recorded_case_of_the_baseline, fires_in_a_case_of_the_study, deciding_check, "
     "reachable, span, function_lines, guards[].text",
     "check-spans.csv holds no such column"),
    ("rows.*.described_check_fires_in_a_case_of_the_study, test_passes_at_baseline_recorder, variant_as_written, "
     "and M3 rows[r].described_check_fires_in_a_case_of_the_study",
     "the first outputs state only whether the described check fires in a recorded case of the baseline"),
    ("per_mutant[m].changed_lines, in_functions_of_checks, killed_by_suite_as",
     "inputs (mutants.csv) or covered per check by checks.members; no first column per mutant"),
    ("counts.recorded_executions_of_included_blocks, mutants_without_a_recorder_value, tool_mutants_at_least_1_check",
     "no first counterpart"),
    ("library.removal_check.note, expectations rules", "text"),
    ("arguments, input_sha256, input_checks, readings, protocol, version", "provenance and checks of the inputs"),
]


def kind_is_shadowed(kind: str | None) -> bool:
    return bool(kind) and kind.startswith("shadowed")

GROUP_MAP = {"described": "tool_mutants_at_the_described_check",
             "deciding": "tool_mutants_at_the_deciding_check",
             "described_not_deciding": "tool_mutants_at_the_described_and_not_at_the_deciding_check"}


def cell(v) -> str:
    """A value as mutants/at_check.py writes it into a CSV cell."""
    return "" if v is None else str(v)


def csv_columns() -> dict:
    """Column of described-cases.csv -> the value of an entry of described-cases.json that it holds."""
    cols = {
        "case": lambda e: e["case"],
        "kind": lambda e: e["kind"],
        "described_check": lambda e: e["described_check"],
        "deciding_check": lambda e: cell(e["deciding_check"]),
        "variant": lambda e: cell(e["variant"]),
    }
    for g in GROUP_MAP:
        for x in ("mutants", "suite", "O_C", "O_S", "own", "unique", "variant"):
            cols[f"{g}_{x}"] = lambda e, g=g, x=x: cell(e["mutants"][g][x])
    for label in ("described", "deciding"):
        cols[f"deletion_{label}_mutant"] = lambda e, label=label: cell((e["deletions"][label] or {}).get("mutant"))
        for x in ("suite", "O_C", "O_S", "own", "unique", "variant"):
            cols[f"deletion_{label}_{x}"] = lambda e, label=label, x=x: yn((e["deletions"][label] or {}).get(x))
    cols["described_fires_in_a_baseline_case"] = lambda e: yn(e["described_fires_in_a_baseline_case"])
    return cols


CSV_COLUMNS = csv_columns()


class Tally:
    def __init__(self):
        self.compared = 0
        self.differences: list[tuple[str, str, object, object]] = []
        self.by_name: Counter = Counter()
        self.differ_by_name: Counter = Counter()
        self.not_compared: list[tuple[str, str]] = []
        self.internal_checked = 0
        self.internal_failures: list[tuple[str, object, object]] = []

    def skip(self, what: str, why: str) -> None:
        if (what, why) not in self.not_compared:
            self.not_compared.append((what, why))

    def internal(self, where: str, length, count) -> None:
        self.internal_checked += 1
        if length != count:
            self.internal_failures.append((where, length, count))

    def opt_sets(self, name: str, item: str, second, first) -> None:
        """Sets where None (no variant) must match None."""
        if second is None or first is None:
            self.eq(name, f"{item} (none)", second is None, first is None)
        else:
            self.sets(name, item, second, first)

    def eq(self, name: str, item: str, second, first) -> None:
        assert name in MAP, name
        self.compared += 1
        self.by_name[name] += 1
        if second != first:
            self.differ_by_name[name] += 1
            self.differences.append((name, item, second, first))

    def sets(self, name: str, item: str, second, first) -> None:
        assert name in MAP, name
        s, f = set(second or ()), set(first or ())
        self.compared += 1
        self.by_name[name] += 1
        if s != f:
            self.differ_by_name[name] += 1
            self.differences.append((name, item, {"only in second": sorted(s - f)},
                                     {"only in first": sorted(f - s)}))


def yn(v) -> str:
    return "" if v is None else ("yes" if v else "no")


def identity(key: str) -> str:
    return key.split("|", 1)[1] if "|" in key else key


def parse_lines(text: str) -> list[int]:
    out = []
    for part in filter(None, (text or "").split(";")):
        a, _, z = part.partition("-")
        out += list(range(int(a), int(z or a) + 1))
    return sorted(set(out))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_xz(path: Path) -> str:
    return lzma.decompress(path.read_bytes()).decode("utf-8")


def need(path: Path) -> Path:
    if not path.exists():
        raise SystemExit(f"compare_mutants: missing input: {path}")
    return path


def fn_counts(functions: list[str]) -> str:
    c = Counter(functions)
    return "; ".join(f"{f} x{n}" for f, n in sorted(c.items()))


def check_lengths(t: Tally, node, where: str) -> None:
    """Every list of the second output with a count beside it has that length."""
    if isinstance(node, dict):
        if isinstance(node.get("ids"), list) and isinstance(node.get("count"), int):
            t.internal(f"{where}.ids", len(node["ids"]), node["count"])
        counts = node.get("counts")
        if isinstance(counts, dict):
            for k, v in sorted(counts.items()):
                if k in node:
                    t.internal(f"{where}.{k}", None if node[k] is None else len(node[k]), v)
        for k, v in sorted(node.items()):
            if k.endswith("_count") and isinstance(node.get(k[:-6]), list):
                t.internal(f"{where}.{k[:-6]}", len(node[k[:-6]]), v)
        for k, v in sorted(node.items()):
            check_lengths(t, v, f"{where}.{k}" if where else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            check_lengths(t, v, f"{where}[{i}]")


def compare(second: dict, first: Path, cases_tsv: Path | None) -> Tally:
    t = Tally()
    check_lengths(t, second, "")
    pm = second["per_mutant"]
    tool = sorted(m for m, v in pm.items() if v["kind"] == "tool mutant")
    dels = sorted(m for m, v in pm.items() if v["kind"] == "deletion")
    digest = second["library"].get("extra_digest")

    # -- per mutant: oracles.csv
    oracles = {r["mutant"]: r for r in read_csv(need(first / "oracles.csv"))}
    t.sets("mutant.file/function/operator/check", "mutants", pm.keys(), oracles.keys())
    for m in sorted(set(pm) & set(oracles)):
        s, f = pm[m], oracles[m]
        t.eq("mutant.file/function/operator/check", m,
             (s["file"], s["function"], s["operator"], s["check"] or ""),
             (f["file"], f["function"], f["operator"], f["check"]))
        t.eq("mutant.recorder_status", m, s["recorder_status"], f["recorder_run"])
        det = s["detected"] or {}
        for o in ORACLES + ("suite",):
            t.eq("mutant.detected", f"{m} {o}", yn(det.get(o)), f[o])
        wf = s["detected_withheld_as_failing"] or {}
        for o in CASE_ORACLES:
            t.eq("mutant.detected_withheld_as_failing", f"{m} {o}", yn(wf.get(o)), f[f"{o} withheld-as-failing"])
        t.eq("mutant.whole_suite_status", m, s["whole_suite_status"], f["whole_suite_run"])
        t.eq("mutant.killed_by_suite", m, yn(s["killed_by_suite"]), f["whole_suite_killed"])
        t.eq("mutant.killing_tests_count", m, len(s["killing_tests"]), int(f["whole_suite_tests_killing"]))

    # -- per mutant: runs.jsonl
    runs = {}
    for line in read_xz(need(first / "runs.jsonl.xz")).splitlines():
        r = json.loads(line)
        runs[r["mutant"]] = r
    for m in sorted(set(pm) & set(runs)):
        s, f = pm[m], runs[m]
        lost = {identity(k) for k in f["whole_not_passing"]} if f["whole"] == "completed" else set()
        t.sets("mutant.killing_tests", m, s["killing_tests"], lost)
        t.eq("mutant.run_counts", m, (s["recorder_runs"], s["whole_suite_runs"]), (f["recorder_runs"], f["whole_runs"]))
        if digest:
            x = (f.get("extra") or {}).get(digest)
            t.eq("mutant.extra_status", m, s["extra_status"], x["status"] if x else None)
            xk = set(x["not_passing"]) if x and x["status"] == "completed" else set()
            t.sets("mutant.killing_extra_tests", m, s["killing_extra_tests"], xk)

    # first-side kills, derived from runs.jsonl
    def f_killers(m: str) -> set:
        r = runs.get(m)
        return set(r["whole_not_passing"]) if r and r["whole"] == "completed" else set()

    def f_xkills(m: str) -> set:
        r = runs.get(m)
        x = ((r or {}).get("extra") or {}).get(digest) if digest else None
        return set(x["not_passing"]) if x and x["status"] == "completed" else set()

    def f_killed(group, removed=(), added=()) -> set:
        rem, add = set(removed), set(added)
        return {m for m in group if m in runs and (runs[m]["whole"] != "completed"
                                                    or ({identity(k) for k in f_killers(m)} - rem)
                                                    or (add & f_xkills(m)))}

    if digest:
        for x, v in sorted(second["extra_tests"].items()):
            t.sets("extra.kills", f"{x} kills (derived)", v["kills"], {m for m in tool if x in f_xkills(m)})
            t.sets("extra.kills", f"{x} deletions_killed (derived)", v["deletions_killed"],
                   {m for m in dels if x in f_xkills(m)})

    # -- at a check
    at_rows = read_csv(need(first / "at-check.csv"))
    first_tool = {f"{r['mutant']}|{r['check']}|{r['part']}" for r in at_rows if r["operator"] != DELETION}
    first_del = {f"{r['mutant']}|{r['check']}" for r in at_rows if r["operator"] == DELETION}
    second_tool = {f"{m}|{c}|{p}" for m in tool for c, p in pm[m]["at_checks"].items()}
    second_del = {f"{m}|{c}" for m in dels for c in pm[m]["at_checks"]}
    t.sets("at_check.tool", "(mutant, check, part)", second_tool, first_tool)
    t.sets("at_check.deletions", "(deletion, check)", second_del, first_del)

    # -- spans
    spans = {r["check"]: r for r in read_csv(need(first / "check-spans.csv"))}
    chk = second["checks"]
    t.sets("checks.set", "checks", chk.keys(), spans.keys())
    for c in sorted(set(chk) & set(spans)):
        s, f = chk[c], spans[c]
        glines = sorted({x for g in s["guards"] for x in g["lines"]})
        kinds = sorted({g["kind"] for g in s["guards"] if g["kind"]})
        t.eq("checks.span", f"{c} raise_lines", s["raise_lines"], parse_lines(f["raise_lines"]))
        t.eq("checks.span", f"{c} guard_lines", glines, parse_lines(f["guard_lines"]))
        t.eq("checks.span", f"{c} guard kinds", kinds, sorted(f["guard"].split()))
        t.eq("checks.span", f"{c} tool mutants at", s["tool_mutants_at_count"], int(f["mutants_at_the_check"]))
        t.eq("checks.span", f"{c} deletion", s["deletion"] or "", f["deletion"])

    # -- members of a check: at it, in its function (first side derived)
    mcsv = {r["mutant"]: r for r in read_csv(need(first / "mutants.csv"))}
    tool_set = set(tool)
    at_by_check: dict[str, set] = {}
    for r in at_rows:
        if r["operator"] != DELETION:
            at_by_check.setdefault(r["check"], set()).add(r["mutant"])
    fn_of_check = {c: (f["file"], f["function"]) for c, f in spans.items()}

    def first_in_fn(c: str | None) -> set:
        if not c or c not in fn_of_check:
            return set()
        return {m for m in tool_set if m in mcsv and (mcsv[m]["file"], mcsv[m]["function"]) == fn_of_check[c]}

    first_deletion_of = {c: f["deletion"] for c, f in spans.items() if f["deletion"]}
    for c in sorted(set(chk) & set(spans)):
        s = chk[c]
        t.sets("checks.members", f"{c} tool_mutants_at", s["tool_mutants_at"], at_by_check.get(c, set()))
        t.sets("checks.members", f"{c} tool_mutants_in_function (derived)", s["tool_mutants_in_function"],
               first_in_fn(c))
        t.eq("checks.members", f"{c} function", (s["file"], s["function"]), fn_of_check[c])

    # -- tests
    pt = read_csv(need(first / "per-test.csv"))
    tests = second["tests"]
    t.sets("tests.set", "tests", tests.keys(), {identity(r["test"]) for r in pt})
    for r in pt:
        i = identity(r["test"])
        if i not in tests:
            continue
        s = tests[i]
        t.eq("tests.counts", f"{r['test']} kills", s["kills_count"], int(r["kills"]))
        t.eq("tests.counts", f"{r['test']} unique_kills", s["unique_kills_count"], int(r["unique_kills"]))
        t.eq("tests.counts", f"{r['test']} check_deletions_killed", s["deletions_killed_count"],
             int(r["check_deletions_killed"]))
        t.sets("tests.counts", f"{r['test']} check_deletions_killed_by_this_test_only",
               s["unique_deletion_kills_checks"], r["check_deletions_killed_by_this_test_only"].split())
        t.eq("tests.counts", f"{r['test']} unique_kill_functions (derived)",
             fn_counts([f"{pm[m]['file']}:{pm[m]['function']}" for m in s["unique_kills"]]),
             r["unique_kill_functions"])

    # -- score.json
    score = json.loads(need(first / "score.json").read_text(encoding="utf-8"))
    lib = second["library"]

    def score_block(name: str, item: str, sblock: dict, fblock: dict, group: list[str]) -> None:
        errors = sorted(m for m in group if pm[m]["whole_suite_status"] == "error")
        timeouts = sorted(m for m in group if pm[m]["whole_suite_status"] == "timeout")
        t.eq(name, f"{item} mutants", sblock["total"], fblock["mutants"])
        t.eq(name, f"{item} killed", sblock["killed_by_the_whole_suite"]["count"], fblock["killed"])
        t.eq(name, f"{item} killed_by_a_test", sblock["killed_by_the_whole_suite_by_kind"]["by_a_test"],
             fblock["killed_by_a_test"])
        t.eq(name, f"{item} timeouts", sblock["killed_by_the_whole_suite_by_kind"]["timeout"], fblock["timeouts"])
        t.eq(name, f"{item} errors", sblock["killed_by_the_whole_suite_by_kind"]["error"], fblock["errors"])
        t.eq(name, f"{item} survived", len(sblock["not_killed_by_the_whole_suite"]["ids"]), fblock["survived"])
        t.eq(name, f"{item} score", None if sblock["score"] is None else round(sblock["score"], 6), fblock["score"])
        t.eq(name, f"{item} score_without_errors",
             None if sblock["score_without_error_mutants"] is None else round(sblock["score_without_error_mutants"], 6),
             fblock["score_without_errors"])
        t.sets(name, f"{item} error_mutants (derived)", errors, fblock["error_mutants"])
        t.sets(name, f"{item} timeout_mutants (derived)", timeouts, fblock["timeout_mutants"])

    score_block("score.whole_suite", "whole_suite", lib["tool_mutants"], score["whole_suite"], tool)
    cd = score["check_deletions"]
    score_block("score.check_deletions", "check_deletions", lib["deletions"], cd, dels)
    t.sets("score.check_deletions", "not_killed (checks, derived)",
           [pm[m]["check"] for m in lib["deletions"]["not_killed_by_the_whole_suite"]["ids"]
            if pm[m]["whole_suite_status"] == "completed"], cd["not_killed"])
    t.eq("score.check_deletions", "killed_by_exactly_1_test (derived)",
         sum(1 for m in dels if len(pm[m]["killing_tests"]) == 1), cd["killed_by_exactly_1_test"])
    t.eq("score.check_deletions", "recorder_runs (derived)",
         dict(sorted(Counter(pm[m]["recorder_status"] for m in dels).items())), cd["recorder_runs"])
    t.eq("score.unique", "mutants_killed_by_exactly_1_test",
         sum(v["unique_kills_count"] for v in tests.values()), score["mutants_killed_by_exactly_1_test"])
    t.eq("score.unique", "tests_killing_at_least_1_mutant",
         sum(1 for v in tests.values() if v["kills_count"] > 0), score["tests_killing_at_least_1_mutant"])
    for o in ORACLES + ("suite",):
        t.eq("score.mutant_level_oracles", f"tool mutants {o}",
             second["counts"]["mutant_level_detection_tool_mutants"][o], score["mutant_level_oracles"][o])
        t.eq("score.mutant_level_oracles", f"deletions {o}",
             second["counts"]["mutant_level_detection_deletions"][o], cd["mutant_level_oracles"][o])
    t.eq("score.run_statuses", "recorder_runs",
         dict(sorted(Counter(pm[m]["recorder_status"] for m in tool).items())), score["recorder_runs"])
    t.eq("score.run_statuses", "whole_suite_runs",
         dict(sorted(Counter(pm[m]["whole_suite_status"] for m in tool).items())), score["whole_suite_runs"])
    t.eq("score.cases", "cases", second["counts"]["cases_of_the_study"], score["cases"])
    sc = second["counts"]
    t.eq("counts.totals", "counts.tool_mutants", sc["tool_mutants"], score["whole_suite"]["mutants"])
    t.eq("counts.totals", "counts.deletions", sc["deletions"], cd["mutants"])
    t.eq("counts.totals", "counts.tool_mutants_by_operator", sc["tool_mutants_by_operator"],
         {k: v["mutants"] for k, v in sorted(score["by_operator"].items())})
    t.eq("counts.totals", "counts.tool_mutants_by_file", sc["tool_mutants_by_file"],
         {k: v["mutants"] for k, v in sorted(score["by_file"].items())})
    t.eq("counts.totals", "counts.deletions_by_file (derived)", sc["deletions_by_file"],
         dict(sorted(Counter(r["file"] for r in mcsv.values() if r["operator"] == DELETION).items())))
    statuses: Counter = Counter()
    ncases = second["counts"]["cases_of_the_study"]
    for m in tool:
        st = pm[m]["recorder_status"]
        if st == "completed":
            statuses.update(pm[m]["case_status"])
        elif st == "timeout":
            statuses["time limit"] += ncases
        else:
            statuses["no record"] += ncases
    t.eq("score.case_statuses", "case_statuses (derived)", dict(sorted(statuses.items())), score["case_statuses"])
    for key, field in (("by_file", "file"), ("by_operator", "operator")):
        groups: dict[str, list[str]] = {}
        for m in tool:
            groups.setdefault(pm[m][field], []).append(m)
        t.sets("score.by_file/by_operator", f"{key} keys", groups.keys(), score[key].keys())
        for g in sorted(set(groups) & set(score[key])):
            ms = groups[g]
            f = score[key][g]
            t.eq("score.by_file/by_operator", f"{key} {g} mutants", len(ms), f["mutants"])
            t.eq("score.by_file/by_operator", f"{key} {g} killed", sum(1 for m in ms if pm[m]["killed_by_suite"]),
                 f["killed"])
            t.eq("score.by_file/by_operator", f"{key} {g} killed_by_a_test",
                 sum(1 for m in ms if pm[m]["killing_tests"]), f["killed_by_a_test"])
            t.eq("score.by_file/by_operator", f"{key} {g} errors",
                 sum(1 for m in ms if pm[m]["whole_suite_status"] == "error"), f["errors"])
            t.eq("score.by_file/by_operator", f"{key} {g} timeouts",
                 sum(1 for m in ms if pm[m]["whole_suite_status"] == "timeout"), f["timeouts"])
    if "without_tests" in score:
        w = score["without_tests"]
        sw = lib["tool_mutants"]["killed_without_the_given_tests"]
        t.eq("score.without_tests", "killed", sw["count"], w["killed"])
        t.eq("score.without_tests", "killed_by_a_test",
             sum(1 for m in sw["ids"] if pm[m]["whole_suite_status"] == "completed"), w["killed_by_a_test"])
        t.sets("score.without_tests", "no_longer_killed",
               set(lib["tool_mutants"]["killed_by_the_whole_suite"]["ids"]) - set(sw["ids"]), w["no_longer_killed"])
        t.sets("score.without_tests", "tests_left_out", lib["without_tests"], w["tests_left_out"])
    if "extra_tests" in score:
        x = score["extra_tests"]
        t.eq("score.extra_tests", "digest", digest, x["digest"])
        t.sets("score.extra_tests", "extra tests", lib["extra_tests"], x["extra_tests"])
        t.sets("score.extra_tests", "extra tests passing in both unmodified runs",
               [k for k, v in second["extra_tests"].items() if v["passes_in_both_unmodified_runs"]],
               x["extra_tests_passing_in_both_unmodified_runs"])
        for label, group, sx, fx in (("tool mutants", tool, lib["tool_mutants"], x),
                                     ("deletions", dels, lib["deletions"], x["check_deletions"])):
            added = sx["killed_with_the_extra_tests_added"]
            t.eq("score.extra_tests", f"{label} with_extra_tests killed", added["count"], fx["with_extra_tests"]["killed"])
            newly = set(added["ids"]) - set(sx["killed_by_the_whole_suite"]["ids"])
            fnew = fx["newly_killed"]
            if label == "deletions":
                newly = {pm[m]["check"] for m in newly}
            t.sets("score.extra_tests", f"{label} newly_killed", newly, fnew)
            t.eq("score.extra_tests", f"{label} extra_tests_alone killed_by_a_test (derived)",
                 sum(1 for m in group if pm[m]["killing_extra_tests"]), fx["extra_tests_alone"]["killed_by_a_test"])
        whole_ids = set(lib["tool_mutants"]["killed_by_the_whole_suite"]["ids"])
        for i, rep in enumerate(x.get("replacements", [])):
            old, new = identity(rep["old"]), rep["new"]
            killed = {m for m in tool if pm[m]["whole_suite_status"] != "completed"
                      or (set(pm[m]["killing_tests"]) - {old}) or new in pm[m]["killing_extra_tests"]}
            item = f"replacement {rep['old']} = {rep['new']}"
            t.eq("score.replacement", f"{item} killed (derived)", len(killed), rep["killed"])
            t.sets("score.replacement", f"{item} no_longer_killed (derived)",
                   {m for m in whole_ids if m not in killed and pm[m]["whole_suite_status"] == "completed"},
                   rep["no_longer_killed"])
            t.sets("score.replacement", f"{item} newly_killed (derived)", killed - whole_ids, rep["newly_killed"])
    td = cd.get("toolkit_deletions")
    if td:
        dc = second["input_checks"]["deletions_compared_with_the_toolkit_deposit"]
        t.eq("score.toolkit_deletions", "compared", len(dc), td["compared"])
        t.eq("score.toolkit_deletions", "differences", len(second["input_checks"]["deletions_that_differ_from_the_toolkit_deposit"]),
             len(td["differences"]))
        t.sets("score.toolkit_deletions", "deleted_here_only (derived)",
               {pm[m]["check"] for m in dels} - set(dc), td["deleted_here_only"])

    # -- library values derived from runs.jsonl
    f_suite = {m for m, r in oracles.items() if r["whole_suite_killed"] == "yes"}
    given = [identity(k) for k in (score.get("without_tests") or {}).get("tests_left_out", [])]
    reps = (score.get("extra_tests") or {}).get("replacements", [])
    rep_old, rep_new = [identity(r["old"]) for r in reps], [r["new"] for r in reps]
    all_extra = (score.get("extra_tests") or {}).get("extra_tests", [])
    for label, group in (("tool_mutants", tool), ("deletions", dels)):
        sx = lib[label]
        t.sets("library.derived", f"{label} killed_by_the_whole_suite (oracles.csv)",
               sx["killed_by_the_whole_suite"]["ids"], f_suite & set(group))
        t.sets("library.derived", f"{label} killed_by_the_whole_suite (derived)",
               sx["killed_by_the_whole_suite"]["ids"], f_killed(group))
        t.sets("library.derived", f"{label} not_killed_by_the_whole_suite (derived)",
               sx["not_killed_by_the_whole_suite"]["ids"], set(group) - f_suite)
        if "without_tests" in score:
            t.sets("library.derived", f"{label} killed_without_the_given_tests (derived)",
                   sx["killed_without_the_given_tests"]["ids"], f_killed(group, removed=given))
        else:
            t.skip(f"library.{label}.killed_without_the_given_tests", "score.json has no without_tests")
        if reps:
            t.sets("library.derived", f"{label} killed_with_the_given_replacements, all together (derived)",
                   sx["killed_with_the_given_replacements"]["ids"],
                   f_killed(group, removed=rep_old, added=rep_new))
        else:
            t.skip(f"library.{label}.killed_with_the_given_replacements", "score.json has no replacements")
        if digest:
            t.sets("library.derived", f"{label} killed_with_the_extra_tests_added (derived)",
                   sx["killed_with_the_extra_tests_added"]["ids"], f_killed(group, added=all_extra))
    if "without_tests" in score:
        f_unique_removed = {m for m in tool if f_killers(m)
                            and len({identity(k) for k in f_killers(m)}) == 1
                            and {identity(k) for k in f_killers(m)} <= set(given)}
        t.sets("library.derived", "unique_kills_of_the_removed_tests (derived)",
               lib["unique_kills_of_the_removed_tests"]["ids"], f_unique_removed)
        t.eq("library.derived", "removal_check killed_minus_killed_without_the_given_tests",
             lib["removal_check"]["killed_minus_killed_without_the_given_tests"],
             score["whole_suite"]["killed"] - score["without_tests"]["killed"])
        t.eq("library.derived", "removal_check unique_kills_of_the_removed_tests (derived)",
             lib["removal_check"]["unique_kills_of_the_removed_tests"], len(f_unique_removed))

    # -- rows and cases
    reports: dict[tuple[str, str], dict] = {}
    for kind in ("shadowed", "other_kinds", "comparison"):
        for case, by_desc in second["rows"].get(kind, {}).items():
            for desc, rep in by_desc.items():
                reports.setdefault((case, desc), rep)
    row_cases = sorted({c for c, _ in reports})
    case_rows: dict[tuple[str, str], dict] = {}
    for r in csv.DictReader(io.StringIO(read_xz(need(first / "cases.csv.xz")))):
        if r["case"] in row_cases:
            case_rows[(r["mutant"], r["case"])] = r
    per_case = {r["case"]: r for r in read_csv(need(first / "per-case.csv"))}
    done_cases = set()
    for (case, desc), rep in sorted(reports.items()):
        if case in done_cases or not rep["case_of_the_study"]:
            continue
        done_cases.add(case)
        g = rep["groups"]["tool_mutants_in_all_mutated_files"]
        f_oc = {m for m in tool if case_rows.get((m, case), {}).get("O_C") == "yes"}
        f_os = {m for m in tool if case_rows.get((m, case), {}).get("O_S") == "yes"}
        f_nr = {m for m in tool if case_rows.get((m, case), {}).get("status") == "no record"}
        t.sets("case.detection", f"{case} O_C", g["detected_by_the_case_under_O_C"], f_oc)
        t.sets("case.detection", f"{case} test not passing / O_S",
               g["test_of_the_case_does_not_pass_in_the_recorder_run"], f_os)
        t.sets("case.detection", f"{case} no value / no record", g["recorder_run_without_a_value"], f_nr)
        pc = per_case.get(case)
        if pc is None:
            t.eq("case.per_case", f"{case} present", True, False)
            continue
        t.eq("case.per_case", f"{case} target", rep["target_rule_2"] or "", pc["target"])
        t.eq("case.per_case", f"{case} deciding_check", rep["deciding_check"] or "", pc["deciding_check"])
        t.sets("case.per_case", f"{case} own_test_in_whole_suite", rep["test_whole_suite_keys"],
               pc["own_test_in_whole_suite"].split())
        t.eq("case.per_case", f"{case} O_C_kills", len(g["detected_by_the_case_under_O_C"]), int(pc["O_C_kills"]))
        t.eq("case.per_case", f"{case} O_S_kills / test not passing",
             len(g["test_of_the_case_does_not_pass_in_the_recorder_run"]), int(pc["O_S_kills"]))
        dg = rep["groups"]["tool_mutants_in_the_function_of_the_deciding_check"]
        if pc["O_C_kills_in_deciding_function"] != "":
            t.eq("case.per_case", f"{case} O_C_kills_in_deciding_function",
                 len(dg["detected_by_the_case_under_O_C"]), int(pc["O_C_kills_in_deciding_function"]))
            t.eq("case.per_case", f"{case} O_S_kills_in_deciding_function / test not passing",
                 len(dg["test_of_the_case_does_not_pass_in_the_recorder_run"]),
                 int(pc["O_S_kills_in_deciding_function"]))
        if rep["target_rule_2"] and rep["target_rule_2"] == desc and pc["O_C_kills_in_target_function"] != "":
            tg = rep["groups"]["tool_mutants_in_the_function_of_the_described_check"]
            t.eq("case.per_case", f"{case} O_C_kills_in_target_function",
                 len(tg["detected_by_the_case_under_O_C"]), int(pc["O_C_kills_in_target_function"]))
        t.eq("case.per_case", f"{case} unique_kills", len(g["unique_kills_of_its_test"]), int(pc["unique_kills"]))

    dpath = first / "described-cases.json"
    doc = json.loads(dpath.read_text(encoding="utf-8")) if dpath.exists() else None
    doc_rows = {(e["case"], e["described_check"]): e for e in (doc or {}).get("cases", [])}

    # -- member lists of the 8 groups of each row (first side derived from the raw first outputs)
    def f_group_lists(members: set, case: str, own_keys: set, variant: str | None) -> dict:
        own_ids = {identity(k) for k in own_keys}

        def cr(m):
            return case_rows.get((m, case), {})
        out = {
            "mutants": set(members),
            "killed_by_suite": {m for m in members if m in f_suite},
            "detected_by_the_case_under_O_C": {m for m in members if cr(m).get("O_C") == "yes"},
            "test_of_the_case_does_not_pass_in_the_recorder_run": {m for m in members if cr(m).get("O_S") == "yes"},
            "killed_by_its_test": {m for m in members if f_killers(m) & own_keys},
            "unique_kills_of_its_test": {m for m in members if f_killers(m)
                                         and {identity(k) for k in f_killers(m)} <= own_ids},
            "killed_by_the_variant": None if variant is None else {m for m in members if variant in f_xkills(m)},
            "recorder_run_without_a_value": {m for m in members if cr(m).get("status") == "no record"},
        }
        return out

    # cases.csv rows for the row cases also cover deletions
    for (case, desc), rep in sorted(reports.items()):
        item = f"{case} -> {desc}"
        pc = per_case.get(case)
        if pc is None or not rep["case_of_the_study"]:
            t.skip(f"rows {item}: member lists", "the case is no case of the study in per-case.csv")
            continue
        dec = pc["deciding_check"] or None
        at_desc, at_dec = at_by_check.get(desc, set()), (at_by_check.get(dec, set()) if dec else set())
        f_members = {
            "tool_mutants_at_the_described_check": at_desc,
            "tool_mutants_at_the_deciding_check": at_dec,
            "tool_mutants_at_the_described_and_not_at_the_deciding_check": at_desc - at_dec,
            "tool_mutants_in_the_function_of_the_described_check": first_in_fn(desc),
            "tool_mutants_in_the_function_of_the_deciding_check": first_in_fn(dec),
            "tool_mutants_in_all_mutated_files": set(tool) & set(mcsv),
            "deletion_of_the_described_check": {first_deletion_of[desc]} if desc in first_deletion_of else set(),
            "deletion_of_the_deciding_check": {first_deletion_of[dec]} if dec in first_deletion_of else set(),
        }
        e = doc_rows.get((case, desc))
        variant = e["variant"] if e is not None else None
        own_keys = set(pc["own_test_in_whole_suite"].split())
        for gname, members in f_members.items():
            sg = rep["groups"][gname]
            fl = f_group_lists(members, case, own_keys, variant)
            for lname, fv in fl.items():
                if gname == "tool_mutants_in_all_mutated_files" and lname in (
                        "detected_by_the_case_under_O_C", "test_of_the_case_does_not_pass_in_the_recorder_run",
                        "recorder_run_without_a_value"):
                    continue        # compared under case.detection
                t.opt_sets("row.group_lists", f"{item} | {gname} | {lname} (derived)", sg[lname], fv)

    if doc is not None:
        first_keys = {(e["case"], e["described_check"]) for e in doc["cases"]}
        second_listed = set()
        for kind in ("shadowed", "other_kinds"):
            for case, by_desc in second["rows"].get(kind, {}).items():
                second_listed |= {(case, d) for d in by_desc}
        comp_second = {(c, d) for c, by in second["rows"].get("comparison", {}).items() for d in by}
        # rows of the first outputs come from the cases file; comparison rows there are matched with
        # the derived comparison rows of the second output
        t.sets("row.rows", "(case, described) of the rows",
               {f"{c} -> {d}" for c, d in second_listed | (comp_second & first_keys)},
               {f"{c} -> {d}" for c, d in first_keys})
        suite_killed = {m for m, r in oracles.items() if r["whole_suite_killed"] == "yes"}
        lib_desc = {}
        for k in ("from_shadowed_rows", "from_rows_of_other_kinds"):
            for c, by_v in (lib.get(k) or {}).get("described_checks", {}).items():
                for v, e in by_v.items():
                    lib_desc[(c, v)] = e
        for e in doc["cases"]:
            key = (e["case"], e["described_check"])
            rep = reports.get(key)
            if rep is None:
                continue
            item = f"{e['case']} -> {e['described_check']}"
            for g, sg in GROUP_MAP.items():
                s, f = rep["groups"][sg], e["mutants"][g]
                c = s["counts"]
                t.eq("row.groups", f"{item} {g} mutants", c["mutants"], f["mutants"])
                t.eq("row.groups", f"{item} {g} suite", c["killed_by_suite"], f["suite"])
                t.eq("row.groups", f"{item} {g} O_C", c["detected_by_the_case_under_O_C"], f["O_C"])
                t.eq("row.groups", f"{item} {g} O_S / test not passing",
                     c["test_of_the_case_does_not_pass_in_the_recorder_run"], f["O_S"])
                t.eq("row.groups", f"{item} {g} own", c["killed_by_its_test"], f["own"])
                t.eq("row.groups", f"{item} {g} unique", c["unique_kills_of_its_test"], f["unique"])
                t.sets("row.groups", f"{item} {g} unique_kills", s["unique_kills_of_its_test"], f["unique_kills"])
                t.eq("row.groups", f"{item} {g} variant", c["killed_by_the_variant"], f["variant"])
                t.sets("row.groups", f"{item} {g} variant_kills", s["killed_by_the_variant"] or [], f["variant_kills"])
            for label in ("described", "deciding"):
                s = rep["groups"][f"deletion_of_the_{label}_check"]
                f = e["deletions"][label]
                if f is None or not s["mutants"]:
                    t.eq("row.deletions", f"{item} {label} deletion", s["mutants"] or None,
                         None if f is None else [f["mutant"]])
                    continue
                t.eq("row.deletions", f"{item} {label} id", s["mutants"][0], f["mutant"])
                for a, b in (("killed_by_suite", "suite"), ("detected_by_the_case_under_O_C", "O_C"),
                             ("test_of_the_case_does_not_pass_in_the_recorder_run", "O_S"),
                             ("killed_by_its_test", "own"), ("unique_kills_of_its_test", "unique")):
                    t.eq("row.deletions", f"{item} {label} {b}", bool(s[a]), f[b])
                t.eq("row.deletions", f"{item} {label} variant",
                     None if s["killed_by_the_variant"] is None else bool(s["killed_by_the_variant"]), f["variant"])
            t.eq("row.facts", f"{item} kind", rep["kind"], e["kind"])
            t.eq("row.facts", f"{item} deciding_check", rep["deciding_check"], e["deciding_check"])
            t.eq("row.facts", f"{item} variant", rep["variant"], e["variant"])
            t.sets("row.facts", f"{item} own_test_in_whole_suite", rep["test_whole_suite_keys"],
                   e["own_test_in_whole_suite"])
            t.eq("row.facts", f"{item} described_fires_in_a_baseline_case",
                 rep["described_check_fires_in_a_recorded_case_of_the_baseline"], e["described_fires_in_a_baseline_case"])
            t.eq("row.files", f"{item} described check in mutated files", rep["described_check_in_mutated_files"],
                 e["described_file_mutated"])
            t.eq("row.files", f"{item} deciding check in mutated files", rep["deciding_check_in_mutated_files"],
                 e["deciding_file_mutated"])
            le = lib_desc.get((e["described_check"], e["variant"] or "(no variant)"))
            if le is not None and e["variant"]:
                fv = set(e["mutants"]["described"]["variant_kills"]) - suite_killed
                t.sets("library.described", f"{item} not killed by the suite and killed by the variant",
                       le["not_killed_by_the_suite_and_killed_by_the_variant"], fv)
                dl = e["deletions"]["described"]
                t.eq("library.described", f"{item} deletion killed by the variant",
                     le["deletion_killed_by_the_variant"], None if dl is None else dl["variant"])

        # -- described-cases.csv, cell by cell against described-cases.json
        cpath = first / "described-cases.csv"
        if cpath.exists():
            with cpath.open(encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, [])
                body = list(reader)
            for col in CSV_COLUMNS:
                if col not in header:
                    t.eq("row.csv", f"column {col} present", True, False)
            for col in header:
                if col not in CSV_COLUMNS:
                    t.skip(f"described-cases.csv column {col}", "no counterpart in described-cases.json")
            t.eq("row.csv", "number of rows", len(doc["cases"]), len(body))
            for i, (e, r) in enumerate(zip(doc["cases"], body)):
                if len(r) != len(header):
                    t.eq("row.csv", f"row {i + 1} number of cells", len(header), len(r))
                    continue
                cells = dict(zip(header, r))
                item = f"row {i + 1} ({e['case']} -> {e['described_check']})"
                t.eq("row.csv", f"{item} (case, described_check)", (e["case"], e["described_check"]),
                     (cells.get("case"), cells.get("described_check")))
                for col, get in CSV_COLUMNS.items():
                    if col in cells and col not in ("case", "described_check"):
                        t.eq("row.csv", f"{item} {col}", get(e), cells[col])
        else:
            t.skip("described-cases.csv", "missing in the first output folder")

        # -- library values from the rows of the cases file (first side derived from described-cases.json rows)
        for lkey, pick in (("from_shadowed_rows", kind_is_shadowed),
                           ("from_rows_of_other_kinds", lambda k: not kind_is_shadowed(k) and k != "comparison")):
            sl = lib.get(lkey)
            frows = [e for e in doc["cases"] if pick(e["kind"])]
            if sl is None and not frows:
                continue
            if sl is None:
                # the second script writes from_rows_of_other_kinds only when such rows exist
                t.eq("library.derived", f"{lkey} present", False, True)
                continue
            # with no row on the first side the derived values are those of the whole suite
            ftests = {identity(k) for e in frows for k in e["own_test_in_whole_suite"]}
            frepl = sorted({(identity(k), e["variant"]) for e in frows if e["variant"]
                            for k in e["own_test_in_whole_suite"]})
            t.sets("library.derived", f"{lkey} tests_that_hold_a_row",
                   [x["test"] for x in sl["tests_that_hold_a_row"]], ftests)
            t.sets("library.derived", f"{lkey} replacements",
                   [f"{x['test']} = {x['variant']}" for x in sl["replacements"]], [f"{a} = {b}" for a, b in frepl])
            for label, group in (("tool_mutants", tool), ("deletions", dels)):
                b = sl[label]
                t.eq("library.derived", f"{lkey} {label} killed_by_the_whole_suite",
                     b["killed_by_the_whole_suite"], len(f_suite & set(group)))
                t.sets("library.derived", f"{lkey} {label} killed_without_the_tests_that_hold_a_row (derived)",
                       b["killed_without_the_tests_that_hold_a_row"]["ids"], f_killed(group, removed=ftests))
                t.sets("library.derived",
                       f"{lkey} {label} killed_with_each_such_test_replaced_by_its_variant (derived)",
                       b["killed_with_each_such_test_replaced_by_its_variant"]["ids"],
                       f_killed(group, removed=[a for a, _ in frepl], added=[v for _, v in frepl]))
            if lkey == "from_shadowed_rows" and "without_tests" in score and set(given) == ftests:
                t.eq("library.derived", f"{lkey} tool_mutants killed_without_the_tests_that_hold_a_row "
                     "(score.json without_tests)", sl["tool_mutants"]["killed_without_the_tests_that_hold_a_row"]
                     ["count"], score["without_tests"]["killed"])

        # -- expectations (shadowed rows only)
        def status(units: int, ok: bool) -> str:
            return "not applicable" if units == 0 else ("held" if ok else "not held")

        kinds_of: dict[str, set] = {}
        for e in doc["cases"]:
            kinds_of.setdefault(e["case"], set()).add(e["kind"])

        def f_shadowed(case: str) -> bool:
            k = kinds_of.get(case, set())
            return bool(k) and all(kind_is_shadowed(x) for x in k)

        other = second.get("expectations_over_rows_of_other_kinds")
        if other:
            for mname in ("M1", "M2", "M3"):
                t.skip(f"second expectations_over_rows_of_other_kinds.{mname} ({other[mname]['units']} rows, "
                       f"status {other[mname]['status']})", NO_EXPECTATION)
        sx = second.get("expectations") or {}

        def by_case(rows: dict) -> tuple[dict, dict]:
            out, desc = {}, {}
            for k, v in rows.items():
                c, d = k.split(" -> ", 1)
                out[c], desc[c] = v, d
            return out, desc

        s_m1, s_desc = by_case(sx["M1"]["rows"]) if sx else ({}, {})
        s_m2, _ = by_case(sx["M2"]["rows"]) if sx else ({}, {})
        s_m3, _ = by_case(sx["M3"]["rows"]) if sx else ({}, {})
        s_units = {mname: (sx[mname]["units"] if sx else 0) for mname in ("M1", "M2", "M3")}
        ebr = doc.get("expectations_by_reading")
        if ebr is None:
            t.skip("described-cases.json expectations_by_reading (both readings)",
                   "the first output was written before the key existed; only the key 'expectations' is present")
            old = doc.get("expectations") or {}
            old_cases = set(old.get("M1_cases", {})) | {r["case"] for r in old.get("M3_variants", [])}
            for c in sorted(x for x in old_cases if not f_shadowed(x)):
                t.skip(f"first expectations, row {c} (kind {', '.join(sorted(kinds_of.get(c, {'?'})))})",
                       NO_EXPECTATION)
            if s_units["M1"] == 0 and not any(f_shadowed(c) for c in old_cases):
                for mname in ("M1", "M2", "M3"):
                    t.skip(f"status of {mname}", NO_EXPECTATION + " (no row of a shadowed kind on either side)")
            elif any(f_shadowed(c) for c in old_cases) or s_units["M1"]:
                # the key 'expectations' counts deletions as mutants (reading tool_mutants_and_deletions)
                for c in sorted(set(s_m1) | {x for x in old.get("M1_cases", {}) if f_shadowed(x)}):
                    s = s_m1.get(c)
                    sv = None if s is None else (len(s["unique_kills_of_its_test_at_the_deciding_check"])
                                                 + int(bool(s["deletion_of_the_deciding_check_is_a_unique_kill_of_its_test"])))
                    t.eq("expect.TD.result", f"{c} M1 value (key 'expectations')", sv, old.get("M1_cases", {}).get(c))
                f3 = {r["case"]: r["holds"] for r in old.get("M3_variants", []) if f_shadowed(r["case"])}
                for c in sorted(set(s_m3) | set(f3)):
                    s = s_m3.get(c)
                    hv = None
                    if s is not None:
                        flag = int(bool(s["variant_kills_the_deletion_of_the_described_check"]))
                        applies = "second_part" not in s
                        sh = (not s["whole_suite_kills_the_deletion"] and bool(s["suite_with_the_variant_kills_the_deletion"])) \
                            if applies else None
                        hv = (len(s["variant_kills_at_the_described_check"]) + flag >= 1) and (sh if applies else True)
                    t.eq("expect.TD.result", f"{c} M3 holds (key 'expectations')", hv, f3.get(c))
        else:
            T, TD = ebr["tool_mutants"], ebr["tool_mutants_and_deletions"]
            all_first = (set(T["M1"]["unique_kills_at_the_deciding_check"])
                         | set(T["M2"]["O_C_detections_at_the_described_check_only"])
                         | {r["case"] for r in T["M3"]["rows"]})
            for c in sorted(x for x in all_first if not f_shadowed(x)):
                t.skip(f"first expectations_by_reading, row {c} (kind {', '.join(sorted(kinds_of.get(c, {'?'})))})",
                       NO_EXPECTATION)
            f_m1 = {c: v for c, v in T["M1"]["unique_kills_at_the_deciding_check"].items() if f_shadowed(c)}
            f_m1td = TD["M1"]["unique_kills_at_the_deciding_check"]
            f_m2 = {c: v for c, v in T["M2"]["O_C_detections_at_the_described_check_only"].items() if f_shadowed(c)}
            f_m2td = TD["M2"]["O_C_detections_at_the_described_check_only"]
            f_m3 = {r["case"]: r for r in T["M3"]["rows"] if f_shadowed(r["case"])}
            f_m3td = {r["case"]: r for r in TD["M3"]["rows"]}
            t.sets("expect.rows", "M1 rows (cases)", s_m1.keys(), f_m1.keys())
            t.sets("expect.rows", "M2 rows (cases)", s_m2.keys(), f_m2.keys())
            t.sets("expect.rows", "M3 rows (cases)", s_m3.keys(), f_m3.keys())
            shadow_tests = {e["test"] for e in doc["cases"] if f_shadowed(e["case"])}

            def doc_row(c: str) -> dict:
                return doc_rows.get((c, s_desc.get(c)), {})

            # M1
            td1 = {}
            for c in sorted(set(s_m1) & set(f_m1)):
                s, e = s_m1[c], doc_row(c)
                u = s["unique_kills_of_its_test_at_the_deciding_check"]
                flag = int(bool(s["deletion_of_the_deciding_check_is_a_unique_kill_of_its_test"]))
                td1[c] = len(u) + flag
                t.eq("expect.T.M1", f"{c} unique kills at the deciding check", len(u), f_m1[c])
                t.sets("expect.T.M1", f"{c} unique kills at the deciding check (members)", u,
                       (e.get("mutants") or {}).get("deciding", {}).get("unique_kills"))
                t.eq("expect.T.M1", f"{c} tool mutants at the deciding check", s["tool_mutants_at_the_deciding_check"],
                     (e.get("mutants") or {}).get("deciding", {}).get("mutants"))
                t.eq("expect.TD.deletion", f"{c} M1 deletion of the deciding check is a unique kill", flag,
                     f_m1td.get(c, 0) - f_m1[c])
                t.eq("expect.TD.result", f"{c} M1 value", td1[c], f_m1td.get(c))
            t.sets("expect.T.M1", "tests with at least 1",
                   {doc_row(c).get("test") for c, v in s_m1.items() if v["unique_kills_of_its_test_at_the_deciding_check"]},
                   set(T["M1"]["tests_with_at_least_1"]) & shadow_tests)
            t.sets("expect.TD.result", "M1 tests with at least 1",
                   {doc_row(c).get("test") for c, v in td1.items() if v >= 1},
                   set(TD["M1"]["tests_with_at_least_1"]) & shadow_tests)
            # M2
            td2 = {}
            for c in sorted(set(s_m2) & set(f_m2)):
                s, e = s_m2[c], doc_row(c)
                lst = s["detected_under_O_C_at_the_described_and_not_at_the_deciding_check"]
                flag = int(bool(s["deletion_of_the_described_check_detected_under_O_C"]))
                td2[c] = len(lst) + flag
                desc = s_desc[c]
                dec = e.get("deciding_check")
                only = at_by_check.get(desc, set()) - (at_by_check.get(dec, set()) if dec else set())
                t.eq("expect.T.M2", f"{c} O_C detections at the described check only", len(lst), f_m2[c])
                t.sets("expect.T.M2", f"{c} O_C detections at the described check only (members, derived)", lst,
                       {m for m in only if case_rows.get((m, c), {}).get("O_C") == "yes"})
                t.sets("expect.T.M2", f"{c} recorder runs without a value (members, derived)",
                       s["recorder_runs_without_a_value"],
                       {m for m in only if case_rows.get((m, c), {}).get("status") == "no record"})
                t.eq("expect.T.M2", f"{c} tool mutants at the described and not at the deciding check",
                     s["tool_mutants_at_the_described_and_not_at_the_deciding_check"],
                     (e.get("mutants") or {}).get("described_not_deciding", {}).get("mutants"))
                t.eq("expect.TD.deletion", f"{c} M2 deletion of the described check detected under O_C", flag,
                     f_m2td.get(c, 0) - f_m2[c])
                t.eq("expect.TD.result", f"{c} M2 value", td2[c], f_m2td.get(c))
            t.sets("expect.T.M2", "rows with such a detection (cases)",
                   {k.split(" -> ", 1)[0] for k in sx["M2"]["rows_with_such_a_detection"]} if sx else set(),
                   {c for c in T["M2"]["cases_with_at_least_1"] if f_shadowed(c)})
            t.sets("expect.TD.result", "M2 cases with at least 1", {c for c, v in td2.items() if v >= 1},
                   {c for c in TD["M2"]["cases_with_at_least_1"] if f_shadowed(c)})
            # M3
            td3 = {}
            for c in sorted(set(s_m3) & set(f_m3)):
                s, f, ftd, e = s_m3[c], f_m3[c], f_m3td.get(c, {}), doc_row(c)
                vk = s["variant_kills_at_the_described_check"]
                flag = int(bool(s["variant_kills_the_deletion_of_the_described_check"]))
                applies = "second_part" not in s
                sh = (not s["whole_suite_kills_the_deletion"] and bool(s["suite_with_the_variant_kills_the_deletion"])) \
                    if applies else None
                td3[c] = (len(vk) + flag >= 1) and (sh if applies else True)
                dl = (e.get("deletions") or {}).get("described")
                t.eq("expect.T.M3", f"{c} variant kills at the described check", len(vk),
                     f["variant_kills_at_the_described_check"])
                t.sets("expect.T.M3", f"{c} variant kills at the described check (members)", vk,
                       (e.get("mutants") or {}).get("described", {}).get("variant_kills"))
                t.eq("expect.T.M3", f"{c} first part holds", len(vk) >= 1, f["first_sentence_holds"])
                t.eq("expect.T.M3", f"{c} second part applies", applies, f["second_sentence_applies"])
                t.eq("expect.T.M3", f"{c} second part holds", sh, f["second_sentence_holds"])
                t.eq("expect.T.M3", f"{c} holds for this row", s["holds_for_this_row"], f["holds"])
                t.eq("expect.T.M3", f"{c} tool mutants at the described check", s["tool_mutants_at_the_described_check"],
                     (e.get("mutants") or {}).get("described", {}).get("mutants"))
                t.eq("expect.T.M3", f"{c} described check fires in a recorded case of the baseline",
                     s["described_check_fires_in_a_recorded_case_of_the_baseline"],
                     e.get("described_fires_in_a_baseline_case"))
                if applies:
                    t.eq("expect.T.M3", f"{c} whole suite kills the deletion", s["whole_suite_kills_the_deletion"],
                         None if dl is None else dl["suite"])
                    t.eq("expect.T.M3", f"{c} suite with the variant kills the deletion",
                         s["suite_with_the_variant_kills_the_deletion"],
                         None if dl is None else bool(dl["suite"] or dl["variant"]))
                t.eq("expect.TD.deletion", f"{c} M3 variant kills the deletion of the described check", flag,
                     ftd.get("variant_kills_at_the_described_check", 0) - f["variant_kills_at_the_described_check"])
                t.eq("expect.TD.result", f"{c} M3 variant kills", len(vk) + flag,
                     ftd.get("variant_kills_at_the_described_check"))
                t.eq("expect.TD.result", f"{c} M3 holds", td3[c], ftd.get("holds"))
            # statuses
            for mname, f_rows in (("M1", f_m1), ("M2", f_m2), ("M3", f_m3)):
                n_other = len([c for c in all_first if not f_shadowed(c)])
                if s_units[mname] == 0 and not f_rows:
                    t.skip(f"status of {mname}", NO_EXPECTATION + " (no row of a shadowed kind on either side)")
                    continue
                note = "" if n_other == 0 else " (the first status also covers rows of other kinds)"
                t.eq("expect.T.status", f"{mname}{note}", sx[mname]["status"] if sx else None, T[mname]["status"])
            if s_units["M1"] or f_m1:
                t.eq("expect.TD.result", "M1 status (derived)", status(s_units["M1"], any(v >= 1 for v in td1.values())),
                     TD["M1"]["status"])
                t.eq("expect.TD.result", "M2 status (derived)", status(s_units["M2"], not any(v >= 1 for v in td2.values())),
                     TD["M2"]["status"])
                t.eq("expect.TD.result", "M3 status (derived)", status(s_units["M3"], all(td3.values())),
                     TD["M3"]["status"])
            # the key 'expectations' against the member tool_mutants_and_deletions
            key = doc.get("expectations")
            if key is None:
                t.skip("described-cases.json expectations", "the key is missing in the first output")
            else:
                exp = {
                    "M1_tests_with_a_unique_kill_at_the_deciding_check": TD["M1"]["tests_with_at_least_1"],
                    "M1_cases": TD["M1"]["unique_kills_at_the_deciding_check"],
                    "M2_cases_that_detect_a_mutant_at_the_described_check_only": TD["M2"]["cases_with_at_least_1"],
                    "M3_variants": [{"case": r["case"], "holds": r["holds"]} for r in TD["M3"]["rows"]],
                }
                t.sets("expect.key", "fields of the key", exp.keys(), key.keys())
                for fld in ("M1_tests_with_a_unique_kill_at_the_deciding_check",
                            "M2_cases_that_detect_a_mutant_at_the_described_check_only"):
                    t.eq("expect.key", fld, exp[fld], key.get(fld))
                k1 = key.get("M1_cases") or {}
                t.sets("expect.key", "M1_cases (cases)", exp["M1_cases"].keys(), k1.keys())
                for c in sorted(set(exp["M1_cases"]) & set(k1)):
                    t.eq("expect.key", f"M1_cases {c}", exp["M1_cases"][c], k1[c])
                k3 = key.get("M3_variants") or []
                t.eq("expect.key", "M3_variants (cases, in order)", [r["case"] for r in exp["M3_variants"]],
                     [r.get("case") for r in k3])
                f3 = {r.get("case"): r.get("holds") for r in k3}
                for r in exp["M3_variants"]:
                    if r["case"] in f3:
                        t.eq("expect.key", f"M3_variants {r['case']} holds", r["holds"], f3[r["case"]])
    else:
        t.skip("described-cases.json", "missing in the first output folder")

    # -- comparison cases and shadowed rows of the cases file
    if cases_tsv is not None and cases_tsv.exists():
        with cases_tsv.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        t.sets("comparison_cases", "comparison cases", second["cases_file"]["comparison_cases_derived"],
               {r["case"] for r in rows if r["kind"] == "comparison"})

        def resolved(r: dict) -> str:
            e = doc_rows.get((r["case"], r["described"]))
            return (e["variant"] if e is not None else r["variant"]) or ""
        t.sets("shadowed_rows", "shadowed rows (case, described, kind, variant)",
               {f"{r['case']} | {r['described']} | {r['kind']} | {r['variant'] or ''}"
                for r in second["cases_file"]["shadowed_rows"]},
               {f"{r['case']} | {r['described']} | {r['kind']} | {resolved(r)}"
                for r in rows if kind_is_shadowed(r["kind"])})
    else:
        t.skip("comparison cases and shadowed rows of the cases file", "no cases.tsv in the first output folder")
    for what, why in STATIC_NOT_COMPARED:
        t.skip(what, why)
    return t


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--second", required=True)
    ap.add_argument("--first", required=True)
    ap.add_argument("--cases")
    ap.add_argument("--summary", help="optional JSON file for the counts per comparison name")
    a = ap.parse_args(argv)
    try:
        second = json.loads(need(Path(a.second)).read_text(encoding="utf-8"))
        first = need(Path(a.first))
        cases = Path(a.cases) if a.cases else (first / "cases.tsv")
        t = compare(second, first, cases if cases.exists() else None)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        print(f"compare_mutants: malformed input: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    differ = len(t.differences)
    failed = len(t.internal_failures)
    print(f"compared {t.compared}, agree {t.compared - differ}, differ {differ}")
    for name in MAP:
        if t.by_name[name]:
            print(f"  {name}: compared {t.by_name[name]}, differ {t.differ_by_name[name]}")
    print(f"internal checks of the second output (list length equals its count): checked {t.internal_checked}, "
          f"failed {failed}")
    print(f"not compared: {len(t.not_compared)}")
    for what, why in t.not_compared:
        print(f"NOT COMPARED {what} | {why}")
    for where, length, count in t.internal_failures:
        print(f"INTERNAL {where} | length {length} | count {count}")
    for name, item, s, f in t.differences:
        print(f"DIFF {name} | {item} | second: {json.dumps(s, sort_keys=True)} | first: {json.dumps(f, sort_keys=True)}")
    if a.summary:
        Path(a.summary).write_text(json.dumps(
            {"compared": t.compared, "agree": t.compared - differ, "differ": differ,
             "by_name": {n: {"compared": t.by_name[n], "differ": t.differ_by_name[n]} for n in MAP if t.by_name[n]},
             "internal_checked": t.internal_checked, "internal_failed": failed,
             "not_compared": [{"what": w, "why": y} for w, y in t.not_compared]},
            indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if differ or failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
