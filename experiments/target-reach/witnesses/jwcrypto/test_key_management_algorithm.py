# deleted check: jwe.JWE._jwa_keymgmt#1
"""A token whose key-management algorithm is outside the allowed list, while its
content-encryption algorithm is inside it."""
import pytest

from jwcrypto import jwe, jwk
from jwcrypto.common import json_encode


def test_key_management_algorithm_not_allowed():
    key = jwk.JWK.generate(kty="oct", size=128)
    token = jwe.JWE(b"payload", json_encode({"alg": "A128KW", "enc": "A256GCM"}))
    token.add_recipient(key)
    serialized = token.serialize(compact=True)

    # control: the token is accepted when both algorithms are allowed
    accepted = jwe.JWE(algs=["A128KW", "A256GCM"])
    accepted.deserialize(serialized, key)
    assert accepted.payload == b"payload"

    received = jwe.JWE(algs=["A256KW", "A256GCM"])
    with pytest.raises(jwe.InvalidJWEData):
        received.deserialize(serialized, key)
