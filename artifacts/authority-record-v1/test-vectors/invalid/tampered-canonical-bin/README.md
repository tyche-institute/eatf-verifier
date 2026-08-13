# `tampered-canonical-bin/`

**Expected:** `verify=false`, diagnostic `Hash mismatch.`

Produced by `scripts/generate-invalid-vectors.mjs` from
`valid/minimal-roundtrip/package.aep` by flipping a single byte at
offset 0 of `canonical.bin`. The SHA-256 in `hash.sha256` therefore
no longer matches `SHA-256(canonical.bin)`.

A v0.1-conformant verifier MUST detect the mismatch during the
hash-chain step (verifier.ts step 4) and reject the package with a
`Hash mismatch.` diagnostic. Cryptographic signature checks are NOT
required to fire — the hash check guards everything downstream.
