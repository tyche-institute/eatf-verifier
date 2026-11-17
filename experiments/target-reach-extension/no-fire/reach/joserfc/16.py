#!/usr/bin/env python3
"""Row 16 of no-fire/sample.csv: joserfc `_rfc7516.message.decrypt_recipient#1`,
`raise InvalidEncryptedKeyError()` at `joserfc/_rfc7516/message.py`, line 249.

Input: `joserfc.jwe.decrypt_compact(token, key)` (an entry point), with no
setting other than the key. The token is a JWE Compact Serialization with
"alg": "dir" and "enc": "A128GCM", sealed with the key, whose second segment
(the JWE Encrypted Key) holds 16 bytes; with direct encryption that segment
has to be empty (RFC 7516, section 5.2, step 10).

Path read in the source: `jwe.py` 123-126 (default registry), 128
`extract_compact` (`_rfc7516/compact.py` 75 keeps the 16 bytes as
`recipient.encrypted_key`), 131-132 `guess_key` and `check_use`, 136
`perform_decrypt` -> `_rfc7516/message.py` 101 `_perform_decrypt` -> 107
`get_enc`, 110 `check_iv`, 120 `check_header`, 123 `get_alg`, 124
`decrypt_recipient` -> 244 (`direct_mode`: "dir" has no key size,
`_rfc7516/models.py` 246-248) -> 248 (`recipient.encrypted_key` is not empty)
-> 249. The handler at 126 catches the error and 128 raises the same object
again (`verify_all_recipients` is true by default, `_rfc7516/registry.py` 74).

Control, not an input of the result: the same token with an empty second
segment decrypts with the same key.

    python3 -I <this file>
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ beside the scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_harness as H  # noqa: E402

ROW = 16
CHECK = "_rfc7516.message.decrypt_recipient#1"
KEY = bytes(range(16))                      # 128-bit key: the CEK of "dir" with A128GCM
IV = bytes(range(100, 112))                 # 96-bit initialization vector
PLAINTEXT = b'{"iss":"https://issuer.example","sub":"reach-16"}'
ENCRYPTED_KEY = bytes(range(200, 216))      # 16 bytes in the second segment


def build(encrypted_key: bytes):
    def make():
        from joserfc import jwe
        from joserfc.jwk import OctKey
        token = H.jwe_dir_gcm(KEY, PLAINTEXT, IV, "A128GCM", encrypted_key)
        key = OctKey.import_key(KEY)
        facts = {"token_sha256": H.sha256_bytes(token.encode("ascii")),
                 "segment_lengths": H.segment_lengths(token),
                 "encrypted_key_bytes": len(encrypted_key),
                 "plaintext_sha256": H.sha256_bytes(PLAINTEXT)}
        return (lambda: jwe.decrypt_compact(token, key)), facts
    return make


CASES = [
    H.Case("input", "input", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "key: OctKey of a 16-byte key; algorithms, registry, sender_key: defaults",
           "dir + A128GCM compact JWE sealed with the key, with 16 bytes in the JWE Encrypted Key segment",
           build(ENCRYPTED_KEY)),
    H.Case("control-empty-encrypted-key", "control", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "as the input", "the same token with an empty JWE Encrypted Key segment",
           build(b"")),
]

if __name__ == "__main__":
    sys.exit(H.main(__file__, ROW, CHECK, CASES))
