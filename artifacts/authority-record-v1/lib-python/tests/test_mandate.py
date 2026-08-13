"""Detached-mandate conformance for the Python port (spec §4.5).

The mandate vectors under ../test-vectors/mandate/ are behavioural: the
`--conformance` harness skips them because they sit outside valid/ and
invalid/. They are nonetheless a two-implementation contract — the §4.5
binding family gates in BOTH reference verifiers — so this suite pins
the Python verdicts against the same verify-expected.txt contract the
TypeScript suite (lib/test/mandate-vectors.test.ts) reads.

The failure STRINGS may differ between implementations; the failure
DECISION may not.
"""

from __future__ import annotations

import pathlib

import pytest

from eatf_verifier import VerifyOptions, verify

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MANDATE_DIR = REPO_ROOT / "test-vectors" / "mandate"

MANDATE_VECTORS = sorted(p for p in MANDATE_DIR.rglob("package.aep"))


def _expected(path: pathlib.Path) -> bool:
    line = (path.parent / "verify-expected.txt").read_text().splitlines()[0].strip()
    assert line in ("verify=true", "verify=false"), line
    return line == "verify=true"


@pytest.mark.parametrize("path", MANDATE_VECTORS, ids=lambda p: p.parent.name)
def test_mandate_vector_verdict(path: pathlib.Path) -> None:
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is _expected(path), (
        f"{path.parent.name}: expected {_expected(path)}, "
        f"got {result.valid} ({result.failure_reason})"
    )


def test_signed_mandate_is_verified_not_merely_carried() -> None:
    path = REPO_ROOT / "test-vectors" / "valid" / "mandated-action" / "package.aep"
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is True
    assert result.mandate is not None
    assert result.mandate["claimed"] is True
    assert result.mandate["bound"] is True
    assert result.mandate["signature_verified"] is True
    assert result.mandate["in_scope"] is True
    assert result.mandate["principal"] == "urn:eatf:mandate:demo:granting-authority"
    # Temporal containment now READS: inspect_tsa() recovers the genTime
    # from the committed RFC 3161 tokens. It did not until the §4.2 port
    # repaired the TSTInfo read — asn1crypto hands back an already-parsed
    # structure, and re-loading its .native raised on every well-formed
    # token, leaving this appraisal silently None corpus-wide. The check is
    # advisory in both implementations, so no verdict ever diverged; the
    # APPRAISAL was simply unavailable. It now matches the TypeScript
    # reference on this vector.
    assert result.mandate["temporal_containment"] is True


def test_reference_only_principal_claims_nothing() -> None:
    path = MANDATE_DIR / "mandate-reference-only" / "package.aep"
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is True
    assert result.mandate is not None
    assert result.mandate["claimed"] is False
    assert result.mandate["bound"] is None
    assert result.mandate["signature_verified"] is None


def test_forged_mandate_signature_rejects() -> None:
    path = MANDATE_DIR / "mandate-signature-forged" / "package.aep"
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is False
    assert result.mandate is not None
    assert result.mandate["signature_verified"] is False


def test_profile_form_policy_rewrite_rejects() -> None:
    """The remedy-side falsification: the deny-to-allow rewrite that
    succeeds on a response-only package fails on the two-layer profile-form
    package, in this implementation as in the TypeScript one."""
    path = REPO_ROOT / "test-vectors" / "invalid" / "profile-form-policy-rewrite" / "package.aep"
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is False
    assert result.failure_reason == "canonical.bin does not match a supported canonical form."


def test_issuer_pinning_separates_the_reauthored_package() -> None:
    """Spec §8.1, the boundary of the remedy: the re-authored package
    verifies under the self-attestation default and is rejected once the
    real issuer's key is pinned. Same frozen bytes, both runs."""
    path = (
        REPO_ROOT
        / "test-vectors"
        / "boundary"
        / "reauthored-package-issuer-substitution"
        / "package.aep"
    )
    dev_pem = (REPO_ROOT / "test-vectors" / "keys" / "dev-rsa-4096.pem").read_bytes()
    unpinned = verify(path.read_bytes(), VerifyOptions())
    assert unpinned.valid is True
    assert unpinned.metadata is not None
    assert unpinned.metadata["policy_decision"] == "allow"
    pinned = verify(path.read_bytes(), VerifyOptions(trusted_signer_pems=[dev_pem]))
    assert pinned.valid is False
    assert pinned.failure_reason == (
        "public_key.pem is not a member of the caller-supplied trustedSignerPems list."
    )
