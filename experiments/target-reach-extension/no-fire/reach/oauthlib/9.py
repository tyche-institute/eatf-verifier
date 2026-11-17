#!/usr/bin/env python3
"""Row 9 of ../../sample.csv: the check
oauth2.rfc8628.grant_types.device_code.DeviceCodeGrant.validate_token_request#1,
`raise rfc6749_errors.InvalidRequestError("Request is missing grant type.",
request=request)` at lines 125-127 of
oauthlib/oauth2/rfc8628/grant_types/device_code.py.

Entry point: DeviceCodeGrant.validate_token_request (device_code.py, line
116), whose first test of the request is the one at line 124.

Input: a device access token request (RFC 8628, section 3.4) sent with POST
whose body carries the device code and the client identifier but no
`grant_type`.

    ../../../../target-reach/work/venvs/oauthlib/bin/python -I -B 9.py

trace_input.py says what is checked, copied and traced; the record is
9.record.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_input  # noqa: E402

ROW = 9
# The device code of the example response in the docstring of
# oauthlib/oauth2/rfc8628/endpoints/device_authorization.py (line 173), and the
# client identifier of examples/device_code_flow.py (line 76) of the clone.
DEVICE_CODE = "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS"
CLIENT_ID = "1406020730"


def build() -> dict:
    from oauthlib.common import Request
    from oauthlib.oauth2 import DeviceCodeGrant
    from oauthlib.oauth2.rfc8628.request_validator import RequestValidator

    # The library's request validator of the device flow, unchanged: the call
    # reaches none of its methods (the record's `lines_executed` holds no line
    # of a request_validator.py).
    grant = DeviceCodeGrant(RequestValidator())
    request = Request("https://server.example.com/token", http_method="POST",
                      body=f"device_code={DEVICE_CODE}&client_id={CLIENT_ID}",
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    return {
        "entry_point": grant.validate_token_request,
        "call": lambda: grant.validate_token_request(request),
        "validator": None,
        "input": ("POST https://server.example.com/token, body "
                  "device_code=GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS&client_id=1406020730, "
                  "no grant_type"),
        "settings": [
            "DeviceCodeGrant(request_validator) with no other argument: no custom validators",
            "request validator: the library's oauthlib.oauth2.rfc8628.request_validator.RequestValidator, "
            "unchanged (the grant's default would be the RequestValidator of rfc6749); the call reaches "
            "none of its methods",
        ],
    }


if __name__ == "__main__":
    sys.exit(trace_input.main(ROW, build))
