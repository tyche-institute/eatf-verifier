# `advisory-fail-imprint/`

**Expected:** `verify=true`, with a failed check inside.

A byte-identical copy of `../valid/minimal-roundtrip` under default
options. The embedded RFC 3161 token was issued over a different hash
than this package's (the round-trip flow grafts an older token), so the
message-imprint comparison FAILS. The verifier accepts the mismatch
"for Java reference compatibility" and returns `valid: true`.

The boundary records the reality the validity bit hides:
`tsa-imprint` is `verdict: "fail"` with `enforced: false` — the live
"assessed, FAILED, accepted anyway" specimen. `tsa-signerinfo` and
`tsa-chain-to-root` are `not_determinate` because the shipped token
carries no embedded signing certificate.

Produced by `scripts/generate-boundary-vectors.mjs`.
