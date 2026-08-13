"""Accepting-authority conformance for the Python port (spec §4.3).

The acceptance vectors under ../test-vectors/acceptance/ and the five §4.3
packages under ../test-vectors/voiding/ are behavioural: the `--conformance`
harness skips them because they sit outside valid/ and invalid/. They are
nonetheless a two-implementation contract — the §4.3 binding family gates in
BOTH reference verifiers — so this suite pins the Python verdicts against the
same verify-expected.txt contract the TypeScript suites
(lib/test/acceptance-vectors.test.ts, lib/test/voiding-vectors.test.ts) read.

The failure STRINGS may differ between implementations; the failure DECISION
may not.
"""

from __future__ import annotations

import pathlib

import pytest

from eatf_verifier import VerifyOptions, verify

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ACCEPTANCE_DIR = REPO_ROOT / "test-vectors" / "acceptance"
VOIDING_DIR = REPO_ROOT / "test-vectors" / "voiding"

ACCEPTANCE_VECTORS = sorted(p for p in ACCEPTANCE_DIR.rglob("package.aep"))

# The §4.3 packages that live in the voiding tree, with the verdict each must
# produce. The two that stay True are the enforced/advisory line: temporal
# containment and role are appraisal and never reject.
VOIDING_ACCEPTANCE = {
    "tampered-acceptance": False,
    "acceptance-policy-mismatch": False,
    "response-only-with-authority": False,
    "expired-acceptance": True,
    "authority-key-substitution": True,
}


def _expected(path: pathlib.Path) -> bool:
    line = (path.parent / "verify-expected.txt").read_text().splitlines()[0].strip()
    assert line in ("verify=true", "verify=false"), line
    return line == "verify=true"


def test_the_generated_set_is_present() -> None:
    assert len(ACCEPTANCE_VECTORS) >= 4


@pytest.mark.parametrize("path", ACCEPTANCE_VECTORS, ids=lambda p: p.parent.name)
def test_acceptance_vector_is_rejected(path: pathlib.Path) -> None:
    result = verify(path.read_bytes(), VerifyOptions())
    assert _expected(path) is False, f"{path.parent.name} is not a negative vector"
    assert result.valid is False, (
        f"{path.parent.name}: expected rejection, got valid=True"
    )
    assert result.failure_reason, "a rejected vector must carry a failure_reason"
    # A rejection must not drop the §4.3 evidence the run had in hand.
    assert result.accepting_authority is not None
    assert result.accepting_authority["bound_to_output"] is not None


@pytest.mark.parametrize("name,expected", sorted(VOIDING_ACCEPTANCE.items()))
def test_voiding_tree_acceptance_verdict(name: str, expected: bool) -> None:
    path = VOIDING_DIR / name / "package.aep"
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is expected, (
        f"{name}: expected {expected}, got {result.valid} ({result.failure_reason})"
    )
    assert result.valid is _expected(path)


def test_signed_acceptance_is_verified_not_merely_carried() -> None:
    path = REPO_ROOT / "test-vectors" / "valid" / "mandated-and-accepted" / "package.aep"
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is True
    assert result.accepting_authority is not None
    assert result.accepting_authority["key_binding_valid"] is True
    assert result.accepting_authority["bound_to_output"] is True
    # Temporal containment now READS: inspect_tsa() recovers the genTime
    # from the committed RFC 3161 tokens. It did not until the §4.2 port
    # repaired the TSTInfo read (see tests/test_warrant.py); the check is
    # appraisal in both implementations, so no verdict ever diverged, but
    # the appraisal itself was unavailable. It now matches the TypeScript
    # reference on this vector.
    assert result.accepting_authority["temporal_containment"] is True
    # Role is attested-only without a caller trust list.
    assert result.accepting_authority["role_verified"] is None


def test_role_is_advisory_and_never_rejects() -> None:
    """A key the caller does not recognise is REPORTED, never rejected."""
    path = VOIDING_DIR / "authority-key-substitution" / "package.aep"
    genuine = (REPO_ROOT / "test-vectors" / "keys" / "test-accepting-authority.pem").read_bytes()
    result = verify(path.read_bytes(), VerifyOptions(authority_trust_list=[genuine]))
    assert result.accepting_authority is not None
    assert result.accepting_authority["role_verified"] is False
    assert result.accepting_authority["key_binding_valid"] is True
    assert result.valid is True
