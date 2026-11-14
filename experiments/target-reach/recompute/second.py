"""Second computation of the counts of PROTOCOL.md, for 1 subject.

    python3 -I -B recompute/second.py --subject subjects/<name>/subject.json \
        --records <records.tar.xz or a directory unpacked from it> --out <file.json>

Written from PROTOCOL.md (sections 2, 4 and 7) and from the formats of the
records and of the definitions. It imports nothing from the toolkit. It reads
`subject.json`, `checks.json`, `blocks.json` and `targets.json` beside the
given `subject.json`, and the records that `records.tar.xz` holds. It writes
1 JSON file: every count of section 7 that the definitions and the records
determine, and per-item lists that locate each count.

Counts that rest on a reading of the sources (the flags by class, A to D)
are not computed here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

PHASES = ("setup", "call", "teardown")
ORACLES = ("O_V", "O_Vfc", "O_C", "O_T")
OUTCOMES = ("the target decides the case", "the target fires and another check decides",
            "the target fires and no check decides", "the target does not fire",
            "not decided by the target")
ALL_ORACLES = ("O_V", "O_Vfc", "O_C", "O_T", "O_S", "suite", "whole_suite")


# -- loading -----------------------------------------------------------------------

def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def records_root(arg: str, keep: list) -> Path:
    """The directory that holds `base-1.json`: the given directory (or its
    `records/` folder), or a temporary directory into which the archive is
    unpacked. Members are checked so that nothing lands outside it."""
    p = Path(arg)
    if p.is_dir():
        return p / "records" if (p / "records").is_dir() else p
    tmp = tempfile.TemporaryDirectory()
    keep.append(tmp)
    with tarfile.open(p, "r:xz") as tar:
        for m in tar.getmembers():
            name = m.name
            if name.startswith("/") or ".." in Path(name).parts or not (m.isfile() or m.isdir()):
                raise SystemExit(f"unexpected member in the archive: {name}")
        tar.extractall(tmp.name, filter="data")
    root = Path(tmp.name)
    return root / "records" if (root / "records").is_dir() else root


def opt(root: Path, rel: str):
    p = root / rel
    return load(p) if p.exists() else None


def safe(check_id: str) -> str:
    return check_id.replace("#", "-")


# -- tests and cases ---------------------------------------------------------------

def case_key(c: dict) -> str:
    return f"{c['test']}|{c['block']}|{c['index']}"


def passes(t: dict | None) -> bool:
    """Section 4, 'A test passes': setup, body and teardown pass, no block fails
    its own check, no subtest fails. An expected failure is no pass."""
    if t is None:
        return False
    if t.get("failed_blocks"):
        return False
    if (t.get("subtests_failed") or 0) > 0:
        return False
    for p in PHASES:
        ph = t.get(p)
        if not ph or ph.get("outcome") != "passed" or ph.get("xfail"):
            return False
    return True


def skipped(t: dict) -> bool:
    """A test that is skipped (or ends as an expected failure) and has no failure."""
    if t.get("failed_blocks") or (t.get("subtests_failed") or 0) > 0:
        return False
    outs = [(t.get(p) or {}).get("outcome") for p in PHASES]
    if "failed" in outs:
        return False
    return "skipped" in outs or any((t.get(p) or {}).get("xfail") for p in PHASES)


def stopped_phase(t: dict) -> dict | None:
    """The phase in which the test stopped (setup or body), or None when both passed.
    A missing phase entry counts as a stop whose cause is unknown."""
    setup = t.get("setup")
    if not setup or setup.get("outcome") != "passed":
        return setup or {"outcome": None, "stop": None, "stop_is_assertion": None}
    call = t.get("call")
    if not call or call.get("outcome") != "passed" or call.get("xfail"):
        return call or {"outcome": None, "stop": None, "stop_is_assertion": None}
    return None


def status_of(ck: str, test_id: str, run_cases: dict, run_tests: dict) -> str:
    """Section 4, 'Status of a case in a deletion run'."""
    if ck in run_cases:
        return "observed"
    t = run_tests.get(test_id)
    if t is None:                                            # rule 1
        return "crashed"
    stop = stopped_phase(t)
    n_sub = t.get("subtests_failed") or 0
    if t.get("failed_blocks"):                               # rule 2
        return "withheld" if (stop is not None or n_sub > 0) else "missing"
    if stop is not None and stop.get("outcome") != "skipped" and not stop.get("xfail"):  # rule 3
        return "withheld" if stop.get("stop_is_assertion") is True else "crashed"
    if n_sub > 0:                                            # rule 4
        stops = t.get("subtest_stops") or []
        named = len(stops) == n_sub and all(s.get("stop") is not None for s in stops)
        if named and not any(s.get("stop_is_assertion") is True for s in stops):
            return "crashed"
        return "withheld"
    return "missing"                                         # rule 5


def strip_messages(x):
    """A record without message texts (sentinel 1)."""
    if isinstance(x, dict):
        return {k: strip_messages(v) for k, v in x.items() if k not in ("message", "check_detail")}
    if isinstance(x, list):
        return [strip_messages(v) for v in x]
    return x


# -- the computation ---------------------------------------------------------------

def compute(subject_path: Path, root: Path) -> dict:
    defs = subject_path.parent
    subject = load(subject_path)
    checks_doc = load(defs / "checks.json")
    blocks_doc = load(defs / "blocks.json")
    targets_doc = load(defs / "targets.json")

    base1 = opt(root, "base-1.json")
    base2 = opt(root, "base-2.json")
    suite = opt(root, "suite.json")
    if base1 is None or base2 is None or suite is None:
        raise SystemExit("a record of the baseline is absent: no output (section 4, 'Sentinels')")

    checks = {c["id"]: c for c in checks_doc["checks"]}
    subject_checks = {i for i, c in checks.items() if c["role"] == "subject"}
    blocks = {b["key"]: b for b in blocks_doc["blocks"]}
    included = {k: b for k, b in blocks.items() if b["included"]}
    target_of = {r["key"]: r.get("target") for r in targets_doc["blocks"]}
    tier_of = {r["key"]: r.get("tier") for r in targets_doc["blocks"]}

    def asserts_more(b: dict) -> bool:
        # Section 4, 'Block': a block asserts more than the class "when it gives a
        # pattern". blocks.json stores a literal pattern as a string, the empty string
        # included, and an absent pattern as null.
        return (b.get("match") is not None or b.get("match_unparsed") is not None
                or bool(b.get("post")) or bool(b.get("post_unparsed")))

    out: dict = {"subject": subject["name"], "version": subject.get("version"),
                 "protocol": "PROTOCOL.md, sections 2, 4 and 7"}

    # --- checks and blocks (definitions) ---
    files_with_included = sorted({b["file"] for b in included.values()})
    blocks_in_included_files = [b for b in blocks.values() if b["file"] in files_with_included]
    # Section 4, 'Block': "The block counts of a subject cover the test files of its
    # recorder runs". A recorder run "runs the test files of the subject" (section 4,
    # 'Runs'): the test files that blocks.json lists for the subject's test paths. For
    # the subjects defined by the 6 decisions these are the files with at least 1
    # included block; subjects/pyjwt "names its test directory by hand".
    run_files = set(blocks_doc.get("test_files", [])) or set(files_with_included)
    blocks_in_run_files = [b for b in blocks.values() if b["file"] in run_files]
    class_only_included = sorted(k for k, b in included.items() if not asserts_more(b))
    out["definitions"] = {
        "checks_all": len(checks),
        "checks_in_subject_files": len(subject_checks),
        "checks_in_observed_files": len(checks) - len(subject_checks),
        "reachable_checks_all": sum(1 for c in checks.values() if c["reachable"]),
        "reachable_checks_in_subject_files": sum(1 for i in subject_checks if checks[i]["reachable"]),
        "raise_statements_listed_apart_not_checks": len(checks_doc.get("other_raises", [])),
        "test_files_with_an_included_block": len(files_with_included),
        "test_files_of_the_recorder_runs": len(run_files),
        "blocks_in_test_files_of_the_recorder_runs": len(blocks_in_run_files),
        "blocks_in_test_files_with_an_included_block": len(blocks_in_included_files),
        "blocks_in_blocks_json": len(blocks),
        "test_files_in_blocks_json": len(blocks_doc.get("test_files", [])),
        "scope_counts_of_subject_json": subject.get("scope_counts"),
        "included_blocks": len(included),
        "class_only_included_blocks": len(class_only_included),
        "included_blocks_asserting_more_than_the_class": len(included) - len(class_only_included),
        "class_only_blocks_among_all_blocks_of_the_recorder_run_files": sum(
            1 for b in blocks_in_run_files if not asserts_more(b)),
        "included_blocks_with_a_target": sum(1 for k in included if target_of.get(k)),
        "included_blocks_with_a_target_by_tier": dict(sorted(Counter(
            tier_of.get(k) for k in included if target_of.get(k)).items())),
    }

    # --- baseline cases ---
    fired_recorded = bool(base1.get("fired_recorded"))
    base_cases = [c for c in base1["cases"] if c.get("included")]
    study, left_out = [], Counter()
    left_out_ids: dict[str, list] = {}
    for c in base_cases:
        if not c.get("raised"):
            reason = "the block raises no exception"
        elif not c.get("rejection"):
            reason = "the exception is of no rejection class"
        elif c.get("check_result") != "accepted":
            reason = "the own check of the block does not accept the exception"
        else:
            study.append(c)
            continue
        left_out[reason] += 1
        left_out_ids.setdefault(reason, []).append(case_key(c))

    def decider(c: dict) -> str | None:
        site = c.get("site")
        if site and site.get("kind") == "check" and site.get("check"):
            return site["check"]
        return None

    def firing(c: dict) -> set:
        s = set(c.get("fired") or [])
        d = decider(c)
        if d:
            s.add(d)
        return s

    study_by_key = {case_key(c): c for c in study}
    deciding = sorted({decider(c) for c in study if decider(c)})
    fire_all = sorted(set().union(*[firing(c) for c in study]) if study else set())
    never_decide = sorted(set(fire_all) - set(deciding))
    no_decider_cases = [case_key(c) for c in study if decider(c) is None]
    site_kinds = Counter(("no frame inside the package" if not c.get("site") else c["site"].get("kind"))
                         for c in study if decider(c) is None)

    out["cases"] = {
        "recorded_executions_of_included_blocks": len(base_cases),
        "cases_of_the_study": len(study),
        "cases_left_out": sum(left_out.values()),
        "cases_left_out_by_reason": dict(sorted(left_out.items())),
        "cases_left_out_ids": {k: sorted(v) for k, v in sorted(left_out_ids.items())},
        "cases_of_the_study_decided_by_a_check": len(study) - len(no_decider_cases),
        "cases_of_the_study_decided_by_no_check": len(no_decider_cases),
        "cases_of_the_study_decided_by_no_check_by_raise_site": dict(sorted(site_kinds.items())),
        "cases_of_the_study_decided_by_no_check_ids": sorted(no_decider_cases),
        "fired_checks_recorded": fired_recorded,
    }
    out["checks_at_run_time"] = {
        "deciding_checks_all": len(deciding),
        "deciding_checks_in_subject_files": sum(1 for d in deciding if d in subject_checks),
        "checks_that_fire_all": len(fire_all),
        "checks_that_fire_in_subject_files": sum(1 for d in fire_all if d in subject_checks),
        "checks_that_fire_and_never_decide_all": len(never_decide),
        "checks_that_fire_and_never_decide_in_subject_files": sum(1 for d in never_decide if d in subject_checks),
        "deciding_checks_ids": deciding,
        "checks_that_fire_and_never_decide_ids": never_decide,
    }

    # --- Q1 ---
    with_target = [c for c in study if target_of.get(c["block"])]
    outcome_ids: dict[str, list] = {}
    outcome_by_tier: dict[str, Counter] = {}
    tier_counts = Counter()
    for c in with_target:
        t = target_of[c["block"]]
        tier_counts[tier_of.get(c["block"])] += 1
        d = decider(c)
        if d == t:
            o = "the target decides the case"
        elif c.get("fired") is None:
            o = "not decided by the target"
        elif t in (c.get("fired") or []) and d is not None:
            o = "the target fires and another check decides"
        elif t in (c.get("fired") or []):
            o = "the target fires and no check decides"
        else:
            o = "the target does not fire"
        outcome_ids.setdefault(o, []).append(case_key(c))
        outcome_by_tier.setdefault(str(tier_of.get(c["block"])), Counter())[o] += 1
    flags = sorted(k for o, v in outcome_ids.items() if o != "the target decides the case" for k in v)
    out["Q1"] = {
        "cases_with_a_target": len(with_target),
        "cases_with_a_target_by_tier": dict(sorted(tier_counts.items())),
        "cases_without_a_target": len(study) - len(with_target),
        "outcomes": {o: len(outcome_ids.get(o, [])) for o in OUTCOMES},
        # Section 4, 'Target': "Counts are reported per tier."
        "outcomes_by_tier": {tier: {o: v.get(o, 0) for o in OUTCOMES}
                             for tier, v in sorted(outcome_by_tier.items())},
        "outcome_ids": {o: sorted(v) for o, v in sorted(outcome_ids.items())},
        "flags": len(flags),
        "flags_by_tier": dict(sorted(Counter(tier_of.get(study_by_key[k]["block"]) for k in flags).items())),
        "flag_ids": flags,
        "flags_by_class": "not computed: a reading of the sources (section 6, step 4)",
    }

    # --- deletions ---
    # An absent manifest (the deletions step left no record) and an empty one (no
    # check of the subject files fires in a case of the study) are kept apart.
    manifest_doc = opt(root, "deletions/manifest.json")
    manifest_present = manifest_doc is not None
    manifest = manifest_doc or {}
    no_record = opt(root, "deletions/no-record.json")
    repeated = opt(root, "deletions/repeated.json")
    whole_base = opt(root, "whole/base.json")
    whole_del = opt(root, "whole/deletions.json")
    witnesses = opt(root, "witnesses.json")
    control = opt(root, "deletions/_control.json")
    no_record = no_record or {}
    repeated = repeated or {}

    base_tests = {t["nodeid"]: t for t in base1["tests"]}
    base_passing_tests = {k for k, t in base_tests.items() if passes(t)}
    study_tests = {c["test"] for c in study}

    expected_deleted = sorted(d for d in fire_all if d in subject_checks)
    deleted = sorted(manifest)

    per_del: dict[str, dict] = {}
    run_records: dict[str, dict] = {}
    for d in deleted:
        rec = None
        nr = no_record.get(d)
        if nr is None:
            rec = opt(root, f"deletions/{manifest[d]['dir']}.json")
        info: dict = {"role": "deciding" if d in deciding else "fires and never decides",
                      "repeated": d in repeated}
        timed_out_twice = bool(nr) and list(nr.get("timed_out", [])) == [True, True]
        info["time_limit_exceeded_twice"] = timed_out_twice
        info["no_record"] = nr is not None or rec is None
        wd = (whole_del or {}).get(d)
        info["whole_suite_detected"] = bool(wd and wd.get("detected"))
        info["whole_suite_record"] = wd is not None
        if wd is not None:
            consistent = bool(wd.get("detected")) == bool(
                wd.get("timed_out") or wd.get("no_result") or (wd.get("tests_not_passing") or 0) > 0)
            info["whole_suite_record_consistent"] = consistent
        det = {o: False for o in ORACLES + ("O_S", "suite")}
        detw = {o: False for o in ORACLES}
        statuses = Counter()
        crashed, withheld, missing, changed = [], [], [], {o: [] for o in ORACLES}
        if timed_out_twice:
            for o in det:
                det[o] = True
            for o in detw:
                detw[o] = True
        elif rec is not None:
            run_records[d] = rec
            run_cases = {case_key(c): c for c in rec["cases"] if c.get("included")}
            run_tests = {t["nodeid"]: t for t in rec["tests"]}
            for ck, c in study_by_key.items():
                st = status_of(ck, c["test"], run_cases, run_tests)
                statuses[st] += 1
                t = target_of.get(c["block"])
                base_hold = {"O_V": True, "O_Vfc": True, "O_C": True,
                             "O_T": bool(t) and decider(c) == t}
                if st == "observed":
                    r = run_cases[ck]
                    raised = bool(r.get("raised"))
                    site = r.get("site") or {}
                    hold = {"O_V": raised and bool(r.get("rejection")),
                            "O_Vfc": raised,
                            "O_C": raised and r.get("class") == c.get("class"),
                            "O_T": raised and bool(t) and site.get("check") == t}
                    for o in ORACLES:
                        if base_hold[o] and not hold[o]:
                            changed[o].append(ck)
                elif st == "crashed":
                    crashed.append(ck)
                elif st == "withheld":
                    withheld.append(ck)
                    for o in ORACLES:
                        if base_hold[o]:
                            detw[o] = True
                else:
                    missing.append(ck)
            for o in ORACLES:
                det[o] = bool(changed[o]) or bool(crashed)
                detw[o] = detw[o] or det[o]
            lost_own = sorted(t for t in study_tests if t in base_passing_tests and not passes(run_tests.get(t)))
            lost_any = sorted(t for t in base_passing_tests if not passes(run_tests.get(t)))
            det["O_S"] = bool(lost_own) or bool(crashed)
            det["suite"] = bool(lost_any)
            info["tests_of_cases_not_passing"] = lost_own
            info["tests_not_passing"] = len(lost_any)
            info["fires_in_cases_of_its_own_run"] = sorted(
                case_key(c) for c in rec["cases"] if c.get("included")
                and (d in (c.get("fired") or []) or (c.get("site") or {}).get("check") == d))
        info["detected"] = det
        info["detected_withheld_as_failing"] = detw
        info["case_status"] = dict(sorted(statuses.items()))
        info["crashed_cases"] = sorted(crashed)
        info["withheld_cases"] = sorted(withheld)
        info["missing_cases"] = sorted(missing)
        info["cases_where_oracle_fails"] = {o: sorted(v) for o, v in changed.items()}
        per_del[d] = info

    def undetected(group: list[str], key: str, oracle: str) -> list[str]:
        if key == "whole_suite":
            return sorted(d for d in group if not per_del[d]["whole_suite_detected"])
        return sorted(d for d in group if not per_del[d][key][oracle])

    groups = {"deciding_checks": [d for d in deleted if per_del[d]["role"] == "deciding"],
              "checks_that_fire_and_never_decide": [d for d in deleted if per_del[d]["role"] != "deciding"]}
    q2: dict = {"deletions": len(deleted),
                "deletions_of_deciding_checks": len(groups["deciding_checks"]),
                "deletions_of_checks_that_fire_and_never_decide": len(groups["checks_that_fire_and_never_decide"])}
    for g, members in groups.items():
        main, wh, main_ids, wh_ids = {}, {}, {}, {}
        for o in ALL_ORACLES:
            ids = undetected(members, "whole_suite" if o == "whole_suite" else "detected", o)
            main[o], main_ids[o] = len(ids), ids
        for o in ORACLES:
            ids = undetected(members, "detected_withheld_as_failing", o)
            wh[o], wh_ids[o] = len(ids), ids
        q2[f"not_detected_{g}"] = main
        q2[f"not_detected_{g}_withheld_as_failing"] = wh
        q2[f"not_detected_{g}_ids"] = main_ids
        q2[f"not_detected_{g}_withheld_as_failing_ids"] = wh_ids
    q2["deletions_with_withheld_cases"] = sorted(d for d in deleted if per_del[d]["withheld_cases"])
    q2["deletions_with_crashed_cases"] = sorted(d for d in deleted if per_del[d]["crashed_cases"])
    q2["deletions_time_limit_exceeded_twice"] = sorted(d for d in deleted if per_del[d]["time_limit_exceeded_twice"])
    q2["cases_of_deletions_that_exceeded_the_time_limit"] = sorted(
        ck for d in q2["deletions_time_limit_exceeded_twice"] for ck, c in study_by_key.items()
        if d in firing(c))
    whole_repeated = sorted(k for k, v in (whole_del or {}).items() if (v.get("runs") or 1) > 1)
    q2["recorder_runs_repeated"] = sorted(repeated)
    q2["whole_suite_runs_repeated"] = whole_repeated
    q2["runs_repeated"] = len(repeated) + len(whole_repeated)
    q2["recorder_runs_without_a_record"] = sorted(no_record)
    whole_no_result = sorted(k for k, v in (whole_del or {}).items() if v.get("timed_out") or v.get("no_result"))
    q2["whole_suite_runs_without_a_result"] = whole_no_result
    q2["whole_suite_final_runs_that_exceeded_the_time_limit"] = sorted(
        k for k, v in (whole_del or {}).items() if v.get("timed_out"))
    q2["whole_suite_final_runs_without_a_result_file"] = sorted(
        k for k, v in (whole_del or {}).items() if v.get("no_result"))
    q2["whole_suite_runs_that_exceeded_the_time_limit_any_attempt"] = sorted(
        k for k, v in (whole_del or {}).items()
        if v.get("timed_out") or (v.get("first_run") or {}).get("timed_out"))
    q2["copies_whose_final_run_ended_without_a_record_or_a_result"] = len(no_record) + len(whole_no_result)
    # Section 4, 'Time limit': "A run that gives no record ... is repeated 1 time" and
    # "The summary lists every run that was repeated and every run that ended without a
    # record or a result." Each first attempt that was repeated ended without a record
    # (or a result), and so does a repeated attempt that failed again: counted per run.
    ended: list[str] = []
    for k in sorted(set(repeated) | set(no_record)):
        nr = no_record.get(k)
        n_runs = len(nr.get("timed_out") or [None, None]) if nr else (1 if k in repeated else 0)
        ended += [f"recorder run {i + 1} of {k}" for i in range(n_runs)]
    for k, v in sorted((whole_del or {}).items()):
        attempts = []
        if (v.get("runs") or 1) > 1:
            attempts.append(v.get("first_run") or {"timed_out": None, "no_result": None})
        attempts.append(v)
        for i, a in enumerate(attempts):
            if a.get("timed_out") or a.get("no_result") or ((v.get("runs") or 1) > 1 and i == 0):
                ended.append(f"whole-suite run {i + 1} of {k}")
    q2["runs_that_ended_without_a_record_or_a_result"] = ended
    q2["runs_without_a_record_or_a_result"] = len(ended)
    q2["whole_suite_records_inconsistent"] = sorted(
        d for d in deleted if per_del[d].get("whole_suite_record_consistent") is False)

    # the 5 inclusions of section 4
    def det_of(d, o):
        return per_del[d]["whole_suite_detected"] if o == "whole_suite" else per_del[d]["detected"][o]
    inclusions = {"O_Vfc_without_O_V": ("O_Vfc", "O_V"), "O_V_without_O_C": ("O_V", "O_C"),
                  "O_V_without_O_S": ("O_V", "O_S"), "O_S_without_suite": ("O_S", "suite"),
                  "suite_without_whole_suite": ("suite", "whole_suite")}
    q2["inclusion_breaks"] = {k: sorted(d for d in deleted if det_of(d, a) and not det_of(d, b))
                              for k, (a, b) in inclusions.items()}
    q2["inclusion_breaks_counts"] = {k: len(v) for k, v in q2["inclusion_breaks"].items()}

    # witnesses
    whole_undetected = set(undetected(deleted, "whole_suite", None))
    wit = {}
    for name, w in sorted((witnesses or {}).items()):
        before, after = w.get("unmodified") or {}, w.get("deleted") or {}
        holds = bool(before) and all(v == "passed" for v in before.values()) \
            and any(after.get(k) == "failed" for k in before)
        wit[name] = {"check": w.get("check"), "holds": holds, "holds_in_record": w.get("holds"),
                     "check_not_detected_by_the_whole_suite": w.get("check") in whole_undetected}
    q2["witness_files"] = wit
    q2["witness_files_count"] = len(wit)
    q2["witness_files_hold"] = sum(1 for w in wit.values() if w["holds"])
    q2["witness_files_do_not_hold"] = sum(1 for w in wit.values() if not w["holds"])
    q2["deletions_not_detected_by_the_whole_suite_with_a_witness_that_holds"] = sorted(
        {w["check"] for w in wit.values() if w["holds"] and w["check_not_detected_by_the_whole_suite"]})
    q2["deletions_not_detected_by_the_whole_suite_without_a_witness_that_holds"] = sorted(
        whole_undetected - {w["check"] for w in wit.values() if w["holds"]})
    q2["per_deletion"] = per_del
    out["Q2"] = q2

    # --- Q3: pinning ---
    def read_own_test(c: dict, check: str | None, kind_reason: str) -> tuple[str, dict | None]:
        """(reason not counted or 'counted', the record of the run)."""
        if check is None:
            return "no check decides the case", None
        if check not in manifest:
            if checks.get(check, {}).get("role") != "subject":
                return f"{kind_reason} lies outside the subject files", None
            return f"{kind_reason} fires in no case of the study", None
        if per_del[check]["time_limit_exceeded_twice"]:
            return "the deletion run exceeded the time limit", None
        if check not in run_records:
            return "the deletion run gave no record", None
        return "counted", run_records[check]

    def what_case_does(c: dict, rec: dict) -> str:
        run_cases = {case_key(x): x for x in rec["cases"] if x.get("included")}
        run_tests = {t["nodeid"]: t for t in rec["tests"]}
        ck = case_key(c)
        st = status_of(ck, c["test"], run_cases, run_tests)
        if st != "observed":
            return st
        r = run_cases[ck]
        if not r.get("raised"):
            return "observed: raises nothing"
        if r.get("class") == c.get("class"):
            return "observed: raises the class it raises at baseline"
        if r.get("rejection"):
            return "observed: raises another rejection class"
        return "observed: raises an exception of no rejection class"

    def pinning(cases: list, check_of, kind_reason: str) -> dict:
        not_counted, ids_nc = Counter(), {}
        table = {"class-only": Counter(), "asserts more": Counter()}
        ids = {"class-only": {"fails": [], "passes": []}, "asserts more": {"fails": [], "passes": []}}
        does = {"class-only": Counter(), "asserts more": Counter()}
        for c in cases:
            reason, rec = read_own_test(c, check_of(c), kind_reason)
            ck = case_key(c)
            if reason != "counted":
                not_counted[reason] += 1
                ids_nc.setdefault(reason, []).append(ck)
                continue
            kind = "asserts more" if asserts_more(blocks[c["block"]]) else "class-only"
            run_tests = {t["nodeid"]: t for t in rec["tests"]}
            res = "passes" if passes(run_tests.get(c["test"])) else "fails"
            table[kind][res] += 1
            ids[kind][res].append(ck)
            if res == "passes":
                does[kind][what_case_does(c, rec)] += 1
        return {"counted": sum(sum(v.values()) for v in table.values()),
                "own_test_by_kind_of_block": {k: {"fails": v["fails"], "passes": v["passes"]}
                                              for k, v in table.items()},
                "when_the_own_test_passes_the_case": {k: dict(sorted(v.items())) for k, v in does.items()},
                "not_counted": sum(not_counted.values()),
                "not_counted_by_reason": dict(sorted(not_counted.items())),
                "not_counted_ids": {k: sorted(v) for k, v in sorted(ids_nc.items())},
                "ids": {k: {r: sorted(x) for r, x in v.items()} for k, v in ids.items()}}

    out["Q3"] = {
        "pinning_without_the_deciding_check": pinning(study, decider, "the deciding check"),
        "own_test_without_the_target": pinning(with_target, lambda c: target_of[c["block"]], "the target"),
    }

    # --- baseline lists and run facts ---
    nested = sorted(case_key(c) for c in study if (c.get("depth") or 1) >= 2)
    nested_all = sorted(case_key(c) for c in base_cases if (c.get("depth") or 1) >= 2)
    other_thread = sorted(case_key(c) for c in study if c.get("fired_other_threads"))
    other_thread_all = sorted(case_key(c) for c in base_cases if c.get("fired_other_threads"))
    out["runs"] = {
        "expected_baseline_failures": sorted(suite.get("failures", [])),
        "expected_baseline_failures_count": len(suite.get("failures", [])),
        "test_files_not_collected": sorted(suite.get("not_collected", [])),
        "test_files_not_collected_count": len(suite.get("not_collected", [])),
        "tests_deselected_in_baseline_recorder_run": sorted(base1.get("deselected", [])),
        "tests_deselected_as_copies": sorted(x["nodeid"] for x in base1.get("collected_again", [])),
        "tests_deselected_as_copies_count": len(base1.get("collected_again", [])),
        "copies_that_stay": sorted(x["nodeid"] for x in base1.get("imported_kept", [])),
        "copies_that_stay_count": len(base1.get("imported_kept", [])),
        "cases_of_nested_blocks_in_the_study": nested,
        "cases_of_nested_blocks_in_the_study_count": len(nested),
        "cases_of_nested_blocks_all_recorded": len(nested_all),
        "cases_with_a_firing_in_another_thread_in_the_study": other_thread,
        "cases_with_a_firing_in_another_thread_in_the_study_count": len(other_thread),
        "cases_with_a_firing_in_another_thread_all_recorded": len(other_thread_all),
        "tests_in_baseline_recorder_run": len(base_tests),
        "tests_passing_in_baseline_recorder_run": len(base_passing_tests),
        "whole_suite_tests_passing_in_both_unmodified_runs":
            (whole_base or {}).get("counts", {}).get("passing in both"),
        "time_limit_seconds_recorder": (opt(root, "timeout.json") or {}).get("timeout_seconds"),
        "time_limit_seconds_whole_suite": (whole_base or {}).get("timeout_seconds"),
    }

    # refused connection attempts
    def att(x):
        return None if x is None else x.get("attempts")
    refused_base = opt(root, "refused.json") or {}
    refused_del = opt(root, "deletions/refused.json") or {}
    ref = {
        "suite_run_without_recorder": att(suite.get("refused")),
        "baseline_recorder_runs": {k: att(v) for k, v in sorted(refused_base.items())},
        "deletion_and_control_recorder_runs_total": sum(att(v) or 0 for v in refused_del.values()),
        "deletion_and_control_recorder_runs_without_a_count": sorted(k for k, v in refused_del.items() if v is None),
        "whole_suite_unmodified_runs": [att(v) for v in (whole_base or {}).get("refused", [])],
        "whole_suite_deletion_and_control_runs_total": sum(att(v.get("refused")) or 0
                                                           for v in (whole_del or {}).values()),
        "whole_suite_deletion_and_control_runs_without_a_count": sorted(
            k for k, v in (whole_del or {}).items() if v.get("refused") is None),
        "witness_runs_total": sum((w.get("refused") or {}).get(s) or 0
                                  for w in (witnesses or {}).values() for s in ("unmodified", "deleted")),
    }
    ref["total"] = (sum(v for v in [ref["suite_run_without_recorder"]] if v)
                    + sum(v or 0 for v in ref["baseline_recorder_runs"].values())
                    + ref["deletion_and_control_recorder_runs_total"]
                    + sum(v or 0 for v in ref["whole_suite_unmodified_runs"])
                    + ref["whole_suite_deletion_and_control_runs_total"] + ref["witness_runs_total"])
    out["refused_connection_attempts"] = ref

    # --- sentinels ---
    s = {}
    notes = {}
    # 1
    if control is None:
        s[1], notes[1] = False, "the control copy gave no record"
    else:
        a, b, cc = (strip_messages(x) for x in (base1, base2, control))
        s[1] = a == b == cc
        notes[1] = ("identical" if s[1] else
                    f"base-1 = base-2: {a == b}; base-1 = control: {a == cc}")
    # 2
    bad_tests = sorted(k for k, t in base_tests.items() if not (passes(t) or skipped(t)))
    # Section 4, sentinel 2: "In the baseline recorder run ... every test file is
    # collected". A file that the run without the recorder cannot collect "is ignored
    # in every recorder run and listed" (section 4, 'Baseline'): it is read on the
    # baseline recorder run. The stricter reading, which also asks the run without the
    # recorder to collect every file, is kept as an alternative status.
    collected = not base1.get("collect_errors")
    desel_ok = set(base1.get("deselected", [])) == set(suite.get("failures", []))
    s[2] = not bad_tests and collected and desel_ok
    s2_strict = s[2] and not suite.get("not_collected")
    notes[2] = {"tests_neither_passing_nor_skipped": bad_tests,
                "collect_errors": base1.get("collect_errors", []),
                "not_collected_in_suite_run": suite.get("not_collected", []),
                "deselected_equal_expected_failures": desel_ok}
    # 3
    fires_own = {d: per_del[d].get("fires_in_cases_of_its_own_run") for d in deleted}
    missing_rec = [d for d in deleted if d not in run_records]
    missing_rec_not_timed_out = [d for d in missing_rec if not per_del[d]["time_limit_exceeded_twice"]]
    # Primary reading: "a sentinel whose other records are absent (the deletion runs ...)
    # does not hold" and "sentinel 3 needs the records of the deletion runs" (section 5).
    # Alternative reading: a deletion whose run exceeded the time limit 2 times has no
    # record by design (sentinel 4 and 'Time limit' accept it), so it is excused.
    s[3] = manifest_present and not missing_rec and all(not v for v in fires_own.values())
    s3_excused = manifest_present and not missing_rec_not_timed_out and all(not v for v in fires_own.values())
    notes[3] = {"deletions_whose_check_fires": sorted(d for d, v in fires_own.items() if v),
                "deletions_without_a_record": sorted(missing_rec),
                "deletions_without_a_record_that_did_not_exceed_the_time_limit_2_times":
                    sorted(missing_rec_not_timed_out)}
    # 4
    # Section 4, 'Time limit': "The recorder run of a deletion copy or of the control
    # copy ... When a run gives no record 2 times without both exceeding the limit,
    # sentinel 4 does not hold": the control copy is included.
    bad4 = sorted(d for d, v in no_record.items() if list(v.get("timed_out", [])) != [True, True])
    s[4] = opt(root, "deletions/no-record.json") is not None and not bad4 and \
        all((d in run_records) or per_del[d]["time_limit_exceeded_twice"] for d in deleted)
    notes[4] = {"no_record_without_two_time_outs": bad4}
    # 5
    bad5 = sorted(case_key(c) for c in study if decider(c) and (c.get("fired") is None or decider(c) not in c["fired"]))
    bad5_all = sorted(case_key(c) for c in base_cases if decider(c)
                      and (c.get("fired") is None or decider(c) not in c["fired"]))
    # Section 4, sentinel 5: "The check that decides a case is among the checks that fire
    # in it." A case is every recorded execution of an included block ('Case'); the
    # cases of the study are a subset. The sentinel is read over every case.
    s[5] = fired_recorded and not bad5_all
    notes[5] = {"cases_of_the_study_whose_deciding_check_is_not_among_the_fired": bad5,
                "recorded_cases_whose_deciding_check_is_not_among_the_fired": bad5_all}
    # 6
    if whole_del is None or whole_base is None:
        s[6], notes[6] = False, "whole-suite records absent"
    else:
        missing6 = sorted(d for d in deleted if d not in whole_del)
        ctl = whole_del.get("_control")
        ctl_ok = bool(ctl) and not ctl.get("timed_out") and not ctl.get("no_result") \
            and (ctl.get("tests_not_passing") or 0) == 0 and not ctl.get("detected")
        s[6] = not missing6 and ctl_ok
        notes[6] = {"deletion_copies_without_whole_suite_run": missing6, "control_ok": ctl_ok}
    # 7
    s[7] = manifest_present and deleted == expected_deleted
    notes[7] = {"deleted_not_expected": sorted(set(deleted) - set(expected_deleted)),
                "expected_not_deleted": sorted(set(expected_deleted) - set(deleted))}
    out["sentinels"] = {str(k): ("holds" if v else "does not hold") for k, v in sorted(s.items())}
    out["sentinels_detail"] = {str(k): v for k, v in sorted(notes.items())}
    all_hold = all(s.values())

    # --- expectations (section 2) ---
    dec = groups["deciding_checks"]
    e5_share_ok = len(class_only_included) * 10 >= 9 * len(included) and len(included) > 0
    pin = out["Q3"]["pinning_without_the_deciding_check"]
    e5_units = pin["own_test_by_kind_of_block"]["class-only"]
    e5_n = e5_units["fails"] + e5_units["passes"]
    exp = {
        "E1": {"units": len(dec), "count": len(q2["not_detected_deciding_checks_ids"]["O_V"]),
               "rule": "at least 1 deletion of a deciding check is not detected by O_V"},
        "E2": {"units": len(dec), "count": sum(1 for d in dec if per_del[d]["detected"]["O_C"]
                                               and not per_del[d]["detected"]["O_V"]),
               "rule": "O_C detects at least 1 deletion of a deciding check that O_V does not"},
        "E3": {"units": len(dec), "count": sum(1 for d in dec if per_del[d]["whole_suite_detected"]),
               "rule": "the whole suite detects every deletion of a deciding check"},
        "E4": {"units": len(with_target), "count": len(flags),
               "rule": "at least 1 case with a target is not decided by its target"},
        "E5": {"units": e5_n, "count": e5_units["passes"],
               "rule": "at least 1 case of a class-only block passes its own test after the deletion of its deciding check",
               "class_only_included_blocks": len(class_only_included), "included_blocks": len(included)},
    }
    raw = {"E1": exp["E1"]["count"] >= 1, "E2": exp["E2"]["count"] >= 1,
           "E3": exp["E3"]["count"] == exp["E3"]["units"], "E4": exp["E4"]["count"] >= 1,
           "E5": exp["E5"]["count"] >= 1}
    readings = {
        "sentinel 2 also asks the run without the recorder to collect every file": {**s, 2: s2_strict},
        "sentinel 3 excuses deletions that exceeded the time limit 2 times": {**s, 3: s3_excused},
    }
    out["sentinels_alternative_readings"] = {
        name: {str(k): ("holds" if v else "does not hold") for k, v in sorted(ss.items())}
        for name, ss in readings.items()}

    def verdict(e: str, v: dict, ss: dict) -> str:
        if not all(ss.values()):
            return "no verdict"
        if e == "E5" and not e5_share_ok:
            return "not stated"
        if v["units"] == 0:
            return "not applicable"
        return "held" if raw[e] else "not held"
    for e, v in exp.items():
        if not all_hold:
            v["verdict"] = "no verdict"
            v["sentinels_not_holding"] = [k for k, ok in sorted(s.items()) if not ok]
        elif e == "E5" and not e5_share_ok:
            v["verdict"] = "not stated"
        elif v["units"] == 0:
            v["verdict"] = "not applicable"
        else:
            v["verdict"] = "held" if raw[e] else "not held"
        v["verdict_under_alternative_readings"] = {name: verdict(e, v, ss) for name, ss in readings.items()}
        v["verdict_ignoring_sentinels"] = ("not stated" if e == "E5" and not e5_share_ok else
                                           "not applicable" if v["units"] == 0 else
                                           ("held" if raw[e] else "not held"))
    out["expectations"] = exp
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", required=True)
    ap.add_argument("--records", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    keep: list = []
    root = records_root(a.records, keep)
    data = compute(Path(a.subject), root)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    s = data["sentinels"]
    print(f"{data['subject']}: {data['cases']['cases_of_the_study']} cases of the study, "
          f"{data['Q2']['deletions']} deletions, sentinels: "
          + ", ".join(f"{k} {'ok' if v == 'holds' else 'NO'}" for k, v in s.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
