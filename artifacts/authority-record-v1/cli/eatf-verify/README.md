# `eatf-verify` — offline CLI verifier

Command-line tool for verifying EATF `.aep` evidence packages. Thin
wrapper around [`@eatf/verifier`](../../lib) — does not make any
network calls and does not require API keys.

## Install

Requires Node 20 or later. From a clone of the repository:

```bash
# Build the verifier library it depends on
cd lib
npm install
npm run build

# Install the CLI's dependencies
cd ../cli/eatf-verify
npm install

# Run
node bin/eatf-verify.js path/to/package.aep
```

## Usage

```
eatf-verify <path.aep> [path.aep ...]    Verify one or more packages.
eatf-verify --batch <directory>          Walk a directory tree.
eatf-verify --conformance <vectors-root> Test-vectors valid/+invalid/ tree;
                                          expect verify=true under valid/,
                                          verify=false under invalid/.

Options:
  --json                                  Emit one JSON object per .aep.
  --tsa-trust-list <pem-file>             Pin RFC 3161 TSA roots. Repeatable.
  --offline-only                          Default. No external lookups.
  --version, -V
  --help, -h
```

Exit codes: `0` all verified / contract met; `1` at least one failure;
`2` bad CLI usage or unreadable file.

## Examples

```bash
eatf-verify action.aep
eatf-verify --batch ./received-packages/ --json | jq 'select(.valid == false)'
eatf-verify --conformance ../../test-vectors/
eatf-verify --tsa-trust-list ./roots/freetsa.pem action.aep
```

## What it checks

See [`../../lib/README.md`](../../lib/README.md) for the verification
pipeline. The CLI exits non-zero only if any of the underlying checks
fail for any of the supplied packages.

## What this CLI does NOT do

- **No network calls.** The CLI never contacts a backend, registry, or
  trust list over the wire.
- **No API keys.** No account, tenant, or paid tier. Same code for
  everyone.
- **No signing.** This CLI verifies; it does not produce `.aep` files.
  Signing tooling will land as a separate CLI in a 0.1.x point
  release.
- **No agent registration.** EATF does not operate a centralised
  registry; agent identity is bound inside each `.aep` via the
  attestation record.

These boundaries are intentional and documented in
[`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## License

Apache License 2.0 — see [`../../LICENSE`](../../LICENSE).
