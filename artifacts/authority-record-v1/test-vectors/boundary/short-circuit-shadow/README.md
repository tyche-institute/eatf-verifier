# `short-circuit-shadow/`

**Expected:** `verify=false`, diagnostic `Hash mismatch.`

`../valid/minimal-roundtrip` with the first hex digit of `hash.sha256`
swapped, so verification fails at the hash comparison. Every check that
runs *after* the hash step — `rsa-signature`, `rsa-digestinfo-fallback`,
`overt-receipt`, `pqc-mldsa65`, `tsa-present`, `tsa-imprint`,
`tsa-signerinfo`, `tsa-chain-to-root` — is emitted as `not_assessed`
with reason `short_circuited`.

The vector freezes the short-circuit shadow: the exact set of evidence
a given failure class destroys by ending the pipeline early. The
boundary makes that shadow a first-class, machine-readable output
rather than an implicit consequence of control flow.

Produced by `scripts/generate-boundary-vectors.mjs`.
