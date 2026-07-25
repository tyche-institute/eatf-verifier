"""Conformance tests — Python verifier vs the bundled test vectors.

The same vectors drive the TypeScript verifier's conformance test
(see cli/eatf-verify/test/conformance.test.mjs). Both ports must
agree on every vector; if a vector flips, the spec or a verifier
is wrong, not the test.
"""

from __future__ import annotations

import io
import json
import pathlib
import zipfile

import pytest

from eatf_verifier import VerifyOptions, verify

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VECTORS_ROOT = REPO_ROOT / "test-vectors"


def _walk(category: str) -> list[pathlib.Path]:
    root = VECTORS_ROOT / category
    return sorted(p for p in root.rglob("package.aep"))


VALID_VECTORS = _walk("valid")
INVALID_VECTORS = _walk("invalid")


@pytest.mark.parametrize("path", VALID_VECTORS, ids=lambda p: p.parent.name)
def test_valid_vector_verifies(path: pathlib.Path) -> None:
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is True, (
        f"{path.parent.name} should verify but failed: {result.failure_reason}"
    )


@pytest.mark.parametrize("path", INVALID_VECTORS, ids=lambda p: p.parent.name)
def test_invalid_vector_rejected(path: pathlib.Path) -> None:
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is False, (
        f"{path.parent.name} should be rejected but verified clean"
    )
    assert result.failure_reason, "rejected vector must include a failure_reason"
    assert result.failure_code, "rejected vector must include a stable failure_code"


def test_explicit_signer_key_pin_accepts_matching_key() -> None:
    package = VECTORS_ROOT / "valid" / "minimal-roundtrip" / "package.aep"
    signer_key = (VECTORS_ROOT / "keys" / "dev-rsa-4096.pem").read_bytes()
    result = verify(
        package.read_bytes(),
        VerifyOptions(trusted_signer_pems=[signer_key]),
    )
    assert result.valid is True
    assert "Signer public key matched" in "\n".join(result.report)


def test_explicit_signer_key_pin_rejects_other_key() -> None:
    package = VECTORS_ROOT / "valid" / "minimal-roundtrip" / "package.aep"
    other_key = (VECTORS_ROOT / "keys" / "dev-tsa-rsa-3072.pem").read_bytes()
    result = verify(
        package.read_bytes(),
        VerifyOptions(trusted_signer_pems=[other_key]),
    )
    assert result.valid is False
    assert "caller-supplied trust set" in (result.failure_reason or "")


def _rewrite_package(
    source: bytes,
    replacements: dict[str, bytes] | None = None,
    removals: set[str] | None = None,
) -> bytes:
    replacements = replacements or {}
    removals = removals or set()
    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(source), "r") as original,
        zipfile.ZipFile(output, "w") as rewritten,
    ):
        for info in original.infolist():
            if info.filename in removals:
                continue
            rewritten.writestr(
                info,
                replacements.get(info.filename, original.read(info.filename)),
            )
    return output.getvalue()


def test_current_signer_binds_receipt_only_fields() -> None:
    package = VECTORS_ROOT / "valid" / "minimal-roundtrip" / "package.aep"
    source = package.read_bytes()
    with zipfile.ZipFile(io.BytesIO(source), "r") as archive:
        receipt = json.loads(archive.read("overt_receipt.json"))
    receipt["scope"] = "foundational:changed-after-signing"
    tampered = _rewrite_package(
        source,
        {"overt_receipt.json": json.dumps(receipt).encode() + b"\n"},
    )

    result = verify(tampered)

    assert result.valid is False
    assert "receipt signature" in (result.failure_reason or "")


def test_current_signer_receipt_signature_is_downgrade_protected() -> None:
    package = VECTORS_ROOT / "valid" / "minimal-roundtrip" / "package.aep"
    tampered = _rewrite_package(package.read_bytes(), removals={"overt_receipt.sig"})

    result = verify(tampered)

    assert result.valid is False
    assert "overt_receipt.sig" in (result.failure_reason or "")


def _zip_with_names(names: list[str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name in names:
            archive.writestr(name, b"x")
    return output.getvalue()


def test_rejects_more_than_32_zip_entries() -> None:
    result = verify(_zip_with_names([f"entry-{index}.txt" for index in range(33)]))
    assert result.valid is False
    assert "too many ZIP entries" in (result.failure_reason or "")


def test_rejects_nested_zip_entry_names() -> None:
    result = verify(_zip_with_names(["nested/entry.txt"]))
    assert result.valid is False
    assert "flat, safe names" in (result.failure_reason or "")
    assert result.failure_code == "ZIP_INVALID_OR_UNSAFE"


def test_rejects_metadata_json_that_is_not_an_object() -> None:
    package = VECTORS_ROOT / "valid" / "minimal-roundtrip" / "package.aep"
    changed = _rewrite_package(
        package.read_bytes(),
        replacements={"metadata.json": b"[]\n"},
    )
    result = verify(changed)
    assert result.valid is False
    assert result.failure_code == "METADATA_NOT_OBJECT"


def test_rejects_half_present_mldsa_pair() -> None:
    package = VECTORS_ROOT / "valid" / "minimal-roundtrip" / "package.aep"
    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(package.read_bytes()), "r") as original,
        zipfile.ZipFile(output, "w") as rewritten,
    ):
        for info in original.infolist():
            rewritten.writestr(info, original.read(info.filename))
        rewritten.writestr("signature_pqc.sig", b"bmVnYXRpdmUtY29udHJvbA==\n")
    result = verify(output.getvalue())
    assert result.valid is False
    assert result.failure_code == "PQC_PAIR_INCOMPLETE"
