import { describe, expect, test } from "vitest";

import {
  generateMlDsa65Keypair,
  mlDsa65PublicKeyFromPem,
  mlDsa65PublicKeyToPem,
  signMlDsa65,
  verifyMlDsa65,
} from "../src/mldsa.js";

describe("ML-DSA-65 FIPS 204 boundary", () => {
  test("round-trips an RFC 9881 SPKI key and verifies a deterministic signature", async () => {
    const keypair = await generateMlDsa65Keypair(new Uint8Array(32).fill(7));
    const message = new TextEncoder().encode("EATF ML-DSA interoperability test");
    const signature = await signMlDsa65(keypair.secretKey, message, false);
    const publicKeyPem = mlDsa65PublicKeyToPem(keypair.publicKey);

    expect(publicKeyPem).toContain("BEGIN PUBLIC KEY");
    expect(mlDsa65PublicKeyFromPem(publicKeyPem)).toEqual(keypair.publicKey);
    await expect(verifyMlDsa65(publicKeyPem, signature, message)).resolves.toBe(true);

    const changed = new Uint8Array(message);
    changed[0] ^= 1;
    await expect(verifyMlDsa65(publicKeyPem, signature, changed)).resolves.toBe(false);
  });

  test("rejects a SubjectPublicKeyInfo with a different algorithm identifier", async () => {
    const keypair = await generateMlDsa65Keypair(new Uint8Array(32).fill(9));
    const pem = mlDsa65PublicKeyToPem(keypair.publicKey);
    const der = Buffer.from(
      pem.replace(/-----BEGIN PUBLIC KEY-----|-----END PUBLIC KEY-----|\s+/g, ""),
      "base64",
    );
    der[16] ^= 1;
    const body = der.toString("base64").match(/.{1,64}/g)!.join("\n");
    const changed = `-----BEGIN PUBLIC KEY-----\n${body}\n-----END PUBLIC KEY-----\n`;

    expect(() => mlDsa65PublicKeyFromPem(changed)).toThrow("absent parameters");
  });
});
