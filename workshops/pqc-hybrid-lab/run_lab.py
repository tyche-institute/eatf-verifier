#!/usr/bin/env python3
"""Replay the prepared PQC packages through both public verifiers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGES = HERE / "packages"
MANIFEST = json.loads((PACKAGES / "manifest.json").read_text(encoding="utf-8"))


def verifier_commands() -> tuple[Path, list[str], list[str]]:
    """Locate both verifiers from a checkout or an installed-tool PATH."""

    candidates = []
    if configured_root := os.environ.get("EATF_REPO_ROOT"):
        candidates.append(Path(configured_root).expanduser().resolve())
    candidates.append(HERE.parents[1])

    for root in candidates:
        ts_cli = root / "cli/eatf-verify/bin/eatf-verify.js"
        if not ts_cli.is_file():
            continue
        venv_python = root / ".venv" / (
            "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
        )
        python = str(venv_python if venv_python.exists() else Path(sys.executable))
        return root, ["node", str(ts_cli)], [python, "-m", "eatf_verifier.cli"]

    ts_cli = shutil.which("eatf-verify")
    py_cli = shutil.which("eatf-verify-py")
    if ts_cli and py_cli:
        return HERE, [ts_cli], [py_cli]

    raise RuntimeError(
        "Verifier setup not found. Run 'bash bin/setup.sh' in an eatf-verifier "
        "checkout, then set EATF_REPO_ROOT to that checkout or add its bin/ "
        "directory to PATH."
    )


def invoke(command: list[str], working_directory: Path) -> dict[str, object]:
    completed = subprocess.run(
        command, cwd=working_directory, text=True, capture_output=True, check=False
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
    root, ts_verifier, py_verifier = verifier_commands()
    mismatches = 0
    print("package                              policy         TypeScript  Python  first code")
    for name, expected_package in MANIFEST["packages"].items():
        package = PACKAGES / name
        for policy in ("transitional", "required"):
            flag = [] if policy == "transitional" else ["--require-pqc"]
            ts = invoke([*ts_verifier, "--json", *flag, str(package)], root)
            py = invoke([*py_verifier, "--json", *flag, str(package)], root)
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
