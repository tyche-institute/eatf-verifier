"""Repaired variant of the second block of
tests/jws/test_json.py::TestJSON::test_b64_must_be_protected.

The original block puts `b64` in the unprotected header and lists it in `crit`
of a protected header that does not hold it. reject_unprotected_crit_header
(joserfc/registry.py, lines 228 to 230) rejects every name listed in `crit`
that stands in the unprotected header and not in the protected one, so it
rejects that input before _is_payload_base64_encoded can. Here the protected
header also holds `"b64": True`; `b64` still stands in the unprotected header,
and _is_payload_base64_encoded rejects it. Nothing else changes. The first
block of the original test is not repeated: its target already decides it.
"""

from unittest import TestCase

from joserfc.errors import UnsupportedHeaderError
from joserfc.jwk import OctKey
from joserfc.jws import deserialize_json, serialize_json
from joserfc.util import json_b64encode, to_str


class TestJSONRepaired(TestCase):
    key = OctKey.import_key("secret")

    def test_repaired_b64_must_be_protected(self):
        value = serialize_json({"protected": {"alg": "HS256"}}, b"hello", self.key)
        value["protected"] = to_str(json_b64encode({"alg": "HS256", "b64": True, "crit": ["b64"]}))
        value["header"] = {"b64": True}
        self.assertRaises(UnsupportedHeaderError, deserialize_json, value, self.key)
