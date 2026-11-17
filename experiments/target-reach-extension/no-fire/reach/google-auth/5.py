"""Row 5 of no-fire/sample.csv: google-auth,
auth.credentials.AnonymousCredentials.refresh#1 (google/auth/credentials.py,
line 595, `raise exceptions.InvalidOperation("Anonymous credentials cannot be
refreshed.")`, the whole body of the method, without a guard).

    python3 -I -B 5.py

On a fresh copy of the release, in the environment of the first study, runs
the census of `reach_common.py` through the 2 functions named `decode`,
records whether line 595 executes and whether the check fires, and writes
`5.json`. No input is targeted at the check: neither function named `decode`
takes a credentials object, and none of the functions that a call of `decode`
can execute calls `refresh` (`READING.md`). The control, run last, is no input
through an entry point: it calls
`AnonymousCredentials().refresh(None)` directly, to show that the tracer
records the raise statement when it executes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_common as rc  # noqa: E402

ROW = 5
CHECK = "auth.credentials.AnonymousCredentials.refresh#1"


def inputs(art, jwt, jwt_async):
    return []


def control(art):
    import google.auth.credentials as credentials
    anonymous = credentials.AnonymousCredentials()
    return ("AnonymousCredentials().refresh(None)", anonymous.refresh, (None,), {})


if __name__ == "__main__":
    raise SystemExit(rc.main(__file__, ROW, CHECK, inputs, control))
