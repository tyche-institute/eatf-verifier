# `boundary/` — behavioural vectors for the BoundaryReport

Unlike `../valid/` and `../invalid/`, these vectors pin the verifier's
per-check **BoundaryReport** (`VerifyResult.boundary`, serialised form
in `schemas/boundary-report-v1.schema.json`), not just the
`verify=true/false` contract. Several of them verify **valid on
purpose**: what they freeze is which checks failed without gating,
which were never assessed and why, and which fields sat outside the
signature while the package passed.

Layout per vector:

```
<vector-name>/
├── package.aep
├── verify-expected.txt      # the verify=true/false contract
├── expected-boundary.json   # VerifyOptions + the boundary rows to pin
└── README.md                # what this vector exercises
```

| Vector | verify | Pins |
|---|---|---|
| `boundary-suppressed-tsa/` | `true` | `tsaTrustList: []` ⇒ `tsa-chain-to-root` is `not_assessed`/`option_disabled` — a disabled check stays visible. |
| `response-only-unsigned-policy-tamper/` | `true` | `policy_decision` flipped `deny`→`allow` in **both** unsigned files post-signing; still verifies; `unsignedFields` names the rewritable fields. |
| `advisory-fail-imprint/` | `true` | `tsa-imprint` is `fail` with `enforced=false` — assessed, failed, accepted anyway. |
| `short-circuit-shadow/` | `false` | Hash mismatch; every check behind it emitted as `not_assessed`/`short_circuited`. |
| `claimed-surface-overclaim/` | `true` | Post-signing `claimed_assessment_surface` claim; `claimedSurface` reports the claimed-vs-computed diff. |
| `not-determinate-imprint-alg/` | `true` | Imprint hash OID flipped to SHA-512; `tsa-imprint` is `not_determinate`/`capability_absent`. |

Produced deterministically by `scripts/generate-boundary-vectors.mjs`
from committed `../valid/` baselines; regenerating produces
byte-identical files. Consumed by `lib/test/boundary-vectors.test.ts`,
which verifies each package with the options in
`expected-boundary.json` and asserts the pinned boundary rows.

The `--conformance` CLIs (TypeScript and Python) intentionally skip
this directory: its contract is the boundary, which only the
TypeScript verifier emits in v0.1.
