"""ML-DSA-65 verification using cryptography's FIPS 204 implementation.

PEM keys are parsed by mldsa65_public_key_from_pem, an exact port of the
TypeScript parser, so both verifiers accept and reject the same key text.
"""

from __future__ import annotations

import functools

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey

from .pem import parse_pem

ML_DSA_65_PUBLIC_KEY_BYTES = 1952

# RFC 9881 id-ml-dsa-65 SubjectPublicKeyInfo header with absent parameters; the
# same 22 bytes as ML_DSA_65_SPKI_PREFIX in lib/src/mldsa.ts.
_ML_DSA_65_SPKI_PREFIX = bytes.fromhex("308207b2300b0609608648016503040312038207a100")


def mldsa65_public_key_from_pem(public_key_pem: bytes) -> bytes:
    """Return the raw FIPS 204 key from an RFC 9881 SPKI or legacy raw-key PEM.

    Accepts exactly the input that mlDsa65PublicKeyFromPem in lib/src/mldsa.ts
    accepts: one PEM block and nothing else but surrounding whitespace.
    Raises ValueError otherwise.
    """
    label, der = parse_pem(public_key_pem)
    if label == "PUBLIC KEY":
        if len(der) != len(_ML_DSA_65_SPKI_PREFIX) + ML_DSA_65_PUBLIC_KEY_BYTES:
            raise ValueError("ML-DSA-65 SubjectPublicKeyInfo has the wrong length")
        if not der.startswith(_ML_DSA_65_SPKI_PREFIX):
            raise ValueError(
                "ML-DSA-65 SubjectPublicKeyInfo must use id-ml-dsa-65 with absent parameters"
            )
        return der[len(_ML_DSA_65_SPKI_PREFIX):]
    if label == "ML-DSA-65 PUBLIC KEY":
        if len(der) != ML_DSA_65_PUBLIC_KEY_BYTES:
            raise ValueError("Legacy ML-DSA-65 raw public key must be 1952 bytes")
        return der
    raise ValueError(f"Unsupported ML-DSA-65 PEM label: {label}")


def verify_mldsa65_raw(public_key: bytes, signature: bytes, signed_data: bytes) -> bool:
    """Verify with a raw 1952-byte FIPS 204 public key, as verifyMlDsa65 does in TS."""
    try:
        MLDSA65PublicKey.from_public_bytes(public_key).verify(signature, signed_data)
    except (InvalidSignature, ValueError):
        return False
    return True


@functools.cache
def mldsa65_supported() -> bool:
    """Whether the cryptography backend implements ML-DSA-65 (OpenSSL 3.5 or later).

    Probed without the package's key, so the answer cannot depend on input.
    """
    try:
        MLDSA65PublicKey.from_public_bytes(bytes(ML_DSA_65_PUBLIC_KEY_BYTES))
    except UnsupportedAlgorithm:
        return False
    return True


def verify_mldsa65(public_key_pem: bytes, signature: bytes, signed_data: bytes) -> bool:
    """Verify against a PEM key parsed as verifyMlDsa65 in lib/src/mldsa.ts parses it.

    Raises ValueError for a key that mldsa65_public_key_from_pem rejects.
    """
    return verify_mldsa65_raw(mldsa65_public_key_from_pem(public_key_pem), signature, signed_data)
