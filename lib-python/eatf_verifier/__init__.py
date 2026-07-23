"""Offline Python verifier for EATF .aep evidence packages.

Public API:

    from eatf_verifier import verify, VerifyResult, VerifyOptions

    with open("action.aep", "rb") as f:
        bytes_ = f.read()

    result = verify(bytes_)
    print(result.valid, result.failure_reason)

This package is a fresh port of the canonical TypeScript reference
in `../lib/`. It is validated against the shared conformance
vectors in `../test-vectors/`; see `../docs/architecture.md` for
the layered structure both implementations follow.
"""

from .tsa_trust_list import DEFAULT_TSA_TRUST_LIST
from .verifier import VerifyOptions, VerifyResult, verify

__all__ = [
    "verify",
    "VerifyOptions",
    "VerifyResult",
    "DEFAULT_TSA_TRUST_LIST",
]
__version__ = "0.2.1"
