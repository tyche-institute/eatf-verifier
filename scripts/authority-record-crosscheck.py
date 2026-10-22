#!/usr/bin/env python3
"""Run the authority-record corpus through the root and the frozen verifier lines.

The frozen study artifact in ``artifacts/authority-record-v1/`` carries its own
TypeScript and Python verifiers (Python 0.2.1) and a 58-vector corpus. The root
toolkit (``lib/``, ``lib-python/``) implements a stricter RFC 3161 contract and
none of the authority-record extension. This script records, per vector, what
each of the four implementations decides, so that every disagreement can be
named rather than discovered.

Both Python ports install the same ``eatf_verifier`` package name, so each one
runs in its own subprocess with ``PYTHONPATH`` pointing at its source tree.
The TypeScript lines are imported from their built ``dist/`` directories; build
them first:

    (cd lib && npm ci && npm run build)
    (cd artifacts/authority-record-v1/lib && npm ci && npm run build)
    python scripts/authority-record-crosscheck.py   # Markdown table, exit 1 on "?"

The script runs the corpus twice. The second, control run copies every
vector to a temporary directory and replaces only
``timestamp.tsr`` with a TEST-ONLY token from ``test-vectors/keys/
dev-tsa-rsa-3072`` whose imprint is the package's ``hash.sha256`` and whose
genTime, serial number and policy are copied from the original token. Every
other ZIP entry stays byte-identical, so any verdict that changes between the
two runs is caused by the timestamp token alone.

The four implementations share one author and one corpus. Agreement between
them is a consistency check, not independent validation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "authority-record-v1"
VECTORS = ARTIFACT / "test-vectors"
TSA_KEY = ROOT / "test-vectors" / "keys" / "dev-tsa-rsa-3072.key"
TSA_CERT = ROOT / "test-vectors" / "keys" / "dev-tsa-rsa-3072.pem"

LINES = [
    ("root-py", "python", ROOT / "lib-python"),
    ("root-ts", "node", ROOT / "lib" / "dist" / "index.js"),
    ("ar-py", "python", ARTIFACT / "lib-python"),
    ("ar-ts", "node", ARTIFACT / "lib" / "dist" / "index.js"),
]

PY_DRIVER = r"""
import json, sys
import eatf_verifier
from eatf_verifier import verify
for path in sys.argv[1:]:
    r = verify(open(path, "rb").read())
    tsa = [l for l in r.report if l.startswith("RFC 3161 timestamp present")]
    print(json.dumps({
        "path": path,
        "version": eatf_verifier.__version__,
        "module": eatf_verifier.__file__,
        "valid": r.valid,
        "code": getattr(r, "failure_code", None),
        "reason": r.failure_reason,
        "tsa": tsa[0] if tsa else None,
    }))
"""

TS_DRIVER = r"""
import { readFileSync } from "node:fs";
const [dist, ...paths] = process.argv.slice(1);
const { verify } = await import(dist);
for (const path of paths) {
  const r = await verify(new Uint8Array(readFileSync(path)));
  const tsa = (r.report ?? []).find((l) => l.startsWith("RFC 3161 timestamp present"));
  console.log(JSON.stringify({
    path, valid: r.valid, code: r.failureCode ?? null,
    reason: r.failureReason ?? null, tsa: tsa ?? null,
  }));
}
"""


def run_line(kind: str, target: Path, paths: list[str]) -> dict[str, dict]:
    if kind == "python":
        env = dict(os.environ, PYTHONPATH=str(target))
        cmd = [sys.executable, "-c", PY_DRIVER, *paths]
    else:
        if not target.exists():
            raise SystemExit(f"{target} is missing; build that TypeScript library first")
        env = dict(os.environ)
        cmd = ["node", "--input-type=module", "-e", TS_DRIVER, target.as_uri(), *paths]
    out = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True).stdout
    rows = [json.loads(line) for line in out.splitlines() if line.strip()]
    if kind == "python":
        module = Path(rows[0]["module"]).resolve()
        if target.resolve() not in module.parents:
            raise SystemExit(f"{target} line resolved to {module}; another install shadows it")
    return {row["path"]: row for row in rows}


def expected(vector_dir: Path) -> bool:
    text = (vector_dir / "verify-expected.txt").read_text(encoding="ascii")
    return "verify=true" in text.split()


def _parse_token(raw: bytes):
    """Return (SignedData, TSTInfo) for a TimeStampResp or bare token, or None."""
    from asn1crypto import cms, tsp

    token = raw
    try:
        resp = tsp.TimeStampResp.load(raw)
        if resp["time_stamp_token"]:
            token = resp["time_stamp_token"].dump()
    except ValueError:
        pass  # not a TimeStampResp: try the bare-token shape below
    try:
        sd = cms.ContentInfo.load(token)["content"]
        return sd, sd["encap_content_info"]["content"].parsed
    except (ValueError, TypeError, KeyError):
        return None


def token_facts(package: Path) -> dict:
    """Read the RFC 3161 token independently of every verifier line."""
    with zipfile.ZipFile(package) as z:
        names = set(z.namelist())
        hash_hex = z.read("hash.sha256").decode("ascii").strip().lower()
        raw = base64.b64decode(z.read("timestamp.tsr").strip())
        canonical = z.read("canonical.bin") if "canonical.bin" in names else None
    facts = {
        "hash": hash_hex,
        "canonical_sha256": hashlib.sha256(canonical).hexdigest() if canonical else None,
        "imprint": None,
        "imprint_alg": None,
        "certs": None,
    }
    parsed = _parse_token(raw)
    if parsed is not None:
        sd, tst = parsed
        mi = tst["message_imprint"]
        facts["imprint"] = mi["hashed_message"].native.hex()
        facts["imprint_alg"] = mi["hash_algorithm"]["algorithm"].native
        facts["certs"] = len(sd["certificates"]) if sd["certificates"] else 0
    return facts


def restamp_token(original_raw: bytes, digest_hex: str) -> bytes:
    """Re-issue a TEST-ONLY token over ``digest_hex``, copying genTime, serial
    and policy from the original token so time-dependent appraisals keep their
    inputs. Returns the bare CMS ContentInfo, the shape the corpus ships."""
    from asn1crypto import algos, cms, core, tsp, x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    # Dotted OID: asn1crypto's name map for content types is built before
    # tsp registers "tst_info", so the name does not resolve when encoding.
    id_ct_tstinfo = "1.2.840.113549.1.9.16.1.4"
    parsed = _parse_token(original_raw)
    if parsed is None:
        raise ValueError("original timestamp.tsr is not an RFC 3161 token")
    old = parsed[1]
    tst = tsp.TSTInfo({
        "version": "v1",
        "policy": old["policy"].dotted,
        "message_imprint": {
            "hash_algorithm": {"algorithm": "sha256"},
            "hashed_message": bytes.fromhex(digest_hex),
        },
        "serial_number": old["serial_number"].native,
        "gen_time": old["gen_time"].native,
    })
    tst_der = tst.dump()
    cert_der = x509.Certificate.load(
        _pem_body(TSA_CERT.read_bytes(), b"CERTIFICATE")
    )
    signed_attrs = cms.CMSAttributes([
        cms.CMSAttribute({"type": "content_type", "values": [id_ct_tstinfo]}),
        cms.CMSAttribute({
            "type": "message_digest",
            "values": [hashlib.sha256(tst_der).digest()],
        }),
    ])
    key = serialization.load_pem_private_key(TSA_KEY.read_bytes(), password=None)
    signature = key.sign(signed_attrs.dump(), padding.PKCS1v15(), hashes.SHA256())
    signed = cms.ContentInfo({
        "content_type": "signed_data",
        "content": cms.SignedData({
            "version": "v3",
            "digest_algorithms": [algos.DigestAlgorithm({"algorithm": "sha256"})],
            "encap_content_info": {
                "content_type": id_ct_tstinfo,
                "content": core.ParsableOctetString(tst_der),
            },
            "certificates": [cert_der],
            "signer_infos": [cms.SignerInfo({
                "version": "v1",
                "sid": cms.SignerIdentifier({
                    "issuer_and_serial_number": {
                        "issuer": cert_der.issuer,
                        "serial_number": cert_der.serial_number,
                    }
                }),
                "digest_algorithm": {"algorithm": "sha256"},
                "signed_attrs": signed_attrs,
                "signature_algorithm": {"algorithm": "sha256_rsa"},
                "signature": signature,
            })],
        }),
    })
    return signed.dump()


def _pem_body(pem: bytes, label: bytes) -> bytes:
    begin, end = b"-----BEGIN " + label + b"-----", b"-----END " + label + b"-----"
    body = pem.split(begin, 1)[1].split(end, 1)[0]
    return base64.b64decode(b"".join(body.split()))


def restamp_corpus(destination: Path) -> None:
    shutil.copytree(VECTORS, destination)
    for package in sorted(destination.rglob("package.aep")):
        with zipfile.ZipFile(package) as source:
            members = [(info, source.read(info.filename)) for info in source.infolist()]
        entries = {info.filename: data for info, data in members}
        original = base64.b64decode(entries["timestamp.tsr"].strip())
        if _parse_token(original) is None:
            continue  # invalid/bad-timestamp: nothing to re-issue
        digest = entries["hash.sha256"].decode("ascii").strip().lower()
        new_entry = base64.b64encode(restamp_token(original, digest)) + b"\n"
        tmp = package.with_suffix(".aep.tmp")
        with zipfile.ZipFile(tmp, "w") as target:
            for info, data in members:
                target.writestr(info, new_entry if info.filename == "timestamp.tsr" else data)
        os.replace(tmp, package)


def verdict(row: dict) -> str:
    if row["valid"]:
        return "true"
    return f"false `{row['code']}`" if row.get("code") else "false"


TSA_CODES = {"TSA_IMPRINT_MISMATCH", "TSA_IMPRINT_UNVERIFIABLE"}
PROFILE_PREFIXES = ("mandate.json invalid", "warrant.json invalid", "acceptance invalid")
AR_TS_SIGNERINFO = "RFC 3161 SignerInfo signature did not verify against the embedded cert."


def classify(shipped: dict, control: dict) -> list[str]:
    """Name every disagreement in one vector, or return ["?"].

    T  shipped token binds nothing: root rejects at the timestamp, the
       frozen line accepts (imprint advisory, SignerInfo not determinate).
    S  root does not implement the §4.2/§4.3/§4.5 authority-record checks:
       visible once the token is valid, root accepts what they reject.
    D  frozen TypeScript line cannot verify a cert-bearing token's
       SignerInfo (it passes the TSTInfo, not the timestamped data, to PKIjs).
    E  no disagreement: all four reject on the same envelope check.
    """
    classes = []
    pair = ("root-py", "root-ts")
    root = [shipped[n] for n in pair] + [control[n] for n in pair]
    if any(r["valid"] != root[0]["valid"] or r["code"] != root[0]["code"] for r in root[:2]):
        return ["?"]
    if any(r["valid"] != root[2]["valid"] or r["code"] != root[2]["code"] for r in root[2:]):
        return ["?"]
    if shipped["ar-py"]["valid"] != shipped["ar-ts"]["valid"]:
        return ["?"]

    if shipped["root-py"]["valid"] != shipped["ar-py"]["valid"]:
        if not (
            shipped["ar-py"]["valid"]
            and shipped["root-py"]["code"] in TSA_CODES
            and shipped["tsa_certs"] == 0
            and not shipped["imprint_equals_hash"]
        ):
            return ["?"]
        classes.append("T")
    if control["root-py"]["valid"] != control["ar-py"]["valid"]:
        if not (
            control["root-py"]["valid"]
            and (control["ar-py"]["reason"] or "").startswith(PROFILE_PREFIXES)
            and control["ar-py"]["reason"] == shipped["ar-py"]["reason"]
        ):
            return ["?"]
        classes.append("S")
    if control["ar-py"]["valid"] != control["ar-ts"]["valid"]:
        if not (control["ar-py"]["valid"] and control["ar-ts"]["reason"] == AR_TS_SIGNERINFO):
            return ["?"]
        classes.append("D")
    if not classes:
        same = all(not shipped[n]["valid"] for n, _, _ in LINES) and (
            shipped["root-py"]["code"] not in TSA_CODES
        )
        classes.append("E" if same else "?")
    return classes


def run_corpus(restamp: bool) -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="eatf-ar-crosscheck-") as temp:
        corpus = VECTORS
        if restamp:
            corpus = Path(temp) / "test-vectors"
            restamp_corpus(corpus)
        vector_dirs = sorted(p.parent for p in corpus.rglob("package.aep"))
        paths = [str(d / "package.aep") for d in vector_dirs]
        results = {name: run_line(kind, target, paths) for name, kind, target in LINES}
        rows = []
        for d, path in zip(vector_dirs, paths, strict=True):
            facts = token_facts(Path(path))
            row = {
                "vector": d.relative_to(corpus).as_posix(),
                "expected": expected(d),
                "imprint_equals_hash": facts["imprint"] == facts["hash"],
                "tsa_certs": facts["certs"],
            }
            for name, _, _ in LINES:
                row[name] = {k: v for k, v in results[name][path].items() if k != "module"}
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", type=Path, help="also write the raw rows to this file")
    args = parser.parse_args()

    shipped = run_corpus(restamp=False)
    control = run_corpus(restamp=True)
    if [r["vector"] for r in shipped] != [r["vector"] for r in control]:
        raise SystemExit("re-stamped corpus does not list the same vectors")

    names = [name for name, _, _ in LINES]
    print(
        "| Vector | Expected | Token binds package | "
        + " | ".join(names)
        + " | "
        + " | ".join(f"{n} (control)" for n in names)
        + " | Class |"
    )
    print("|---|---|---|" + "---|" * (2 * len(names)) + "---|")
    out, unexplained = [], 0
    for s_row, c_row in zip(shipped, control, strict=True):
        classes = classify(s_row, c_row)
        unexplained += "?" in classes
        out.append(
            {"vector": s_row["vector"], "classes": classes, "shipped": s_row, "control": c_row}
        )
        print(
            f"| `{s_row['vector']}` | {str(s_row['expected']).lower()} | "
            f"{'yes' if s_row['imprint_equals_hash'] else 'no'} | "
            + " | ".join(verdict(s_row[n]) for n in names)
            + " | "
            + " | ".join(verdict(c_row[n]) for n in names)
            + f" | {', '.join(classes)} |"
        )
    print()
    for label, rows in (("shipped", shipped), ("re-stamped", control)):
        counts = ", ".join(
            f"{n} {sum(r[n]['valid'] == r['expected'] for r in rows)}/{len(rows)}" for n in names
        )
        print(f"Verdicts equal to verify-expected.txt ({label}): {counts}.")
    tally = {}
    for row in out:
        for c in row["classes"]:
            tally[c] = tally.get(c, 0) + 1
    print("Classes: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())) + ".")
    print(f"Unexplained disagreements: {unexplained}.")
    if args.json:
        args.json.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 1 if unexplained else 0


if __name__ == "__main__":
    raise SystemExit(main())
