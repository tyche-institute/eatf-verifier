#!/usr/bin/env node
/*
 * eatf-verify — offline command-line verifier for EATF .aep evidence packages.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Thin wrapper around the @eatf/verifier library (../lib). Reads one or
 * more .aep files, runs the full offline verification pipeline (envelope,
 * canonicalisation, hash chain, classical + post-quantum signatures,
 * issuer chain, RFC 3161 timestamp, optional attestation), and prints a
 * structured report.
 *
 * No network calls. No API keys. Trust anchors are passed in via CLI
 * flags; the verifier itself never reaches out.
 */

import { readFile } from "node:fs/promises";
import { resolve, basename } from "node:path";
import { existsSync, statSync, readdirSync } from "node:fs";
import process from "node:process";

const VERSION = "0.1.1";

function usage() {
  process.stdout.write(`\
eatf-verify ${VERSION} — offline verifier for EATF .aep evidence packages

Usage:
  eatf-verify <path.aep> [path.aep ...]      Verify one or more packages.
  eatf-verify --batch <directory>            Walk a directory tree, verify
                                             every .aep, print a summary.
  eatf-verify --conformance <vectors-root>   Run against a test-vectors/
                                             tree (valid/ + invalid/);
                                             expect verify=true under
                                             valid/ and verify=false under
                                             invalid/.

Options:
  --json                                     Emit one JSON object per .aep
                                             on stdout (machine-readable).
  --tsa-trust-list <pem-file>                Pin RFC 3161 TSA roots. Repeatable.
  --offline-only                             Default. Refuse to consult any
                                             external resource.
  --version, -V                              Print version and exit.
  --help, -h                                 Print this message.

Exit codes:
  0     All packages verified successfully (or --conformance contract met).
  1     At least one package failed verification.
  2     Bad CLI usage or unreadable file.

Examples:
  eatf-verify action.aep
  eatf-verify --batch ./received-packages/
  eatf-verify --conformance ./test-vectors/
  eatf-verify --json action.aep | jq .
`);
}

function parseArgs(argv) {
  const args = {
    paths: [], batch: null, conformance: null,
    json: false, tsaTrustList: [], offlineOnly: true,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") return { help: true };
    if (a === "--version" || a === "-V") return { version: true };
    if (a === "--json") { args.json = true; continue; }
    if (a === "--offline-only") { args.offlineOnly = true; continue; }
    if (a === "--batch") { args.batch = argv[++i]; continue; }
    if (a === "--conformance") { args.conformance = argv[++i]; continue; }
    if (a === "--tsa-trust-list") { args.tsaTrustList.push(argv[++i]); continue; }
    if (a.startsWith("--")) {
      process.stderr.write(`eatf-verify: unknown option ${a}\n`);
      return { error: 2 };
    }
    args.paths.push(a);
  }
  return args;
}

async function loadVerifier() {
  // bin/eatf-verify.js → cli/eatf-verify/bin/ → ../../../lib/
  const libRoot = new URL("../../../lib/", import.meta.url);
  try {
    return await import(new URL("dist/index.js", libRoot).href);
  } catch (e) {
    process.stderr.write(`\
eatf-verify: cannot load @eatf/verifier from ../lib/dist/.
Run \`npm install && npm run build\` in ../lib/ first, then retry.
Underlying error: ${e?.message ?? e}
`);
    process.exit(2);
  }
}

async function loadTsaTrustList(paths) {
  if (paths.length === 0) return [];
  const out = [];
  for (const p of paths) out.push(await readFile(resolve(p), "utf8"));
  return out;
}

function findAep(root) {
  const out = [];
  const stack = [root];
  while (stack.length) {
    const cur = stack.pop();
    const st = statSync(cur);
    if (st.isDirectory()) {
      for (const name of readdirSync(cur)) stack.push(`${cur}/${name}`);
    } else if (st.isFile() && cur.endsWith(".aep")) out.push(cur);
  }
  return out.sort();
}

function expectedFromTreePath(p, conformanceRoot) {
  const base = conformanceRoot.replace(/\/+$/, "");
  // findAep may produce paths with extra slashes when the root ends in /;
  // strip any leading slashes from the relative portion before matching.
  const rel = p.slice(base.length).replace(/^\/+/, "");
  if (rel.startsWith("valid/")) return "true";
  if (rel.startsWith("invalid/")) return "false";
  return null;
}

function formatHuman(path, result) {
  const lines = [`VECTOR ${path}`, `  verify=${result.valid}`];
  if (result.failureReason) lines.push(`  diagnostic=${result.failureReason}`);
  if (result.pqcValid !== null) lines.push(`  pqc=${result.pqcValid}`);
  if (result.tsaTrusted !== null && result.tsaTrusted !== undefined) {
    lines.push(`  tsaTrusted=${result.tsaTrusted}`);
  }
  return lines.join("\n");
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) { usage(); return 0; }
  if (args.version) { process.stdout.write(`eatf-verify ${VERSION}\n`); return 0; }
  if (args.error) { usage(); return args.error; }

  const { verify } = await loadVerifier();
  const tsaTrustList = await loadTsaTrustList(args.tsaTrustList);

  if (args.paths.length > 0 && !args.batch && !args.conformance) {
    let anyFail = false;
    for (const p of args.paths) {
      if (!existsSync(p)) {
        process.stderr.write(`eatf-verify: no such file: ${p}\n`);
        return 2;
      }
      const bytes = await readFile(resolve(p));
      const result = await verify(bytes, { offlineOnly: args.offlineOnly, tsaTrustList });
      if (args.json) process.stdout.write(JSON.stringify({ path: p, ...result }) + "\n");
      else process.stdout.write(formatHuman(p, result) + "\n");
      if (!result.valid) anyFail = true;
    }
    return anyFail ? 1 : 0;
  }

  if (args.batch) {
    if (!existsSync(args.batch)) {
      process.stderr.write(`eatf-verify: --batch directory missing: ${args.batch}\n`);
      return 2;
    }
    const aeps = findAep(args.batch);
    let pass = 0, fail = 0;
    for (const p of aeps) {
      const bytes = await readFile(resolve(p));
      const result = await verify(bytes, { offlineOnly: args.offlineOnly, tsaTrustList });
      if (args.json) process.stdout.write(JSON.stringify({ path: p, ...result }) + "\n");
      else process.stdout.write(formatHuman(p, result) + "\n");
      if (result.valid) pass++; else fail++;
    }
    if (!args.json) process.stdout.write(`\nSummary: ${pass} verified, ${fail} failed.\n`);
    return fail > 0 ? 1 : 0;
  }

  if (args.conformance) {
    if (!existsSync(args.conformance)) {
      process.stderr.write(`eatf-verify: --conformance directory missing: ${args.conformance}\n`);
      return 2;
    }
    const aeps = findAep(args.conformance);
    let pass = 0, fail = 0, mismatch = 0;
    for (const p of aeps) {
      const expected = expectedFromTreePath(p, args.conformance);
      if (expected === null) continue;
      const bytes = await readFile(resolve(p));
      const result = await verify(bytes, { offlineOnly: args.offlineOnly, tsaTrustList });
      const actual = result.valid ? "true" : "false";
      const ok = actual === expected;
      if (args.json) {
        process.stdout.write(JSON.stringify({
          path: p, expected, actual, contractMet: ok,
          failureReason: result.failureReason,
        }) + "\n");
      } else {
        const tag = ok ? "PASS" : "MISMATCH";
        process.stdout.write(`${tag}  ${basename(p)}  expected=${expected}  actual=${actual}${result.failureReason ? `  (${result.failureReason})` : ""}\n`);
      }
      if (!ok) mismatch++;
      if (result.valid) pass++; else fail++;
    }
    if (!args.json) {
      process.stdout.write(`\nConformance: ${pass} verified, ${fail} rejected, ${mismatch} contract mismatches.\n`);
    }
    return mismatch > 0 ? 1 : 0;
  }

  usage();
  return 2;
}

main().then((code) => process.exit(code)).catch((e) => {
  process.stderr.write(`eatf-verify: ${e?.stack ?? e}\n`);
  process.exit(2);
});
