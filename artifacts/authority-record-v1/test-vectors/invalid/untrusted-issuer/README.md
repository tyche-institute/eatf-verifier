# `untrusted-issuer/`

**Expected:** `verify=false`, diagnostic
`RSA signature does not verify against public_key.pem.`

Produced by `scripts/generate-invalid-vectors.mjs` from
`valid/minimal-roundtrip/package.aep` by replacing `public_key.pem`
with a freshly-generated, unrelated RSA-4096 public key. The
embedded `signature.sig` was produced with the original (dev) key
and therefore does NOT verify against the swapped public key.

A v0.1-conformant verifier MUST refuse the package — even though
the swap key is itself a perfectly valid RSA key, it is not the
key that signed `canonical.bin`, so the signature check fails.

This vector exercises the same code path as `bad-signature-classical`
but for a different attacker model: instead of corrupting the
signature, the attacker tries to substitute their own public key
and have the relying party trust it. The verifier never trusts
embedded keys without a matching signature.
