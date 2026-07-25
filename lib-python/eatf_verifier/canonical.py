"""RFC 8785 JSON Canonicalization Scheme (JCS) for the Python port."""

from __future__ import annotations

from typing import Any

import rfc8785

_MAX_SAFE_INTEGER = 2**53 - 1


def jcs(value: Any) -> bytes:
    """Return RFC 8785 canonical UTF-8 bytes for the shared I-JSON profile."""
    _assert_shared_ijson_domain(value, set())
    return rfc8785.dumps(value)


def _assert_shared_ijson_domain(value: Any, seen: set[int]) -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        if abs(value) > _MAX_SAFE_INTEGER:
            raise rfc8785.IntegerDomainError(value)
        return
    if isinstance(value, float):
        if value.is_integer() and abs(value) > _MAX_SAFE_INTEGER:
            raise rfc8785.FloatDomainError(value)
        return
    if not isinstance(value, (list, tuple, dict)):
        raise rfc8785.CanonicalizationError(f"unsupported type: {type(value)}")

    identity = id(value)
    if identity in seen:
        raise rfc8785.CanonicalizationError("circular references are not supported")
    seen.add(identity)
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise rfc8785.CanonicalizationError("object keys must be strings")
            _assert_shared_ijson_domain(item, seen)
    else:
        for item in value:
            _assert_shared_ijson_domain(item, seen)
    seen.remove(identity)
