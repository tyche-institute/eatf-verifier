"""RSA verification — RSASSA-PKCS1-v1_5 with SHA-256.

Mirrors lib/src/rsa.ts. The TypeScript reference has two paths:

1. Primary: Web Crypto's RSASSA-PKCS1-v1_5. The Python port uses
   pyca/cryptography, which provides the same algorithm.

2. Legacy-encoding compatibility (read-only): the Java reference signer
   (BouncyCastle NONEwithRSA) emits DigestInfo for SHA-256 with the
   AlgorithmIdentifier parameters absent. RFC 8017 Appendix B.1 requires
   NULL parameters inside EMSA-PKCS1-v1_5, so strict implementations reject
   it and writers MUST NOT produce it.

   The fallback builds the one full-length legacy block for the expected
   digest and compares the whole recovered block with it. Any other
   DigestInfo, a short padding string, or extra bytes are rejected. This is
   what `verifyRsaDigestInfo` does in lib/src/rsa.ts. Versions up to v0.7.3
   compared only the trailing 32 bytes.
"""

from __future__ import annotations

import hmac

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .pem import parse_pem


def rsa_spki_from_pem(pem: bytes) -> bytes:
    """Return the DER SubjectPublicKeyInfo in ``public_key.pem`` or an RSA pin.

    Port of rsaSpkiFromPem in lib/src/rsa.ts: one PEM block labelled PUBLIC KEY
    whose DER is one SEQUENCE with nothing after it. Raises ValueError otherwise.
    """
    label, der = parse_pem(pem)
    if label != "PUBLIC KEY":
        raise ValueError(f"PEM label is {label}, not PUBLIC KEY")
    if _der_sequence_end(der) != len(der):
        raise ValueError("bytes follow the SubjectPublicKeyInfo")
    return der


def load_rsa_spki(spki: bytes) -> rsa.RSAPublicKey:
    """Load an RSA SubjectPublicKeyInfo that is the DER encoding of the key.

    Port of importRsaSpki in lib/src/rsa.ts: the loaded key must encode back to
    the same bytes, so the key that verifies is the only reading of ``spki``.
    """
    key = serialization.load_der_public_key(spki)
    if not isinstance(key, rsa.RSAPublicKey):
        raise TypeError("SubjectPublicKeyInfo does not hold an RSA key")
    encoded = key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    if not hmac.compare_digest(encoded, spki):
        raise ValueError("SubjectPublicKeyInfo is not the DER encoding of an RSA key")
    return key


def load_public_key_pem(pem: bytes) -> rsa.RSAPublicKey:
    return load_rsa_spki(rsa_spki_from_pem(pem))


def _der_sequence_end(der: bytes) -> int:
    """Offset just past the outer DER SEQUENCE, as readSequence reads it in TS."""
    if len(der) < 2 or der[0] != 0x30:
        raise ValueError("Unexpected DER tag.")
    first = der[1]
    if first < 0x80:
        return 2 + first
    count = first & 0x7F
    if count == 0 or count > 4 or len(der) < 2 + count:
        raise ValueError("Unsupported DER length.")
    length = int.from_bytes(der[2 : 2 + count], "big")
    if 2 + count + length > len(der):
        raise ValueError("DER length exceeds input.")
    return 2 + count + length


def verify_rsa(key: rsa.RSAPublicKey, signature: bytes, signed_data: bytes) -> bool:
    """Verify a RSASSA-PKCS1-v1_5 + SHA-256 signature.

    Returns True if the signature is valid for the given data
    under the public key. Returns False on any verification
    failure (does not raise).
    """
    try:
        key.verify(
            signature,
            signed_data,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False


# DER prefix of DigestInfo(SHA-256) with absent AlgorithmIdentifier parameters.
SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS = bytes.fromhex("302f300b06096086480165030402010420")


def verify_rsa_digest_info(
    key: rsa.RSAPublicKey, signature: bytes, expected_digest: bytes
) -> bool:
    """Legacy-encoding compatibility path (read-only).

    Accepts exactly the full-length EMSA-PKCS1-v1_5 block
    0x00 0x01 0xFF..0xFF 0x00 || DigestInfo(SHA-256, absent parameters) || H.
    See module docstring.

    Returns False on any failure; never raises.
    """
    if len(expected_digest) != 32 or len(signature) == 0:
        return False

    numbers = key.public_numbers()
    modulus = numbers.n
    exponent = numbers.e
    modulus_bytes = (modulus.bit_length() + 7) // 8
    if len(signature) != modulus_bytes:
        return False
    sig_int = int.from_bytes(signature, "big")
    if sig_int >= modulus:
        return False

    t = SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS + expected_digest
    if modulus_bytes < len(t) + 11:
        return False
    expected = b"\x00\x01" + b"\xff" * (modulus_bytes - len(t) - 3) + b"\x00" + t
    encoded = pow(sig_int, exponent, modulus).to_bytes(modulus_bytes, "big")
    return hmac.compare_digest(encoded, expected)
