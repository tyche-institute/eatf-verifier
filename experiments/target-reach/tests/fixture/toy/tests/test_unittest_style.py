import unittest

from toyverify import decode
from toyverify.errors import FormatError, PolicyError

GOOD = 'v1.{"aud": "a"}.sig-secret1'


class TestToy(unittest.TestCase):
    def test_non_string_token(self):
        with self.assertRaises(FormatError) as cm:
            decode(7)
        self.assertEqual(str(cm.exception), "token must be a string")

    def test_three_parts_callable(self):
        self.assertRaises(FormatError, decode, "a.b")

    def test_bad_json_regex(self):
        with self.assertRaisesRegex(FormatError, "json"):
            decode("v1.{.x")

    def test_bad_json_regex_callable(self):
        self.assertRaisesRegex(FormatError, "json", decode, "v1.[.x")

    def test_audience_in_message(self):
        with self.assertRaises(PolicyError) as cm:
            decode(GOOD, audience="zz")
        self.assertIn("audience", str(cm.exception))
