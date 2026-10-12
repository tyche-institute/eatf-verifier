"""Caller-supplied ML-DSA-65 signer pin, mirrored from lib/test/pqc-signer-pin.test.ts."""

from __future__ import annotations

import base64
import pathlib
import textwrap
import zipfile

import pytest

from eatf_verifier import VerifyOptions, verify
from eatf_verifier.mldsa import mldsa65_public_key_from_pem

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LAB_PACKAGES = REPO_ROOT / "workshops" / "pqc-hybrid-lab" / "packages"
KEYS = REPO_ROOT / "test-vectors" / "keys"
MLDSA_KEY = (KEYS / "dev-mldsa65.pem").read_bytes()
RSA_KEY = (KEYS / "dev-rsa-4096.pem").read_bytes()


def _package(name: str) -> bytes:
    return (LAB_PACKAGES / name).read_bytes()


def _legacy_raw_pem(spki_pem: bytes) -> bytes:
    body = base64.b64encode(mldsa65_public_key_from_pem(spki_pem)).decode("ascii")
    return (
        "-----BEGIN ML-DSA-65 PUBLIC KEY-----\n"
        + "\n".join(textwrap.wrap(body, 64))
        + "\n-----END ML-DSA-65 PUBLIC KEY-----\n"
    ).encode("ascii")


def test_matching_pin_accepts_hybrid_package() -> None:
    result = verify(
        _package("01-valid-hybrid.aep"),
        VerifyOptions(pqc_policy="required", trusted_pqc_signer_pems=[MLDSA_KEY]),
    )
    assert result.valid is True
    assert result.pqc_valid is True
    assert "ML-DSA-65 signer public key matched" in "\n".join(result.report)


def test_legacy_raw_pem_spelling_matches_decoded_key() -> None:
    result = verify(
        _package("01-valid-hybrid.aep"),
        VerifyOptions(trusted_pqc_signer_pems=[_legacy_raw_pem(MLDSA_KEY)]),
    )
    assert result.valid is True
    assert result.pqc_valid is True


def test_foreign_key_passes_required_policy_without_pin() -> None:
    result = verify(
        _package("07-foreign-mldsa-key.aep"),
        VerifyOptions(pqc_policy="required", trusted_signer_pems=[RSA_KEY]),
    )
    assert result.valid is True
    assert result.pqc_valid is True
    assert "ML-DSA-65 signer identity not evaluated" in "\n".join(result.report)


def test_foreign_key_rejected_by_pin() -> None:
    result = verify(
        _package("07-foreign-mldsa-key.aep"),
        VerifyOptions(
            pqc_policy="required",
            trusted_signer_pems=[RSA_KEY],
            trusted_pqc_signer_pems=[MLDSA_KEY],
        ),
    )
    assert result.valid is False
    assert result.failure_code == "PQC_SIGNER_NOT_TRUSTED"
    assert result.pqc_valid is None


def test_any_member_of_pin_set_matches() -> None:
    with zipfile.ZipFile(LAB_PACKAGES / "07-foreign-mldsa-key.aep") as package:
        foreign_key = package.read("pqc_public_key.pem")
    result = verify(
        _package("01-valid-hybrid.aep"),
        VerifyOptions(trusted_pqc_signer_pems=[foreign_key, MLDSA_KEY]),
    )
    assert result.valid is True


def test_pin_implies_required_policy() -> None:
    result = verify(
        _package("04-classical-transition.aep"),
        VerifyOptions(pqc_policy="if-present", trusted_pqc_signer_pems=[MLDSA_KEY]),
    )
    assert result.valid is False
    assert result.failure_code == "PQC_SIGNATURE_REQUIRED"
    assert "key pin" in (result.failure_reason or "")


def test_malformed_pin_raises() -> None:
    with pytest.raises(ValueError, match=r"trusted_pqc_signer_pems\[0\] is not an ML-DSA-65"):
        verify(_package("01-valid-hybrid.aep"), VerifyOptions(trusted_pqc_signer_pems=[RSA_KEY]))
