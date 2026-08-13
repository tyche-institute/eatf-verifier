#!/usr/bin/env node
/*
 * eatf-sign — offline command-line signer for EATF .aep evidence packages.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Thin wrapper around the @eatf/verifier `sign` export. No network I/O:
 * the RFC 3161 timestamp token must be supplied as a file (the AEP v0.1
 * format requires one). Producers who want a fresh timestamp can fetch
 * one out-of-band with curl + openssl ts -reply.
 */

import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { existsSync } from "node:fs";
import { generateKeyPairSync } from "node:crypto";
import process from "node:process";

const VERSION = "0.1.3";

function usage() {
  process.stdout.write(`\
eatf-sign ${VERSION} — sign a payload into an EATF .aep evidence package

Usage:
  eatf-sign --payload <file> --key <pem> --public-key <pem> \\
            --metadata <json> --scope <urn> --timestamp <tsr> \\
            [--out <file>]

Required options:
  --payload <file>        File to attest (typically the AI response).
  --key <pem>             RSA private key in PEM (PKCS#8 or PKCS#1).
  --public-key <pem>      RSA public key in PEM (will be embedded).
  --metadata <json>       JSON file with attestation metadata (schema,
                          attestation_id, agent_id, action_type, etc.).
  --scope <urn>           OVERT scope (e.g. foundational:aep-response).
  --timestamp <tsr>       RFC 3161 TimeStampResp bytes. The signer does
                          NOT call a TSA; fetch one with
                          \`openssl ts -query ... | curl -d @-\` and pass
                          the response here.

Optional:
  --out <file>            Output path. Default: ./package.aep.
  --iap <name>            Issuing AEP party name. Default: "EATF.eu".
  --canonical-form <f>    "response-only" (default; canonical.bin equals
                          the payload, matching the Java reference) or
                          "profile" (canonical.bin = response.txt + LF +
                          JCS(metadata.json), so the metadata is signed).
  --warrant <json>        Warrant record to package as warrant.json
                          (aep-profile-v1.md section 4.2), complete with
                          its acceptance block. The signer writes the
                          JCS-canonical bytes and fills the metadata
                          warrant_id/warrant_version/warrant_digest
                          reference. Combine with --canonical-form
                          profile to place the reference under the
                          signature.
  --voiding <json>        JSON file with the typed per-output voiding
                          predicate array (aep-profile-v1.md section 4.4).
                          Written into metadata.voiding.
  --accepting-authority <json>
                          JSON file with the epistemic accepting-authority
                          block {principal, policy_id, policy_version,
                          validity} (aep-profile-v1.md section 4.3). Written
                          into metadata.accepting_authority.
  --acceptance-json <json>
                          JSON file with the detached acceptance record. The
                          signer packages its JCS-canonical bytes as
                          acceptance.json and fills the accepting-authority
                          acceptance_digest. Requires --acceptance-sig.
  --acceptance-sig <file> File with the Base64 acceptance signature (made by
                          the accepting authority over JCS(acceptance.json)).
                          Written to acceptance.sig. Requires
                          --acceptance-json.
  --version, -V
  --help, -h

Key generation (utility):
  eatf-sign --gen-rsa <stem>     Generate <stem>.key (private, PEM)
                                  and <stem>.pem (public, PEM).
                                  Marked clearly as a DEV key — not
                                  suitable for production attestations.

Exit codes:
  0    Package written successfully.
  1    Sign error (bad key, bad payload, bad timestamp).
  2    Bad CLI usage / missing file.

Example (round-trip with the bundled dev key + an existing fixture's TSR):

  # 1. Generate a dev keypair (one-off).
  eatf-sign --gen-rsa /tmp/dev-key

  # 2. Sign.
  echo "Hello, world." > /tmp/payload.txt
  echo '{"schema":"urn:eatf:spec:aep:metadata:1.0","created_at":"2026-05-15T00:00:00Z","attestation_id":"att_demo_01"}' > /tmp/meta.json
  eatf-sign \\
    --payload /tmp/payload.txt \\
    --key /tmp/dev-key.key \\
    --public-key /tmp/dev-key.pem \\
    --metadata /tmp/meta.json \\
    --scope foundational:aep-response \\
    --timestamp test-vectors/valid/valid-overt-profile/package.aep:timestamp.tsr \\
    --out /tmp/hello.aep

  # 3. Verify.
  node cli/eatf-verify/bin/eatf-verify.js /tmp/hello.aep
`);
}

function parseArgs(argv) {
  const args = {
    payload: null, key: null, publicKey: null, metadata: null,
    scope: null, timestamp: null, out: "package.aep", iap: null,
    canonicalForm: null, warrant: null, genRsa: null,
    voiding: null, acceptingAuthority: null, acceptanceJson: null, acceptanceSig: null,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") return { help: true };
    if (a === "--version" || a === "-V") return { version: true };
    if (a === "--payload") { args.payload = argv[++i]; continue; }
    if (a === "--key") { args.key = argv[++i]; continue; }
    if (a === "--public-key") { args.publicKey = argv[++i]; continue; }
    if (a === "--metadata") { args.metadata = argv[++i]; continue; }
    if (a === "--scope") { args.scope = argv[++i]; continue; }
    if (a === "--timestamp") { args.timestamp = argv[++i]; continue; }
    if (a === "--out") { args.out = argv[++i]; continue; }
    if (a === "--iap") { args.iap = argv[++i]; continue; }
    if (a === "--canonical-form") {
      const v = argv[++i];
      if (v !== "profile" && v !== "response-only") {
        process.stderr.write(`eatf-sign: --canonical-form must be "profile" or "response-only", got ${v}\n`);
        return { error: 2 };
      }
      args.canonicalForm = v;
      continue;
    }
    if (a === "--warrant") { args.warrant = argv[++i]; continue; }
    if (a === "--voiding") { args.voiding = argv[++i]; continue; }
    if (a === "--accepting-authority") { args.acceptingAuthority = argv[++i]; continue; }
    if (a === "--acceptance-json") { args.acceptanceJson = argv[++i]; continue; }
    if (a === "--acceptance-sig") { args.acceptanceSig = argv[++i]; continue; }
    if (a === "--gen-rsa") { args.genRsa = argv[++i]; continue; }
    if (a.startsWith("--")) {
      process.stderr.write(`eatf-sign: unknown option ${a}\n`);
      return { error: 2 };
    }
    process.stderr.write(`eatf-sign: unexpected positional argument: ${a}\n`);
    return { error: 2 };
  }
  return args;
}

async function loadSigner() {
  const libRoot = new URL("../../../lib/", import.meta.url);
  try {
    return await import(new URL("dist/index.js", libRoot).href);
  } catch (e) {
    process.stderr.write(`\
eatf-sign: cannot load @eatf/verifier (which exports sign()) from ../lib/dist/.
Run \`npm install && npm run build\` in ../../lib/ first, then retry.
Underlying error: ${e?.message ?? e}
`);
    process.exit(1);
  }
}

function generateRsaKeypair(stemPath) {
  const { publicKey, privateKey } = generateKeyPairSync("rsa", {
    modulusLength: 4096,
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });
  return { publicKeyPem: publicKey, privateKeyPem: privateKey };
}

/**
 * Resolve --timestamp argument. Accepts:
 *   /path/to/file.tsr               raw TSR bytes file
 *   /path/to/some.aep:timestamp.tsr extract timestamp.tsr from inside an .aep
 */
async function loadTimestamp(spec) {
  if (spec.includes(":") && spec.endsWith(":timestamp.tsr")) {
    const aepPath = spec.slice(0, -":timestamp.tsr".length);
    const fflate = await import("fflate");
    const aepBytes = new Uint8Array(await readFile(resolve(aepPath)));
    const entries = fflate.unzipSync(aepBytes);
    if (!entries["timestamp.tsr"]) {
      throw new Error(`${aepPath} does not contain a timestamp.tsr entry`);
    }
    return entries["timestamp.tsr"];
  }
  return new Uint8Array(await readFile(resolve(spec)));
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) { usage(); return 0; }
  if (args.version) { process.stdout.write(`eatf-sign ${VERSION}\n`); return 0; }
  if (args.error) { usage(); return args.error; }

  // --gen-rsa subcommand.
  if (args.genRsa) {
    const stem = args.genRsa;
    const { publicKeyPem, privateKeyPem } = generateRsaKeypair(stem);
    // PEM standard does not permit comment lines — banners would break
    // parsers. The "DEV key" warning lives in the README and the
    // file name convention only.
    await writeFile(`${stem}.key`, privateKeyPem);
    await writeFile(`${stem}.pem`, publicKeyPem);
    process.stdout.write(`Wrote ${stem}.key (private) and ${stem}.pem (public)\n`);
    process.stdout.write(`NOTE: these are DEV keys. Do NOT use for production attestations.\n`);
    return 0;
  }

  // Validate required args.
  const required = ["payload", "key", "publicKey", "metadata", "scope", "timestamp"];
  for (const k of required) {
    if (!args[k]) {
      process.stderr.write(`eatf-sign: missing required option --${k.replace(/([A-Z])/g, "-$1").toLowerCase()}\n`);
      usage();
      return 2;
    }
  }
  for (const k of ["payload", "key", "publicKey", "metadata"]) {
    if (!existsSync(args[k])) {
      process.stderr.write(`eatf-sign: file not found: ${args[k]}\n`);
      return 2;
    }
  }

  const payloadBytes = new Uint8Array(await readFile(resolve(args.payload)));
  const privateKeyPem = await readFile(resolve(args.key), "utf8");
  const publicKeyPem = await readFile(resolve(args.publicKey), "utf8");
  let metadata;
  try {
    metadata = JSON.parse(await readFile(resolve(args.metadata), "utf8"));
  } catch (e) {
    process.stderr.write(`eatf-sign: metadata is not valid JSON: ${e?.message ?? e}\n`);
    return 2;
  }
  let timestampBytes;
  try {
    timestampBytes = await loadTimestamp(args.timestamp);
  } catch (e) {
    process.stderr.write(`eatf-sign: cannot load timestamp: ${e?.message ?? e}\n`);
    return 2;
  }
  let warrant;
  if (args.warrant) {
    if (!existsSync(args.warrant)) {
      process.stderr.write(`eatf-sign: file not found: ${args.warrant}\n`);
      return 2;
    }
    try {
      warrant = JSON.parse(await readFile(resolve(args.warrant), "utf8"));
    } catch (e) {
      process.stderr.write(`eatf-sign: warrant is not valid JSON: ${e?.message ?? e}\n`);
      return 2;
    }
  }

  let voiding;
  if (args.voiding) {
    if (!existsSync(args.voiding)) {
      process.stderr.write(`eatf-sign: file not found: ${args.voiding}\n`);
      return 2;
    }
    try {
      voiding = JSON.parse(await readFile(resolve(args.voiding), "utf8"));
    } catch (e) {
      process.stderr.write(`eatf-sign: voiding is not valid JSON: ${e?.message ?? e}\n`);
      return 2;
    }
    if (!Array.isArray(voiding)) {
      process.stderr.write(`eatf-sign: --voiding must be a JSON array of predicates\n`);
      return 2;
    }
  }

  let acceptingAuthority;
  if (args.acceptingAuthority) {
    if (!existsSync(args.acceptingAuthority)) {
      process.stderr.write(`eatf-sign: file not found: ${args.acceptingAuthority}\n`);
      return 2;
    }
    try {
      acceptingAuthority = JSON.parse(await readFile(resolve(args.acceptingAuthority), "utf8"));
    } catch (e) {
      process.stderr.write(`eatf-sign: accepting-authority is not valid JSON: ${e?.message ?? e}\n`);
      return 2;
    }
  }

  let acceptance;
  if (args.acceptanceJson || args.acceptanceSig) {
    if (!args.acceptanceJson || !args.acceptanceSig) {
      process.stderr.write(`eatf-sign: --acceptance-json and --acceptance-sig must be supplied together\n`);
      return 2;
    }
    for (const f of [args.acceptanceJson, args.acceptanceSig]) {
      if (!existsSync(f)) {
        process.stderr.write(`eatf-sign: file not found: ${f}\n`);
        return 2;
      }
    }
    let acceptanceRecord;
    try {
      acceptanceRecord = JSON.parse(await readFile(resolve(args.acceptanceJson), "utf8"));
    } catch (e) {
      process.stderr.write(`eatf-sign: acceptance-json is not valid JSON: ${e?.message ?? e}\n`);
      return 2;
    }
    const sig = (await readFile(resolve(args.acceptanceSig), "utf8")).trim();
    acceptance = { json: acceptanceRecord, sig };
  }

  const { sign } = await loadSigner();
  try {
    const result = await sign({
      payload: payloadBytes,
      privateKeyPem,
      publicKeyPem,
      metadata,
      overtScope: args.scope,
      timestampTsr: timestampBytes,
      iap: args.iap ?? undefined,
      canonicalForm: args.canonicalForm ?? undefined,
      warrant: warrant ?? undefined,
      voiding: voiding ?? undefined,
      acceptingAuthority: acceptingAuthority ?? undefined,
      acceptance: acceptance ?? undefined,
    });
    await writeFile(resolve(args.out), result.aep);
    process.stdout.write(`Signed → ${args.out}\n`);
    process.stdout.write(`  entries: ${result.entries.join(", ")}\n`);
    process.stdout.write(`  canonical.bin SHA-256: ${result.canonicalHashHex}\n`);
    process.stdout.write(`  size: ${result.aep.byteLength} bytes\n`);
    return 0;
  } catch (e) {
    process.stderr.write(`eatf-sign: ${e?.message ?? e}\n`);
    return 1;
  }
}

main().then((code) => process.exit(code)).catch((e) => {
  process.stderr.write(`eatf-sign: ${e?.stack ?? e}\n`);
  process.exit(1);
});
