# Changelog

## v0.1.2 — documentation reconciliation (2026-07-23)

- Rewrite `docs/aep-format.md` to match the shipped verifier exactly (real
  entry names `signature.sig` / `signature_pqc.sig` + `pqc_public_key.pem`,
  `response.txt` required, `timestamp.tsr` required, hash-view rule).
- Correct the conformance-vector count everywhere: 4 valid + 7 invalid.
- Rewrite `lib/README.md` to describe the implemented verifier (drop unshipped
  ECDSA-P256 / manifest-envelope / RFC 5280 path-validation prose).
- `schemas/README.md` updated to the two shipped schemas.
- Test-vector READMEs no longer reference an unshipped generator script.
- Source comments point at `docs/aep-format.md` (the in-tree format summary).

## v0.1.1 — reviewer-facing fixes (2026-07-23)

- Remove the stale in-tree SDK mirror (`sdks/eatf-verifier-ts`).
- `bin/eatf-verify-ts`: CommonJS launcher + ESM implementation; exits 1 on
  invalid packages and 2 on usage errors (previously could exit 0 silently).
- Apache-2.0 across all manifests; versions unified at 0.1.1.
- Neutral issuer default; repository homepages.
- `verify-expected.txt` regenerated from the actual Python verifier output.

## v0.1.0 — initial public open-core release (2026-07-23)

First public release of the EATF Agent Evidence Package (AEP) reference
verifiers as an open, self-contained project under Apache-2.0.

- TypeScript verifier library (`lib/`) and offline verifier SDK.
- Independent Python verifier (`lib-python/`).
- Offline CLIs: `eatf-verify`, `eatf-sign`, `eatf-inspect` (no network, no keys).
- JSON Schemas for the AEP package, claims, and OVERT receipt.
- Conformance test-vectors: 4 valid + 7 invalid (negative controls).
- Worked examples (minimal sign+verify, RFC 3161 timestamp, batch, private CA).
- Hybrid RSA-4096 + ML-DSA-65 (FIPS 204) signatures; RFC 3161 timestamps
  (structural verification).

Tests: Python 23/23, TypeScript 19/19.
