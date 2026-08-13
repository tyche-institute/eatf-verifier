#!/usr/bin/env node
/**
 * Boundary census over the whole vector corpus.
 *
 * Reports four measurements from the verifier's BoundaryReport across
 * every package under test-vectors/{valid,invalid,boundary}/:
 *
 *   F2  boundary-vacuity census — per vector, the pass/fail/
 *       not_assessed/not_determinate counts and the share of the spec's
 *       normative surface actually assessed (denominator from
 *       docs/specs/assessment-surface-v1.json, NEVER the registry).
 *   F3  4x2 lattice occupancy — which (verdict x enforced) cells real
 *       vectors populate.
 *   F4  short-circuit shadow ranking — per failure class, how many
 *       checks the early return left not_assessed/short_circuited.
 *   F5  registry-vs-spec two-set diff — registry checks with no spec
 *       clause, mapped checks absent from the registry, and the spec's
 *       normative clauses with no executable check.
 *
 * Read-only; prints a report, writes nothing. Build the verifier first:
 *
 *   (cd lib && npm install && npm run build)
 *   node scripts/boundary-census.mjs
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
const execRows = surface.clauses.filter((c) => c.check !== "no-executable-check").length;
const noExec = surface.clauses.filter((c) => c.check === "no-executable-check");

function collect(cat) {
  const base = path.join(root, "test-vectors", cat);
  if (!existsSync(base)) return [];
  return readdirSync(base, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => ({ cat, name: d.name, file: path.join(base, d.name, "package.aep") }))
    .filter((v) => existsSync(v.file))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function optsFor(v) {
  const eb = path.join(root, "test-vectors", v.cat, v.name, "expected-boundary.json");
  if (existsSync(eb)) {
    const j = JSON.parse(readFileSync(eb, "utf8"));
    if (j.options) return j.options;
  }
  return {};
}

const vectors = [
  ...collect("valid"),
  ...collect("invalid"),
  ...collect("boundary"),
  ...collect("mandate"),
  ...collect("acceptance"),
];
const lattice = {};
const shadow = {};
const rows = [];

for (const v of vectors) {
  const r = await verify(new Uint8Array(readFileSync(v.file)), optsFor(v));
  const counts = { pass: 0, fail: 0, not_assessed: 0, not_determinate: 0 };
  const assessedIds = new Set();
  for (const c of r.boundary.checks) {
    counts[c.verdict]++;
    const key = `${c.verdict}|${c.enforced}`;
    (lattice[key] ??= { n: 0, sample: `${v.name}:${c.id}` }).n++;
    if (c.verdict === "pass" || c.verdict === "fail") assessedIds.add(c.id);
  }
  const clausesAssessed = surface.clauses.filter(
    (cl) => cl.check !== "no-executable-check" && assessedIds.has(cl.check),
  ).length;
  rows.push({
    v: `${v.cat}/${v.name}`, valid: r.valid, form: r.boundary.canonicalForm, ...counts,
    clausesAssessed, shareFull: clausesAssessed / surfaceRows, shareExec: clausesAssessed / execRows,
  });
  if (!r.valid) {
    shadow[r.failureReason] = {
      notReached: r.boundary.checks.filter((c) => c.reason === "short_circuited").length,
    };
  }
}

console.log("=== F2: boundary-vacuity census (all valid+invalid+boundary vectors) ===");
console.log(
  `spec surface: ${surfaceRows} normative clause rows, ${execRows} with an executable check, ` +
    `${surfaceRows - execRows} no-executable-check; registry: ${CHECK_REGISTRY.length} checks`,
);
// Percentages are reported WITH their integer numerator: a share with no numerator
// cannot be recomputed by a reader, and both shares here share one numerator
// (clausesAssessed) over two different denominators (surfaceRows, execRows).
console.log(
  "vector".padEnd(48),
  `valid  form           P  F NA ND  cls  surf(n/${surfaceRows})  exec(n/${execRows})`,
);
for (const r of rows) {
  console.log(
    r.v.padEnd(48), String(r.valid).padEnd(6), String(r.form).padEnd(14),
    String(r.pass).padStart(2), String(r.fail).padStart(2),
    String(r.not_assessed).padStart(2), String(r.not_determinate).padStart(2),
    String(r.clausesAssessed).padStart(4),
    `  ${r.clausesAssessed}/${surfaceRows} (${(100 * r.shareFull).toFixed(0)}%)`.padEnd(16),
    `${r.clausesAssessed}/${execRows} (${(100 * r.shareExec).toFixed(0)}%)`,
  );
}

const validRows = rows.filter((r) => r.v.startsWith("valid/"));
const lo = Math.min(...validRows.map((r) => r.clausesAssessed));
const hi = Math.max(...validRows.map((r) => r.clausesAssessed));
const floorVec = validRows.find((r) => r.clausesAssessed === lo).v;
const topVecs = validRows.filter((r) => r.clausesAssessed === hi).map((r) => r.v).join(", ");
console.log(
  `F2 numerators: over the ${validRows.length} valid/ vectors the assessed count runs ` +
    `${lo} to ${hi} of ${surfaceRows} clause rows ` +
    `(${(100 * lo / surfaceRows).toFixed(0)}%-${(100 * hi / surfaceRows).toFixed(0)}%), ` +
    `equivalently ${lo} to ${hi} of ${execRows} executable checks ` +
    `(${(100 * lo / execRows).toFixed(0)}%-${(100 * hi / execRows).toFixed(0)}%); ` +
    `floor ${floorVec}, ceiling ${topVecs}`,
);

console.log("\n=== F3: 4x2 lattice occupancy (verdict x enforced) ===");
for (const verdict of ["pass", "fail", "not_assessed", "not_determinate"]) {
  for (const enf of [true, false]) {
    const cell = lattice[`${verdict}|${enf}`];
    console.log(
      `${verdict.padEnd(16)} enforced=${String(enf).padEnd(6)} ` +
        (cell ? `OCCUPIED n=${String(cell.n).padStart(4)}  e.g. ${cell.sample}` : "empty"),
    );
  }
}

console.log("\n=== F4: short-circuit shadow ranking (checks never reached per failure class) ===");
for (const [reason, info] of Object.entries(shadow).sort((a, b) => b[1].notReached - a[1].notReached)) {
  console.log(String(info.notReached).padStart(2), "not_assessed/short_circuited  <=  " + reason);
}

console.log("\n=== F5: registry-vs-spec two-set diff ===");
const mapped = new Set(surface.clauses.map((c) => c.check).filter((c) => c !== "no-executable-check"));
const regIds = new Set(CHECK_REGISTRY.map((c) => c.id));
console.log("registry checks with NO spec clause:", [...regIds].filter((id) => !mapped.has(id)));
console.log("mapped checks NOT in registry:", [...mapped].filter((id) => !regIds.has(id)));
console.log(`spec normative clauses with no-executable-check (${noExec.length} of ${surfaceRows}):`);
for (const c of noExec) console.log("  -", c.clause, "::", c.statement.slice(0, 88));
