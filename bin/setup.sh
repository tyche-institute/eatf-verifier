#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"

require_version() {
  local command_name="$1"
  local minimum_major="$2"
  local version
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing prerequisite: $command_name" >&2
    exit 2
  fi
  version="$("$command_name" --version 2>&1)"
  printf 'Found %s: %s\n' "$command_name" "$version"
  local major
  if [[ "$command_name" == "node" ]]; then
    major="${version#v}"
    major="${major%%.*}"
  else
    major="$(python3 -c 'import sys; print(sys.version_info.major * 100 + sys.version_info.minor)')"
  fi
  if (( major < minimum_major )); then
    echo "$command_name is too old; required minimum is $minimum_major" >&2
    exit 2
  fi
}

require_version node 20
require_version python3 311

cd "$REPO_ROOT"
npm ci --no-audit --no-fund
npm run build

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install -e 'lib-python[dev]'

for command_path in \
  "$REPO_ROOT/bin/eatf-sign" \
  "$REPO_ROOT/bin/eatf-inspect" \
  "$REPO_ROOT/bin/eatf-verify" \
  "$REPO_ROOT/bin/eatf-verify-py" \
  "$REPO_ROOT/bin/eatf-tamper"; do
  "$command_path" --help >/dev/null
done

printf '\nSetup complete. Add this directory to PATH for the current shell:\n'
printf '  export PATH="%s/bin:$PATH"\n' "$REPO_ROOT"
printf '\nRun the complete reviewer smoke test with:\n'
printf '  npm run test:toolkit\n'
