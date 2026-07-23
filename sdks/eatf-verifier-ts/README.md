# `@eatf/verifier`

[![EATF](https://img.shields.io/badge/EATF-trust%20service-orange)](https://eatf.eu)
[![Spec](https://img.shields.io/badge/spec-urn%3Aeatf%3Aspec%3Aaep%3A1.0-lightgrey)](../../docs/specs/aep-profile-v1.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Offline TypeScript verifier for EATF `.aep` evidence packages.**

Runs in the browser via Web Crypto and in Node 20+. No backend call,
no telemetry, no API key. Drop a `.aep` file in, get a structured
verification result. The recommended way to verify an EATF evidence
package locally, with no server round-trip.

> **Status:** v0.1.0-alpha. Phase 1 step 1.20 of the
> [EATF roadmap](../../docs/specs/aep-profile-v1.md). Hash + canonical
> + RSA-4096 verification are production-shape. ML-DSA-65 verification
> uses `@noble/post-quantum`. RFC 3161 verification is **structural
> only in v0.1** (message-imprint match); full TSA-signature
> verification arrives in v0.2 with a pinned trust list.

---

## Why exists

The Java reference verifier at
the AEP profile specification
is the canonical implementation. It ships as a shaded JAR for
auditors and is the authoritative source of truth per
[`docs/specs/aep-profile-v1.md`](../../docs/specs/aep-profile-v1.md)
§12.

A TypeScript port lets:

- **Browsers** verify a package fully locally
  locally, with no server round-trip.
- **Node services** verify without bundling a JVM.
- **Air-gapped reviews** — every byte of the dependency tree is open
  source.

## Install

```bash
npm install @eatf/verifier
# or
pnpm add @eatf/verifier
```

## Use — in the browser

```ts
import { verify } from "@eatf/verifier/browser";

const file: File = /* from a drag-and-drop event */;
const result = await verify(file);

if (result.valid) {
  // result.report : string[]   — human-readable per-step log
  // result.pqcValid : boolean? — ML-DSA-65 result if PQC entries present
  // result.metadata : object   — parsed metadata.json
} else {
  console.error(result.failureReason, result.report);
}
```

## Use — in Node 20+

```ts
import { verify } from "@eatf/verifier";
import { readFile } from "node:fs/promises";

const bytes = await readFile("./sample.aep");
const result = await verify(bytes);
console.log(JSON.stringify(result, null, 2));
```

## What gets checked

1. **ZIP structure** — package opens, required entries present.
2. **Canonical bytes** — `canonical.bin` matches a supported Java/AEP
   canonical form.
3. **SHA-256** of canonical bytes matches `hash.sha256`.
4. **RSA-4096 PKCS#1 v1.5 / SHA-256** signature verifies against
   `public_key.pem`.
5. **ML-DSA-65** signature verifies against `pqc_public_key.pem`
   (when PQC entries are present in the package).
6. **OVERT receipt** — when `overt_receipt.json` is present, its profile,
   scope, content hash, metadata-bound fields, and witness file refs are
   checked.
7. **RFC 3161** — token present and parses as ASN.1. Message-imprint mismatch
   is reported but accepted for Java-reference compatibility.

What does **not** get checked in v0.1:

- Full RFC 3161 TSA signature verification (no trust list shipped).
- Trust chain back to the EATF public-key history mirror.
- C2PA-style chain semantics across multiple linked packages.

These land in v0.2 alongside the
[`public-key-mirror`](../../docs/specs/public-key-mirror.md) trust
list and a pinned set of TSA certificates.

## Result shape

```ts
type VerifyResult = {
  valid: boolean;
  report: string[];
  failureReason: string | null;
  pqcValid: boolean | null;          // null when PQC entries absent
  metadata: Record<string, unknown> | null;
  overtReceipt: Record<string, unknown> | null;
};
```

## Bundle size

| Mode | Approx size (gzip) | Notes |
|---|---|---|
| RSA-only (no PQC entries) | ~12 kB | `fflate` + Web Crypto + canonicaliser |
| With ML-DSA-65 | ~85 kB | `@noble/post-quantum` is lazy-imported |

## Reference implementation

The Java verifier in this repository is the source of truth. When the
TypeScript implementation disagrees, the Java one wins until proven
otherwise — `report` always cites the package layout precisely so the
discrepancy is debuggable.

Test vectors at `backend/src/test/resources/fixtures/` are shared
between Java and TS implementations. v0.1 passes the smoke vectors;
v0.2 will pass the full forward-compat and tampered suites.

## License

MIT. Verification is free forever; we charge only for operating the
trust service that mints these packages. See
[`https://eatf.eu/pricing`](https://eatf.eu/pricing).
