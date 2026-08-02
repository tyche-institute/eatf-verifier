#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { zipSync } from "fflate";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PACKAGE = JSON.parse(await readFile(resolve(ROOT, "package.json"), "utf8"));
const FIXED_ZIP_TIME = new Date(1980, 0, 1, 0, 0, 0);
const OUTPUT_NAME = `eatf-pqc-hybrid-lab-v${PACKAGE.version}.zip`;
const OUTPUT = resolve(ROOT, "dist", OUTPUT_NAME);

const files = [
  ["README.md", "workshops/pqc-hybrid-lab/README.md"],
  ["QUICKSTART.md", "workshops/pqc-hybrid-lab/QUICKSTART.md"],
  ["RUN-SHEETS.md", "workshops/pqc-hybrid-lab/RUN-SHEETS.md"],
  ["EXPECTED-TRANSCRIPT.md", "workshops/pqc-hybrid-lab/EXPECTED-TRANSCRIPT.md"],
  ["SHA256SUMS", "workshops/pqc-hybrid-lab/SHA256SUMS"],
  ["packages/manifest.json", "workshops/pqc-hybrid-lab/packages/manifest.json"],
  ["packages/01-valid-hybrid.aep", "workshops/pqc-hybrid-lab/packages/01-valid-hybrid.aep"],
  ["packages/02-pqc-signature-tampered.aep", "workshops/pqc-hybrid-lab/packages/02-pqc-signature-tampered.aep"],
  ["packages/03-pqc-pair-stripped.aep", "workshops/pqc-hybrid-lab/packages/03-pqc-pair-stripped.aep"],
  ["packages/04-classical-transition.aep", "workshops/pqc-hybrid-lab/packages/04-classical-transition.aep"],
  ["packages/05-pqc-signature-missing.aep", "workshops/pqc-hybrid-lab/packages/05-pqc-signature-missing.aep"],
  ["packages/06-response-tampered.aep", "workshops/pqc-hybrid-lab/packages/06-response-tampered.aep"],
  ["archive-migration/pqc-archive-migration-worksheet.md", "docs/pqc-archive-migration-worksheet.md"],
  ["archive-migration/pqc-archive-migration-worksheet.html", "docs/pqc-archive-migration-worksheet.html"],
  ["archive-migration/pqc-archive-migration-worksheet.pdf", "docs/pqc-archive-migration-worksheet.pdf"],
];

const entries = {};
for (const [archiveName, sourceName] of files) {
  entries[archiveName] = [
    await readFile(resolve(ROOT, sourceName)),
    { mtime: FIXED_ZIP_TIME },
  ];
}

await mkdir(dirname(OUTPUT), { recursive: true });
const bytes = zipSync(entries, { level: 9 });
await writeFile(OUTPUT, bytes);
const digest = createHash("sha256").update(bytes).digest("hex");
await writeFile(`${OUTPUT}.sha256`, `${digest}  ${OUTPUT_NAME}\n`);
process.stdout.write(`${OUTPUT_NAME}  ${digest}\n`);
