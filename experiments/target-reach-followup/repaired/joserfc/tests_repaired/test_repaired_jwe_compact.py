"""Repaired variant of tests/jwe/test_compact.py::TestJWECompact::test_ciphertext_exceeds_size.

The original builds a ciphertext segment of 93334 characters (the encoding of
70000 bytes). The whole compact value then exceeds the sum of the 5 segment
limits (67712 characters), and JWERegistry.validate_compact_value_size rejects
it before the segments are checked. Here the ciphertext segment is the
encoding of 49153 bytes, 65538 characters: above the ciphertext limit of 65536
and with the whole value below 67712, so that
JWERegistry.validate_ciphertext_size rejects it. Nothing else changes.
"""

from unittest import TestCase

from joserfc.errors import ExceededSizeError
from joserfc.jwe import decrypt_compact
from joserfc.jwk import OctKey
from joserfc.util import json_b64encode, urlsafe_b64encode


class TestJWECompactRepaired(TestCase):
    def test_repaired_ciphertext_exceeds_size(self):
        header = json_b64encode({"alg": "dir", "enc": "A128GCM"}).decode("utf-8")
        ciphertext = urlsafe_b64encode(("a" * 49153).encode("utf-8")).decode("utf-8")
        s = header + "..YbDfdYa6p-wAEFul." + ciphertext + ".wES6-QAOEbErZqXiS0JHRw"
        self.assertRaises(ExceededSizeError, decrypt_compact, s, OctKey.import_key("secret"))
