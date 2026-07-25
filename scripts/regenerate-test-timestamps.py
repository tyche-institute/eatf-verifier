#!/usr/bin/env python3
"""Regenerate RFC 3161 timestamps in the committed AEP test vectors.

The script uses a repository-local, TEST-ONLY TSA key and certificate. It
updates every package except ``invalid/bad-timestamp`` so the timestamp
message imprint equals the package's recorded ``hash.sha256`` value and the
CMS signature can be verified from the embedded TSA certificate.

RFC 3161 tokens include a generation time and serial number, so regeneration
is semantically reproducible but not byte-for-byte deterministic.
"""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
KEYS = ROOT / "test-vectors" / "keys"
TSA_KEY = KEYS / "dev-tsa-rsa-3072.key"
TSA_CERT = KEYS / "dev-tsa-rsa-3072.pem"


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def ensure_test_tsa() -> None:
    if TSA_KEY.exists() != TSA_CERT.exists():
        raise SystemExit(
            f"Refusing partial TEST TSA state: expected both {TSA_KEY} and {TSA_CERT}"
        )
    if TSA_KEY.exists():
        return

    run("openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", str(TSA_KEY))
    os.chmod(TSA_KEY, 0o600)
    run(
        "openssl",
        "req",
        "-new",
        "-x509",
        "-key",
        str(TSA_KEY),
        "-out",
        str(TSA_CERT),
        "-days",
        "3650",
        "-sha256",
        "-subj",
        "/C=EE/O=Tyche Institute Test Fixtures/OU=TEST ONLY/CN=EATF Test TSA",
        "-addext",
        "basicConstraints=critical,CA:FALSE",
        "-addext",
        "keyUsage=critical,digitalSignature,nonRepudiation",
        "-addext",
        "extendedKeyUsage=critical,timeStamping",
    )


def config_text(work: Path) -> str:
    return f"""\
[ tsa ]
default_tsa = tsa_config

[ tsa_config ]
dir = {work}
serial = {work / "serial"}
signer_cert = {TSA_CERT}
certs = {TSA_CERT}
signer_key = {TSA_KEY}
signer_digest = sha256
crypto_device = builtin
default_policy = 1.3.6.1.4.1.55555.1
other_policies = 1.3.6.1.4.1.55555.2
digests = sha256
accuracy = secs:1
ordering = yes
tsa_name = yes
ess_cert_id_chain = no
ess_cert_id_alg = sha256
"""


def timestamp_for_digest(digest_hex: str, work: Path, serial: int) -> bytes:
    (work / "serial").write_text(f"{serial:02X}\n", encoding="ascii")
    config = work / "tsa.cnf"
    config.write_text(config_text(work), encoding="utf-8")
    query = work / "request.tsq"
    response = work / "response.tsr"
    run(
        "openssl",
        "ts",
        "-query",
        "-digest",
        digest_hex,
        "-sha256",
        "-no_nonce",
        "-cert",
        "-out",
        str(query),
    )
    run(
        "openssl",
        "ts",
        "-reply",
        "-config",
        str(config),
        "-queryfile",
        str(query),
        "-out",
        str(response),
    )
    return response.read_bytes()


def replace_timestamp(package: Path, raw_tsr: bytes) -> None:
    encoded = base64.b64encode(raw_tsr) + b"\n"
    with zipfile.ZipFile(package, "r") as source:
        members = [(info, source.read(info.filename)) for info in source.infolist()]

    destination = package.with_suffix(".aep.tmp")
    with zipfile.ZipFile(destination, "w") as target:
        found = False
        for info, data in members:
            if info.filename == "timestamp.tsr":
                data = encoded
                found = True
            target.writestr(info, data)
        if not found:
            raise ValueError(f"{package} has no timestamp.tsr entry")
    os.replace(destination, package)


def packages() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "test-vectors").glob("*/*/package.aep")
        if "invalid/bad-timestamp" not in path.as_posix()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-openssl-only",
        action="store_true",
        help="Check prerequisites and TEST TSA material without changing packages.",
    )
    parser.add_argument(
        "--digest",
        help="Create one raw TimeStampResp for this SHA-256 hex digest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path used with --digest.",
    )
    args = parser.parse_args()

    if shutil.which("openssl") is None:
        raise SystemExit("openssl is required")
    ensure_test_tsa()
    if args.check_openssl_only:
        return 0
    if bool(args.digest) != bool(args.output):
        parser.error("--digest and --output must be supplied together")
    if args.digest:
        digest = args.digest.strip().lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            parser.error("--digest must be a SHA-256 hex digest")
        with tempfile.TemporaryDirectory(prefix="eatf-tsa-") as temp:
            args.output.write_bytes(timestamp_for_digest(digest, Path(temp), 1))
        print(f"wrote {args.output}")
        return 0

    with tempfile.TemporaryDirectory(prefix="eatf-tsa-") as temp:
        work = Path(temp)
        for serial, package in enumerate(packages(), start=1):
            with zipfile.ZipFile(package, "r") as archive:
                digest = archive.read("hash.sha256").decode("ascii").strip().lower()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"{package}: hash.sha256 is not a SHA-256 hex digest")
            raw_tsr = timestamp_for_digest(digest, work, serial)
            replace_timestamp(package, raw_tsr)
            print(f"updated {package.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
