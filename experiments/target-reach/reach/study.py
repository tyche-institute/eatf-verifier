"""The cases of the study and the checks that fire in them, read from 1 record.

The runner (which checks to delete) and the analysis (which cases to count)
use these functions, so the 2 cannot disagree. Definitions: PROTOCOL.md,
section 4.
"""

from __future__ import annotations


def case_key(case: dict) -> str:
    return f"{case['test']}|{case['block']}|{case['index']}"


def left_out_reason(case: dict) -> str | None:
    """Why a baseline execution of an included block is not a case of the study,
    or None when it is one: the block raises an exception of a rejection class
    and the block's own check accepts it."""
    if not case.get("raised"):
        return "no exception"
    if case.get("check_result") != "accepted":
        return f"the block does not accept the exception ({case.get('check_result')})"
    if not case.get("rejection"):
        return f"not a rejection class ({case.get('class')})"
    return None


def study_cases(record: dict) -> dict[str, dict]:
    """Case key -> record, for the cases of the study in a baseline record."""
    return {case_key(c): c for c in record["cases"]
            if c["included"] and left_out_reason(c) is None}


def firing(case: dict) -> set[str]:
    """The checks that fire in a case: the check at the raise site of the
    exception, and every check whose exception was raised while the block was
    open, caught or not."""
    out = set(case.get("fired") or [])
    site = (case.get("site") or {}).get("check")
    if site:
        out.add(site)
    return out


def firing_checks(record: dict) -> set[str]:
    """The checks that fire in at least 1 case of the study."""
    out: set[str] = set()
    for case in study_cases(record).values():
        out |= firing(case)
    return out
