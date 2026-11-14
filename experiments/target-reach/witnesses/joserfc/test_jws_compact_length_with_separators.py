# deleted check: _rfc7515.registry.JWSRegistry.validate_compact_value_size#1
"""A compact JWS whose 3 segments each fit the default limits (512, 128000 and 1024
characters) while the whole value, with its 2 separators, exceeds their sum of 129536."""
import json

import pytest

from joserfc import jws
from joserfc.errors import ExceededSizeError
from joserfc.jwk import RSAKey

KEY = RSAKey.generate_key(6144)  # an RS256 signature of 768 bytes: 1024 characters


def compact(payload_bytes: int) -> str:
    """A header of 384 bytes (512 characters) and a payload of `payload_bytes` bytes."""
    padding = 384 - len(json.dumps({"alg": "RS256", "kid": ""}, separators=(",", ":")))
    return jws.serialize_compact({"alg": "RS256", "kid": "k" * padding}, b"p" * payload_bytes, KEY)


def test_segments_within_their_limits_whole_value_beyond_the_total():
    # control: a payload of 127996 characters gives a value of 129534 characters, accepted
    accepted = compact(95997)
    assert len(accepted) == 129534
    assert jws.deserialize_compact(accepted, KEY).payload == b"p" * 95997

    received = compact(96000)  # payload of 128000 characters, value of 129538
    assert [len(part) for part in received.split(".")] == [512, 128000, 1024]
    with pytest.raises(ExceededSizeError):
        jws.deserialize_compact(received, KEY)
