#!/usr/bin/env python3
"""Row 10 of ../../sample.csv: the check
oauth2.rfc8628.grant_types.device_code.DeviceCodeGrant.validate_device_code#3,
`raise rfc6749_errors.InvalidGrantError(request=request)` at line 202 of
oauthlib/oauth2/rfc8628/grant_types/device_code.py.

Entry point: DeviceCodeGrant.validate_token_request (device_code.py, line
116), which calls DeviceCodeGrant.validate_device_code at line 147.

Input: a device access token request (RFC 8628, section 3.4) sent with POST,
with the grant type of the device flow and a device code of which the
provider holds no record. The client is confidential and authenticates with
HTTP Basic. The provider's request validator answers the device code with
None, the answer that its documentation gives for an unknown or invalid
device code (oauthlib/oauth2/rfc8628/request_validator.py, lines 49-50).

    ../../../../target-reach/work/venvs/oauthlib/bin/python -I -B 10.py

trace_input.py says what is checked, copied and traced; the record is
10.record.json.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_input  # noqa: E402

ROW = 10
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"   # device_code.py, line 129
# The device code of the example response in the docstring of
# oauthlib/oauth2/rfc8628/endpoints/device_authorization.py (line 173), and the
# client identifier of examples/device_code_flow.py (line 76) of the clone.
DEVICE_CODE = "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS"
CLIENT_ID = "1406020730"
SECRET = "7Fjfp0ZBr1KtDRbnfVdmIw"


def build() -> dict:
    from oauthlib.common import Request
    from oauthlib.oauth2 import DeviceCodeGrant
    from oauthlib.oauth2.rfc8628.request_validator import RequestValidator

    class Client:
        def __init__(self, client_id: str) -> None:
            self.client_id = client_id

    class Validator(RequestValidator):
        """The provider's records: 1 confidential client, allowed the device
        flow, and no device code on record (none was issued, or it was
        removed). Each call is logged with its answer."""

        clients = {CLIENT_ID: {"secret": SECRET, "grant_types": [GRANT_TYPE]}}
        device_codes: dict[str, dict] = {}

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

        def validate_device_code(self, client_id, code, request, *args, **kwargs):
            issued = self.device_codes.get(code)
            if issued is None or issued["client_id"] != client_id:
                return self.log("validate_device_code", None)
            return self.log("validate_device_code", issued["status"])

    basic = base64.b64encode(f"{CLIENT_ID}:{SECRET}".encode("utf-8")).decode("ascii")
    request = Request("https://server.example.com/token", http_method="POST",
                      body=("grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code"
                            f"&device_code={DEVICE_CODE}"),
                      headers={"Authorization": f"Basic {basic}",
                               "Content-Type": "application/x-www-form-urlencoded"})
    grant = DeviceCodeGrant(Validator())
    return {
        "entry_point": grant.validate_token_request,
        "call": lambda: grant.validate_token_request(request),
        "validator": grant.request_validator,
        "input": ("POST https://server.example.com/token, Authorization: Basic (client 1406020730 and its "
                  "secret), body grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code"
                  "&device_code=GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS, a device code of which the "
                  "provider holds no record"),
        "settings": [
            "DeviceCodeGrant(request_validator) with no other argument: no custom validators",
            "request validator, a subclass of oauthlib.oauth2.rfc8628.request_validator.RequestValidator: "
            "client_authentication_required keeps the library's default (True)",
            "authenticate_client: accepts the HTTP Basic credentials of the registered client and sets "
            "request.client (the library has no default)",
            "validate_grant_type: True, the client is allowed the device flow (no default)",
            "validate_device_code: None, the provider holds no record of the device code; the "
            "documented answer for an unknown or invalid device code (rfc8628/request_validator.py, "
            "lines 49-50; no default)",
        ],
    }


if __name__ == "__main__":
    sys.exit(trace_input.main(ROW, build))
