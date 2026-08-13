#!/usr/bin/env node
/*
 * eatf-inspect — pretty-print the structure of an EATF .aep evidence package
 * without verifying signatures.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Useful for debugging packaging bugs and for inspecting received packages
 * before deciding whether to invoke eatf-verify. Does NOT check
 * authenticity — anything in the printed manifest/signatures could be
 * forged. To assert authenticity, run eatf-verify on the same file.
 */

import { readFile } from "node:fs/promises";
import { resolve, basename } from "node:path";
import { existsSync } from "node:fs";
import process from "node:process";
import { unzipSync, strFromU8 } from "fflate";

const VERSION = "0.1.2";

function usage() {
  process.stdout.write(`\
eatf-inspect ${VERSION} — pretty-print the structure of an .aep evidence package

Usage:
  eatf-inspect <path.aep>       Print manifest + entries + signatures summary.
  eatf-inspect --json <path>    Emit one JSON object describing the package.
  eatf-inspect --version, -V
  eatf-inspect --help, -h

eatf-inspect does NOT verify authenticity. Anything in the printed
output could have been forged after signing. Run eatf-verify to
assert authenticity.

Exit codes:
  0     Inspection completed.
  1     Package is not a well-formed ZIP / cannot be read.
  2     Bad CLI usage.
`);
}

function parseArgs(argv) {
  const args = { path: null, json: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") return { help: true };
    if (a === "--version" || a === "-V") return { version: true };
    if (a === "--json") { args.json = true; continue; }
    if (a.startsWith("--")) {
      process.stderr.write(`eatf-inspect: unknown option ${a}\n`);
      return { error: 2 };
    }
    args.path = a;
  }
  if (!args.path) return { error: 2 };
  return args;
}

function tryParseJson(bytes) {
  try {
    return JSON.parse(strFromU8(bytes));
  } catch {
    return null;
  }
}

function summarise(bytes) {
  const entries = unzipSync(bytes);
  const names = Object.keys(entries).sort();
  const sizes = Object.fromEntries(names.map((n) => [n, entries[n].byteLength]));

  // AEP v1 wire format is flat — see docs/aep-profile.md.
  const metadata = entries["metadata.json"] ? tryParseJson(entries["metadata.json"]) : null;
  const overtReceipt = entries["overt_receipt.json"] ? tryParseJson(entries["overt_receipt.json"]) : null;

  const knownEntries = [
    "canonical.bin",
    "hash.sha256",
    "metadata.json",
    "overt_receipt.json",
    "public_key.pem",
    "response.txt",
    "signature.sig",
    "signature.mldsa",   // post-quantum signature (when present)
    "timestamp.tsr",
  ];
  const presence = Object.fromEntries(
    knownEntries.map((k) => [k, k in entries ? sizes[k] : null])
  );
  const unknown = names.filter((n) => !knownEntries.includes(n));

  return {
    totalEntries: names.length,
    entries: names,
    presence,
    unknown,
    metadata,
    overtReceipt: overtReceipt ? {
      overt: overtReceipt.overt ?? null,
      profile: overtReceipt.profile ?? null,
      scope: overtReceipt.scope ?? null,
      subject: overtReceipt.subject ?? null,
      policy: overtReceipt.policy ?? null,
      contentHash: overtReceipt.content_hash ?? null,
      witness: overtReceipt.witness ?? null,
    } : null,
  };
}

function formatHuman(path, summary) {
  const lines = [];
  lines.push(`PACKAGE ${path}`);
  lines.push(`  total ZIP entries: ${summary.totalEntries}`);
  lines.push(`  envelope entries (AEP v1 format):`);
  for (const [name, size] of Object.entries(summary.presence)) {
    const marker = size === null ? "—" : `${size} B`;
    lines.push(`    ${name.padEnd(22)} ${marker}`);
  }
  if (summary.unknown.length > 0) {
    lines.push(`  unknown extra entries: ${summary.unknown.join(", ")}`);
  }
  if (summary.metadata) {
    lines.push(`  metadata.json:`);
    if (summary.metadata.schema) lines.push(`    schema: ${summary.metadata.schema}`);
    if (summary.metadata.attestation_id) lines.push(`    attestation_id: ${summary.metadata.attestation_id}`);
    if (summary.metadata.agent_id) lines.push(`    agent_id: ${summary.metadata.agent_id}`);
    if (summary.metadata.action_type) lines.push(`    action_type: ${summary.metadata.action_type}`);
    if (summary.metadata.policy_id) lines.push(`    policy: ${summary.metadata.policy_id} v${summary.metadata.policy_version ?? "?"} → ${summary.metadata.policy_decision ?? "?"}`);
    if (summary.metadata.created_at) lines.push(`    created_at: ${summary.metadata.created_at}`);
    if (summary.metadata.format_version) lines.push(`    format_version: ${summary.metadata.format_version}`);
  } else {
    lines.push(`  metadata.json: (absent or not JSON)`);
  }
  if (summary.overtReceipt) {
    lines.push(`  overt_receipt.json:`);
    if (summary.overtReceipt.overt) lines.push(`    overt: ${summary.overtReceipt.overt}`);
    if (summary.overtReceipt.profile) lines.push(`    profile: ${summary.overtReceipt.profile}`);
    if (summary.overtReceipt.scope) lines.push(`    scope: ${summary.overtReceipt.scope}`);
    if (summary.overtReceipt.policy) {
      lines.push(`    policy: ${summary.overtReceipt.policy.id ?? "?"} v${summary.overtReceipt.policy.version ?? "?"} → ${summary.overtReceipt.policy.decision ?? "?"}`);
    }
    if (summary.overtReceipt.contentHash) lines.push(`    content_hash: ${summary.overtReceipt.contentHash}`);
  }
  lines.push(``);
  lines.push(`Note: this is a structure dump only. Authenticity is NOT checked.`);
  lines.push(`Run eatf-verify to assert signature, hash chain, and timestamp.`);
  return lines.join("\n");
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) { usage(); return 0; }
  if (args.version) { process.stdout.write(`eatf-inspect ${VERSION}\n`); return 0; }
  if (args.error) { usage(); return args.error; }

  if (!existsSync(args.path)) {
    process.stderr.write(`eatf-inspect: no such file: ${args.path}\n`);
    return 1;
  }
  const bytes = new Uint8Array(await readFile(resolve(args.path)));
  let summary;
  try {
    summary = summarise(bytes);
  } catch (e) {
    process.stderr.write(`eatf-inspect: not a well-formed .aep / ZIP — ${e?.message ?? e}\n`);
    return 1;
  }
  if (args.json) {
    process.stdout.write(JSON.stringify({ path: args.path, ...summary }) + "\n");
  } else {
    process.stdout.write(formatHuman(args.path, summary) + "\n");
  }
  return 0;
}

main().then((code) => process.exit(code)).catch((e) => {
  process.stderr.write(`eatf-inspect: ${e?.stack ?? e}\n`);
  process.exit(1);
});
