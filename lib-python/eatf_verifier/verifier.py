"""Top-level verifier — Python port of lib/src/verifier.ts.

Public entrypoint:

    from eatf_verifier import verify
    result = verify(b"...")           # accepts raw bytes
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
from dataclasses import dataclass, field
from typing import Any

from .canonical import jcs
from .hash import sha256, to_hex
from .overt import parse_and_validate_overt_receipt
from .rsa import load_public_key_pem, verify_rsa, verify_rsa_digest_info
from .tsa import inspect_tsa, verify_tsa_trust
from .tsa_trust_list import DEFAULT_TSA_TRUST_LIST


@dataclass
class VerifyOptions:
    """Caller-supplied verification configuration."""

    offline_only: bool = True
    tsa_trust_list: list[bytes] = field(default_factory=list)
    """List of PEM-encoded TSA root certificates. When empty the
    verifier falls through to :data:`DEFAULT_TSA_TRUST_LIST`
    (the three DigiCert public roots, mirroring the TypeScript
    reference). Pass ``[b""]`` or an explicit empty list semantics
    via a wrapper if you want to opt out of the chain check
    entirely (the v0.2.1 contract treats empty as fall-through;
    a future minor may add an explicit ``skip`` sentinel)."""


@dataclass
class VerifyResult:
    valid: bool
    report: list[str] = field(default_factory=list)
    failure_reason: str | None = None
    pqc_valid: bool | None = None
    tsa_trusted: bool | None = None
    metadata: dict[str, Any] | None = None
    overt_receipt: dict[str, Any] | None = None


REQUIRED_ENTRIES = (
    "response.txt",
    "canonical.bin",
    "hash.sha256",
    "signature.sig",
    "public_key.pem",
    "metadata.json",
    "timestamp.tsr",
)


def verify(data: bytes, options: VerifyOptions | None = None) -> VerifyResult:
    """Verify an .aep package. Returns a VerifyResult."""
    opts = options or VerifyOptions()
    report: list[str] = []
    metadata: dict[str, Any] | None = None

    # 1. Unzip.
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            entries = {name: zf.read(name) for name in zf.namelist()}
    except Exception:
        return _fail(report, "Package is not a valid ZIP.", metadata)
    report.append(f"Package unzipped ({len(entries)} entries).")

    # 2. Required entries.
    for name in REQUIRED_ENTRIES:
        if name not in entries:
            return _fail(report, f"Missing required entry: {name}.", metadata)

    # 3. Parse metadata.
    try:
        metadata = json.loads(entries["metadata.json"].decode("utf-8"))
        if not isinstance(metadata, dict):
            return _fail(report, "metadata.json is not a JSON object.", None)
    except Exception:
        return _fail(report, "metadata.json is not valid JSON.", None)
    report.append("metadata.json parsed.")

    # 4. Canonical-form check (accept either profile or response-only form).
    response = entries["response.txt"]
    canonical = entries["canonical.bin"]
    profile_canonical = response + b"\n" + jcs(metadata)
    if _ct_eq(profile_canonical, canonical):
        report.append("Canonical bytes match AEP profile canonical form.")
    elif _ct_eq(response, canonical):
        report.append("Canonical bytes match Java response-only canonical form.")
    else:
        return _fail(
            report,
            "canonical.bin does not match a supported canonical form.",
            metadata,
        )

    # 5. Hash check.
    expected_hash_hex = entries["hash.sha256"].decode("ascii").strip().lower()
    actual_hash = sha256(canonical)
    actual_hash_hex = to_hex(actual_hash)
    if actual_hash_hex != expected_hash_hex:
        return _fail(report, "Hash mismatch.", metadata)
    report.append("SHA-256 hash matches.")

    # 6. RSA signature.
    pem = entries["public_key.pem"]
    sig_b64 = entries["signature.sig"].decode("ascii").strip()
    try:
        sig = base64.b64decode(sig_b64, validate=False)
    except Exception:
        return _fail(report, "signature.sig is not valid base64.", metadata)
    try:
        key = load_public_key_pem(pem)
        rsa_ok = verify_rsa(key, sig, canonical)
        if not rsa_ok:
            # Java-reference compatibility: BouncyCastle DigestInfo
            # encoding without NULL parameters in the SHA-256
            # AlgorithmIdentifier. Strip padding and compare digests.
            rsa_ok = verify_rsa_digest_info(key, sig, actual_hash)
    except Exception as e:
        return _fail(report, f"RSA verify error: {e}.", metadata)
    if not rsa_ok:
        return _fail(
            report, "RSA signature does not verify against public_key.pem.", metadata
        )
    report.append("RSA-4096 signature verified.")

    # 7. OVERT receipt.
    receipt, err = parse_and_validate_overt_receipt(entries, metadata, expected_hash_hex)
    if err:
        return _fail(report, f"overt_receipt.json invalid: {err}.", metadata, None, receipt)
    if receipt is not None:
        report.append(f"OVERT receipt verified ({receipt.get('scope')!s}).")
    else:
        report.append("OVERT receipt absent (optional profile entry).")

    # 8. Optional ML-DSA-65 verification.
    pqc_valid: bool | None = None
    if entries.get("signature_pqc.sig") and entries.get("pqc_public_key.pem"):
        try:
            from .mldsa import verify_mldsa65

            pqc_sig_b64 = entries["signature_pqc.sig"].decode("ascii").strip()
            pqc_sig = base64.b64decode(pqc_sig_b64, validate=False)
            pqc_valid = verify_mldsa65(
                entries["pqc_public_key.pem"], pqc_sig, canonical
            )
            report.append(f"ML-DSA-65 signature {'verified' if pqc_valid else 'FAILED'}.")
            if not pqc_valid:
                return _fail(
                    report,
                    "ML-DSA-65 signature does not verify.",
                    metadata,
                    pqc_valid,
                    receipt,
                )
        except ImportError as e:
            return _fail(
                report,
                f"ML-DSA-65 support not compiled in: {e}",
                metadata,
                None,
                receipt,
            )
    else:
        report.append("ML-DSA-65 entries absent (transitional v1 package).")

    # 9. RFC 3161 timestamp inspection.
    tsr_b64 = entries["timestamp.tsr"].decode("ascii", errors="replace").strip()
    tsa = inspect_tsa(tsr_b64, expected_hash_hex)
    if not tsa.tsa_present:
        return _fail(report, "timestamp.tsr missing or empty.", metadata, pqc_valid, receipt)
    report.append(
        f"RFC 3161 timestamp present ({tsa.raw_size_bytes} bytes, genTime={tsa.gen_time}). "
        f"Message imprint match: {tsa.message_imprint_matches}. "
        f"SignerInfo signature: {tsa.signature_verified}. "
        f"Signer: {tsa.signer_subject} (issued by {tsa.signer_issuer})."
    )
    if tsa.signature_verified is False:
        return _fail(
            report,
            "RFC 3161 SignerInfo signature did not verify against the embedded cert.",
            metadata,
            pqc_valid,
            receipt,
        )

    # 10. TSA chain-to-root (single-step pin check).
    # Mirrors lib/src/verifier.ts: if the caller didn't pass a custom
    # trust list, fall through to DEFAULT_TSA_TRUST_LIST (DigiCert
    # public roots). An empty list opts out of the check entirely.
    trust_list = (
        opts.tsa_trust_list if opts.tsa_trust_list else DEFAULT_TSA_TRUST_LIST
    )
    tsa_trusted: bool | None = None
    if trust_list:
        trust = verify_tsa_trust(tsa, trust_list)
        tsa_trusted = trust.trusted
        report.append(f"TSA chain-to-root: trusted={trust.trusted}. {trust.reason}")

    return VerifyResult(
        valid=True,
        report=report,
        failure_reason=None,
        pqc_valid=pqc_valid,
        tsa_trusted=tsa_trusted,
        metadata=metadata,
        overt_receipt=receipt,
    )


def _fail(
    report: list[str],
    reason: str,
    metadata: dict[str, Any] | None,
    pqc_valid: bool | None = None,
    overt_receipt: dict[str, Any] | None = None,
) -> VerifyResult:
    report.append(f"FAIL: {reason}")
    return VerifyResult(
        valid=False,
        report=report,
        failure_reason=reason,
        pqc_valid=pqc_valid,
        tsa_trusted=None,
        metadata=metadata,
        overt_receipt=overt_receipt,
    )


def _ct_eq(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b, strict=True):
        result |= x ^ y
    return result == 0
