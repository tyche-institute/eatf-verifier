"""ML-DSA-65 verification using cryptography's FIPS 204 implementation."""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey

ML_DSA_65_PUBLIC_KEY_BYTES = 1952


def mldsa65_public_key_from_pem(public_key_pem: bytes) -> bytes:
    """Return the raw FIPS 204 key from an RFC 9881 SPKI or legacy raw-key PEM."""
    if b"-----BEGIN PUBLIC KEY-----" in public_key_pem:
        try:
            key = serialization.load_pem_public_key(public_key_pem)
        except UnsupportedAlgorithm as exc:
            raise ValueError(f"unsupported SubjectPublicKeyInfo algorithm: {exc}") from exc
        if not isinstance(key, MLDSA65PublicKey):
            raise ValueError("SubjectPublicKeyInfo is not an ML-DSA-65 public key")
        return key.public_bytes_raw()
    if b"-----BEGIN ML-DSA-65 PUBLIC KEY-----" in public_key_pem:
        raw = _pem_body(public_key_pem)
        if len(raw) != ML_DSA_65_PUBLIC_KEY_BYTES:
            raise ValueError("Legacy ML-DSA-65 raw public key must be 1952 bytes")
        return raw
    raise ValueError("Unsupported ML-DSA-65 PEM label")


def verify_mldsa65(public_key_pem: bytes, signature: bytes, signed_data: bytes) -> bool:
    """Verify an RFC 9881 SPKI key, with read-only legacy raw-PEM support."""
    if b"-----BEGIN PUBLIC KEY-----" in public_key_pem:
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, MLDSA65PublicKey):
            raise ValueError("pqc_public_key.pem is not an ML-DSA-65 public key")
    else:
        key = MLDSA65PublicKey.from_public_bytes(_pem_body(public_key_pem))
    try:
        key.verify(signature, signed_data)
    except InvalidSignature:
        return False
    return True


def _pem_body(pem: bytes) -> bytes:
    """Strip PEM headers/footers and base64-decode the body."""
    import base64

    text = pem.decode("ascii").strip()
    lines = [line for line in text.splitlines() if not line.startswith("-----")]
    return base64.b64decode("".join(lines))
