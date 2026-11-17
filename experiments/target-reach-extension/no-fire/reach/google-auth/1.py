"""Row 1 of no-fire/sample.csv: google-auth,
auth.aws.RequestSigner.get_request_options#1 (google/auth/aws.py, line 126,
`raise exceptions.InvalidResource("Invalid AWS service URL")`, under
`if not uri.hostname or uri.scheme != "https":` at line 125).

    python3 -I -B 1.py

On a fresh copy of the release, in the environment of the first study, runs
through the 2 functions named `decode` the targeted inputs below and the
census of `reach_common.py`, records whether line 126 executes and whether
the check fires, and writes `1.json`. The targeted inputs carry a URL that
the check rejects (scheme http, or no host) in the claims of a valid token,
the only place where an input through `decode` can hold a URL. The control,
run last, is no input through an entry point: it calls
`RequestSigner.get_request_options` directly with such a URL, to show that
the tracer records the raise statement when it executes. The result and its
reason from the source are in `READING.md`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach_common as rc  # noqa: E402

ROW = 1
CHECK = "auth.aws.RequestSigner.get_request_options#1"
HTTP_URL = "http://sts.us-east-1.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15"
NO_HOST_URL = "https://"


def inputs(art, jwt, jwt_async):
    d, a = "google.auth.jwt.decode", "google.auth._jwt_async.decode"
    with_http = art.token(payload=art.claims(aud=HTTP_URL))
    no_host = art.token(payload=art.claims(iss=NO_HOST_URL, aud=NO_HOST_URL))
    return [
        rc.Input("T1 aud is an http STS URL, audience the same", d, jwt.decode, (with_http,),
                 {"certs": art.rsa_cert, "audience": HTTP_URL},
                 f"RS256 token with aud {HTTP_URL}",
                 f"certs: public_cert.pem; audience={HTTP_URL!r}"),
        rc.Input("T2 iss and aud are https URLs without host", d, jwt.decode, (no_host,),
                 {"certs": art.rsa_cert, "audience": HTTP_URL},
                 "RS256 token with iss and aud 'https://'",
                 f"certs: public_cert.pem; audience={HTTP_URL!r}"),
        rc.Input("T3 async entry point, aud is an http STS URL", a, jwt_async.decode, (with_http,),
                 {"certs": art.rsa_cert, "audience": HTTP_URL},
                 f"RS256 token with aud {HTTP_URL}",
                 f"certs: public_cert.pem; audience={HTTP_URL!r}"),
    ]


def control(art):
    import google.auth.aws as aws
    signer = aws.RequestSigner("us-east-1")
    credentials = aws.AwsSecurityCredentials("AKIDEXAMPLE", "secret")
    return (f"RequestSigner('us-east-1').get_request_options(credentials, {HTTP_URL!r}, 'POST')",
            signer.get_request_options, (credentials, HTTP_URL, "POST"), {})


if __name__ == "__main__":
    raise SystemExit(rc.main(__file__, ROW, CHECK, inputs, control))
