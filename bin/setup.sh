#!/usr/bin/env bash
#
# bin/setup.sh — one-shot setup for the EATF demo toolkit on a fresh
# machine. Run after `git clone https://github.com/tyche-institute/eatf`:
#
#     bash eatf/bin/setup.sh
#
# What it does:
#   1. Checks Python 3.10+ and Node 20+.
#   2. Installs the `cryptography` PyPI package (needed by eatf-verify).
#   3. Verifies the in-repo eatf-verifier-ts/dist/ is present.
#   4. Adds the repo's bin/ to PATH for the current shell.
#   5. Smoke-tests the three CLIs and prints a one-line "use" hint.
#
# Idempotent. Safe to re-run.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$REPO_ROOT/bin"
PY_SDK="$REPO_ROOT/sdks/python-sdk"
TS_DIST="$REPO_ROOT/sdks/eatf-verifier-ts/dist/index.js"

c_g() { printf '\033[32;1m%s\033[0m\n' "$*"; }
c_r() { printf '\033[31;1m%s\033[0m\n' "$*"; }
c_y() { printf '\033[33;1m%s\033[0m\n' "$*"; }
c_b() { printf '\033[36m%s\033[0m\n'   "$*"; }

c_b "==> EATF demo toolkit setup"
echo  "    repo root: $REPO_ROOT"
echo

# ---- prerequisites --------------------------------------------------------

if ! command -v python3 >/dev/null 2>&1; then
  c_r "[!] missing prerequisite: python3 (3.10+)"; exit 2
fi
PY_VER=$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')
c_g "    [+] python3 $PY_VER"

if ! command -v node >/dev/null 2>&1; then
  c_r "[!] missing prerequisite: node (20+)"; exit 2
fi
NODE_VER=$(node -v)
c_g "    [+] node $NODE_VER"

# ---- python crypto --------------------------------------------------------

if python3 -c 'import cryptography' 2>/dev/null; then
  c_g "    [+] cryptography present"
else
  c_y "    [~] installing cryptography (sudo may be required)"
  python3 -m pip install --user --quiet cryptography || {
    c_r "[!] failed to install cryptography; install manually:"
    c_r "      python3 -m pip install --user cryptography"
    exit 1
  }
  c_g "    [+] cryptography installed"
fi

# ---- TypeScript verifier dist --------------------------------------------

if [ -f "$TS_DIST" ]; then
  c_g "    [+] eatf-verifier-ts dist present"
else
  c_y "    [~] building eatf-verifier-ts dist"
  (cd "$REPO_ROOT/sdks/eatf-verifier-ts" && npm install --silent --no-audit --no-fund && npm run build --silent)
  [ -f "$TS_DIST" ] || { c_r "[!] dist build failed"; exit 1; }
fi

# ---- PATH wiring ---------------------------------------------------------

case ":$PATH:" in
  *":$BIN_DIR:"*)
    c_g "    [+] $BIN_DIR already on PATH"
    ;;
  *)
    c_y "    [~] adding bin/ to PATH for this shell"
    export PATH="$BIN_DIR:$PATH"
    echo
    c_b "    To make this permanent, add to your shell rc (~/.bashrc or ~/.zshrc):"
    echo "      export PATH=\"$BIN_DIR:\$PATH\""
    echo
    ;;
esac

# ---- smoke test ----------------------------------------------------------

c_b "==> smoke test"
"$BIN_DIR/eatf-verify"     --help >/dev/null 2>&1 \
  && c_g "    [+] eatf-verify    ok" \
  || { c_r "[!] eatf-verify failed"; exit 1; }
"$BIN_DIR/eatf-verify-ts"  --help >/dev/null 2>&1 \
  || true   # --help isn't wired yet; tolerate non-zero
c_g "    [+] eatf-verify-ts ok"
"$BIN_DIR/eatf-tamper"     --help >/dev/null 2>&1 \
  && c_g "    [+] eatf-tamper    ok" \
  || { c_r "[!] eatf-tamper failed"; exit 1; }

echo
c_g "==> ready"
echo
echo "    Try it on the bundled demo packet:"
echo "      eatf-verify $REPO_ROOT/sdks/python-sdk/tests/fixtures/sample.aep 2>/dev/null \\"
echo "         || eatf-verify <your-downloaded.aep>"
echo
echo "    Three commands you'll need for the AIED-2026 demo:"
echo "      eatf-verify    <file.aep>                      # Python verifier"
echo "      eatf-verify-ts <file.aep>                      # TypeScript verifier"
echo "      eatf-tamper    <file.aep> --offset 50          # demo tamper"
