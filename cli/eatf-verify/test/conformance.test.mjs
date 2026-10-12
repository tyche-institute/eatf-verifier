// SPDX-License-Identifier: Apache-2.0
//
// --conformance must count every shared vector and must not report an
// empty run as a pass. Needs `npm run build` first (the CLI loads lib/dist).

import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, sep } from "node:path";

const repoRoot = resolve(import.meta.dirname, "../../..");
const cli = join(repoRoot, "cli", "eatf-verify", "bin", "eatf-verify.js");
const vectors = join(repoRoot, "test-vectors");

const countAep = (dir) => readdirSync(dir, { recursive: true })
  .filter((name) => name.endsWith(".aep")).length;
const validCount = countAep(join(vectors, "valid"));
const invalidCount = countAep(join(vectors, "invalid"));

const run = (...args) => spawnSync(process.execPath, [cli, ...args], {
  cwd: repoRoot, encoding: "utf8",
});

test("the shared corpus has accepted and rejected vectors", () => {
  assert.ok(validCount > 0);
  assert.ok(invalidCount > 0);
});

for (const [label, root] of [
  ["relative", "test-vectors"],
  ["relative with trailing slash", "test-vectors/"],
  ["absolute", vectors],
  ["absolute with trailing separator", vectors + sep],
]) {
  test(`--conformance counts every vector (${label})`, () => {
    const proc = run("--conformance", root);
    assert.equal(proc.status, 0, proc.stdout + proc.stderr);
    assert.ok(proc.stdout.includes(
      `Conformance: ${validCount} verified, ${invalidCount} rejected, 0 contract mismatches.`,
    ), proc.stdout);
  });
}

test("--conformance on a tree with no vectors exits 2", () => {
  const dir = mkdtempSync(join(tmpdir(), "eatf-conformance-"));
  try {
    mkdirSync(join(dir, "keys"));
    writeFileSync(join(dir, "keys", "stray.aep"), "not under valid/ or invalid/");
    const proc = run("--conformance", dir);
    assert.equal(proc.status, 2, proc.stdout + proc.stderr);
    assert.ok(!proc.stdout.includes("Conformance:"), proc.stdout);
    assert.match(proc.stderr, /no \.aep vectors under valid\/ or invalid\//);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("--conformance on a category directory exits 2", () => {
  const proc = run("--conformance", join("test-vectors", "valid"));
  assert.equal(proc.status, 2, proc.stdout + proc.stderr);
  assert.match(proc.stderr, /no \.aep vectors under valid\/ or invalid\//);
});

test("--conformance on a missing directory exits 2", () => {
  const proc = run("--conformance", "no-such-dir");
  assert.equal(proc.status, 2, proc.stdout + proc.stderr);
  assert.match(proc.stderr, /--conformance directory missing/);
});
