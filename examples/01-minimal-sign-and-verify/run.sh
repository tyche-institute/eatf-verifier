#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
EXAMPLE_DIR="$REPO_ROOT/examples/01-minimal-sign-and-verify"
OUTPUT_DIR="${1:-}"
REMOVE_OUTPUT=false
if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$(mktemp -d)"
  REMOVE_OUTPUT=true
fi
mkdir -p "$OUTPUT_DIR"
PACKAGE="$OUTPUT_DIR/minimal-roundtrip.aep"

"$REPO_ROOT/bin/eatf-sign" \
  --payload "$EXAMPLE_DIR/payload.txt" \
  --key "$REPO_ROOT/test-vectors/keys/dev-rsa-4096.key" \
  --public-key "$REPO_ROOT/test-vectors/keys/dev-rsa-4096.pem" \
  --metadata "$EXAMPLE_DIR/metadata.json" \
  --scope foundational:aep-response \
  --timestamp "$REPO_ROOT/test-vectors/valid/minimal-roundtrip/package.aep:timestamp.tsr" \
  --out "$PACKAGE"

"$REPO_ROOT/bin/eatf-inspect" --json "$PACKAGE"
"$REPO_ROOT/bin/eatf-verify" \
  --signer-key "$REPO_ROOT/test-vectors/keys/dev-rsa-4096.pem" "$PACKAGE"
"$REPO_ROOT/bin/eatf-verify-py" \
  --signer-key "$REPO_ROOT/test-vectors/keys/dev-rsa-4096.pem" "$PACKAGE"

printf 'Round-trip passed with both verifiers: %s\n' "$PACKAGE"
if [[ "$REMOVE_OUTPUT" == true ]]; then
  rm -rf -- "$OUTPUT_DIR"
fi
