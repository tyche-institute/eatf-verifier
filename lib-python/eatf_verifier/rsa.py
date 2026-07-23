"""RSA verification — RSASSA-PKCS1-v1_5 with SHA-256.

Mirrors lib/src/rsa.ts. The TypeScript reference has two paths:

1. Primary: Web Crypto's RSASSA-PKCS1-v1_5. The Python port uses
   pyca/cryptography, which provides the same algorithm.

2. Java-reference compatibility: the backend signs DigestInfo
   (SHA-256, hash) with NONEwithRSA via BouncyCastle. BC emits the
   SHA-256 AlgorithmIdentifier without the NULL parameters that
   strict ASN.1 RSASSA-PKCS1-v1_5 implementations expect, so some
   library combinations reject the wire signature even though the
   underlying RSA operation succeeds.

   The fallback performs the raw RSA public operation, strips the
   PKCS#1 v1.5 padding, and compares the trailing 32-byte digest
   to the expected SHA-256 hash. This is what `verifyRsaDigestInfo`
   does in lib/src/rsa.ts.
"""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def load_public_key_pem(pem: bytes) -> rsa.RSAPublicKey:
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, rsa.RSAPublicKey):
        raise TypeError("public_key.pem is not an RSA key")
    return key


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


def verify_rsa_digest_info(
    key: rsa.RSAPublicKey, signature: bytes, expected_digest: bytes
) -> bool:
    """Java-reference compatibility path.

    Performs the raw RSA public operation, strips PKCS#1 v1.5
    padding, and compares the trailing 32-byte digest with the
    given expected_digest. See module docstring.

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
    recovered_int = pow(sig_int, exponent, modulus)
    encoded = recovered_int.to_bytes(modulus_bytes, "big")

    # PKCS#1 v1.5 encoded message: 0x00 || 0x01 || 0xFF...0xFF || 0x00 || DigestInfo
    if len(encoded) < 11 or encoded[0] != 0x00 or encoded[1] != 0x01:
        return False
    sep = -1
    for i in range(2, len(encoded)):
        if encoded[i] == 0x00:
            sep = i
            break
        if encoded[i] != 0xFF:
            return False
    if sep < 0:
        return False
    digest_info = encoded[sep + 1 :]
    if len(digest_info) < len(expected_digest):
        return False
    recovered_digest = digest_info[-len(expected_digest) :]
    return _ct_eq(recovered_digest, expected_digest)


def _ct_eq(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b, strict=True):
        result |= x ^ y
    return result == 0
