#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python "$REPO_ROOT/workshops/pqc-hybrid-lab/run_lab.py"
