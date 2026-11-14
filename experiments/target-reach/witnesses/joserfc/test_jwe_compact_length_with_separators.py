# deleted check: _rfc7516.registry.JWERegistry.validate_compact_value_size#1
"""A compact JWE, under a registry whose limits on the initialization vector and the tag are
the lengths that A128GCM uses, whose 5 segments each fit their limits while the whole value,
with its 4 separators, exceeds their sum."""
import json

import pytest

from joserfc import jwe
from joserfc.errors import ExceededSizeError
from joserfc.jwk import RSAKey

KEY = RSAKey.generate_key(6144)  # an RSA-OAEP encrypted key of 768 bytes: 1024 characters


class GCMRegistry(jwe.JWERegistry):
    max_initialization_vector_length = 16  # 12 bytes
    max_auth_tag_length = 22  # 16 bytes


REGISTRY = GCMRegistry(algorithms=["RSA-OAEP", "A128GCM"])  # sum of the limits: 67622


def compact(plaintext_bytes: int) -> str:
    """A header of 768 bytes (1024 characters) and a plaintext of `plaintext_bytes` bytes."""
    base = {"alg": "RSA-OAEP", "enc": "A128GCM", "kid": ""}
    header = dict(base, kid="k" * (768 - len(json.dumps(base, separators=(",", ":")))))
    return jwe.encrypt_compact(header, b"p" * plaintext_bytes, KEY, registry=REGISTRY)


def test_segments_within_their_limits_whole_value_beyond_the_total():
    # control: a ciphertext of 65532 characters gives a value of 67622 characters, accepted
    accepted = compact(49149)
    assert len(accepted) == 67622
    assert jwe.decrypt_compact(accepted, KEY, registry=REGISTRY).plaintext == b"p" * 49149

    received = compact(49152)  # ciphertext of 65536 characters, value of 67626
    assert [len(part) for part in received.split(".")] == [1024, 1024, 16, 65536, 22]
    with pytest.raises(ExceededSizeError):
        jwe.decrypt_compact(received, KEY, registry=REGISTRY)
