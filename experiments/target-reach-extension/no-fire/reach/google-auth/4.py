"""Row 4 of no-fire/sample.csv: google-auth,
auth.credentials.AnonymousCredentials.apply#1 (google/auth/credentials.py,
line 606, `raise exceptions.InvalidValue("Anonymous credentials don't support
tokens.")`, under `if token is not None:` at line 605).

    python3 -I -B 4.py

On a fresh copy of the release, in the environment of the first study, runs
the census of `reach_common.py` through the 2 functions named `decode`,
records whether line 606 executes and whether the check fires, and writes
`4.json`. No input is targeted at the check: neither function named `decode`
takes a credentials object or a token for one, and none of the functions that
a call of `decode` can execute calls `apply` (`READING.md`). The control, run
last, is no input through an entry point: it calls
`AnonymousCredentials().apply({}, token="token")` directly, to show that the
tracer records the raise statement when it executes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_common as rc  # noqa: E402

ROW = 4
CHECK = "auth.credentials.AnonymousCredentials.apply#1"


def inputs(art, jwt, jwt_async):
    return []


def control(art):
    import google.auth.credentials as credentials
    anonymous = credentials.AnonymousCredentials()
    return ("AnonymousCredentials().apply({}, token='token')", anonymous.apply, ({},), {"token": "token"})


if __name__ == "__main__":
    raise SystemExit(rc.main(__file__, ROW, CHECK, inputs, control))
