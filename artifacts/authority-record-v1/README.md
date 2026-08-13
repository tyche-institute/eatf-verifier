# Authority-record study artifact

This directory is the public, frozen artifact accompanying the manuscript
*Valid Is a Floor, Not a Ceiling: The Assessed Perimeter of an Offline
Signed-Evidence Verifier for Autonomous-Agent Actions*.

The snapshot contains the exact reference code, specification surface, and
synthetic vector corpus used for the manuscript's measurements as of
2026-08-13. It is published as a research artifact, not as a managed service.

## Contents

- `lib/`: TypeScript reference verifier and signer, with its test suite.
- `lib-python/`: independent-language Python verifier port and tests.
- `cli/`: the `eatf-verify`, `eatf-sign`, and non-verifying `eatf-inspect`
  command-line entry points.
- `schemas/`: the six JSON Schema documents used by the artifact.
- `docs/specs/aep-profile-v1.md`: the measured profile specification.
- `docs/specs/assessment-surface-v1.json`: the normative-clause-to-check map
  used as the study denominator.
- `test-vectors/`: 58 frozen synthetic packages: 11 valid, 8 invalid,
  7 boundary, 9 mandate, 4 acceptance, 11 voiding, and 8 warrant vectors.
- `scripts/`: the frozen vector generators, census programs, and rewrite-class
  probe used to reproduce the reported measurements.
- `SHA256SUMS`: hashes for every other file in this snapshot.

The corpus includes an intentionally insecure development RSA private key.
It is labelled under `test-vectors/keys/` and exists only so that the synthetic
fixtures can be regenerated. It must never be used outside tests.

The `$id` values in the schema files are stable identifiers. The schemas are
self-contained in this directory; reproducing the study does not require those
identifier URLs to be dereferenceable or any other network access.

## Scope and evidentiary boundary

Both verifier implementations, the additive authority-record extension, the
assessment map, and the frozen corpus are the manuscript author's own research
artifacts. The release demonstrates reproducibility across those two
implementations and this authored corpus. It does **not** claim independent
implementation, third-party adoption, production prevalence, live-deployment
performance, interoperability certification, or external validation.

EATF is not an eIDAS trust service and does not issue qualified certificates,
signatures, timestamps, or attestations. The packages here are technical
self-attestations. A successful verifier result is not a claim that an agent's
action was correct, safe, lawful, or appropriate.

## OVERT attribution and non-endorsement

OVERT is an open standard published by Glacis Technologies, Inc.
<https://overt.is>. This artifact is independent of Glacis Technologies and
there is no ownership, employment, financial, contractual, institutional,
funding, or partnership relationship. Prior author correspondence about
terminology does not imply endorsement. The `overt_receipt.json` entry is an
OVERT-inspired, receipt-shaped object defined by the AEP profile. It is not
claimed to be OVERT-conformant and has not been reviewed, certified, or
approved by Glacis Technologies. No endorsement is made in either direction.

## Reproduce the verification checks

Requirements: Node.js 20 or later and Python 3.11 or later.

```bash
# TypeScript build and tests (113 tests in the frozen snapshot)
(cd lib && npm ci && npm run build && npm test)

# TypeScript conformance contract (11 accepted, 8 rejected, 0 mismatches)
node cli/eatf-verify/bin/eatf-verify.js --conformance test-vectors

# Python tests (75 tests in the frozen snapshot)
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e 'lib-python[dev]'
pytest -q lib-python/tests

# Python conformance contract (11 accepted, 8 rejected, 0 mismatches)
python -m eatf_verifier.cli --conformance test-vectors
```

The census commands used in the paper are:

```bash
node scripts/boundary-census.mjs
node scripts/warrant-census.mjs
node scripts/voiding-census.mjs
node scripts/rewrite-class-probe.mjs
```

## License

The snapshot is released under the Apache License 2.0. See `LICENSE` and
`NOTICE`. Package-local copies of the same license are included for the two
libraries and three command-line packages.
