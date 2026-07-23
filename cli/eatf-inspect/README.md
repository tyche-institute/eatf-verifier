# `eatf-inspect` — structure dump for `.aep` packages

Pretty-prints the layout of an EATF `.aep` evidence package: ZIP
entries, parsed manifest, OVERT receipt summary, attestation summary,
signature and timestamp filenames. Does **NOT** verify authenticity —
anything in the printed output could have been forged after signing.

For authenticity assertion, use [`eatf-verify`](../eatf-verify) on the
same file.

## Install

```bash
cd cli/eatf-inspect
npm install
node bin/eatf-inspect.js path/to/package.aep
```

## Usage

```
eatf-inspect <path.aep>       Print manifest + entries + signatures summary.
eatf-inspect --json <path>    Emit one JSON object describing the package.
eatf-inspect --version, -V
eatf-inspect --help, -h
```

Exit codes: `0` inspection completed; `1` package is not a well-formed
ZIP / cannot be read; `2` bad CLI usage.

## Example

```bash
$ node cli/eatf-inspect/bin/eatf-inspect.js test-vectors/valid/mcp-tools-call-valid/package.aep

PACKAGE test-vectors/valid/mcp-tools-call-valid/package.aep
  total ZIP entries: 7
  manifest:
    profile: urn:eatf:spec:aep:1.0
    issuer.commonName: ...
    issuer.fingerprint: ...…
    createdAt: 2026-...
    records: 1
  overt_receipt.json:
    scope: agentic-extended:mcp-tools-call
    policy.decision: allow
  records: 1 (0001-action.json)
  signatures: 2 (manifest.sig.cms, manifest.sig.mldsa)
  timestamps: 1 (manifest.tsr)
  certs: 2 (issuer.pem, tsa.pem)

Note: this is a structure dump only. Authenticity is NOT checked.
Run eatf-verify to assert signature, hash chain, and timestamp.
```

## License

Apache License 2.0 — see [`../../LICENSE`](../../LICENSE).
