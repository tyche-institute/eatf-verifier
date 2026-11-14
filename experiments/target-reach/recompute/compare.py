"""Compares the output of recompute/second.py with generated/<name>/summary.json.

    python3 -I -B recompute/compare.py --second recompute/out/<name>/second.json \
        --first generated/<name>/summary.json

The table MAP names, for each compared count, where it stands in the second
output and where the same count stands in the first. A place is a path of
keys, or a small function of the file where the first output keeps the count
in another shape (for example the deletions of checks that fire and never
decide, which the first output gives as all deletions minus the deletions of
deciding checks). The script prints 1 line per count, lists the counts of
either file that the table does not compare, and exits with 1 when any
compared count differs.
"""

from __future__ import annotations

import argparse
import json
import sys

MISSING = object()


class Doc:
    """A JSON document that remembers which leaves were read."""

    def __init__(self, data) -> None:
        self.data = data
        self.used: set[tuple] = set()

    def get(self, *path, default=MISSING):
        x = self.data
        for k in path:
            if isinstance(x, dict) and k in x:
                x = x[k]
            elif isinstance(x, list) and isinstance(k, int) and -len(x) <= k < len(x):
                x = x[k]
            else:
                if default is MISSING:
                    return MISSING
                self.used.add(tuple(path))
                return default
        self.used.add(tuple(path))
        return x

    def leaves(self, x=None, path=()):
        x = self.data if x is None and not path else x
        if isinstance(x, dict) and x:
            for k, v in x.items():
                yield from self.leaves(v, path + (k,))
        else:
            yield path

    def unused(self) -> list[tuple]:
        out = []
        for p in self.leaves():
            if not any(p[:len(u)] == u or u[:len(p)] == p for u in self.used):
                out.append(p)
        return out


def n(x):
    """A list compared by its length where the other file gives a number."""
    return len(x) if isinstance(x, list) else x


def srt(x):
    return sorted(x) if isinstance(x, list) else x


ORACLE_FIRST = {"O_V": "O_V", "O_Vfc": "O_Vfc", "O_C": "O_C", "O_T": "O_T", "O_S": "O_S",
                "suite": "suite", "whole_suite": "whole suite"}
INCLUSIONS = {"O_Vfc_without_O_V": "O_Vfc within O_V", "O_V_without_O_C": "O_V within O_C",
              "O_V_without_O_S": "O_V within O_S", "O_S_without_suite": "O_S within suite",
              "suite_without_whole_suite": "suite within whole suite"}
OUTCOMES = {"the target decides the case": "decided by the target",
            "the target fires and another check decides": "the target fires and another check decides",
            "the target fires and no check decides": "the target fires and no check decides",
            "the target does not fire": "the target does not fire"}
SENTINELS = 7


def own_test_without_target(f: Doc, what: str):
    """The first output gives the own test on the copy without the target per
    outcome; the sum over the outcomes."""
    by = f.get("counts", "cases_with_target_by_outcome", default={})
    return sum(v for k, v in by.items() if k.endswith(f"; own test without the target: {what}"))


def MAP(s: Doc, f: Doc) -> list[tuple[str, object, object]]:
    rows = []

    def row(label, a, b):
        rows.append((label, a, b))

    # checks and blocks
    row("checks", s.get("definitions", "checks_all"), f.get("counts", "checks"))
    row("checks in subject files", s.get("definitions", "checks_in_subject_files"),
        f.get("counts", "checks_in_subject_files"))
    row("reachable checks", s.get("definitions", "reachable_checks_all"), f.get("counts", "checks_reachable"))
    row("blocks (test files of the recorder runs)", s.get("definitions", "blocks_in_test_files_of_the_recorder_runs"),
        f.get("counts", "blocks"))
    row("included blocks", s.get("definitions", "included_blocks"), f.get("counts", "included_blocks"))
    row("class-only included blocks", s.get("definitions", "class_only_included_blocks"),
        f.get("counts", "included_blocks_class_only"))
    row("included blocks with a target", s.get("definitions", "included_blocks_with_a_target"),
        f.get("counts", "included_blocks_with_target"))
    # cases
    row("recorded executions of included blocks", s.get("cases", "recorded_executions_of_included_blocks"),
        f.get("counts", "cases_of_included_blocks"))
    row("cases of the study", s.get("cases", "cases_of_the_study"), f.get("counts", "cases"))
    row("cases left out", s.get("cases", "cases_left_out"), f.get("counts", "cases_left_out"))
    lo_s, lo_f = s.get("cases", "cases_left_out_by_reason"), f.get("counts", "cases_left_out_by_reason")
    row("cases left out, values by reason (sorted)", sorted(lo_s.values()) if isinstance(lo_s, dict) else lo_s,
        sorted(lo_f.values()) if isinstance(lo_f, dict) else lo_f)
    ids = s.get("cases", "cases_left_out_ids")
    row("cases left out, number of identifiers",
        sum(len(v) for v in ids.values()) if isinstance(ids, dict) else ids, n(f.get("lists", "cases_left_out")))
    row("cases decided by a check", s.get("cases", "cases_of_the_study_decided_by_a_check"),
        f.get("counts", "cases_by_site_kind", "check", default=0))
    nd_s = s.get("cases", "cases_of_the_study_decided_by_no_check")
    by_kind = f.get("counts", "cases_by_site_kind", default={})
    row("cases decided by no check", nd_s, sum(v for k, v in by_kind.items() if k != "check"))
    row("fired checks recorded", s.get("cases", "fired_checks_recorded"), f.get("counts", "fired_recorded"))
    # checks at run time
    row("deciding checks", s.get("checks_at_run_time", "deciding_checks_all"), f.get("counts", "checks_deciding"))
    row("deciding checks in subject files", s.get("checks_at_run_time", "deciding_checks_in_subject_files"),
        f.get("counts", "checks_deciding_in_subject_files"))
    row("checks that fire", s.get("checks_at_run_time", "checks_that_fire_all"), f.get("counts", "checks_firing"))
    row("checks that fire and never decide", s.get("checks_at_run_time", "checks_that_fire_and_never_decide_all"),
        f.get("counts", "checks_firing_and_never_deciding"))
    # Q1
    row("Q1 cases with a target", s.get("Q1", "cases_with_a_target"), f.get("counts", "cases_with_target"))
    for tier in ("assertion", "name"):
        row(f"Q1 cases with a target, {tier} tier", s.get("Q1", "cases_with_a_target_by_tier", tier, default=0),
            f.get("counts", "cases_with_target_by_tier", tier, default=0))
    for mine, theirs in OUTCOMES.items():
        row(f"Q1 outcome: {mine}", s.get("Q1", "outcomes", mine),
            f.get("counts", "cases_with_target_by_outcome", theirs, default=0))
    row("Q1 outcome: not decided by the target (no fired checks)",
        s.get("Q1", "outcomes", "not decided by the target"),
        f.get("counts", "cases_with_target_by_outcome", "not decided by the target", default=0))
    row("Q1 cases the target decides", s.get("Q1", "outcomes", "the target decides the case"),
        f.get("counts", "cases_reaching_target"))
    o = s.get("Q1", "outcomes")
    row("Q1 cases in which the target fires (decides or fires)",
        o["the target decides the case"] + o["the target fires and another check decides"]
        + o["the target fires and no check decides"], f.get("counts", "cases_target_fires"))
    row("Q1 flags", s.get("Q1", "flags"), f.get("counts", "flags"))
    for tier in ("assertion", "name"):
        row(f"Q1 flags, {tier} tier", s.get("Q1", "flags_by_tier", tier, default=0),
            f.get("counts", "flags_by_tier", tier, default=0))
    row("Q1 flags whose target fires", o["the target fires and another check decides"]
        + o["the target fires and no check decides"], f.get("counts", "flags_target_fires"))
    # Q2
    row("Q2 deletions", s.get("Q2", "deletions"), f.get("counts", "deletions"))
    row("Q2 deletions of deciding checks", s.get("Q2", "deletions_of_deciding_checks"),
        f.get("counts", "deletions_of_deciding_checks"))
    row("Q2 deletions of checks that fire and never decide",
        s.get("Q2", "deletions_of_checks_that_fire_and_never_decide"),
        f.get("counts", "deletions_of_checks_that_fire_and_never_decide"))
    nfd = f.get("lists", "deletions_of_checks_that_fire_and_never_decide")
    pd = s.get("Q2", "per_deletion")
    row("Q2 deletions of checks that fire and never decide, identifiers",
        sorted(d for d, v in pd.items() if v["role"] != "deciding"), srt(nfd))
    for mine, theirs in ORACLE_FIRST.items():
        a = s.get("Q2", "not_detected_deciding_checks", mine)
        b = f.get("counts", "deletions_not_detected_of_deciding_checks", theirs)
        row(f"Q2 not detected, deciding checks, {mine}", a, b)
        a2 = s.get("Q2", "not_detected_checks_that_fire_and_never_decide", mine)
        tot = f.get("counts", "deletions_not_detected", theirs)
        row(f"Q2 not detected, checks that fire and never decide, {mine} (first: all minus deciding)", a2,
            tot - b if isinstance(tot, int) and isinstance(b, int) else MISSING)
        ids_s = sorted(s.get("Q2", "not_detected_deciding_checks_ids", mine)
                       + s.get("Q2", "not_detected_checks_that_fire_and_never_decide_ids", mine))
        row(f"Q2 not detected, all deletions, {mine}, identifiers", ids_s,
            srt(f.get("lists", "deletions_not_detected", theirs)))
    for mine in ("O_V", "O_Vfc", "O_C", "O_T"):
        a = s.get("Q2", "not_detected_deciding_checks_withheld_as_failing", mine)
        b = f.get("counts", "deletions_not_detected_withheld_as_failing_of_deciding_checks", mine)
        row(f"Q2 withheld as failing, not detected, deciding checks, {mine}", a, b)
        tot = f.get("counts", "deletions_not_detected_withheld_as_failing", mine)
        row(f"Q2 withheld as failing, not detected, checks that fire and never decide, {mine} (first: all minus deciding)",
            s.get("Q2", "not_detected_checks_that_fire_and_never_decide_withheld_as_failing", mine),
            tot - b if isinstance(tot, int) and isinstance(b, int) else MISSING)
        ids_s = sorted(s.get("Q2", "not_detected_deciding_checks_withheld_as_failing_ids", mine)
                       + s.get("Q2", "not_detected_checks_that_fire_and_never_decide_withheld_as_failing_ids", mine))
        row(f"Q2 withheld as failing, not detected, all deletions, {mine}, identifiers", ids_s,
            srt(f.get("lists", "deletions_not_detected_withheld_as_failing", mine)))
    row("Q2 deletions that exceeded the time limit 2 times", n(s.get("Q2", "deletions_time_limit_exceeded_twice")),
        f.get("counts", "deletions_time_limit"))
    row("Q2 deletions that exceeded the time limit, identifiers", s.get("Q2", "deletions_time_limit_exceeded_twice"),
        srt(f.get("lists", "deletions_time_limit")))
    row("Q2 recorder runs repeated", n(s.get("Q2", "recorder_runs_repeated")), f.get("counts", "deletion_runs_repeated"))
    row("Q2 recorder runs repeated, identifiers", s.get("Q2", "recorder_runs_repeated"),
        srt(f.get("lists", "deletion_runs_repeated")))
    row("Q2 recorder runs without a record", n(s.get("Q2", "recorder_runs_without_a_record")),
        f.get("counts", "deletions_without_record"))
    row("Q2 recorder runs without a record, identifiers", s.get("Q2", "recorder_runs_without_a_record"),
        srt(f.get("lists", "deletions_without_record")))
    row("Q2 whole-suite runs repeated", s.get("Q2", "whole_suite_runs_repeated"),
        srt(f.get("whole_suite", "runs_repeated")))
    wn, wt = f.get("whole_suite", "deletions_no_result"), f.get("whole_suite", "deletions_time_limit")
    row("Q2 whole-suite runs without a result (time limit or no result file)",
        s.get("Q2", "whole_suite_runs_without_a_result"),
        sorted(set(wn) | set(wt)) if isinstance(wn, list) and isinstance(wt, list) else MISSING)
    row("Q2 whole-suite runs that exceeded the time limit (final run), identifiers",
        s.get("Q2", "whole_suite_final_runs_that_exceeded_the_time_limit"), srt(wt))
    row("Q2 whole-suite runs without a result file (final run), identifiers",
        s.get("Q2", "whole_suite_final_runs_without_a_result_file"), srt(wn))
    for mine, theirs in INCLUSIONS.items():
        row(f"Q2 inclusion broken: {mine}", s.get("Q2", "inclusion_breaks_counts", mine),
            f.get("counts", "deletions_breaking_an_inclusion", theirs))
        row(f"Q2 inclusion broken: {mine}, identifiers", s.get("Q2", "inclusion_breaks", mine),
            srt(f.get("lists", "deletions_breaking_an_inclusion", theirs)))
    wf = f.get("witnesses", default={})
    row("Q2 witness files", s.get("Q2", "witness_files_count"), len(wf))
    row("Q2 witness files that hold", s.get("Q2", "witness_files_hold"),
        sum(1 for v in wf.values() if v.get("holds")))
    for name in sorted(set(s.get("Q2", "witness_files")) | set(wf)):
        row(f"Q2 witness {name}: check", s.get("Q2", "witness_files", name, "check"),
            f.get("witnesses", name, "check"))
        row(f"Q2 witness {name}: holds", s.get("Q2", "witness_files", name, "holds"),
            f.get("witnesses", name, "holds"))
    # Q3
    p = "pinning_without_the_deciding_check"
    tab = s.get("Q3", p, "own_test_by_kind_of_block")
    row("Q3 pinning: cases counted", s.get("Q3", p, "counted"), f.get("counts", "pinning", "cases"))
    row("Q3 pinning: class-only cases", tab["class-only"]["fails"] + tab["class-only"]["passes"],
        f.get("counts", "pinning", "class_only", "cases"))
    row("Q3 pinning: class-only cases whose test passes", tab["class-only"]["passes"],
        f.get("counts", "pinning", "class_only", "test_passes"))
    row("Q3 pinning: cases of blocks that assert more", tab["asserts more"]["fails"] + tab["asserts more"]["passes"],
        f.get("counts", "pinning", "message", "cases"))
    row("Q3 pinning: cases of blocks that assert more whose test passes", tab["asserts more"]["passes"],
        f.get("counts", "pinning", "message", "test_passes"))
    row("Q3 pinning: test fails", tab["class-only"]["fails"] + tab["asserts more"]["fails"],
        f.get("counts", "pinning", "test_fails"))
    row("Q3 pinning: test passes", tab["class-only"]["passes"] + tab["asserts more"]["passes"],
        f.get("counts", "pinning", "test_passes"))
    nc = s.get("Q3", p, "not_counted_by_reason")
    row("Q3 pinning: not counted, no deciding check", nc.get("no check decides the case", 0),
        f.get("counts", "pinning", "cases_not_counted_no_deciding_check"))
    row("Q3 pinning: not counted, deciding check not deleted",
        nc.get("the deciding check lies outside the subject files", 0)
        + nc.get("the deciding check fires in no case of the study", 0),
        f.get("counts", "pinning", "cases_not_counted_deciding_check_not_deleted"))
    row("Q3 pinning: not counted, time limit", nc.get("the deletion run exceeded the time limit", 0),
        f.get("counts", "pinning", "cases_not_counted_time_limit"))
    row("Q3 pinning: not counted, no record", nc.get("the deletion run gave no record", 0),
        f.get("counts", "pinning", "cases_not_counted_no_record"))
    passes_by = s.get("Q3", p, "when_the_own_test_passes_the_case")
    row("Q3 pinning: test passes, number described by what the case does",
        sum(sum(v.values()) for v in passes_by.values()),
        sum(f.get("counts", "pinning", "test_passes_by_what_the_case_does", default={}).values()))
    q = "own_test_without_the_target"
    t2 = s.get("Q3", q, "own_test_by_kind_of_block")
    row("Q3 own test without the target: fails (first: sum over outcomes)",
        t2["class-only"]["fails"] + t2["asserts more"]["fails"], own_test_without_target(f, "fails"))
    row("Q3 own test without the target: passes (first: sum over outcomes)",
        t2["class-only"]["passes"] + t2["asserts more"]["passes"], own_test_without_target(f, "passes"))
    row("Q3 own test without the target: not read (first: sum over outcomes of every other value)",
        s.get("Q3", q, "not_counted"),
        sum(v for k, v in f.get("counts", "cases_with_target_by_outcome", default={}).items()
            if "; own test without the target: " in k and not k.endswith((": fails", ": passes"))))
    # runs
    row("expected baseline failures", s.get("runs", "expected_baseline_failures_count"),
        f.get("counts", "tests_expected_to_fail_at_baseline"))
    row("expected baseline failures, identifiers", s.get("runs", "expected_baseline_failures"),
        srt(f.get("expected_baseline_failures")))
    row("test files not collected", s.get("runs", "test_files_not_collected_count"),
        f.get("counts", "test_files_not_collected"))
    row("test files not collected, identifiers", s.get("runs", "test_files_not_collected"),
        srt(f.get("test_files_not_collected")))
    row("tests deselected as copies", s.get("runs", "tests_deselected_as_copies_count"),
        f.get("counts", "tests_collected_again"))
    row("tests deselected as copies, number of identifiers", n(s.get("runs", "tests_deselected_as_copies")),
        n(f.get("tests_collected_again")))
    row("copies that stay", s.get("runs", "copies_that_stay_count"), f.get("counts", "tests_imported_and_kept"))
    row("copies that stay, number of identifiers", n(s.get("runs", "copies_that_stay")),
        n(f.get("tests_imported_and_kept")))
    row("cases of nested blocks", s.get("runs", "cases_of_nested_blocks_in_the_study_count"),
        f.get("counts", "cases_nested"))
    row("cases with a firing in another thread", s.get("runs", "cases_with_a_firing_in_another_thread_in_the_study_count"),
        f.get("counts", "cases_fired_in_other_threads"))
    row("tests of the baseline recorder run", s.get("runs", "tests_in_baseline_recorder_run"), f.get("counts", "tests_run"))
    row("whole-suite tests passing in both unmodified runs",
        s.get("runs", "whole_suite_tests_passing_in_both_unmodified_runs"),
        f.get("whole_suite", "counts", "passing in both"))
    # refused connection attempts
    r = "refused_connection_attempts"
    row("refused attempts, suite run", s.get(r, "suite_run_without_recorder"), f.get(r, "suite_run"))
    b = s.get(r, "baseline_recorder_runs")
    row("refused attempts, baseline recorder runs", [b.get("base-1"), b.get("base-2")],
        f.get(r, "baseline_recorder_runs"))
    row("refused attempts, whole-suite unmodified runs", s.get(r, "whole_suite_unmodified_runs"),
        f.get(r, "whole_suite_baseline_runs"))
    mx = f.get(r, "deletion_recorder_runs", "maximum")
    row("refused attempts, deletion and control recorder runs: total is 0 (first: maximum is 0)",
        s.get(r, "deletion_and_control_recorder_runs_total") == 0, mx == 0 if mx is not MISSING else MISSING)
    row("refused attempts, deletion and control recorder runs without a count",
        n(s.get(r, "deletion_and_control_recorder_runs_without_a_count")),
        f.get(r, "deletion_recorder_runs", "runs_without_a_count"))
    mx = f.get(r, "whole_suite_deletion_runs", "maximum")
    row("refused attempts, whole-suite deletion and control runs: total is 0 (first: maximum is 0)",
        s.get(r, "whole_suite_deletion_and_control_runs_total") == 0, mx == 0 if mx is not MISSING else MISSING)
    row("refused attempts, whole-suite deletion and control runs without a count",
        n(s.get(r, "whole_suite_deletion_and_control_runs_without_a_count")),
        f.get(r, "whole_suite_deletion_runs", "runs_without_a_count"))
    row("refused attempts, witness runs", s.get(r, "witness_runs_total"), f.get(r, "witness_runs"))
    # sentinels
    for k in range(1, SENTINELS + 1):
        a = s.get("sentinels", str(k))
        b = f.get("sentinels", k - 1, "pass")
        row(f"sentinel {k}", a, ("holds" if b else "does not hold") if b is not MISSING else MISSING)
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="compare the second computation with summary.json")
    ap.add_argument("--second", required=True)
    ap.add_argument("--first", required=True)
    ap.add_argument("--quiet", action="store_true", help="print only the counts that differ")
    a = ap.parse_args(argv)
    with open(a.second, encoding="utf-8") as h:
        s = Doc(json.load(h))
    with open(a.first, encoding="utf-8") as h:
        f = Doc(json.load(h))
    rows = MAP(s, f)
    differ = absent = 0
    for label, x, y in rows:
        if x is MISSING or y is MISSING:
            absent += 1
            print(f"ABSENT   {label}: second {'(absent)' if x is MISSING else json.dumps(x)}; "
                  f"first {'(absent)' if y is MISSING else json.dumps(y)}")
        elif x == y:
            if not a.quiet:
                print(f"agrees   {label}: {json.dumps(x)}")
        else:
            differ += 1
            print(f"DIFFERS  {label}: second {json.dumps(x)}; first {json.dumps(y)}")
    print()
    print("counts of the second output without a counterpart in the table:")
    for p in sorted({p[:3] for p in s.unused()}, key=lambda t: tuple(map(str, t))):
        print("  second: " + " / ".join(map(str, p)))
    print("counts of the first output without a counterpart in the table:")
    for p in sorted({p[:3] for p in f.unused()}, key=lambda t: tuple(map(str, t))):
        print("  first: " + " / ".join(map(str, p)))
    print()
    print(f"{len(rows)} counts compared: {len(rows) - differ - absent} agree, {differ} differ, "
          f"{absent} absent from 1 file")
    return 1 if differ or absent else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
