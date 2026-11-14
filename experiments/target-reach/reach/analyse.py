"""Analysis of the target-reach runs: writes generated/<subject>/.

    python -I reach/analyse.py --subject subjects/<name>/subject.json [--work DIR] [--defs DIR] [--out DIR]

Reads checks.json, blocks.json (written by `run.py define`), targets.json
(written by `run.py targets`) and the records of `run.py baseline`, `run.py
deletions`, `run.py whole-baseline` and `run.py whole-deletions`. `--work` is
the directory that holds `records/`: the work directory of the runs, or the
directory where `records.tar.xz` was unpacked. Stops without writing any output
when checks.json, blocks.json, targets.json, suite.json or 1 of the 2 baseline
records is absent. Otherwise writes every output, then exits nonzero if a
sentinel does not hold; a sentinel whose other records are absent (the deletion
runs, the control copy, the whole-suite runs) does not hold. Definitions:
PROTOCOL.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_ROOT = HERE.parent
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from reach.checks import load_json  # noqa: E402
from reach.study import case_key, firing, left_out_reason  # noqa: E402

CASE_ORACLES = ["O_V", "O_Vfc", "O_C", "O_T"]   # decided on a case
ORACLES = CASE_ORACLES + ["O_S"]                 # O_S is decided on the case's test
COLUMNS = ORACLES + ["suite"]


class Run:
    def __init__(self, record: dict) -> None:
        self.record = record
        self.cases = {case_key(c): c for c in record["cases"] if c["included"]}
        self.tests = {t["nodeid"]: t for t in record["tests"]}

    def passed(self, nodeid: str) -> bool:
        """The test's own outcome. The recorder lets a test go on after a block
        that failed its own check, so such a test counts as failed here."""
        t = self.tests.get(nodeid)
        if t is None or t.get("failed_blocks") or t.get("subtests_failed"):
            return False
        return (t.get("setup", {}).get("outcome") == "passed"
                and t.get("call", {}).get("outcome") == "passed"
                and t.get("teardown", {}).get("outcome", "passed") == "passed")

    def ok(self, nodeid: str) -> bool:
        """Passed or skipped."""
        t = self.tests.get(nodeid)
        if t is None or t.get("failed_blocks") or t.get("subtests_failed"):
            return False
        if t.get("setup", {}).get("outcome") == "skipped" or t.get("call", {}).get("outcome") == "skipped":
            return True
        return self.passed(nodeid)

    def status(self, key: str, test: str) -> str:
        """observed, or why the case did not run (PROTOCOL.md, section 4):

        crashed   the test has no record; or it stopped, in its setup or in its
                  body, on an exception that is not an assertion failure; or
                  it did not stop, subtests of it failed and every failed
                  subtest stopped on such an exception
        withheld  the test stopped on an assertion failure; or it went on
                  after a block that failed its own check and then stopped or
                  had a failed subtest; or it did not stop and 1 of its failed
                  subtests stopped on an assertion failure, or on something
                  the record does not name
        missing   the test was skipped, or it ended without running the case
        """
        if key in self.cases:
            return "observed"
        t = self.tests.get(test)
        if t is None:
            return "crashed"
        setup, call = t.get("setup", {}), t.get("call", {})
        setup_ok = setup.get("outcome") == "passed"
        stopped = not setup_ok or call.get("stop") is not None
        skipped = "skipped" in (setup.get("outcome"), call.get("outcome"))
        subtests = t.get("subtests_failed", 0)
        if t.get("failed_blocks"):
            # the test went on after a block that failed its own check; a later
            # stop of any kind, a skip or a failed subtest included, is not
            # credited to the subject
            return "withheld" if stopped or subtests else "missing"
        if stopped and not skipped:
            phase = call if setup_ok else setup
            return "withheld" if phase.get("stop_is_assertion") else "crashed"
        if subtests:
            # a failed subtest ends its own body and the test goes on; the case
            # may have been in the body of any failed subtest
            stops = t.get("subtest_stops", [])
            crashed = len(stops) == subtests and all(s.get("stop_is_assertion") is False for s in stops)
            return "crashed" if crashed else "withheld"
        return "missing"  # a skip is no failure of the test


def site_label(obs: dict | None) -> str:
    if obs is None:
        return ""
    if not obs.get("raised"):
        return "no exception"
    site = obs.get("site")
    if site is None:
        return "outside package"
    if site["check"]:
        return site["check"]
    return f"{site['kind']} ({site['file']}:{site['line']} {site['source']})"


def site_kind(obs: dict) -> str:
    if not obs.get("raised"):
        return "no exception"
    site = obs.get("site")
    if site is None:
        return "outside package"
    return "check" if site["check"] else site["kind"]


def oracles(obs: dict, base: dict, target: str | None) -> dict:
    raised = bool(obs.get("raised"))
    site = (obs.get("site") or {}).get("check")
    return {
        "O_V": raised and bool(obs.get("rejection")),
        "O_Vfc": raised,
        "O_C": raised and obs.get("class") == base.get("class"),
        "O_T": (site == target) if target else None,
    }


def csv_text(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


def yn(v: bool | None) -> str:
    return "" if v is None else ("yes" if v else "no")


def asserts_message(block: dict) -> bool:
    """The block asserts more than the class: a pattern, or an assertion on the bound exception."""
    return bool(block.get("match") is not None or block.get("match_unparsed")
                or block.get("post") or block.get("post_unparsed"))


def analyse(subject: dict, defs: Path, work: Path, out: Path) -> int:
    checks_doc = load_json(defs / "checks.json")
    blocks_doc = load_json(defs / "blocks.json")
    targets_doc = load_json(defs / "targets.json")
    rec = work / "records"
    suite = load_json(rec / "suite.json")
    base_raw = load_json(rec / "base-1.json")
    base2_raw = load_json(rec / "base-2.json")
    base = Run(base_raw)
    checks = {c["id"]: c for c in checks_doc["checks"]}
    blocks = {b["key"]: b for b in blocks_doc["blocks"]}
    targets = {t["key"]: t for t in targets_doc["blocks"]}
    # The cases of the study: baseline cases of included blocks that raise a
    # rejection class which the block accepts. A block is included by the names
    # it expects, so a case can raise a class of that name from another package;
    # such a case is counted and left out.
    left_out = {k: reason for k, c in sorted(base.cases.items())
                if (reason := left_out_reason(c)) is not None}
    keys = sorted(k for k in base.cases if k not in left_out)

    manifest_path = rec / "deletions" / "manifest.json"
    deletions_ran = manifest_path.exists()
    manifest = load_json(manifest_path) if deletions_ran else {}
    control_path = rec / "deletions" / "_control.json"
    control_raw = load_json(control_path) if control_path.exists() else None
    no_record_path = rec / "deletions" / "no-record.json"
    no_record = load_json(no_record_path) if no_record_path.exists() else {}
    repeated_path = rec / "deletions" / "repeated.json"
    repeated = load_json(repeated_path) if repeated_path.exists() else {}
    witness_path = rec / "witnesses.json"
    witnesses = load_json(witness_path) if witness_path.exists() else {}
    whole_base_path, whole_path = rec / "whole" / "base.json", rec / "whole" / "deletions.json"
    whole_base = load_json(whole_base_path) if whole_base_path.exists() else None
    whole = load_json(whole_path) if whole_path.exists() else None
    runs = {}
    for cid, m in sorted(manifest.items()):
        p = rec / "deletions" / f"{m['dir']}.json"
        runs[cid] = Run(load_json(p)) if p.exists() else None
    refused = refused_attempts(rec, suite, whole_base, whole, witnesses)

    def target_of(key: str) -> dict:
        return targets.get(base.cases[key]["block"], {})

    def site_of(key: str) -> str | None:
        return (base.cases[key].get("site") or {}).get("check")

    fired_recorded = bool(base_raw.get("fired_recorded"))

    def fired_of(key: str) -> list[str]:
        """The checks that fire in the case, in the order of the first firing."""
        return base.cases[key].get("fired") or []

    def target_fired(key: str) -> bool | None:
        target = target_of(key).get("target")
        return (target in fired_of(key)) if target and fired_recorded else None

    base_or = {k: oracles(base.cases[k], base.cases[k], target_of(k).get("target")) for k in keys}
    case_tests = sorted({base.cases[k]["test"] for k in keys})

    # -- cases.csv ------------------------------------------------------------------
    case_rows = []
    for k in keys:
        c = base.cases[k]
        t = target_of(k)
        b = blocks[c["block"]]
        case_rows.append([c["block"], c["index"], c["test"], " | ".join(b["expected"] or []),
                          "message" if asserts_message(b) else "class only",
                          c.get("class", ""), site_label(c), t.get("target"), t.get("basis") or "",
                          t.get("tier") or "", yn(base_or[k]["O_T"]), "; ".join(fired_of(k)),
                          yn(target_fired(k))])
    reach_count = sum(1 for k in keys if base_or[k]["O_T"])
    kinds = Counter(site_kind(base.cases[k]) for k in keys)

    # -- per check -------------------------------------------------------------------
    decided = Counter(site_of(k) for k in keys)
    fires = Counter(c for k in keys for c in firing(base.cases[k]))
    targeted = Counter(t["target"] for t in targets_doc["blocks"] if t["target"])
    check_rows = [[c["id"], c["file"], c["role"], c["function"], c["class"], c["template"],
                   yn(any((g or "").startswith("except") for g in c["guards"])), yn(c["reachable"]),
                   yn(decided.get(c["id"], 0) > 0), decided.get(c["id"], 0), targeted.get(c["id"], 0),
                   fires.get(c["id"], 0)]
                  for c in checks_doc["checks"]]
    reached_unreachable = sorted(c["id"] for c in checks_doc["checks"]
                                 if decided.get(c["id"]) and not c["reachable"])

    # -- deletions ---------------------------------------------------------------------
    deletion_rows, deletion_detail = [], {}
    invariant_broken, time_limit = [], []
    after_deletion = {}  # per deletion: the cases in which the deleted check fires at baseline, afterwards
    for cid, run in runs.items():
        ck = checks[cid]
        w = (whole or {}).get(cid)
        whole_cells = [yn(w["detected"]) if w else "", w["tests_not_passing"] if w else "",
                       fires.get(cid, 0)]
        instead = Counter()  # in the cases where the check fires at baseline: what fires now and did not
        if run is None:
            limit = no_record.get(cid, {}).get("timed_out") or []
            if limit and all(limit):
                # the run exceeded the time limit 2 times: detected under every oracle
                time_limit.append(cid)
                deletion_detail[cid] = {"detected": {o: True for o in ORACLES}, "suite": True,
                                        "withheld_as_failing": {o: True for o in CASE_ORACLES},
                                        "statuses": {}}
                deletion_rows.append([cid, ck["file"], ck["function"], ck["class"], ck["template"],
                                      decided.get(cid, 0), "time limit",
                                      yn(any((g or "").startswith("except") for g in ck["guards"]))]
                                     + ["yes"] * 10 + [""] * 7 + whole_cells + [""])
            else:
                deletion_rows.append([cid, ck["file"], ck["function"], ck["class"], ck["template"],
                                      decided.get(cid, 0), "no record"] + [""] * 18 + whole_cells + [""])
            continue
        det = {o: False for o in ORACLES}
        withheld_det = {o: False for o in CASE_ORACLES}
        statuses = Counter()
        moved = Counter()
        after_deletion[cid] = []
        for k in keys:
            b = base.cases[k]
            st = run.status(k, b["test"])
            statuses[st] += 1
            fires_here = cid in firing(b)
            before = [cid, b["block"], b["index"], b["test"], b.get("class", ""), site_label(b),
                      b.get("message", "")]
            if st == "observed":
                obs = run.cases[k]
                now = oracles(obs, b, target_of(k).get("target"))
                for o in CASE_ORACLES:
                    if base_or[k][o] and now[o] is False:
                        det[o] = True
                if (obs.get("site") or {}).get("check") == cid or cid in (obs.get("fired") or []):
                    invariant_broken.append(f"{cid}: {k}")
                new_checks = sorted(set(obs.get("fired") or []) - set(fired_of(k)))
                if fired_recorded and fires_here:
                    for c in new_checks or ["no other check"]:
                        instead[c] += 1
                if fires_here:
                    after_deletion[cid].append(before + [
                        st, obs.get("class", "") if obs.get("raised") else "", site_label(obs),
                        obs.get("message", "") if obs.get("raised") else "",
                        ("; ".join(new_checks) or "no other check") if fired_recorded else ""])
                dest = site_label(obs)
            else:
                if fires_here:
                    after_deletion[cid].append(before + [st, "", "", "", ""])
                if st == "withheld":
                    for o in CASE_ORACLES:
                        if base_or[k][o]:
                            withheld_det[o] = True
                dest = st
            if dest != site_label(b):
                moved[dest] += 1
        det["O_S"] = any(base.passed(n) and not run.passed(n) for n in case_tests)
        if statuses["crashed"]:  # a crash of any case is detected under every oracle
            det = {o: True for o in ORACLES}
        suite_det = any(base.passed(n) and not run.passed(n) for n in base.tests)
        sens = {o: det[o] or withheld_det[o] for o in CASE_ORACLES}
        deletion_detail[cid] = {"detected": det, "suite": suite_det, "withheld_as_failing": sens,
                                "statuses": dict(statuses)}
        deletion_rows.append([cid, ck["file"], ck["function"], ck["class"], ck["template"],
                              decided.get(cid, 0), "ran",
                              yn(any((g or "").startswith("except") for g in ck["guards"])),
                              yn(det["O_V"]), yn(det["O_Vfc"]), yn(det["O_C"]), yn(det["O_T"]), yn(det["O_S"]),
                              yn(suite_det),
                              yn(sens["O_V"]), yn(sens["O_Vfc"]), yn(sens["O_C"]), yn(sens["O_T"]),
                              sum(moved.values()),
                              "; ".join(f"{d} x{n}" for d, n in sorted(moved.items())),
                              statuses.get("withheld", 0), statuses.get("crashed", 0),
                              statuses.get("missing", 0),
                              sum(1 for n in case_tests if base.passed(n) and not run.passed(n)),
                              sum(1 for n in base.tests if base.passed(n) and not run.passed(n))]
                             + whole_cells
                             + ["; ".join(f"{d} x{n}" for d, n in sorted(instead.items()))])

    # -- the case's own test on the copy without the case's target ---------------------------
    def without_target(key: str) -> str:
        target = target_of(key).get("target")
        if not target:
            return ""
        if target not in runs:
            # it fires in no case of the study, or it is not in a subject file
            return "target not deleted"
        run = runs[target]
        if run is None:
            return "time limit" if target in time_limit else "no record"
        return "passes" if run.passed(base.cases[key]["test"]) else "fails"

    def outcome(key: str) -> str:
        if base_or[key]["O_T"]:
            return "decided by the target"
        if not fired_recorded:
            return "not decided by the target"
        if not target_fired(key):
            return "the target does not fire"
        return ("the target fires and another check decides" if site_of(key)
                else "the target fires and no check decides")

    by_outcome = Counter()
    for row, k in zip(case_rows, keys):
        row.append(without_target(k))
        if target_of(k).get("target"):
            by_outcome[outcome(k)] += 1
            by_outcome[f"{outcome(k)}; own test without the target: {without_target(k)}"] += 1

    # -- pinning: the case's own test, when the check that decides the case is deleted -------
    pin_rows = []
    pin = Counter()
    pin_by = {"class only": Counter(), "message": Counter()}
    takeover = Counter()
    for k in keys:
        d = site_of(k)
        if d is None:
            pin["no deciding check"] += 1  # the exception is raised by no check
            continue
        if d not in runs:
            pin["deciding check not deleted"] += 1  # not in a subject file, or the stage was not run
            continue
        run = runs[d]
        if run is None:
            pin["time limit" if d in time_limit else "no record"] += 1
            continue
        b = base.cases[k]
        blk = blocks[b["block"]]
        kind = "message" if asserts_message(blk) else "class only"
        st = run.status(k, b["test"])
        passes = run.passed(b["test"])
        obs = run.cases.get(k)
        if st != "observed":
            what = st
        elif not obs.get("raised"):
            what = "no exception"
        else:
            same = obs.get("class") == b.get("class")
            where = site_kind(obs)
            what = f"{'same class' if same else 'other class'}, {where if where != 'check' else 'another check'}"
        pin["cases"] += 1
        pin["test passes" if passes else "test fails"] += 1
        pin_by[kind]["cases"] += 1
        pin_by[kind]["test passes" if passes else "test fails"] += 1
        if passes:
            takeover[what] += 1
        pin_rows.append([b["block"], b["index"], b["test"], kind, d, b.get("class", ""), st,
                         obs.get("class", "") if obs else "", site_label(obs) if obs else "",
                         what, yn(passes)])

    # -- flags --------------------------------------------------------------------------
    flag_rows = []
    for k in keys:
        t = target_of(k)
        if not t.get("target") or base_or[k]["O_T"]:
            continue
        b = base.cases[k]
        site = site_of(k)
        tgt = t["target"]
        flag_rows.append([b["block"], b["index"], blocks[b["block"]]["test"], t["basis"], t["tier"],
                          tgt, checks[tgt]["template"], site or site_label(b),
                          checks[site]["template"] if site else "", yn(target_fired(k)),
                          without_target(k)])

    # -- sentinels ------------------------------------------------------------------------
    sentinels = []

    def norm(r):
        """A record without the text of the exception messages: a message can hold
        the time of the run, and no count is computed from it."""
        cases = [{k: v for k, v in c.items() if k != "message"} for c in r["cases"]]
        return json.dumps(dict(r, cases=cases), sort_keys=True)
    same = norm(base_raw) == norm(base2_raw) and control_raw is not None and norm(base_raw) == norm(control_raw)
    sentinels.append({"name": "2 baseline runs and the control copy give identical records, message texts aside",
                      "pass": same, "detail": "" if same else (
                          "records differ" if control_raw is not None
                          else "the control copy gave no record" if "_control" in no_record
                          else "control not run")})
    message_differs = 0
    if same:
        triples = zip(base_raw["cases"], base2_raw["cases"], control_raw["cases"])
        message_differs = sum(1 for x in triples if len({c.get("message") for c in x}) > 1)
    expected_failures = sorted(suite["failures"])
    not_collected = sorted(suite.get("not_collected", []))
    failing = sorted(n for n in base.tests if not base.ok(n) and n not in expected_failures)
    deselected = base_raw.get("deselected")
    not_those = sorted(set(expected_failures) ^ set(deselected or []))
    sentinels.append({"name": "in the baseline recorder run every test passes or is skipped, every test "
                              "file is collected, and the tests deselected are the expected baseline "
                              "failures",
                      "pass": (not failing and not base_raw["collect_errors"] and deselected is not None
                               and not not_those),
                      "detail": (failing[:20] or [e["nodeid"] for e in base_raw["collect_errors"]][:20]
                                 or ("the baseline record does not hold the deselected tests"
                                     if deselected is None else not_those[:20]))})
    sentinels.append({"name": "under the deletion of a check, that check fires in no case",
                      "pass": deletions_ran and not invariant_broken,
                      "detail": invariant_broken[:20] if deletions_ran else "deletion stage not run"})
    lost = sorted(c for c, r in runs.items() if r is None and c not in time_limit)
    sentinels.append({"name": "every deletion run gave a record or exceeded the time limit 2 times",
                      "pass": deletions_ran and not lost,
                      "detail": lost if deletions_ran else "deletion stage not run"})
    absent = sorted(k for k in keys if site_of(k) and site_of(k) not in fired_of(k))
    sentinels.append({"name": "the check that decides a case is among the checks that fire in it",
                      "pass": fired_recorded and not absent,
                      "detail": absent[:20] if fired_recorded
                      else "the baseline record does not hold the checks that fire"})
    control = (whole or {}).get("_control", {})
    missing = sorted(c for c in runs if c not in (whole or {}))
    sentinels.append({"name": "the whole suite ran on every deletion copy, and on the control copy it "
                              "ends with its results and loses no test that passes in both unmodified "
                              "runs",
                      "pass": (whole is not None and bool(control) and not control.get("detected", True)
                               and not missing),
                      "detail": (control.get("examples", []) or missing) if whole is not None
                      else "whole-suite stage not run"})
    to_delete = sorted(c for c in fires if checks[c]["role"] == "subject")
    sentinels.append({"name": "the deleted checks are the checks of the subject files that fire in "
                              "at least 1 case of the study",
                      "pass": deletions_ran and sorted(manifest) == to_delete,
                      "detail": sorted(set(manifest) ^ set(to_delete))[:20] if deletions_ran
                      else "deletion stage not run"})

    # -- summary ---------------------------------------------------------------------------
    ran = {c["block"] for c in base.cases.values()}
    never = sorted(b["key"] for b in blocks_doc["blocks"] if b["included"] and b["key"] not in ran)
    included = [b for b in blocks_doc["blocks"] if b["included"]]
    with_target = Counter(target_of(k).get("basis") for k in keys if target_of(k).get("target"))
    by_tier = Counter(target_of(k).get("tier") for k in keys if target_of(k).get("target"))
    flags_by_tier = Counter(r[4] for r in flag_rows)
    hidden = {o: sorted(c for c, d in deletion_detail.items() if not d["detected"][o]) for o in ORACLES}
    hidden["suite"] = sorted(c for c, d in deletion_detail.items() if not d["suite"])
    if whole is not None:
        hidden["whole suite"] = sorted(c for c in runs if c in whole and not whole[c]["detected"])
    hidden_sens_lists = {o: sorted(c for c, d in deletion_detail.items() if not d["withheld_as_failing"][o])
                         for o in CASE_ORACLES}
    hidden_sens = {o: len(v) for o, v in hidden_sens_lists.items()}
    reached_targets = sorted({target_of(k)["target"] for k in keys if base_or[k]["O_T"]})
    # the inclusions that hold by construction (PROTOCOL.md, section 4): deletions that break them
    def flag_of(cid: str, column: str) -> bool | None:
        d = deletion_detail.get(cid)
        if d is None:
            return None
        if column == "whole suite":
            w = (whole or {}).get(cid)
            return None if w is None else bool(w["detected"])
        return d["suite"] if column == "suite" else d["detected"][column]

    inclusions = {}
    for narrow, wide in (("O_Vfc", "O_V"), ("O_V", "O_C"), ("O_V", "O_S"), ("O_S", "suite"),
                         ("suite", "whole suite")):
        inclusions[f"{narrow} within {wide}"] = sorted(
            c for c in deletion_detail if flag_of(c, narrow) and flag_of(c, wide) is False)
    fired_only = sorted(c for c in runs if not decided.get(c))
    # undetected.csv is about the whole suite and stays empty without its records
    undetected_rows = [r for c in hidden.get("whole suite", []) for r in after_deletion.get(c, [])]
    hidden_deciding = {o: sum(1 for c in v if decided.get(c)) for o, v in hidden.items()}
    hidden_sens_deciding = {o: sum(1 for c in v if decided.get(c)) for o, v in hidden_sens_lists.items()}
    summary = {
        "subject": {k: subject[k] for k in ("name", "version", "commit")},
        "rule_version": targets_doc["rule_version"],
        "suite_without_recorder": suite["summary"],
        "expected_baseline_failures": expected_failures,
        "test_files_not_collected": not_collected,
        "tests_collected_again": base_raw.get("collected_again") or [],
        "tests_imported_and_kept": base_raw.get("imported_kept") or [],
        "refused_connection_attempts": refused,
        "counts": {
            "blocks": len(blocks_doc["blocks"]),
            "included_blocks": len(included),
            "included_blocks_class_only": sum(1 for b in included if not asserts_message(b)),
            "included_blocks_never_run": len(never),
            "included_blocks_with_target": sum(1 for t in targets_doc["blocks"] if t["target"]),
            "block_targets_by_basis": targets_doc["counts"],
            "tests_with_cases": len(case_tests),
            "tests_run": len(base.tests),
            "tests_expected_to_fail_at_baseline": len(expected_failures),
            "test_files_not_collected": len(not_collected),
            "tests_collected_again": len(base_raw.get("collected_again") or []),
            "tests_imported_and_kept": len(base_raw.get("imported_kept") or []),
            "cases_nested": sum(1 for k in keys if (base.cases[k].get("depth") or 1) > 1),
            "cases_fired_in_other_threads": sum(1 for k in keys if base.cases[k].get("fired_other_threads")),
            "cases_of_included_blocks": len(base.cases),
            "cases_left_out": len(left_out),
            "cases_left_out_by_reason": dict(sorted(Counter(
                r.split(" (")[0] for r in left_out.values()).items())),
            "cases": len(keys),
            "cases_message_text_differs_between_unmodified_runs": message_differs,
            "cases_class_only": sum(1 for k in keys if not asserts_message(blocks[base.cases[k]["block"]])),
            "cases_by_site_kind": dict(sorted(kinds.items())),
            "cases_with_target": sum(with_target.values()),
            "cases_with_target_by_basis": dict(sorted(with_target.items())),
            "cases_with_target_by_tier": dict(sorted(by_tier.items())),
            "cases_reaching_target": reach_count,
            "cases_target_fires": sum(1 for k in keys if target_fired(k)),
            "cases_another_check_fires_too": sum(
                1 for k in keys if set(fired_of(k)) - {site_of(k)}),
            "flags": len(flag_rows),
            "flags_by_tier": dict(sorted(flags_by_tier.items())),
            "flags_target_fires": sum(1 for r in flag_rows if r[-2] == "yes"),
            "cases_with_target_by_outcome": dict(sorted(by_outcome.items())),
            "checks": len(checks_doc["checks"]),
            "checks_in_subject_files": sum(c["role"] == "subject" for c in checks_doc["checks"]),
            "checks_reachable": sum(c["reachable"] for c in checks_doc["checks"]),
            "checks_deciding": sum(1 for c in checks_doc["checks"] if decided.get(c["id"])),
            "checks_deciding_in_subject_files": sum(1 for c in checks_doc["checks"]
                                                    if decided.get(c["id"]) and c["role"] == "subject"),
            "checks_deciding_not_statically_reachable": len(reached_unreachable),
            "checks_firing": sum(1 for c in checks_doc["checks"] if fires.get(c["id"])),
            "checks_firing_and_never_deciding": sum(1 for c in checks_doc["checks"]
                                                    if fires.get(c["id"]) and not decided.get(c["id"])),
            "fired_recorded": fired_recorded,
            "deletions": len(runs),
            "deletions_of_deciding_checks": len(runs) - len(fired_only),
            "deletions_of_checks_that_fire_and_never_decide": len(fired_only),
            "deletions_time_limit": len(time_limit),
            "deletions_without_record": len(lost),
            "deletion_runs_repeated": len(repeated),
            "deletions_in_handler": sum(1 for c in runs if any((g or "").startswith("except")
                                                               for g in checks[c]["guards"])),
            "deletions_not_detected": {o: len(v) for o, v in hidden.items()},
            "deletions_not_detected_of_deciding_checks": hidden_deciding,
            "deletions_breaking_an_inclusion": {k: len(v) for k, v in inclusions.items()},
            "deletions_not_detected_withheld_as_failing": hidden_sens,
            "deletions_not_detected_withheld_as_failing_of_deciding_checks": hidden_sens_deciding,
            "reached_targets": len(reached_targets),
            "reached_targets_deletion_not_detected_O_T": sum(
                1 for t in reached_targets if t in deletion_detail and not deletion_detail[t]["detected"]["O_T"]),
            "pinning": {
                "cases": pin["cases"], "test_fails": pin["test fails"], "test_passes": pin["test passes"],
                "cases_not_counted_time_limit": pin["time limit"],
                "cases_not_counted_no_record": pin["no record"],
                "cases_not_counted_no_deciding_check": pin["no deciding check"],
                "cases_not_counted_deciding_check_not_deleted": pin["deciding check not deleted"],
                "class_only": {"cases": pin_by["class only"]["cases"],
                               "test_passes": pin_by["class only"]["test passes"]},
                "message": {"cases": pin_by["message"]["cases"],
                            "test_passes": pin_by["message"]["test passes"]},
                "test_passes_by_what_the_case_does": dict(sorted(takeover.items())),
            },
        },
        "witnesses": {name: {"check": w["check"], "holds": w["holds"],
                             "tests": len(w["unmodified"]),
                             "tests_passing_on_the_unmodified_copy": sum(
                                 1 for v in w["unmodified"].values() if v == "passed"),
                             "tests_failing_without_the_check": sum(
                                 1 for k in w["unmodified"] if w["deleted"].get(k) == "failed"),
                             "tests_not_passing_without_the_check": sum(
                                 1 for k in w["unmodified"] if w["deleted"].get(k) != "passed"),
                             "failure_messages_without_the_check": dict(sorted(
                                 (w.get("deleted_failures") or {}).items()))}
                      for name, w in sorted(witnesses.items())},
        "whole_suite": None if whole_base is None else {
            "suite_runs": whole_base["suite_runs"], "counts": whole_base["counts"],
            "deletions_run": whole is not None,
            "deletions_time_limit": sorted(c for c, r in (whole or {}).items() if r["timed_out"]),
            "deletions_no_result": sorted(c for c, r in (whole or {}).items() if r.get("no_result")),
            "runs_repeated": sorted(c for c, r in (whole or {}).items() if r.get("runs") == 2)},
        "lists": {
            "deletions_time_limit": time_limit,
            "deletions_without_record": lost,
            "deletion_runs_repeated": sorted(repeated),
            "cases_left_out": [{"case": k, "reason": r} for k, r in sorted(left_out.items())],
            "included_blocks_never_run": never,
            "checks_deciding_not_statically_reachable": reached_unreachable,
            "deletions_of_checks_that_fire_and_never_decide": fired_only,
            "deletions_breaking_an_inclusion": inclusions,
            "deletions_not_detected": hidden,
            "deletions_not_detected_withheld_as_failing": hidden_sens_lists,
        },
        "sentinels": sentinels,
    }

    out.mkdir(parents=True, exist_ok=True)
    files = {
        "cases.csv": csv_text(["block", "index", "test_node", "expected", "asserts", "baseline_class",
                               "baseline_site", "target", "basis", "tier", "reaches_target", "fired",
                               "target_fired", "own_test_without_target"], case_rows),
        "checks.csv": csv_text(["check", "file", "role", "function", "class", "template", "in_handler",
                                "reachable", "decides", "cases_decided", "blocks_targeting",
                                "cases_fired"], check_rows),
        "deletions.csv": csv_text(["check", "file", "function", "class", "template", "cases_decided", "run",
                                   "in_handler", "O_V", "O_Vfc", "O_C", "O_T", "O_S", "suite",
                                   "O_V withheld-as-failing", "O_Vfc withheld-as-failing",
                                   "O_C withheld-as-failing", "O_T withheld-as-failing",
                                   "cases_site_moved", "moved_to", "cases_withheld", "cases_crashed",
                                   "cases_missing", "tests_with_cases_failing", "tests_failing",
                                   "whole_suite", "whole_suite_tests_not_passing", "cases_fired",
                                   "fires_instead"],
                                  deletion_rows),
        "pinning.csv": csv_text(["block", "index", "test_node", "asserts", "deleted_check", "baseline_class",
                                 "status", "class", "site", "what_the_case_does", "test_passes"], pin_rows),
        "flags.csv": csv_text(["block", "index", "test", "basis", "tier", "target", "target_template",
                               "deciding_check", "deciding_template", "target_fired",
                               "own_test_without_target"], flag_rows),
        # the deletions that the whole suite does not detect: every case in which the deleted
        # check fires at baseline, before and after the deletion
        "undetected.csv": csv_text(["deleted_check", "block", "index", "test_node", "baseline_class",
                                    "baseline_decided_by", "baseline_message", "status", "class",
                                    "decided_by", "message", "fires_now_and_not_before"], undetected_rows),
        "summary.json": json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        "SUMMARY.md": summary_md(summary),
    }
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    sums = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name not in ("SHA256SUMS", "VALIDATION.md"):
            sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    failed = [s["name"] for s in sentinels if not s["pass"]]
    print(f"analyse: {len(keys)} cases, {reach_count} of {sum(with_target.values())} reach their target, "
          f"{len(flag_rows)} flags, {len(runs)} deletions, not detected "
          f"{json.dumps(summary['counts']['deletions_not_detected'])}; pinning "
          f"the own test passes in {pin['test passes']} of {pin['cases']} cases; "
          f"sentinels that do not hold: {failed or 'none'}")
    return 1 if failed else 0


def refused_attempts(rec: Path, suite: dict, whole_base: dict | None, whole: dict | None,
                     witnesses: dict) -> dict:
    """The connection attempts that the offline module refused, per kind of run
    (reach/run.py writes them). A run without a count did not reach its end."""
    def number(doc):
        return None if doc is None else doc["attempts"]

    def spread(docs: list) -> dict:
        counted = [d["attempts"] for d in docs if d is not None]
        return {"runs": len(docs), "runs_without_a_count": len(docs) - len(counted),
                "runs_with_attempts": sum(1 for n in counted if n),
                "minimum": min(counted, default=None), "maximum": max(counted, default=None)}

    def read(path: Path) -> dict:
        return load_json(path) if path.exists() else {}

    base, deleted = read(rec / "refused.json"), read(rec / "deletions" / "refused.json")
    whole_docs = [r.get("refused") for r in (whole or {}).values()]
    docs = ([suite.get("refused")] + list(base.values()) + list(deleted.values()) + whole_docs
            + list((whole_base or {}).get("refused", [])))
    return {
        "suite_run": number(suite.get("refused")),
        "baseline_recorder_runs": [number(base.get(n)) for n in ("base-1", "base-2")],
        "deletion_recorder_runs": spread(list(deleted.values())),
        "whole_suite_baseline_runs": [number(r) for r in (whole_base or {}).get("refused", [])],
        "whole_suite_deletion_runs": spread(whole_docs),
        "witness_runs": sum((w.get("refused") or {}).get(k) or 0
                            for w in witnesses.values() for k in ("unmodified", "deleted")),
        "tests": sorted({t for d in docs if d for t in d["tests"]}),
    }


def summary_md(s: dict) -> str:
    c = s["counts"]
    p = c["pinning"]
    lines = [f"# Target reach: {s['subject']['name']} {s['subject']['version']}", "",
             f"Commit `{s['subject']['commit']}`. Rule `{s['rule_version']}`. "
             f"Suite without the recorder: {s['suite_without_recorder']}.", "",
             "| Count | Value |", "|---|---|"]
    for k in ("blocks", "included_blocks", "included_blocks_class_only", "included_blocks_never_run",
              "included_blocks_with_target", "tests_run", "tests_expected_to_fail_at_baseline",
              "test_files_not_collected", "tests_collected_again", "tests_imported_and_kept",
              "tests_with_cases",
              "cases_of_included_blocks", "cases_left_out", "cases", "cases_class_only", "cases_nested",
              "cases_fired_in_other_threads",
              "cases_with_target", "cases_reaching_target", "cases_target_fires", "flags",
              "flags_target_fires", "cases_another_check_fires_too", "checks", "checks_in_subject_files",
              "checks_reachable", "checks_deciding", "checks_deciding_in_subject_files",
              "checks_deciding_not_statically_reachable", "checks_firing",
              "checks_firing_and_never_deciding", "deletions", "deletions_of_deciding_checks",
              "deletions_of_checks_that_fire_and_never_decide", "deletions_in_handler"):
        lines.append(f"| {k} | {c[k]} |")
    lines += ["", "Where the baseline cases raise:", ""]
    lines += [f"- {k}: {v}" for k, v in c["cases_by_site_kind"].items()]
    lines += ["", "Included blocks by basis of the target, or by the reason for none:", ""]
    lines += [f"- {k}: {v}" for k, v in c["block_targets_by_basis"].items()]
    lines += ["", "Cases with a target, by tier (flags: the baseline raise site is not the target):", ""]
    lines += [f"- {k}: {v} cases, {c['flags_by_tier'].get(k, 0)} flags"
              for k, v in c["cases_with_target_by_tier"].items()]
    lines += ["", "Cases with a target, by what decides them and by the case's own test on the copy "
              "without the target:", "", "| Outcome | Cases |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in c["cases_with_target_by_outcome"].items()]
    lines += ["", f"Deletions of the {c['deletions']} reached checks, not detected:", "",
              "| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing "
              "| Of them, deciding checks |",
              "|---|---|---|---|---|"]
    for o, v in c["deletions_not_detected"].items():
        w = c["deletions_not_detected_withheld_as_failing"].get(o)
        wd = c["deletions_not_detected_withheld_as_failing_of_deciding_checks"].get(o)
        lines.append(f"| {o} | {v} | {c['deletions_not_detected_of_deciding_checks'][o]} | "
                     f"{'' if w is None else w} | {'' if wd is None else wd} |")
    ws = s.get("whole_suite")
    if ws:
        lines += ["", "Whole suite, without the recorder (" + "; ".join(
            f"{r['name']}: pytest {' '.join(r['paths'])}" for r in ws["suite_runs"]) + "): "
            f"{ws['counts']['passing in both']} tests pass in both unmodified runs, "
            f"{ws['counts']['unstable']} differ between them."]
        if ws.get("runs_repeated"):
            lines += ["", "Whole-suite runs repeated on a fresh copy, because the first run exceeded "
                      "the time limit or a pytest call left no result file: "
                      + ", ".join(f"`{n}`" for n in ws["runs_repeated"]) + "."]
        if ws.get("deletions_time_limit") or ws.get("deletions_no_result"):
            ended = sorted(set(ws.get("deletions_time_limit", [])) | set(ws.get("deletions_no_result", [])))
            lines += ["", "Whole-suite runs whose repeated run also exceeded the time limit or left no "
                      "result file (detected by the whole suite): "
                      + ", ".join(f"`{n}`" for n in ended) + "."]
    if c["deletions_time_limit"]:
        lines += ["", f"Deletion runs that exceeded the time limit 2 times (detected under every oracle): "
                  f"{c['deletions_time_limit']}."]
    if c["deletions_without_record"]:
        lines += ["", "Deletion runs that gave no record 2 times without both exceeding the time limit "
                  f"(they are in no count of detection, and sentinel 4 does not hold): "
                  f"{c['deletions_without_record']}."]
    if s["lists"]["deletion_runs_repeated"]:
        lines += ["", "Recorder runs repeated on a fresh copy, because the first run gave no record: "
                  + ", ".join(f"`{n}`" for n in s["lists"]["deletion_runs_repeated"]) + "."]
    r = s["refused_connection_attempts"]
    d, w = r["deletion_recorder_runs"], r["whole_suite_deletion_runs"]
    lines += ["", "Connection attempts to another machine, refused and counted in every run: "
              f"suite run {r['suite_run']}; recorder runs at baseline {r['baseline_recorder_runs']}; "
              f"recorder runs of the deletion copies and the control: {d['runs_with_attempts']} of "
              f"{d['runs']} runs with an attempt; whole suite at baseline "
              f"{r['whole_suite_baseline_runs']}; whole suite on the deletion copies and the control: "
              f"between {w['minimum']} and {w['maximum']} in {w['runs']} runs; witness runs "
              f"{r['witness_runs']}."]
    if r["tests"]:
        lines += ["", "Tests during which an attempt was refused (the name of a suite run comes before "
                  "`|` for a whole-suite run):", ""]
        lines += [f"- `{t or '(no test running)'}`" for t in r["tests"]]
    if s.get("witnesses"):
        lines += ["", "Witness files (written after the run; a file holds when every test of it passes on "
                  "the unmodified copy and at least 1 fails on the copy without the check):", "",
                  "| File | Deleted check | Holds | Tests | Passing on the unmodified copy | "
                  "Failing without the check | Not passing without the check |",
                  "|---|---|---|---|---|---|---|"]
        lines += [f"| `{name}` | `{w['check']}` | {'yes' if w['holds'] else 'no'} | {w['tests']} | "
                  f"{w['tests_passing_on_the_unmodified_copy']} | {w['tests_failing_without_the_check']} | "
                  f"{w['tests_not_passing_without_the_check']} |" for name, w in s["witnesses"].items()]
        messages = [(name, test.split("::", 1)[-1], " ".join(message.split()).replace("`", "'"))
                    for name, w in s["witnesses"].items()
                    for test, message in w["failure_messages_without_the_check"].items()]
        if messages:
            lines += ["", "Recorded message of each failure on the copy without the check:", ""]
            lines += [f"- `{name}`, `{test}`: `{message or '(no message)'}`" for name, test, message in messages]
    broken = c["deletions_breaking_an_inclusion"]
    lines += ["", "Deletions that break an inclusion which holds by construction: "
              + "; ".join(f"{k}: {v}" for k, v in broken.items()) + "."]
    lines += ["", f"Reached target checks whose deletion O_T does not detect: "
              f"{c['reached_targets_deletion_not_detected_O_T']} of {c['reached_targets']}.", "",
              "Pinning. For each case, the check that decides it is deleted and the case's own test is "
              "read. The unit counted is the case: a test with several cases is read 1 time per case, "
              "and it fails when it does not pass:", "",
              f"- cases decided by a deleted check: {p['cases']}; the own test fails for "
              f"{p['test_fails']} and still passes for {p['test_passes']}",
              f"- cases of blocks that assert the class only: the own test still passes for "
              f"{p['class_only']['test_passes']} of {p['class_only']['cases']}",
              f"- cases of blocks that assert more than the class: the own test still passes for "
              f"{p['message']['test_passes']} of {p['message']['cases']}",
              f"- cases not counted: {p['cases_not_counted_no_deciding_check']} whose exception no "
              f"check raises; {p['cases_not_counted_deciding_check_not_deleted']} whose deciding check "
              f"was not deleted; {p['cases_not_counted_time_limit']} whose deletion run exceeded the "
              f"time limit 2 times; {p['cases_not_counted_no_record']} whose deletion run gave no "
              "record"]
    if p["test_passes_by_what_the_case_does"]:
        lines += ["- what the case does when its test still passes: " + "; ".join(
            f"{k}: {v}" for k, v in p["test_passes_by_what_the_case_does"].items())]
    lines += ["", "Sentinels:", ""]
    lines += [f"- {'pass' if x['pass'] else 'FAIL'}: {x['name']}" for x in s["sentinels"]]
    if s["expected_baseline_failures"]:
        lines += ["", "Tests that fail without the recorder (deselected in every recorder run):", ""]
        lines += [f"- `{n}`" for n in s["expected_baseline_failures"]]
    if s["test_files_not_collected"]:
        lines += ["", "Test files that pytest could not collect (ignored in every recorder run):", ""]
        lines += [f"- `{n}`" for n in s["test_files_not_collected"]]
    if s["tests_collected_again"]:
        lines += ["", "Tests that a test file imports from another test file and that pytest collects "
                  "again (the copy is deselected in every recorder run):", ""]
        lines += [f"- `{t['nodeid']}`, defined in `{t['defined_in']}`" for t in s["tests_collected_again"]]
    if s["tests_imported_and_kept"]:
        lines += ["", "Tests that a test file imports from another test file and that stay in the recorder "
                  "runs, because the runs do not hold the test in the file that defines it:", ""]
        lines += [f"- `{t['nodeid']}`, defined in `{t['defined_in']}`" for t in s["tests_imported_and_kept"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="target-reach analysis")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--work")
    parser.add_argument("--defs")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    subject_path = Path(args.subject).resolve()
    subject = load_json(subject_path)
    defs = Path(args.defs).resolve() if args.defs else subject_path.parent
    work = Path(args.work).resolve() if args.work else TOOL_ROOT / "work" / subject["name"]
    out = Path(args.out).resolve() if args.out else TOOL_ROOT / "generated" / subject["name"]
    return analyse(subject, defs, work, out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
