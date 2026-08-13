#!/usr/bin/env node
/**
 * Generate the boundary behavioural test vectors.
 *
 * Unlike test-vectors/valid/ and test-vectors/invalid/, these vectors
 * pin the verifier's per-check BoundaryReport (VerifyResult.boundary,
 * schemas/boundary-report-v1.schema.json), not just the verify=true/false
 * contract — several of them verify VALID on purpose: what they freeze
 * is which checks failed without gating, which were never assessed, and
 * which fields sat outside the signature while the package passed.
 *
 *   - boundary-suppressed-tsa            (tsaTrustList: [] => chain check option_disabled)
 *   - response-only-unsigned-policy-tamper (deny->allow flip in BOTH unsigned
 *                                         files of a response-only package; still verifies)
 *   - advisory-fail-imprint              (imprint check fails, enforced=false, valid stays true)
 *   - short-circuit-shadow               (hash.sha256 corrupted; registry tail short_circuited)
 *   - claimed-surface-overclaim          (claimed_assessment_surface injected post-signing)
 *   - not-determinate-imprint-alg        (imprint hash OID flipped to SHA-512; check not determinate)
 *
 * Run from the repo root:
 *
 *   node scripts/generate-boundary-vectors.mjs
 *
 * Each vector ships package.aep, verify-expected.txt, and an
 * expected-boundary.json consumed by lib/test/boundary-vectors.test.ts
 * (which options to verify with, and the boundary rows to pin).
 *
 * Determinism note: mutations are fixed string/byte substitutions on
 * committed baselines, and every re-zip is stamped with the pinned
 * ZIP_ENTRY_MTIME, so re-running the script produces byte-identical
 * .aep files. Run `git diff --quiet` after regenerating to confirm.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { createRequire } from "node:module";

// fflate is a dependency of lib/, not of the repo root; resolve it from
// lib/node_modules so this script runs from a clean checkout after
// `npm install` in lib/.
const require = createRequire(new URL("../lib/package.json", import.meta.url));
const { unzipSync, zipSync, strFromU8, strToU8 } = require("fflate");

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const OUT_DIR = path.join(root, "test-vectors/boundary");

// Fixed timestamp stamped on every ZIP entry so regeneration is
// byte-identical across hosts. Must match lib/src/signer.ts's
// ZIP_ENTRY_MTIME (see that file for why 1980-01-02, local fields).
const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);

function loadVector(name) {
  const bytes = new Uint8Array(
    readFileSync(path.join(root, `test-vectors/valid/${name}/package.aep`)),
  );
  return { bytes, entries: unzipSync(bytes) };
}

function rezip(entries) {
  return zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME });
}

function writeVector(name, packageBytes, verifyExpectedLines, expectedBoundary) {
  const dir = path.join(OUT_DIR, name);
  mkdirSync(dir, { recursive: true });
  writeFileSync(path.join(dir, "package.aep"), Buffer.from(packageBytes));
  writeFileSync(
    path.join(dir, "verify-expected.txt"),
    verifyExpectedLines.join("\n") + "\n",
  );
  writeFileSync(
    path.join(dir, "expected-boundary.json"),
    JSON.stringify(expectedBoundary, null, 2) + "\n",
  );
  process.stdout.write(`  ok  ${name}\n`);
}

// 1. boundary-suppressed-tsa: byte-identical copy of mcp-tools-call-valid,
//    verified with tsaTrustList: []. The package is unremarkable; what
//    the vector freezes is that disabling the trust list must surface as
//    not_assessed/option_disabled in the boundary rather than silently
//    dropping the check.
{
  const { bytes } = loadVector("mcp-tools-call-valid");
  writeVector("boundary-suppressed-tsa", bytes, ["verify=true"], {
    description:
      "Copy of valid/mcp-tools-call-valid verified with an empty tsaTrustList; the suppressed chain-to-root check must be visible in the boundary as option_disabled.",
    options: { tsaTrustList: [] },
    expect: {
      valid: true,
      canonicalForm: "response-only",
      checks: {
        "tsa-chain-to-root": { verdict: "not_assessed", enforced: false, reason: "option_disabled" },
      },
    },
  });
}

// 2. response-only-unsigned-policy-tamper: take the denied-payment
//    package and flip policy_decision deny->allow in BOTH unsigned
//    files (metadata.json and overt_receipt.json). The response-only
//    canonical form signs neither, and the OVERT cross-check only
//    compares the two files to each other, so the package still
//    verifies — with the flipped fields listed in unsignedFields.
{
  const { entries } = loadVector("mcp-tools-call-denied-policy");
  const mutated = { ...entries };
  const metadata = JSON.parse(strFromU8(mutated["metadata.json"]));
  if (metadata.policy_decision !== "deny") {
    throw new Error("baseline mcp-tools-call-denied-policy no longer carries policy_decision=deny");
  }
  metadata.policy_decision = "allow";
  mutated["metadata.json"] = strToU8(JSON.stringify(metadata) + "\n");
  const receipt = JSON.parse(strFromU8(mutated["overt_receipt.json"]));
  if (receipt.policy?.decision !== "deny") {
    throw new Error("baseline receipt no longer carries policy.decision=deny");
  }
  receipt.policy.decision = "allow";
  mutated["overt_receipt.json"] = strToU8(JSON.stringify(receipt) + "\n");
  writeVector("response-only-unsigned-policy-tamper", rezip(mutated), ["verify=true"], {
    description:
      "valid/mcp-tools-call-denied-policy with policy_decision flipped deny->allow in metadata.json AND overt_receipt.json after signing. Both files lie outside the response-only signature, so verification still succeeds; only the boundary's unsignedFields reveals that the policy decision was rewritable.",
    options: { tsaTrustList: [] },
    expect: {
      valid: true,
      canonicalForm: "response-only",
      metadata: { policy_decision: "allow" },
      checks: {
        "canonical-profile": { verdict: "fail", enforced: false },
        "canonical-response-only": { verdict: "pass", enforced: true },
        "overt-receipt": { verdict: "pass", enforced: true },
      },
      unsignedFieldsInclude: [
        "metadata.policy_decision",
        "metadata.policy_id",
        "metadata.policy_version",
      ],
    },
  });
}

// 3. advisory-fail-imprint: byte-identical copy of minimal-roundtrip
//    under default options. Its timestamp token was issued over a
//    different hash (the round-trip flow reuses older tokens), so the
//    message-imprint check FAILS while the package verifies: the
//    "assessed, failed, accepted anyway" specimen, frozen.
{
  const { bytes } = loadVector("minimal-roundtrip");
  writeVector("advisory-fail-imprint", bytes, ["verify=true"], {
    description:
      "Copy of valid/minimal-roundtrip under default options. The embedded RFC 3161 token covers a different hash, so tsa-imprint is verdict=fail — and enforced=false, because the verifier accepts the mismatch for Java reference compatibility. valid stays true.",
    expect: {
      valid: true,
      canonicalForm: "response-only",
      checks: {
        "tsa-imprint": { verdict: "fail", enforced: false },
        "tsa-signerinfo": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
        "tsa-chain-to-root": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
      },
    },
  });
}

// 4. short-circuit-shadow: corrupt hash.sha256 (first hex digit
//    swapped) so verification fails mid-pipeline; every check behind
//    the hash comparison must be emitted as not_assessed with reason
//    short_circuited — the evidence the failure destroyed, made
//    visible.
{
  const { entries } = loadVector("minimal-roundtrip");
  const mutated = { ...entries };
  const hashText = strFromU8(mutated["hash.sha256"]);
  const swapped = (hashText[0] === "0" ? "1" : "0") + hashText.slice(1);
  mutated["hash.sha256"] = strToU8(swapped);
  writeVector("short-circuit-shadow", rezip(mutated), [
    "verify=false",
    "diagnostic=Hash mismatch.",
  ], {
    description:
      "valid/minimal-roundtrip with the first hex digit of hash.sha256 swapped. Fails at hash-sha256; the boundary must list rsa-signature through tsa-chain-to-root as not_assessed/short_circuited.",
    options: { tsaTrustList: [] },
    expect: {
      valid: false,
      canonicalForm: "response-only",
      checks: {
        "hash-sha256": { verdict: "fail", enforced: true },
        "rsa-signature": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
        "rsa-digestinfo-fallback": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
        "overt-receipt": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
        "pqc-mldsa65": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
        "tsa-present": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
        "tsa-imprint": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
        "tsa-signerinfo": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
        "tsa-chain-to-root": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
      },
    },
  });
}

// 5. claimed-surface-overclaim: inject a claimed_assessment_surface
//    into metadata.json AFTER signing (possible precisely because the
//    response-only form leaves metadata unsigned). The claim names two
//    checks this run never assesses plus one id that does not exist;
//    the boundary's claimed-vs-computed diff must expose all three.
{
  const { entries } = loadVector("minimal-roundtrip");
  const mutated = { ...entries };
  const metadata = JSON.parse(strFromU8(mutated["metadata.json"]));
  metadata.claimed_assessment_surface = ["tsa-chain-to-root", "pqc-mldsa65", "not-a-real-check"];
  mutated["metadata.json"] = strToU8(JSON.stringify(metadata) + "\n");
  writeVector("claimed-surface-overclaim", rezip(mutated), ["verify=true"], {
    description:
      "valid/minimal-roundtrip with claimed_assessment_surface injected into metadata.json post-signing, claiming two checks the run never assesses (pqc-mldsa65, tsa-chain-to-root under an empty trust list) and one unknown id. claimedSurface must report the overclaim — and, the claim being unsigned in this form, unsignedFields must list it too.",
    options: { tsaTrustList: [] },
    expect: {
      valid: true,
      canonicalForm: "response-only",
      claimedSurface: {
        claimed: ["not-a-real-check", "pqc-mldsa65", "tsa-chain-to-root"],
        unrecognized: ["not-a-real-check"],
        notAssessed: ["pqc-mldsa65", "tsa-chain-to-root"],
      },
      unsignedFieldsInclude: ["metadata.claimed_assessment_surface"],
    },
  });
}

// 6. not-determinate-imprint-alg: flip the messageImprint hash
//    algorithm OID inside the TSTInfo from SHA-256
//    (2.16.840.1.101.3.4.2.1) to SHA-512 (...2.3). The verifier only
//    compares SHA-256 imprints, so the check ends not_determinate with
//    reason capability_absent. The shipped tokens carry no embedded
//    certificate, so no SignerInfo signature constrains the edit.
//    (The memo planned a cert-stripping "not-determinate-tsa-cert"
//    vector; every shipped token already lacks a cert, so the
//    certificate-absence case is pinned by advisory-fail-imprint and
//    this vector pins the OTHER not_determinate path instead.)
{
  const { entries } = loadVector("minimal-roundtrip");
  const mutated = { ...entries };
  const tsrText = strFromU8(mutated["timestamp.tsr"]);
  const trailing = tsrText.slice(tsrText.trimEnd().length);
  const der = Buffer.from(tsrText.trim(), "base64");
  // The messageImprint AlgorithmIdentifier is the unique occurrence of
  // the SHA-256 OID immediately followed by the 32-byte OCTET STRING
  // header (04 20); the other occurrences (digestAlgorithms, signed
  // attributes) are followed by different tags.
  const pattern = Buffer.from([0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01, 0x04, 0x20]);
  const hits = [];
  for (let i = der.indexOf(pattern); i !== -1; i = der.indexOf(pattern, i + 1)) hits.push(i);
  if (hits.length !== 1) {
    throw new Error(`expected exactly one messageImprint OID occurrence, found ${hits.length}`);
  }
  der[hits[0] + 10] = 0x03; // last OID arc 1 -> 3: SHA-256 -> SHA-512
  mutated["timestamp.tsr"] = strToU8(der.toString("base64") + trailing);
  writeVector("not-determinate-imprint-alg", rezip(mutated), ["verify=true"], {
    description:
      "valid/minimal-roundtrip with the TSTInfo messageImprint hash algorithm OID flipped to SHA-512. The verifier can only evaluate SHA-256 imprints, so tsa-imprint is not_determinate/capability_absent; the package still verifies.",
    options: { tsaTrustList: [] },
    expect: {
      valid: true,
      canonicalForm: "response-only",
      checks: {
        "tsa-present": { verdict: "pass", enforced: true },
        "tsa-imprint": { verdict: "not_determinate", enforced: false, reason: "capability_absent" },
      },
    },
  });
}

process.stdout.write(`\nGenerated ${6} boundary vectors under ${path.relative(root, OUT_DIR)}/.\n`);
