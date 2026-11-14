# deleted check: jose.rfc7519.claims.BaseClaims._validate_essential_claims#2
"""A token whose essential "sub" claim is present with an empty value, under
options that name no value for the claim."""
import pytest

from authlib.jose import errors
from authlib.jose import jwt

OPTIONS = {"sub": {"essential": True}}


def claims(sub):
    token = jwt.encode({"alg": "HS256"}, {"sub": sub}, "secret")
    return jwt.decode(token, "secret", claims_options=OPTIONS)


def test_essential_claim_with_empty_value():
    # control: the same construction is accepted with a non-empty subject
    claims("alice").validate()

    with pytest.raises(errors.InvalidClaimError):
        claims("").validate()
