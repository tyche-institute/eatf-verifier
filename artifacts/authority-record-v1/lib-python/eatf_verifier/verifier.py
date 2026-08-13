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

from .acceptance import parse_and_check_acceptance
from .canonical import jcs
from .hash import sha256, to_hex
from .mandate import evaluate_mandate_temporal, parse_and_check_mandate
from .overt import parse_and_validate_overt_receipt
from .rsa import load_public_key_pem, verify_rsa, verify_rsa_digest_info
from .tsa import inspect_tsa, verify_tsa_trust
from .tsa_trust_list import DEFAULT_TSA_TRUST_LIST
from .warrant import evaluate_warrant_freshness, parse_and_check_warrant


@dataclass
class VerifyOptions:
    """Caller-supplied verification configuration."""

    offline_only: bool = True
    trusted_signer_pems: list[bytes] = field(default_factory=list)
    """PEM-encoded RSA public keys of the issuers this relying party
    accepts (spec §8.1). When non-empty, `public_key.pem` MUST be a
    member or the package is REJECTED; membership ignores PEM
    whitespace. When empty (the default) the check is not performed and
    the issuer is attested only — the self-attestation trust model, under
    which a package re-authored end to end with a different key is
    indistinguishable from one of the expected issuer."""
    authority_trust_list: list[bytes] = field(default_factory=list)
    """PEM-encoded public keys of the accepting authorities this relying
    party recognises (spec §4.3 role). Advisory in both reference
    implementations: when empty, role assertion stays attested-only; when
    supplied, membership is reported and never rejects. Role is the one
    §4.3 outcome undecidable from the package alone."""
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
    canonical_form: str | None = None
    warrant: dict[str, Any] | None = None
    """Warrant cross-check outcome (spec §4.2), when the package
    references a warrant and verification reached the warrant step. Keys
    mirror WarrantResult in the TypeScript reference: present, bound,
    policy_linked, applicable, acceptance_verified, fresh. Carried onto a
    rejecting result too, when the §4.2 gate is what rejected."""
    mandate: dict[str, Any] | None = None
    """Detached-mandate outcome (spec §4.5), when the package carries an
    authorizing_principal block or a mandate.json entry and verification
    reached the mandate step. Keys mirror MandateResult in the TypeScript
    reference: claimed, present, bound, signature_verified, in_scope,
    temporal_containment, principal."""
    accepting_authority: dict[str, Any] | None = None
    """Accepting-authority outcome (spec §4.3), when the package carries a
    metadata.accepting_authority block and verification reached the
    accepting-authority step. Keys mirror AcceptingAuthorityResult in the
    TypeScript reference: key_binding_valid, bound_to_output,
    temporal_containment, role_verified. Carried onto a rejecting result
    too — a rejection must not drop the evidence the run had in hand."""


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
        canonical_form = "profile"
        report.append("Canonical bytes match AEP profile canonical form.")
    elif _ct_eq(response, canonical):
        canonical_form = "response-only"
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
        return _fail(report, "Hash mismatch.", metadata, None, None, canonical_form)
    report.append("SHA-256 hash matches.")

    # 6. RSA signature.
    pem = entries["public_key.pem"]
    sig_b64 = entries["signature.sig"].decode("ascii").strip()
    try:
        sig = base64.b64decode(sig_b64, validate=False)
    except Exception:
        return _fail(
            report, "signature.sig is not valid base64.", metadata, None, None, canonical_form
        )
    try:
        key = load_public_key_pem(pem)
        rsa_ok = verify_rsa(key, sig, canonical)
        if not rsa_ok:
            # Java-reference compatibility: BouncyCastle DigestInfo
            # encoding without NULL parameters in the SHA-256
            # AlgorithmIdentifier. Strip padding and compare digests.
            rsa_ok = verify_rsa_digest_info(key, sig, actual_hash)
    except Exception as e:
        return _fail(report, f"RSA verify error: {e}.", metadata, None, None, canonical_form)
    if not rsa_ok:
        return _fail(
            report,
            "RSA signature does not verify against public_key.pem.",
            metadata,
            None,
            None,
            canonical_form,
        )
    report.append("RSA-4096 signature verified.")

    # 6b. Issuer key pinning (spec §8.1). Gates when the caller supplies a
    # list; not performed otherwise.
    if opts.trusted_signer_pems:
        packaged = _normalize_pem(pem)
        if not any(_normalize_pem(t) == packaged for t in opts.trusted_signer_pems):
            return _fail(
                report,
                "public_key.pem is not a member of the caller-supplied trustedSignerPems list.",
                metadata,
                None,
                None,
                canonical_form,
            )
        report.append(
            "Signing key pinned: public_key.pem is a member of the caller-supplied trust list."
        )

    # 7. OVERT-inspired receipt.
    receipt, err = parse_and_validate_overt_receipt(entries, metadata, expected_hash_hex)
    if err:
        return _fail(
            report,
            f"overt_receipt.json invalid: {err}.",
            metadata,
            None,
            receipt,
            canonical_form,
        )
    if receipt is not None:
        report.append(f"OVERT-inspired receipt verified ({receipt.get('scope')!s}).")
    else:
        report.append("OVERT-inspired receipt absent (optional profile entry).")

    # 7a. Optional warrant.json cross-check (spec §4.2). Binding-family
    # inconsistencies reject like an inconsistent OVERT-inspired receipt;
    # applicability is an appraisal outcome that is reported and never
    # rejects. Freshness is judged later, once the RFC 3161 genTime and
    # the TSA trust verdict are known. Placed between the OVERT-inspired receipt
    # and the mandate, exactly as in lib/src/verifier.ts.
    warrant_check = parse_and_check_warrant(entries, metadata, canonical_form)
    warrant: dict[str, Any] | None = None
    if not warrant_check.referenced:
        report.append("Warrant absent (optional profile entry).")
    else:
        warrant = _warrant_result(warrant_check)

        def _warrant_fail() -> VerifyResult:
            return _fail(
                report,
                f"warrant.json invalid: {warrant_check.error}.",
                metadata,
                None,
                receipt,
                canonical_form,
                warrant=warrant,
            )

        # Registry order: warrant-digest, warrant-parse, warrant-bound,
        # warrant-policy-link, warrant-applicability,
        # warrant-acceptance-signature. The three gating members return;
        # the two appraisal members report and fall through.
        if warrant_check.error_check in ("warrant-digest", "warrant-parse"):
            return _warrant_fail()
        if not warrant_check.bound:
            report.append(
                "Warrant present but unbound: the response-only canonical form "
                "leaves metadata.warrant_digest outside signature.sig."
            )
        if warrant_check.error_check == "warrant-policy-link":
            return _warrant_fail()
        if warrant_check.applicable is None:
            report.append(
                "Warrant applicability not determinate: metadata.action_type or "
                "metadata.policy_decision absent."
            )
        elif not warrant_check.applicable:
            report.append(
                "Warrant does not apply to this action: the output may inform "
                "but carries no warrant to compel."
            )
        if warrant_check.error_check == "warrant-acceptance-signature":
            return _warrant_fail()
        record = warrant_check.record or {}
        acceptance = record.get("acceptance")
        authority = (
            acceptance.get("authority_id") if isinstance(acceptance, dict) else None
        )
        report.append(
            f"Warrant verified ({record.get('warrant_id')}, accepted by {authority})."
        )

    # 7b. Optional detached deontic mandate (spec §4.5). The binding
    # family gates; scope and temporal containment are reported.
    mandate_check = parse_and_check_mandate(entries, metadata, canonical_form)
    mandate: dict[str, Any] | None = None
    if mandate_check.referenced:
        mandate = _mandate_result(mandate_check)
        if mandate_check.error:
            return _fail(
                report,
                f"mandate.json invalid: {mandate_check.error}.",
                metadata,
                None,
                receipt,
                canonical_form,
                mandate,
                warrant=warrant,
            )
        if not mandate_check.claimed:
            report.append(
                "Authorizing principal named without a signed mandate: the deontic "
                "layer is a reference only and nothing in it is verified."
            )
        else:
            if mandate_check.in_scope is False:
                report.append(
                    "Action lies outside the granted mandate: the output may inform "
                    "but carries no mandate to compel."
                )
            report.append(
                f"Mandate verified ({mandate_check.record.get('mandate_id')}, granted by "
                f"{mandate_check.record.get('principal')} to "
                f"{mandate_check.record.get('subject')})."
            )
    else:
        report.append("Authorizing principal absent (optional profile entry).")

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
                    canonical_form,
                    mandate,
                    warrant=warrant,
                )
        except ImportError as e:
            return _fail(
                report,
                f"ML-DSA-65 support not compiled in: {e}",
                metadata,
                None,
                receipt,
                canonical_form,
                mandate,
                warrant=warrant,
            )
    else:
        report.append("ML-DSA-65 entries absent (transitional v1 package).")

    # 9. RFC 3161 timestamp inspection.
    tsr_b64 = entries["timestamp.tsr"].decode("ascii", errors="replace").strip()
    tsa = inspect_tsa(tsr_b64, expected_hash_hex)
    if not tsa.tsa_present:
        return _fail(
            report,
            "timestamp.tsr missing or empty.",
            metadata,
            pqc_valid,
            receipt,
            canonical_form,
            mandate,
            warrant=warrant,
        )
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
            canonical_form,
            mandate,
            warrant=warrant,
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

    # 11. Mandate temporal containment (spec §4.5): appraisal against the
    # RFC 3161 genTime, reported and never rejecting.
    if mandate is not None and mandate_check.claimed:
        inside = evaluate_mandate_temporal(mandate_check, tsa.gen_time)
        mandate["temporal_containment"] = inside
        if inside is False:
            report.append(
                f"Mandate not in force at signing time: genTime {tsa.gen_time} "
                "lies outside valid_from..valid_until."
            )

    # 11b. Warrant freshness (spec §4.2): judged against the RFC 3161
    # genTime and the validity window. A fresh verdict additionally needs
    # the TSA trust verdict — an untrusted clock can refute freshness (a
    # genTime outside the window is self-refuting) but never establish it.
    if warrant is not None:
        fresh = evaluate_warrant_freshness(warrant_check, tsa.gen_time, tsa_trusted)
        warrant["fresh"] = fresh
        if fresh is False:
            report.append(
                f"Warrant not in force at signing time: genTime {tsa.gen_time} "
                "lies outside valid_from..valid_until."
            )
        elif fresh is True:
            report.append(
                "Warrant in force at signing time: genTime inside "
                "valid_from..valid_until under a trusted TSA."
            )

    # 12. Epistemic accepting authority (spec §4.3). The two binding-family
    # checks GATE, on the §4.5 rule; temporal containment and role are
    # appraisal. Placed last, after genTime is known, exactly as in
    # lib/src/verifier.ts.
    acceptance = parse_and_check_acceptance(
        entries,
        metadata,
        canonical_form,
        tsa.gen_time,
        opts.authority_trust_list,
    )
    accepting_authority: dict[str, Any] | None = None
    if acceptance.referenced:
        accepting_authority = {
            "key_binding_valid": acceptance.key_binding_valid,
            "bound_to_output": acceptance.bound_to_output,
            "temporal_containment": acceptance.temporal_containment,
            "role_verified": acceptance.role_verified,
        }
        report.append(
            f"Accepting authority checked (keyBinding={acceptance.key_binding_valid}, "
            f"bound={acceptance.bound_to_output}, "
            f"temporal={acceptance.temporal_containment}, "
            f"role={acceptance.role_verified}) — binding and key binding gate; "
            f"temporal containment and role are appraisal."
        )
        if acceptance.error_check is not None:
            return _fail(
                report,
                f"acceptance invalid: {acceptance.error}.",
                metadata,
                pqc_valid,
                receipt,
                canonical_form,
                mandate,
                accepting_authority,
                warrant=warrant,
            )
    else:
        report.append("Accepting authority absent (optional profile entry).")

    return VerifyResult(
        valid=True,
        report=report,
        failure_reason=None,
        pqc_valid=pqc_valid,
        tsa_trusted=tsa_trusted,
        metadata=metadata,
        overt_receipt=receipt,
        canonical_form=canonical_form,
        warrant=warrant,
        mandate=mandate,
        accepting_authority=accepting_authority,
    )


def _fail(
    report: list[str],
    reason: str,
    metadata: dict[str, Any] | None,
    pqc_valid: bool | None = None,
    overt_receipt: dict[str, Any] | None = None,
    canonical_form: str | None = None,
    mandate: dict[str, Any] | None = None,
    accepting_authority: dict[str, Any] | None = None,
    warrant: dict[str, Any] | None = None,
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
        canonical_form=canonical_form,
        warrant=warrant,
        mandate=mandate,
        accepting_authority=accepting_authority,
    )


def _warrant_result(check: Any) -> dict[str, Any]:
    """Project the cross-check onto the VerifyResult.warrant mapping."""
    return {
        "present": check.present,
        "bound": check.bound,
        "policy_linked": check.policy_linked,
        "applicable": check.applicable,
        "acceptance_verified": check.acceptance_verified,
        "fresh": None,
    }


def _mandate_result(check: Any) -> dict[str, Any]:
    """Project the cross-check onto the VerifyResult.mandate mapping."""
    record = check.record if isinstance(check.record, dict) else None
    return {
        "claimed": check.claimed,
        "present": check.present,
        "bound": check.bound,
        "signature_verified": check.signature_verified,
        "in_scope": check.in_scope,
        "temporal_containment": None,
        "principal": record.get("principal") if record else None,
    }


def _normalize_pem(pem: bytes | str) -> str:
    """Collapse PEM whitespace so membership survives newline differences."""
    text = pem.decode("ascii", errors="replace") if isinstance(pem, bytes) else pem
    return "".join(text.split())


def _ct_eq(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b, strict=True):
        result |= x ^ y
    return result == 0
