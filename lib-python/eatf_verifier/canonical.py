"""RFC 8785 JSON Canonicalization Scheme (JCS) for the Python port.

Mirrors lib/src/canonical.ts in the TypeScript reference. The
output bytes MUST be identical between implementations for any
given input.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any


_NUMBER_RE_TRAILING_ZEROS = re.compile(r"(\.\d*?)0+$")


def jcs(value: Any) -> bytes:
    """Return the RFC 8785 canonical bytes for the JSON value.

    Object members are sorted lexicographically by Unicode codepoint
    of the key. Numbers use ECMA-404 serialisation with no trailing
    zeros and no superfluous signs. Strings use JSON escape rules
    (UTF-8 output, no BOM).
    """
    return _serialize(value).encode("utf-8")


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return _serialize_number(value)
    if isinstance(value, str):
        return _serialize_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_serialize(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys(), key=lambda k: [ord(c) for c in k])
        parts = []
        for k in keys:
            parts.append(_serialize_string(k) + ":" + _serialize(value[k]))
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"JCS does not support {type(value).__name__}")


def _serialize_number(n: int | float) -> str:
    if isinstance(n, bool):  # bool is a subclass of int in Python
        return "true" if n else "false"
    if isinstance(n, int):
        return str(n)
    if math.isnan(n) or math.isinf(n):
        raise ValueError("JCS does not permit NaN or Infinity")
    if n == 0:
        return "0"
    # Use repr-like formatting then strip trailing zeros / dot.
    s = format(n, "g")
    if "e" in s or "E" in s:
        # ECMA-404 doesn't forbid scientific notation but JCS prefers
        # plain decimal where the number fits without loss.
        s = format(n, "f")
    if "." in s:
        s = _NUMBER_RE_TRAILING_ZEROS.sub(r"\1", s)
        s = s.rstrip(".")
    return s


def _serialize_string(s: str) -> str:
    # json.dumps gives RFC 8259 escapes by default with ensure_ascii=False;
    # JCS requires the same escaping rules.
    return json.dumps(s, ensure_ascii=False, separators=(",", ":"))
