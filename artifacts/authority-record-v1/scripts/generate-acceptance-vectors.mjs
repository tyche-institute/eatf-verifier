#!/usr/bin/env node
/**
 * Generate the accepting-authority negative vectors (spec §4.3).
 *
 * Until this run the epistemic acceptance layer had no negative family of
 * its own: the five §4.3 packages in the corpus lived under
 * `test-vectors/voiding/`, and every one of them verified `valid: true`
 * because all four §4.3 checks were advisory. Two of the four now GATE
 * (`accepting-authority-binding`, `accepting-authority-key-binding`), so the
 * layer needs the same isolated adversaries the §4.5 mandate layer has —
 * one property broken per vector, so a failure names one check:
 *
 *   acceptance/acceptance-signature-forged      (record intact, signature belongs to other bytes)
 *   acceptance/acceptance-stripped              (entries removed; the digest reference stays)
 *   acceptance/acceptance-digest-mismatch       (an authentic acceptance of DIFFERENT bytes)
 *   acceptance/acceptance-principal-substitution (an authentic acceptance by a DIFFERENT principal)
 *
 * All four are rejected. The two adversaries that do NOT reject are already
 * frozen elsewhere and stay there, because they are the enforced/advisory
 * line and it is worth being able to point at them:
 *
 *   voiding/expired-acceptance          temporal containment fails, `valid: true`
 *   voiding/authority-key-substitution  role fails against a caller trust list, `valid: true`
 *
 * The acceptance is signed by the committed `test-accepting-authority`
 * keypair — a TEST principal, distinct from the package issuer
 * (`dev-rsa-4096`) and from the granting authority of §4.5
 * (`test-granting-authority`). Who accepts in production, and under what
 * custody, is a governance question out of scope for these fixtures
 * (see test-vectors/keys/README.md).
 *
 * Requires the library to be built first:
 *
 *   (cd lib && npm install && npm run build)
 *   node scripts/generate-acceptance-vectors.mjs
 *
 * Each vector ships package.aep, verify-expected.txt, and an
 * expected-acceptance.json consumed by lib/test/acceptance-vectors.test.ts.
 * The script re-verifies every package before writing it.
 *
 * Determinism: accepted_at / created_at fixed, the RFC 3161 token reused
 * verbatim from valid-overt-profile/package.aep (genTime 2026-01-01),
 * RSASSA-PKCS1-v1_5 and JCS deterministic, every ZIP entry timestamp
 * pinned. Two runs produce byte-identical .aep files; `git diff --quiet
 * test-vectors/` after regenerating confirms no drift.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createSign } from "node:crypto";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(new URL("../lib/package.json", import.meta.url));
const { unzipSync, zipSync } = require("fflate");

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const ACCEPTANCE_OUT = path.join(root, "test-vectors/acceptance");
const KEYS_DIR = path.join(root, "test-vectors/keys");
const TSR_SOURCE = path.join(root, "test-vectors/valid/valid-overt-profile/package.aep");

const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);

let sign, verify, jcs;
try {
  ({ sign, verify } = await import(new URL("../lib/dist/index.js", import.meta.url).href));
  ({ jcs } = await import(new URL("../lib/dist/canonical.js", import.meta.url).href));
} catch (e) {
  process.stderr.write(`\
generate-acceptance-vectors: cannot load ../lib/dist/.
Run \`npm install && npm run build\` in lib/ first, then retry.
Underlying error: ${e?.message ?? e}
`);
  process.exit(2);
}

const devPrivate = readFileSync(path.join(KEYS_DIR, "dev-rsa-4096.key"), "utf8");
const devPublic = readFileSync(path.join(KEYS_DIR, "dev-rsa-4096.pem"), "utf8");
const authorityPrivate = readFileSync(path.join(KEYS_DIR, "test-accepting-authority.key"), "utf8");
const authorityPublic = readFileSync(path.join(KEYS_DIR, "test-accepting-authority.pem"), "utf8");

const timestampTsr = unzipSync(new Uint8Array(readFileSync(TSR_SOURCE)))["timestamp.tsr"];

const baseMetadata = {
  schema: "urn:eatf:spec:aep:metadata:1.0",
  attestation_id: "att_acceptance_negative_01",
  created_at: "2026-08-13T00:00:00Z",
  agent_id: "urn:eatf:tenant:demo:agent:acceptance-demo",
  action_type: "foundational:aep-response",
  policy_id: "atap-basic",
  policy_version: "1.0",
  policy_coverage: 1.0,
  policy_decision: "allow",
  format_version: "ATAP-1.0",
};

/** The signed metadata block naming the epistemic accepting authority. */
const ACCEPTING_AUTHORITY = {
  principal: "test-accepting-authority",
  policy_id: "atap-basic",
  policy_version: "1.0",
  validity: { not_before: "2025-07-01T00:00:00Z", not_after: "2026-07-01T00:00:00Z" },
};

/** Build a detached acceptance {json, sig}: the authority signs JCS(record). */
function makeAcceptance(recordOverrides = {}, signWithKey = authorityPrivate, publicKey = authorityPublic) {
  const record = {
    principal: "test-accepting-authority",
    policy_id: "atap-basic",
    policy_version: "1.0",
    accepted_at: "2026-08-13T00:00:00Z",
    public_key: publicKey,
    ...recordOverrides,
  };
  const signer = createSign("sha256");
  signer.update(jcs(record));
  signer.end();
  return { json: record, sig: signer.sign(signWithKey).toString("base64") };
}

async function signPackage({
  metadata = baseMetadata,
  acceptingAuthority = ACCEPTING_AUTHORITY,
  acceptance,
  canonicalForm = "profile",
} = {}) {
  const result = await sign({
    payload: "EATF acceptance demo: this output carries a named authority's signed acceptance.\n",
    privateKeyPem: devPrivate,
    publicKeyPem: devPublic,
    metadata,
    overtScope: "foundational:aep-response",
    timestampTsr,
    canonicalForm,
    acceptingAuthority,
    acceptance,
  });
  return result.aep;
}

async function writeVector(dir, name, packageBytes, verifyExpectedLines, expected) {
  const result = await verify(packageBytes, expected.options ?? {});
  if (result.valid !== expected.expect.valid) {
    throw new Error(
      `${name}: self-check failed (valid=${result.valid}, expected ${expected.expect.valid}): ${result.failureReason}`,
    );
  }
  if (expected.expect.failureReason !== undefined && result.failureReason !== expected.expect.failureReason) {
    throw new Error(
      `${name}: self-check failed (failureReason=${result.failureReason}, expected ${expected.expect.failureReason})`,
    );
  }
  for (const [key, value] of Object.entries(expected.expect.acceptingAuthority ?? {})) {
    const actual = result.acceptingAuthority?.[key] ?? null;
    if (actual !== value) {
      throw new Error(
        `${name}: self-check failed (acceptingAuthority.${key}=${actual}, expected ${value})`,
      );
    }
  }
  const out = path.join(dir, name);
  mkdirSync(out, { recursive: true });
  writeFileSync(path.join(out, "package.aep"), Buffer.from(packageBytes));
  writeFileSync(path.join(out, "verify-expected.txt"), verifyExpectedLines.join("\n") + "\n");
  writeFileSync(path.join(out, "expected-acceptance.json"), JSON.stringify(expected, null, 2) + "\n");
  process.stdout.write(`  ok  ${name}\n`);
}

function rezip(entries) {
  return zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME });
}

// The positive baseline every mutation below starts from. It is not written
// out: valid/mandated-and-accepted and valid/voided-and-authorized already
// freeze an accepted, bound acceptance, and a fifth positive would add a
// package without adding a decision.
const accepted = await signPackage({ acceptance: makeAcceptance() });
{
  const check = await verify(accepted, {});
  if (!check.valid || check.acceptingAuthority?.boundToOutput !== true || check.acceptingAuthority?.keyBindingValid !== true) {
    throw new Error("baseline acceptance package does not verify clean; refusing to derive negatives from it");
  }
}

// 1. acceptance-signature-forged: the record is untouched — its digest still
//    matches the signed metadata, so the acceptance IS bound to these bytes —
//    but acceptance.sig carries the authority's real signature over a
//    DIFFERENT record. Isolates key binding: it is the only failing check.
{
  const entries = unzipSync(accepted);
  const mutated = { ...entries };
  const otherSignature = makeAcceptance({ accepted_at: "2026-08-12T00:00:00Z" }).sig;
  mutated["acceptance.sig"] = new TextEncoder().encode(otherSignature + "\n");
  await writeVector(ACCEPTANCE_OUT, "acceptance-signature-forged", rezip(mutated), [
    "verify=false",
    "diagnostic=acceptance invalid: acceptance.sig does not verify against the acceptance's public_key.",
  ], {
    description:
      "acceptance.sig replaced after signing with a signature the same authority made over a different acceptance record. The packaged record is untouched, so its digest still matches the signed metadata and the acceptance is bound to these bytes; what fails is key binding alone. A package cannot carry an acceptance its named authority never signed FOR THIS RECORD, and the verifier rejects rather than reporting it.",
    expect: {
      valid: false,
      failureReason: "acceptance invalid: acceptance.sig does not verify against the acceptance's public_key.",
      canonicalForm: "profile",
      acceptingAuthority: { keyBindingValid: false, boundToOutput: true, temporalContainment: true },
      checks: {
        "accepting-authority-binding": { verdict: "pass", enforced: true },
        "accepting-authority-key-binding": { verdict: "fail", enforced: true },
        "accepting-authority-temporal": { verdict: "pass", enforced: false },
        "accepting-authority-role": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
      },
    },
  });
}

// 2. acceptance-stripped: both acceptance entries are removed after signing.
//    accepting_authority.acceptance_digest lies inside the signed metadata
//    and cannot be removed with them, so the package still claims an
//    acceptance whose bytes are absent.
{
  const entries = unzipSync(accepted);
  const mutated = { ...entries };
  delete mutated["acceptance.json"];
  delete mutated["acceptance.sig"];
  await writeVector(ACCEPTANCE_OUT, "acceptance-stripped", rezip(mutated), [
    "verify=false",
    "diagnostic=acceptance invalid: acceptance.json entry is missing but metadata references an acceptance_digest.",
  ], {
    description:
      "The baseline package with acceptance.json and acceptance.sig removed after signing. The digest reference is inside the signed metadata and survives, so the package advertises a named authority's acceptance it does not carry. Key binding is not determinable — there is nothing to verify — and it is output binding that rejects.",
    expect: {
      valid: false,
      failureReason: "acceptance invalid: acceptance.json entry is missing but metadata references an acceptance_digest.",
      canonicalForm: "profile",
      acceptingAuthority: { keyBindingValid: null, boundToOutput: false },
      checks: {
        "accepting-authority-binding": { verdict: "fail", enforced: true },
        "accepting-authority-key-binding": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
      },
    },
  });
}

// 3. acceptance-digest-mismatch: the packaged acceptance is authentic —
//    signed by the genuine authority, and its own signature verifies — but
//    it is an acceptance of DIFFERENT bytes: the digest inside the signed
//    metadata names the record the issuer signed over, not this one.
//    Isolates output binding with key binding passing.
{
  const entries = unzipSync(accepted);
  const mutated = { ...entries };
  const other = makeAcceptance({ accepted_at: "2026-08-12T00:00:00Z" });
  mutated["acceptance.json"] = jcs(other.json);
  mutated["acceptance.sig"] = new TextEncoder().encode(other.sig + "\n");
  await writeVector(ACCEPTANCE_OUT, "acceptance-digest-mismatch", rezip(mutated), [
    "verify=false",
    "diagnostic=acceptance invalid: digest does not match accepting_authority.acceptance_digest.",
  ], {
    description:
      "The acceptance pair swapped after signing for a DIFFERENT but entirely authentic acceptance by the same authority (a different accepted_at). Its detached signature verifies against its own embedded key, so key binding passes; the digest inside the signed metadata still names the record the package was signed over, so the acceptance is bound to other bytes and the package is rejected. Authenticity and binding are separate properties, and authenticity alone is not enough.",
    expect: {
      valid: false,
      failureReason: "acceptance invalid: digest does not match accepting_authority.acceptance_digest.",
      canonicalForm: "profile",
      acceptingAuthority: { keyBindingValid: true, boundToOutput: false, temporalContainment: true },
      checks: {
        "accepting-authority-binding": { verdict: "fail", enforced: true },
        "accepting-authority-key-binding": { verdict: "pass", enforced: true },
      },
    },
  });
}

// 4. acceptance-principal-substitution: the packaged acceptance is
//    authentic and its digest matches — the issuer really did sign over
//    these bytes — but the principal that accepted is not the principal the
//    signed metadata names. Cross-field binding is what catches it.
{
  const acceptance = makeAcceptance({ principal: "impostor-authority" });
  const aep = await signPackage({ acceptance });
  await writeVector(ACCEPTANCE_OUT, "acceptance-principal-substitution", aep, [
    "verify=false",
    "diagnostic=acceptance invalid: acceptance principal does not match accepting_authority.principal.",
  ], {
    description:
      "The package is signed over an authentic acceptance whose digest matches, but the record's principal (impostor-authority) is not the principal the signed metadata.accepting_authority names (test-accepting-authority). The signature is real and the digest is right; what is wrong is WHO accepted. Cross-field binding rejects the package rather than reporting the mismatch beside a valid verdict.",
    expect: {
      valid: false,
      failureReason: "acceptance invalid: acceptance principal does not match accepting_authority.principal.",
      canonicalForm: "profile",
      acceptingAuthority: { keyBindingValid: true, boundToOutput: false, temporalContainment: true },
      checks: {
        "accepting-authority-binding": { verdict: "fail", enforced: true },
        "accepting-authority-key-binding": { verdict: "pass", enforced: true },
      },
    },
  });
}

process.stdout.write("\nGenerated 4 accepting-authority negative vectors.\n");
