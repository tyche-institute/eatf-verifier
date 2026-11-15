"""One reading of public_key.pem, metadata.json and the base64 signature entries.

lib/test/strict-entries.test.ts runs the same cases against the TypeScript
verifier; both ports must report the same first-failure code for each.
"""

from __future__ import annotations

import base64
import io
import pathlib
import zipfile
from collections.abc import Callable

from eatf_verifier import VerifyOptions, verify

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VECTORS = REPO_ROOT / "test-vectors"
# Current profile form, so metadata.json is bound by the signature; it also
# carries a marked overt_receipt.sig.
BASE = VECTORS / "valid" / "minimal-roundtrip" / "package.aep"
# dev-rsa-4096.pem is the key that signed minimal-roundtrip.
SIGNER_PEM = (VECTORS / "keys" / "dev-rsa-4096.pem").read_bytes()

Entries = dict[str, bytes]


def _verify_replacing(
    replace: Callable[[Entries], None] = lambda e: None,
    options: VerifyOptions | None = None,
) -> tuple[bool, str | None]:
    with zipfile.ZipFile(BASE) as package:
        entries = {name: package.read(name) for name in package.namelist()}
    replace(entries)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        for name, data in entries.items():
            package.writestr(name, data)
    result = verify(output.getvalue(), options)
    return (result.valid, result.failure_code)


def _pem_body(pem: bytes) -> bytes:
    return b"".join(
        line.strip() for line in pem.splitlines() if line.strip() and not line.startswith(b"-----")
    )


def _pem_of(label: bytes, body: bytes, eol: bytes = b"\n", width: int = 64) -> bytes:
    lines = [body[i : i + width] for i in range(0, len(body), width)]
    return (
        b"-----BEGIN " + label + b"-----" + eol
        + eol.join(lines) + eol
        + b"-----END " + label + b"-----" + eol
    )


def _nested(depth: int) -> bytes:
    # A member holding depth - 1 arrays inside the top-level object.
    return b"[" * (depth - 1) + b"]" * (depth - 1)


def _set(name: str, value: Callable[[bytes], bytes]) -> Callable[[Entries], None]:
    def replace(entries: Entries) -> None:
        entries[name] = value(entries[name])

    return replace


# public_key.pem


def test_base_package_verifies() -> None:
    assert _verify_replacing() == (True, None)


def test_public_key_accepts_crlf_and_other_line_widths() -> None:
    replace = _set(
        "public_key.pem", lambda pem: _pem_of(b"PUBLIC KEY", _pem_body(pem), b"\r\n", 76)
    )
    assert _verify_replacing(replace) == (True, None)


def test_public_key_rejects_two_pem_blocks() -> None:
    assert _verify_replacing(_set("public_key.pem", lambda pem: pem + pem)) == (
        False,
        "RSA_VERIFY_ERROR",
    )


def test_public_key_rejects_the_pkcs1_label() -> None:
    replace = _set("public_key.pem", lambda pem: _pem_of(b"RSA PUBLIC KEY", _pem_body(pem)))
    assert _verify_replacing(replace) == (False, "RSA_VERIFY_ERROR")


def test_public_key_rejects_bytes_after_the_spki() -> None:
    def replace(pem: bytes) -> bytes:
        der = base64.b64decode(_pem_body(pem)) + b"\x05\x00"
        return _pem_of(b"PUBLIC KEY", base64.b64encode(der))

    assert _verify_replacing(_set("public_key.pem", replace)) == (False, "RSA_VERIFY_ERROR")


def test_signer_pin_matches_on_the_der_whatever_its_line_layout() -> None:
    pin = _pem_of(b"PUBLIC KEY", _pem_body(SIGNER_PEM), b"\r\n", 76)
    assert _verify_replacing(options=VerifyOptions(trusted_signer_pems=[pin])) == (True, None)


def test_signer_pin_of_two_pem_blocks_matches_nothing() -> None:
    options = VerifyOptions(trusted_signer_pems=[SIGNER_PEM + SIGNER_PEM])
    assert _verify_replacing(options=options) == (False, "SIGNER_NOT_TRUSTED")


# metadata.json


def _prefix_member(member: bytes) -> Callable[[Entries], None]:
    return _set("metadata.json", lambda text: b"{" + member + b"," + text.removeprefix(b"{"))


def test_metadata_rejects_a_repeated_member_name() -> None:
    replace = _prefix_member(b'"schema":"urn:example:other"')
    assert _verify_replacing(replace) == (False, "METADATA_INVALID_JSON")


def test_metadata_rejects_a_repeated_member_name_written_with_an_escape() -> None:
    replace = _prefix_member(b'"sch\\u0065ma":"urn:example:other"')
    assert _verify_replacing(replace) == (False, "METADATA_INVALID_JSON")


def test_metadata_allows_one_name_in_two_different_objects() -> None:
    replace = _prefix_member(b'"x":{"schema":1}')
    assert _verify_replacing(replace) == (False, "CANONICAL_FORM_MISMATCH")


def test_metadata_rejects_a_byte_order_mark() -> None:
    replace = _set("metadata.json", lambda text: b"\xef\xbb\xbf" + text)
    assert _verify_replacing(replace) == (False, "METADATA_INVALID_JSON")


def test_metadata_rejects_bytes_that_are_not_utf8() -> None:
    replace = _set("metadata.json", lambda text: b'{"x":"\xff"}')
    assert _verify_replacing(replace) == (False, "METADATA_INVALID_JSON")


def test_metadata_rejects_a_nan_literal() -> None:
    replace = _set("metadata.json", lambda text: b'{"x":NaN}')
    assert _verify_replacing(replace) == (False, "METADATA_INVALID_JSON")


def test_metadata_allows_64_nested_levels_and_rejects_65() -> None:
    def at(depth: int) -> tuple[bool, str | None]:
        return _verify_replacing(
            _set("metadata.json", lambda text: b'{"x":' + _nested(depth) + b"}")
        )

    assert at(64) == (False, "CANONICAL_FORM_MISMATCH")
    assert at(65) == (False, "METADATA_INVALID_JSON")


# signature entries


def test_signature_accepts_crlf_wrapped_base64() -> None:
    def replace(sig: bytes) -> bytes:
        sig = sig.strip()
        return b"\r\n".join(sig[i : i + 64] for i in range(0, len(sig), 64)) + b"\r\n"

    assert _verify_replacing(_set("signature.sig", replace)) == (True, None)


def test_signature_rejects_missing_padding() -> None:
    replace = _set("signature.sig", lambda sig: sig.strip().rstrip(b"="))
    assert _verify_replacing(replace) == (False, "RSA_SIGNATURE_ENCODING")


def test_signature_rejects_a_nul_byte_inside_the_base64() -> None:
    replace = _set("signature.sig", lambda sig: sig[:100] + b"\x00" + sig[100:])
    assert _verify_replacing(replace) == (False, "RSA_SIGNATURE_ENCODING")


def test_receipt_signature_rejects_a_nul_byte_inside_the_base64() -> None:
    replace = _set("overt_receipt.sig", lambda sig: sig[:100] + b"\x00" + sig[100:])
    assert _verify_replacing(replace) == (False, "OVERT_SIGNATURE_ERROR")


def test_unreadable_timestamp_is_reported_as_such_not_as_missing() -> None:
    result = verify((VECTORS / "invalid" / "bad-timestamp" / "package.aep").read_bytes())
    assert result.failure_code == "TSA_MISSING_OR_INVALID"
    assert result.failure_reason == (
        "timestamp.tsr is empty or not a readable RFC 3161 TimeStampResp or token."
    )
