# `missing-canonical-bin/`

**Expected:** `verify=false`, diagnostic
`Missing required entry: canonical.bin.`

Produced by `scripts/generate-invalid-vectors.mjs` from
`valid/minimal-roundtrip/package.aep` by deleting the
`canonical.bin` ZIP entry.

A v0.1-conformant verifier enumerates the required entries
(`response.txt`, `canonical.bin`, `hash.sha256`, `signature.sig`,
`public_key.pem`, `metadata.json`, `timestamp.tsr`) and rejects
the package before any cryptographic check runs when any of them
is absent. The diagnostic names which entry was missing.

This vector also serves as the canonical example of the
envelope-integrity failure class. Verifiers MAY also produce the
same diagnostic class for malformed ZIP envelopes — the first
test the verifier should do is "is this even a well-formed
package".
