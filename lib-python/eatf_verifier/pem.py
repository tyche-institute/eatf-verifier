"""PEM reading shared by every key entry and pin.

parse_pem is an exact port of parsePem in lib/src/rsa.ts, so both verifiers
accept and reject the same PEM text: one block and nothing else but
surrounding whitespace. public_key.pem, pqc_public_key.pem and every key pin
are read with it.
"""

from __future__ import annotations

import base64
import re

# Pins and packaged keys, with or without a pin, are parsed exactly as
# lib/src/rsa.ts parsePem and decodeBase64 parse them, so the two verifiers
# accept and reject the same PEM text. _JS_WHITESPACE is the set that
# JavaScript's String.prototype.trim() and regex \s use.
_JS_WHITESPACE = (
    "\t\n\x0b\x0c\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)
# One body group that starts and ends with whitespace, as in parsePem: the same
# language as [ws]+(...)[ws]+, without cubic backtracking on long whitespace runs.
_PEM_BLOCK = re.compile(
    "-----BEGIN ([A-Z0-9 -]+)-----"
    "([" + _JS_WHITESPACE + "][A-Za-z0-9+/=" + _JS_WHITESPACE + "]+[" + _JS_WHITESPACE + "])"
    "-----END \\1-----"
)
_BASE64_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
)


def parse_pem(pem: bytes) -> tuple[str, bytes]:
    """Return (label, DER) of the one PEM block in ``pem``; raise ValueError otherwise."""
    text = pem.decode("utf-8", errors="replace").strip(_JS_WHITESPACE)
    match = _PEM_BLOCK.fullmatch(text)
    if match is None:
        raise ValueError("Malformed PEM block")
    return match.group(1), _forgiving_base64(match.group(2))


def _forgiving_base64(body: str) -> bytes:
    """WHATWG forgiving-base64 decode, as atob() applies it after whitespace removal."""
    data = "".join(ch for ch in body if ch not in _JS_WHITESPACE)
    if len(data) % 4 == 0:
        if data.endswith("=="):
            data = data[:-2]
        elif data.endswith("="):
            data = data[:-1]
    if len(data) % 4 == 1 or not _BASE64_ALPHABET.issuperset(data):
        raise ValueError("PEM body is not valid base64")
    return base64.b64decode(data + "=" * (-len(data) % 4))
