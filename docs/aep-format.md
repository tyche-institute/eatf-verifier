# The `.aep` package format (summary)

An Agent Evidence Package (`.aep`) is a ZIP archive that makes one recorded
agent action independently verifiable offline. The normative source of truth is
the verifier implementations (`lib/`, `lib-python/`) and the JSON Schemas under
`schemas/`; this page is an orientation summary derived from the verifier
behaviour.

## Entries

Required entries (a package missing any of these is rejected with
`Missing required entry: <name>.`):

| Entry | Purpose |
|---|---|
| `response.txt` | The recorded payload (response) bytes |
| `canonical.bin` | Canonicalized payload bytes — the exact bytes that are hashed and signed |
| `hash.sha256` | Lowercase hex SHA-256 digest of `canonical.bin` |
| `signature.sig` | Base64 RSA-4096 (PKCS#1 v1.5 / SHA-256) signature over the canonical bytes |
| `public_key.pem` | RSA verification key (PEM) |
| `metadata.json` | Package metadata: identifiers, claims, policy and transport context |
| `timestamp.tsr` | Base64 RFC 3161 timestamp token (checked structurally; see below) |

Optional entries:

| Entry | Purpose |
|---|---|
| `signature_pqc.sig` + `pqc_public_key.pem` | ML-DSA-65 (FIPS 204) hybrid signature over the same canonical bytes, plus its verification key; both must be present together |
| `overt_receipt.json` | OVERT receipt binding (profile, scope, content hash, metadata-bound fields) |

## Verification order

1. ZIP opens and parses.
2. All required entries present.
3. `metadata.json` parses.
4. Canonical-form match: `canonical.bin` must equal either the profile form
   recomputed from `response.txt` + `metadata.json`, or `response.txt` itself
   (the response-only form). Once a form is accepted, the embedded
   `canonical.bin` bytes are the single authority for hashing and signing
   (the *hash-view rule*).
5. SHA-256(`canonical.bin`) equals `hash.sha256`.
6. RSA signature verifies against `public_key.pem` (with a DigestInfo
   compatibility fallback; see verifier source).
7. OVERT receipt fields check out (when `overt_receipt.json` is present).
8. ML-DSA-65 signature verifies (when the PQC pair is present).
9. RFC 3161 token parses; its message imprint is compared against the package
   hash and reported, but an imprint mismatch is accepted for compatibility with
   the historical reference producer (structural check, not full RFC 3161
   validation). The TSA trust result is informational.

A package is `verify=true` only if every applicable decisive check passes. The
`test-vectors/invalid/` tree (7 vectors) exercises failure modes as negative
controls; `test-vectors/valid/` ships 4 accepted packages. Each vector directory
carries a `verify-expected.txt` generated from the actual Python verifier
output.
