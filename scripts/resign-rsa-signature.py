#!/usr/bin/env python3
"""Re-sign signature.sig of an .aep package in the RFC 8017 form.

    python3 scripts/resign-rsa-signature.py <package.aep> <private-key.pem>

Computes RSASSA-PKCS1-v1_5 / SHA-256 over canonical.bin (DigestInfo with
NULL parameters, RFC 8017 Section 9.2) and rewrites only signature.sig.
Every other entry keeps its bytes, name, order, timestamp and compression,
and the private key must match public_key.pem.

Used on 14 November 2026 for the four shared vectors whose signatures had
been made by the Java reference signer with DigestInfo parameters absent.
"""

from __future__ import annotations

import base64
import io
import sys
import zipfile

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def main(package: str, key_path: str) -> None:
    with open(package, "rb") as f:
        original = f.read()
    with open(key_path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    src = zipfile.ZipFile(io.BytesIO(original))
    entries = {info.filename: src.read(info) for info in src.infolist()}
    embedded = serialization.load_pem_public_key(entries["public_key.pem"])
    if embedded.public_numbers() != key.public_key().public_numbers():
        sys.exit("private key does not match public_key.pem")
    old = entries["signature.sig"]
    sig = key.sign(entries["canonical.bin"], padding.PKCS1v15(), hashes.SHA256())
    new = base64.b64encode(sig) + (b"\n" if old.endswith(b"\n") else b"")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            data = new if info.filename == "signature.sig" else entries[info.filename]
            dst.writestr(info, data, compress_type=info.compress_type)
    with open(package, "wb") as f:
        f.write(out.getvalue())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
