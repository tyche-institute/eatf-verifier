"""ML-DSA-65 key encoding, mirrored from lib/test/mldsa-key-encoding.test.ts.

Row 3 of docs/hybrid-test-matrix.md: the object identifier, absent parameters
and the key length of an RFC 9881 ML-DSA-65 SubjectPublicKeyInfo. Both
verifiers must agree on every row.
"""

from __future__ import annotations

import base64
import io
import pathlib
import textwrap
import zipfile

import pytest

from eatf_verifier import VerifyOptions, verify
from eatf_verifier.mldsa import mldsa65_public_key_from_pem

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
HYBRID = (
    REPO_ROOT / "workshops" / "pqc-hybrid-lab" / "packages" / "01-valid-hybrid.aep"
).read_bytes()
COMMITTED = (REPO_ROOT / "test-vectors" / "keys" / "dev-mldsa65.pem").read_bytes()
KEY = mldsa65_public_key_from_pem(COMMITTED)


def _spki(key: bytes, oid_last: int = 0x12, null_parameters: bool = False) -> bytes:
    """DER SubjectPublicKeyInfo for an ML-DSA key. Every length matches its content."""
    algorithm = bytes.fromhex("06096086480165030403") + bytes([oid_last])
    if null_parameters:
        algorithm += b"\x05\x00"
    bit_string = b"\x03\x82" + (len(key) + 1).to_bytes(2, "big") + b"\x00" + key
    body = b"\x30" + bytes([len(algorithm)]) + algorithm + bit_string
    return b"\x30\x82" + len(body).to_bytes(2, "big") + body


def _pem(der: bytes) -> bytes:
    body = base64.b64encode(der).decode("ascii")
    return (
        "-----BEGIN PUBLIC KEY-----\n"
        + "\n".join(textwrap.wrap(body, 64))
        + "\n-----END PUBLIC KEY-----\n"
    ).encode("ascii")


def _with_entry(package: bytes, name: str, data: bytes) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package)) as zin, zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            zout.writestr(info, data if info.filename == name else zin.read(info))
    return out.getvalue()


ROWS = [
    ("id-ml-dsa-65, absent parameters, 1952-byte key", lambda k: _spki(k), True),
    ("the id-ml-dsa-44 object identifier", lambda k: _spki(k, oid_last=0x11), False),
    ("the id-ml-dsa-87 object identifier", lambda k: _spki(k, oid_last=0x13), False),
    ("explicit NULL parameters", lambda k: _spki(k, null_parameters=True), False),
    ("a key one byte short", lambda k: _spki(k[:-1]), False),
    ("a key one byte long", lambda k: _spki(k + b"\x00"), False),
]
IDS = [row[0] for row in ROWS]


def test_builder_reproduces_the_committed_rfc9881_key() -> None:
    body = "".join(
        line for line in COMMITTED.decode("ascii").splitlines() if not line.startswith("-----")
    )
    der = base64.b64decode(body)
    assert len(der) == 1974
    assert _spki(KEY) == der


@pytest.mark.parametrize(("label", "make", "accepted"), ROWS, ids=IDS)
def test_parser_matches_typescript(label: str, make, accepted: bool) -> None:
    text = _pem(make(KEY))
    if accepted:
        assert mldsa65_public_key_from_pem(text) == KEY
    else:
        with pytest.raises(ValueError):
            mldsa65_public_key_from_pem(text)


@pytest.mark.parametrize(("label", "make", "accepted"), ROWS, ids=IDS)
def test_packaged_key_matches_typescript(label: str, make, accepted: bool) -> None:
    result = verify(
        _with_entry(HYBRID, "pqc_public_key.pem", _pem(make(KEY))),
        VerifyOptions(pqc_policy="required"),
    )
    expected = (True, None, True) if accepted else (False, "PQC_VERIFY_ERROR", False)
    assert (result.valid, result.failure_code, result.pqc_valid) == expected
