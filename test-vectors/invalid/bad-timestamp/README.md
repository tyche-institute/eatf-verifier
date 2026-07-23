# `bad-timestamp/`

**Expected:** `verify=false`, diagnostic
`timestamp.tsr missing or empty.`

Produced by `scripts/generate-invalid-vectors.mjs` from
`valid/minimal-roundtrip/package.aep` by flipping three bytes
inside `timestamp.tsr` (offsets center, center+17, center+53),
mangling the ASN.1 structure enough that `pkijs.inspectTsa` can
no longer extract a usable RFC 3161 `TimeStampToken`.

The verifier's `inspectTsa` returns `tsaPresent: false` for the
mangled input, and the verifier rejects the package with the
"timestamp missing" diagnostic — semantically equivalent to
deleting the entry, but exercising the parser-robustness path.

A v0.1-conformant verifier MUST reject this package. It MAY
report a different diagnostic (e.g. "RFC 3161 SignerInfo signature
did not verify") if its parser is more permissive and reaches the
signature-verification step before failing; the conformance
contract only requires `verify=false`.
