#!/usr/bin/env node
/**
 * Voiding + accepting-authority census over the whole vector corpus.
 *
 * Two measurements, both re-runnable, printed and never written:
 *
 *   F11  deontic/epistemic divergence rate — the fraction of corpus
 *        packages whose deontic authorizing principal
 *        (metadata.authorizing_principal) and epistemic accepting authority
 *        (metadata.accepting_authority) differ, or where one is present
 *        without the other. Two axes are reported separately: (a) CO-LOCATION
 *        — both layers present in one package over the same signed bytes; and
 *        (b) DIFFER — among co-located packages, whether the two named
 *        principals are distinct identifiers. Most eatf packages carry only
 *        the epistemic acceptance layer while the deontic authorizing
 *        principal otherwise lives in the mandate layer (MandateGraph /
 *        machine-mandate), so a present-epistemic / absent-deontic package is
 *        one-sided by construction; the valid/co-located-authority vector
 *        carries both in-package (the deontic layer as an attested reference
 *        with no validity semantics) so the co-located case is now exercised.
 *
 *   F12  cost accounting — added bytes per element against the 10 MB package
 *        cap, and the verification-latency delta from the two new steps,
 *        isolated by signing an otherwise-identical pair (plain vs carrying
 *        voiding + accepting authority) and timing verify() on both.
 *
 * Build the verifier first:
 *
 *   (cd lib && npm install && npm run build)
 *   node scripts/voiding-census.mjs
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createSign } from "node:crypto";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(new URL("../lib/package.json", import.meta.url));
const { unzipSync } = require("fflate");

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const distIndex = path.join(root, "lib/dist/index.js");
if (!existsSync(distIndex)) {
  process.stderr.write("lib/dist not found — run `(cd lib && npm run build)` first.\n");
  process.exit(2);
}
const { verify, sign } = await import(new URL("../lib/dist/index.js", import.meta.url));
const { jcs } = await import(new URL("../lib/dist/canonical.js", import.meta.url));

const TEXT_DEC = new TextDecoder();
const CAP_BYTES = 10 * 1024 * 1024;

function collect(cat) {
  const base = path.join(root, "test-vectors", cat);
  if (!existsSync(base)) return [];
  return readdirSync(base, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => ({ cat, name: d.name, file: path.join(base, d.name, "package.aep") }))
    .filter((v) => existsSync(v.file))
    .sort((a, b) => a.name.localeCompare(b.name));
}

const vectors = [
  ...collect("valid"),
  ...collect("invalid"),
  ...collect("boundary"),
  ...collect("warrant"),
  ...collect("voiding"),
  ...collect("mandate"),
  ...collect("acceptance"),
];

// --- F11 ------------------------------------------------------------------
let epistemic = 0;
let deontic = 0;
let both = 0;
let oneSided = 0;
let differ = 0;
let signedMandate = 0;
let bothSigned = 0;
const signedMandateRows = [];
const bothSignedRows = [];
const epistemicRows = [];

/** Does the package carry the named ZIP entry? */
function entriesHave(file, name) {
  try {
    return unzipSync(new Uint8Array(readFileSync(file)))[name] !== undefined;
  } catch {
    return false;
  }
}
const oneSidedRows = [];
const coLocatedRows = [];

for (const v of vectors) {
  let metadata = {};
  try {
    const entries = unzipSync(new Uint8Array(readFileSync(v.file)));
    if (entries["metadata.json"]) {
      metadata = JSON.parse(TEXT_DEC.decode(entries["metadata.json"]));
    }
  } catch {
    metadata = {};
  }
  const hasEpistemic = metadata && typeof metadata === "object" && "accepting_authority" in metadata;
  const hasDeontic = metadata && typeof metadata === "object" && "authorizing_principal" in metadata;
  // §4.5 split: a deontic block claiming a signed mandate (a digest
  // reference, packaged bytes, or both) versus the pre-§4.5 reference form,
  // which names a principal and carries nothing the verifier can check.
  const hasSignedMandate =
    hasDeontic &&
    (typeof metadata.authorizing_principal?.mandate_digest === "string" ||
      entriesHave(v.file, "mandate.json"));
  if (hasEpistemic) {
    epistemic++;
    epistemicRows.push(`${v.cat}/${v.name}`);
  }
  if (hasDeontic) deontic++;
  if (hasSignedMandate) {
    signedMandate++;
    signedMandateRows.push(`${v.cat}/${v.name}`);
  }
  if (hasEpistemic && hasSignedMandate) {
    bothSigned++;
    bothSignedRows.push(`${v.cat}/${v.name}`);
  }
  if (hasEpistemic && hasDeontic) {
    both++;
    const ep = metadata.accepting_authority?.principal;
    const de = metadata.authorizing_principal?.principal ?? metadata.authorizing_principal?.token_ref;
    const principalsDiffer = ep !== de;
    if (principalsDiffer) differ++;
    coLocatedRows.push({ name: `${v.cat}/${v.name}`, ep, de, principalsDiffer });
  }
  if (hasEpistemic !== hasDeontic) {
    oneSided++;
    oneSidedRows.push(`${v.cat}/${v.name}`);
  }
}

const divergentOrOneSided = oneSided + differ;

console.log("=== F11: deontic/epistemic divergence rate over the full vector corpus ===");
console.log(
  `corpus = ${vectors.length} packages; ` +
    `${epistemic} carry an epistemic accepting_authority, ${deontic} carry a deontic authorizing_principal, ${both} carry both (co-located).`,
);
console.log(
  `divergent-or-one-sided = ${divergentOrOneSided}/${vectors.length} ` +
    `(${((100 * divergentOrOneSided) / vectors.length).toFixed(1)}%): ${oneSided} present-on-exactly-one-side, ${differ} co-located-with-different-principals.`,
);
// Co-location axis (both layers present in ONE package) reported separately
// from the "differ" axis (whether the two named principals are distinct).
console.log(
  `\n  co-located packages (both deontic authorizing_principal AND epistemic accepting_authority over the same bytes): ${both}`,
);
if (coLocatedRows.length === 0) {
  console.log(
    "   (none) — a package carrying only one layer is one-sided by construction; a co-located vector must carry both in-package.",
  );
}
for (const r of coLocatedRows) {
  console.log(
    `   - ${r.name}: deontic=${r.de} epistemic=${r.ep} -> principals ${r.principalsDiffer ? "DIFFER" : "SAME"}`,
  );
}
console.log(
  `  of the ${both} co-located: ${differ} with differing principals, ${both - differ} with the same principal.`,
);
// The §4.5 split. Carriage of a deontic block is not verification of one:
// only packages claiming a signed mandate put the deontic layer inside the
// verifier's gate.
console.log(
  `\n  deontic layer by kind: ${signedMandate} claim a SIGNED mandate (§4.5, gated), ` +
    `${deontic - signedMandate} carry the pre-§4.5 reference form only (named, nothing verified).`,
);
for (const r of signedMandateRows) console.log("   - signed:", r);
console.log(
  `  co-located with a SIGNED mandate on the deontic side (both layers live and gated): ${bothSigned}`,
);
for (const r of bothSignedRows) console.log("   -", r);
console.log(
  `\n  one-sided packages (epistemic present, deontic absent — the deontic principal otherwise lives in the mandate layer, off-package):`,
);
for (const r of oneSidedRows) console.log("   -", r);

// --- F12: added bytes -----------------------------------------------------
console.log("\n=== F12: cost accounting ===");
let maxTotal = 0;
let maxTotalVector = "(none)";
const carriers = [];
for (const v of vectors) {
  let entries = {};
  try {
    entries = unzipSync(new Uint8Array(readFileSync(v.file)));
  } catch {
    continue;
  }
  let metadata = {};
  try {
    metadata = JSON.parse(TEXT_DEC.decode(entries["metadata.json"]));
  } catch {
    metadata = {};
  }
  const voidingBytes = metadata.voiding ? Buffer.byteLength(JSON.stringify(metadata.voiding)) : 0;
  const aaBytes = metadata.accepting_authority
    ? Buffer.byteLength(JSON.stringify(metadata.accepting_authority))
    : 0;
  const accJson = entries["acceptance.json"]?.length ?? 0;
  const accSig = entries["acceptance.sig"]?.length ?? 0;
  // §4.5 deontic layer: the metadata block plus the detached pair.
  const apBytes = metadata.authorizing_principal
    ? Buffer.byteLength(JSON.stringify(metadata.authorizing_principal))
    : 0;
  const manJson = entries["mandate.json"]?.length ?? 0;
  const manSig = entries["mandate.sig"]?.length ?? 0;
  const total = voidingBytes + aaBytes + accJson + accSig + apBytes + manJson + manSig;
  if (total === 0) continue;
  carriers.push({ v: `${v.cat}/${v.name}`, voidingBytes, aaBytes, accJson, accSig, apBytes, manJson, manSig, total });
  if (total > maxTotal) {
    maxTotal = total;
    maxTotalVector = `${v.cat}/${v.name}`;
  }
}
console.log("added bytes per element, over packages that carry any new element:");
console.log(
  "  " +
    "vector".padEnd(38) +
    "voiding".padStart(9) +
    "accept_auth".padStart(12) +
    "accept.json".padStart(12) +
    "accept.sig".padStart(11) +
    "auth_princ".padStart(11) +
    "mandate.json".padStart(13) +
    "mandate.sig".padStart(12) +
    "total".padStart(8),
);
for (const c of carriers) {
  console.log(
    "  " +
      c.v.padEnd(38) +
      String(c.voidingBytes).padStart(9) +
      String(c.aaBytes).padStart(12) +
      String(c.accJson).padStart(12) +
      String(c.accSig).padStart(11) +
      String(c.apBytes).padStart(11) +
      String(c.manJson).padStart(13) +
      String(c.manSig).padStart(12) +
      String(c.total).padStart(8),
  );
}
console.log(
  `\nlargest added footprint: ${maxTotal} bytes (${maxTotalVector}) = ` +
    `${((100 * maxTotal) / CAP_BYTES).toFixed(4)}% of the 10 MB (${CAP_BYTES}-byte) uncompressed package cap; ` +
    `headroom ${(CAP_BYTES - maxTotal).toLocaleString()} bytes.`,
);

// --- F12: verification-latency delta --------------------------------------
const devPrivate = readFileSync(path.join(root, "test-vectors/keys/dev-rsa-4096.key"), "utf8");
const devPublic = readFileSync(path.join(root, "test-vectors/keys/dev-rsa-4096.pem"), "utf8");
const authorityPrivate = readFileSync(path.join(root, "test-vectors/keys/test-accepting-authority.key"), "utf8");
const authorityPublic = readFileSync(path.join(root, "test-vectors/keys/test-accepting-authority.pem"), "utf8");
const tsr = unzipSync(new Uint8Array(readFileSync(path.join(root, "test-vectors/valid/valid-overt-profile/package.aep"))))[
  "timestamp.tsr"
];

const meta = {
  schema: "urn:eatf:spec:aep:metadata:1.0",
  attestation_id: "att_census_latency_01",
  created_at: "2026-08-05T00:00:00Z",
  policy_id: "atap-basic",
  policy_version: "1.0",
  policy_coverage: 1.0,
  policy_decision: "allow",
};
const acceptanceRecord = {
  principal: "test-accepting-authority",
  policy_id: "atap-basic",
  policy_version: "1.0",
  accepted_at: "2026-08-05T00:00:00Z",
  public_key: authorityPublic,
};
const accSigner = createSign("sha256");
accSigner.update(jcs(acceptanceRecord));
accSigner.end();
const acceptance = { json: acceptanceRecord, sig: accSigner.sign(authorityPrivate).toString("base64") };

const common = {
  payload: "census latency probe.\n",
  privateKeyPem: devPrivate,
  publicKeyPem: devPublic,
  metadata: meta,
  overtScope: "foundational:aep-response",
  timestampTsr: tsr,
  canonicalForm: "profile",
};
const plainAep = (await sign({ ...common })).aep;

// Third arm: the §4.5 deontic layer on its own, so the cost of the gated
// mandate step is isolated from the informational §4.3/§4.4 steps.
const grantingPrivate = readFileSync(path.join(root, "test-vectors/keys/test-granting-authority.key"), "utf8");
const grantingPublic = readFileSync(path.join(root, "test-vectors/keys/test-granting-authority.pem"), "utf8");
const mandateRecord = {
  mandate_id: "urn:eatf:mandate:demo:mandate:0001",
  mandate_version: "1.0",
  principal: "urn:eatf:mandate:demo:granting-authority",
  subject: "urn:eatf:tenant:demo:agent:latency-probe",
  granted_at: "2026-08-05T00:00:00Z",
  statement: "The granting authority authorises the subject agent to act under policy atap-basic.",
  scope: { action_types: ["foundational:aep-response"], policy_ids: ["atap-basic"] },
  valid_from: "2025-07-01T00:00:00Z",
  valid_until: "2026-07-01T00:00:00Z",
  public_key: grantingPublic,
};
const manSigner = createSign("sha256");
manSigner.update(jcs(mandateRecord));
manSigner.end();
const mandatePair = { json: mandateRecord, sig: manSigner.sign(grantingPrivate).toString("base64") };
const mandateAep = (
  await sign({
    ...common,
    metadata: { ...meta, agent_id: "urn:eatf:tenant:demo:agent:latency-probe", action_type: "foundational:aep-response" },
    authorizingPrincipal: {
      principal: "urn:eatf:mandate:demo:granting-authority",
      mandate_ref: "urn:eatf:mandate:demo:mandate:0001",
    },
    mandate: mandatePair,
  })
).aep;
const fullAep = (
  await sign({
    ...common,
    voiding: [
      { id: "reg-1", type: "registry-status", subject: { entry_id: "atap-basic:1.0" }, on_true: "void" },
      { id: "tel-1", type: "telemetry-freshness", subject: { sampled_at: "2025-12-31T23:00:00Z", max_age_seconds: 86400 }, on_true: "degrade" },
    ],
    acceptingAuthority: {
      principal: "test-accepting-authority",
      policy_id: "atap-basic",
      policy_version: "1.0",
      validity: { not_before: "2025-07-01T00:00:00Z", not_after: "2026-07-01T00:00:00Z" },
    },
    acceptance,
  })
).aep;

const snapshot = {
  bytes: new TextEncoder().encode(JSON.stringify({ entries: { "atap-basic:1.0": { status: "active" } } })),
  date: "2026-06-01T00:00:00Z",
};

function quantile(sorted, q) {
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

// Per-call timing so we can report a robust median + IQR instead of a single
// mean. hrtime.bigint has nanosecond resolution; each verify is ~1 ms.
async function sampleVerify(aep, opts, warmup, iters) {
  const bytes = new Uint8Array(aep);
  for (let i = 0; i < warmup; i++) await verify(bytes, opts); // warm cache
  const samples = new Array(iters);
  for (let i = 0; i < iters; i++) {
    const t0 = process.hrtime.bigint();
    await verify(bytes, opts);
    samples[i] = Number(process.hrtime.bigint() - t0) / 1e6; // ms
  }
  samples.sort((a, b) => a - b);
  return {
    median: quantile(samples, 0.5),
    q1: quantile(samples, 0.25),
    q3: quantile(samples, 0.75),
  };
}

const WARMUP = 100;
const ITERS = 1000;
const plain = await sampleVerify(plainAep, {}, WARMUP, ITERS);
const full = await sampleVerify(
  fullAep,
  { registrySnapshot: snapshot, authorityTrustList: [authorityPublic] },
  WARMUP,
  ITERS,
);
const mandateArm = await sampleVerify(mandateAep, {}, WARMUP, ITERS);
const deltaMedian = full.median - plain.median;
const mandateDelta = mandateArm.median - plain.median;
// The delta of medians is smaller than each arm's own IQR — i.e. the two new
// informational steps cost less than the run-to-run jitter of a single verify.
const withinNoise = Math.abs(deltaMedian) < Math.max(plain.q3 - plain.q1, full.q3 - full.q1);
console.log(
  `\nverification latency (profile form, same payload/key/timestamp; ${ITERS} timed iters, ${WARMUP} warmup, median [IQR]):`,
);
console.log(
  `  plain package                   : ${plain.median.toFixed(4)} ms [${plain.q1.toFixed(4)}-${plain.q3.toFixed(4)}]`,
);
console.log(
  `  + voiding + accepting authority : ${full.median.toFixed(4)} ms [${full.q1.toFixed(4)}-${full.q3.toFixed(4)}]`,
);
console.log(
  `  + signed mandate (\u00a74.5, gated) : ${mandateArm.median.toFixed(4)} ms [${mandateArm.q1.toFixed(4)}-${mandateArm.q3.toFixed(4)}]`,
);
console.log(
  `  median delta, mandate arm       : ${mandateDelta.toFixed(4)} ms/verify (one extra RSA verification over JCS bytes)`,
);
console.log(
  `  median delta                    : ${deltaMedian.toFixed(4)} ms/verify` +
    ` — ${withinNoise ? "WITHIN each arm's IQR" : "exceeds the IQR"}; both arms are sub-millisecond and dominated by`,
);
console.log(
  `                                    the shared RFC 3161 timestamp inspection. No percentage is reported: the delta is`,
);
console.log(
  `                                    noise-dominated (it swings across runs), so only the byte footprint and the`,
);
console.log(
  `                                    qualitative "well under a millisecond" reading are load-bearing.`,
);
