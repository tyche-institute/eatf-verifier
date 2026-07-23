"""ML-DSA-65 verification, optional.

Mirrors lib/src/mldsa.ts (which uses @noble/post-quantum). The
Python port uses oqs-python (which wraps liboqs). Both libraries
agree on the wire format from NIST FIPS 204.

When the `oqs` extra is not installed, this module's `verify_mldsa65`
raises ImportError, and the higher-level verifier surfaces a
clean "ML-DSA-65 support not compiled in" failure rather than a
verifier crash.
"""

from __future__ import annotations


def verify_mldsa65(public_key_pem: bytes, signature: bytes, signed_data: bytes) -> bool:
    """Verify an ML-DSA-65 signature.

    Public key is PEM-wrapped raw bytes (the EATF convention until
    LAMPS finalises the X.509 wrapping). The raw bytes are the
    FIPS 204 public key serialisation.
    """
    try:
        import oqs  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "ML-DSA-65 verification requires the `oqs` extra: "
            "`pip install eatf-verifier[pqc]`. This depends on "
            "the liboqs native library being present."
        ) from e

    raw = _pem_body(public_key_pem)
    sig = oqs.Signature("ML-DSA-65")
    return sig.verify(signed_data, signature, raw)


def _pem_body(pem: bytes) -> bytes:
    """Strip PEM headers/footers and base64-decode the body."""
    import base64

    text = pem.decode("ascii").strip()
    lines = [line for line in text.splitlines() if not line.startswith("-----")]
    return base64.b64decode("".join(lines))
