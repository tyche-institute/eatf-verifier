"""Row 2 of no-fire/sample.csv: google-auth,
auth._agent_identity_utils.parse_certificate#1
(google/auth/_agent_identity_utils.py, line 329,
`raise ValueError("Certificate bytes cannot be empty or None.")`, under
`if not cert_bytes:` at line 328).

    python3 -I -B 2.py

On a fresh copy of the release, in the environment of the first study, runs
through the 2 functions named `decode` the targeted inputs below and the
census of `reach_common.py`, records whether line 329 executes and whether
the check fires, and writes `2.json`. The targeted inputs give `decode` an
empty certificate, the value that the check rejects, through its documented
parameter `certs` (as bytes, as str and in a mapping by key id, for RS256 and
ES256 tokens); the census adds `certs=None`. The control, run last, is no
input through an entry point: it calls `parse_certificate(b"")` directly, to
show that the tracer records the raise statement when it executes. The
result and its reason from the source are in `READING.md`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_common as rc  # noqa: E402

ROW = 2
CHECK = "auth._agent_identity_utils.parse_certificate#1"


def inputs(art, jwt, jwt_async):
    d, a = "google.auth.jwt.decode", "google.auth._jwt_async.decode"
    good = art.token()
    return [
        rc.Input("T1 empty certificate, bytes", d, jwt.decode, (good,), {"certs": b""},
                 "RS256 token signed with tests/data/privatekey.pem", "certs=b''"),
        rc.Input("T2 empty certificate, str", d, jwt.decode, (good,), {"certs": ""},
                 "RS256 token", "certs=''"),
        rc.Input("T3 empty certificate under the token's kid", d, jwt.decode, (art.token(kid="1"),),
                 {"certs": {"1": b""}}, "RS256 token with kid 1", "certs={'1': b''}"),
        rc.Input("T4 empty certificate, ES256 token", d, jwt.decode, (art.token("ES256"),),
                 {"certs": b""}, "ES256 token signed with es256_privatekey.pem", "certs=b''"),
        rc.Input("T5 async entry point, empty certificate", a, jwt_async.decode, (good,),
                 {"certs": b""}, "RS256 token", "certs=b''"),
    ]


def control(art):
    import google.auth._agent_identity_utils as agent
    return ("parse_certificate(b'')", agent.parse_certificate, (b"",), {})


if __name__ == "__main__":
    raise SystemExit(rc.main(__file__, ROW, CHECK, inputs, control))
