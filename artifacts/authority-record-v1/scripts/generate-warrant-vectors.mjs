#!/usr/bin/env node
/**
 * Generate the warrant test vectors (spec §4.2).
 *
 * One valid conformance vector plus eight behavioural vectors:
 *
 *   valid/warranted-action                 (profile canonical + accepted warrant)
 *   warrant/warrant-digest-mismatch        (warrant.json rewritten after signing)
 *   warrant/warrant-unbound                (response-only canonical + warrant present)
 *   warrant/warrant-swap                   (an authentic warrant for a DIFFERENT policy)
 *   warrant/warrant-inapplicable-action    (action_type outside applies_to)
 *   warrant/warrant-decision-void          (policy decision deny; warrant licenses allow only)
 *   warrant/warrant-stale                  (validity window ends before genTime)
 *   warrant/warrant-acceptance-forged      (acceptance signed with the wrong key)
 *   warrant/warrant-acceptance-stripped    (acceptance block removed, digest consistent)
 *
 * The warrant fixture is authored against the demo policy fields the
 * shipped vectors already use (atap-basic 1.0, decision allow, action
 * class foundational:aep-response) and accepted by the committed
 * test-accepting-authority keypair — a TEST principal; who signs
 * acceptance in production is out of scope here (see
 * test-vectors/keys/README.md).
 *
 * Requires the library to be built first:
 *
 *   (cd lib && npm install && npm run build)
 *   node scripts/generate-warrant-vectors.mjs
 *
 * Each behavioural vector ships package.aep, verify-expected.txt, and
 * an expected-warrant.json consumed by lib/test/warrant-vectors.test.ts.
 * The script re-verifies every package before writing it.
 *
 * Determinism note: created_at and accepted_at are fixed, the RFC 3161
 * token is reused verbatim from valid-overt-profile/package.aep
 * (genTime 2026-01-01T00:00:00Z), RSASSA-PKCS1-v1_5 and JCS are
 * deterministic, and every ZIP entry timestamp is pinned
 * (ZIP_ENTRY_MTIME in lib/src/signer.ts), so re-running the script
 * produces byte-identical .aep files. Run `git diff --quiet` after
 * regenerating to confirm no drift.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createSign } from "node:crypto";
import path from "node:path";

import { createRequire } from "node:module";

// fflate is a dependency of lib/, not of the repo root; resolve it from
// lib/node_modules so this script runs from a clean checkout after
// `npm install` in lib/.
const require = createRequire(new URL("../lib/package.json", import.meta.url));
const { unzipSync, zipSync } = require("fflate");

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const VALID_OUT = path.join(root, "test-vectors/valid/warranted-action");
const WARRANT_OUT = path.join(root, "test-vectors/warrant");
const TSR_SOURCE = path.join(root, "test-vectors/valid/valid-overt-profile/package.aep");

// Must match lib/src/signer.ts ZIP_ENTRY_MTIME (local calendar fields).
const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);

let sign, verify, jcs;
try {
  ({ sign, verify } = await import(new URL("../lib/dist/index.js", import.meta.url).href));
  ({ jcs } = await import(new URL("../lib/dist/canonical.js", import.meta.url).href));
} catch (e) {
  process.stderr.write(`\
generate-warrant-vectors: cannot load ../lib/dist/.
Run \`npm install && npm run build\` in lib/ first, then retry.
Underlying error: ${e?.message ?? e}
`);
  process.exit(2);
}

const devPrivate = readFileSync(path.join(root, "test-vectors/keys/dev-rsa-4096.key"), "utf8");
const devPublic = readFileSync(path.join(root, "test-vectors/keys/dev-rsa-4096.pem"), "utf8");
const authorityPrivate = readFileSync(
  path.join(root, "test-vectors/keys/test-accepting-authority.key"),
  "utf8",
);
const authorityPublic = readFileSync(
  path.join(root, "test-vectors/keys/test-accepting-authority.pem"),
  "utf8",
);

const timestampTsr = unzipSync(new Uint8Array(readFileSync(TSR_SOURCE)))["timestamp.tsr"];

const baseMetadata = {
  schema: "urn:eatf:spec:aep:metadata:1.0",
  attestation_id: "att_warranted_action_01",
  created_at: "2026-08-05T00:00:00Z",
  agent_id: "urn:eatf:tenant:demo:agent:warranted-action-demo",
  action_type: "foundational:aep-response",
  policy_id: "atap-basic",
  policy_version: "1.0",
  policy_coverage: 1.0,
  policy_decision: "allow",
  format_version: "ATAP-1.0",
};

/**
 * The warrant fixture: authored once against the demo policy, accepted
 * by the test-accepting-authority TEST principal. The acceptance
 * signature covers JCS(warrant with acceptance.signature removed).
 */
function makeAcceptedWarrant(overrides = {}, signWithKey = authorityPrivate) {
  const warrant = {
    warrant_id: "urn:eatf:warrant:demo:atap-basic-allow-01",
    warrant_version: "1.0",
    policy_ref: { policy_id: "atap-basic", policy_version: "1.0" },
    inference_form: "policy-evaluation",
    statement:
      "Outputs that policy atap-basic 1.0 evaluates to allow are licensed for the action class foundational:aep-response.",
    applies_to: {
      action_types: ["foundational:aep-response"],
      policy_decisions: ["allow"],
    },
    valid_from: "2025-07-01T00:00:00Z",
    valid_until: "2026-07-01T00:00:00Z",
    void_if: [
      { kind: "machine", predicate: "metadata.policy_coverage < 1.0" },
      {
        kind: "attested",
        text: "The policy evaluation configuration diverges from the assurance case this acceptance was made against.",
      },
    ],
    ...overrides,
  };
  const acceptance = {
    authority_id: "test-accepting-authority",
    accepted_at: "2026-08-05T00:00:00Z",
    public_key: authorityPublic,
  };
  const signer = createSign("sha256");
  signer.update(jcs({ ...warrant, acceptance }));
  signer.end();
  acceptance.signature = signer.sign(signWithKey).toString("base64");
  return { ...warrant, acceptance };
}

async function signPackage({ metadata = baseMetadata, warrant, canonicalForm = "profile" }) {
  const result = await sign({
    payload: "EATF warranted-action demo: this output carries an accepted warrant.\n",
    privateKeyPem: devPrivate,
    publicKeyPem: devPublic,
    metadata,
    overtScope: "foundational:aep-response",
    timestampTsr,
    canonicalForm,
    warrant,
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
  for (const [key, value] of Object.entries(expected.expect.warrant ?? {})) {
    const actual = result.warrant?.[key] ?? null;
    if (actual !== value) {
      throw new Error(`${name}: self-check failed (warrant.${key}=${actual}, expected ${value})`);
    }
  }
  const out = path.join(dir, name);
  mkdirSync(out, { recursive: true });
  writeFileSync(path.join(out, "package.aep"), Buffer.from(packageBytes));
  writeFileSync(path.join(out, "verify-expected.txt"), verifyExpectedLines.join("\n") + "\n");
  writeFileSync(path.join(out, "expected-warrant.json"), JSON.stringify(expected, null, 2) + "\n");
  process.stdout.write(`  ok  ${name}\n`);
}

function rezip(entries) {
  return zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME });
}

// 0. valid/warranted-action: profile canonical form, the accepted
//    warrant packaged and digest-bound inside the signed metadata.
const warrantedAction = await signPackage({ warrant: makeAcceptedWarrant() });
await writeVector(path.dirname(VALID_OUT), path.basename(VALID_OUT), warrantedAction, ["verify=true"], {
  description:
    "Profile canonical form with an accepted warrant: warrant.json is JCS-canonical, digest-bound from signed metadata, policy-linked, applicable, and its acceptance signature verifies against the test-accepting-authority key. Freshness stays open because no shipped TSA token chains to a trusted root.",
  expect: {
    valid: true,
    canonicalForm: "profile",
    warrant: {
      present: true,
      bound: true,
      policyLinked: true,
      applicable: true,
      acceptanceVerified: true,
      fresh: null,
    },
    checks: {
      "warrant-digest": { verdict: "pass", enforced: true },
      "warrant-parse": { verdict: "pass", enforced: true },
      "warrant-bound": { verdict: "pass", enforced: false },
      "warrant-policy-link": { verdict: "pass", enforced: true },
      "warrant-applicability": { verdict: "pass", enforced: false },
      "warrant-acceptance-signature": { verdict: "pass", enforced: true },
      "warrant-freshness": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
    },
    reportIncludes: [
      "Warrant verified (urn:eatf:warrant:demo:atap-basic-allow-01, accepted by test-accepting-authority).",
    ],
  },
});

// 1. warrant-digest-mismatch: rewrite warrant.json after signing. The
//    profile form signs the metadata digest reference, so the rewritten
//    record can no longer match it.
{
  const entries = unzipSync(warrantedAction);
  const mutated = { ...entries };
  const record = JSON.parse(Buffer.from(mutated["warrant.json"]).toString("utf8"));
  record.statement =
    "Outputs that policy atap-basic 1.0 evaluates to ANY decision are licensed for every action class.";
  mutated["warrant.json"] = jcs(record);
  await writeVector(WARRANT_OUT, "warrant-digest-mismatch", rezip(mutated), [
    "verify=false",
    "diagnostic=warrant.json invalid: digest does not match metadata.warrant_digest.",
  ], {
    description:
      "valid/warranted-action with the warrant statement rewritten (and re-canonicalised) after signing. The digest reference in signed metadata no longer matches, so a warrant-aware verifier rejects.",
    expect: {
      valid: false,
      failureReason: "warrant.json invalid: digest does not match metadata.warrant_digest.",
      warrant: { present: true, bound: null, acceptanceVerified: null },
      checks: {
        "warrant-digest": { verdict: "fail", enforced: true },
        "warrant-acceptance-signature": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
      },
    },
  });
}

// 2. warrant-unbound: the same accepted warrant in a response-only
//    package. Everything cross-checks, but the digest reference lies
//    outside the signature — the warrant is reported unbound and the
//    package stays accepted (compatibility form semantics unchanged).
{
  const aep = await signPackage({ warrant: makeAcceptedWarrant(), canonicalForm: "response-only" });
  await writeVector(WARRANT_OUT, "warrant-unbound", aep, ["verify=true"], {
    description:
      "The accepted warrant packaged under the response-only canonical form: metadata.warrant_digest itself lies outside signature.sig, so the binding does not hold. bound=false is reported loudly; the package stays accepted.",
    expect: {
      valid: true,
      canonicalForm: "response-only",
      warrant: {
        present: true,
        bound: false,
        policyLinked: true,
        applicable: true,
        acceptanceVerified: true,
        fresh: null,
      },
      checks: {
        "warrant-bound": { verdict: "fail", enforced: false },
      },
      unsignedFieldsInclude: ["metadata.warrant_digest", "metadata.warrant_id", "metadata.warrant_version"],
      reportIncludes: [
        "Warrant present but unbound: the response-only canonical form leaves metadata.warrant_digest outside signature.sig.",
      ],
    },
  });
}

// 3. warrant-swap: an AUTHENTIC warrant (correctly accepted, correctly
//    digested) written against a different policy. Only the linkage
//    check catches the swap.
{
  const swapped = makeAcceptedWarrant({
    warrant_id: "urn:eatf:warrant:demo:atap-extended-allow-01",
    policy_ref: { policy_id: "atap-extended", policy_version: "2.0" },
    statement:
      "Outputs that policy atap-extended 2.0 evaluates to allow are licensed for the action class foundational:aep-response.",
  });
  const metadata = { ...baseMetadata, warrant_id: "urn:eatf:warrant:demo:atap-extended-allow-01" };
  const aep = await signPackage({ metadata, warrant: swapped });
  await writeVector(WARRANT_OUT, "warrant-swap", aep, [
    "verify=false",
    "diagnostic=warrant.json invalid: policy_ref.policy_id does not match metadata.policy_id.",
  ], {
    description:
      "An authentic, correctly accepted warrant for a DIFFERENT policy (atap-extended 2.0) packaged with an atap-basic action. Digest and acceptance are consistent; only the policy linkage check exposes the swap.",
    expect: {
      valid: false,
      failureReason: "warrant.json invalid: policy_ref.policy_id does not match metadata.policy_id.",
      warrant: { present: true, bound: true, policyLinked: false, acceptanceVerified: null },
      checks: {
        "warrant-digest": { verdict: "pass", enforced: true },
        "warrant-policy-link": { verdict: "fail", enforced: true },
        "warrant-acceptance-signature": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
      },
    },
  });
}

// 4. warrant-inapplicable-action: the warrant covers a different action
//    class. Appraisal outcome: reported, never a rejection.
{
  const warrant = makeAcceptedWarrant({
    applies_to: {
      action_types: ["agentic-extended:mcp-tools-call"],
      policy_decisions: ["allow"],
    },
  });
  const aep = await signPackage({ warrant });
  await writeVector(WARRANT_OUT, "warrant-inapplicable-action", aep, ["verify=true"], {
    description:
      "The accepted warrant licenses agentic-extended:mcp-tools-call, but the package attests a foundational:aep-response action. The warrant does not apply — the output may inform but carries no warrant to compel — and the package stays accepted.",
    expect: {
      valid: true,
      warrant: {
        present: true,
        bound: true,
        policyLinked: true,
        applicable: false,
        acceptanceVerified: true,
        fresh: null,
      },
      checks: {
        "warrant-applicability": { verdict: "fail", enforced: false },
      },
      reportIncludes: [
        "Warrant does not apply to this action: the output may inform but carries no warrant to compel.",
      ],
    },
  });
}

// 5. warrant-decision-void: the policy decided deny, and the warrant
//    licenses allow outputs only. Same appraisal semantics as an
//    inapplicable action class.
{
  const metadata = { ...baseMetadata, attestation_id: "att_warranted_action_denied_01", policy_decision: "deny" };
  const aep = await signPackage({ metadata, warrant: makeAcceptedWarrant() });
  await writeVector(WARRANT_OUT, "warrant-decision-void", aep, ["verify=true"], {
    description:
      "The policy evaluated this action to deny; the warrant licenses allow outputs only. The deny output falls outside applies_to.policy_decisions — it may inform but carries no warrant to compel — and the package stays accepted (the AEP remains authentic evidence of the denial).",
    expect: {
      valid: true,
      warrant: {
        present: true,
        bound: true,
        policyLinked: true,
        applicable: false,
        acceptanceVerified: true,
        fresh: null,
      },
      checks: {
        "warrant-applicability": { verdict: "fail", enforced: false },
      },
      reportIncludes: [
        "Warrant does not apply to this action: the output may inform but carries no warrant to compel.",
      ],
    },
  });
}

// 6. warrant-stale: the validity window closed before the RFC 3161
//    genTime (2026-01-01). fresh=false is reported; the package stays
//    accepted.
{
  const warrant = makeAcceptedWarrant({
    valid_from: "2024-01-01T00:00:00Z",
    valid_until: "2025-12-31T23:59:59Z",
  });
  const aep = await signPackage({ warrant });
  await writeVector(WARRANT_OUT, "warrant-stale", aep, ["verify=true"], {
    description:
      "The warrant's validity window ended 2025-12-31, before the package's RFC 3161 genTime (2026-01-01). The warrant was not in force at signing time: fresh=false is reported and the package stays accepted.",
    expect: {
      valid: true,
      warrant: {
        present: true,
        bound: true,
        policyLinked: true,
        applicable: true,
        acceptanceVerified: true,
        fresh: false,
      },
      checks: {
        "warrant-freshness": { verdict: "fail", enforced: false },
      },
      reportIncludes: [
        "Warrant not in force at signing time: genTime 2026-01-01T00:00:00.000Z lies outside valid_from..valid_until.",
      ],
    },
  });
}

// 7. warrant-acceptance-forged: the acceptance signature was made with
//    the WRONG private key (the packaging dev key) while the authority's
//    public key stays in place.
{
  const aep = await signPackage({ warrant: makeAcceptedWarrant({}, devPrivate) });
  await writeVector(WARRANT_OUT, "warrant-acceptance-forged", aep, [
    "verify=false",
    "diagnostic=warrant.json invalid: acceptance.signature does not verify against acceptance.public_key.",
  ], {
    description:
      "The acceptance block names test-accepting-authority and carries its public key, but the signature was made with a different private key. A package cannot assert an acceptance its named principal never signed.",
    expect: {
      valid: false,
      failureReason: "warrant.json invalid: acceptance.signature does not verify against acceptance.public_key.",
      warrant: { present: true, bound: true, policyLinked: true, acceptanceVerified: false },
      checks: {
        "warrant-acceptance-signature": { verdict: "fail", enforced: true },
      },
    },
  });
}

// 8. warrant-acceptance-stripped: the acceptance block removed before
//    packaging. The digest is CONSISTENT (the signer digested the
//    stripped record), so only the acceptance check exposes that the
//    warrant carries no acceptor.
{
  const stripped = makeAcceptedWarrant();
  delete stripped.acceptance;
  const aep = await signPackage({ warrant: stripped });
  await writeVector(WARRANT_OUT, "warrant-acceptance-stripped", aep, [
    "verify=false",
    "diagnostic=warrant.json invalid: acceptance block is missing.",
  ], {
    description:
      "The warrant was packaged without its acceptance block; the digest reference is consistent with the stripped record. A warrant without a named acceptor is rejected: a package cannot assert policy backing without one.",
    expect: {
      valid: false,
      failureReason: "warrant.json invalid: acceptance block is missing.",
      warrant: { present: true, bound: true, policyLinked: true, acceptanceVerified: false },
      checks: {
        "warrant-acceptance-signature": { verdict: "fail", enforced: true },
      },
    },
  });
}

process.stdout.write(`\nGenerated 1 valid + 8 warrant vectors.\n`);
