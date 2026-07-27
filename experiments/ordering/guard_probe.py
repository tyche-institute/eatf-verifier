#!/usr/bin/env python3
"""Guard-level fault sets, measured without modifying either verifier.

The repair-peeling attempt recorded in DESIGN.md could not separate guards that
react to the same bytes. This does, and it does so without touching shipped
code: the guards are evaluated here by calling the same public components the
Python verifier calls — `canonical.jcs`, `hash.sha256`, `rsa.verify_rsa`,
`overt.parse_and_validate_overt_receipt`, `tsa.inspect_tsa` — once each, on the
same package, independently of whether an earlier guard already rejected it.

Each guard returns one of three things, and the third matters:

- `rejects`     the guard would reject this package;
- `accepts`     the guard would let it through;
- `unevaluable` the guard's own inputs are not well defined for this package,
                so no verdict may be attributed to it.

`unevaluable` is not a pass. A guard whose input never materialises is exactly
the situation this experiment exists to describe, and folding it into either
bucket would produce the tidy answer the instrument wants.
"""

from __future__ import annotations

import hashlib
import io
import json
import platform
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GENERATED = HERE / "generated"

sys.path.insert(0, str(REPO_ROOT / "lib-python"))
from eatf_verifier import canonical, hash as hashmod, overt, rsa, tsa  # noqa: E402

REQUIRED = ("response.txt", "metadata.json", "canonical.bin", "hash.sha256",
            "signature.sig", "public_key.pem", "timestamp.tsr")

MAX_ENTRIES = 32
MAX_ENTRY_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024

REJECTS, ACCEPTS, UNEVALUABLE = "rejects", "accepts", "unevaluable"


def g_zip(raw: bytes) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = z.namelist()
            if len(names) != len(set(names)):
                return REJECTS, "duplicate entry name"
            if len(names) > MAX_ENTRIES:
                return REJECTS, f"{len(names)} entries exceeds {MAX_ENTRIES}"
            total = 0
            for info in z.infolist():
                if "/" in info.filename or "\\" in info.filename or "\x00" in info.filename:
                    return REJECTS, f"non-flat name {info.filename!r}"
                if info.file_size > MAX_ENTRY_BYTES:
                    return REJECTS, "entry exceeds the per-entry bound"
                total += info.file_size
            if total > MAX_TOTAL_BYTES:
                return REJECTS, "expanded size exceeds the total bound"
        return ACCEPTS, ""
    except Exception as exc:
        return REJECTS, type(exc).__name__


def entries_of(raw: bytes) -> dict[str, bytes] | None:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            return {n: z.read(n) for n in z.namelist()}
    except Exception:
        return None


def g_required(e: dict[str, bytes] | None) -> tuple[str, str]:
    if e is None:
        return UNEVALUABLE, "archive does not parse"
    missing = [n for n in REQUIRED if n not in e]
    return (REJECTS, f"missing {missing}") if missing else (ACCEPTS, "")


def g_metadata(e: dict[str, bytes] | None) -> tuple[str, str]:
    if e is None or "metadata.json" not in e:
        return UNEVALUABLE, "no metadata.json to parse"
    try:
        v = json.loads(e["metadata.json"])
    except Exception:
        return REJECTS, "metadata.json is not valid JSON"
    return (ACCEPTS, "") if isinstance(v, dict) else (REJECTS, "metadata.json is not an object")


def g_canonical(e: dict[str, bytes] | None) -> tuple[str, str]:
    if e is None or not {"canonical.bin", "response.txt", "metadata.json"} <= set(e):
        return UNEVALUABLE, "canonical form needs response, metadata and canonical bytes"
    try:
        md = json.loads(e["metadata.json"])
        if not isinstance(md, dict):
            return UNEVALUABLE, "metadata is not an object, so no profile form exists"
        profile = e["response.txt"] + b"\n" + canonical.jcs(md)
    except Exception as exc:
        return UNEVALUABLE, f"profile form could not be built: {type(exc).__name__}"
    if e["canonical.bin"] == profile or e["canonical.bin"] == e["response.txt"]:
        return ACCEPTS, ""
    return REJECTS, "canonical.bin matches neither accepted form"


def g_hash(e: dict[str, bytes] | None) -> tuple[str, str]:
    if e is None or not {"canonical.bin", "hash.sha256"} <= set(e):
        return UNEVALUABLE, "no canonical bytes or no recorded digest"
    try:
        recorded = e["hash.sha256"].decode().strip().lower()
    except Exception:
        return REJECTS, "hash.sha256 is not decodable text"
    return (ACCEPTS, "") if recorded == hashmod.to_hex(hashmod.sha256(e["canonical.bin"])) \
        else (REJECTS, "digest does not match canonical.bin")


def g_rsa(e: dict[str, bytes] | None) -> tuple[str, str]:
    import base64
    if e is None or not {"signature.sig", "public_key.pem", "canonical.bin"} <= set(e):
        return UNEVALUABLE, "no signature, key or canonical bytes"
    try:
        key = rsa.load_public_key_pem(e["public_key.pem"])
        sig = base64.b64decode(e["signature.sig"], validate=False)
    except Exception as exc:
        return REJECTS, f"signature or key will not load: {type(exc).__name__}"
    try:
        return (ACCEPTS, "") if rsa.verify_rsa(key, sig, e["canonical.bin"]) \
            else (REJECTS, "RSA signature does not verify")
    except Exception as exc:
        return REJECTS, type(exc).__name__


def g_overt(e: dict[str, bytes] | None) -> tuple[str, str]:
    if e is None or "overt_receipt.json" not in e:
        return UNEVALUABLE, "no receipt present"
    if "hash.sha256" not in e or "metadata.json" not in e:
        return UNEVALUABLE, "receipt cross-check needs metadata and the digest"
    try:
        md = json.loads(e["metadata.json"])
        if not isinstance(md, dict):
            return UNEVALUABLE, "metadata is not an object"
        digest = e["hash.sha256"].decode().strip().lower()
    except Exception:
        return UNEVALUABLE, "metadata or digest not readable"
    try:
        _, err = overt.parse_and_validate_overt_receipt(e, md, digest)
    except Exception as exc:
        return REJECTS, type(exc).__name__
    return (REJECTS, err) if err else (ACCEPTS, "")


def g_receipt_signature(e: dict[str, bytes] | None) -> tuple[str, str]:
    """The guard the verifier applies after the receipt cross-check: when signed
    metadata marks a receipt signature, both files must be present and the
    signature must verify over the exact receipt bytes."""
    import base64
    if e is None or "metadata.json" not in e:
        return UNEVALUABLE, "no metadata to read the marker from"
    try:
        md = json.loads(e["metadata.json"])
        if not isinstance(md, dict):
            return UNEVALUABLE, "metadata is not an object"
    except Exception:
        return UNEVALUABLE, "metadata does not parse"
    marker = md.get("overt_receipt_signature")
    if marker is None:
        return (REJECTS, "unmarked overt_receipt.sig is not accepted") \
            if "overt_receipt.sig" in e else (ACCEPTS, "no receipt signature required")
    if marker != "overt_receipt.sig":
        return REJECTS, "metadata marker names the wrong entry"
    receipt, sig = e.get("overt_receipt.json"), e.get("overt_receipt.sig")
    if not receipt or not sig:
        return REJECTS, "signed metadata requires both the receipt and its signature"
    if "public_key.pem" not in e:
        return UNEVALUABLE, "no key to verify the receipt signature against"
    try:
        key = rsa.load_public_key_pem(e["public_key.pem"])
        raw = base64.b64decode(sig.decode("ascii").strip(), validate=False)
    except Exception as exc:
        return REJECTS, f"receipt signature will not load: {type(exc).__name__}"
    try:
        return (ACCEPTS, "") if rsa.verify_rsa(key, raw, receipt) \
            else (REJECTS, "receipt signature does not verify")
    except Exception as exc:
        return REJECTS, type(exc).__name__


def g_pqc(e: dict[str, bytes] | None) -> tuple[str, str]:
    if e is None:
        return UNEVALUABLE, "archive does not parse"
    present = [n for n in ("signature_pqc.sig", "pqc_public_key.pem") if n in e]
    if not present:
        return ACCEPTS, "optional pair absent"
    return (ACCEPTS, "") if len(present) == 2 else (REJECTS, f"half pair: {present}")


def g_tsa(e: dict[str, bytes] | None) -> tuple[str, str]:
    if e is None or "timestamp.tsr" not in e or "hash.sha256" not in e:
        return UNEVALUABLE, "no timestamp or no digest to compare against"
    raw = e["timestamp.tsr"]
    if not raw.strip():
        return REJECTS, "timestamp.tsr is empty"
    try:
        digest = e["hash.sha256"].decode().strip().lower()
        check = tsa.inspect_tsa(raw.decode(), digest)
    except Exception as exc:
        return REJECTS, type(exc).__name__
    if not check.tsa_present:
        return REJECTS, "no timestamp token present"
    if check.message_imprint_matches is False:
        return REJECTS, "message imprint does not match hash.sha256"
    if check.embedded_cert_count == 0:
        return REJECTS, "no embedded signing certificate"
    if check.signature_verified is False:
        return REJECTS, "CMS SignerInfo signature does not verify"
    if check.message_imprint_matches is None:
        return UNEVALUABLE, "imprint could not be determined"
    return ACCEPTS, ""


GUARDS = [
    ("1-zip", lambda raw, e: g_zip(raw)),
    ("2-required-entries", lambda raw, e: g_required(e)),
    ("3-metadata-object", lambda raw, e: g_metadata(e)),
    ("4-canonical-form", lambda raw, e: g_canonical(e)),
    ("5-digest", lambda raw, e: g_hash(e)),
    ("7-rsa", lambda raw, e: g_rsa(e)),
    ("8a-overt-crosscheck", lambda raw, e: g_overt(e)),
    ("8b-receipt-signature", lambda raw, e: g_receipt_signature(e)),
    ("9-pqc-pair", lambda raw, e: g_pqc(e)),
    ("10-12-timestamp", lambda raw, e: g_tsa(e)),
]


def corpus() -> list[tuple[str, bytes, str]]:
    out = []
    for source, root in (
        ("decision-path", REPO_ROOT / "experiments/decision-path/generated/corpus"),
        ("path-shadowing", REPO_ROOT / "experiments/path-shadowing/generated"),
    ):
        if root.exists():
            for d in sorted(root.iterdir()):
                p = d / "package.aep"
                if p.is_file():
                    out.append((d.name, p.read_bytes(), source))
    return out


def main() -> int:
    cases = corpus()
    if not cases:
        print("no corpus; run the other experiments first", file=sys.stderr)
        return 1

    rows = []
    for cid, raw, source in cases:
        e = entries_of(raw)
        verdicts = {}
        for name, fn in GUARDS:
            state, why = fn(raw, e)
            verdicts[name] = {"state": state, "detail": why}
        rejecting = [n for n, v in verdicts.items() if v["state"] == REJECTS]
        unevaluable = [n for n, v in verdicts.items() if v["state"] == UNEVALUABLE]
        rows.append({
            "id": cid, "source": source,
            "rejecting_guards": rejecting,
            "fault_set_size": len(rejecting),
            "unevaluable_guards": unevaluable,
            "order_sensitive": len(rejecting) > 1,
            "guards": verdicts,
        })

    # Sentinel: the accepting controls are valid packages. If any guard claims
    # to reject one, the probe is wrong and no number from this run may be
    # used. This is the check that caught a mis-called key loader on the first
    # attempt, when every case came back with a rejecting RSA guard.
    sentinels = [r for r in rows if r["id"].startswith("accept")]
    broken = [r for r in sentinels if r["fault_set_size"] > 0]
    if broken:
        for r in broken:
            for g in r["rejecting_guards"]:
                print(f"SENTINEL FAILED: {r['id']} rejected by {g}: "
                      f"{r['guards'][g]['detail']}", file=sys.stderr)
        print("The probe disagrees with the shipped verifier on a valid package. "
              "No fault-set figure from this run is usable.", file=sys.stderr)
        return 2

    # Second sentinel: completeness. Every package the shipped verifier rejects
    # must be rejected by at least one guard here, and every package it accepts
    # by none. A probe that under-detects would report fault sets that are
    # lower bounds while looking like measurements.
    from eatf_verifier import verify as _shipped  # noqa: PLC0415
    disagreements = []
    for r, (_, raw, _src) in zip(rows, cases):
        shipped_valid = bool(_shipped(raw).valid)
        probe_rejects = r["fault_set_size"] > 0
        if shipped_valid == probe_rejects:
            disagreements.append((r["id"], shipped_valid, r["rejecting_guards"]))
    if disagreements:
        for cid, valid, guards in disagreements:
            print(f"COMPLETENESS FAILED: {cid} shipped valid={valid} but probe guards={guards}",
                  file=sys.stderr)
        print("The probe does not agree with the shipped verifier on which packages are "
              "rejected. Fault sets from this run are lower bounds, not measurements.",
              file=sys.stderr)
        return 2

    multi = [r for r in rows if r["order_sensitive"]]
    zero = [r for r in rows if r["fault_set_size"] == 0]
    summary = {
        "cases": len(rows),
        "guards_evaluated_per_case": len(GUARDS),
        "sentinel_accepting_controls": f"{len(sentinels)} checked, all with an empty fault set",
        "sentinel_completeness": ("every package the shipped verifier rejects has at least one "
                                  "rejecting guard here, and every one it accepts has none"),
        "cases_with_no_rejecting_guard": len(zero),
        "cases_with_exactly_one_rejecting_guard": sum(1 for r in rows if r["fault_set_size"] == 1),
        "cases_with_more_than_one_rejecting_guard": len(multi),
        "order_sensitive_ids": [r["id"] for r in multi],
        "max_fault_set_size": max((r["fault_set_size"] for r in rows), default=0),
        "note": ("A case with one rejecting guard receives the same first-failure code under "
                 "every ordering of the guards; that is analytic. A case with more than one "
                 "rejecting guard receives a code that depends on which of them the "
                 "implementation reaches first, so for those cases the standard's permission "
                 "to reorder does not preserve the code. Guards whose own inputs are not well "
                 "defined for a package are reported as unevaluable and are counted in "
                 "neither direction."),
    }

    GENERATED.mkdir(exist_ok=True)
    (GENERATED / "guard-faultsets.json").write_text(json.dumps({
        "schema": "urn:eatf:experiment:guard-faultsets:1",
        "environment": {"python": platform.python_version()},
        "method": "guards evaluated independently via the shipped public components; "
                  "no verifier source modified",
        "summary": summary, "rows": rows,
    }, indent=2) + "\n", encoding="utf-8")

    lines = ["case,source,fault_set_size,order_sensitive,rejecting_guards,unevaluable_guards"]
    for r in rows:
        lines.append(f"{r['id']},{r['source']},{r['fault_set_size']},"
                     f"{str(r['order_sensitive']).lower()},"
                     f"{'|'.join(r['rejecting_guards'])},{'|'.join(r['unevaluable_guards'])}")
    (GENERATED / "guard-faultsets.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    digest = hashlib.sha256((GENERATED / "guard-faultsets.csv").read_bytes()).hexdigest()

    print("# Guard-level fault sets")
    for k, v in summary.items():
        if k != "note":
            print(f"- {k}: {v}")
    for r in rows:
        if r["order_sensitive"] or r["fault_set_size"] == 0:
            print(f"  {r['id']:34s} n={r['fault_set_size']}  {' + '.join(r['rejecting_guards'])}")
    print(f"- guard-faultsets.csv digest: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
