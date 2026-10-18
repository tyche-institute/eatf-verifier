"""Caller-supplied ML-DSA-65 signer pin, mirrored from lib/test/pqc-signer-pin.test.ts."""

from __future__ import annotations

import base64
import io
import json
import pathlib
import textwrap
import zipfile

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from eatf_verifier import VerifyOptions, verify
from eatf_verifier.cli import main
from eatf_verifier.mldsa import mldsa65_public_key_from_pem

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LAB_PACKAGES = REPO_ROOT / "workshops" / "pqc-hybrid-lab" / "packages"
KEYS = REPO_ROOT / "test-vectors" / "keys"
HYBRID = REPO_ROOT / "test-vectors" / "valid" / "hybrid-mldsa65" / "package.aep"
MLDSA_KEY = (KEYS / "dev-mldsa65.pem").read_bytes()
RSA_KEY = (KEYS / "dev-rsa-4096.pem").read_bytes()


def _package(name: str) -> bytes:
    return (LAB_PACKAGES / name).read_bytes()


def _foreign_key() -> bytes:
    with zipfile.ZipFile(LAB_PACKAGES / "07-foreign-mldsa-key.aep") as package:
        return package.read("pqc_public_key.pem")


def _legacy_raw_pem(spki_pem: bytes) -> bytes:
    body = base64.b64encode(mldsa65_public_key_from_pem(spki_pem)).decode("ascii")
    return (
        "-----BEGIN ML-DSA-65 PUBLIC KEY-----\n"
        + "\n".join(textwrap.wrap(body, 64))
        + "\n-----END ML-DSA-65 PUBLIC KEY-----\n"
    ).encode("ascii")


def _with_entry(package: bytes, name: str, data: bytes) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package)) as zin, zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            zout.writestr(info, data if info.filename == name else zin.read(info))
    return out.getvalue()


def test_matching_pin_accepts_hybrid_package() -> None:
    result = verify(
        _package("01-valid-hybrid.aep"),
        VerifyOptions(pqc_policy="required", trusted_pqc_signer_pems=[MLDSA_KEY]),
    )
    assert result.valid is True
    assert result.pqc_valid is True
    assert "ML-DSA-65 signer public key matched" in "\n".join(result.report)


def test_legacy_raw_pem_form_matches_decoded_key() -> None:
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


def test_pin_enforced_under_default_if_present_policy() -> None:
    result = verify(
        _package("07-foreign-mldsa-key.aep"),
        VerifyOptions(trusted_pqc_signer_pems=[MLDSA_KEY]),
    )
    assert result.valid is False
    assert result.failure_code == "PQC_SIGNER_NOT_TRUSTED"
    assert result.pqc_valid is None


@pytest.mark.parametrize("order", ["foreign-first", "dev-first"])
def test_any_member_of_pin_set_matches(order: str) -> None:
    pins = [_foreign_key(), MLDSA_KEY]
    if order == "dev-first":
        pins.reverse()
    result = verify(_package("01-valid-hybrid.aep"), VerifyOptions(trusted_pqc_signer_pems=pins))
    assert result.valid is True


def test_no_member_of_pin_set_matches() -> None:
    other = MLDSA65PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    result = verify(
        _package("01-valid-hybrid.aep"),
        VerifyOptions(trusted_pqc_signer_pems=[_foreign_key(), other]),
    )
    assert result.valid is False
    assert result.failure_code == "PQC_SIGNER_NOT_TRUSTED"


def test_pin_implies_required_policy() -> None:
    result = verify(
        _package("04-classical-transition.aep"),
        VerifyOptions(pqc_policy="if-present", trusted_pqc_signer_pems=[MLDSA_KEY]),
    )
    assert result.valid is False
    assert result.failure_code == "PQC_SIGNATURE_REQUIRED"
    assert "key pin" in (result.failure_reason or "")


@pytest.mark.parametrize("kind", ["rsa", "garbage"])
def test_malformed_packaged_key_with_pin_is_verify_error(kind: str) -> None:
    replacement = RSA_KEY if kind == "rsa" else b"not a PEM block\n"
    result = verify(
        _with_entry(_package("01-valid-hybrid.aep"), "pqc_public_key.pem", replacement),
        VerifyOptions(trusted_pqc_signer_pems=[MLDSA_KEY]),
    )
    assert result.valid is False
    assert result.failure_code == "PQC_VERIFY_ERROR"
    assert result.pqc_valid is None


def test_malformed_pin_raises() -> None:
    with pytest.raises(ValueError, match=r"trusted_pqc_signer_pems\[0\] is not an ML-DSA-65"):
        verify(_package("01-valid-hybrid.aep"), VerifyOptions(trusted_pqc_signer_pems=[RSA_KEY]))


def test_two_block_pin_raises() -> None:
    with pytest.raises(ValueError, match=r"trusted_pqc_signer_pems\[0\] is not an ML-DSA-65"):
        verify(
            _package("01-valid-hybrid.aep"),
            VerifyOptions(trusted_pqc_signer_pems=[MLDSA_KEY + _foreign_key()]),
        )


# The same table is asserted against the TypeScript parser in
# lib/test/pqc-signer-pin.test.ts; both verifiers must agree on every row.
def _unwrap(pem: str) -> str:
    lines = pem.strip().split("\n")
    return f"{lines[0]}\n{''.join(lines[1:-1])}\n{lines[-1]}\n"


END_SPKI = "-----END PUBLIC KEY-----"
END_LEGACY = "-----END ML-DSA-65 PUBLIC KEY-----"
SPELLINGS = [
    ("SPKI as written", lambda s, lg, fg: s, True),
    ("CRLF line endings", lambda s, lg, fg: s.replace("\n", "\r\n"), True),
    ("leading byte-order mark", lambda s, lg, fg: "﻿" + s, True),
    ("surrounding blank lines", lambda s, lg, fg: "\n\n" + s + "\n  \n", True),
    ("body on one line", lambda s, lg, fg: _unwrap(s), True),
    ("legacy raw-key PEM", lambda s, lg, fg: lg, True),
    (
        "legacy raw-key PEM without padding",
        lambda s, lg, fg: lg.replace("=\n-----END", "\n-----END", 1),
        True,
    ),
    ("two PEM blocks", lambda s, lg, fg: s + fg, False),
    ("the same block twice", lambda s, lg, fg: s + s, False),
    ("text before the block", lambda s, lg, fg: "pinned key:\n" + s, False),
    ("text after the block", lambda s, lg, fg: s + "end\n", False),
    ("END label differs from BEGIN", lambda s, lg, fg: s.replace(END_SPKI, END_LEGACY, 1), False),
    ("lower-case label", lambda s, lg, fg: s.replace("PUBLIC KEY", "public key"), False),
    ("'=' inside the body", lambda s, lg, fg: s.replace("-----\nMII", "-----\nM=II", 1), False),
    (
        "SPKI body under the legacy label",
        lambda s, lg, fg: s.replace("PUBLIC KEY", "ML-DSA-65 PUBLIC KEY"),
        False,
    ),
]


@pytest.mark.parametrize(
    ("label", "make", "accepted"), SPELLINGS, ids=[row[0] for row in SPELLINGS]
)
def test_pem_parsing_matches_typescript(label: str, make, accepted: bool) -> None:
    spki = MLDSA_KEY.decode("ascii")
    pem = make(spki, _legacy_raw_pem(MLDSA_KEY).decode("ascii"), _foreign_key().decode("ascii"))
    if accepted:
        expected = mldsa65_public_key_from_pem(MLDSA_KEY)
        assert mldsa65_public_key_from_pem(pem.encode("utf-8")) == expected
    else:
        with pytest.raises(ValueError):
            mldsa65_public_key_from_pem(pem.encode("utf-8"))


# CLI contract: exit 2 for unusable pin files, stderr-only warning.
def test_cli_require_pqc_without_pin_warns(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--require-pqc", str(HYBRID)]) == 0
    assert "warning: --require-pqc without --pqc-signer-key" in capsys.readouterr().err


def test_cli_pin_without_require_pqc_rejects_foreign_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main([
        "--json", "--pqc-signer-key", str(KEYS / "dev-mldsa65.pem"),
        str(LAB_PACKAGES / "07-foreign-mldsa-key.aep"),
    ])
    captured = capsys.readouterr()
    assert code == 1
    assert json.loads(captured.out)["failure_code"] == "PQC_SIGNER_NOT_TRUSTED"
    assert "warning" not in captured.err


@pytest.mark.parametrize("kind", ["rsa", "two-blocks", "missing"])
def test_cli_unusable_pin_file_exits_2(
    kind: str, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / f"{kind}.pem"
    if kind == "rsa":
        path.write_bytes(RSA_KEY)
    elif kind == "two-blocks":
        path.write_bytes(MLDSA_KEY + _foreign_key())
    code = main(["--pqc-signer-key", str(path), str(HYBRID)])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    if kind == "missing":
        assert "cannot read --pqc-signer-key" in captured.err
    else:
        assert "is not an ML-DSA-65 public key" in captured.err
