# `tampered-metadata/`

**Expected:** `verify=false`, diagnostic containing
`overt_receipt.json invalid: policy.decision does not match metadata.policy_decision.`

Derived by a scripted single-field mutation from
`valid/minimal-roundtrip/package.aep` by flipping
`metadata.policy_decision` (`allow` ↔ `deny`). The change makes the
metadata file inconsistent with the OVERT receipt's
`policy.decision` field, which the verifier cross-checks in
`parseAndValidateOvertReceipt`.

Why this specific tamper: this retained early-package fixture uses the legacy
response-only canonical form (`canonical.bin == response.txt`) rather than the
current AEP profile form
(`canonical.bin == response.txt || LF || JCS(metadata)`). With the
response-only form, modifying `metadata.json` does NOT change the
hash chain. The cross-check in the OVERT receipt is what catches
this single-field mutation. The verifier explicitly warns that legacy
metadata is not signature-bound.

Current `eatf-sign` output uses the profile form, so even a coordinated change
to metadata and receipt is rejected at canonical reconstruction. A compatible
verifier MUST still reject this legacy negative package via the OVERT receipt
step.
