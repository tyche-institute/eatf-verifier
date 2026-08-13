#!/usr/bin/env node
/**
 * Generate the profile-canonical valid conformance vector.
 *
 * Produces test-vectors/valid/profile-canonical/package.aep: an AEP
 * whose canonical.bin uses the profile canonical form of
 * docs/specs/aep-profile-v1.md §6 (response.txt + LF +
 * JCS(metadata.json)), so metadata.json sits under signature.sig and
 * the RFC 3161 timestamp. Every other shipped valid vector uses the
 * Java response-only form, in which the metadata is NOT signed; this
 * vector is the conformance evidence for the stronger binding.
 *
 * Requires the library to be built first:
 *
 *   (cd lib && npm install && npm run build)
 *   node scripts/generate-profile-canonical-vector.mjs
 *
 * Determinism note: created_at is fixed, the RFC 3161 token is reused
 * verbatim from valid-overt-profile/package.aep, RSASSA-PKCS1-v1_5 and
 * JCS are deterministic, and the signer pins every ZIP entry timestamp
 * (ZIP_ENTRY_MTIME in lib/src/signer.ts), so re-running the script
 * produces a byte-identical .aep. Run `git diff --quiet` after
 * regenerating to confirm no drift.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { createRequire } from "node:module";

// fflate is a dependency of lib/, not of the repo root; resolve it from
// lib/node_modules so this script runs from a clean checkout after
// `npm install` in lib/.
const require = createRequire(new URL("../lib/package.json", import.meta.url));
const { unzipSync } = require("fflate");

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const OUT_DIR = path.join(root, "test-vectors/valid/profile-canonical");
const TSR_SOURCE = path.join(
  root,
  "test-vectors/valid/valid-overt-profile/package.aep",
);

let sign, verify;
try {
  ({ sign, verify } = await import(
    new URL("../lib/dist/index.js", import.meta.url).href
  ));
} catch (e) {
  process.stderr.write(`\
generate-profile-canonical-vector: cannot load ../lib/dist/.
Run \`npm install && npm run build\` in lib/ first, then retry.
Underlying error: ${e?.message ?? e}
`);
  process.exit(2);
}

const payload =
  "EATF profile-canonical demo: metadata.json is signed alongside this response.\n";

const metadata = {
  schema: "urn:eatf:spec:aep:metadata:1.0",
  attestation_id: "att_profile_canonical_01",
  created_at: "2026-05-15T20:00:00Z",
  agent_id: "urn:eatf:tenant:demo:agent:profile-canonical-demo",
  action_type: "foundational:aep-response",
  policy_id: "atap-basic",
  policy_version: "1.0",
  policy_coverage: 1.0,
  policy_decision: "allow",
  format_version: "ATAP-1.0",
};

// Reuse the RFC 3161 token from the valid-overt-profile vector so the
// generation is fully offline (same approach as minimal-roundtrip).
const tsrSource = unzipSync(new Uint8Array(readFileSync(TSR_SOURCE)));
const timestampTsr = tsrSource["timestamp.tsr"];

const result = await sign({
  payload,
  privateKeyPem: readFileSync(path.join(root, "test-vectors/keys/dev-rsa-4096.key"), "utf8"),
  publicKeyPem: readFileSync(path.join(root, "test-vectors/keys/dev-rsa-4096.pem"), "utf8"),
  metadata,
  overtScope: "foundational:aep-response",
  timestampTsr,
  canonicalForm: "profile",
});

// Sanity: the package must verify AND report the profile form.
const check = await verify(result.aep, { tsaTrustList: [] });
if (!check.valid || check.canonicalForm !== "profile") {
  process.stderr.write(
    `generate-profile-canonical-vector: self-check failed ` +
      `(valid=${check.valid}, canonicalForm=${check.canonicalForm}): ${check.failureReason}\n`,
  );
  process.exit(1);
}

mkdirSync(OUT_DIR, { recursive: true });
writeFileSync(path.join(OUT_DIR, "package.aep"), Buffer.from(result.aep));
writeFileSync(path.join(OUT_DIR, "verify-expected.txt"), "verify=true\n");

process.stdout.write(`  ok  profile-canonical (canonical.bin SHA-256: ${result.canonicalHashHex})\n`);
process.stdout.write(`\nGenerated 1 valid vector under ${path.relative(root, OUT_DIR)}/.\n`);
