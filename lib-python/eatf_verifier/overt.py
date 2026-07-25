"""OVERT 1.0 receipt validation. Mirrors lib/src/overt.ts."""

from __future__ import annotations

from typing import Any

OVERT_VERSION = "1.0.0"
AEP_PROFILE = "urn:eatf:spec:aep:1.0"


def parse_and_validate_overt_receipt(
    entries: dict[str, bytes],
    metadata: dict[str, Any],
    expected_hash_hex: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (receipt, error). Either receipt or error may be None.

    Returns (None, None) when no overt_receipt.json is present
    (the receipt is optional in v0.1 packages).
    Returns (receipt, "...") when the receipt is present but
    invalid; the error string MAY differ from the TypeScript
    reference but the failure decision MUST match.
    """
    import json

    raw = entries.get("overt_receipt.json")
    if not raw:
        return None, None

    try:
        receipt = json.loads(raw.decode("utf-8"))
    except Exception:
        return None, "receipt is not valid JSON"

    if not isinstance(receipt, dict):
        return None, "receipt must be a JSON object"

    if receipt.get("overt") != OVERT_VERSION:
        return receipt, f"overt must be {OVERT_VERSION}"
    if receipt.get("profile") != AEP_PROFILE:
        return receipt, f"profile must be {AEP_PROFILE}"
    if not receipt.get("scope"):
        return receipt, "scope is required"
    if receipt.get("content_hash") != f"sha256:{expected_hash_hex.lower()}":
        return receipt, "content_hash does not match hash.sha256"

    # Cross-checks against metadata.
    for meta_keys, receipt_path, label in (
        (("created_at", "createdAt"), ("event", "timestamp"), "event.timestamp"),
        (("agent_id", "agentId"), ("subject", "agent_id"), "subject.agent_id"),
        (
            ("tenant_id_hash", "tenantIdHash"),
            ("subject", "tenant_hash"),
            "subject.tenant_hash",
        ),
        (
            ("action_type", "actionType"),
            ("event", "action_type"),
            "event.action_type",
        ),
        (
            ("policy_version", "policyVersion"),
            ("policy", "version"),
            "policy.version",
        ),
        (
            ("policy_decision", "policyDecision"),
            ("policy", "decision"),
            "policy.decision",
        ),
    ):
        err = _compare_text(metadata, meta_keys, receipt, receipt_path, label)
        if err:
            return receipt, err

    metadata_coverage = metadata.get("policy_coverage")
    receipt_policy = receipt.get("policy")
    receipt_coverage = (
        receipt_policy.get("coverage")
        if isinstance(receipt_policy, dict)
        else None
    )
    if metadata_coverage is not None:
        if (
            not isinstance(metadata_coverage, (int, float))
            or isinstance(metadata_coverage, bool)
            or not isinstance(receipt_coverage, (int, float))
            or isinstance(receipt_coverage, bool)
            or abs(float(metadata_coverage) - float(receipt_coverage)) > 1e-9
        ):
            return receipt, "policy.coverage does not match metadata.policy_coverage"

    witness = receipt.get("witness")
    if not isinstance(witness, dict):
        return receipt, "witness must be a JSON object"
    signature_refs_error = _validate_refs(
        entries,
        witness.get("signature_refs"),
        "signature_refs",
        require_non_empty=True,
    )
    if signature_refs_error:
        return receipt, signature_refs_error
    timestamp_refs_error = _validate_refs(
        entries,
        witness.get("timestamp_refs"),
        "timestamp_refs",
        require_non_empty=False,
    )
    if timestamp_refs_error:
        return receipt, timestamp_refs_error

    return receipt, None


def _validate_refs(
    entries: dict[str, bytes],
    value: Any,
    key: str,
    *,
    require_non_empty: bool,
) -> str | None:
    if not isinstance(value, list):
        return f"witness.{key} must be an array"
    if require_non_empty and not value:
        return f"witness.{key} must name at least one file"
    for ref in value:
        if not isinstance(ref, str) or not ref.strip():
            return f"witness.{key} contains a non-text ref"
        if "/" in ref or "\\" in ref:
            return f"witness.{key} must use flat package filenames"
        if ref not in entries:
            return f"witness.{key} references missing file {ref}"
        if not entries[ref]:
            return f"witness.{key} references empty file {ref}"
    return None


def _compare_text(
    metadata: dict[str, Any],
    meta_keys: tuple[str, ...],
    receipt: dict[str, Any],
    receipt_path: tuple[str, ...],
    label: str,
) -> str | None:
    meta_value = _first(metadata, meta_keys)
    receipt_value = _path(receipt, receipt_path)
    if meta_value is None or receipt_value is None:
        return None
    if not isinstance(meta_value, str) or not isinstance(receipt_value, str):
        return None
    if meta_value != receipt_value:
        return f"{label} ({receipt_value}) does not match metadata.{meta_keys[0]} ({meta_value})"
    return None


def _first(d: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return None


def _path(d: dict[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = d
    for k in path:
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    return node
