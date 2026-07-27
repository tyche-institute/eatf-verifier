#!/usr/bin/env node
// Verify each package given on the command line and print one JSON line each.
import { readFile } from "node:fs/promises";
import { verify } from "../../lib/dist/index.js";

for (const path of process.argv.slice(2)) {
  const result = await verify(new Uint8Array(await readFile(path)));
  process.stdout.write(
    JSON.stringify({
      path,
      valid: result.valid,
      failureCode: result.failureCode ?? null,
      failureReason: result.failureReason ?? null,
    }) + "\n",
  );
}
