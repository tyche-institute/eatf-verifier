"""Detached deontic mandate (spec §4.5). Mirrors lib/src/mandate.ts.

`metadata.authorizing_principal` names the authority that granted the
subject agent a mandate to act. A block that names a principal and
nothing else claims no signed mandate: it is the reference form, and
nothing about it is verified. A block carrying `mandate_digest`, or a
package carrying a `mandate.json` entry, claims a signed mandate, and
the binding family below GATES verification — digest, record, binding
to the protected bytes, and the granting authority's detached
signature. Scope and temporal containment are appraisal outcomes:
reported, never rejecting.

The failure strings MAY differ from the TypeScript reference; the
failure DECISION must match, which is what the conformance contract and
tests/test_mandate.py compare.
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
    "mandate_id",
    "mandate_version",
    "principal",
    "subject",
    "granted_at",
    "statement",
    "valid_from",
    "valid_until",
    "public_key",
)


@dataclass
class MandateValidation:
    referenced: bool = False
    claimed: bool = False
    present: bool = False
    record: dict[str, Any] | None = None
    error: str | None = None
    error_check: str | None = None
    digest_ok: bool | None = None
    bound: bool | None = None
    signature_verified: bool | None = None
    in_scope: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    temporal_containment: bool | None = None


def _text(obj: Any, key: str) -> str | None:
    if not isinstance(obj, dict):
        return None
    value = obj.get(key)
    return value if isinstance(value, str) and value != "" else None


def _fail(out: MandateValidation, check: str, message: str) -> MandateValidation:
    out.error = message
    out.error_check = check
    return out


def _parse_rfc3339(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_and_check_mandate(
    entries: dict[str, bytes],
    metadata: dict[str, Any],
    canonical_form: str,
) -> MandateValidation:
    """Cross-check the detached mandate. Mirrors parseAndCheckMandate()."""
    block = metadata.get("authorizing_principal")
    block = block if isinstance(block, dict) else None
    raw = entries.get("mandate.json")
    sig_raw = entries.get("mandate.sig")
    present = bool(raw)
    if block is None and not present:
        return MandateValidation()

    digest_field = _text(block, "mandate_digest") if block is not None else None
    out = MandateValidation(
        referenced=True,
        claimed=present or digest_field is not None,
        present=present,
    )
    if not out.claimed:
        return out

    # --- mandate-digest --------------------------------------------------
    if not present:
        out.digest_ok = False
        return _fail(
            out,
            "mandate-digest",
            "mandate.json entry is missing but metadata references a mandate",
        )
    if digest_field is None:
        out.digest_ok = False
        return _fail(
            out,
            "mandate-digest",
            "mandate.json is packaged but metadata.authorizing_principal.mandate_digest is missing",
        )
    actual = "sha256:" + to_hex(sha256(raw))
    if actual != digest_field.strip().lower():
        out.digest_ok = False
        return _fail(
            out,
            "mandate-digest",
            "digest does not match authorizing_principal.mandate_digest",
        )
    out.digest_ok = True

    # --- mandate-parse ---------------------------------------------------
    try:
        record = json.loads(raw.decode("utf-8"))
    except Exception:
        return _fail(out, "mandate-parse", "record is not valid JSON")
    if not isinstance(record, dict):
        return _fail(out, "mandate-parse", "record must be a JSON object")
    out.record = record
    if jcs(record) != raw:
        return _fail(out, "mandate-parse", "record bytes are not in JCS canonical form")
    for field in REQUIRED_FIELDS:
        if _text(record, field) is None:
            return _fail(out, "mandate-parse", f"{field} is required")
    scope = record.get("scope")
    for key in ("action_types", "policy_ids"):
        values = scope.get(key) if isinstance(scope, dict) else None
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(v, str) or v.strip() == "" for v in values)
        ):
            return _fail(
                out,
                "mandate-parse",
                f"scope.{key} must be a non-empty array of strings",
            )
    out.valid_from = _parse_rfc3339(_text(record, "valid_from") or "")
    out.valid_until = _parse_rfc3339(_text(record, "valid_until") or "")
    if out.valid_from is None or out.valid_until is None:
        return _fail(
            out, "mandate-parse", "valid_from/valid_until must be RFC 3339 timestamps"
        )

    # --- mandate-bound ---------------------------------------------------
    if canonical_form != "profile":
        out.bound = False
        return _fail(
            out,
            "mandate-bound",
            "the response-only canonical form leaves authorizing_principal.mandate_digest outside signature.sig",
        )
    for record_key, other, other_key in (
        ("mandate_id", block, "mandate_ref"),
        ("principal", block, "principal"),
        ("subject", metadata, "agent_id"),
    ):
        expected = _text(other, other_key)
        if expected is None:
            out.bound = False
            return _fail(
                out,
                "mandate-bound",
                f"{other_key} is missing but a signed mandate is claimed",
            )
        if _text(record, record_key) != expected:
            out.bound = False
            return _fail(
                out, "mandate-bound", f"mandate {record_key} does not match {other_key}"
            )
    out.bound = True

    # --- mandate-signature -----------------------------------------------
    if not sig_raw:
        out.signature_verified = False
        return _fail(out, "mandate-signature", "mandate.sig entry is missing")
    pem = _text(record, "public_key")
    sig_b64 = sig_raw.decode("ascii", errors="replace").strip()
    if pem is None or sig_b64 == "":
        out.signature_verified = False
        return _fail(out, "mandate-signature", "mandate.public_key or mandate.sig is empty")
    try:
        key = load_public_key_pem(pem.encode("utf-8"))
        out.signature_verified = verify_rsa(
            key, base64.b64decode(sig_b64, validate=False), jcs(record)
        )
    except Exception:
        out.signature_verified = False
        return _fail(
            out, "mandate-signature", "mandate.public_key or mandate.sig could not be parsed"
        )
    if not out.signature_verified:
        return _fail(
            out,
            "mandate-signature",
            "mandate.sig does not verify against the mandate's public_key",
        )

    # --- mandate-scope (appraisal) ---------------------------------------
    action_type = _text(metadata, "action_type")
    policy_id = _text(metadata, "policy_id")
    if action_type is None or policy_id is None:
        out.in_scope = None
    else:
        out.in_scope = (
            action_type in scope["action_types"] and policy_id in scope["policy_ids"]
        )

    return out


def evaluate_mandate_temporal(
    check: MandateValidation, gen_time: str | None
) -> bool | None:
    """Appraisal: RFC 3161 genTime inside the mandate's validity window.

    `gen_time` is the ISO 8601 string TsaCheck carries (tsa.py), so it is
    parsed here with the same RFC 3339 reader the record fields use.
    """
    if check.valid_from is None or check.valid_until is None or not gen_time:
        return None
    parsed = _parse_rfc3339(gen_time)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=check.valid_from.tzinfo)
    check.temporal_containment = check.valid_from <= parsed <= check.valid_until
    return check.temporal_containment
