#!/usr/bin/env node
/**
 * Warrant census over the whole vector corpus.
 *
 * Two measurements, both read-only, printed and never written:
 *
 *   F7  decidability partition over the per-output obligations — the
 *       warrant sub-checks plus the step-1 boundary checks — split into
 *         machine-decidable-offline   (a shipped check reaches a
 *                                      determinate verdict from package
 *                                      bytes alone),
 *         decidable-with-supplied-input (a shipped check reaches its
 *                                      affirmative verdict only when the
 *                                      caller supplies a trust anchor via
 *                                      VerifyOptions), and
 *         attested-only               (the obligation has no executable
 *                                      check in this verifier).
 *       The denominator is the spec surface
 *       (docs/specs/assessment-surface-v1.json), NOT the verifier's own
 *       check list. The input-dependent set is derived from the shipped
 *       control flow (the checks whose determinate PASS consults a
 *       VerifyOptions trust field) and is corroborated empirically: the
 *       observed-verdict column shows what each check reaches across the
 *       corpus under default (no supplied trust) options.
 *
 *   F9  may-inform-cannot-compel rate — the fraction of corpus packages
 *       whose verification yields warrant.present=false or
 *       warrant.applicable=false: no warrant compels the action, either
 *       because none is carried (or the run failed before the warrant
 *       step) or because the carried warrant does not apply.
 *
 * Build the verifier first:
 *
 *   (cd lib && npm install && npm run build)
 *   node scripts/warrant-census.mjs
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const distIndex = path.join(root, "lib/dist/index.js");
if (!existsSync(distIndex)) {
  process.stderr.write("lib/dist not found — run `(cd lib && npm run build)` first.\n");
  process.exit(2);
}
const { verify } = await import(new URL("../lib/dist/index.js", import.meta.url));
const { CHECK_REGISTRY } = await import(new URL("../lib/dist/check-registry.js", import.meta.url));

const surface = JSON.parse(
  readFileSync(path.join(root, "docs/specs/assessment-surface-v1.json"), "utf8"),
);
const surfaceRows = surface.clauses.length;

// Derived from shipped control flow (lib/src/verifier.ts): the checks
// whose verdict requires a caller-supplied input through VerifyOptions —
// chain-to-root cannot reach a trusted root without a tsaTrustList,
// warrant freshness is only affirmed under a trusted TSA, and issuer
// pinning (§8.1) does not execute at all without a trustedSignerPems
// list. Every other executable check decides from package bytes alone.
// The empirical column below corroborates that none of the three
// reaches PASS on this corpus under default options.
const NEEDS_SUPPLIED_INPUT = new Set([
  "tsa-chain-to-root",
  "warrant-freshness",
  "signer-key-pinned",
]);

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
  ...collect("mandate"),
  ...collect("acceptance"),
];

// Run the whole corpus once under DEFAULT options (no supplied trust),
// recording the verdicts each registry check reaches and the warrant
// outcome per package.
const observed = new Map(CHECK_REGISTRY.map((c) => [c.id, new Set()]));
const rows = [];

for (const v of vectors) {
  const r = await verify(new Uint8Array(readFileSync(v.file)), {});
  for (const c of r.boundary.checks) observed.get(c.id).add(c.verdict);
  rows.push({
    v: `${v.cat}/${v.name}`,
    valid: r.valid,
    present: r.warrant?.present === true,
    // null: the run rejected the package before applicability was judged.
    applicable: r.warrant?.present === true ? r.warrant.applicable : undefined,
  });
}

// Memo F9: present=false OR applicable===false. A package with no
// operative warrant cannot compel; a carried-but-inapplicable warrant
// may inform but carries no warrant to compel. applicable===null is a
// distinct state (the warrant was rejected before appraisal) and is NOT
// counted as may-inform.
const mayInformRows = rows.filter((r) => !r.present || r.applicable === false);
const mayInform = mayInformRows.length;

// --- F7 -------------------------------------------------------------
const bucketOf = (check) => {
  if (check === "no-executable-check") return "attested-only";
  if (NEEDS_SUPPLIED_INPUT.has(check)) return "decidable-with-supplied-input";
  return "machine-decidable-offline";
};
const buckets = {
  "machine-decidable-offline": [],
  "decidable-with-supplied-input": [],
  "attested-only": [],
};
for (const row of surface.clauses) buckets[bucketOf(row.check)].push(row);

console.log("=== F7: decidability partition over the per-output obligations ===");
console.log(
  `spec surface = ${surfaceRows} obligation rows; input-dependent set (from shipped control flow) = ` +
    `${[...NEEDS_SUPPLIED_INPUT].join(", ")}`,
);
for (const [bucket, rows] of Object.entries(buckets)) {
  console.log(
    `\n${bucket}: ${rows.length}/${surfaceRows} (${((100 * rows.length) / surfaceRows).toFixed(0)}%)`,
  );
  for (const row of rows) console.log("   -", row.clause, "::", row.check);
}
const attestedRemainder = buckets["attested-only"].filter((r) =>
  /attested remainder/.test(r.clause),
).length;
console.log(
  `\nof the ${buckets["attested-only"].length} attested-only rows, ${attestedRemainder} are the ` +
    `irreducibly-attested remainder (soundness of the licensed inference, key-to-principal binding, ` +
    `attested void_if text); the rest are spec MUSTs this verifier does not yet mechanise.`,
);

console.log("\nempirical corroboration — verdicts each registry check reaches under default options:");
for (const c of CHECK_REGISTRY) {
  const verdicts = [...observed.get(c.id)].sort().join(",") || "(never recorded)";
  const determinate = observed.get(c.id).has("pass") || observed.get(c.id).has("fail");
  console.log(
    "  ",
    c.id.padEnd(28),
    bucketOf(c.id).padEnd(30),
    `reaches: ${verdicts}`.padEnd(34),
    determinate ? "determinate-offline" : "indeterminate-without-input",
  );
}

// --- F9 -------------------------------------------------------------
console.log("\n=== F9: may-inform-cannot-compel rate over the full vector corpus ===");
console.log(
  `${mayInform}/${vectors.length} packages (${((100 * mayInform) / vectors.length).toFixed(1)}%) ` +
    `yield warrant.present=false or applicable=false — no carried warrant compels the action.`,
);
const noWarrant = mayInformRows.filter((r) => !r.present).length;
const inapplicable = mayInformRows.filter((r) => r.present && r.applicable === false).length;
const rejectedBeforeAppraisal = rows.filter((r) => r.present && r.applicable == null).length;
const compels = rows.filter((r) => r.present && r.applicable === true).length;
console.log(
  `  of these: ${noWarrant} carry no operative warrant (or fail before the warrant step); ` +
    `${inapplicable} carry a warrant that does not apply (the sharp may-inform-cannot-compel case).`,
);
console.log(
  `  outside the rate: ${compels} carry an applicable warrant; ` +
    `${rejectedBeforeAppraisal} carry a warrant rejected before appraisal (applicable=null).`,
);
console.log("  the carried-but-inapplicable packages (present=true, applicable=false):");
for (const r of mayInformRows.filter((r) => r.present && r.applicable === false)) {
  console.log("   -", r.v);
}
