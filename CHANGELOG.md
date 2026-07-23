# Changelog

## v0.1.0 — initial public open-core release (2026-07-23)

First public release of the EATF Agent Evidence Package (AEP) reference
verifiers as an open, self-contained project under Apache-2.0.

- TypeScript verifier library (`lib/`) and offline verifier SDK.
- Independent Python verifier (`lib-python/`).
- Offline CLIs: `eatf-verify`, `eatf-sign`, `eatf-inspect` (no network, no keys).
- JSON Schemas for the AEP package, claims, and OVERT receipt.
- Conformance test-vectors: 5 valid + 8 invalid (negative controls).
- Worked examples (minimal sign+verify, RFC 3161 timestamp, batch, private CA).
- Hybrid RSA-4096 + ML-DSA-65 (FIPS 204) signatures; RFC 3161 timestamps
  (structural verification).

Tests: Python 23/23, TypeScript 19/19.
