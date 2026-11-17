#!/usr/bin/env python3
"""Row 7 of ../../sample.csv: the check
oauth2.rfc6749.endpoints.base.BaseEndpoint._raise_on_bad_method#1,
`raise InvalidRequestError(request=request, description=('Unsupported request
method %s' % request.http_method.upper()))` at lines 79-80 of
oauthlib/oauth2/rfc6749/endpoints/base.py.

Entry point: TokenEndpoint.validate_token_request
(oauthlib/oauth2/rfc6749/endpoints/token.py, line 117), which calls
_raise_on_bad_method at line 118. It is called on the pre-configured
WebApplicationServer, which inherits it from TokenEndpoint.

Input: an access token request sent with GET, its parameters in the query of
the URI.

    ../../../../target-reach/work/venvs/oauthlib/bin/python -I -B 7.py

trace_input.py says what is checked, copied and traced; the record is
7.record.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_input  # noqa: E402

ROW = 7


def build() -> dict:
    from oauthlib.common import Request
    from oauthlib.oauth2 import RequestValidator, WebApplicationServer

    # The library's RequestValidator, unchanged: the call reaches none of its
    # methods (the record's `lines_executed` holds no line of request_validator.py).
    server = WebApplicationServer(RequestValidator())
    request = Request("https://server.example.com/token?grant_type=authorization_code"
                      "&code=SplxlOBeZQQYbYS6WxSbIA", http_method="GET")
    # Read from the class dictionaries only, so that no function of the package runs here.
    holders = [[k.__qualname__, repr(vars(k)["valid_request_methods"])]
               for k in type(server).__mro__ if "valid_request_methods" in vars(k)]
    return {
        "entry_point": server.validate_token_request,
        "call": lambda: server.validate_token_request(request),
        "validator": None,
        "input": ("GET https://server.example.com/token?grant_type=authorization_code"
                  "&code=SplxlOBeZQQYbYS6WxSbIA, no body"),
        "settings": [
            "WebApplicationServer(request_validator) with no other argument; the library's "
            "RequestValidator, unchanged, whose methods the call does not reach",
            "valid_request_methods is not set by the caller: the class attribute ('POST',) of the "
            "library applies",
        ],
        "facts": {
            "method_resolution_order": [k.__qualname__ for k in type(server).__mro__],
            "classes_of_the_mro_that_define_valid_request_methods": holders,
        },
    }


if __name__ == "__main__":
    sys.exit(trace_input.main(ROW, build))
