#!/usr/bin/env node
/**
 * Decompose the F3 fail/advisory cell (verdict=fail, enforced=false) by the
 * package's overall verify() verdict, over the SAME corpus F3 uses
 * (valid + invalid + boundary). Read-only.
 *
 *   (cd lib && npm run build)
 *   node scripts/fail-advisory-by-valid.mjs
 */
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const { verify } = await import(new URL("../lib/dist/index.js", import.meta.url));

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

const vectors = [...collect("valid"), ...collect("invalid"), ...collect("boundary"), ...collect("mandate"), ...collect("acceptance")];
let faTrue = 0, faFalse = 0, pkgTrue = 0, pkgFalse = 0;
let pkgsWithFailAdvisoryAmongValidTrue = 0;
const perPkg = [];
for (const v of vectors) {
  const r = await verify(new Uint8Array(readFileSync(v.file)), optsFor(v));
  let fa = 0;
  for (const c of r.boundary.checks) {
    if (c.verdict === "fail" && c.enforced === false) fa++;
  }
  if (r.valid) { pkgTrue++; faTrue += fa; if (fa > 0) pkgsWithFailAdvisoryAmongValidTrue++; }
  else { pkgFalse++; faFalse += fa; }
  perPkg.push({ v: `${v.cat}/${v.name}`, valid: r.valid, failAdvisory: fa });
}

console.log(`=== fail/advisory (verdict=fail, enforced=false) by package verdict, ${vectors.length}-vector corpus ===`);
console.log("vector".padEnd(46), "valid".padEnd(6), "fail/advisory");
for (const p of perPkg) {
  console.log(p.v.padEnd(46), String(p.valid).padEnd(6), String(p.failAdvisory).padStart(4));
}
console.log("---");
console.log(`packages valid:true  = ${pkgTrue}; fail/advisory instances among them = ${faTrue}`);
console.log(`  of the ${pkgTrue} valid:true packages, ${pkgsWithFailAdvisoryAmongValidTrue} carry >=1 fail/advisory check`);
console.log(`packages valid:false = ${pkgFalse}; fail/advisory instances among them = ${faFalse}`);
console.log(`TOTAL fail/advisory = ${faTrue + faFalse}  (F3 cell cross-check)`);
