# deleted check: jwa._RSA.unwrap#1
"""A token whose header names AES GCM with a 128-bit key, while the
content-encryption key that it carries has 256 bits."""
import os

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from jwcrypto import jwe, jwk
from jwcrypto.common import base64url_encode, json_encode

KEY = jwk.JWK.generate(kty="RSA", size=2048)


def compact(content_key: bytes) -> str:
    """A compact serialization built by hand: `content_key` encrypted to the RSA
    key, under a header that names AES GCM with a 128-bit key."""
    protected = base64url_encode(json_encode({"alg": "RSA-OAEP", "enc": "A128GCM"}))
    nonce = os.urandom(12)
    sealed = AESGCM(content_key).encrypt(nonce, b"payload", protected.encode("ascii"))
    oaep = padding.OAEP(padding.MGF1(hashes.SHA1()), hashes.SHA1(), None)
    encrypted_key = KEY.get_op_key("wrapKey").encrypt(content_key, oaep)
    return ".".join([protected, base64url_encode(encrypted_key), base64url_encode(nonce),
                     base64url_encode(sealed[:-16]), base64url_encode(sealed[-16:])])


def test_content_key_longer_than_the_algorithm_names():
    # control: the same construction is accepted with a 128-bit content-encryption key
    accepted = jwe.JWE()
    accepted.deserialize(compact(os.urandom(16)), KEY)
    assert accepted.payload == b"payload"

    received = jwe.JWE()
    with pytest.raises(jwe.InvalidJWEData):
        received.deserialize(compact(os.urandom(32)), KEY)
