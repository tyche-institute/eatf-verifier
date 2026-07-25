#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
"$REPO_ROOT/bin/eatf-verify" --conformance "$REPO_ROOT/test-vectors"
"$REPO_ROOT/bin/eatf-verify-py" --conformance "$REPO_ROOT/test-vectors"
