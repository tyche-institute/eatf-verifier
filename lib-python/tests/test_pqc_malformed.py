"""Malformed ML-DSA entries yield valid=False with a stable first-failure code.

lib/test/pqc-malformed.test.ts runs the same cases against the TypeScript
verifier; both ports must report the same code for each. The tests at the end
cover the Python-only PQC_SUPPORT_UNAVAILABLE path.
"""

from __future__ import annotations

import io
import pathlib
import sys
import zipfile
from collections.abc import Callable

import pytest

from eatf_verifier import VerifyOptions, mldsa, verify
from eatf_verifier.verifier import VerifyResult

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LAB_PACKAGES = REPO_ROOT / "workshops" / "pqc-hybrid-lab" / "packages"
KEYS = REPO_ROOT / "test-vectors" / "keys"
RSA_PUBLIC_KEY = KEYS / "dev-rsa-4096.pem"
NOT_BASE64 = b"!!!not-base64!!!\n"


def _pinned() -> VerifyOptions:
    # dev-mldsa65.pem is the key that signed 01-valid-hybrid.aep.
    return VerifyOptions(trusted_pqc_signer_pems=[(KEYS / "dev-mldsa65.pem").read_bytes()])


PIN_MODES = pytest.mark.parametrize(
    "options", [VerifyOptions, _pinned], ids=["without a key pin", "with a key pin"]
)


def _lab_entries(name: str) -> dict[str, bytes]:
    with zipfile.ZipFile(LAB_PACKAGES / name) as package:
        return {entry: package.read(entry) for entry in package.namelist()}


def _verify_replacing(
    replacements: dict[str, bytes],
    base: str = "01-valid-hybrid.aep",
    options: VerifyOptions | None = None,
) -> VerifyResult:
    entries = {**_lab_entries(base), **replacements}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        for name, data in entries.items():
            package.writestr(name, data)
    return verify(output.getvalue(), options)


def _signature() -> bytes:
    return _lab_entries("01-valid-hybrid.aep")["signature_pqc.sig"].strip()


def _outcome(result: VerifyResult) -> tuple[bool, str | None, bool | None]:
    return (result.valid, result.failure_code, result.pqc_valid)


def _wrap(signature: bytes, separators: bytes) -> bytes:
    lines = [signature[i : i + 64] for i in range(0, len(signature), 64)]
    return b"".join(
        line + separators[i % len(separators) : i % len(separators) + 1]
        for i, line in enumerate(lines)
    )


BAD_SIGNATURES: list[tuple[str, Callable[[bytes], bytes]]] = [
    ("text that is not base64", lambda sig: NOT_BASE64),
    (
        "a stray character inside the valid signature",
        lambda sig: sig[:100] + b"!" + sig[100:] + b"\n",
    ),
    ("base64 without its padding", lambda sig: b"AAAAAA\n"),
    ("padding in the middle", lambda sig: b"AA==AA==\n"),
    ("excess padding", lambda sig: b"AAAA====\n"),
    ("the URL-safe alphabet", lambda sig: sig.replace(b"+", b"-").replace(b"/", b"_") + b"\n"),
    ("a non-ASCII byte", lambda sig: sig + b"\xff\n"),
    ("a UTF-8 byte-order mark", lambda sig: b"\xef\xbb\xbf" + sig),
    ("a non-breaking space", lambda sig: sig[:100] + b"\xc2\xa0" + sig[100:]),
]


def test_rsa_key_in_pqc_public_key_fails_pqc_verify_error() -> None:
    result = _verify_replacing({"pqc_public_key.pem": RSA_PUBLIC_KEY.read_bytes()})
    assert _outcome(result) == (False, "PQC_VERIFY_ERROR", False)


def test_pqc_public_key_that_is_not_pem_fails_pqc_verify_error() -> None:
    result = _verify_replacing({"pqc_public_key.pem": b"garbage\n"})
    assert _outcome(result) == (False, "PQC_VERIFY_ERROR", False)


def test_empty_pqc_public_key_fails_pqc_verify_error() -> None:
    result = _verify_replacing({"pqc_public_key.pem": b""})
    assert _outcome(result) == (False, "PQC_VERIFY_ERROR", False)


def test_empty_mldsa_pair_added_to_a_classical_package_is_rejected() -> None:
    result = _verify_replacing(
        {"signature_pqc.sig": b"", "pqc_public_key.pem": b""},
        base="04-classical-transition.aep",
    )
    assert _outcome(result) == (False, "PQC_VERIFY_ERROR", False)


@PIN_MODES
@pytest.mark.parametrize(
    "mutate", [mutate for _, mutate in BAD_SIGNATURES], ids=[label for label, _ in BAD_SIGNATURES]
)
def test_undecodable_signature_fails_pqc_signature_encoding(
    mutate: Callable[[bytes], bytes], options: Callable[[], VerifyOptions]
) -> None:
    result = _verify_replacing({"signature_pqc.sig": mutate(_signature())}, options=options())
    assert _outcome(result) == (False, "PQC_SIGNATURE_ENCODING", False)


@PIN_MODES
def test_multi_megabyte_signature_entry_is_decoded(
    options: Callable[[], VerifyOptions],
) -> None:
    result = _verify_replacing(
        {"signature_pqc.sig": b"A" * 4_600_000 + b"\n"}, options=options()
    )
    assert _outcome(result) == (False, "PQC_SIGNATURE_INVALID", False)


@PIN_MODES
def test_signature_wrapped_at_64_columns_with_crlf_still_verifies(
    options: Callable[[], VerifyOptions],
) -> None:
    signature = _signature()
    lines = [signature[i : i + 64] for i in range(0, len(signature), 64)]
    result = _verify_replacing(
        {"signature_pqc.sig": b"\r\n".join(lines) + b"\r\n"}, options=options()
    )
    assert _outcome(result) == (True, None, True)


@PIN_MODES
def test_each_ascii_whitespace_byte_inside_the_signature_is_ignored(
    options: Callable[[], VerifyOptions],
) -> None:
    signature = _wrap(_signature(), b"\t\n\x0b\x0c\r ")
    result = _verify_replacing({"signature_pqc.sig": signature}, options=options())
    assert _outcome(result) == (True, None, True)


def test_without_a_pin_signature_encoding_is_reported_before_an_unusable_key() -> None:
    result = _verify_replacing(
        {"signature_pqc.sig": NOT_BASE64, "pqc_public_key.pem": RSA_PUBLIC_KEY.read_bytes()}
    )
    assert _outcome(result) == (False, "PQC_SIGNATURE_ENCODING", False)


def test_with_a_pin_an_unusable_key_is_reported_before_the_signature_encoding() -> None:
    result = _verify_replacing(
        {"signature_pqc.sig": NOT_BASE64, "pqc_public_key.pem": RSA_PUBLIC_KEY.read_bytes()},
        options=_pinned(),
    )
    assert _outcome(result) == (False, "PQC_VERIFY_ERROR", None)


def test_with_a_pin_a_foreign_key_is_reported_before_the_signature_encoding() -> None:
    result = _verify_replacing(
        {"signature_pqc.sig": NOT_BASE64}, base="07-foreign-mldsa-key.aep", options=_pinned()
    )
    assert _outcome(result) == (False, "PQC_SIGNER_NOT_TRUSTED", None)


def test_unimportable_mldsa_support_fails_pqc_support_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "eatf_verifier.mldsa", None)
    assert _outcome(_verify_replacing({})) == (False, "PQC_SUPPORT_UNAVAILABLE", None)


def test_signature_encoding_is_checked_before_mldsa_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "eatf_verifier.mldsa", None)
    result = _verify_replacing({"signature_pqc.sig": NOT_BASE64})
    assert _outcome(result) == (False, "PQC_SIGNATURE_ENCODING", False)


@PIN_MODES
def test_backend_without_mldsa_fails_pqc_support_unavailable(
    monkeypatch: pytest.MonkeyPatch, options: Callable[[], VerifyOptions]
) -> None:
    monkeypatch.setattr(mldsa, "mldsa65_supported", lambda: False)
    result = _verify_replacing({}, options=options())
    assert _outcome(result) == (False, "PQC_SUPPORT_UNAVAILABLE", None)
