"""Repaired variant of tests/jwe/test_compact.py::TestJWECompact::test_header_exceeds_size.

The original builds a protected header segment of 679188 characters (the
encoding of a JSON object of 1000 members). The whole compact value then
exceeds the sum of the 5 segment limits (67712 characters), and
JWERegistry.validate_compact_value_size rejects it before the segments are
checked. Here the object has 32 members, a segment of 1034 characters: above
the header limit of 1024 and with the whole value below 67712, so that
JWERegistry.validate_protected_header_size rejects it. Nothing else changes.
"""

from unittest import TestCase

from joserfc.errors import ExceededSizeError
from joserfc.jwe import decrypt_compact
from joserfc.jwk import OctKey
from joserfc.util import json_b64encode


class TestJWECompactHeaderRepaired(TestCase):
    def test_repaired_header_exceeds_size(self):
        header = json_b64encode({f"a{i}": "a" * i for i in range(32)}).decode("utf-8")
        s = header + "..YbDfdYa6p-wAEFul.YK7j0MsH-Dko6ifsEg.wES6-QAOEbErZqXiS0JHRw"
        self.assertRaises(ExceededSizeError, decrypt_compact, s, OctKey.import_key("secret"))
