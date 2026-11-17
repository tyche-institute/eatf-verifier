#!/usr/bin/env python3
"""Row 20 of no-fire/sample.csv: joserfc `_rfc7516.registry.JWERegistry._check_algorithm#2`,
`raise UnsupportedAlgorithmError(f"Algorithm of '{name}' is not allowed")`
at `joserfc/_rfc7516/registry.py`, line 190.

Input: `joserfc.jwe.decrypt_compact(token, key, algorithms=["dir", "A256GCM"])`
(an entry point). The setting that is not the default is `algorithms`
(default None), the documented parameter "a collection (list, tuple, or set)
of allowed algorithms" (`jwe.py` 118). The token is a JWE Compact
Serialization with "alg": "dir" and "enc": "A128GCM", sealed with the key.

Path read in the source: `jwe.py` 123-124 (`algorithms` given: a new
JWERegistry with `allowed` = the list, `_rfc7516/registry.py` 83), 128
`extract_compact`, 131-132, 136 `perform_decrypt` -> `_rfc7516/message.py` 101
-> 107 `registry.get_enc("A128GCM")` -> `_rfc7516/registry.py` 171-172 -> 185
("A128GCM" is registered) -> 188 (`allowed` is set) -> 189 ("A128GCM" is not
in it) -> 190. Line 107 is outside the handler of 118-128, and
`perform_decrypt` (99-103) catches only InvalidExchangeKeyError.

Control, not an input of the result: the same token decrypts with the default
settings.

    python3 -I <this file>
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ beside the scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_harness as H  # noqa: E402

ROW = 20
CHECK = "_rfc7516.registry.JWERegistry._check_algorithm#2"
KEY = bytes(range(64, 80))
IV = bytes(range(124, 136))
PLAINTEXT = b'{"iss":"https://issuer.example","sub":"reach-20"}'
ALLOWED = ["dir", "A256GCM"]


def build(algorithms):
    def make():
        from joserfc import jwe
        from joserfc.jwk import OctKey
        token = H.jwe_dir_gcm(KEY, PLAINTEXT, IV, "A128GCM")
        key = OctKey.import_key(KEY)
        facts = {"token_sha256": H.sha256_bytes(token.encode("ascii")), "segment_lengths": H.segment_lengths(token),
                 "algorithms": algorithms, "plaintext_sha256": H.sha256_bytes(PLAINTEXT)}
        if algorithms is None:
            return (lambda: jwe.decrypt_compact(token, key)), facts
        return (lambda: jwe.decrypt_compact(token, key, algorithms=algorithms)), facts
    return make


CASES = [
    H.Case("input", "input", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "algorithms=[\"dir\", \"A256GCM\"] (default None); key: OctKey of a 16-byte key; "
           "registry, sender_key: defaults",
           "dir + A128GCM compact JWE sealed with the key", build(ALLOWED)),
    H.Case("control-default-settings", "control", "joserfc.jwe.decrypt_compact (jwe.py:96)",
           "key only; algorithms, registry, sender_key: defaults", "the same token", build(None)),
]

if __name__ == "__main__":
    sys.exit(H.main(__file__, ROW, CHECK, CASES))
