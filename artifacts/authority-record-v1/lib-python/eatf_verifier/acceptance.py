"""Epistemic accepting authority (spec §4.3). Mirrors lib/src/acceptance.ts.

`metadata.accepting_authority` names the principal that accepted, once,
that outputs under this policy version license their action class. It is
the EPISTEMIC layer, deliberately distinct from the DEONTIC authorizing
principal of §4.5 (who granted the mandate to act). An optional detached
`acceptance.json` / `acceptance.sig` pair carries the accepting
authority's signed acceptance record, bound to the package by
`accepting_authority.acceptance_digest`.

Two of the four outcomes GATE, on the §4.5 rule and for the same reason —
§4.3 is surface added after the response-only compatibility form was
frozen, so it carries no compatibility debt to it:

    accepting-authority-binding      GATES. Stripped, re-pointed,
                                     cross-field-substituted, or carried
                                     under the response-only form: the
                                     acceptance is bound to nothing and
                                     the package is REJECTED.
    accepting-authority-key-binding  GATES. A packaged acceptance whose
                                     detached signature does not verify
                                     against its own embedded key is
                                     forged, and the package is REJECTED.
    accepting-authority-temporal     APPRAISAL. An expired acceptance is
                                     authentic and bound; what lapsed is
                                     its licence.
    accepting-authority-role         APPRAISAL. Undecidable from the
                                     package alone: without a
                                     caller-supplied trust list there is
                                     nothing to decide membership against.

A tri-state that is None — the property was not determinable on this
input — never gates.

The failure STRINGS MAY differ from the TypeScript reference; the failure
DECISION must match, which is what the conformance contract and
tests/test_acceptance.py compare.
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

CROSS_FIELDS = ("principal", "policy_id", "policy_version")


@dataclass
class AcceptanceValidation:
    referenced: bool = False
    present: bool = False
    record: dict[str, Any] | None = None
    key_binding_valid: bool | None = None
    bound_to_output: bool | None = None
    temporal_containment: bool | None = None
    role_verified: bool | None = None
    error: str | None = None
    error_check: str | None = None


def _text(obj: Any, key: str) -> str | None:
    if not isinstance(obj, dict):
        return None
    value = obj.get(key)
    return value if isinstance(value, str) and value != "" else None


def _parse_rfc3339(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_pem(pem: bytes | str) -> str:
    text = pem.decode("ascii", errors="replace") if isinstance(pem, bytes) else pem
    return "".join(text.split())


def parse_and_check_acceptance(
    entries: dict[str, bytes],
    metadata: dict[str, Any],
    canonical_form: str,
    gen_time: str | None = None,
    authority_trust_list: list[bytes] | None = None,
) -> AcceptanceValidation:
    """Cross-check the accepting authority. Mirrors parseAndCheckAcceptance()."""
    authority = metadata.get("accepting_authority")
    if not isinstance(authority, dict):
        return AcceptanceValidation()

    raw = entries.get("acceptance.json")
    sig_raw = entries.get("acceptance.sig")
    out = AcceptanceValidation(referenced=True, present=bool(raw))

    record: dict[str, Any] | None = None
    if out.present:
        try:
            parsed = json.loads(raw.decode("utf-8"))
            record = parsed if isinstance(parsed, dict) else None
        except Exception:
            record = None
        out.record = record

    # --- key binding: acceptance.sig over JCS(acceptance.json) -----------
    key_binding_error: str | None = None
    if out.present:
        if record is None:
            out.key_binding_valid = False
            key_binding_error = "acceptance.json is not valid JSON"
        elif not sig_raw:
            out.key_binding_valid = False
            key_binding_error = "acceptance.sig entry is missing"
        else:
            pem = _text(record, "public_key")
            sig_b64 = sig_raw.decode("ascii", errors="replace").strip()
            if pem is None or sig_b64 == "":
                out.key_binding_valid = False
                key_binding_error = "acceptance.public_key or acceptance.sig is empty"
            else:
                try:
                    key = load_public_key_pem(pem.encode("utf-8"))
                    out.key_binding_valid = verify_rsa(
                        key, base64.b64decode(sig_b64, validate=False), jcs(record)
                    )
                    if not out.key_binding_valid:
                        key_binding_error = (
                            "acceptance.sig does not verify against the acceptance's public_key"
                        )
                except Exception:
                    out.key_binding_valid = False
                    key_binding_error = (
                        "acceptance.public_key or acceptance.sig could not be parsed"
                    )

    # --- bound to THIS output --------------------------------------------
    digest_field = _text(authority, "acceptance_digest")
    binding_error: str | None = None
    if canonical_form != "profile":
        out.bound_to_output = False
        binding_error = (
            "the response-only canonical form leaves metadata.accepting_authority "
            "outside signature.sig"
        )
    elif out.present:
        if record is None:
            out.bound_to_output = False
            binding_error = "acceptance.json is not a JSON object"
        else:
            actual = "sha256:" + to_hex(sha256(jcs(record)))
            digest_ok = digest_field is not None and actual == digest_field.strip().lower()
            mismatched = None
            if digest_ok:
                for key_name in CROSS_FIELDS:
                    a = _text(record, key_name)
                    b = _text(authority, key_name)
                    if a is None or b is None or a != b:
                        mismatched = key_name
                        break
            out.bound_to_output = digest_ok and mismatched is None
            if not digest_ok:
                binding_error = (
                    "acceptance.json is packaged but "
                    "metadata.accepting_authority.acceptance_digest is missing"
                    if digest_field is None
                    else "digest does not match accepting_authority.acceptance_digest"
                )
            elif mismatched is not None:
                binding_error = (
                    f"acceptance {mismatched} does not match accepting_authority.{mismatched}"
                )
    else:
        # Profile form, inline claim only: a dangling digest reference is
        # unbound; a bare signed claim is bound.
        out.bound_to_output = digest_field is None
        if not out.bound_to_output:
            binding_error = (
                "acceptance.json entry is missing but metadata references an acceptance_digest"
            )

    # --- temporal containment (appraisal) --------------------------------
    validity = authority.get("validity")
    if isinstance(validity, dict) and gen_time:
        not_before = _text(validity, "not_before")
        not_after = _text(validity, "not_after")
        parsed_gen = _parse_rfc3339(gen_time)
        if not_before is not None and not_after is not None and parsed_gen is not None:
            start = _parse_rfc3339(not_before)
            end = _parse_rfc3339(not_after)
            if start is not None and end is not None:
                if parsed_gen.tzinfo is None:
                    parsed_gen = parsed_gen.replace(tzinfo=start.tzinfo)
                out.temporal_containment = start <= parsed_gen <= end

    # --- role (appraisal) -------------------------------------------------
    if authority_trust_list:
        pem = _text(record, "public_key") if record is not None else None
        if pem is None:
            out.role_verified = False
        else:
            normalized = _normalize_pem(pem)
            out.role_verified = any(
                _normalize_pem(t) == normalized for t in authority_trust_list
            )

    # --- the gate ---------------------------------------------------------
    # Every outcome above is computed first, so a rejection still carries the
    # full §4.3 picture. Only then do the two binding-family checks decide,
    # in registry order.
    if out.bound_to_output is False:
        out.error = binding_error or "the acceptance is not bound to this output"
        out.error_check = "accepting-authority-binding"
    elif out.key_binding_valid is False:
        out.error = key_binding_error or "the acceptance signature does not verify"
        out.error_check = "accepting-authority-key-binding"

    return out
