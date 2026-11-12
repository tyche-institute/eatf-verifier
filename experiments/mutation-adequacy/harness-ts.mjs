#!/usr/bin/env node
// TypeScript harness for the mutation-adequacy experiment.
//
// StrykerJS runs it once per mutant through its command runner, with the active
// mutant named in __STRYKER_ACTIVE_MUTANT__ and the sandbox as working
// directory, so the build under test is <cwd>/lib/dist. The experiment runner
// calls it for the unmutated build and for the guard deletions, with
// EATF_TS_DIST and EATF_MUTANT_LABEL set.
//
// It verifies every case and records (valid, failure code) or the exception
// type. It writes the record to $EATF_MUTATION_OUT/<label>.json, then exits 1
// if the verdict-and-code oracle O_C fails on any case. So Stryker's killed
// status and the O_C kill computed later from the record must agree. The
// harness never reads the failure reason or the report.

import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const manifest = process.env.EATF_MUTATION_CASES;
if (!manifest) {
  process.stderr.write("EATF_MUTATION_CASES is not set\n");
  process.exit(2);
}
const dist = process.env.EATF_TS_DIST ?? resolve(process.cwd(), "lib/dist");
const label = process.env.EATF_MUTANT_LABEL ?? process.env.__STRYKER_ACTIVE_MUTANT__ ?? null;
const outDir = process.env.EATF_MUTATION_OUT ?? null;

async function record(payload) {
  if (!outDir || label === null) return;
  await mkdir(outDir, { recursive: true });
  const path = join(outDir, `${label}.json`);
  const tmp = `${path}.${process.pid}.tmp`;
  await writeFile(tmp, JSON.stringify({ label, port: "typescript", dist, ...payload }) + "\n");
  await rename(tmp, path);
}

const { cases } = JSON.parse(await readFile(manifest, "utf8"));
for (const item of cases) {
  item.bytes = new Uint8Array(await readFile(item.package));
  item.pin = item.signer_pin_pem ? await readFile(item.signer_pin_pem, "utf8") : null;
}

let verify;
try {
  ({ verify } = await import(pathToFileURL(join(dist, "index.js")).href));
} catch (error) {
  // A build that cannot load is killed under every oracle; no case is credited.
  await record({ load_error: error?.constructor?.name ?? typeof error, outcomes: [] });
  process.exit(1);
}

function observe(value) {
  // Anything other than a result object with a boolean verdict and a string or
  // absent code is recorded as malformed; it kills under every oracle.
  if (value === null || typeof value !== "object") return { malformed: typeof value };
  if (typeof value.valid !== "boolean") return { malformed: `valid:${typeof value.valid}` };
  const code = value.failureCode;
  if (code !== undefined && code !== null && typeof code !== "string") {
    return { malformed: `failureCode:${typeof code}` };
  }
  return { valid: value.valid, code: code ?? null };
}

const start = performance.now();
const outcomes = [];
for (const item of cases) {
  const options = item.pin ? { trustedSignerPems: [item.pin] } : {};
  try {
    const seen = observe(await verify(item.bytes, options));
    if ("malformed" in seen) {
      outcomes.push({ id: item.id, valid: null, code: null, exception: `MalformedResult(${seen.malformed})` });
    } else {
      outcomes.push({ id: item.id, valid: seen.valid, code: seen.code, exception: null });
    }
  } catch (error) {
    outcomes.push({ id: item.id, valid: null, code: null, exception: error?.constructor?.name ?? typeof error });
  }
}
const seconds = Math.round(performance.now() - start) / 1000;
await record({ seconds, outcomes });

const failures = [];
cases.forEach((item, index) => {
  const seen = outcomes[index];
  if (seen.exception !== null) {
    failures.push(`${item.id}: raised ${seen.exception}`);
  } else if (seen.valid !== item.expected_valid || seen.code !== item.expected_code) {
    failures.push(`${item.id}: observed (${seen.valid}, ${seen.code}), expected (${item.expected_valid}, ${item.expected_code})`);
  }
});
for (const line of failures) process.stdout.write(`${line}\n`);
process.exit(failures.length ? 1 : 0);
