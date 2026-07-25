#!/usr/bin/env python3
"""Run the independent oracle against the TypeScript and Python verifiers."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GENERATED = HERE / "generated"
CORPUS = GENERATED / "corpus"
RESULTS = GENERATED / "results"

sys.path.insert(0, str(REPO_ROOT / "lib-python"))
from eatf_verifier import VerifyOptions, verify


def python_results(oracle: dict) -> list[dict]:
    matching = (REPO_ROOT / "test-vectors/keys/dev-rsa-4096.pem").read_bytes()
    mismatching = (REPO_ROOT / "test-vectors/keys/dev-tsa-rsa-3072.pem").read_bytes()
    output = []
    for case in oracle["cases"]:
        options = VerifyOptions()
        if case.get("signer_pin") == "matching":
            options.trusted_signer_pems = [matching]
        if case.get("signer_pin") == "mismatching":
            options.trusted_signer_pems = [mismatching]
        result = verify((CORPUS / case["id"] / "package.aep").read_bytes(), options)
        output.append(
            {
                "id": case["id"],
                "valid": result.valid,
                "failure_code": result.failure_code,
                "failure_reason": result.failure_reason,
            }
        )
    return output


def typescript_results() -> list[dict]:
    completed = subprocess.run(
        ["node", str(HERE / "run-ts.mjs")],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    )
    return [json.loads(line) for line in completed.stdout.splitlines() if line]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    subprocess.run(
        [sys.executable, str(HERE / "generate_corpus.py")],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(["npm", "run", "build"], cwd=REPO_ROOT, check=True)

    oracle = json.loads((HERE / "oracle.json").read_text(encoding="utf-8"))
    expected = {item["id"]: item for item in oracle["cases"]}
    ts = {item["id"]: item for item in typescript_results()}
    py = {item["id"]: item for item in python_results(oracle)}

    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_id, item in expected.items():
        ts_result = ts[case_id]
        py_result = py[case_id]
        oracle_ts = (
            ts_result["valid"] == item["expected_valid"]
            and ts_result["failure_code"] == item["expected_code"]
        )
        oracle_py = (
            py_result["valid"] == item["expected_valid"]
            and py_result["failure_code"] == item["expected_code"]
        )
        cross_language = (
            ts_result["valid"] == py_result["valid"]
            and ts_result["failure_code"] == py_result["failure_code"]
        )
        rows.append(
            {
                "id": case_id,
                "expected_valid": item["expected_valid"],
                "expected_code": item["expected_code"],
                "ts_valid": ts_result["valid"],
                "ts_code": ts_result["failure_code"],
                "py_valid": py_result["valid"],
                "py_code": py_result["failure_code"],
                "oracle_ts": oracle_ts,
                "oracle_py": oracle_py,
                "cross_language": cross_language,
            }
        )

    with (RESULTS / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    raw = {
        "schema": "urn:eatf:experiment:decision-path-results:1",
        "environment": {
            "python": platform.python_version(),
            "node": subprocess.check_output(["node", "--version"], text=True).strip(),
            "platform": platform.platform(),
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
            ).strip(),
        },
        "rows": rows,
    }
    (RESULTS / "results.json").write_text(
        json.dumps(raw, indent=2) + "\n",
        encoding="utf-8",
    )

    total = len(rows)
    oracle_matches = sum(row["oracle_ts"] and row["oracle_py"] for row in rows)
    parity = sum(row["cross_language"] for row in rows)
    states = sorted(
        {row["expected_code"] for row in rows if row["expected_code"] is not None}
    )
    summary = f"""# Decision-path experiment result

- Cases: {total}
- Distinct expected rejection states: {len(states)}
- Oracle matches in both implementations: {oracle_matches}/{total}
- TypeScript/Python verdict-and-code agreement: {parity}/{total}
- Boolean mismatches: {sum(row["ts_valid"] != row["py_valid"] for row in rows)}
- First-failure-code mismatches: {sum(row["ts_code"] != row["py_code"] for row in rows)}

The oracle was fixed in `oracle.json` before verifier execution. Each case
changes one predeclared condition or invocation parameter. The corpus is not
the repository's 4+7 conformance suite and does not vary transport roots.
"""
    (RESULTS / "SUMMARY.md").write_text(summary, encoding="utf-8")

    checksummed = sorted(CORPUS.rglob("*")) + [
        HERE / "oracle.json",
        RESULTS / "results.csv",
        RESULTS / "results.json",
        RESULTS / "SUMMARY.md",
    ]
    checksum_lines = [
        f"{sha256(path)}  {path.relative_to(HERE)}"
        for path in checksummed
        if path.is_file()
    ]
    (RESULTS / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="ascii",
    )

    print(summary, end="")
    return 0 if oracle_matches == total and parity == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
