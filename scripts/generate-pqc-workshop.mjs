#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { unzipSync, zipSync } from "fflate";

import {
  generateMlDsa65Keypair,
  sign,
  verify,
} from "../lib/dist/index.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const WORKSHOP = resolve(ROOT, "workshops/pqc-hybrid-lab/packages");
// fflate writes ZIP/DOS local-time fields, so use a local constructor. The
// encoded value is then 1980-01-01 00:00 regardless of the host timezone.
const FIXED_ZIP_TIME = new Date(1980, 0, 1, 0, 0, 0);
const textDecoder = new TextDecoder();

function pack(entries) {
  const zippable = {};
  for (const [name, bytes] of Object.entries(entries)) {
    zippable[name] = [bytes, { mtime: FIXED_ZIP_TIME }];
  }
  return zipSync(zippable, { level: 0 });
}

function cloneEntries(packageBytes) {
  const clone = {};
  for (const [name, bytes] of Object.entries(unzipSync(packageBytes))) {
    clone[name] = new Uint8Array(bytes);
  }
  return clone;
}

function tamperPqcSignature(packageBytes) {
  const entries = cloneEntries(packageBytes);
  const signature = Buffer.from(
    textDecoder.decode(entries["signature_pqc.sig"]).trim(),
    "base64",
  );
  signature[signature.length - 1] ^= 1;
  entries["signature_pqc.sig"] = new TextEncoder().encode(
    signature.toString("base64") + "\n",
  );
  return pack(entries);
}

function remove(packageBytes, ...names) {
  const entries = cloneEntries(packageBytes);
  for (const name of names) delete entries[name];
  return pack(entries);
}

function tamperResponse(packageBytes) {
  const entries = cloneEntries(packageBytes);
  entries["response.txt"][0] ^= 1;
  return pack(entries);
}

async function sha256Hex(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

async function writePackage(relativePath, bytes) {
  const target = resolve(ROOT, relativePath);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, bytes);
}

async function main() {
  const payload = await readFile(resolve(ROOT, "examples/01-minimal-sign-and-verify/payload.txt"));
  const metadata = JSON.parse(
    await readFile(resolve(ROOT, "examples/01-minimal-sign-and-verify/metadata.json"), "utf8"),
  );
  const rsaPrivateKey = await readFile(
    resolve(ROOT, "test-vectors/keys/dev-rsa-4096.key"),
    "utf8",
  );
  const rsaPublicKey = await readFile(
    resolve(ROOT, "test-vectors/keys/dev-rsa-4096.pem"),
    "utf8",
  );
  const timestampSource = unzipSync(
    await readFile(resolve(ROOT, "test-vectors/valid/minimal-roundtrip/package.aep")),
  );
  const timestamp = Buffer.from(
    textDecoder.decode(timestampSource["timestamp.tsr"]).trim(),
    "base64",
  );
  const seed = createHash("sha256")
    .update("EATF public PKIC PQC workshop seed v1", "utf8")
    .digest();
  const keypair = await generateMlDsa65Keypair(seed);
  const signed = await sign({
    payload,
    privateKeyPem: rsaPrivateKey,
    publicKeyPem: rsaPublicKey,
    metadata,
    overtScope: "foundational:aep-response",
    timestampTsr: timestamp,
    iap: "eatf-verifier-public-workshop",
    pqcSecretKey: keypair.secretKey,
    pqcPublicKey: keypair.publicKey,
    pqcExtraEntropy: false,
  });
  const classical = await sign({
    payload,
    privateKeyPem: rsaPrivateKey,
    publicKeyPem: rsaPublicKey,
    metadata,
    overtScope: "foundational:aep-response",
    timestampTsr: timestamp,
    iap: "eatf-verifier-public-workshop",
  });

  const packages = {
    "01-valid-hybrid.aep": signed.aep,
    "02-pqc-signature-tampered.aep": tamperPqcSignature(signed.aep),
    "03-pqc-pair-stripped.aep": remove(
      signed.aep,
      "signature_pqc.sig",
      "pqc_public_key.pem",
    ),
    "04-classical-transition.aep": classical.aep,
    "05-pqc-signature-missing.aep": remove(signed.aep, "signature_pqc.sig"),
    "06-response-tampered.aep": tamperResponse(signed.aep),
  };
  await mkdir(WORKSHOP, { recursive: true });

  const manifest = { format: 1, packages: {} };
  for (const [name, bytes] of Object.entries(packages)) {
    await writeFile(resolve(WORKSHOP, name), bytes);
    const transitional = await verify(bytes, { pqcPolicy: "if-present" });
    const required = await verify(bytes, { pqcPolicy: "required" });
    manifest.packages[name] = {
      sha256: await sha256Hex(bytes),
      transitional: {
        valid: transitional.valid,
        failureCode: transitional.failureCode,
        pqcValid: transitional.pqcValid,
      },
      required: {
        valid: required.valid,
        failureCode: required.failureCode,
        pqcValid: required.pqcValid,
      },
    };
  }
  const manifestBytes = Buffer.from(JSON.stringify(manifest, null, 2) + "\n");
  await writeFile(resolve(WORKSHOP, "manifest.json"), manifestBytes);
  const checksumLines = [];
  for (const name of Object.keys(packages).sort()) {
    checksumLines.push(`${manifest.packages[name].sha256}  packages/${name}`);
  }
  checksumLines.push(`${await sha256Hex(manifestBytes)}  packages/manifest.json`);
  await writeFile(
    resolve(WORKSHOP, "..", "SHA256SUMS"),
    checksumLines.join("\n") + "\n",
  );

  await writePackage(
    "test-vectors/valid/hybrid-mldsa65/package.aep",
    packages["01-valid-hybrid.aep"],
  );
  await writePackage(
    "test-vectors/invalid/bad-signature-pqc/package.aep",
    packages["02-pqc-signature-tampered.aep"],
  );
  process.stdout.write("Generated deterministic PQC workshop and conformance packages.\n");
}

await main();
