"""Conformance tests — Python verifier vs the bundled test vectors.

The same vectors drive the TypeScript verifier's conformance test
(see cli/eatf-verify/test/conformance.test.mjs). Both ports must
agree on every vector; if a vector flips, the spec or a verifier
is wrong, not the test.
"""

from __future__ import annotations

import pathlib

import pytest

from eatf_verifier import VerifyOptions, verify

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VECTORS_ROOT = REPO_ROOT / "test-vectors"


def _walk(category: str) -> list[pathlib.Path]:
    root = VECTORS_ROOT / category
    return sorted(p for p in root.rglob("package.aep"))


VALID_VECTORS = _walk("valid")
INVALID_VECTORS = _walk("invalid")


@pytest.mark.parametrize("path", VALID_VECTORS, ids=lambda p: p.parent.name)
def test_valid_vector_verifies(path: pathlib.Path) -> None:
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is True, (
        f"{path.parent.name} should verify but failed: {result.failure_reason}"
    )


@pytest.mark.parametrize("path", INVALID_VECTORS, ids=lambda p: p.parent.name)
def test_invalid_vector_rejected(path: pathlib.Path) -> None:
    result = verify(path.read_bytes(), VerifyOptions())
    assert result.valid is False, (
        f"{path.parent.name} should be rejected but verified clean"
    )
    assert result.failure_reason, "rejected vector must include a failure_reason"
