# Changelog

## v0.2.0 — toolkit hardening (unreleased)

- Present the repository as one focused AEP toolkit: sign, inspect, dual
  verification, schemas, conformance vectors, examples, and tamper demo.
- Enforce RFC 3161 SHA-256 message-imprint equality and embedded CMS
  SignerInfo verification; remove mismatched-imprint compatibility acceptance.
- Add caller-supplied signer-key pinning to both libraries and CLIs.
- Bound archive, entry, and expanded sizes; reject duplicate or nested ZIP
  names before verifier extraction.
- Make current signer output bind both payload and metadata using the profile
  canonical form; retain response-only support solely for labeled legacy reads.
- Sign exact OVERT receipt bytes separately and place the required-signature
  marker inside signed metadata, preventing receipt-field tampering or
  signature-removal downgrade in current packages.
- Replace divergent handwritten JCS routines with maintained TypeScript and
  Python RFC 8785 implementations plus shared numeric/Unicode boundary tests.
- Add `eatf-sign --print-digest` so producers can request a timestamp for the
  exact payload-plus-metadata canonical digest.
- Compile both Draft 2020-12 schemas in tests and validate every positive
  conformance package against them.
- Replace every positive vector's timestamp with a matching TEST-ONLY RFC 3161
  response and add an auditable regeneration script.
- Add one-command workspace setup and a full sign/inspect/dual-verify/tamper
  smoke test.
- Prepare publishable npm workspace manifests and correct the Python PQC extra
  to use the official `liboqs-python` distribution.
- Remove obsolete wrappers, stub examples, hosted-platform assumptions, and
  the unrelated BKT demonstrator.

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
