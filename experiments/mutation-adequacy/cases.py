#!/usr/bin/env python3
"""Build the case manifest for the mutation-adequacy experiment.

The suite is the 25 named cases as deposited: 21 decision-path cases and 4
path-shadowing cases. Nothing here invents a case or an expectation. Every
expected value is copied from the two oracle files, and every package is checked
against the digest its own experiment recorded.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
WORK = HERE / "work"
DP = REPO_ROOT / "experiments" / "decision-path"
PS = REPO_ROOT / "experiments" / "path-shadowing"
PIN_KEYS = {
    "matching": REPO_ROOT / "test-vectors" / "keys" / "dev-rsa-4096.pem",
    "mismatching": REPO_ROOT / "test-vectors" / "keys" / "dev-tsa-rsa-3072.pem",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guard_of(code: str | None, guards: dict) -> str | None:
    if code is None:
        return None
    owners = [name for name, meta in guards.items() if code in meta["codes"]]
    if len(owners) != 1:
        raise SystemExit(f"code {code} belongs to {owners}, expected exactly one guard")
    return owners[0]


def _load_path_shadowing_builder():
    """Import path-shadowing's own build() under a private module name, so it
    cannot be confused with this experiment's or decision-path's runner."""
    spec = importlib.util.spec_from_file_location("ps_run_experiment", PS / "run_experiment.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build


def build_cases() -> list[dict]:
    regions = json.loads((HERE / "guard-regions.json").read_text(encoding="utf-8"))
    guards = regions["guards"]

    deposited = {}
    for line in (DP / "generated" / "results" / "SHA256SUMS").read_text().splitlines():
        digest, path = line.split("  ", 1)
        deposited[path] = digest

    cases: list[dict] = []
    for case in json.loads((DP / "oracle.json").read_text(encoding="utf-8"))["cases"]:
        rel = f"generated/corpus/{case['id']}/package.aep"
        package = DP / rel
        digest = sha256(package.read_bytes())
        if digest != deposited[rel]:
            raise SystemExit(f"decision-path package differs from its deposit: {case['id']}")
        pin = case.get("signer_pin")
        cases.append({
            "id": case["id"],
            "source": "decision-path",
            "package": str(package),
            "package_sha256": digest,
            "signer_pin": pin,
            "signer_pin_pem": str(PIN_KEYS[pin]) if pin else None,
            "expected_valid": case["expected_valid"],
            "expected_code": case["expected_code"],
            "target_code": case["expected_code"],
            "target_guard": guard_of(case["expected_code"], guards),
        })

    build = _load_path_shadowing_builder()
    ps_oracle = json.loads((PS / "oracle.json").read_text(encoding="utf-8"))
    ps_digests = {
        row["id"]: row["package_sha256"]
        for row in json.loads((PS / "generated" / "results.json").read_text(encoding="utf-8"))["rows"]
    }
    baseline = (REPO_ROOT / ps_oracle["baseline"]).read_bytes()
    for case in ps_oracle["cases"]:
        out = WORK / "cases" / case["id"] / "package.aep"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(build(case["operator"], baseline))
        digest = sha256(out.read_bytes())
        if digest != ps_digests[case["id"]]:
            raise SystemExit(f"path-shadowing package differs from its deposit: {case['id']}")
        cases.append({
            "id": case["id"],
            "source": "path-shadowing",
            "package": str(out),
            "package_sha256": digest,
            "signer_pin": None,
            "signer_pin_pem": None,
            "expected_valid": False,
            "expected_code": case["predicted_observed_code"],
            "target_code": case["targets_state"],
            "target_guard": guard_of(case["targets_state"], guards),
        })

    if len(cases) != 25 or len({c["id"] for c in cases}) != 25:
        raise SystemExit(f"expected 25 named cases, found {len(cases)}")
    return cases


def main() -> int:
    cases = build_cases()
    WORK.mkdir(exist_ok=True)
    manifest = {
        "schema": "urn:eatf:experiment:mutation-adequacy-cases:1",
        "cases": cases,
    }
    (WORK / "cases.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    packages = {c["package_sha256"] for c in cases}
    invocations = {(c["package_sha256"], c["signer_pin"]) for c in cases}
    print(f"cases: {len(cases)} named, {len(invocations)} distinct (package, invocation), "
          f"{len(packages)} distinct packages -> {WORK / 'cases.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
