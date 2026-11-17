#!/usr/bin/env python3
"""Row 18 of no-fire/sample.csv: joserfc
`_rfc7516.registry.JWERegistry.validate_ciphertext_size#1`,
`raise ExceededSizeError(f"Ciphertext size exceeds {self.max_ciphertext_length} bytes.")`
at `joserfc/_rfc7516/registry.py`, line 140.

Input: `joserfc.jwe.decrypt_compact(token, key)` (an entry point), with no
setting other than the key. The token is a JWE Compact Serialization with
"alg": "dir" and "enc": "A128GCM", sealed with the key, of a 49153-byte
plaintext: its ciphertext segment has 65538 characters, above the default
maximum of 65536 (`_rfc7516/registry.py` 62), while the whole token stays
below the maximum of the compact value, 1024 + 1024 + 64 + 65536 + 64 = 67712
(113-122).

Path read in the source: `jwe.py` 123-126 (default registry), 128
`extract_compact` -> `_rfc7516/compact.py` 37 (`validate_compact_value_size`
passes), 40 (5 segments), 44-46 (header, encrypted key and IV sizes pass), 47
`validate_ciphertext_size(ciphertext_segment)` -> `_rfc7516/registry.py` 139
(the segment is longer than 65536) -> 140. Nothing between 140 and the caller
catches it (`extract_compact` and `decrypt_compact` have no handler).

Control, not an input of the result: the same construction with a 49152-byte
plaintext (a ciphertext segment of 65536 characters) decrypts.

    python3 -I <this file>
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ beside the scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_harness as H  # noqa: E402

ROW = 18
CHECK = "_rfc7516.registry.JWERegistry.validate_ciphertext_size#1"
KEY = bytes(range(16, 32))
IV = bytes(range(112, 124))


def plaintext(length: int) -> bytes:
    """A JSON object of exactly `length` bytes."""
    return b'{"d":"' + b"A" * (length - 8) + b'"}'


def build(length: int):
    def make():
        from joserfc import jwe
        from joserfc.jwk import OctKey
        data = plaintext(length)
        token = H.jwe_dir_gcm(KEY, data, IV, "A128GCM")
        key = OctKey.import_key(KEY)
        facts = {"token_sha256": H.sha256_bytes(token.encode("ascii")),
                 "segment_lengths": H.segment_lengths(token), "token_length": len(token),
                 "plaintext_length": len(data), "plaintext_sha256": H.sha256_bytes(data)}
        return (lambda: jwe.decrypt_compact(token, key)), facts
    return make


CASES = [
    H.Case("input", "input", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "key: OctKey of a 16-byte key; algorithms, registry, sender_key: defaults",
           "dir + A128GCM compact JWE of a 49153-byte plaintext: ciphertext segment of 65538 characters",
           build(49153)),
    H.Case("control-at-limit", "control", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "as the input", "the same construction with a 49152-byte plaintext: segment of 65536 characters",
           build(49152)),
]

if __name__ == "__main__":
    sys.exit(H.main(__file__, ROW, CHECK, CASES))
