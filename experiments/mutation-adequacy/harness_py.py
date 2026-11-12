"""Python harness for the mutation-adequacy experiment.

One file serves two callers:

- mutmut copies it into its project as `tests/test_harness.py` and runs
  `test_all_cases_hold_verdict_and_code`, once per mutant, with the active
  mutant named in `MUTANT_UNDER_TEST`;
- the experiment runner calls it as a script for the unmutated program and for
  the guard deletions: `python harness_py.py --package-root DIR --label NAME`.

Either way it verifies every case, records (valid, failure code) or the
exception type, writes the record to `$EATF_MUTATION_OUT/<label>.json`, and
then asserts the verdict-and-code oracle O_C on all 25 cases. So the tool's
killed status and the O_C kill computed later from the record must agree.
The harness never reads the failure reason or the report.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def _load_cases() -> list[dict]:
    manifest = os.environ.get("EATF_MUTATION_CASES")
    if not manifest:
        raise RuntimeError("EATF_MUTATION_CASES is not set")
    cases = json.loads(Path(manifest).read_text(encoding="utf-8"))["cases"]
    for case in cases:
        case["_bytes"] = Path(case["package"]).read_bytes()
        pem = case.get("signer_pin_pem")
        case["_pin"] = Path(pem).read_bytes() if pem else None
    return cases


def evaluate(cases: list[dict]) -> list[dict]:
    from eatf_verifier import VerifyOptions, verify  # imported late: mutmut swaps the module

    outcomes = []
    for case in cases:
        options = VerifyOptions()
        if case["_pin"] is not None:
            options.trusted_signer_pems = [case["_pin"]]
        try:
            result = verify(case["_bytes"], options)
            valid = getattr(result, "valid", None)
            code = getattr(result, "failure_code", None)
            # Anything other than a boolean verdict with a string or absent code
            # is recorded as malformed; it kills under every oracle, as in the
            # TypeScript harness.
            if not isinstance(valid, bool) or not (code is None or isinstance(code, str)):
                outcomes.append({
                    "id": case["id"],
                    "valid": None,
                    "code": None,
                    "exception": f"MalformedResult(valid:{type(valid).__name__},"
                                 f"code:{type(code).__name__})",
                })
                continue
            outcomes.append({"id": case["id"], "valid": valid, "code": code, "exception": None})
        except Exception as exc:  # noqa: BLE001 - every exception is an observation
            outcomes.append({
                "id": case["id"],
                "valid": None,
                "code": None,
                "exception": type(exc).__name__,
            })
    return outcomes


def oracle_c_failures(cases: list[dict], outcomes: list[dict]) -> list[str]:
    failures = []
    for case, seen in zip(cases, outcomes, strict=True):
        if seen["exception"] is not None:
            failures.append(f"{case['id']}: raised {seen['exception']}")
        elif seen["valid"] != case["expected_valid"] or seen["code"] != case["expected_code"]:
            failures.append(f"{case['id']}: observed ({seen['valid']}, {seen['code']}), "
                            f"expected ({case['expected_valid']}, {case['expected_code']})")
    return failures


def record(label: str, cases: list[dict], outcomes: list[dict], seconds: float) -> None:
    out = os.environ.get("EATF_MUTATION_OUT")
    if not out:
        return
    path = Path(out) / f"{label}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    import eatf_verifier

    payload = {"label": label, "port": "python", "module": eatf_verifier.__file__,
               "seconds": round(seconds, 4), "outcomes": outcomes}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    tmp.replace(path)


def test_all_cases_hold_verdict_and_code() -> None:
    mutant = os.environ.get("MUTANT_UNDER_TEST", "")
    cases = _load_cases()
    start = time.perf_counter()
    outcomes = evaluate(cases)
    # mutmut's own bookkeeping runs ("", "stats", "fail") are not mutants
    if "__mutmut_" in mutant:
        record(mutant, cases, outcomes, time.perf_counter() - start)
    failures = oracle_c_failures(cases, outcomes)
    assert not failures, "; ".join(failures)


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--package-root", required=True,
                        help="directory that contains the eatf_verifier package to test")
    parser.add_argument("--label", required=True)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path(args.package_root).resolve()))
    cases = _load_cases()
    start = time.perf_counter()
    outcomes = evaluate(cases)
    record(args.label, cases, outcomes, time.perf_counter() - start)
    failures = oracle_c_failures(cases, outcomes)
    for line in failures:
        print(line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
