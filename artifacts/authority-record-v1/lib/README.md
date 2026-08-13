# `@eatf/verifier` — offline TypeScript verifier for EATF Action Evidence Packages

Reference TypeScript implementation of the EATF offline verifier.
Runs in Node 20+ and in modern browsers via Web Crypto.

## What it does

Given an `.aep` evidence package, the verifier asserts:

1. **Envelope integrity** — well-formed ZIP with expected entries
   (manifest, records, attestations, signatures, timestamp, certs).
2. **Manifest canonicalisation** — re-canonicalises the manifest under
   RFC 8785 JCS and asserts byte-for-byte equality with the signed copy.
3. **Hash chain** — every record's SHA-256 matches the manifest's
   declared digest.
4. **Classical signature** — RSA-4096 (or ECDSA-P256) detached CMS
   signature against the issuer certificate.
5. **Post-quantum signature** — ML-DSA-65 (FIPS 204) when present.
6. **Issuer chain** — issuer certificate up to a configured trust
   anchor (RFC 5280).
7. **Timestamp** — RFC 3161 `TimeStampResp` against the TSA trust
   anchor; covers the manifest signature.
8. **Attestation** — W3C VC validation when `agent.vc.json` is present.

No network access required. Trust anchors are passed in by the caller.

## Modules

| File                  | Responsibility                                                                                |
|-----------------------|-----------------------------------------------------------------------------------------------|
| `src/canonical.ts`    | RFC 8785 JCS canonicalisation.                                                                |
| `src/hash.ts`         | SHA-256 wrapper around Web Crypto / Node `crypto`.                                            |
| `src/rsa.ts`          | RSA-PSS / PKCS#1 v1.5 signature verification, CMS parsing.                                    |
| `src/mldsa.ts`        | ML-DSA-65 (NIST FIPS 204) signature verification via `@noble/post-quantum`.                   |
| `src/tsa.ts`          | RFC 3161 `TimeStampResp` parser and verifier.                                                 |
| `src/tsa-trust-list.ts` | TSA trust-anchor list management.                                                            |
| `src/overt.ts`        | OVERT-inspired receipt validation.                                                            |
| `src/verifier.ts`     | Orchestrates the eight checks above and returns a structured `VerifyResult`.                  |
| `src/index.ts`        | Node entry point (uses Node `crypto` and filesystem).                                         |
| `src/browser.ts`      | Browser entry point (Web Crypto only; package input via `ArrayBuffer`).                       |

## Install

The package will be published to npm once the API stabilises. For now,
consume it from a clone of the repository:

```bash
git clone https://github.com/tyche-institute/eatf-verifier
cd eatf-verifier/artifacts/authority-record-v1/lib
npm install
npm run build
```

## Usage

### Node

```ts
import { verify } from "@eatf/verifier";
import { readFile } from "node:fs/promises";

const bytes = await readFile("./action.aep");
const result = await verify(bytes, { tsaTrustList: [] });

console.log(result.valid, result.failureReason);
```

### Browser

```ts
import { verify } from "@eatf/verifier/browser";

const file = inputElement.files[0];
const bytes = new Uint8Array(await file.arrayBuffer());

const result = await verify(bytes, { tsaTrustList: [/* PEM strings */] });
```

## Cryptographic suites supported

- **Classical:** RSA-4096 (default), ECDSA-P256.
- **Post-quantum:** ML-DSA-65 (NIST FIPS 204).
- **Hash:** SHA-256.
- **Canonicalisation:** RFC 8785 JCS for JSON; deterministic ZIP
  layout for the envelope.

## Tests

```bash
npm test
```

Runs the vitest suite under `test/`:

- RFC 8785 JCS canonicalisation conformance.
- RFC 3161 `TimeStampResp` parsing.
- TSA trust-list construction.
- OVERT-inspired receipt fixture validation against `../test-vectors/`.

## OVERT attribution and non-endorsement

OVERT is an open standard published by Glacis Technologies, Inc. (https://overt.is).
Tyche Institute and this package are independent of Glacis Technologies: there is no
affiliation, partnership, sponsorship, funding, certification, or endorsement in
either direction. The `overt_receipt.json` handling in `src/overt.ts` is
OVERT-inspired and is not claimed to be OVERT-conformant; it has not been reviewed,
certified, or approved by Glacis Technologies. The `OVERT_*` failure codes and the
receipt's `overt` and `witness.iap` field names are local wire-format and API
identifiers, not conformance claims.

## License

Apache License 2.0 — see [`../LICENSE`](../LICENSE).
