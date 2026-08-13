"""SHA-256 wrapper. Trivial; here for parity with lib/src/hash.ts."""

from __future__ import annotations

import hashlib


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def to_hex(data: bytes) -> str:
    return data.hex()
