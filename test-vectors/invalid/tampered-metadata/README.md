# `tampered-metadata/`

**Expected:** `verify=false`, diagnostic containing
`overt_receipt.json invalid: policy.decision does not match metadata.policy_decision.`

Produced by `scripts/generate-invalid-vectors.mjs` from
`valid/minimal-roundtrip/package.aep` by flipping
`metadata.policy_decision` (`allow` ↔ `deny`). The change makes the
metadata file inconsistent with the OVERT receipt's
`policy.decision` field, which the verifier cross-checks in
`parseAndValidateOvertReceipt`.

Why this specific tamper: the v0.1 reference packages use the
"Java response-only" canonical form (`canonical.bin == response.txt`)
rather than the "AEP profile" form
(`canonical.bin == response.txt || LF || JCS(metadata)`). With the
response-only form, modifying `metadata.json` does NOT change the
hash chain. The cross-check in the OVERT receipt is what catches
the tamper in this fixture set.

A v0.1-conformant verifier MUST reject this package via the OVERT
receipt step.
