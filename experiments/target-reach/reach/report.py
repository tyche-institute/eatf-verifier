"""The table across subjects and the 5 expectations of PROTOCOL.md, section 2.

Reads generated/<name>/summary.json of each named subject and writes
generated/REPORT.md and generated/report.json. It computes nothing from the
records: every number comes from a summary that reach/analyse.py wrote.

    python3 -I -B reach/report.py --held-out google-auth oauthlib authlib joserfc \
        --reference pyjwt-package --pilot jwcrypto

The rules of PROTOCOL.md, section 2, are applied here and nowhere else:

- Expectation E5 is stated for a subject in which at least 9 of every 10
  included blocks assert the class alone, and it is decided on the cases of
  those blocks. Both counts come from the summary.
- An expectation that has 0 units to be decided on is not applicable.
- A subject in which a sentinel does not hold, or whose summary does not hold
  the 7 sentinels, gets no verdict: each of the 5 expectations is reported as
  `no verdict`, with the numbers of the sentinels that do not hold.
- The report is not written while the summary of a named subject lacks the
  records of the whole suite.
- The verdicts are tallied per held-out library, never across libraries.

Exits nonzero if a sentinel of a named subject does not hold.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parents[1]
CASE_ORACLES = ["O_V", "O_Vfc", "O_C", "O_T"]
ORACLES = CASE_ORACLES + ["O_S", "suite", "whole suite"]
OUTCOMES = ["decided by the target", "the target fires and another check decides",
            "the target fires and no check decides", "the target does not fire"]


def facts(summary: dict) -> dict:
    """The numbers of 1 subject that the report shows, by name."""
    name = summary["subject"]["name"]
    c, lists = summary["counts"], summary["lists"]
    whole = summary.get("whole_suite") or {}
    if not whole.get("deletions_run") or "whole suite" not in lists["deletions_not_detected"]:
        raise SystemExit(f"report: the summary of {name} has no records of the whole suite")
    never = set(lists["deletions_of_checks_that_fire_and_never_decide"])
    hidden = {o: set(v) for o, v in lists["deletions_not_detected"].items()}
    deciding_hidden = {o: sorted(v - never) for o, v in hidden.items()}
    never_hidden = {o: sorted(v & never) for o, v in hidden.items()}
    withheld = {o: set(v) for o, v in lists["deletions_not_detected_withheld_as_failing"].items()}
    by_outcome = c["cases_with_target_by_outcome"]
    pin = c["pinning"]
    witnesses = summary.get("witnesses") or {}
    return {
        "version": summary["subject"]["version"],
        "checks in subject files": c["checks_in_subject_files"],
        "checks reachable": c["checks_reachable"],
        "checks that fire": c["checks_firing"],
        "deciding checks": c["checks_deciding"],
        "checks that fire and never decide": c["checks_firing_and_never_deciding"],
        "blocks": c["blocks"],
        "included blocks": c["included_blocks"],
        "included blocks, class-only": c["included_blocks_class_only"],
        "included blocks with a target": c["included_blocks_with_target"],
        "cases": c["cases"],
        "cases left out": c["cases_left_out"],
        "cases with a target": c["cases_with_target"],
        "cases with a target, assertion tier": c["cases_with_target_by_tier"].get("assertion", 0),
        "cases with a target, name tier": c["cases_with_target_by_tier"].get("name", 0),
        "outcomes": {o: by_outcome.get(o, 0) for o in OUTCOMES},
        "flags": c["flags"],
        "flags, assertion tier": c["flags_by_tier"].get("assertion", 0),
        "flags, name tier": c["flags_by_tier"].get("name", 0),
        "deletions": c["deletions"],
        "deletions of deciding checks": c["deletions_of_deciding_checks"],
        "deletions of checks that fire and never decide":
            c["deletions_of_checks_that_fire_and_never_decide"],
        "not detected, deciding checks": {o: len(deciding_hidden[o]) for o in ORACLES},
        "not detected, checks that fire and never decide": {o: len(never_hidden[o]) for o in ORACLES},
        "not detected with withheld cases counted as failing, deciding checks":
            {o: len(withheld[o] - never) for o in CASE_ORACLES},
        "not detected with withheld cases counted as failing, checks that fire and never decide":
            {o: len(withheld[o] & never) for o in CASE_ORACLES},
        "deciding checks: O_C detects and O_V does not":
            len(set(deciding_hidden["O_V"]) - set(deciding_hidden["O_C"])),
        "deletions that exceeded the time limit": c["deletions_time_limit"],
        "deletions without a record": c["deletions_without_record"],
        "pinning": {"cases": pin["cases"], "test passes": pin["test_passes"],
                    "class-only cases": pin["class_only"]["cases"],
                    "class-only, test passes": pin["class_only"]["test_passes"],
                    "cases of blocks that assert more": pin["message"]["cases"],
                    "blocks that assert more, test passes": pin["message"]["test_passes"]},
        "tests expected to fail at baseline": len(summary["expected_baseline_failures"]),
        "test files not collected": len(summary["test_files_not_collected"]),
        "tests collected again and deselected": c["tests_collected_again"],
        "imported tests that stay": c["tests_imported_and_kept"],
        "cases of a block inside another block": c["cases_nested"],
        "cases in which a check fires in another thread": c["cases_fired_in_other_threads"],
        "whole-suite tests passing in both unmodified runs": whole["counts"]["passing in both"],
        "connection attempts refused in the recorder runs at baseline":
            sum(n or 0 for n in summary["refused_connection_attempts"]["baseline_recorder_runs"]),
        "connection attempts refused in a whole-suite run at baseline":
            max((n or 0 for n in summary["refused_connection_attempts"]["whole_suite_baseline_runs"]),
                default=0),
        "sentinels": len(summary["sentinels"]),
        "sentinels that hold": sum(1 for s in summary["sentinels"] if s["pass"]),
        "deletions breaking an inclusion": sum(c["deletions_breaking_an_inclusion"].values()),
        "witness tests": len(witnesses),
        "witness tests that hold": sum(1 for w in witnesses.values() if w["holds"]),
    }


def e5_stated(f: dict) -> bool:
    """At least 9 of every 10 included blocks assert the class alone."""
    return f["included blocks"] > 0 and 10 * f["included blocks, class-only"] >= 9 * f["included blocks"]


def sentinels_not_holding(summary: dict) -> list[str]:
    """What stands against a verdict for 1 subject: the sentinels that do not
    hold, by number and name, or the fact that the summary does not hold 7."""
    sentinels = summary["sentinels"]
    if len(sentinels) != SENTINELS:
        return [f"the summary holds {len(sentinels)} sentinels, not {SENTINELS}"]
    return [f"{i}: {s['name']}" for i, s in enumerate(sentinels, 1) if not s["pass"]]


def expectations(f: dict, against: list[str] | None = None) -> dict:
    """E1 to E5 for 1 subject: {"status", "counts"}. The status is `held`, `not
    held`, `not applicable` (0 units to decide on), `not stated` (E5 alone) or,
    for all 5 when something stands against a verdict (`against`), `no verdict`."""
    if against:
        numbers = [a.split(":")[0] for a in against]
        if not all(n.isdigit() for n in numbers):
            why = against[0]
        elif len(numbers) == 1:
            why = f"sentinel {numbers[0]} does not hold"
        else:
            why = f"sentinels {', '.join(numbers)} do not hold"
        return {key: {"status": "no verdict", "counts": why} for key in TEXT}
    hidden = f["not detected, deciding checks"]
    n = f["deletions of deciding checks"]
    with_target = f["cases with a target"]
    undecided = with_target - f["outcomes"]["decided by the target"]
    pin = f["pinning"]

    def verdict(units: int, held: bool, counts: str) -> dict:
        if units == 0:
            return {"status": "not applicable", "counts": counts}
        return {"status": "held" if held else "not held", "counts": counts}

    return {
        "E1": verdict(n, hidden["O_V"] >= 1, f"{hidden['O_V']} of {n}"),
        "E2": verdict(n, f["deciding checks: O_C detects and O_V does not"] >= 1,
                      f"{f['deciding checks: O_C detects and O_V does not']} of {n}"),
        "E3": verdict(n, hidden["whole suite"] == 0, f"{n - hidden['whole suite']} of {n}"),
        "E4": verdict(with_target, undecided >= 1, f"{undecided} of {with_target}"),
        "E5": (verdict(pin["class-only cases"], pin["class-only, test passes"] >= 1,
                       f"{pin['class-only, test passes']} of {pin['class-only cases']}")
               if e5_stated(f) else
               {"status": "not stated",
                "counts": f"{f['included blocks, class-only']} of {f['included blocks']} included "
                          "blocks assert the class alone"}),
    }


SENTINELS = 7
STATUSES = ("held", "not held", "not applicable", "not stated", "no verdict")
TEXT = {
    "E1": "At least 1 deletion of a deciding check is not detected by O_V.",
    "E2": "O_C detects at least 1 deletion of a deciding check that O_V does not.",
    "E3": "The whole suite detects every deletion of a deciding check.",
    "E4": "At least 1 case with a target is not decided by its target.",
    "E5": "At least 1 case of a block that asserts the class alone passes its own test after the "
          "deletion of its deciding check.",
}

ROWS = [
    "version", "checks in subject files", "checks reachable", "checks that fire", "deciding checks",
    "checks that fire and never decide", "blocks", "included blocks", "included blocks, class-only",
    "included blocks with a target", "cases", "cases left out", "cases with a target",
    "cases with a target, assertion tier", "cases with a target, name tier",
    *[("outcomes", o) for o in OUTCOMES], "flags", "flags, assertion tier", "flags, name tier",
    "deletions", "deletions of deciding checks", "deletions of checks that fire and never decide",
    *[("not detected, deciding checks", o) for o in ORACLES],
    *[("not detected, checks that fire and never decide", o) for o in ORACLES],
    *[("not detected with withheld cases counted as failing, deciding checks", o) for o in CASE_ORACLES],
    *[("not detected with withheld cases counted as failing, checks that fire and never decide", o)
      for o in CASE_ORACLES],
    "deciding checks: O_C detects and O_V does not", "deletions that exceeded the time limit",
    "deletions without a record",
    ("pinning", "cases"), ("pinning", "test passes"), ("pinning", "class-only cases"),
    ("pinning", "class-only, test passes"), ("pinning", "cases of blocks that assert more"),
    ("pinning", "blocks that assert more, test passes"),
    "tests expected to fail at baseline", "test files not collected",
    "tests collected again and deselected", "imported tests that stay",
    "cases of a block inside another block",
    "cases in which a check fires in another thread",
    "whole-suite tests passing in both unmodified runs",
    "connection attempts refused in the recorder runs at baseline",
    "connection attempts refused in a whole-suite run at baseline",
    "sentinels", "sentinels that hold",
    "deletions breaking an inclusion", "witness tests", "witness tests that hold",
]


def cell(f: dict, row) -> str:
    v = f[row[0]].get(row[1]) if isinstance(row, tuple) else f[row]
    return "" if v is None else str(v)


def label(row) -> str:
    if not isinstance(row, tuple):
        return row
    if row[0] == "outcomes":
        return f"cases with a target: {row[1]}"
    if row[0] == "pinning":
        return f"pinning: {row[1]}"
    return f"{row[0]}: {row[1]}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="table across subjects and the 5 expectations")
    parser.add_argument("--held-out", nargs="+", required=True)
    parser.add_argument("--reference", nargs="*", default=[])
    parser.add_argument("--pilot", nargs="*", default=[])
    parser.add_argument("--generated", default=str(TOOL_ROOT / "generated"))
    parser.add_argument("--out", help="directory of REPORT.md and report.json (default: --generated)")
    args = parser.parse_args(argv)
    generated = Path(args.generated)
    out = Path(args.out) if args.out else generated
    roles = ([(n, "reference") for n in args.reference] + [(n, "pilot") for n in args.pilot]
             + [(n, "held out") for n in args.held_out])
    subjects, failing = {}, {}
    for name, role in roles:
        summary = json.loads((generated / name / "summary.json").read_text(encoding="utf-8"))
        f = facts(summary)
        bad = sentinels_not_holding(summary)
        subjects[name] = {"role": role, "facts": f, "expectations": expectations(f, bad)}
        if bad:
            failing[name] = bad
    names = [n for n, _ in roles]
    lines = ["# Target reach: the subjects side by side", "",
             "Every number is read from `generated/<name>/summary.json`.", "",
             "| | " + " | ".join(f"{n} ({subjects[n]['role']})" for n in names) + " |",
             "|---|" + "---|" * len(names)]
    for row in ROWS:
        lines.append(f"| {label(row)} | " + " | ".join(cell(subjects[n]["facts"], row) for n in names) + " |")
    lines += ["", "## The 5 expectations (PROTOCOL.md, section 2)", "",
              "Stated for the held-out libraries. The reference and the pilot are shown for comparison; "
              "the expectations were written with their counts in view. E5 is stated for a subject in "
              "which at least 9 of every 10 included blocks assert the class alone. An expectation with "
              "0 units to decide on is not applicable. A subject in which a sentinel does not hold gets "
              "no verdict on any expectation.", "",
              "| | Expectation | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for key, text in TEXT.items():
        cells = [f"{e['status']} ({e['counts']})" for e in (subjects[n]["expectations"][key] for n in names)]
        lines.append(f"| {key} | {text} | " + " | ".join(cells) + " |")
    held_out = [n for n, r in roles if r == "held out"]
    counts = {}
    lines += ["", "Verdicts per held-out library (no count is pooled across libraries):", ""]
    for n in held_out:
        status = [subjects[n]["expectations"][k]["status"] for k in TEXT]
        counts[n] = {s: status.count(s) for s in STATUSES}
        lines.append(f"- {n}: " + ", ".join(f"{s} {c}" for s, c in counts[n].items()))
    lines += ["", "Sentinels that do not hold: " + ("none." if not failing else "; ".join(
        f"{n}: {'; '.join(v)}" for n, v in failing.items()) + ".")]
    out.mkdir(parents=True, exist_ok=True)
    (out / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "report.json").write_text(
        json.dumps({"subjects": subjects, "expectations": TEXT, "held_out": held_out,
                    "held_out_expectations": counts, "sentinels_that_do_not_hold": failing},
                   indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"report: {len(names)} subjects; held-out expectations: {json.dumps(counts)}; "
          f"sentinels that do not hold: {failing or 'none'}")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
