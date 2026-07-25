#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { verify } from "../../lib/dist/index.js";

const experimentRoot = resolve(import.meta.dirname);
const repoRoot = resolve(experimentRoot, "../..");
const oracle = JSON.parse(
  await readFile(resolve(experimentRoot, "oracle.json"), "utf8"),
);
const matchingKey = await readFile(
  resolve(repoRoot, "test-vectors/keys/dev-rsa-4096.pem"),
  "utf8",
);
const mismatchingKey = await readFile(
  resolve(repoRoot, "test-vectors/keys/dev-tsa-rsa-3072.pem"),
  "utf8",
);

for (const item of oracle.cases) {
  const packagePath = resolve(
    experimentRoot,
    "generated/corpus",
    item.id,
    "package.aep",
  );
  const options = {};
  if (item.signer_pin === "matching") options.trustedSignerPems = [matchingKey];
  if (item.signer_pin === "mismatching") options.trustedSignerPems = [mismatchingKey];
  const result = await verify(new Uint8Array(await readFile(packagePath)), options);
  process.stdout.write(JSON.stringify({
    id: item.id,
    valid: result.valid,
    failure_code: result.failureCode,
    failure_reason: result.failureReason,
  }) + "\n");
}
