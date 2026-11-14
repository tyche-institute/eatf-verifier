# deleted check: jwa._AesKw._get_key#2
"""A token whose header names AES Key Wrap with a 256-bit key, while the key that
wraps the content-encryption key has 128 bits."""
import os

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.keywrap import aes_key_wrap

from jwcrypto import jwe, jwk
from jwcrypto.common import base64url_encode, json_encode


def compact(algorithm: str, wrapping_key: bytes) -> str:
    """A compact serialization built by hand: a 256-bit content-encryption key,
    wrapped with `wrapping_key`, under a header that names `algorithm`."""
    protected = base64url_encode(json_encode({"alg": algorithm, "enc": "A256GCM"}))
    content_key, nonce = os.urandom(32), os.urandom(12)
    sealed = AESGCM(content_key).encrypt(nonce, b"payload", protected.encode("ascii"))
    return ".".join([protected, base64url_encode(aes_key_wrap(wrapping_key, content_key)),
                     base64url_encode(nonce), base64url_encode(sealed[:-16]),
                     base64url_encode(sealed[-16:])])


def test_key_shorter_than_the_algorithm_names():
    wrapping_key = os.urandom(16)
    key = jwk.JWK(kty="oct", k=base64url_encode(wrapping_key))

    # control: the same construction is accepted under the 128-bit algorithm
    accepted = jwe.JWE()
    accepted.deserialize(compact("A128KW", wrapping_key), key)
    assert accepted.payload == b"payload"

    received = jwe.JWE()
    with pytest.raises(jwe.InvalidJWEData):
        received.deserialize(compact("A256KW", wrapping_key), key)
