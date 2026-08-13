# `boundary-suppressed-tsa/`

**Expected:** `verify=true`.

A byte-identical copy of `../valid/mcp-tools-call-valid`, verified with
`tsaTrustList: []`. The package is unremarkable; the vector exists to
freeze the boundary contract that **disabling** the chain-to-root check
must remain *visible*: the `tsa-chain-to-root` row is
`not_assessed` with reason `option_disabled`, `enforced=false` — never
silently dropped from the report. This is the anti-gaming property at
the level of one check: an operator who narrows the check universe
still shows the narrowing in the boundary.

Produced by `scripts/generate-boundary-vectors.mjs`.
