#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_DIR="${1:-}"
REMOVE_OUTPUT=false
if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$(mktemp -d)"
  REMOVE_OUTPUT=true
fi
mkdir -p "$OUTPUT_DIR"

"$REPO_ROOT/bin/eatf-sign" --gen-mldsa "$OUTPUT_DIR/dev-mldsa65"
"$REPO_ROOT/bin/eatf-sign" \
  --payload "$REPO_ROOT/examples/01-minimal-sign-and-verify/payload.txt" \
  --key "$REPO_ROOT/test-vectors/keys/dev-rsa-4096.key" \
  --public-key "$REPO_ROOT/test-vectors/keys/dev-rsa-4096.pem" \
  --pqc-key "$OUTPUT_DIR/dev-mldsa65.key" \
  --pqc-public-key "$OUTPUT_DIR/dev-mldsa65.pem" \
  --metadata "$REPO_ROOT/examples/01-minimal-sign-and-verify/metadata.json" \
  --scope foundational:aep-response \
  --timestamp "$REPO_ROOT/test-vectors/valid/minimal-roundtrip/package.aep:timestamp.tsr" \
  --out "$OUTPUT_DIR/hybrid-mldsa65.aep"

"$REPO_ROOT/bin/eatf-verify" --require-pqc "$OUTPUT_DIR/hybrid-mldsa65.aep"
"$REPO_ROOT/bin/eatf-verify-py" --require-pqc "$OUTPUT_DIR/hybrid-mldsa65.aep"

printf 'Hybrid round-trip passed with both verifiers: %s\n' "$OUTPUT_DIR/hybrid-mldsa65.aep"
if [[ "$REMOVE_OUTPUT" == true ]]; then
  rm -rf -- "$OUTPUT_DIR"
fi
