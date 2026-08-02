#!/usr/bin/env python3
"""Replay the prepared PQC packages through both public verifiers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = Path(__file__).resolve().parent / "packages"
MANIFEST = json.loads((PACKAGES / "manifest.json").read_text(encoding="utf-8"))
VENV_PYTHON = ROOT / ".venv" / (
    "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
)
PYTHON = str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable))
TS_VERIFIER = ["node", str(ROOT / "cli/eatf-verify/bin/eatf-verify.js")]
PY_VERIFIER = [PYTHON, "-m", "eatf_verifier.cli"]


def invoke(command: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(f"{' '.join(command)} failed:\n{completed.stderr}")
    return json.loads(completed.stdout)


def observed(result: dict[str, object]) -> dict[str, object]:
    return {
        "valid": result["valid"],
        "failureCode": result.get("failureCode", result.get("failure_code")),
        "pqcValid": result.get("pqcValid", result.get("pqc_valid")),
    }


def main() -> int:
    mismatches = 0
    print("package                              policy         TypeScript  Python  first code")
    for name, expected_package in MANIFEST["packages"].items():
        package = PACKAGES / name
        for policy in ("transitional", "required"):
            flag = [] if policy == "transitional" else ["--require-pqc"]
            ts = invoke([*TS_VERIFIER, "--json", *flag, str(package)])
            py = invoke([*PY_VERIFIER, "--json", *flag, str(package)])
            ts_observed = observed(ts)
            py_observed = observed(py)
            expected = expected_package[policy]
            ok = ts_observed == expected and py_observed == expected
            mismatches += 0 if ok else 1
            print(
                f"{name:36} {policy:14} "
                f"{ts_observed['valid']!s:10}  {py_observed['valid']!s:6}  "
                f"{ts_observed['failureCode'] or '-'}"
            )
            if not ok:
                print(f"  expected={expected} ts={ts_observed} py={py_observed}")
    print(f"\nCross-language policy mismatches: {mismatches}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
