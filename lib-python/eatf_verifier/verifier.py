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


@dataclass
class VerifyOptions:
    """Caller-supplied verification configuration."""

    offline_only: bool = True
    trusted_signer_pems: list[bytes] = field(default_factory=list)
    """Optional exact SPKI PEM trust set for the package signer."""
    tsa_trust_list: list[bytes] = field(default_factory=list)
    """Optional PEM certificates for the advisory TSA issuer-name pin.

    An empty list skips the pin. This is not full RFC 5280 path
    validation; see ``verify_tsa_trust``.
    """


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
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ENTRY_BYTES = 16 * 1024 * 1024
MAX_EXPANDED_BYTES = 32 * 1024 * 1024
MAX_ENTRIES = 32


def verify(data: bytes, options: VerifyOptions | None = None) -> VerifyResult:
    """Verify an .aep package. Returns a VerifyResult."""
    opts = options or VerifyOptions()
    report: list[str] = []
    metadata: dict[str, Any] | None = None

    # 1. Unzip with explicit resource and name limits.
    if len(data) > MAX_ARCHIVE_BYTES:
        return _fail(report, "Package exceeds the 64 MiB archive safety limit.", metadata)
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            if len(infos) > MAX_ENTRIES:
                raise ValueError("too many ZIP entries")
            if len(set(names)) != len(names):
                raise ValueError("duplicate ZIP entry")
            if any(
                "/" in name or "\\" in name or "\0" in name
                for name in names
            ):
                raise ValueError("AEP entries must use flat, safe names")
            if any(info.file_size > MAX_ENTRY_BYTES for info in infos):
                raise ValueError("ZIP entry too large")
            if sum(info.file_size for info in infos) > MAX_EXPANDED_BYTES:
                raise ValueError("expanded ZIP too large")
            entries = {info.filename: zf.read(info) for info in infos}
    except Exception as exc:
        return _fail(
            report,
            f"Package failed ZIP parsing or safety limits: {exc}.",
            metadata,
        )
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

    # 4. Canonical-form check. Response-only is read-only compatibility for
    # early packages and does not authenticate metadata.
    response = entries["response.txt"]
    canonical = entries["canonical.bin"]
    try:
        profile_canonical = response + b"\n" + jcs(metadata)
    except Exception as exc:
        return _fail(
            report,
            f"metadata.json cannot be represented as RFC 8785 JCS: {exc}.",
            metadata,
        )
    if _ct_eq(profile_canonical, canonical):
        report.append("Canonical bytes match AEP profile canonical form.")
    elif _ct_eq(response, canonical):
        report.append(
            "Canonical bytes match legacy response-only form; metadata is not signature-bound."
        )
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
    if opts.trusted_signer_pems:
        packaged_key = _normalized_pem_body(pem)
        if not any(
            _normalized_pem_body(trusted) == packaged_key
            for trusted in opts.trusted_signer_pems
        ):
            return _fail(
                report,
                "Signer public key is not in the caller-supplied trust set.",
                metadata,
            )
        report.append("Signer public key matched the caller-supplied trust set.")
    else:
        report.append("Signer identity trust not evaluated (no trusted signer keys supplied).")
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

    receipt_signature_name = metadata.get("overt_receipt_signature")
    if receipt_signature_name is not None:
        if receipt_signature_name != "overt_receipt.sig":
            return _fail(
                report,
                "metadata.overt_receipt_signature must equal overt_receipt.sig.",
                metadata,
                None,
                receipt,
            )
        receipt_bytes = entries.get("overt_receipt.json")
        receipt_signature_bytes = entries.get("overt_receipt.sig")
        if receipt is None or not receipt_bytes or not receipt_signature_bytes:
            return _fail(
                report,
                "Signed metadata requires overt_receipt.json and overt_receipt.sig.",
                metadata,
                None,
                receipt,
            )
        try:
            receipt_signature = base64.b64decode(
                receipt_signature_bytes.decode("ascii").strip(),
                validate=False,
            )
            if not verify_rsa(key, receipt_signature, receipt_bytes):
                return _fail(
                    report,
                    "OVERT receipt signature does not verify against public_key.pem.",
                    metadata,
                    None,
                    receipt,
                )
        except Exception as exc:
            return _fail(
                report,
                f"OVERT receipt signature verify error: {exc}.",
                metadata,
                None,
                receipt,
            )
        report.append("OVERT receipt signature verified (required by signed metadata).")
    elif "overt_receipt.sig" in entries:
        return _fail(
            report,
            "Unmarked overt_receipt.sig is not accepted.",
            metadata,
            None,
            receipt,
        )
    elif receipt is not None:
        report.append(
            "Legacy OVERT receipt is cross-checked but not separately signature-bound."
        )

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
    if tsa.message_imprint_matches is not True:
        reason = (
            "RFC 3161 message imprint does not match hash.sha256."
            if tsa.message_imprint_matches is False
            else "RFC 3161 message imprint could not be validated as SHA-256."
        )
        return _fail(report, reason, metadata, pqc_valid, receipt)
    if tsa.signature_verified is not True:
        reason = (
            "RFC 3161 SignerInfo signature did not verify against the embedded certificate."
            if tsa.signature_verified is False
            else "RFC 3161 token does not contain a verifiable embedded signing certificate."
        )
        return _fail(
            report,
            reason,
            metadata,
            pqc_valid,
            receipt,
        )

    # 10. Optional issuer-name pin (not full RFC 5280 path validation).
    trust_list = opts.tsa_trust_list
    tsa_trusted: bool | None = None
    if trust_list:
        trust = verify_tsa_trust(tsa, trust_list)
        tsa_trusted = trust.trusted
        report.append(f"TSA issuer-name pin: matched={trust.trusted}. {trust.reason}")

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


def _normalized_pem_body(pem: bytes) -> bytes:
    return b"".join(
        line.strip()
        for line in pem.splitlines()
        if not line.startswith(b"-----")
    )
