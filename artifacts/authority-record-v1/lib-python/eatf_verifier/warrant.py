"""Optional warrant.json parse-and-cross-check (spec §4.2).

Mirrors lib/src/warrant.ts, on the overt.py pattern. A warrant is a
once-authored, versioned record stating that outputs a named policy
evaluates to a listed decision are licensed for a listed action class,
carried as JCS-canonical bytes and bound by digest from metadata.json.
Its acceptance block names the principal that accepted the warrant, with
a signature over the JCS bytes of the warrant minus the signature itself.

Binding verification and authorization appraisal are SEPARATE verifier
decisions. The binding family GATES — a warrant whose digest, record
shape, policy linkage, or acceptance signature is inconsistent makes the
verifier reject, exactly as an inconsistent OVERT-inspired receipt does:

    warrant-digest                GATES.
    warrant-parse                 GATES.
    warrant-bound                 APPRAISAL. Response-only packages stay
                                  accepted; the unbound state is reported.
    warrant-policy-link           GATES.
    warrant-applicability         APPRAISAL. An output whose warrant does
                                  not apply may inform but carries no
                                  warrant to compel.
    warrant-acceptance-signature  GATES.
    warrant-freshness             APPRAISAL, judged in verifier.py once
                                  the RFC 3161 genTime and the TSA trust
                                  verdict are known.

The accepting authority is a named principal with a verifiable key
binding — the same self-attestation trust model as public_key.pem.
Nothing here establishes it as a legally constituted authority, and the
soundness of the licensed inference is attested, never machine-checked.
void_if entries are shape-validated (the machine/attested partition stays
explicit) but their predicates are not evaluated in this release.

Unlike the sibling ports, the failure STRINGS here are pinned to the
TypeScript reference verbatim: verify-expected.txt carries a
``diagnostic=`` line, and the cross-implementation parity claim the
article makes is verdict AND diagnostic, vector by vector.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .canonical import jcs
from .hash import sha256, to_hex
from .rsa import load_public_key_pem, verify_rsa

REQUIRED_FIELDS = (
    "warrant_id",
    "warrant_version",
    "inference_form",
    "statement",
    "valid_from",
    "valid_until",
)

ACCEPTANCE_FIELDS = ("authority_id", "accepted_at", "signature", "public_key")


@dataclass
class WarrantValidation:
    referenced: bool = False
    present: bool = False
    record: dict[str, Any] | None = None
    error: str | None = None
    error_check: str | None = None
    digest_ok: bool | None = None
    bound: bool | None = None
    policy_linked: bool | None = None
    applicable: bool | None = None
    acceptance_verified: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


def _text(value: Any, *path: str) -> str | None:
    """Mirror textAt(): a non-blank string at `path`, else None."""
    current = value
    for segment in path:
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    if not isinstance(current, str) or current.strip() == "":
        return None
    return current


def _value_at(value: Any, path: tuple[str, ...]) -> Any:
    current = value
    for segment in path:
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _parse_rfc3339(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fail(out: WarrantValidation, check: str, message: str) -> WarrantValidation:
    out.error = message
    out.error_check = check
    return out


def parse_and_check_warrant(
    entries: dict[str, bytes],
    metadata: dict[str, Any],
    canonical_form: str,
) -> WarrantValidation:
    """Cross-check the optional warrant. Mirrors parseAndCheckWarrant()."""
    raw = entries.get("warrant.json")
    digest_field = _text(metadata, "warrant_digest")
    if digest_field is not None:
        digest_field = digest_field.strip().lower()
    referenced = (
        bool(raw)
        or digest_field is not None
        or isinstance(metadata.get("warrant_id"), str)
        or isinstance(metadata.get("warrant_version"), str)
    )
    if not referenced:
        return WarrantValidation()

    out = WarrantValidation(referenced=True, present=bool(raw))

    # --- warrant-digest ---------------------------------------------------
    # The digest reference and the packaged bytes must exist together and
    # agree.
    if not out.present:
        out.digest_ok = False
        return _fail(
            out,
            "warrant-digest",
            "warrant.json entry is missing but metadata references a warrant",
        )
    if digest_field is None:
        out.digest_ok = False
        return _fail(out, "warrant-digest", "metadata.warrant_digest is missing")
    if to_hex(sha256(raw)) != digest_field:
        out.digest_ok = False
        return _fail(
            out, "warrant-digest", "digest does not match metadata.warrant_digest"
        )
    out.digest_ok = True

    # --- warrant-parse ----------------------------------------------------
    # Valid JSON, JCS-canonical bytes, required shape.
    try:
        record = json.loads(raw.decode("utf-8"))
    except Exception:
        return _fail(out, "warrant-parse", "record is not valid JSON")
    if not isinstance(record, dict):
        return _fail(out, "warrant-parse", "record must be a JSON object")
    out.record = record
    if jcs(record) != raw:
        return _fail(out, "warrant-parse", "record bytes are not in JCS canonical form")
    shape_error = _validate_shape(record)
    if shape_error:
        return _fail(out, "warrant-parse", shape_error)
    out.valid_from = _parse_rfc3339(_text(record, "valid_from") or "")
    out.valid_until = _parse_rfc3339(_text(record, "valid_until") or "")
    if out.valid_from is None or out.valid_until is None:
        out.valid_from = None
        out.valid_until = None
        return _fail(
            out, "warrant-parse", "valid_from/valid_until must be RFC 3339 timestamps"
        )

    # --- warrant-bound (appraisal) ----------------------------------------
    # The digest reference lies inside the signed canonical bytes only
    # under the profile form. Response-only packages stay accepted; the
    # unbound state is reported, not rejected.
    out.bound = canonical_form == "profile"

    # --- warrant-policy-link ----------------------------------------------
    # The warrant is written against THIS package's policy.
    linkage_error = (
        _compare_to_metadata(record, ("policy_ref", "policy_id"), metadata, "policy_id", True)
        or _compare_to_metadata(record, ("policy_ref", "policy_version"), metadata, "policy_version", True)
        or _compare_to_metadata(record, ("warrant_id",), metadata, "warrant_id", False)
        or _compare_to_metadata(
            record, ("warrant_version",), metadata, "warrant_version", False
        )
    )
    if linkage_error:
        out.policy_linked = False
        return _fail(out, "warrant-policy-link", linkage_error)
    out.policy_linked = True

    # --- warrant-applicability (appraisal) --------------------------------
    action_type = _text(metadata, "action_type")
    decision = _text(metadata, "policy_decision")
    if action_type is None or decision is None:
        out.applicable = None
    else:
        action_types = _value_at(record, ("applies_to", "action_types"))
        decisions = _value_at(record, ("applies_to", "policy_decisions"))
        out.applicable = action_type in action_types and decision in decisions

    # --- warrant-acceptance-signature -------------------------------------
    # The named principal's signature over the JCS bytes of the warrant
    # with acceptance.signature removed. Produced by our own tooling, so
    # no DigestInfo fallback is needed here.
    acceptance = record.get("acceptance")
    if not isinstance(acceptance, dict):
        out.acceptance_verified = False
        return _fail(
            out, "warrant-acceptance-signature", "acceptance block is missing"
        )
    for field in ACCEPTANCE_FIELDS:
        if _text(acceptance, field) is None:
            out.acceptance_verified = False
            return _fail(
                out, "warrant-acceptance-signature", f"acceptance.{field} is required"
            )
    unsigned = dict(record)
    unsigned["acceptance"] = {k: v for k, v in acceptance.items() if k != "signature"}
    try:
        key = load_public_key_pem(acceptance["public_key"].encode("utf-8"))
        sig = base64.b64decode(acceptance["signature"].strip(), validate=False)
        out.acceptance_verified = verify_rsa(key, sig, jcs(unsigned))
    except Exception:
        out.acceptance_verified = False
        return _fail(
            out,
            "warrant-acceptance-signature",
            "acceptance.public_key or acceptance.signature could not be parsed",
        )
    if not out.acceptance_verified:
        return _fail(
            out,
            "warrant-acceptance-signature",
            "acceptance.signature does not verify against acceptance.public_key",
        )

    return out


def _validate_shape(record: dict[str, Any]) -> str | None:
    """Required-shape validation per schemas/warrant-v1.schema.json."""
    for field in REQUIRED_FIELDS:
        if _text(record, field) is None:
            return f"{field} is required"
    if (
        _text(record, "policy_ref", "policy_id") is None
        or _text(record, "policy_ref", "policy_version") is None
    ):
        return "policy_ref must carry policy_id and policy_version"
    for key in ("action_types", "policy_decisions"):
        values = _value_at(record, ("applies_to", key))
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(v, str) or v.strip() == "" for v in values)
        ):
            return f"applies_to.{key} must be a non-empty array of strings"
    void_if = record.get("void_if")
    if void_if is not None:
        if not isinstance(void_if, list):
            return "void_if must be an array"
        for entry in void_if:
            if not isinstance(entry, dict):
                return "void_if entries must be objects"
            kind = _text(entry, "kind")
            if kind == "machine":
                if _text(entry, "predicate") is None:
                    return "void_if machine entries require a predicate"
            elif kind == "attested":
                if _text(entry, "text") is None:
                    return "void_if attested entries require a text"
            else:
                return "void_if entries must be kind machine or attested"
    return None


def _compare_to_metadata(
    record: dict[str, Any],
    record_path: tuple[str, ...],
    metadata: dict[str, Any],
    metadata_key: str,
    metadata_required: bool,
) -> str | None:
    metadata_value = _text(metadata, metadata_key)
    if metadata_value is None:
        return (
            f"metadata.{metadata_key} is missing but the warrant references a policy"
            if metadata_required
            else None
        )
    if _text(record, *record_path) != metadata_value:
        return f"{'.'.join(record_path)} does not match metadata.{metadata_key}"
    return None


def evaluate_warrant_freshness(
    check: WarrantValidation, gen_time: str | None, tsa_trusted: bool | None
) -> bool | None:
    """Appraisal: RFC 3161 genTime inside the warrant's validity window.

    A `fresh` verdict additionally needs the TSA trust verdict — an
    untrusted clock can refute freshness (a genTime outside the window is
    self-refuting) but never establish it. Mirrors the warrant-freshness
    block of lib/src/verifier.ts.
    """
    if check.valid_from is None or check.valid_until is None or not gen_time:
        return None
    parsed = _parse_rfc3339(gen_time)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=check.valid_from.tzinfo)
    if parsed < check.valid_from or parsed > check.valid_until:
        return False
    return True if tsa_trusted is True else None
