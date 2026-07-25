#!/usr/bin/env python3
"""Generate the SNCS decision-path corpus from explicit mutation operators."""

from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path
import shutil
import warnings
import zipfile

from asn1crypto import tsp
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
ORACLE = HERE / "oracle.json"
DEFAULT_OUTPUT = HERE / "generated" / "corpus"


def read_entries(source: bytes) -> list[tuple[zipfile.ZipInfo, bytes]]:
    with zipfile.ZipFile(io.BytesIO(source), "r") as archive:
        return [(info, archive.read(info.filename)) for info in archive.infolist()]


def rewrite(
    source: bytes,
    *,
    replacements: dict[str, bytes] | None = None,
    removals: set[str] | None = None,
    additions: list[tuple[str, bytes]] | None = None,
) -> bytes:
    replacements = replacements or {}
    removals = removals or set()
    additions = additions or []
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for info, data in read_entries(source):
            if info.filename in removals:
                continue
            archive.writestr(info.filename, replacements.get(info.filename, data))
        for name, data in additions:
            archive.writestr(name, data)
    return output.getvalue()


def timestamp_raw(source: bytes):
    entries = dict((info.filename, data) for info, data in read_entries(source))
    return tsp.TimeStampResp.load(base64.b64decode(entries["timestamp.tsr"].strip()))


def timestamp_entry(response: tsp.TimeStampResp) -> bytes:
    return base64.b64encode(response.dump()) + b"\n"


def rewrite_receipt(
    source: bytes,
    mutate,
    *,
    removals: set[str] | None = None,
    replacements: dict[str, bytes] | None = None,
) -> bytes:
    entries = dict((info.filename, data) for info, data in read_entries(source))
    receipt = json.loads(entries["overt_receipt.json"])
    mutate(receipt)
    receipt_bytes = (
        json.dumps(receipt, separators=(",", ":")).encode("utf-8") + b"\n"
    )
    private_key = serialization.load_pem_private_key(
        (REPO_ROOT / "test-vectors/keys/dev-rsa-4096.key").read_bytes(),
        password=None,
    )
    receipt_signature = private_key.sign(
        receipt_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    changed = dict(replacements or {})
    changed["overt_receipt.json"] = receipt_bytes
    changed["overt_receipt.sig"] = base64.b64encode(receipt_signature) + b"\n"
    return rewrite(
        source,
        replacements=changed,
        removals=removals,
    )


def mutate_timestamp_imprint(source: bytes) -> bytes:
    response = timestamp_raw(source)
    signed_data = response["time_stamp_token"]["content"]
    encapsulated = signed_data["encap_content_info"]["content"]
    info = encapsulated.parsed
    if not isinstance(info, tsp.TSTInfo):
        info = tsp.TSTInfo.load(encapsulated.contents)
    digest = bytearray(info["message_imprint"]["hashed_message"].native)
    digest[0] ^= 0x01
    info["message_imprint"]["hashed_message"] = bytes(digest)
    signed_data["encap_content_info"]["content"] = info
    return rewrite(
        source,
        replacements={"timestamp.tsr": timestamp_entry(response)},
    )


def mutate_timestamp_cert_missing(source: bytes) -> bytes:
    response = timestamp_raw(source)
    del response["time_stamp_token"]["content"]["certificates"]
    return rewrite(
        source,
        replacements={"timestamp.tsr": timestamp_entry(response)},
    )


def mutate_timestamp_signature(source: bytes) -> bytes:
    response = timestamp_raw(source)
    signer_info = response["time_stamp_token"]["content"]["signer_infos"][0]
    signature = bytearray(signer_info["signature"].native)
    signature[0] ^= 0x01
    signer_info["signature"] = bytes(signature)
    return rewrite(
        source,
        replacements={"timestamp.tsr": timestamp_entry(response)},
    )


def apply_operator(operator: str, baseline: bytes) -> bytes:
    if operator == "identity":
        return baseline
    if operator == "replace_archive_with_non_zip_bytes":
        return b"EATF decision-path negative control: not a ZIP archive\n"
    if operator == "replace_archive_with_33_flat_entries":
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index in range(33):
                archive.writestr(f"entry-{index:02d}.txt", b"x")
        return output.getvalue()
    if operator == "add_nested_entry":
        return rewrite(baseline, additions=[("nested/entry.txt", b"x")])
    if operator == "append_duplicate_entry":
        output = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for info, data in read_entries(baseline):
                    archive.writestr(info.filename, data)
                archive.writestr("response.txt", b"duplicate")
        return output.getvalue()
    if operator == "remove_canonical.bin":
        return rewrite(baseline, removals={"canonical.bin"})
    if operator == "replace_metadata_with_invalid_json":
        return rewrite(baseline, replacements={"metadata.json": b"{invalid\n"})
    if operator == "replace_metadata_with_json_array":
        return rewrite(baseline, replacements={"metadata.json": b"[]\n"})
    if operator == "flip_first_canonical_byte":
        entries = dict((info.filename, data) for info, data in read_entries(baseline))
        changed = bytearray(entries["canonical.bin"])
        changed[0] ^= 0x01
        return rewrite(baseline, replacements={"canonical.bin": bytes(changed)})
    if operator == "replace_hash_with_zero_digest":
        return rewrite(baseline, replacements={"hash.sha256": b"0" * 64 + b"\n"})
    if operator == "replace_rsa_signature_with_zero_bytes":
        return rewrite(
            baseline,
            replacements={"signature.sig": base64.b64encode(b"\0" * 512) + b"\n"},
        )
    if operator == "replace_receipt_content_hash":
        entries = dict((info.filename, data) for info, data in read_entries(baseline))
        receipt = json.loads(entries["overt_receipt.json"])
        receipt["content_hash"] = f"sha256:{'0' * 64}"
        return rewrite(
            baseline,
            replacements={
                "overt_receipt.json": json.dumps(
                    receipt, separators=(",", ":")
                ).encode()
                + b"\n"
            },
        )
    if operator == "replace_overt_signature_with_zero_bytes":
        return rewrite(
            baseline,
            replacements={"overt_receipt.sig": base64.b64encode(b"\0" * 512) + b"\n"},
        )
    if operator == "remove_overt_signature_witness_then_remove_file":
        def remove_witness(receipt: dict) -> None:
            receipt["witness"]["signature_refs"] = ["signature.sig"]

        return rewrite_receipt(
            baseline,
            remove_witness,
            removals={"overt_receipt.sig"},
        )
    if operator == "add_signature_pqc.sig_without_public_key":
        return rewrite(
            baseline,
            additions=[("signature_pqc.sig", base64.b64encode(b"negative-control") + b"\n")],
        )
    if operator == "remove_timestamp_witness_then_empty_timestamp":
        def remove_witness(receipt: dict) -> None:
            receipt["witness"]["timestamp_refs"] = []

        return rewrite_receipt(
            baseline,
            remove_witness,
            replacements={"timestamp.tsr": b""},
        )
    if operator == "flip_timestamp_message_imprint":
        return mutate_timestamp_imprint(baseline)
    if operator == "remove_timestamp_embedded_certificates":
        return mutate_timestamp_cert_missing(baseline)
    if operator == "flip_timestamp_signerinfo_signature":
        return mutate_timestamp_signature(baseline)
    raise ValueError(f"unknown operator: {operator}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    baseline_path = REPO_ROOT / oracle["baseline"]
    baseline = baseline_path.read_bytes()

    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True)

    for case in oracle["cases"]:
        case_dir = args.output / case["id"]
        case_dir.mkdir()
        package = apply_operator(case["operator"], baseline)
        (case_dir / "package.aep").write_bytes(package)
        (case_dir / "case.json").write_text(
            json.dumps(case, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(f"generated {len(oracle['cases'])} cases in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
