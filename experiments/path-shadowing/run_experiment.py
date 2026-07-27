#!/usr/bin/env python3
"""Path-shadowing demonstration on shipped code.

Builds four packages from one valid seed — two written naively, two written so
that the earlier guard is cleared first — runs both shipped verifiers over all
four, and reports for each whether the decision state the mutation targets was
actually reached.

Predictions are recorded in oracle.json before execution. The runner reports
whether each prediction held; a wrong prediction is printed as such and is not
silently corrected.
"""

from __future__ import annotations

import base64
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GENERATED = HERE / "generated"

sys.path.insert(0, str(REPO_ROOT / "experiments" / "decision-path"))
from generate_corpus import apply_operator, rewrite, rewrite_receipt  # noqa: E402


def build(operator: str, baseline: bytes) -> bytes:
    """The two naive operators live here; the refined ones come from the
    decision-path generator unchanged, so the pair differs only as documented."""
    if operator == "remove_overt_signature_file_only":
        return rewrite(baseline, removals={"overt_receipt.sig"})
    if operator == "empty_timestamp_file_only":
        return rewrite(baseline, replacements={"timestamp.tsr": b""})
    return apply_operator(operator, baseline)


def verify_ts(package: Path) -> dict:
    proc = subprocess.run(
        ["node", str(HERE / "run-ts.mjs"), str(package)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"TypeScript runner failed: {proc.stderr[:400]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def verify_py(package: Path) -> dict:
    from eatf_verifier import verify  # noqa: PLC0415

    report = verify(package.read_bytes())
    return {"valid": report.valid, "failureCode": report.failure_code}


def main() -> int:
    oracle = json.loads((HERE / "oracle.json").read_text(encoding="utf-8"))
    baseline = (REPO_ROOT / oracle["baseline"]).read_bytes()
    GENERATED.mkdir(exist_ok=True)

    rows = []
    for case in oracle["cases"]:
        case_dir = GENERATED / case["id"]
        case_dir.mkdir(exist_ok=True)
        package = case_dir / "package.aep"
        package.write_bytes(build(case["operator"], baseline))

        ts = verify_ts(package)
        py = verify_py(package)
        ts_code, py_code = ts.get("failureCode"), py.get("failureCode")

        reached = ts_code == case["targets_state"] and py_code == case["targets_state"]
        both_reject = (not ts.get("valid")) and (not py.get("valid"))
        outcome = "reaches_target" if reached else ("shadowed" if both_reject else "accepted")
        rows.append({
            "id": case["id"],
            "targets_state": case["targets_state"],
            "prediction": case["prediction"],
            "predicted_observed_code": case["predicted_observed_code"],
            "ts_valid": ts.get("valid"),
            "ts_code": ts_code,
            "py_valid": py.get("valid"),
            "py_code": py_code,
            "cross_language_agree": ts.get("valid") == py.get("valid") and ts_code == py_code,
            "outcome": outcome,
            "prediction_held": outcome == case["prediction"]
                and ts_code == case["predicted_observed_code"],
            "package_sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
        })

    shadowed = [r for r in rows if r["outcome"] == "shadowed"]
    summary = {
        "cases": len(rows),
        "rejected_by_both_implementations": sum(1 for r in rows if not r["ts_valid"] and not r["py_valid"]),
        "reached_their_target_state": sum(1 for r in rows if r["outcome"] == "reaches_target"),
        "shadowed": len(shadowed),
        "shadowed_ids": [r["id"] for r in shadowed],
        "predictions_held": f"{sum(1 for r in rows if r['prediction_held'])}/{len(rows)}",
        "cross_language_agreement": f"{sum(1 for r in rows if r['cross_language_agree'])}/{len(rows)}",
    }

    payload = {
        "schema": "urn:eatf:experiment:path-shadowing-results:1",
        "environment": {
            "python": platform.python_version(),
            "node": subprocess.run(["node", "-v"], capture_output=True, text=True).stdout.strip(),
        },
        "summary": summary,
        "rows": rows,
    }
    (GENERATED / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = ["case,targets_state,ts_code,py_code,outcome,prediction_held"]
    for r in rows:
        lines.append(f"{r['id']},{r['targets_state']},{r['ts_code']},{r['py_code']},"
                     f"{r['outcome']},{str(r['prediction_held']).lower()}")
    (GENERATED / "results.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    digest = hashlib.sha256((GENERATED / "results.csv").read_bytes()).hexdigest()
    (GENERATED / "SHA256SUMS").write_text(
        f"{digest}  generated/results.csv\n"
        f"{hashlib.sha256((HERE / 'oracle.json').read_bytes()).hexdigest()}  oracle.json\n",
        encoding="utf-8")

    print("# Path-shadowing demonstration")
    for k, v in summary.items():
        print(f"- {k}: {v}")
    for r in rows:
        mark = "ok " if r["prediction_held"] else "NO "
        print(f"  [{mark}] {r['id']}: targets {r['targets_state']}, "
              f"observed ts={r['ts_code']} py={r['py_code']} -> {r['outcome']}")
    print(f"- results.csv digest: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
