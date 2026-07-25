# Implemented `.aep` package format

An Agent Evidence Package is a ZIP archive for one recorded agent action. This
page documents version 0.2.0 behavior. The schemas, source, and shared vectors
are the executable contract; the project does not claim that this summary is an
external standard.

## Entries

| Entry | Status | Meaning |
|---|---|---|
| `response.txt` | required | Recorded payload bytes |
| `canonical.bin` | required | Exact bytes hashed and signed |
| `hash.sha256` | required | Lowercase SHA-256 hex of `canonical.bin` |
| `signature.sig` | required | Base64 RSA PKCS#1 v1.5/SHA-256 signature |
| `public_key.pem` | required | Embedded RSA SPKI verification key |
| `metadata.json` | required | Package metadata JSON object |
| `timestamp.tsr` | required | Base64 RFC 3161 `TimeStampResp` or bare token |
| `overt_receipt.json` | optional | OVERT receipt bound to hash and metadata |
| `overt_receipt.sig` | conditional | RSA/SHA-256 signature over exact receipt bytes; required when named by signed metadata |
| `signature_pqc.sig` | paired optional | Base64 ML-DSA-65 signature |
| `pqc_public_key.pem` | paired optional | ML-DSA-65 verification key |

## Ordered verification

1. Parse ZIP and require all required entries.
2. Parse `metadata.json` as an object.
3. Reconstruct the current profile form
   `response.txt || LF || RFC8785-JCS(metadata)`. Current writers MUST use
   this form. For read-only compatibility, verifiers also recognize the
   early response-only form and explicitly report that its metadata is not
   signature-bound. `canonical.bin` must equal one of these forms.
4. Require SHA-256(`canonical.bin`) to equal `hash.sha256`.
5. If the caller supplied trusted signer PEMs, require `public_key.pem` to
   match one exactly. Without this option, signer identity is explicitly
   reported as not evaluated.
6. Verify `signature.sig` over `canonical.bin`.
7. If present, validate the OVERT profile, scope, content hash, and
   metadata-bound fields. When signed metadata contains
   `overt_receipt_signature: "overt_receipt.sig"`, require that entry and
   verify its RSA signature over the exact `overt_receipt.json` bytes.
   Receipt signatures without the signed marker are rejected to prevent
   downgrade. Older receipts without either field remain readable and are
   explicitly reported as not separately signature-bound.
8. If the ML-DSA pair is present, verify it over the same canonical bytes.
9. Decode the RFC 3161 object, require SHA-256 as the imprint algorithm,
   require the imprint to equal `hash.sha256`, and verify the CMS SignerInfo
   against the embedded TSA signing certificate.
10. If caller-supplied TSA certificates are present, report the advisory
    issuer-name comparison.

A failure in steps 1–9 returns `valid=false`. Step 10 is informational because
version 0.2.0 does not implement RFC 5280 chain construction, certificate
policy, revocation, or qualified-trust-service evaluation.

## Trust interpretation

A package can be internally consistent yet signed by an unknown key. Therefore:

- `valid=true` without a signer trust set means integrity and proof of control
  of the embedded key, not verified organizational identity;
- `valid=true` with a matching signer trust set additionally proves that the
  embedded key is one the caller selected out of band;
- timestamp CMS verification proves internal token integrity, while external
  TSA identity assurance remains deployment policy.

The distinction is surfaced in reports and examples.

## Canonicalization domain

The TypeScript and Python implementations use independent maintained RFC 8785
libraries and share boundary tests for number formatting and UTF-16 member
ordering. To keep parsed JSON behavior identical across the two languages, the
AEP metadata profile rejects integer-valued numbers outside
`[-9007199254740991, 9007199254740991]`, non-finite values, unsupported JSON
types, circular values, and unpaired Unicode surrogates.
