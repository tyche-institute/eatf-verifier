#!/usr/bin/env python3
"""Row 6 of ../../sample.csv: the check
oauth2.rfc6749.grant_types.authorization_code.AuthorizationCodeGrant.validate_token_request#9,
`raise errors.MissingRedirectURIError(request=request)` at line 510 of
oauthlib/oauth2/rfc6749/grant_types/authorization_code.py.

Entry point: AuthorizationCodeGrant.validate_token_request
(authorization_code.py, line 436).

Input: an access token request of the authorization code grant (RFC 6749,
section 4.1.3), sent with POST, that carries no `redirect_uri`. The client is
confidential and authenticates with HTTP Basic; the code was issued to it.
The provider's request validator knows no default redirect URI for the client.

    ../../../../target-reach/work/venvs/oauthlib/bin/python -I -B 6.py

trace_input.py says what is checked, copied and traced; the record is
6.record.json.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_input  # noqa: E402

ROW = 6
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
        """The provider's records: 1 confidential client, allowed the authorization
        code grant and registered without a default redirect URI, and 1 code issued
        to it by an authorization request without `redirect_uri`. Each call is
        logged with its answer."""

        clients = {CLIENT_ID: {"secret": SECRET, "grant_types": ["authorization_code"],
                               "default_redirect_uri": None}}
        codes = {CODE: {"client_id": CLIENT_ID, "user": "resource-owner-1", "scopes": ["profile"]}}

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

        def validate_code(self, client_id, code, client, request, *args, **kwargs):
            issued = self.codes.get(code)
            if issued is None or issued["client_id"] != client_id:
                return self.log("validate_code", False)
            request.user, request.scopes = issued["user"], list(issued["scopes"])
            return self.log("validate_code", True)

        def get_code_challenge(self, code, request):
            return self.log("get_code_challenge (library default)", super().get_code_challenge(code, request))

        def is_pkce_required(self, client_id, request):
            return self.log("is_pkce_required (library default)", super().is_pkce_required(client_id, request))

        def get_default_redirect_uri(self, client_id, request, *args, **kwargs):
            return self.log("get_default_redirect_uri", self.clients[client_id]["default_redirect_uri"])

    basic = base64.b64encode(f"{CLIENT_ID}:{SECRET}".encode("utf-8")).decode("ascii")
    request = Request("https://server.example.com/token", http_method="POST",
                      body=f"grant_type=authorization_code&code={CODE}",
                      headers={"Authorization": f"Basic {basic}",
                               "Content-Type": "application/x-www-form-urlencoded"})
    grant = AuthorizationCodeGrant(Validator())
    return {
        "entry_point": grant.validate_token_request,
        "call": lambda: grant.validate_token_request(request),
        "validator": grant.request_validator,
        "input": ("POST https://server.example.com/token, Authorization: Basic (client s6BhdRkqt3 and its "
                  "secret), body grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA, no redirect_uri"),
        "settings": [
            "AuthorizationCodeGrant(request_validator) with no other argument: no custom validators, "
            "the library's code challenge methods",
            "request validator, a subclass of oauthlib.oauth2.RequestValidator: client_authentication_required, "
            "get_code_challenge and is_pkce_required keep the library's defaults (True, None, False)",
            "authenticate_client: accepts the HTTP Basic credentials of the registered client and sets "
            "request.client (the library has no default)",
            "validate_grant_type: True, the client is allowed the authorization code grant (no default)",
            "validate_code: True, the code was issued to the client; sets request.user and request.scopes "
            "(no default)",
            "get_default_redirect_uri: None, the client is registered without a default redirect URI "
            "(no default)",
        ],
    }


if __name__ == "__main__":
    sys.exit(trace_input.main(ROW, build))
