# Shared AEP conformance vectors

Every implementation claiming compatibility with this repository must accept
all packages under `valid/` and reject all packages under `invalid/`.
Diagnostic wording may differ; the boolean verdict is the contract.

| Vector | Expected | Target |
|---|---:|---|
| `valid/valid-overt-profile` | true | Foundational OVERT profile |
| `valid/mcp-tools-call-valid` | true | MCP call with allow decision |
| `valid/mcp-tools-call-denied-policy` | true | Authentic evidence of a deny decision |
| `valid/minimal-roundtrip` | true | Current signer-to-verifier workflow |
| `valid/hybrid-mldsa65` | true | RFC 9881 ML-DSA-65 + RSA hybrid package |
| `invalid/tampered-canonical-bin` | false | Canonical bytes changed |
| `invalid/tampered-metadata` | false | Metadata/receipt binding changed |
| `invalid/bad-signature-classical` | false | RSA signature changed |
| `invalid/bad-signature-pqc` | false | ML-DSA-65 signature changed |
| `invalid/untrusted-issuer` | false | Embedded key does not verify signature |
| `invalid/missing-canonical-bin` | false | Required entry absent |
| `invalid/bad-timestamp` | false | RFC 3161 object malformed |
| `invalid/tampered-overt-receipt` | false | Receipt/hash binding changed |

All non-timestamp-fault vectors carry an RFC 3161 message imprint matching
their recorded `hash.sha256` plus a verifiable embedded TEST TSA certificate.
Regenerate those tokens with:

```bash
python3 scripts/regenerate-test-timestamps.py
```

RFC 3161 generation time and serial number make regenerated package bytes
different, while the verification contract remains the same.

```bash
eatf-verify --conformance test-vectors
eatf-verify-py --conformance test-vectors
```

Expected from each: `5 verified, 8 rejected, 0 contract mismatches`.
