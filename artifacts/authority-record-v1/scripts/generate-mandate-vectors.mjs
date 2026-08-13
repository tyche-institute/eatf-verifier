#!/usr/bin/env node
/**
 * Generate the detached-mandate test vectors (spec §4.5).
 *
 * Three valid conformance vectors plus nine behavioural vectors:
 *
 *   valid/mandated-action            (profile; signed mandate, in scope, in force)
 *   valid/mandated-and-accepted      (profile; signed mandate AND accepted warrant
 *                                     AND detached epistemic acceptance — three
 *                                     distinct principals over the same bytes)
 *   valid/mandated-denied-action     (as above, policy_decision deny: the package
 *                                     is authentic evidence of a denial)
 *   mandate/mandate-signature-forged   (signature made with the wrong private key)
 *   mandate/mandate-stripped           (mandate.json removed; digest reference stays)
 *   mandate/mandate-digest-mismatch    (record widened after signing)
 *   mandate/mandate-unbound            (response-only form: reference outside the signature)
 *   mandate/mandate-principal-substitution (authentic mandate of a DIFFERENT authority)
 *   mandate/mandate-subject-swap       (authentic mandate granted to a different agent)
 *   mandate/mandate-out-of-scope       (action outside scope — appraisal, stays valid)
 *   mandate/mandate-expired            (window closed before genTime — appraisal, stays valid)
 *   mandate/mandate-reference-only     (the pre-§4.5 named-principal form: nothing verified)
 *
 * The mandate is signed by the committed `test-granting-authority`
 * keypair — a TEST principal, and one DISTINCT from both the package
 * issuer (`dev-rsa-4096`) and the epistemic accepting authority
 * (`test-accepting-authority`). Who grants mandates in production, and
 * under what custody, is a governance question out of scope for these
 * fixtures (see test-vectors/keys/README.md).
 *
 * Requires the library to be built first:
 *
 *   (cd lib && npm install && npm run build)
 *   node scripts/generate-mandate-vectors.mjs
 *
 * Each vector ships package.aep, verify-expected.txt, and an
 * expected-mandate.json consumed by lib/test/mandate-vectors.test.ts.
 * The script re-verifies every package before writing it.
 *
 * Determinism: granted_at / accepted_at / created_at fixed, the RFC 3161
 * token reused verbatim from valid-overt-profile/package.aep (genTime
 * 2026-01-01T00:00:00Z), RSASSA-PKCS1-v1_5 and JCS deterministic, every
 * ZIP entry timestamp pinned (ZIP_ENTRY_MTIME in lib/src/signer.ts). Two
 * runs of this script produce byte-identical .aep files; `git diff
 * --quiet test-vectors/` after regenerating confirms no drift.
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

const VALID_DIR = path.join(root, "test-vectors/valid");
const MANDATE_OUT = path.join(root, "test-vectors/mandate");
const KEYS_DIR = path.join(root, "test-vectors/keys");
const TSR_SOURCE = path.join(root, "test-vectors/valid/valid-overt-profile/package.aep");

// Must match lib/src/signer.ts ZIP_ENTRY_MTIME (local calendar fields).
const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);

let sign, verify, jcs;
try {
  ({ sign, verify } = await import(new URL("../lib/dist/index.js", import.meta.url).href));
  ({ jcs } = await import(new URL("../lib/dist/canonical.js", import.meta.url).href));
} catch (e) {
  process.stderr.write(`\
generate-mandate-vectors: cannot load ../lib/dist/.
Run \`npm install && npm run build\` in lib/ first, then retry.
Underlying error: ${e?.message ?? e}
`);
  process.exit(2);
}

const devPrivate = readFileSync(path.join(KEYS_DIR, "dev-rsa-4096.key"), "utf8");
const devPublic = readFileSync(path.join(KEYS_DIR, "dev-rsa-4096.pem"), "utf8");
const acceptingPrivate = readFileSync(path.join(KEYS_DIR, "test-accepting-authority.key"), "utf8");
const acceptingPublic = readFileSync(path.join(KEYS_DIR, "test-accepting-authority.pem"), "utf8");
const grantingPrivate = readFileSync(path.join(KEYS_DIR, "test-granting-authority.key"), "utf8");
const grantingPublic = readFileSync(path.join(KEYS_DIR, "test-granting-authority.pem"), "utf8");

const timestampTsr = unzipSync(new Uint8Array(readFileSync(TSR_SOURCE)))["timestamp.tsr"];

const AGENT_ID = "urn:eatf:tenant:demo:agent:mandated-demo";
const GRANTING_PRINCIPAL = "urn:eatf:mandate:demo:granting-authority";
const MANDATE_ID = "urn:eatf:mandate:demo:mandate:0001";

const baseMetadata = {
  schema: "urn:eatf:spec:aep:metadata:1.0",
  attestation_id: "att_mandated_action_01",
  created_at: "2026-08-05T00:00:00Z",
  agent_id: AGENT_ID,
  action_type: "foundational:aep-response",
  policy_id: "atap-basic",
  policy_version: "1.0",
  policy_coverage: 1.0,
  policy_decision: "allow",
  format_version: "ATAP-1.0",
};

const AUTHORIZING_PRINCIPAL = {
  principal: GRANTING_PRINCIPAL,
  mandate_ref: MANDATE_ID,
};

const ACCEPTING_AUTHORITY = {
  principal: "test-accepting-authority",
  policy_id: "atap-basic",
  policy_version: "1.0",
  validity: { not_before: "2025-07-01T00:00:00Z", not_after: "2026-07-01T00:00:00Z" },
};

/**
 * The mandate fixture: a once-authored grant, signed by the granting
 * authority over the JCS bytes of the record. The signature is detached
 * (mandate.sig) and is made HERE, never by the package signer.
 */
function makeMandate(overrides = {}, signWithKey = grantingPrivate) {
  const record = {
    mandate_id: MANDATE_ID,
    mandate_version: "1.0",
    principal: GRANTING_PRINCIPAL,
    subject: AGENT_ID,
    granted_at: "2026-08-05T00:00:00Z",
    statement:
      "The granting authority authorises the subject agent to take foundational:aep-response actions evaluated under policy atap-basic.",
    scope: {
      action_types: ["foundational:aep-response"],
      policy_ids: ["atap-basic"],
    },
    valid_from: "2025-07-01T00:00:00Z",
    valid_until: "2026-07-01T00:00:00Z",
    public_key: grantingPublic,
    ...overrides,
  };
  const signer = createSign("sha256");
  signer.update(jcs(record));
  signer.end();
  return { json: record, sig: signer.sign(signWithKey).toString("base64") };
}

/** The epistemic warrant of §4.2, accepted by the accepting authority. */
function makeAcceptedWarrant() {
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
  };
  const acceptance = {
    authority_id: "test-accepting-authority",
    accepted_at: "2026-08-05T00:00:00Z",
    public_key: acceptingPublic,
  };
  const signer = createSign("sha256");
  signer.update(jcs({ ...warrant, acceptance }));
  signer.end();
  acceptance.signature = signer.sign(acceptingPrivate).toString("base64");
  return { ...warrant, acceptance };
}

/** The detached §4.3 acceptance record: the authority signs JCS(record). */
function makeAcceptance() {
  const record = {
    principal: "test-accepting-authority",
    policy_id: "atap-basic",
    policy_version: "1.0",
    accepted_at: "2026-08-05T00:00:00Z",
    public_key: acceptingPublic,
  };
  const signer = createSign("sha256");
  signer.update(jcs(record));
  signer.end();
  return { json: record, sig: signer.sign(acceptingPrivate).toString("base64") };
}

async function signPackage({
  metadata = baseMetadata,
  mandate,
  authorizingPrincipal = AUTHORIZING_PRINCIPAL,
  warrant,
  acceptingAuthority,
  acceptance,
  canonicalForm = "profile",
} = {}) {
  const result = await sign({
    payload: "EATF mandate demo: this output is covered by a signed mandate.\n",
    privateKeyPem: devPrivate,
    publicKeyPem: devPublic,
    metadata,
    overtScope: "foundational:aep-response",
    timestampTsr,
    canonicalForm,
    mandate,
    authorizingPrincipal,
    warrant,
    acceptingAuthority,
    acceptance,
  });
  return result.aep;
}

async function writeVector(dir, name, packageBytes, verifyExpectedLines, expected, expectedFile = "expected-mandate.json") {
  const result = await verify(packageBytes, expected.options ?? {});
  if (result.valid !== expected.expect.valid) {
    throw new Error(
      `${name}: self-check failed (valid=${result.valid}, expected ${expected.expect.valid}): ${result.failureReason}`,
    );
  }
  for (const [key, value] of Object.entries(expected.expect.mandate ?? {})) {
    const actual = result.mandate?.[key] ?? null;
    if (actual !== value) {
      throw new Error(`${name}: self-check failed (mandate.${key}=${actual}, expected ${value})`);
    }
  }
  const out = path.join(dir, name);
  mkdirSync(out, { recursive: true });
  writeFileSync(path.join(out, "package.aep"), Buffer.from(packageBytes));
  writeFileSync(path.join(out, "verify-expected.txt"), verifyExpectedLines.join("\n") + "\n");
  writeFileSync(path.join(out, expectedFile), JSON.stringify(expected, null, 2) + "\n");
  process.stdout.write(`  ok  ${name}\n`);
}

function rezip(entries) {
  return zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME });
}

// ---------------------------------------------------------------- valid ---

// 0. valid/mandated-action: the signed mandate alone, bound under the
//    profile canonical form.
const mandatedAction = await signPackage({ mandate: makeMandate() });
await writeVector(VALID_DIR, "mandated-action", mandatedAction, ["verify=true"], {
  description:
    "Profile canonical form carrying a detached mandate.json / mandate.sig pair signed by the test-granting-authority principal, bound by authorizing_principal.mandate_digest from inside the signed metadata. The four binding-family checks gate and pass; the action lies inside the granted scope and the RFC 3161 genTime inside the mandate's validity window.",
  expect: {
    valid: true,
    canonicalForm: "profile",
    mandate: {
      claimed: true,
      present: true,
      bound: true,
      signatureVerified: true,
      inScope: true,
      temporalContainment: true,
    },
    checks: {
      "mandate-digest": { verdict: "pass", enforced: true },
      "mandate-parse": { verdict: "pass", enforced: true },
      "mandate-bound": { verdict: "pass", enforced: true },
      "mandate-signature": { verdict: "pass", enforced: true },
      "mandate-scope": { verdict: "pass", enforced: false },
      "mandate-temporal": { verdict: "pass", enforced: false },
    },
    reportIncludes: [
      `Mandate verified (${MANDATE_ID}, granted by ${GRANTING_PRINCIPAL} to ${AGENT_ID}).`,
    ],
  },
});

// 1. valid/mandated-and-accepted: both authority layers live over the
//    same protected bytes — a signed mandate from the granting
//    authority (deontic, gated) and an accepted warrant plus a detached
//    acceptance record from the accepting authority (epistemic, its
//    acceptance signature gated too). Three distinct principals.
const mandatedAndAccepted = await signPackage({
  metadata: { ...baseMetadata, attestation_id: "att_mandated_and_accepted_01" },
  mandate: makeMandate(),
  warrant: makeAcceptedWarrant(),
  acceptingAuthority: ACCEPTING_AUTHORITY,
  acceptance: makeAcceptance(),
});
await writeVector(VALID_DIR, "mandated-and-accepted", mandatedAndAccepted, ["verify=true"], {
  description:
    "Both authority layers signed over the same protected bytes: a detached mandate signed by the granting authority (deontic) and an accepted warrant plus a detached acceptance record signed by the accepting authority (epistemic). Three distinct keys — package issuer, granting authority, accepting authority — and the enforced checks of both layers pass.",
  expect: {
    valid: true,
    canonicalForm: "profile",
    mandate: {
      claimed: true,
      present: true,
      bound: true,
      signatureVerified: true,
      inScope: true,
      temporalContainment: true,
      principal: GRANTING_PRINCIPAL,
    },
    checks: {
      "mandate-digest": { verdict: "pass", enforced: true },
      "mandate-bound": { verdict: "pass", enforced: true },
      "mandate-signature": { verdict: "pass", enforced: true },
      "warrant-acceptance-signature": { verdict: "pass", enforced: true },
      "accepting-authority-binding": { verdict: "pass", enforced: true },
      "accepting-authority-key-binding": { verdict: "pass", enforced: true },
    },
  },
});

// 2. valid/mandated-denied-action: the same two-layer package recording
//    a DENY decision. It is authentic evidence that the action was
//    refused, and it is the baseline the deny-to-allow rewrite is
//    attempted against (test-vectors/invalid/profile-form-policy-rewrite).
const mandatedDenied = await signPackage({
  metadata: {
    ...baseMetadata,
    attestation_id: "att_mandated_denied_action_01",
    policy_decision: "deny",
  },
  mandate: makeMandate(),
  warrant: makeAcceptedWarrant(),
  acceptingAuthority: ACCEPTING_AUTHORITY,
  acceptance: makeAcceptance(),
});
await writeVector(VALID_DIR, "mandated-denied-action", mandatedDenied, ["verify=true"], {
  description:
    "The two-layer package recording policy_decision deny. The AEP is authentic evidence of the denial: the mandate binds and verifies, the warrant licenses allow outputs only and so does not apply (reported, never rejecting), and the package stays accepted. This is the baseline package the profile-form deny-to-allow rewrite is attempted against.",
  expect: {
    valid: true,
    canonicalForm: "profile",
    mandate: { claimed: true, bound: true, signatureVerified: true, inScope: true },
    checks: {
      "mandate-bound": { verdict: "pass", enforced: true },
      "mandate-signature": { verdict: "pass", enforced: true },
      "warrant-applicability": { verdict: "fail", enforced: false },
    },
  },
});

// ------------------------------------------------------------ behavioural ---

// 3. mandate-signature-forged: the record names the granting authority
//    and carries its public key, but the detached signature was made
//    with the package issuer's private key.
{
  const aep = await signPackage({ mandate: makeMandate({}, devPrivate) });
  await writeVector(MANDATE_OUT, "mandate-signature-forged", aep, [
    "verify=false",
    "diagnostic=mandate.json invalid: mandate.sig does not verify against the mandate's public_key.",
  ], {
    description:
      "The mandate record names the granting authority and carries its public key, but mandate.sig was made with a different private key. A package cannot assert a mandate its named granting authority never signed.",
    expect: {
      valid: false,
      failureReason: "mandate.json invalid: mandate.sig does not verify against the mandate's public_key.",
      mandate: { claimed: true, present: true, bound: true, signatureVerified: false },
      checks: {
        "mandate-digest": { verdict: "pass", enforced: true },
        "mandate-bound": { verdict: "pass", enforced: true },
        "mandate-signature": { verdict: "fail", enforced: true },
        "mandate-scope": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
      },
    },
  });
}

// 4. mandate-stripped: the mandate entries are removed after signing.
//    The digest reference stays inside the signed metadata, so the
//    package still claims a mandate it does not carry.
{
  const entries = unzipSync(mandatedAction);
  const mutated = { ...entries };
  delete mutated["mandate.json"];
  delete mutated["mandate.sig"];
  await writeVector(MANDATE_OUT, "mandate-stripped", rezip(mutated), [
    "verify=false",
    "diagnostic=mandate.json invalid: mandate.json entry is missing but metadata references a mandate.",
  ], {
    description:
      "valid/mandated-action with mandate.json and mandate.sig removed after signing. The digest reference lies inside the signed metadata and cannot be removed with them, so the package claims a mandate whose bytes are absent.",
    expect: {
      valid: false,
      failureReason: "mandate.json invalid: mandate.json entry is missing but metadata references a mandate.",
      mandate: { claimed: true, present: false },
      checks: { "mandate-digest": { verdict: "fail", enforced: true } },
    },
  });
}

// 5. mandate-digest-mismatch: the record is widened after signing. The
//    profile form signs the digest reference, so the rewritten record
//    can no longer match it.
{
  const entries = unzipSync(mandatedAction);
  const mutated = { ...entries };
  const record = JSON.parse(Buffer.from(mutated["mandate.json"]).toString("utf8"));
  record.scope.action_types = ["foundational:aep-response", "agentic-extended:mcp-tools-call"];
  mutated["mandate.json"] = jcs(record);
  await writeVector(MANDATE_OUT, "mandate-digest-mismatch", rezip(mutated), [
    "verify=false",
    "diagnostic=mandate.json invalid: digest does not match authorizing_principal.mandate_digest.",
  ], {
    description:
      "valid/mandated-action with the mandate's granted scope widened (and the record re-canonicalised) after signing. The digest reference inside the signed metadata no longer matches the packaged bytes.",
    expect: {
      valid: false,
      failureReason: "mandate.json invalid: digest does not match authorizing_principal.mandate_digest.",
      mandate: { claimed: true, present: true },
      checks: {
        "mandate-digest": { verdict: "fail", enforced: true },
        "mandate-signature": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
      },
    },
  });
}

// 6. mandate-unbound: the same authentic mandate under the response-only
//    canonical form, where authorizing_principal.mandate_digest itself
//    lies outside signature.sig. §4.5 rejects rather than reports —
//    deliberately unlike the §4.2 warrant and the §4.3 acceptance.
{
  const aep = await signPackage({ mandate: makeMandate(), canonicalForm: "response-only" });
  await writeVector(MANDATE_OUT, "mandate-unbound", aep, [
    "verify=false",
    "diagnostic=mandate.json invalid: the response-only canonical form leaves authorizing_principal.mandate_digest outside signature.sig.",
  ], {
    description:
      "The authentic, correctly signed mandate packaged under the response-only canonical form. Its own digest reference lies outside signature.sig and is rewritable, so the mandate is bound to nothing. Unlike an unbound warrant (§4.2) or an unbound acceptance (§4.3), which are reported and accepted, an unbound mandate is rejected.",
    expect: {
      valid: false,
      canonicalForm: "response-only",
      failureReason:
        "mandate.json invalid: the response-only canonical form leaves authorizing_principal.mandate_digest outside signature.sig.",
      mandate: { claimed: true, present: true, bound: false },
      checks: {
        "mandate-digest": { verdict: "pass", enforced: true },
        "mandate-parse": { verdict: "pass", enforced: true },
        "mandate-bound": { verdict: "fail", enforced: true },
        "mandate-signature": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
      },
      unsignedFieldsInclude: ["metadata.authorizing_principal"],
    },
  });
}

// 7. mandate-principal-substitution: an authentic, correctly signed
//    mandate — signed by the ACCEPTING authority's key and naming that
//    principal — presented where the signed metadata names the granting
//    authority. The signature verifies against its own record; only the
//    cross-binding to the signed metadata exposes the substitution.
{
  const substituted = makeMandate(
    { principal: "test-accepting-authority", public_key: acceptingPublic },
    acceptingPrivate,
  );
  const aep = await signPackage({ mandate: substituted });
  await writeVector(MANDATE_OUT, "mandate-principal-substitution", aep, [
    "verify=false",
    "diagnostic=mandate.json invalid: mandate principal does not match principal.",
  ], {
    description:
      "A mandate authentically signed by the epistemic accepting authority's key, naming that principal, packaged where the signed metadata names the granting authority. Digest and signature are internally consistent; only the cross-binding of the record's principal to the signed authorizing_principal block exposes the substitution.",
    expect: {
      valid: false,
      failureReason: "mandate.json invalid: mandate principal does not match principal.",
      mandate: { claimed: true, present: true, bound: false },
      checks: {
        "mandate-parse": { verdict: "pass", enforced: true },
        "mandate-bound": { verdict: "fail", enforced: true },
      },
    },
  });
}

// 8. mandate-subject-swap: an authentic mandate granted to a DIFFERENT
//    agent, packaged with this agent's output.
{
  const other = makeMandate({ subject: "urn:eatf:tenant:demo:agent:some-other-agent" });
  const aep = await signPackage({ mandate: other });
  await writeVector(MANDATE_OUT, "mandate-subject-swap", aep, [
    "verify=false",
    "diagnostic=mandate.json invalid: mandate subject does not match agent_id.",
  ], {
    description:
      "An authentic mandate, correctly signed by the granting authority, but granted to a different subject agent than the one this package attests. The grant is real; it is not a grant to this agent.",
    expect: {
      valid: false,
      failureReason: "mandate.json invalid: mandate subject does not match agent_id.",
      mandate: { claimed: true, present: true, bound: false },
      checks: { "mandate-bound": { verdict: "fail", enforced: true } },
    },
  });
}

// 9. mandate-out-of-scope: the mandate covers a different action class.
//    Appraisal outcome: reported, never a rejection.
{
  const narrow = makeMandate({
    scope: {
      action_types: ["agentic-extended:mcp-tools-call"],
      policy_ids: ["atap-basic"],
    },
  });
  const aep = await signPackage({ mandate: narrow });
  await writeVector(MANDATE_OUT, "mandate-out-of-scope", aep, ["verify=true"], {
    description:
      "The signed mandate grants agentic-extended:mcp-tools-call, but the package attests a foundational:aep-response action. The action lies outside the granted mandate — it may inform but carries no mandate to compel — and the package stays accepted.",
    expect: {
      valid: true,
      mandate: { claimed: true, bound: true, signatureVerified: true, inScope: false },
      checks: { "mandate-scope": { verdict: "fail", enforced: false } },
      reportIncludes: [
        "Action lies outside the granted mandate: the output may inform but carries no mandate to compel.",
      ],
    },
  });
}

// 10. mandate-expired: the validity window closed before the RFC 3161
//     genTime (2026-01-01). Reported; the package stays accepted.
{
  const expired = makeMandate({
    valid_from: "2024-01-01T00:00:00Z",
    valid_until: "2025-12-31T23:59:59Z",
  });
  const aep = await signPackage({ mandate: expired });
  await writeVector(MANDATE_OUT, "mandate-expired", aep, ["verify=true"], {
    description:
      "The mandate's validity window ended 2025-12-31, before the package's RFC 3161 genTime (2026-01-01). The mandate was not in force at signing time: the outcome is reported and the package stays accepted.",
    expect: {
      valid: true,
      mandate: { claimed: true, bound: true, signatureVerified: true, temporalContainment: false },
      checks: { "mandate-temporal": { verdict: "fail", enforced: false } },
      reportIncludes: [
        "Mandate not in force at signing time: genTime 2026-01-01T00:00:00.000Z lies outside valid_from..valid_until.",
      ],
    },
  });
}

// 11. mandate-reference-only: the pre-§4.5 form. A deontic principal is
//     named, no signed mandate is claimed, and every mandate check
//     reports not determinate. This vector pins the state the extension
//     replaces: named, and unverified.
{
  const aep = await signPackage({ mandate: undefined, authorizingPrincipal: AUTHORIZING_PRINCIPAL });
  await writeVector(MANDATE_OUT, "mandate-reference-only", aep, ["verify=true"], {
    description:
      "metadata.authorizing_principal names a deontic principal and a mandate_ref, and carries no mandate_digest; no mandate.json is packaged. No signed mandate is claimed: every §4.5 check reports not determinate, nothing about the grant is verified, and the package stays accepted. This is the state §4.5 replaces.",
    expect: {
      valid: true,
      mandate: { claimed: false, present: false, bound: null, signatureVerified: null },
      checks: {
        "mandate-digest": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
        "mandate-parse": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
        "mandate-bound": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
        "mandate-signature": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
        "mandate-scope": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
        "mandate-temporal": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
      },
      reportIncludes: [
        "Authorizing principal named without a signed mandate: the deontic layer is a reference only and nothing in it is verified.",
      ],
    },
  });
}

// ------------------------------------------------------- the remedy test ---

// 12. invalid/profile-form-policy-rewrite: the deny-to-allow rewrite of
//     test-vectors/boundary/response-only-unsigned-policy-tamper,
//     applied byte-for-byte the same way to the two-layer profile-form
//     package. Both reference implementations reject it, so it is a
//     GATING vector rather than a behavioural one.
{
  const entries = unzipSync(mandatedDenied);
  const mutated = { ...entries };
  const metadata = JSON.parse(Buffer.from(mutated["metadata.json"]).toString("utf8"));
  if (metadata.policy_decision !== "deny") {
    throw new Error("baseline valid/mandated-denied-action no longer carries policy_decision=deny");
  }
  metadata.policy_decision = "allow";
  mutated["metadata.json"] = new TextEncoder().encode(JSON.stringify(metadata) + "\n");
  const receipt = JSON.parse(Buffer.from(mutated["overt_receipt.json"]).toString("utf8"));
  if (receipt.policy?.decision !== "deny") {
    throw new Error("baseline receipt no longer carries policy.decision=deny");
  }
  receipt.policy.decision = "allow";
  mutated["overt_receipt.json"] = new TextEncoder().encode(JSON.stringify(receipt) + "\n");
  await writeVector(
    path.join(root, "test-vectors/invalid"),
    "profile-form-policy-rewrite",
    rezip(mutated),
    [
      "verify=false",
      "diagnostic=canonical.bin does not match a supported canonical form.",
    ],
    {
      description:
        "valid/mandated-denied-action with policy_decision flipped deny->allow in metadata.json AND overt_receipt.json after signing — the identical rewrite that boundary/response-only-unsigned-policy-tamper performs on a response-only package, where it succeeds. Under the profile canonical form metadata.json is inside canonical.bin, so the rewrite no longer reproduces the signed bytes and verification fails at the canonical-form check, before the signature is even consulted.",
      expect: {
        valid: false,
        canonicalForm: null,
        failureReason: "canonical.bin does not match a supported canonical form.",
        checks: {
          "canonical-profile": { verdict: "fail", enforced: true },
          "canonical-response-only": { verdict: "fail", enforced: true },
          "mandate-signature": { verdict: "not_assessed", enforced: false, reason: "short_circuited" },
        },
      },
    },
  );
}

// 13. boundary/reauthored-package-issuer-substitution: the rewrite class
//     that the profile canonical form does NOT close. The adversary flips
//     the decision, recomputes canonical.bin, hash.sha256 and the receipt
//     content_hash, and re-signs with a key of its own, swapping
//     public_key.pem. Every internal obligation then holds — including the
//     mandate's own signature, which binds the grant and not the decision —
//     and the package verifies, because nothing in the package names the
//     issuer the reader expected. Only a caller-supplied trusted-signer
//     list (spec §8.1) separates the two, and lib/test/signer-pinning.test.ts
//     verifies this same frozen package both ways.
{
  const adversaryPrivate = readFileSync(path.join(KEYS_DIR, "reauthoring-adversary-4096.key"), "utf8");
  const adversaryPublic = readFileSync(path.join(KEYS_DIR, "reauthoring-adversary-4096.pem"), "utf8");
  const { canonical } = await import(new URL("../lib/dist/canonical.js", import.meta.url).href);
  const { sha256, toHex } = await import(new URL("../lib/dist/hash.js", import.meta.url).href);
  const TE = new TextEncoder();

  const mutated = { ...unzipSync(mandatedDenied) };
  const metadata = JSON.parse(Buffer.from(mutated["metadata.json"]).toString("utf8"));
  metadata.policy_decision = "allow";
  mutated["metadata.json"] = TE.encode(JSON.stringify(metadata) + "\n");
  const canonicalBytes = canonical({
    responseBytes: mutated["response.txt"],
    metadataBytes: jcs(metadata),
  });
  mutated["canonical.bin"] = canonicalBytes;
  const hashHex = toHex(await sha256(canonicalBytes));
  mutated["hash.sha256"] = TE.encode(hashHex + "\n");
  const receipt = JSON.parse(Buffer.from(mutated["overt_receipt.json"]).toString("utf8"));
  receipt.policy.decision = "allow";
  receipt.content_hash = "sha256:" + hashHex;
  mutated["overt_receipt.json"] = TE.encode(JSON.stringify(receipt) + "\n");
  const resign = createSign("sha256");
  resign.update(canonicalBytes);
  resign.end();
  mutated["signature.sig"] = TE.encode(resign.sign(adversaryPrivate).toString("base64") + "\n");
  mutated["public_key.pem"] = TE.encode(adversaryPublic.endsWith("\n") ? adversaryPublic : adversaryPublic + "\n");

  await writeVector(
    path.join(root, "test-vectors/boundary"),
    "reauthored-package-issuer-substitution",
    rezip(mutated),
    ["verify=true"],
    {
      description:
        "valid/mandated-denied-action re-authored end to end by an adversary holding a key of its own: policy_decision flipped deny->allow, canonical.bin, hash.sha256 and the receipt content_hash recomputed, signature.sig re-made and public_key.pem swapped. The profile canonical form does not close this class — every obligation inside the package holds, and the signed mandate still verifies, because a mandate binds the grant and not the decision. The package is authentic evidence of a DIFFERENT issuer's claim. Only spec §8.1 issuer pinning tells them apart: with the real issuer key in trustedSignerPems the same bytes verify false (lib/test/signer-pinning.test.ts).",
      expect: {
        valid: true,
        canonicalForm: "profile",
        mandate: { claimed: true, bound: true, signatureVerified: true, inScope: true },
        checks: {
          "rsa-signature": { verdict: "pass", enforced: true },
          "signer-key-pinned": { verdict: "not_assessed", enforced: false, reason: "option_disabled" },
          "mandate-signature": { verdict: "pass", enforced: true },
        },
      },
    },
    // The boundary tree's suite reads expected-boundary.json.
    "expected-boundary.json",
  );
}

process.stdout.write(`\nGenerated 3 valid + 9 mandate + 1 invalid + 1 boundary vector.\n`);
