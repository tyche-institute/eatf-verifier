#!/usr/bin/env node
/**
 * Rewrite-class probe: three deny-to-allow rewrite classes against the
 * SAME two-layer profile-form package (valid/mandated-denied-action), to
 * delimit exactly which adversary the profile canonical form and the two
 * signed authority layers close.
 *
 * Run from the repo root, after `(cd lib && npm run build)`:
 *
 *   node scripts/rewrite-class-probe.mjs
 *
 * B1 and B3 are frozen as vectors (invalid/profile-form-policy-rewrite and
 * boundary/reauthored-package-issuer-substitution); B2 is not, because it
 * fails the way invalid/tampered-metadata already does. Nothing here is
 * written to disk.
 *
 * B3 generates a fresh adversary keypair on every run rather than reading
 * the committed reauthoring-adversary-4096 fixture: the point is that ANY
 * well-formed RSA key does, because nothing in the package names the issuer
 * the reader expected. The frozen vector pins one such run.
 *
 *   B1  flip policy_decision in metadata.json + overt_receipt.json only
 *       (the identical rewrite of boundary/response-only-unsigned-policy-tamper)
 *   B2  B1 + recompute canonical.bin and hash.sha256 (adversary cannot re-sign)
 *   B3  B2 + re-sign with the ADVERSARY's own RSA key and swap public_key.pem
 *       (adversary holds a key, but not the issuer's)
 */
import { readFileSync } from "node:fs";
import { createSign, generateKeyPairSync } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const ROOT_URL = new URL("../", import.meta.url);
const require = createRequire(new URL("lib/package.json", ROOT_URL));
const { unzipSync, zipSync } = require("fflate");
const { verify } = await import(new URL("lib/dist/index.js", ROOT_URL).href);
const { jcs, canonical } = await import(new URL("lib/dist/canonical.js", ROOT_URL).href);
const { sha256, toHex } = await import(new URL("lib/dist/hash.js", ROOT_URL).href);

const ROOT = fileURLToPath(ROOT_URL);
const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);
const TE = new TextEncoder();
const base = unzipSync(new Uint8Array(readFileSync(path.join(ROOT, "test-vectors/valid/mandated-denied-action/package.aep"))));

function flip(entries) {
  const m = JSON.parse(Buffer.from(entries["metadata.json"]).toString("utf8"));
  m.policy_decision = "allow";
  entries["metadata.json"] = TE.encode(JSON.stringify(m) + "\n");
  const r = JSON.parse(Buffer.from(entries["overt_receipt.json"]).toString("utf8"));
  r.policy.decision = "allow";
  entries["overt_receipt.json"] = TE.encode(JSON.stringify(r) + "\n");
  return m;
}

async function report(label, entries) {
  const aep = zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME });
  const res = await verify(aep);
  console.log(`${label}`);
  console.log(`    valid=${res.valid}  failureReason=${res.failureReason ?? "(none)"}`);
  console.log(`    canonicalForm=${res.canonicalForm}  mandate=${JSON.stringify(res.mandate)}`);
  console.log(`    metadata.policy_decision as read by the verifier = ${JSON.stringify(res.metadata?.policy_decision)}`);
  return res;
}

// B1
{
  const e = { ...base };
  flip(e);
  await report("B1  flip the two unsigned-in-the-legacy-form files only", e);
}
// B2
{
  const e = { ...base };
  const m = flip(e);
  const canon = canonical({ responseBytes: e["response.txt"], metadataBytes: jcs(m) });
  e["canonical.bin"] = canon;
  const h = toHex(await sha256(canon));
  e["hash.sha256"] = TE.encode(h + "\n");
  const r = JSON.parse(Buffer.from(e["overt_receipt.json"]).toString("utf8"));
  r.content_hash = "sha256:" + h;
  e["overt_receipt.json"] = TE.encode(JSON.stringify(r) + "\n");
  await report("B2  + recompute canonical.bin, hash.sha256, receipt content_hash (no issuer key)", e);
}
// B3
{
  const e = { ...base };
  const m = flip(e);
  const canon = canonical({ responseBytes: e["response.txt"], metadataBytes: jcs(m) });
  e["canonical.bin"] = canon;
  const h = toHex(await sha256(canon));
  e["hash.sha256"] = TE.encode(h + "\n");
  const r = JSON.parse(Buffer.from(e["overt_receipt.json"]).toString("utf8"));
  r.content_hash = "sha256:" + h;
  e["overt_receipt.json"] = TE.encode(JSON.stringify(r) + "\n");
  const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 4096 });
  const s = createSign("sha256");
  s.update(canon);
  s.end();
  e["signature.sig"] = TE.encode(s.sign(privateKey).toString("base64") + "\n");
  e["public_key.pem"] = TE.encode(publicKey.export({ type: "spki", format: "pem" }));
  await report("B3  + re-sign with an ADVERSARY key and swap public_key.pem", e);
}
