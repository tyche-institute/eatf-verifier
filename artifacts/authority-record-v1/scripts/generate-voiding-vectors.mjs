#!/usr/bin/env node
/**
 * Generate the voiding + accepting-authority test vectors (spec §4.3, §4.4).
 *
 * One valid conformance vector plus eleven behavioural vectors:
 *
 *   valid/voided-and-authorized             (profile; valid acceptance; voiding all holding both times)
 *   valid/co-located-authority              (profile; BOTH deontic authorizing_principal + epistemic accepting_authority over the same signed bytes; distinct principals)
 *   voiding/voided-registry-at-signing      (withdrawn before genTime -> voided at both instants)
 *   voiding/diverged-registry-status        (withdrawn between genTime and now -> the (holds, voided) PAIR)
 *   voiding/forward-dated-withdrawal         (withdrawal effective in the future -> holds at both; French notAfter pattern, SYNTHETIC)
 *   voiding/unknown-voiding-type            (unknown type -> not-assessed, never holds)
 *   voiding/stale-telemetry                 (telemetry already stale at genTime -> voided)
 *   voiding/missing-snapshot-input          (registry-status with no snapshot -> unknown, not holds)
 *   voiding/tampered-acceptance             (acceptance.json rewritten after signing -> REJECTED)
 *   voiding/acceptance-policy-mismatch      (acceptance.json policy != accepting_authority -> REJECTED)
 *   voiding/expired-acceptance              (validity window ends before genTime -> temporalContainment fails, ACCEPTED)
 *   voiding/authority-key-substitution      (key binding OK, role fails against trust list — reported SEPARATELY, ACCEPTED)
 *   voiding/response-only-with-authority    (accepting_authority in a response-only bundle -> unbound, REJECTED)
 *
 * The three rejections are the §4.3 binding family, promoted to gating on
 * 2026-08-13: `accepting-authority-binding` and `accepting-authority-key-binding`
 * now decide `valid`, on the §4.5 rule (new surface, no compatibility debt).
 * Temporal containment and role remain appraisal, which is why the two
 * vectors that exercise them still verify true. The isolated single-property
 * negatives live under test-vectors/acceptance/ (scripts/generate-acceptance-vectors.mjs).
 *
 * The accepting-authority fixture is accepted by the committed
 * test-accepting-authority TEST principal. Who signs acceptance in production
 * is a governance decision out of scope here (see test-vectors/keys/README.md).
 *
 * Registry snapshots are CALLER-SUPPLIED inputs (never packaged in the .aep):
 * each behavioural vector's expected-voiding.json carries them inline under
 * `options.registrySnapshot.inline`, and both this generator and
 * lib/test/voiding-vectors.test.ts resolve them the same way.
 *
 * Requires the library to be built first:
 *
 *   (cd lib && npm install && npm run build)
 *   node scripts/generate-voiding-vectors.mjs
 *
 * Determinism: created_at / accepted_at fixed, the RFC 3161 token reused
 * verbatim from valid-overt-profile/package.aep (genTime 2026-01-01), JCS and
 * RSASSA-PKCS1-v1_5 deterministic, ZIP entry timestamps pinned. Re-running
 * produces byte-identical .aep files; run `git diff --quiet` to confirm.
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

const VALID_OUT = path.join(root, "test-vectors/valid/voided-and-authorized");
const VOIDING_OUT = path.join(root, "test-vectors/voiding");
const KEYS_DIR = path.join(root, "test-vectors/keys");
const TSR_SOURCE = path.join(root, "test-vectors/valid/valid-overt-profile/package.aep");

const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);
const TEXT_ENC = new TextEncoder();

let sign, verify, jcs;
try {
  ({ sign, verify } = await import(new URL("../lib/dist/index.js", import.meta.url).href));
  ({ jcs } = await import(new URL("../lib/dist/canonical.js", import.meta.url).href));
} catch (e) {
  process.stderr.write(`\
generate-voiding-vectors: cannot load ../lib/dist/.
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
  attestation_id: "att_voided_and_authorized_01",
  created_at: "2026-08-05T00:00:00Z",
  agent_id: "urn:eatf:tenant:demo:agent:voiding-demo",
  action_type: "foundational:aep-response",
  policy_id: "atap-basic",
  policy_version: "1.0",
  policy_coverage: 1.0,
  policy_decision: "allow",
  format_version: "ATAP-1.0",
};

const ACCEPTING_AUTHORITY = {
  principal: "test-accepting-authority",
  policy_id: "atap-basic",
  policy_version: "1.0",
  validity: { not_before: "2025-07-01T00:00:00Z", not_after: "2026-07-01T00:00:00Z" },
};

// Deontic authorizing principal (mandate-layer reference only; the verifier
// assigns it NO validity semantics — see schemas/aep-v1.schema.json). Its
// principal identifier is deliberately DISTINCT from the epistemic
// accepting_authority principal so the co-located vector exercises the
// "principals differ" axis of the F11 census. The mandate itself lives in the
// mandate layer and is NOT resolved here.
const AUTHORIZING_PRINCIPAL = {
  principal: "urn:eatf:mandate:demo:granting-authority",
  mandate_ref: "urn:eatf:mandate:demo:mandate:0001",
};

/** Build a detached acceptance {json, sig}: the authority signs JCS(record). */
function makeAcceptance(recordOverrides = {}, signWithKey = authorityPrivate, publicKey = authorityPublic) {
  const record = {
    principal: "test-accepting-authority",
    policy_id: "atap-basic",
    policy_version: "1.0",
    accepted_at: "2026-08-05T00:00:00Z",
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
  voiding,
  acceptingAuthority,
  acceptance,
  canonicalForm = "profile",
} = {}) {
  const result = await sign({
    payload: "EATF voiding+authority demo: per-output voiding and epistemic acceptance.\n",
    privateKeyPem: devPrivate,
    publicKeyPem: devPublic,
    metadata,
    overtScope: "foundational:aep-response",
    timestampTsr,
    canonicalForm,
    voiding,
    acceptingAuthority,
    acceptance,
  });
  return result.aep;
}

/** Resolve the inline snapshot / trust-list references into real VerifyOptions. */
function resolveOptions(raw) {
  if (!raw) return {};
  const opts = {};
  if (raw.tsaTrustList !== undefined) opts.tsaTrustList = raw.tsaTrustList;
  if (raw.supersessionList) opts.supersessionList = raw.supersessionList;
  if (raw.registrySnapshot && raw.registrySnapshot.inline) {
    opts.registrySnapshot = {
      bytes: TEXT_ENC.encode(JSON.stringify(raw.registrySnapshot.inline)),
      date: raw.registrySnapshot.date,
    };
  }
  if (raw.authorityTrustListKeys) {
    opts.authorityTrustList = raw.authorityTrustListKeys.map((k) =>
      readFileSync(path.join(KEYS_DIR, `${k}.pem`), "utf8"),
    );
  }
  return opts;
}

async function writeVector(dir, name, packageBytes, verifyExpectedLines, expected) {
  const options = resolveOptions(expected.options);
  const result = await verify(packageBytes, options);
  if (result.valid !== expected.expect.valid) {
    throw new Error(
      `${name}: self-check failed (valid=${result.valid}, expected ${expected.expect.valid}): ${result.failureReason}`,
    );
  }
  for (const ev of expected.expect.voiding ?? []) {
    const actual = (result.voidingVerdicts ?? []).find((v) => v.id === ev.id);
    if (!actual) throw new Error(`${name}: voiding verdict ${ev.id} missing`);
    for (const [k, v] of Object.entries(ev)) {
      if (actual[k] !== v) {
        throw new Error(`${name}: voiding.${ev.id}.${k}=${actual[k]}, expected ${v}`);
      }
    }
  }
  if (expected.expect.acceptingAuthority) {
    const aa = result.acceptingAuthority;
    if (!aa) throw new Error(`${name}: acceptingAuthority is null`);
    for (const [k, v] of Object.entries(expected.expect.acceptingAuthority)) {
      if (aa[k] !== v) throw new Error(`${name}: acceptingAuthority.${k}=${aa[k]}, expected ${v}`);
    }
  }
  const out = path.join(dir, name);
  mkdirSync(out, { recursive: true });
  writeFileSync(path.join(out, "package.aep"), Buffer.from(packageBytes));
  writeFileSync(path.join(out, "verify-expected.txt"), verifyExpectedLines.join("\n") + "\n");
  writeFileSync(path.join(out, "expected-voiding.json"), JSON.stringify(expected, null, 2) + "\n");
  process.stdout.write(`  ok  ${name}\n`);
}

function rezip(entries) {
  return zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME });
}

const snapshotDate = "2026-06-01T00:00:00Z";
const snapshotInline = (entry) => ({
  registrySnapshot: { inline: { registry: "demo-status-registry", entries: { "atap-basic:1.0": entry } }, date: snapshotDate },
});

// 0. valid/voided-and-authorized ------------------------------------------
{
  const voiding = [
    { id: "reg-atap", type: "registry-status", subject: { entry_id: "atap-basic:1.0" }, on_true: "void" },
    { id: "telemetry-fresh", type: "telemetry-freshness", subject: { sampled_at: "2025-12-31T23:00:00Z", max_age_seconds: 86400 }, on_true: "degrade" },
  ];
  const aep = await signPackage({ voiding, acceptingAuthority: ACCEPTING_AUTHORITY, acceptance: makeAcceptance() });
  await writeVector(path.dirname(VALID_OUT), path.basename(VALID_OUT), aep, ["verify=true"], {
    description:
      "Profile canonical form with a valid detached acceptance and two voiding predicates that hold at both evaluation instants: the atap-basic:1.0 registry entry is active, and the telemetry sample is within its max age. Under default (no-snapshot) options the registry predicate reads unknown; the conformance harness only requires valid=true.",
    options: snapshotInline({ status: "active" }),
    expect: {
      valid: true,
      canonicalForm: "profile",
      voiding: [
        { id: "reg-atap", verdict: "holds", atSigning: "holds", now: "holds" },
        { id: "telemetry-fresh", verdict: "holds" },
      ],
      acceptingAuthority: { keyBindingValid: true, boundToOutput: true, temporalContainment: true, roleVerified: null },
      checks: {
        "voiding-predicates": { verdict: "pass", enforced: false },
        "accepting-authority-binding": { verdict: "pass", enforced: true },
        "accepting-authority-key-binding": { verdict: "pass", enforced: true },
        "accepting-authority-temporal": { verdict: "pass", enforced: false },
        "accepting-authority-role": { verdict: "not_determinate", enforced: false, reason: "input_absent" },
      },
    },
  });
}

// 0b. valid/co-located-authority ------------------------------------------
// ONE package carrying BOTH the deontic authorizing_principal and the
// epistemic accepting_authority over the SAME signed action bytes (profile
// canonical form). This is the co-located case F11 was previously unable to
// exercise, built entirely inside eatf with no machine-mandate dependency:
// the deontic layer is represented as an attested in-package reference with no
// validity semantics. The two principals are distinct identifiers.
{
  const voiding = [
    { id: "reg-atap", type: "registry-status", subject: { entry_id: "atap-basic:1.0" }, on_true: "void" },
  ];
  const metadata = {
    ...baseMetadata,
    attestation_id: "att_co_located_authority_01",
    authorizing_principal: AUTHORIZING_PRINCIPAL,
  };
  const aep = await signPackage({
    metadata,
    voiding,
    acceptingAuthority: ACCEPTING_AUTHORITY,
    acceptance: makeAcceptance(),
  });
  await writeVector(path.join(root, "test-vectors/valid"), "co-located-authority", aep, ["verify=true"], {
    description:
      "Profile canonical form carrying BOTH layers over the same signed action bytes: a deontic authorizing_principal (urn:eatf:mandate:demo:granting-authority, an attested mandate-layer reference the verifier assigns no validity semantics) and an epistemic accepting_authority (test-accepting-authority, a valid bound detached acceptance). The two named principals are distinct, so the F11 census counts this package as co-located with differing principals. Voiding predicate holds. Verifies valid; both layers are informational and do not flip valid.",
    options: snapshotInline({ status: "active" }),
    expect: {
      valid: true,
      canonicalForm: "profile",
      voiding: [{ id: "reg-atap", verdict: "holds", atSigning: "holds", now: "holds" }],
      acceptingAuthority: { keyBindingValid: true, boundToOutput: true, temporalContainment: true, roleVerified: null },
    },
  });
}

// 1. voided-registry-at-signing -------------------------------------------
{
  const voiding = [{ id: "reg-withdrawn", type: "registry-status", subject: { entry_id: "atap-basic:1.0" }, on_true: "void" }];
  const aep = await signPackage({ voiding });
  await writeVector(VOIDING_OUT, "voided-registry-at-signing", aep, ["verify=true"], {
    description:
      "The atap-basic:1.0 registry entry was withdrawn 2025-06-01, before the package's genTime (2026-01-01). Both dual-time evaluations report voided; the output was already void at signing. Informational — the package stays accepted.",
    options: snapshotInline({ status: "withdrawn", withdrawn_at: "2025-06-01T00:00:00Z" }),
    expect: {
      valid: true,
      voiding: [{ id: "reg-withdrawn", verdict: "voided", atSigning: "voided", now: "voided" }],
      checks: { "voiding-predicates": { verdict: "pass", enforced: false } },
    },
  });
}

// 2. diverged-registry-status ---------------------------------------------
{
  const voiding = [{ id: "reg-diverged", type: "registry-status", subject: { entry_id: "atap-basic:1.0" }, on_true: "void" }];
  const aep = await signPackage({ voiding });
  await writeVector(VOIDING_OUT, "diverged-registry-status", aep, ["verify=true"], {
    description:
      "The registry entry was withdrawn 2026-03-01 — after the genTime (2026-01-01) but before the snapshot instant (2026-06-01). The verdict PAIR (atSigning=holds, now=voided) is surfaced and never collapsed: authorised at signing, void now. This is the registry-half-life divergence rendered as a per-output machine verdict.",
    options: snapshotInline({ status: "withdrawn", withdrawn_at: "2026-03-01T00:00:00Z" }),
    expect: {
      valid: true,
      voiding: [{ id: "reg-diverged", verdict: "voided", atSigning: "holds", now: "voided" }],
      reportIncludes: [
        "Voiding predicates evaluated (1): 1 voided, 1 with a diverged at-signing/now pair (informational).",
      ],
    },
  });
}

// 3. forward-dated-withdrawal (SYNTHETIC, modelled on the French notAfter) --
{
  const voiding = [{ id: "reg-forward", type: "registry-status", subject: { entry_id: "atap-basic:1.0" }, on_true: "void" }];
  const aep = await signPackage({ voiding });
  await writeVector(VOIDING_OUT, "forward-dated-withdrawal", aep, ["verify=true"], {
    description:
      "A SYNTHETIC vector modelled on the forward-dated French registry withdrawal pattern (a notAfter/withdrawal timestamp in the future): the withdrawal is effective 2027-01-01, after both the genTime and the snapshot instant. A correct time comparison must NOT treat the entry as withdrawn now — both instants report holds. This exercises the time-comparison logic against premature voiding; no real registry data is copied into eatf.",
    options: snapshotInline({ status: "active", withdrawn_at: "2027-01-01T00:00:00Z" }),
    expect: {
      valid: true,
      voiding: [{ id: "reg-forward", verdict: "holds", atSigning: "holds", now: "holds" }],
    },
  });
}

// 4. unknown-voiding-type -------------------------------------------------
{
  const voiding = [{ id: "weird", type: "quantum-flux-collapse", subject: {}, on_true: "void" }];
  const aep = await signPackage({ voiding });
  await writeVector(VOIDING_OUT, "unknown-voiding-type", aep, ["verify=true"], {
    description:
      "A voiding predicate of a type the verifier does not understand. It MUST yield not-assessed (reason unknown_type), never holds: an unrecognised predicate is not silently satisfied. (Not schema-validated in CI — carried under test-vectors/voiding/, not valid/.)",
    expect: {
      valid: true,
      voiding: [{ id: "weird", verdict: "not-assessed", reason: "unknown_type" }],
    },
  });
}

// 5. stale-telemetry ------------------------------------------------------
{
  const voiding = [{ id: "tel-stale", type: "telemetry-freshness", subject: { sampled_at: "2025-01-01T00:00:00Z", max_age_seconds: 3600 }, on_true: "void" }];
  const aep = await signPackage({ voiding });
  await writeVector(VOIDING_OUT, "stale-telemetry", aep, ["verify=true"], {
    description:
      "The telemetry underlying the decision was sampled a year before the genTime, far beyond its 3600-second max age: it was already stale at signing time, so the predicate reports voided. Judged offline against the RFC 3161 genTime — no extra caller input.",
    expect: {
      valid: true,
      voiding: [{ id: "tel-stale", verdict: "voided" }],
    },
  });
}

// 6. missing-snapshot-input -----------------------------------------------
{
  const voiding = [{ id: "reg-nosnap", type: "registry-status", subject: { entry_id: "atap-basic:1.0" }, on_true: "void" }];
  const aep = await signPackage({ voiding });
  await writeVector(VOIDING_OUT, "missing-snapshot-input", aep, ["verify=true"], {
    description:
      "A registry-status predicate verified WITHOUT a caller-supplied registry snapshot. It MUST yield unknown (reason input_absent) at both instants — never holds. A verdict is only ever asserted relative to a named snapshot.",
    expect: {
      valid: true,
      voiding: [{ id: "reg-nosnap", verdict: "unknown", atSigning: "unknown", now: "unknown", reason: "input_absent" }],
    },
  });
}

// 7. tampered-acceptance --------------------------------------------------
{
  const aep = await signPackage({ acceptingAuthority: ACCEPTING_AUTHORITY, acceptance: makeAcceptance() });
  const entries = unzipSync(aep);
  const mutated = { ...entries };
  const record = JSON.parse(Buffer.from(mutated["acceptance.json"]).toString("utf8"));
  record.principal = "attacker-principal";
  mutated["acceptance.json"] = jcs(record);
  await writeVector(VOIDING_OUT, "tampered-acceptance", rezip(mutated), [
    "verify=false",
    "diagnostic=acceptance invalid: digest does not match accepting_authority.acceptance_digest.",
  ], {
    description:
      "The detached acceptance.json was rewritten after signing (principal changed). acceptance.sig no longer verifies over the tampered bytes (keyBindingValid=false) and the digest no longer matches the signed metadata (boundToOutput=false). Both gating §4.3 checks fail and the package is REJECTED; output binding is reported first, in registry order. Until the §4.3 binding family was promoted this package verified valid:true with the tamper reported beside the verdict.",
    expect: {
      valid: false,
      failureReason: "acceptance invalid: digest does not match accepting_authority.acceptance_digest.",
      acceptingAuthority: { keyBindingValid: false, boundToOutput: false, temporalContainment: true },
      checks: {
        "accepting-authority-key-binding": { verdict: "fail", enforced: true },
        "accepting-authority-binding": { verdict: "fail", enforced: true },
      },
    },
  });
}

// 8. acceptance-policy-mismatch -------------------------------------------
{
  const acceptance = makeAcceptance({ policy_id: "atap-extended" });
  const aep = await signPackage({ acceptingAuthority: ACCEPTING_AUTHORITY, acceptance });
  await writeVector(VOIDING_OUT, "acceptance-policy-mismatch", aep, [
    "verify=false",
    "diagnostic=acceptance invalid: acceptance policy_id does not match accepting_authority.policy_id.",
  ], {
    description:
      "The detached acceptance is authentically signed (keyBindingValid=true) and its digest matches, but its policy_id (atap-extended) does not agree with metadata.accepting_authority (atap-basic): the acceptance is not bound to this output (boundToOutput=false). Authenticity and binding are separate properties; an authentic acceptance of a different policy is still not an acceptance of THIS output, and the package is REJECTED. Until the §4.3 binding family was promoted it verified valid:true.",
    expect: {
      valid: false,
      failureReason: "acceptance invalid: acceptance policy_id does not match accepting_authority.policy_id.",
      acceptingAuthority: { keyBindingValid: true, boundToOutput: false, temporalContainment: true },
      checks: {
        "accepting-authority-key-binding": { verdict: "pass", enforced: true },
        "accepting-authority-binding": { verdict: "fail", enforced: true },
      },
    },
  });
}

// 9. expired-acceptance ---------------------------------------------------
{
  const acceptingAuthority = {
    ...ACCEPTING_AUTHORITY,
    validity: { not_before: "2025-01-01T00:00:00Z", not_after: "2025-12-01T00:00:00Z" },
  };
  const aep = await signPackage({ acceptingAuthority, acceptance: makeAcceptance() });
  await writeVector(VOIDING_OUT, "expired-acceptance", aep, ["verify=true"], {
    description:
      "The acceptance is authentic and bound, but its validity window closed 2025-12-01, before the package's genTime (2026-01-01): temporalContainment=false. This is the enforced/advisory line inside §4.3: the two binding-family checks gate, temporal containment is appraisal and does not reject. What lapsed is the licence, not the binding, and the genTime it is judged against is only as good as a TSA trust anchor the package cannot supply. The exact mirror of mandate/mandate-expired.",
    expect: {
      valid: true,
      acceptingAuthority: { keyBindingValid: true, boundToOutput: true, temporalContainment: false },
      checks: {
        "accepting-authority-binding": { verdict: "pass", enforced: true },
        "accepting-authority-key-binding": { verdict: "pass", enforced: true },
        "accepting-authority-temporal": { verdict: "fail", enforced: false },
      },
    },
  });
}

// 10. authority-key-substitution ------------------------------------------
{
  // The acceptance keeps the authority's principal name but is signed with,
  // and embeds, a DIFFERENT key (the packaging dev key). The signature is
  // self-consistent (keyBindingValid=true), but the key is not in the
  // caller's authorityTrustList, so role verification fails — reported
  // SEPARATELY from key binding.
  const acceptance = makeAcceptance({}, devPrivate, devPublic);
  const aep = await signPackage({ acceptingAuthority: ACCEPTING_AUTHORITY, acceptance });
  await writeVector(VOIDING_OUT, "authority-key-substitution", aep, ["verify=true"], {
    description:
      "The acceptance names test-accepting-authority but is signed with — and carries — a substituted key. The signature is internally consistent, so key binding passes; role verification against the caller's authorityTrustList (the genuine authority key) fails. Key binding and role are reported separately, and only key binding gates: role is undecidable from the package alone — without a caller-supplied trust list there is nothing to decide membership against — so a substituted key is reported and the package stays accepted. This is what the self-attestation trust model costs on the acceptance side, exactly as boundary/reauthored-package-issuer-substitution is what it costs on the issuer side.",
    options: { authorityTrustListKeys: ["test-accepting-authority"] },
    expect: {
      valid: true,
      acceptingAuthority: { keyBindingValid: true, boundToOutput: true, temporalContainment: true, roleVerified: false },
      checks: {
        "accepting-authority-binding": { verdict: "pass", enforced: true },
        "accepting-authority-key-binding": { verdict: "pass", enforced: true },
        "accepting-authority-role": { verdict: "fail", enforced: false },
      },
    },
  });
}

// 11. response-only-with-authority ----------------------------------------
{
  const aep = await signPackage({ acceptingAuthority: ACCEPTING_AUTHORITY, acceptance: makeAcceptance(), canonicalForm: "response-only" });
  await writeVector(VOIDING_OUT, "response-only-with-authority", aep, [
    "verify=false",
    "diagnostic=acceptance invalid: the response-only canonical form leaves metadata.accepting_authority outside signature.sig.",
  ], {
    description:
      "The canonical-form overclaim guard: a valid acceptance packaged under the response-only canonical form. The whole accepting_authority block lies outside signature.sig and is rewritable, so boundToOutput=false even though the detached signature still verifies. §4.3 is surface added in this work and carries no compatibility debt to the response-only form, so — as with §4.5 — an accepting_authority in a response-only bundle is REJECTED rather than flagged. Until the binding family was promoted it verified valid:true with the overclaim reported beside the verdict.",
    expect: {
      valid: false,
      failureReason: "acceptance invalid: the response-only canonical form leaves metadata.accepting_authority outside signature.sig.",
      canonicalForm: "response-only",
      acceptingAuthority: { keyBindingValid: true, boundToOutput: false, temporalContainment: true },
      checks: { "accepting-authority-binding": { verdict: "fail", enforced: true } },
      reportIncludes: [
        "Accepting authority present but unbound: the response-only canonical form leaves metadata.accepting_authority outside signature.sig.",
      ],
    },
  });
}

process.stdout.write(`\nGenerated 2 valid + 11 voiding/accepting-authority vectors.\n`);
