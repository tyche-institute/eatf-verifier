# `claimed-surface-overclaim/`

**Expected:** `verify=true`, with a flagged overclaim in the boundary.

`../valid/minimal-roundtrip` with a producer-side
`claimed_assessment_surface` array injected into `metadata.json` after
signing (possible precisely because the response-only form leaves
metadata unsigned). The claim names:

- `tsa-chain-to-root` — not assessed here (empty trust list),
- `pqc-mldsa65` — not assessed here (no PQC entries),
- `not-a-real-check` — not in the registry at all.

The boundary's `claimedSurface` diff reports `unrecognized:
["not-a-real-check"]` and `notAssessed: ["pqc-mldsa65",
"tsa-chain-to-root"]`, so the gap between what the producer claims was
assessed and what the verifier actually assessed is machine-checkable.
Because the claim itself is unsigned in this form, `unsignedFields`
also lists `metadata.claimed_assessment_surface` — the claim carries no
more weight than any other unsigned metadata field.

Produced by `scripts/generate-boundary-vectors.mjs`.
