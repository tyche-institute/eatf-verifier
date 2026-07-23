# `@eatf/verifier` — offline TypeScript verifier for EATF Agent Evidence Packages

Reference TypeScript implementation of the EATF offline verifier.
Runs in Node 20+ and in modern browsers via Web Crypto.

## What it does

Given an `.aep` evidence package (a ZIP archive; see
[`../docs/aep-format.md`](../docs/aep-format.md)), the verifier asserts:

1. **Package structure** — the archive opens and every required entry is
   present (`response.txt`, `canonical.bin`, `hash.sha256`, `signature.sig`,
   `public_key.pem`, `metadata.json`, `timestamp.tsr`).
2. **Metadata** — `metadata.json` parses.
3. **Canonical form** — `canonical.bin` equals either the profile form
   recomputed from `response.txt` + `metadata.json`, or `response.txt` itself
   (response-only form). The embedded bytes are then the single authority for
   hashing and signing (the *hash-view rule*).
4. **Hash** — SHA-256 of `canonical.bin` equals `hash.sha256`.
5. **Classical signature** — RSA-4096 (PKCS#1 v1.5 / SHA-256) over the
   canonical bytes against `public_key.pem`, with a DigestInfo-encoding
   compatibility fallback.
6. **OVERT receipt** — when `overt_receipt.json` is present, its profile,
   scope, content hash, and metadata-bound fields are cross-checked.
7. **Post-quantum signature** — ML-DSA-65 (FIPS 204) over the same canonical
   bytes when the `signature_pqc.sig` + `pqc_public_key.pem` pair is present
   (reported in `pqcValid`).
8. **Timestamp (structural)** — the RFC 3161 token parses; its message imprint
   is compared and reported, but an imprint mismatch is accepted for
   compatibility with the historical reference producer, and the TSA
   trust result (`tsaTrusted`) is informational. This is deliberately **not**
   full RFC 3161 validation.

No network access, account, or API key is required. TSA trust anchors, when
used, are passed in by the caller.

## Modules

| File | Responsibility |
|---|---|
| `src/canonical.ts` | Canonical-form reconstruction and matching. |
| `src/hash.ts` | SHA-256 wrapper around Web Crypto / Node `crypto`. |
| `src/rsa.ts` | RSA PKCS#1 v1.5 verification incl. DigestInfo fallback. |
| `src/mldsa.ts` | ML-DSA-65 (FIPS 204) verification via `@noble/post-quantum`. |
| `src/tsa.ts` | RFC 3161 token parsing and structural checks. |
| `src/tsa-trust-list.ts` | TSA trust-anchor list handling (informational result). |
| `src/overt.ts` | OVERT receipt validation. |
| `src/signer.ts` | Test/reference signer used to mint fixture packages (RSA-only). |
| `src/verifier.ts` | Orchestrates the checks above; returns a structured `VerifyResult`. |
| `src/index.ts` | Node entry point. |
| `src/browser.ts` | Browser entry point (Web Crypto; input via `ArrayBuffer`). |

## Install

Consume it from a clone of the repository:

```bash
git clone https://github.com/tyche-institute/eatf-verifier
cd eatf-verifier/lib
npm ci
npm run build
```

## Usage

### Node

```ts
import { verify } from "@eatf/verifier";
import { readFile } from "node:fs/promises";

const bytes = await readFile("./package.aep");
const result = await verify(bytes);

console.log(result.valid, result.failureReason);
```

### Browser

```ts
import { verify } from "@eatf/verifier/browser";

const file = inputElement.files[0];
const bytes = new Uint8Array(await file.arrayBuffer());
const result = await verify(bytes);
```

## Cryptographic suite

- **Classical:** RSA-4096, PKCS#1 v1.5 / SHA-256.
- **Post-quantum (optional):** ML-DSA-65 (NIST FIPS 204).
- **Hash:** SHA-256.

## Tests

```bash
npm test
```

Runs the vitest suite under `test/`: canonical/OVERT fixture validation against
`../test-vectors/`, RFC 3161 parsing, and TSA trust-list construction. The
cross-implementation contract is that this library and the Python port
(`../lib-python`) agree on the verify verdict for every conformance vector.

## License

Apache License 2.0 — see [`../LICENSE`](../LICENSE).
