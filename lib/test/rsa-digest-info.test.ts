import { constants, createHash, createPrivateKey, privateEncrypt, sign } from "node:crypto";
import { readFile } from "node:fs/promises";
import { unzipSync, zipSync } from "fflate";
import { describe, expect, test } from "vitest";

import { verifyRsaDigestInfo } from "../src/rsa.js";
import { verify } from "../src/verifier.js";

// RSA DigestInfo handling: RFC 8017 form, the exact legacy form, nothing else.
// Up to v0.7.3 the legacy fallback compared only the trailing 32 bytes after
// the padding. These tests sign hand-built blocks with the public development
// key; only the two exact encodings may pass.

const LEGACY_PREFIX = Buffer.from("302f300b06096086480165030402010420", "hex");
const RFC8017_PREFIX = Buffer.from("3031300d060960864801650304020105000420", "hex");
const SHA512_OID_PREFIX = Buffer.from("302f300b06096086480165030402030420", "hex");

async function fixtures() {
  const keyPem = await readFile(
    new URL("../../test-vectors/keys/dev-rsa-4096.key", import.meta.url),
    "utf8",
  );
  const key = createPrivateKey(keyPem);
  const source = await readFile(
    new URL("../../test-vectors/valid/minimal-roundtrip/package.aep", import.meta.url),
  );
  const entries = unzipSync(source);
  const canonical = entries["canonical.bin"]!;
  const digest = createHash("sha256").update(canonical).digest();
  const pem = new TextDecoder().decode(entries["public_key.pem"]!);
  const k = 512;
  const rawSign = (block: Buffer) =>
    new Uint8Array(privateEncrypt({ key, padding: constants.RSA_NO_PADDING }, block));
  const fullBlock = (t: Buffer) =>
    Buffer.concat([Buffer.from([0x00, 0x01]), Buffer.alloc(k - t.length - 3, 0xff), Buffer.from([0x00]), t]);
  const withSignature = (sig: Uint8Array) => {
    const copy = { ...entries };
    copy["signature.sig"] = new TextEncoder().encode(Buffer.from(sig).toString("base64"));
    return zipSync(copy, { level: 0 });
  };
  return { key, canonical, digest, pem, k, rawSign, fullBlock, withSignature };
}

describe("RSA DigestInfo", () => {
  test("RFC 8017 form verifies without the legacy note", async () => {
    const f = await fixtures();
    const sig = new Uint8Array(sign("sha256", f.canonical, f.key));
    expect(Buffer.from(f.rawSign(f.fullBlock(Buffer.concat([RFC8017_PREFIX, f.digest]))))).toEqual(
      Buffer.from(sig),
    );
    const result = await verify(f.withSignature(sig));
    expect(result.valid).toBe(true);
    expect(result.report.some((l) => l.includes("legacy SHA-256 DigestInfo"))).toBe(false);
  });

  test("the exact legacy form is accepted and reported", async () => {
    const f = await fixtures();
    const sig = f.rawSign(f.fullBlock(Buffer.concat([LEGACY_PREFIX, f.digest])));
    expect(verifyRsaDigestInfo(f.pem, sig, f.digest)).toBe(true);
    const result = await verify(f.withSignature(sig));
    expect(result.valid).toBe(true);
    expect(result.report.some((l) => l.includes("legacy SHA-256 DigestInfo"))).toBe(true);
  });

  const cases: Array<[string, (f: Awaited<ReturnType<typeof fixtures>>) => Buffer]> = [
    ["garbage-prefix", (f) => f.fullBlock(Buffer.concat([Buffer.alloc(17, 0x13), f.digest]))],
    [
      "garbage-after-legacy-prefix",
      (f) => f.fullBlock(Buffer.concat([LEGACY_PREFIX, Buffer.alloc(64), f.digest])),
    ],
    ["sha512-oid", (f) => f.fullBlock(Buffer.concat([SHA512_OID_PREFIX, f.digest]))],
    [
      "short-padding",
      (f) => {
        const head = Buffer.from([0x00, 0x01, 0x00]);
        const t = Buffer.concat([LEGACY_PREFIX, f.digest]);
        return Buffer.concat([head, Buffer.alloc(f.k - head.length - t.length, 0x42), t]);
      },
    ],
  ];

  test.each(cases)("rejects %s even though it ends in the digest", async (_label, build) => {
    const f = await fixtures();
    const block = build(f);
    expect(block.length).toBe(f.k);
    const sig = f.rawSign(block);
    expect(verifyRsaDigestInfo(f.pem, sig, f.digest)).toBe(false);
    const result = await verify(f.withSignature(sig));
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("RSA_SIGNATURE_INVALID");
  });
});
