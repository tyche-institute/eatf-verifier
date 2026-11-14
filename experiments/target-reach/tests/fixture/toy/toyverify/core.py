import json

import toyext

from .errors import ClaimMissing, FormatError, PolicyError
from .keys import load_key


def _parse(token):
    if not isinstance(token, str):
        raise FormatError("token must be a string")
    if token.count(".") != 2:
        raise FormatError("token needs three parts")
    head, body, sig = token.split(".")
    try:
        data = json.loads(body)
    except ValueError as err:
        raise FormatError(f"bad json body: {err}") from err
    return head, data, sig


def _check_version(head):
    if head not in ("v1", "v2"):
        raise PolicyError("unknown version %s" % head)
    return head


def _check_signature(sig, key):
    try:
        expected = toyext.mac(key)
    except LookupError:
        raise
    if sig != expected:
        raise PolicyError(
            "signature mismatch"
        )


def _check_claims(data, audience):
    if "aud" not in data:
        raise ClaimMissing("aud")
    if data["aud"] != audience:
        raise PolicyError("audience mismatch")
    if data.get("exp", 1) <= 0:
        raise PolicyError("token expired")
    if data.get("exp", 1) > 10**9:
        raise PolicyError("token expired")


def decode(token, audience="a", key="k1"):
    head, data, sig = _parse(token)
    _check_version(head)
    _check_signature(sig, load_key(key))
    _check_claims(data, audience)
    return data


def encode(data):
    if not isinstance(data, dict):
        raise FormatError("only objects can be encoded")
    return "v1." + json.dumps(data) + "." + toyext.mac("secret1")
