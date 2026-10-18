"""ML-DSA-65 verification using cryptography's FIPS 204 implementation.

PEM keys are parsed by mldsa65_public_key_from_pem, an exact port of the
TypeScript parser, so both verifiers accept and reject the same key text.
"""

from __future__ import annotations

import base64
import functools
import re

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey

ML_DSA_65_PUBLIC_KEY_BYTES = 1952

# RFC 9881 id-ml-dsa-65 SubjectPublicKeyInfo header with absent parameters; the
# same 22 bytes as ML_DSA_65_SPKI_PREFIX in lib/src/mldsa.ts.
_ML_DSA_65_SPKI_PREFIX = bytes.fromhex("308207b2300b0609608648016503040312038207a100")

# Pins and packaged keys, with or without a pin, are parsed exactly as
# lib/src/mldsa.ts parsePem and decodeBase64 parse them, so the two verifiers
# accept and reject the same PEM text. _JS_WHITESPACE is the set that
# JavaScript's String.prototype.trim() and regex \s use.
_JS_WHITESPACE = (
    "\t\n\x0b\x0c\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)
# One body group that starts and ends with whitespace, as in parsePem: the same
# language as [ws]+(...)[ws]+, without cubic backtracking on long whitespace runs.
_PEM_BLOCK = re.compile(
    "-----BEGIN ([A-Z0-9 -]+)-----"
    "([" + _JS_WHITESPACE + "][A-Za-z0-9+/=" + _JS_WHITESPACE + "]+[" + _JS_WHITESPACE + "])"
    "-----END \\1-----"
)
_BASE64_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
)


def mldsa65_public_key_from_pem(public_key_pem: bytes) -> bytes:
    """Return the raw FIPS 204 key from an RFC 9881 SPKI or legacy raw-key PEM.

    Accepts exactly the input that mlDsa65PublicKeyFromPem in lib/src/mldsa.ts
    accepts: one PEM block and nothing else but surrounding whitespace.
    Raises ValueError otherwise.
    """
    text = public_key_pem.decode("utf-8", errors="replace").strip(_JS_WHITESPACE)
    match = _PEM_BLOCK.fullmatch(text)
    if match is None:
        raise ValueError("Malformed PEM block")
    label, der = match.group(1), _forgiving_base64(match.group(2))
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


def _forgiving_base64(body: str) -> bytes:
    """WHATWG forgiving-base64 decode, as atob() applies it after whitespace removal."""
    data = "".join(ch for ch in body if ch not in _JS_WHITESPACE)
    if len(data) % 4 == 0:
        if data.endswith("=="):
            data = data[:-2]
        elif data.endswith("="):
            data = data[:-1]
    if len(data) % 4 == 1 or not _BASE64_ALPHABET.issuperset(data):
        raise ValueError("PEM body is not valid base64")
    return base64.b64decode(data + "=" * (-len(data) % 4))


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
