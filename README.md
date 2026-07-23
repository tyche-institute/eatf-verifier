# EATF — Agent Evidence Package (AEP) reference verifiers

Open reference implementation for creating and **offline-verifying Agent
Evidence Packages (`.aep`)** — portable, cryptographically verifiable evidence
of AI-agent actions.

## Statement of need

AI agents increasingly act across organizational boundaries, but the party that
produces a record of an agent's action is rarely the party that later needs to
check it. Auditors, deployers, and researchers need a way to verify — offline,
without trusting the producer's infrastructure — that a recorded agent action is
authentic, untampered, timestamped, and within delegated scope. Existing
attestation stacks (RATS/EAT/COSE) provide building blocks but no end-to-end,
runnable package format plus verifier for AI-agent evidence. EATF fills that
gap: a documented `.aep` package profile, two independent verifier
implementations, and a conformance suite with negative controls.

## What is in this repository

| Path | What it is |
|---|---|
| `lib/` | TypeScript verifier library (`@eatf/verifier`) — browser + Node 20+ |
| `lib-python/` | Python verifier (`eatf_verifier`) — independent implementation |
| `cli/eatf-verify`, `cli/eatf-sign`, `cli/eatf-inspect` | Offline CLIs (no network calls, no API keys) |
| `schemas/` | JSON Schemas: `aep-v1.schema.json` (package metadata) and `overt-receipt-v1.schema.json` (OVERT receipt) |
| `test-vectors/` | Conformance vectors — `valid/` (4), `invalid/` (7 negative controls), `keys/` |
| `examples/` | Worked examples (minimal sign+verify, RFC 3161 timestamp, batch verification, private-CA setup) |
| `docs/aep-format.md` | The `.aep` package format summary |

## What is verified

1. ZIP package structure (required entries present)
2. Canonical bytes match a supported AEP canonical form
3. SHA-256 of canonical bytes matches the recorded hash
4. RSA-4096 (PKCS#1 v1.5 / SHA-256) signature
5. ML-DSA-65 (FIPS 204) post-quantum signature, when present
6. OVERT receipt fields, when present
7. RFC 3161 timestamp token structure and message imprint

The two implementations (TypeScript and Python) are expected to agree on the
same `verify=true/false` outcome for every conformance vector.

## Quickstart

```bash
git clone <this-repository>
cd eatf-oss

# Python verifier
cd lib-python
python3 -m venv .venv && .venv/bin/pip install -e . pytest
.venv/bin/python -m pytest tests   # 23 tests

# TypeScript verifier
cd ../lib
npm ci && npm test                 # vitest, 19 tests
```

Verify a conformance vector with the offline CLI:

```bash
cd cli/eatf-verify && npm ci
node bin/eatf-verify.js ../../test-vectors/valid/<vector>/package.aep
```

## Scope and limitations

- This is an **offline reference implementation** of the AEP profile: format,
  verifiers, schemas, and conformance vectors. It is self-contained.
- It is **not** an eIDAS trust service, does not issue qualified certificates or
  attestations, and provides no hosted service. The EU AI Act mapping that
  motivates the format is an engineering argument, not legal advice.
- RFC 3161 verification is structural (message-imprint match); full TSA
  chain validation requires a pinned TSA trust list.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## How to cite

See [CITATION.cff](CITATION.cff). If you use this software in research, please
cite the repository (a versioned archive DOI will be added on release).
