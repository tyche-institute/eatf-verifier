#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf -- "$WORK_DIR"' EXIT

SOURCE="$REPO_ROOT/test-vectors/valid/minimal-roundtrip/package.aep"
TAMPERED="$WORK_DIR/minimal-roundtrip-tampered.aep"
"$REPO_ROOT/bin/eatf-tamper" "$SOURCE" --offset 0 --output "$TAMPERED"

if "$REPO_ROOT/bin/eatf-verify" "$TAMPERED"; then
  echo "TypeScript verifier unexpectedly accepted the tampered package" >&2
  exit 1
fi
if "$REPO_ROOT/bin/eatf-verify-py" "$TAMPERED"; then
  echo "Python verifier unexpectedly accepted the tampered package" >&2
  exit 1
fi
echo "Both verifiers rejected the tampered package as expected."
