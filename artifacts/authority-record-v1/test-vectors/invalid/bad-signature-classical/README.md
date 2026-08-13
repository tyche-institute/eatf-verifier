# `bad-signature-classical/`

**Expected:** `verify=false`, diagnostic
`RSA signature does not verify against public_key.pem.`

Produced by `scripts/generate-invalid-vectors.mjs` from
`valid/minimal-roundtrip/package.aep` by decoding `signature.sig`
from base64, flipping one byte near the middle, and re-encoding.
RSASSA-PKCS1-v1_5 verification then fails deterministically.

A v0.1-conformant verifier MUST validate the classical signature
in `signature.sig` against the embedded `public_key.pem` over the
bytes of `canonical.bin`, and reject when verification fails.
