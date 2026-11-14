"""RSA DigestInfo handling: RFC 8017 form, the exact legacy form, nothing else.

The legacy fallback once stripped the PKCS#1 v1.5 padding and compared only
the trailing 32 bytes, so a block with arbitrary bytes between the padding
and the digest verified. These tests sign hand-built blocks with the public
development key and check that only the two exact encodings pass.
"""

from __future__ import annotations

import base64
import hashlib
import io
import pathlib
import zipfile

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from eatf_verifier import verify
from eatf_verifier.rsa import (
    SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS,
    load_public_key_pem,
    verify_rsa,
    verify_rsa_digest_info,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VECTORS_ROOT = REPO_ROOT / "test-vectors"
KEY = serialization.load_pem_private_key(
    (VECTORS_ROOT / "keys" / "dev-rsa-4096.key").read_bytes(), password=None
)
BASELINE = VECTORS_ROOT / "valid" / "minimal-roundtrip" / "package.aep"
RFC8017_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
K = (KEY.key_size + 7) // 8


def _raw_sign(block: bytes) -> bytes:
    """Apply the private RSA operation to a hand-built encoded block."""
    numbers = KEY.private_numbers()
    m = int.from_bytes(block, "big")
    return pow(m, numbers.d, numbers.public_numbers.n).to_bytes(K, "big")


def _block(t: bytes) -> bytes:
    """Full-length EMSA-PKCS1-v1_5 block around t."""
    return b"\x00\x01" + b"\xff" * (K - len(t) - 3) + b"\x00" + t


def _entries() -> dict[str, bytes]:
    with zipfile.ZipFile(BASELINE) as z:
        return {n: z.read(n) for n in z.namelist()}


def _package_with(signature: bytes) -> bytes:
    entries = _entries()
    entries["signature.sig"] = base64.b64encode(signature)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return out.getvalue()


def _digest() -> bytes:
    return hashlib.sha256(_entries()["canonical.bin"]).digest()


def test_baseline_is_signed_by_the_development_key() -> None:
    pem = _entries()["public_key.pem"]
    assert load_public_key_pem(pem).public_numbers() == KEY.public_key().public_numbers()


def test_rfc8017_form_passes_the_strict_path() -> None:
    entries = _entries()
    sig = KEY.sign(entries["canonical.bin"], padding.PKCS1v15(), hashes.SHA256())
    assert _raw_sign(_block(RFC8017_PREFIX + _digest())) == sig
    key = load_public_key_pem(entries["public_key.pem"])
    assert verify_rsa(key, sig, entries["canonical.bin"])
    result = verify(_package_with(sig))
    assert result.valid
    assert not any("legacy SHA-256 DigestInfo" in line for line in result.report)


def test_exact_legacy_form_is_accepted_and_reported() -> None:
    sig = _raw_sign(_block(SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS + _digest()))
    key = KEY.public_key()
    assert not verify_rsa(key, sig, _entries()["canonical.bin"])
    assert verify_rsa_digest_info(key, sig, _digest())
    result = verify(_package_with(sig))
    assert result.valid, result.failure_reason
    assert any("legacy SHA-256 DigestInfo" in line for line in result.report)


@pytest.mark.parametrize(
    "label,t,pad_len",
    [
        # Arbitrary bytes between the padding and the digest: accepted up to v0.7.3.
        ("garbage-prefix", b"\x13" * 17, None),
        (
            "garbage-after-legacy-prefix",
            SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS + b"\x00" * 64,
            None,
        ),
        # SHA-512 OID with the right digest length is still not SHA-256.
        ("sha512-oid", bytes.fromhex("302f300b06096086480165030402030420"), None),
        # Padding string shorter than the modulus requires.
        ("short-padding", SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS, 0),
    ],
    ids=["garbage-prefix", "garbage-after-legacy-prefix", "sha512-oid", "short-padding"],
)
def test_other_blocks_ending_in_the_digest_are_rejected(
    label: str, t: bytes, pad_len: int | None
) -> None:
    digest = _digest()
    full_t = t + digest
    if pad_len is None:
        block = _block(full_t)
    else:
        # A short padding string leaves room for bytes placed before the digest.
        head = b"\x00\x01" + b"\xff" * pad_len + b"\x00"
        block = head + b"\x42" * (K - len(head) - len(full_t)) + full_t
    assert len(block) == K and block.endswith(digest)
    sig = _raw_sign(block)
    assert not verify_rsa_digest_info(KEY.public_key(), sig, digest), label
    result = verify(_package_with(sig))
    assert not result.valid
    assert result.failure_code == "RSA_SIGNATURE_INVALID"


@pytest.mark.parametrize(
    "path", sorted((VECTORS_ROOT / "valid").rglob("package.aep")), ids=lambda p: p.parent.name
)
def test_every_valid_vector_uses_the_rfc8017_form(path: pathlib.Path) -> None:
    with zipfile.ZipFile(path) as z:
        key = load_public_key_pem(z.read("public_key.pem"))
        sig = base64.b64decode(z.read("signature.sig").strip())
        assert verify_rsa(key, sig, z.read("canonical.bin"))
