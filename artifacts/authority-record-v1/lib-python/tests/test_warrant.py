"""Warrant conformance for the Python port (spec §4.2).

The vectors under ../test-vectors/warrant/ — plus the valid conformance
vector ../test-vectors/valid/warranted-action/ — are behavioural: the
`--conformance` harness skips them because they sit outside valid/ and
invalid/. They are nonetheless a two-implementation contract, so this
suite pins the Python verdicts, diagnostics and tri-states against the
SAME expected-warrant.json files the TypeScript suite
(lib/test/warrant-vectors.test.ts) reads.

Unlike the sibling suites, the diagnostic STRINGS are asserted verbatim
here, not just the decision: the article's cross-implementation claim is
verdict AND diagnostic, vector by vector.

Several of these packages verify VALID on purpose. Only three §4.2 checks
gate — digest, record, policy linkage — plus the acceptance signature;
binding form, applicability and freshness are appraisal, and an output
whose warrant does not apply may inform but carries no warrant to compel.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from eatf_verifier import VerifyOptions, verify

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WARRANT_DIR = REPO_ROOT / "test-vectors" / "warrant"
WARRANTED_ACTION_DIR = REPO_ROOT / "test-vectors" / "valid" / "warranted-action"

VECTOR_DIRS = [WARRANTED_ACTION_DIR] + sorted(
    d for d in WARRANT_DIR.iterdir() if d.is_dir()
)

# The four §4.2 negatives that GATE. Each breaks one property, so a
# rejection names one check.
GATING_NEGATIVES = (
    "warrant-digest-mismatch",
    "warrant-swap",
    "warrant-acceptance-forged",
    "warrant-acceptance-stripped",
)

# VerifyResult.warrant is snake_case here and camelCase in the TypeScript
# reference the expectation files were written against.
FIELD_NAMES = {
    "present": "present",
    "bound": "bound",
    "policyLinked": "policy_linked",
    "applicable": "applicable",
    "acceptanceVerified": "acceptance_verified",
    "fresh": "fresh",
}


def _expectation(directory: pathlib.Path) -> dict:
    return json.loads((directory / "expected-warrant.json").read_text())["expect"]


def test_the_generated_set_is_present() -> None:
    assert len(VECTOR_DIRS) >= 9


@pytest.mark.parametrize("directory", VECTOR_DIRS, ids=lambda d: d.name)
def test_warrant_vector_matches_the_shared_expectation(directory: pathlib.Path) -> None:
    expected = _expectation(directory)
    result = verify((directory / "package.aep").read_bytes(), VerifyOptions())

    assert result.valid is expected["valid"], (
        f"{directory.name}: expected valid={expected['valid']}, "
        f"got {result.valid} ({result.failure_reason})"
    )
    if "failureReason" in expected:
        assert result.failure_reason == expected["failureReason"]
    if "canonicalForm" in expected:
        assert result.canonical_form == expected["canonicalForm"]
    if "warrant" in expected:
        assert result.warrant is not None
        for camel, snake in FIELD_NAMES.items():
            if camel in expected["warrant"]:
                assert result.warrant[snake] == expected["warrant"][camel], (
                    f"{directory.name}: warrant.{snake}"
                )


@pytest.mark.parametrize("name", GATING_NEGATIVES)
def test_the_gating_negatives_reject(name: str) -> None:
    """The four §4.2 negatives the TypeScript verifier rejects, and the
    frozen verify-expected.txt contract, must also reject here — with the
    same diagnostic. Before the §4.2 port these four verified TRUE in
    Python, the only verdict divergence in the corpus."""
    directory = WARRANT_DIR / name
    contract = (directory / "verify-expected.txt").read_text().splitlines()
    assert contract[0].strip() == "verify=false"
    diagnostic = contract[1].split("=", 1)[1].strip()

    result = verify((directory / "package.aep").read_bytes(), VerifyOptions())
    assert result.valid is False
    assert result.failure_reason == diagnostic
    # A rejection must not drop the §4.2 evidence the run had in hand.
    assert result.warrant is not None
    assert result.warrant["present"] is True


def test_a_valid_warranted_package_verifies_with_every_tri_state_true() -> None:
    result = verify((WARRANTED_ACTION_DIR / "package.aep").read_bytes(), VerifyOptions())
    assert result.valid is True
    assert result.warrant == {
        "present": True,
        "bound": True,
        "policy_linked": True,
        "applicable": True,
        "acceptance_verified": True,
        # Freshness needs a TSA that chains to a trusted root: an
        # untrusted clock can refute freshness but never establish it,
        # and no shipped token chains. Not determinable, not false.
        "fresh": None,
    }
    assert (
        "Warrant verified (urn:eatf:warrant:demo:atap-basic-allow-01, "
        "accepted by test-accepting-authority)." in result.report
    )


def test_binding_form_is_appraisal_not_a_gate() -> None:
    """Unlike §4.5, a warrant carried under the response-only form stays
    accepted; the unbound state is reported loudly."""
    result = verify(
        (WARRANT_DIR / "warrant-unbound" / "package.aep").read_bytes(), VerifyOptions()
    )
    assert result.valid is True
    assert result.canonical_form == "response-only"
    assert result.warrant is not None
    assert result.warrant["bound"] is False
    assert (
        "Warrant present but unbound: the response-only canonical form "
        "leaves metadata.warrant_digest outside signature.sig." in result.report
    )


def test_applicability_is_appraisal_not_a_gate() -> None:
    for name in ("warrant-decision-void", "warrant-inapplicable-action"):
        result = verify(
            (WARRANT_DIR / name / "package.aep").read_bytes(), VerifyOptions()
        )
        assert result.valid is True, name
        assert result.warrant is not None
        assert result.warrant["applicable"] is False, name
        assert (
            "Warrant does not apply to this action: the output may inform "
            "but carries no warrant to compel." in result.report
        ), name


def test_freshness_is_appraisal_and_reads_the_rfc3161_gentime() -> None:
    """warrant-stale's window closed before the package's genTime. The
    verdict stays true and fresh=False is reported — which also pins the
    TSTInfo read: before it was repaired the Python port never recovered a
    genTime, so this appraisal silently returned None on every vector."""
    result = verify(
        (WARRANT_DIR / "warrant-stale" / "package.aep").read_bytes(), VerifyOptions()
    )
    assert result.valid is True
    assert result.warrant is not None
    assert result.warrant["fresh"] is False
    assert any(
        line.startswith("Warrant not in force at signing time: genTime ")
        for line in result.report
    )
