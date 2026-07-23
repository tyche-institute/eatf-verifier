# The `.aep` package format (summary)

An Agent Evidence Package (`.aep`) is a ZIP archive that makes one recorded
agent action independently verifiable offline. Normative detail lives in the
JSON Schemas under `schemas/`; this page is an orientation summary derived from
the verifier behaviour.

## Entries

| Entry | Purpose |
|---|---|
| `canonical.bin` | Canonicalized payload bytes — the exact bytes that are hashed and signed |
| `hash.sha256` | SHA-256 digest of the canonical bytes |
| `signature.rsa` | RSA-4096 PKCS#1 v1.5 / SHA-256 signature over the canonical bytes |
| `signature.mldsa` | ML-DSA-65 (FIPS 204) signature (optional; present in hybrid packages) |
| `public_key(s)` | Verification keys for the signatures |
| `timestamp.tsr` | RFC 3161 timestamp token over the package hash (optional) |
| `metadata.json` | Package metadata: identifiers, claims, transport context |
| `overt_receipt.json` | OVERT receipt binding (optional) |

## Verification order

1. ZIP structure — required entries present.
2. Canonical bytes parse as a supported canonical form.
3. SHA-256(canonical) equals `hash.sha256`.
4. RSA signature verifies against the packaged public key.
5. ML-DSA-65 signature verifies (when present).
6. OVERT receipt fields check out (when present).
7. RFC 3161 token parses and its message imprint matches the package hash.

A package is `verify=true` only if every applicable check passes. The
`test-vectors/invalid/` tree exercises each failure mode as a negative control.
