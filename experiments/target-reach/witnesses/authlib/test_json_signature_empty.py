# deleted check: jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2
"""A flattened JSON serialization with an empty "signature" value, under the
"none" algorithm that the caller allows explicitly."""
import pytest

from authlib.jose import JsonWebSignature
from authlib.jose import errors


def test_json_serialization_with_empty_signature():
    jws = JsonWebSignature(algorithms=["none"])

    # control: the same unsigned content is accepted in the compact serialization
    compact = jws.serialize_compact({"alg": "none"}, b"payload", None)
    assert jws.deserialize_compact(compact, None)["payload"] == b"payload"

    flattened = jws.serialize_json({"protected": {"alg": "none"}}, b"payload", None)
    assert flattened["signature"] == ""
    with pytest.raises(errors.DecodeError):
        jws.deserialize_json(flattened, None)
