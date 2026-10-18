// SPDX-License-Identifier: Apache-2.0
//
// --pqc-signer-key and the --require-pqc warning, mirrored from the Python
// CLI tests in lib-python/tests/test_pqc_signer_pin.py. Needs `npm run build`
// first (the CLI loads lib/dist).

import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
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

test("--require-pqc without --pqc-signer-key warns on stderr only", () => {
  const proc = run("--json", "--require-pqc", hybrid);
  assert.equal(proc.status, 0, proc.stderr);
  assert.ok(proc.stderr.includes("warning: --require-pqc without --pqc-signer-key"), proc.stderr);
  assert.equal(JSON.parse(proc.stdout).valid, true);
});

test("--pqc-signer-key without --require-pqc rejects a foreign ML-DSA key", () => {
  const proc = run("--json", "--pqc-signer-key", devKey, foreignPackage);
  assert.equal(proc.status, 1, proc.stderr);
  assert.equal(JSON.parse(proc.stdout).failureCode, "PQC_SIGNER_NOT_TRUSTED");
  assert.ok(!proc.stderr.includes("warning"), proc.stderr);
});

for (const kind of ["rsa", "two-blocks", "missing"]) {
  test(`an unusable --pqc-signer-key file exits 2 (${kind})`, () => {
    const dir = mkdtempSync(join(tmpdir(), "eatf-pqc-pin-"));
    try {
      const path = join(dir, `${kind}.pem`);
      if (kind === "rsa") writeFileSync(path, readFileSync(join(keys, "dev-rsa-4096.pem")));
      if (kind === "two-blocks") {
        const foreign = unzipSync(readFileSync(foreignPackage))["pqc_public_key.pem"];
        writeFileSync(path, Buffer.concat([readFileSync(devKey), Buffer.from(foreign)]));
      }
      const proc = run("--pqc-signer-key", path, hybrid);
      assert.equal(proc.status, 2, proc.stdout + proc.stderr);
      assert.equal(proc.stdout, "");
      const expected = kind === "missing"
        ? "cannot read --pqc-signer-key"
        : "is not an ML-DSA-65 public key";
      assert.ok(proc.stderr.includes(expected), proc.stderr);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
}
