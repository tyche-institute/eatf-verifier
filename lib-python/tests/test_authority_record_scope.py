"""Root verifier vs the frozen authority-record corpus.

``artifacts/authority-record-v1/`` ships its own verifier line and 58
vectors. Every RFC 3161 token in that corpus is a certificate-less
placeholder whose imprint matches none of the packages: the frozen line
accepts that "for Java reference compatibility", while this verifier has
required imprint equality and a verified SignerInfo since v0.2.0. These
tests pin that scope, and prove with a one-entry swap that the timestamp
token is the only reason the root verifier rejects the corpus's ``valid/``
packages. See ``docs/authority-record-v1-scope.md``.

They also pin two TSA defects found on the way: a TSTInfo edited after
signing (the signed message-digest no longer matches) and a non-SHA-256
imprint (not determinable, as in lib/src/tsa.ts).
"""

from __future__ import annotations

import base64
import datetime
import importlib.util
import io
import pathlib
import zipfile

import pytest
from asn1crypto import cms, core, tsp

from eatf_verifier import verify

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
AR_VECTORS = REPO_ROOT / "artifacts" / "authority-record-v1" / "test-vectors"
ROOT_VECTORS = REPO_ROOT / "test-vectors"


def _crosscheck():
    path = REPO_ROOT / "scripts" / "authority-record-crosscheck.py"
    spec = importlib.util.spec_from_file_location("authority_record_crosscheck", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _expected_true(vector: pathlib.Path) -> bool:
    return "verify=true" in (vector / "verify-expected.txt").read_text().split()


def _entries(package: bytes) -> list[tuple[zipfile.ZipInfo, bytes]]:
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        return [(info, z.read(info.filename)) for info in z.infolist()]


def _with_timestamp(package: bytes, tsr: bytes) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as target:
        for info, data in _entries(package):
            target.writestr(info, tsr if info.filename == "timestamp.tsr" else data)
    return out.getvalue()


def _entry(package: bytes, name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        return z.read(name)


AR_TRUE = sorted(
    p.parent for p in AR_VECTORS.rglob("package.aep") if _expected_true(p.parent)
)


def test_ar_corpus_shape() -> None:
    assert len(list(AR_VECTORS.rglob("package.aep"))) == 58
    assert len(AR_TRUE) == 32


@pytest.mark.parametrize("vector", AR_TRUE, ids=lambda p: p.relative_to(AR_VECTORS).as_posix())
def test_root_rejects_ar_true_vectors_at_the_timestamp(vector: pathlib.Path) -> None:
    package = (vector / "package.aep").read_bytes()
    facts = _crosscheck().token_facts(vector / "package.aep")
    assert facts["certs"] == 0
    assert facts["imprint"] != facts["hash"]

    result = verify(package)
    assert result.valid is False
    expected = (
        "TSA_IMPRINT_UNVERIFIABLE"
        if facts["imprint_alg"] != "sha256"
        else "TSA_IMPRINT_MISMATCH"
    )
    assert result.failure_code == expected


def test_swapping_only_the_token_makes_mandated_action_verify() -> None:
    package = (AR_VECTORS / "valid" / "mandated-action" / "package.aep").read_bytes()
    digest = _entry(package, "hash.sha256").decode("ascii").strip().lower()
    original = base64.b64decode(_entry(package, "timestamp.tsr").strip())
    token = _crosscheck().restamp_token(original, digest)
    restamped = _with_timestamp(package, base64.b64encode(token) + b"\n")

    for info, data in _entries(restamped):
        if info.filename != "timestamp.tsr":
            assert data == _entry(package, info.filename)

    assert verify(package).failure_code == "TSA_IMPRINT_MISMATCH"
    result = verify(restamped)
    assert result.valid is True, result.failure_reason
    assert any("genTime=2026-01-01T00:00:00" in line for line in result.report)


def _edit_tstinfo(package: bytes, edit) -> bytes:
    resp = tsp.TimeStampResp.load(base64.b64decode(_entry(package, "timestamp.tsr").strip()))
    sd = resp["time_stamp_token"]["content"]
    tst = tsp.TSTInfo.load(sd["encap_content_info"]["content"].parsed.dump())
    edit(tst)
    sd["encap_content_info"]["content"] = core.ParsableOctetString(tst.dump())
    token = cms.ContentInfo({"content_type": "signed_data", "content": sd})
    forged = tsp.TimeStampResp({"status": resp["status"], "time_stamp_token": token})
    return _with_timestamp(package, base64.b64encode(forged.dump()) + b"\n")


def test_tstinfo_edited_after_signing_is_rejected() -> None:
    package = (ROOT_VECTORS / "valid" / "minimal-roundtrip" / "package.aep").read_bytes()
    assert verify(package).valid is True

    def move_gen_time(tst: tsp.TSTInfo) -> None:
        tst["gen_time"] = tst["gen_time"].native + datetime.timedelta(days=365)

    result = verify(_edit_tstinfo(package, move_gen_time))
    assert result.valid is False
    assert result.failure_code == "TSA_SIGNATURE_INVALID"


def test_token_grafted_with_an_edited_imprint_is_rejected() -> None:
    donor = (ROOT_VECTORS / "valid" / "minimal-roundtrip" / "package.aep").read_bytes()
    target = (ROOT_VECTORS / "valid" / "mcp-tools-call-valid" / "package.aep").read_bytes()
    target_hash = bytes.fromhex(_entry(target, "hash.sha256").decode("ascii").strip())

    def set_imprint(tst: tsp.TSTInfo) -> None:
        tst["message_imprint"]["hashed_message"] = target_hash

    grafted = _with_timestamp(target, _entry(_edit_tstinfo(donor, set_imprint), "timestamp.tsr"))
    result = verify(grafted)
    assert result.valid is False
    assert result.failure_code == "TSA_SIGNATURE_INVALID"
