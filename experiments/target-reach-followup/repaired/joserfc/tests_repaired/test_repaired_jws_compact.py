"""Repaired variant of tests/jws/test_compact.py::TestCompact::test_payload_exceeded_size_error.

The original builds a payload segment of 170668 characters (the encoding of
128000 + 1 bytes). The whole compact value then exceeds the sum of the 3
segment limits (129536 characters), and JWSRegistry.validate_compact_value_size
rejects it before the segments are checked. The payload limit of 128000 applies
to the encoded segment. Here the payload is 96000 + 1 bytes, a segment of
128002 characters: above the payload limit and with the whole value below
129536, so that JWSRegistry.validate_payload_size rejects it. Nothing else
changes.
"""

from unittest import TestCase

from joserfc.errors import ExceededSizeError
from joserfc.jwk import OctKey
from joserfc.jws import deserialize_compact
from joserfc.util import json_b64encode, urlsafe_b64encode


class TestCompactRepaired(TestCase):
    key = OctKey.import_key("secret")

    def test_repaired_payload_exceeded_size_error(self):
        header = json_b64encode({"alg": "HS256"})
        exceeded_payload = urlsafe_b64encode(("o" * (96000 + 1)).encode("utf8"))
        fake_jws = header + b"." + exceeded_payload + b"." + urlsafe_b64encode(b"o")
        self.assertRaises(ExceededSizeError, deserialize_compact, fake_jws, self.key)
