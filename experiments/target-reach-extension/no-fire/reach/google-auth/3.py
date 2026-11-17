"""Row 3 of no-fire/sample.csv: google-auth,
auth.crypt._python_rsa.RSASigner.from_string#1
(google/auth/crypt/_python_rsa.py, line 190,
`raise exceptions.InvalidValue("Unused bytes", remaining)`, under
`if remaining != b"":` at line 189, in the branch of a PKCS #8 key, line 187).

    python3 -I -B 3.py

On a fresh copy of the release, in the environment of the first study, runs
through the 2 functions named `decode` the targeted inputs below and the
census of `reach_common.py`, records whether line 190 executes and whether
the check fires, and writes `3.json`. The targeted inputs give `decode`, as
the value of its documented parameter `certs`, the PEM block that the check
rejects: the RSA key of tests/data/privatekey.pem in PKCS #8 with 1 byte after
its DER structure (and once without it), for RS256 and ES256 tokens and in a
mapping by key id. The control, run last, is no input through an entry
point: it calls `_python_rsa.RSASigner.from_string` directly with that PEM
block, to show that the check rejects the block and that the tracer records
the raise statement when it executes. The result and its
reason from the source are in `READING.md`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_common as rc  # noqa: E402

ROW = 3
CHECK = "auth.crypt._python_rsa.RSASigner.from_string#1"


def inputs(art, jwt, jwt_async):
    d, a = "google.auth.jwt.decode", "google.auth._jwt_async.decode"
    good = art.token()
    trailing = art.pkcs8_private_key_pem(b"\x00")
    plain = art.pkcs8_private_key_pem()
    return [
        rc.Input("T1 PKCS #8 key with 1 trailing byte as certificate", d, jwt.decode, (good,),
                 {"certs": trailing}, "RS256 token signed with tests/data/privatekey.pem",
                 "certs: PKCS #8 PEM of privatekey.pem + 1 byte 00 after the DER"),
        rc.Input("T2 the same PEM under the token's kid", d, jwt.decode, (art.token(kid="1"),),
                 {"certs": {"1": trailing}}, "RS256 token with kid 1",
                 "certs: {'1': PKCS #8 PEM + 1 byte 00}"),
        rc.Input("T3 the same PEM, ES256 token", d, jwt.decode, (art.token("ES256"),),
                 {"certs": trailing}, "ES256 token signed with es256_privatekey.pem",
                 "certs: PKCS #8 PEM + 1 byte 00"),
        rc.Input("T4 PKCS #8 key without trailing byte as certificate", d, jwt.decode, (good,),
                 {"certs": plain}, "RS256 token", "certs: PKCS #8 PEM of privatekey.pem"),
        rc.Input("T5 async entry point, PEM with 1 trailing byte", a, jwt_async.decode, (good,),
                 {"certs": trailing}, "RS256 token", "certs: PKCS #8 PEM + 1 byte 00"),
    ]


def control(art):
    from google.auth.crypt import _python_rsa
    return ("_python_rsa.RSASigner.from_string(PKCS #8 PEM + 1 byte 00)",
            _python_rsa.RSASigner.from_string, (art.pkcs8_private_key_pem(b"\x00"),), {})


if __name__ == "__main__":
    raise SystemExit(rc.main(__file__, ROW, CHECK, inputs, control))
