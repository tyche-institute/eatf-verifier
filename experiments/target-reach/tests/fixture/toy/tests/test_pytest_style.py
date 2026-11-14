import pytest

from toyverify import decode, encode
from toyverify.errors import ClaimMissing, FormatError, PolicyError, ToyError

GOOD = 'v1.{"aud": "a"}.sig-secret1'


def test_good_token():
    assert decode(GOOD) == {"aud": "a"}


def test_non_string_token():
    with pytest.raises(FormatError, match="string"):
        decode(5)


def test_three_parts_needed():
    pytest.raises(FormatError, decode, "v1.x")


@pytest.mark.parametrize("body", ["{", "[1,"])
def test_bad_json_body(body):
    with pytest.raises(FormatError) as excinfo:
        decode(f"v1.{body}.sig-secret1")
    assert "bad json" in str(excinfo.value)


def test_versions_loop():
    for head in ["v0", "v9"]:
        with pytest.raises(PolicyError):
            decode(head + '.{"aud": "a"}.bad')


def test_audience_mismatch():
    with pytest.raises(PolicyError) as excinfo:
        decode(GOOD, audience="b")
    assert str(excinfo.value) == "audience mismatch"


def test_missing_audience_claim():
    with pytest.raises(ClaimMissing) as excinfo:
        decode('v1.{}.sig-secret1')
    assert excinfo.value.claim == "aud"


def test_expired():
    with pytest.raises(PolicyError, match="expired"):
        decode('v1.{"aud": "a", "exp": 0}.sig-secret1')


def test_signature_with_revoked_key():
    with pytest.raises(PolicyError):
        decode('v1.{"aud": "a"}.sig-secret3', key="k3")


def test_signature_twice():
    with pytest.raises(PolicyError, match="signature"):
        decode('v1.{"aud": "a"}.wrong')
    with pytest.raises(PolicyError):
        decode('v1.{"aud": "a"}.wrong')


def test_unknown_key():
    with pytest.raises(ToyError) as excinfo:
        decode(GOOD, key="nokey")
    excinfo.match("unknown key")


def test_lookup_error_passes_through():
    with pytest.raises(LookupError):
        decode(GOOD, key="k2")


def test_encode_rejects_list():
    with pytest.raises(FormatError):
        encode([1])
