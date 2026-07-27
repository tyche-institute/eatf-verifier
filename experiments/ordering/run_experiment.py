#!/usr/bin/env python3
"""Fault-set measurement by repair peeling, per experiments/ordering/DESIGN.md.

For each case, run the verifier, restore from the valid seed exactly the entries
the returned failure code concerns, and run again — repeating until the package
is accepted or no repair is defined. The sequence of codes observed is the
case's fault set in pipeline order.

A case whose sequence has length 1 violates exactly one guard, so every legal
ordering assigns it the same first-failure code: it is order-invariant, and
that is analytic rather than measured. A case whose sequence is longer violates
several guards, so which code it receives depends on which of them runs first.

The shipped verifiers are not modified. Predictions were fixed in DESIGN.md
before this file existed.
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

# Which archive entries a failure code concerns. Restoring exactly these from
# the valid seed is the minimal repair for that code. Codes absent from this
# table are declared unrepairable and terminate the peel; that is a statement
# about the repair vocabulary, not about the package, and is reported as such.
# A repair may legitimately touch several entries when they form one signed
# unit; what it may not do is touch anything outside the set declared here,
# which the runner asserts after every step.
CODE_ENTRIES: dict[str, tuple[str, ...]] = {
    "REQUIRED_ENTRY_MISSING": ("canonical.bin", "hash.sha256", "metadata.json",
                               "public_key.pem", "response.txt", "signature.sig",
                               "timestamp.tsr"),
    "METADATA_INVALID_JSON": ("metadata.json",),
    "METADATA_NOT_OBJECT": ("metadata.json",),
    "CANONICAL_FORM_MISMATCH": ("canonical.bin",),
    "HASH_MISMATCH": ("hash.sha256",),
    "RSA_SIGNATURE_INVALID": ("signature.sig",),
    # The receipt and its signature are a signed pair and must be restored
    # together; restoring either alone leaves the pair inconsistent.
    #
    # OVERT_INVALID is deliberately NOT given a repair that reaches the entries
    # the receipt names as witnesses. Doing so was tried and rejected: it also
    # clears whatever fault those entries carry, so the peel reports one fault
    # where there are two, and the measurement silently becomes the answer the
    # harness wanted. See the limitation recorded in DESIGN.md.
    "OVERT_INVALID": ("overt_receipt.json", "overt_receipt.sig"),
    "OVERT_SIGNATURE_REQUIRED": ("overt_receipt.json", "overt_receipt.sig"),
    "OVERT_SIGNATURE_INVALID": ("overt_receipt.json", "overt_receipt.sig"),
    "TSA_MISSING_OR_INVALID": ("timestamp.tsr",),
    "TSA_IMPRINT_MISMATCH": ("timestamp.tsr",),
    "TSA_CERT_MISSING": ("timestamp.tsr",),
    "TSA_SIGNATURE_INVALID": ("timestamp.tsr",),
}
# Removal rather than restoration: the optional pair must go away entirely.
CODE_REMOVE: dict[str, tuple[str, ...]] = {
    "PQC_PAIR_INCOMPLETE": ("signature_pqc.sig", "pqc_public_key.pem"),
}
# Codes for which no byte-level repair is defined.
UNREPAIRABLE = {
    "ZIP_INVALID_OR_UNSAFE": "the archive itself does not parse, so no entry can be restored",
    "SIGNER_NOT_TRUSTED": "decided by a caller-supplied trust set, not by package bytes",
}

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def entries_of(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {n: z.read(n) for n in z.namelist()}


def rebuild(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
            info.external_attr = 0o600 << 16
            z.writestr(info, entries[name])
    return buf.getvalue()


def repair(data: bytes, code: str, seed: dict[str, bytes]) -> tuple[bytes, list[str]]:
    """Apply the minimal repair for `code`. Returns the new bytes and the exact
    list of entry names touched, so the caller can assert nothing else moved."""
    current = entries_of(data)
    touched: list[str] = []
    for name in CODE_ENTRIES.get(code, ()):
        if name in seed and current.get(name) != seed[name]:
            current[name] = seed[name]
            touched.append(name)
    for name in CODE_REMOVE.get(code, ()):
        if name in current:
            del current[name]
            touched.append(name)
    return rebuild(current), touched


def verify(data: bytes) -> tuple[bool, str | None]:
    from eatf_verifier import verify as _verify  # noqa: PLC0415

    r = _verify(data)
    return bool(r.valid), r.failure_code


def peel(case_id: str, data: bytes, seed: dict[str, bytes], limit: int = 12) -> dict:
    """Peel one case down to acceptance, recording the code seen at each step."""
    sequence: list[str] = []
    steps: list[dict] = []
    stopped = None
    for _ in range(limit):
        valid, code = verify(data)
        if valid:
            stopped = "accepted"
            break
        if code is None:
            stopped = "rejected-without-code"
            break
        sequence.append(code)
        if code in UNREPAIRABLE:
            stopped = f"unrepairable:{code}"
            break
        before = entries_of(data)
        data, touched = repair(data, code, seed)
        after = entries_of(data)
        changed = sorted(set(before) ^ set(after)) + sorted(
            n for n in set(before) & set(after) if before[n] != after[n])
        if not touched:
            stopped = f"repair-had-no-effect:{code}"
            break
        # The repair must move exactly what it claims to move.
        assert sorted(set(changed)) == sorted(set(touched)), (case_id, code, changed, touched)
        steps.append({"code": code, "entries_restored": touched})
    else:
        stopped = "limit-reached"
    return {
        "id": case_id,
        "fault_sequence": sequence,
        "fault_set_size": len(sequence),
        "order_invariant": len(sequence) == 1,
        "steps": steps,
        "stopped": stopped,
    }


def load_corpus() -> list[tuple[str, bytes, str]]:
    """(case id, package bytes, source experiment) for every case we can reach."""
    out: list[tuple[str, bytes, str]] = []
    for source, root in (
        ("decision-path", REPO_ROOT / "experiments/decision-path/generated/corpus"),
        ("path-shadowing", REPO_ROOT / "experiments/path-shadowing/generated"),
    ):
        if not root.exists():
            continue
        for case_dir in sorted(root.iterdir()):
            pkg = case_dir / "package.aep"
            if pkg.is_file():
                out.append((case_dir.name, pkg.read_bytes(), source))
    return out


def main() -> int:
    seed_path = REPO_ROOT / "test-vectors/valid/minimal-roundtrip/package.aep"
    seed = entries_of(seed_path.read_bytes())

    corpus = load_corpus()
    if not corpus:
        print("no corpus found; run the decision-path and path-shadowing experiments first",
              file=sys.stderr)
        return 1

    rows = []
    for case_id, data, source in corpus:
        row = peel(case_id, data, seed)
        row["source"] = source
        rows.append(row)

    # A peel that stalls because its repair changes nothing is not a
    # measurement: it means the guard that fired is reacting to bytes this
    # repair vocabulary does not reach. Those cases are reported as
    # inconclusive rather than folded into an invariance figure.
    measurable = [r for r in rows if r["stopped"] == "accepted"]
    unrepairable = [r for r in rows if r["stopped"].startswith("unrepairable")]
    other = [r for r in rows if r not in measurable and r not in unrepairable]
    multi = [r for r in measurable if r["fault_set_size"] > 1]

    summary = {
        "cases": len(rows),
        "peeled_to_acceptance": len(measurable),
        "terminated_on_an_unrepairable_code": len(unrepairable),
        "other_terminations": len(other),
        "single_repair_cases": sum(1 for r in measurable if r["fault_set_size"] == 1),
        "multi_repair_cases": len(multi),
        "multi_repair_ids": [r["id"] for r in multi],
        "inconclusive_cases": len(other),
        "inconclusive_ids": [r["id"] for r in other],
        "code_invariance": "NOT MEASURED — see limitation",
        "limitation": (
            "This harness measures how many REPAIRS a package needs, not how many GUARDS "
            "reject it, and for this artifact the two come apart. A single byte-level fault "
            "is often visible at several guards: an absent overt_receipt.sig is seen both by "
            "the receipt's witness-reference check and by the signed-receipt-required check, "
            "and one restoration clears both. Peeling therefore reports one repair where two "
            "guards would fire, which is precisely the structure this experiment exists to "
            "detect. No code-invariance figure may be derived from these numbers. The "
            "preference for repair peeling recorded in DESIGN.md is hereby withdrawn on the "
            "evidence of this run; guard-level fault sets require the non-short-circuiting "
            "collect mode that design rejected."),
    }

    GENERATED.mkdir(exist_ok=True)
    payload = {
        "schema": "urn:eatf:experiment:ordering-faultsets:1",
        "environment": {"python": platform.python_version()},
        "seed": str(seed_path.relative_to(REPO_ROOT)),
        "unrepairable_codes": UNREPAIRABLE,
        "summary": summary,
        "rows": rows,
    }
    (GENERATED / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = ["case,source,fault_set_size,order_invariant,stopped,fault_sequence"]
    for r in rows:
        lines.append(f"{r['id']},{r['source']},{r['fault_set_size']},"
                     f"{str(r['order_invariant']).lower()},{r['stopped']},"
                     f"{'|'.join(r['fault_sequence'])}")
    (GENERATED / "results.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    digest = hashlib.sha256((GENERATED / "results.csv").read_bytes()).hexdigest()
    (GENERATED / "SHA256SUMS").write_text(f"{digest}  generated/results.csv\n", encoding="utf-8")

    print("# Repair peeling — instrument check, not a result")
    for k, v in summary.items():
        if k != "note":
            print(f"- {k}: {v}")
    for r in rows:
        if r["fault_set_size"] > 1 or r["stopped"] != "accepted":
            print(f"  {r['id']:34s} {r['stopped']:32s} {' -> '.join(r['fault_sequence'])}")
    print(f"- results.csv digest: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
