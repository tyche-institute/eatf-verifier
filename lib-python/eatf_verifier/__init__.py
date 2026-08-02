"""Offline Python verifier for EATF .aep evidence packages.

Public API:

    from eatf_verifier import verify, VerifyResult, VerifyOptions

    with open("action.aep", "rb") as f:
        bytes_ = f.read()

    result = verify(bytes_)
    print(result.valid, result.failure_reason)

This cross-language implementation is validated against the same
shared conformance vectors as the TypeScript library.
"""

from .tsa_trust_list import DEFAULT_TSA_TRUST_LIST
from .verifier import VerifyOptions, VerifyResult, verify

__all__ = [
    "DEFAULT_TSA_TRUST_LIST",
    "VerifyOptions",
    "VerifyResult",
    "verify",
]
__version__ = "0.6.1"
