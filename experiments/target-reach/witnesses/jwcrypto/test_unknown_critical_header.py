# deleted check: jws.JWS._merge_check_headers#1
"""A signed object with a valid signature whose protected header lists a
critical header parameter that the library does not know."""
import hashlib
import hmac

import pytest

from jwcrypto import jwk, jws
from jwcrypto.common import base64url_encode, json_encode

SECRET = b"k" * 32
KEY = jwk.JWK(kty="oct", k=base64url_encode(SECRET))


def compact(header: dict) -> str:
    """A compact serialization signed by hand with HMAC SHA-256."""
    signing_input = base64url_encode(json_encode(header)) + "." + base64url_encode(b"payload")
    signature = hmac.new(SECRET, signing_input.encode("ascii"), hashlib.sha256).digest()
    return signing_input + "." + base64url_encode(signature)


def test_unknown_critical_header_with_valid_signature():
    # control: the same construction without the critical header verifies
    accepted = jws.JWS()
    accepted.deserialize(compact({"alg": "HS256"}), KEY)
    assert accepted.payload == b"payload"

    header = {"alg": "HS256", "crit": ["http://example.com/UNDEFINED"],
              "http://example.com/UNDEFINED": True}
    received = jws.JWS()
    with pytest.raises(jws.InvalidJWSSignature):
        received.deserialize(compact(header), KEY)
