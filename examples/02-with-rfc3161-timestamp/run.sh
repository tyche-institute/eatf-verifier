#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
PACKAGE="$REPO_ROOT/test-vectors/valid/minimal-roundtrip/package.aep"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf -- "$WORK_DIR"' EXIT

python3 - "$PACKAGE" "$WORK_DIR/timestamp.tsr" "$WORK_DIR/digest.hex" <<'PY'
import base64
import pathlib
import sys
import zipfile

package, timestamp_out, digest_out = map(pathlib.Path, sys.argv[1:])
with zipfile.ZipFile(package) as archive:
    timestamp_out.write_bytes(base64.b64decode(archive.read("timestamp.tsr")))
    digest_out.write_text(archive.read("hash.sha256").decode("ascii").strip(), encoding="ascii")
PY

openssl ts -reply -in "$WORK_DIR/timestamp.tsr" -text
openssl ts -verify \
  -in "$WORK_DIR/timestamp.tsr" \
  -digest "$(cat "$WORK_DIR/digest.hex")" \
  -CAfile "$REPO_ROOT/test-vectors/keys/dev-tsa-rsa-3072.pem"
"$REPO_ROOT/bin/eatf-verify" \
  --signer-key "$REPO_ROOT/test-vectors/keys/dev-rsa-4096.pem" "$PACKAGE"
"$REPO_ROOT/bin/eatf-verify-py" \
  --signer-key "$REPO_ROOT/test-vectors/keys/dev-rsa-4096.pem" "$PACKAGE"
