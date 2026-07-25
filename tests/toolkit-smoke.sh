#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf -- "$WORK_DIR"' EXIT

"$REPO_ROOT/examples/01-minimal-sign-and-verify/run.sh" "$WORK_DIR/roundtrip"
"$REPO_ROOT/examples/02-with-rfc3161-timestamp/run.sh" >/dev/null
"$REPO_ROOT/examples/03-batch-verification/run.sh" >/dev/null
"$REPO_ROOT/examples/04-tamper-and-reject/run.sh" >/dev/null

echo "Toolkit smoke test passed: sign, inspect, dual verify, RFC 3161, conformance, tamper rejection."
