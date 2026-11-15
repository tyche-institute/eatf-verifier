# `bad-timestamp/`

**Expected:** `verify=false`, diagnostic
`timestamp.tsr is empty or not a readable RFC 3161 TimeStampResp or token.`

Derived by a scripted single-field mutation from
`valid/minimal-roundtrip/package.aep` by flipping three bytes
inside `timestamp.tsr` (offsets center, center+17, center+53),
mangling the ASN.1 structure enough that `pkijs.inspectTsa` can
no longer extract a usable RFC 3161 `TimeStampToken`.

The verifier's `inspectTsa` returns `tsaPresent: false` for the
mangled input, and the verifier rejects the package as an unreadable
timestamp. The entry is present (992 bytes); versions up to v0.7.3
reported it as "missing or empty".

A v0.1-conformant verifier MUST reject this package. It MAY
report a different diagnostic (e.g. "RFC 3161 SignerInfo signature
did not verify") if its parser is more permissive and reaches the
signature-verification step before failing; the conformance
contract only requires `verify=false`.
