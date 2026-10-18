// SPDX-License-Identifier: Apache-2.0
//
// --pqc-signer-key, unreadable trust files and the --require-pqc warning,
// mirrored from the Python CLI tests in lib-python/tests/test_pqc_signer_pin.py.
// Needs `npm run build` first (the CLI loads lib/dist).

import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { unzipSync } from "fflate";

const repoRoot = resolve(import.meta.dirname, "../../..");
const cli = join(repoRoot, "cli", "eatf-verify", "bin", "eatf-verify.js");
const keys = join(repoRoot, "test-vectors", "keys");
const hybrid = join(repoRoot, "test-vectors", "valid", "hybrid-mldsa65", "package.aep");
const foreignPackage = join(repoRoot, "workshops", "pqc-hybrid-lab", "packages", "07-foreign-mldsa-key.aep");
const devKey = join(keys, "dev-mldsa65.pem");

const run = (...args) => spawnSync(process.execPath, [cli, ...args], {
  cwd: repoRoot, encoding: "utf8",
});
const lines = (text) => text.split("\n").filter((line) => line !== "");

function withTempDir(fn) {
  const dir = mkdtempSync(join(tmpdir(), "eatf-pqc-pin-"));
  try {
    return fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test("--require-pqc without --pqc-signer-key warns on stderr only", () => {
  const proc = run("--json", "--require-pqc", hybrid);
  assert.equal(proc.status, 0, proc.stderr);
  assert.ok(proc.stderr.includes("warning: --require-pqc without --pqc-signer-key"), proc.stderr);
  assert.equal(JSON.parse(proc.stdout).valid, true);
});

test("--require-pqc with --pqc-signer-key does not warn", () => {
  const proc = run("--require-pqc", "--pqc-signer-key", devKey, hybrid);
  assert.equal(proc.status, 0, proc.stderr);
  assert.ok(!proc.stderr.includes("warning"), proc.stderr);
});

test("--pqc-signer-key without --require-pqc rejects a foreign ML-DSA key", () => {
  const proc = run("--json", "--pqc-signer-key", devKey, foreignPackage);
  assert.equal(proc.status, 1, proc.stderr);
  assert.equal(JSON.parse(proc.stdout).failureCode, "PQC_SIGNER_NOT_TRUSTED");
  assert.ok(!proc.stderr.includes("warning"), proc.stderr);
});

for (const flag of ["--batch", "--conformance", "--signer-key", "--pqc-signer-key", "--tsa-trust-list"]) {
  test(`${flag} as the last argument is a usage error`, () => {
    const proc = run("--json", hybrid, flag);
    assert.equal(proc.status, 2, proc.stdout + proc.stderr);
    assert.equal(proc.stdout, "");
    assert.equal(lines(proc.stderr).length, 1, proc.stderr);
    assert.ok(proc.stderr.includes(`option ${flag} requires a value`), proc.stderr);
  });
}

for (const kind of ["rsa", "two-blocks"]) {
  test(`a --pqc-signer-key file that is not one ML-DSA-65 key exits 2 (${kind})`, () => withTempDir((dir) => {
    const path = join(dir, `${kind}.pem`);
    if (kind === "rsa") writeFileSync(path, readFileSync(join(keys, "dev-rsa-4096.pem")));
    else {
      const foreign = unzipSync(readFileSync(foreignPackage))["pqc_public_key.pem"];
      writeFileSync(path, Buffer.concat([readFileSync(devKey), Buffer.from(foreign)]));
    }
    const proc = run("--pqc-signer-key", path, hybrid);
    assert.equal(proc.status, 2, proc.stdout + proc.stderr);
    assert.equal(proc.stdout, "");
    assert.equal(lines(proc.stderr).length, 1, proc.stderr);
    assert.ok(proc.stderr.startsWith("eatf-verify: --pqc-signer-key "), proc.stderr);
    assert.ok(proc.stderr.includes("is not an ML-DSA-65 public key"), proc.stderr);
  }));
}

const unreadable = ["missing", "directory"];
if (process.platform !== "win32" && process.getuid?.() !== 0) unreadable.push("no-permission");

for (const flag of ["--pqc-signer-key", "--signer-key", "--tsa-trust-list"]) {
  for (const kind of unreadable) {
    test(`an unreadable ${flag} file exits 2 (${kind})`, () => withTempDir((dir) => {
      const path = join(dir, `${kind}.pem`);
      if (kind === "directory") mkdirSync(path);
      if (kind === "no-permission") {
        writeFileSync(path, readFileSync(devKey));
        chmodSync(path, 0);
      }
      const proc = run(flag, path, hybrid);
      assert.equal(proc.status, 2, proc.stdout + proc.stderr);
      assert.equal(proc.stdout, "");
      assert.equal(lines(proc.stderr).length, 1, proc.stderr);
      assert.ok(proc.stderr.startsWith(`eatf-verify: cannot read ${flag} `), proc.stderr);
    }));
  }
}
