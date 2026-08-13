"""Unit tests for :func:`eatf_verifier.tsa.verify_tsa_trust`.

The trust-list check is a *single-step pin*: the TSA signing
cert's issuer DN must equal one of the pinned roots' subject DN.
This is not full RFC 5280 path validation — it matches the
TypeScript reference's behaviour byte-for-byte.

These tests synthesise small :class:`TsaCheck` values and assert
the three return cases (trusted / not trusted / skipped).
"""

from __future__ import annotations

from eatf_verifier.tsa import TsaCheck, verify_tsa_trust
from eatf_verifier.tsa_trust_list import (
    DEFAULT_TSA_TRUST_LIST,
    DIGICERT_GLOBAL_ROOT_CA_PEM,
)

# Subject DN of DigiCert Global Root CA in pyca/cryptography's
# RFC 4514 string form. This is what `cert.subject.rfc4514_string()`
# returns for that cert; verify_tsa_trust compares against it.
DIGICERT_GLOBAL_ROOT_SUBJECT = (
    "CN=DigiCert Global Root CA,OU=www.digicert.com,O=DigiCert Inc,C=US"
)


def _check(*, embedded_cert_count: int, signer_issuer: str | None) -> TsaCheck:
    return TsaCheck(
        tsa_present=True,
        raw_size_bytes=1024,
        gen_time="2026-01-01T00:00:00+00:00",
        message_imprint_matches=True,
        signature_verified=True,
        signer_subject="CN=DigiCert Timestamp 2024,O=DigiCert Inc,C=US",
        signer_issuer=signer_issuer,
        embedded_cert_count=embedded_cert_count,
    )


def test_returns_none_when_no_embedded_cert() -> None:
    chk = _check(embedded_cert_count=0, signer_issuer=None)
    result = verify_tsa_trust(chk, DEFAULT_TSA_TRUST_LIST)
    assert result.trusted is None
    assert "no embedded cert" in result.reason


def test_returns_none_when_trust_list_empty() -> None:
    chk = _check(
        embedded_cert_count=1,
        signer_issuer=DIGICERT_GLOBAL_ROOT_SUBJECT,
    )
    result = verify_tsa_trust(chk, [])
    assert result.trusted is None
    assert "Empty trust list" in result.reason


def test_returns_true_when_signer_issuer_matches_pinned_root() -> None:
    chk = _check(
        embedded_cert_count=1,
        signer_issuer=DIGICERT_GLOBAL_ROOT_SUBJECT,
    )
    result = verify_tsa_trust(chk, [DIGICERT_GLOBAL_ROOT_CA_PEM])
    assert result.trusted is True
    assert DIGICERT_GLOBAL_ROOT_SUBJECT in result.reason


def test_returns_false_when_signer_issuer_does_not_match_any_root() -> None:
    chk = _check(
        embedded_cert_count=1,
        signer_issuer="CN=Not A Real Root,O=Made Up,C=ZZ",
    )
    result = verify_tsa_trust(chk, DEFAULT_TSA_TRUST_LIST)
    assert result.trusted is False
    assert "Not A Real Root" in result.reason


def test_tsa_not_present_returns_none() -> None:
    chk = TsaCheck(
        tsa_present=False,
        raw_size_bytes=0,
        gen_time=None,
        message_imprint_matches=None,
        signature_verified=None,
        signer_subject=None,
        signer_issuer=None,
        embedded_cert_count=0,
    )
    result = verify_tsa_trust(chk, DEFAULT_TSA_TRUST_LIST)
    assert result.trusted is None
