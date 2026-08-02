# `@eatf/verifier`

TypeScript library for creating and offline-verifying EATF Agent Evidence
Packages. The main entry runs in Node.js 20.19+; the verification-only
`@eatf/verifier/browser` entry runs in modern browsers through Web Crypto.

```ts
import { verify } from "@eatf/verifier";

const result = await verify(aepBytes, {
  trustedSignerPems: [expectedSignerPem],
  pqcPolicy: "required",
});
if (!result.valid) throw new Error(result.failureReason ?? "invalid AEP");
```

The verifier checks package structure, canonical bytes, SHA-256, an optional
caller-supplied signer-key trust set, RSA signatures, optional OVERT and
ML-DSA-65 bindings, and a strict RFC 3161 message imprint plus CMS signature.
See [`../docs/aep-format.md`](../docs/aep-format.md) for the ordered contract.

`verify()` never performs network I/O. If no `trustedSignerPems` are supplied,
the result says that signer identity trust was not evaluated. `tsaTrustList`
performs an advisory issuer-name pin only; it is not full RFC 5280 validation.

The same package exports the hybrid-capable reference `sign()` function used
by `eatf-sign`. The caller supplies a matching raw RFC 3161 response; the signer
will not package a mismatched or unverifiable timestamp. `prepareCanonical()`
returns the exact profile digest to send to a TSA; current signer output binds
both the payload and RFC 8785-canonical metadata. It also emits
`overt_receipt.sig`; a marker inside the signed metadata makes deleting or
bypassing that receipt signature a verification failure.
When an ML-DSA-65 keypair is supplied, the signer adds a FIPS 204 signature
over the same canonical bytes and an RFC 9881 SubjectPublicKeyInfo public key.

```bash
npm ci
npm run build
npm test
```

The tests include 34 unit/integration assertions and the shared AEP vectors.
Cross-language conformance is run through the repository-level toolkit test.

Apache-2.0; see [`../LICENSE`](../LICENSE).
