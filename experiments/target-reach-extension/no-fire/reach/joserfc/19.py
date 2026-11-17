#!/usr/bin/env python3
"""Row 19 of no-fire/sample.csv: joserfc `_rfc7516.registry.JWERegistry._check_algorithm#1`,
`raise UnsupportedAlgorithmError(f"Algorithm of '{name}' is not supported")`
at `joserfc/_rfc7516/registry.py`, line 186.

Input: `joserfc.jwe.decrypt_compact(token, key)` (an entry point), with no
setting other than the key. The token is a JWE Compact Serialization with
"alg": "dir" and "enc": "XC20P" (XChaCha20-Poly1305), sealed with a 256-bit
key and a 192-bit nonce by the pycryptodome cipher of the environment. The
package defines XC20P only in `drafts/jwe_chacha20.py` (33-34), and its
`register_chacha20_poly1305` (39-41) is not called by default, so "XC20P" is
not in the "enc" registry.

Path read in the source: `jwe.py` 123-126 (default registry), 128
`extract_compact` (sizes and header pass), 131-132, 136 `perform_decrypt` ->
`_rfc7516/message.py` 101 -> 107 `registry.get_enc("XC20P")` ->
`_rfc7516/registry.py` 171-172 -> 185 ("XC20P" is not in the registry) -> 186.
Line 107 is outside the handler of 118-128, and `perform_decrypt` (99-103)
catches only InvalidExchangeKeyError, so the error reaches the caller.

    python3 -I <this file>
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ beside the scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_harness as H  # noqa: E402

ROW = 19
CHECK = "_rfc7516.registry.JWERegistry._check_algorithm#1"
KEY = bytes(range(32, 64))                  # 256-bit key
NONCE = bytes(range(64, 88))                # 192-bit nonce of XChaCha20
PLAINTEXT = b'{"iss":"https://issuer.example","sub":"reach-19"}'


def build():
    from joserfc import jwe
    from joserfc.jwk import OctKey
    token = H.jwe_dir_xc20p(KEY, PLAINTEXT, NONCE)
    key = OctKey.import_key(KEY)
    facts = {"token_sha256": H.sha256_bytes(token.encode("ascii")), "segment_lengths": H.segment_lengths(token),
             "plaintext_sha256": H.sha256_bytes(PLAINTEXT)}
    return (lambda: jwe.decrypt_compact(token, key)), facts


CASES = [
    H.Case("input", "input", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "key: OctKey of a 32-byte key; algorithms, registry, sender_key: defaults",
           "dir + XC20P compact JWE sealed with the key (enc not registered by default)",
           build),
]

if __name__ == "__main__":
    sys.exit(H.main(__file__, ROW, CHECK, CASES))
