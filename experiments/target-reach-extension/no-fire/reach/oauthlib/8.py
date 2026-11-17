#!/usr/bin/env python3
"""Row 8 of ../../sample.csv: the check
oauth2.rfc6749.grant_types.base.GrantTypeBase.validate_grant_type#1,
`raise errors.UnauthorizedClientError(request=request)` at line 162 of
oauthlib/oauth2/rfc6749/grant_types/base.py.

Entry point: AuthorizationCodeGrant.validate_token_request
(oauthlib/oauth2/rfc6749/grant_types/authorization_code.py, line 436), which
calls GrantTypeBase.validate_grant_type at line 460.

Input: an access token request of the authorization code grant (RFC 6749,
section 4.1.3), sent with POST by a confidential client that authenticates
with HTTP Basic and that the provider allows the client credentials grant
only.

    ../../../../target-reach/work/venvs/oauthlib/bin/python -I -B 8.py

trace_input.py says what is checked, copied and traced; the record is
8.record.json.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_input  # noqa: E402

ROW = 8
# The client identifier and the code of the examples in the docstrings of
# oauthlib/oauth2/rfc6749/parameters.py (lines 59 and 141).
CLIENT_ID = "s6BhdRkqt3"
SECRET = "7Fjfp0ZBr1KtDRbnfVdmIw"
CODE = "SplxlOBeZQQYbYS6WxSbIA"


def build() -> dict:
    from oauthlib.common import Request
    from oauthlib.oauth2 import AuthorizationCodeGrant, RequestValidator

    class Client:
        def __init__(self, client_id: str) -> None:
            self.client_id = client_id

    class Validator(RequestValidator):
        """The provider's records: 1 confidential client, allowed the client
        credentials grant only. Each call is logged with its answer."""

        clients = {CLIENT_ID: {"secret": SECRET, "grant_types": ["client_credentials"]}}

        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def log(self, name: str, value):
            self.calls.append([name, repr(value)])
            return value

        def client_authentication_required(self, request, *args, **kwargs):
            return self.log("client_authentication_required (library default)",
                            super().client_authentication_required(request, *args, **kwargs))

        def authenticate_client(self, request, *args, **kwargs):
            scheme, _, value = request.headers.get("Authorization", "").partition(" ")
            client_id, secret = "", ""
            if scheme == "Basic":
                client_id, _, secret = base64.b64decode(value).decode("utf-8").partition(":")
            known = self.clients.get(client_id)
            if known is None or known["secret"] != secret:
                return self.log("authenticate_client", False)
            request.client = Client(client_id)
            return self.log("authenticate_client", True)

        def validate_grant_type(self, client_id, grant_type, client, request, *args, **kwargs):
            return self.log("validate_grant_type", grant_type in self.clients[client_id]["grant_types"])

    basic = base64.b64encode(f"{CLIENT_ID}:{SECRET}".encode("utf-8")).decode("ascii")
    request = Request("https://server.example.com/token", http_method="POST",
                      body=(f"grant_type=authorization_code&code={CODE}"
                            "&redirect_uri=https%3A%2F%2Fclient.example.com%2Fcb"),
                      headers={"Authorization": f"Basic {basic}",
                               "Content-Type": "application/x-www-form-urlencoded"})
    grant = AuthorizationCodeGrant(Validator())
    return {
        "entry_point": grant.validate_token_request,
        "call": lambda: grant.validate_token_request(request),
        "validator": grant.request_validator,
        "input": ("POST https://server.example.com/token, Authorization: Basic (client s6BhdRkqt3 and its "
                  "secret), body grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA"
                  "&redirect_uri=https%3A%2F%2Fclient.example.com%2Fcb"),
        "settings": [
            "AuthorizationCodeGrant(request_validator) with no other argument: no custom validators",
            "request validator, a subclass of oauthlib.oauth2.RequestValidator: client_authentication_required "
            "keeps the library's default (True)",
            "authenticate_client: accepts the HTTP Basic credentials of the registered client and sets "
            "request.client (the library has no default)",
            "validate_grant_type: False, the client is allowed the client credentials grant only "
            "(no default)",
        ],
    }


if __name__ == "__main__":
    sys.exit(trace_input.main(ROW, build))
