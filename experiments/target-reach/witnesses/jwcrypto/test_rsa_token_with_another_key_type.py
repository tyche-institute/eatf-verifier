# deleted check: jwa._RSA._check_key#1
"""An attempt that is expected not to hold: a token for an RSA key, given a key of
another type outside a key set. The library rejects it with and without the check."""
import pytest

from jwcrypto import jwe, jwk
from jwcrypto.common import json_encode

RSA = jwk.JWK.generate(kty="RSA", size=2048)
OTHER = {"symmetric": jwk.JWK.generate(kty="oct", size=256),
         "elliptic curve": jwk.JWK.generate(kty="EC", crv="P-256")}


@pytest.mark.parametrize("algorithm", ["RSA-OAEP", "RSA1_5"])
@pytest.mark.parametrize("kind", sorted(OTHER))
def test_rsa_token_with_another_key_type(algorithm, kind):
    allowed = [algorithm, "A256GCM"]
    token = jwe.JWE(b"payload", json_encode({"alg": algorithm, "enc": "A256GCM"}), algs=allowed)
    token.add_recipient(RSA)
    serialized = token.serialize(compact=True)

    # control: the token is accepted with its own key
    accepted = jwe.JWE(algs=allowed)
    accepted.deserialize(serialized, RSA)
    assert accepted.payload == b"payload"

    received = jwe.JWE(algs=allowed)
    with pytest.raises(jwe.InvalidJWEData):
        received.deserialize(serialized, OTHER[kind])
