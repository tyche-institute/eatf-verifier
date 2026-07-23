# `valid-overt-profile/`

**Expected:** `verify=true`.

A well-formed AEP containing a valid OVERT 1.0 foundational receipt
(`scope: foundational:aep-response`). Exercises the full happy-path
pipeline: envelope integrity, manifest canonicalisation, hash chain,
classical signature, ML-DSA-65 signature, RFC 3161 timestamp, and
OVERT receipt validation.

A v0.1-conformant verifier MUST report `verify=true` with no
diagnostic, with the `overtReceipt.scope` field equal to
`foundational:aep-response`.
