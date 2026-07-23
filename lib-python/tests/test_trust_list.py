"""Pinned-trust-list integrity tests — Python port of
`lib/test/tsa-trust-list.test.ts`.

Guards the three DigiCert root PEMs against silent mutation. A
trust anchor that drifts from upstream is a security regression,
not a refactor, so an accidental byte edit anywhere in
`tsa_trust_list.py` fails the corresponding assertion immediately.
"""

from __future__ import annotations

import base64
import hashlib

import pytest
from cryptography.x509 import load_der_x509_certificate

from eatf_verifier.tsa_trust_list import (
    DEFAULT_TSA_TRUST_LIST,
    DIGICERT_ASSURED_ID_ROOT_CA_PEM,
    DIGICERT_GLOBAL_ROOT_CA_PEM,
    DIGICERT_ROOT_FINGERPRINTS,
    DIGICERT_TRUSTED_ROOT_G4_PEM,
)


def _pem_to_der(pem: bytes) -> bytes:
    text = pem.decode("ascii").strip()
    body = "".join(
        line for line in text.splitlines() if not line.startswith("-----")
    )
    return base64.b64decode(body)


def _colon_fingerprint(der: bytes) -> str:
    return ":".join(f"{b:02X}" for b in hashlib.sha256(der).digest())


def test_default_trust_list_is_the_three_pinned_digicert_roots() -> None:
    assert len(DEFAULT_TSA_TRUST_LIST) == 3
    assert DIGICERT_GLOBAL_ROOT_CA_PEM in DEFAULT_TSA_TRUST_LIST
    assert DIGICERT_ASSURED_ID_ROOT_CA_PEM in DEFAULT_TSA_TRUST_LIST
    assert DIGICERT_TRUSTED_ROOT_G4_PEM in DEFAULT_TSA_TRUST_LIST


@pytest.mark.parametrize(
    ("name", "pem"),
    [
        ("DigiCertGlobalRootCA", DIGICERT_GLOBAL_ROOT_CA_PEM),
        ("DigiCertAssuredIDRootCA", DIGICERT_ASSURED_ID_ROOT_CA_PEM),
        ("DigiCertTrustedRootG4", DIGICERT_TRUSTED_ROOT_G4_PEM),
    ],
    ids=["GlobalRootCA", "AssuredIDRootCA", "TrustedRootG4"],
)
def test_pinned_pem_matches_published_fingerprint(name: str, pem: bytes) -> None:
    expected = DIGICERT_ROOT_FINGERPRINTS[name]
    actual = _colon_fingerprint(_pem_to_der(pem))
    assert actual == expected, (
        f"{name} fingerprint drift — PEM was mutated. "
        f"Expected {expected}, got {actual}."
    )


@pytest.mark.parametrize(
    "pem",
    DEFAULT_TSA_TRUST_LIST,
    ids=["GlobalRootCA", "AssuredIDRootCA", "TrustedRootG4"],
)
def test_each_pinned_pem_parses_as_x509(pem: bytes) -> None:
    der = _pem_to_der(pem)
    cert = load_der_x509_certificate(der)
    # Sanity: every pinned root has a non-empty subject and is self-signed
    # (issuer DN equals subject DN). Catches accidentally pinning an
    # intermediate.
    assert cert.subject.rfc4514_string()
    assert cert.subject.rfc4514_string() == cert.issuer.rfc4514_string(), (
        f"Pinned cert is not self-signed: {cert.subject.rfc4514_string()}"
    )
