/**
 * v0.1 — unit tests for the pkijs-based TSA verifier path.
 *
 * Full end-to-end testing against a real DigiCert-signed TSR is
 * out-of-scope here (it would require shipping a binary sample and
 * tying tests to a wall-clock-sensitive cert validity window). What
 * this suite locks down:
 *
 *   - Empty / missing token → tsaPresent=false, no crash.
 *   - Bogus / non-CMS DER → tsaPresent=false with a useful note.
 *   - verifyTsaTrust against an empty trust list → returns null
 *     (skipped), never throws.
 *   - verifyTsaTrust against a TSA-not-present check → returns null.
 *   - DEFAULT_TSA_TRUST_LIST is exported and non-empty (v0.4 promoted
 *     it from the v0.2 empty placeholder to ship the three pinned
 *     DigiCert public roots — see tsa-trust-list.test.ts for the
 *     SHA-256 fingerprint cross-check).
 */

import { describe, expect, it } from "vitest";

import { inspectTsa, verifyTsaTrust } from "../src/tsa.js";
import { DEFAULT_TSA_TRUST_LIST } from "../src/tsa-trust-list.js";

describe("inspectTsa", () => {
  it("returns tsaPresent=false for empty input", async () => {
    const check = await inspectTsa("", "deadbeef");
    expect(check.tsaPresent).toBe(false);
    expect(check.messageImprintMatches).toBeNull();
    expect(check.signatureVerified).toBeNull();
    expect(check.note).toMatch(/No timestamp/i);
  });

  it("returns tsaPresent=false for whitespace-only input", async () => {
    const check = await inspectTsa("   \n  \t  ", "deadbeef");
    expect(check.tsaPresent).toBe(false);
  });

  it("rejects too-short binary as not-a-TSR", async () => {
    // "AAAA" decodes to 3 bytes, which is < the 32-byte minimum.
    const check = await inspectTsa("AAAA", "deadbeef");
    expect(check.tsaPresent).toBe(false);
    expect(check.note).toMatch(/too short/i);
  });

  it("rejects garbage that does parse as ASN.1 but is not CMS SignedData", async () => {
    // 64 bytes of pseudo-random base64 that is unlikely to parse as
    // ContentInfo + SignedData. Whatever happens, tsaPresent must be
    // false (no crash) and the note should mention parsing or the
    // ContentInfo OID.
    const bigGarbage = Buffer.from(new Uint8Array(80).fill(0x42)).toString("base64");
    const check = await inspectTsa(bigGarbage, "deadbeef");
    expect(check.tsaPresent).toBe(false);
    // Note will mention one of: ASN.1 parse, ContentInfo parse, or
    // unexpected contentType. We only care that it didn't throw.
    expect(check.note).toBeDefined();
  });
});

describe("verifyTsaTrust", () => {
  it("returns trusted=null when the TSA is not present", async () => {
    const noTsa = await inspectTsa("", "deadbeef");
    const trust = await verifyTsaTrust(noTsa, [
      "-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----",
    ]);
    expect(trust.trusted).toBeNull();
    expect(trust.reason).toMatch(/not present/i);
  });

  it("returns trusted=null when the trust list is empty (skipped)", async () => {
    // Use a stub check that pretends a TSA is present so we hit the
    // empty-list branch. Real production code reaches this via the
    // result of inspectTsa(); here we construct a minimal shape.
    const trust = await verifyTsaTrust(
      {
        tsaPresent: true,
        messageImprintMatches: true,
        signatureVerified: true,
        imprintAlgorithmOid: "2.16.840.1.101.3.4.2.1",
        genTime: new Date("2026-01-01T00:00:00Z"),
        embeddedCertCount: 1,
        signerSubject: "CN=Demo TSA",
        signerIssuer: "CN=Demo Root",
        rawSizeBytes: 1024,
      },
      [],
    );
    expect(trust.trusted).toBeNull();
    expect(trust.reason).toMatch(/empty trust list/i);
  });

  it("DEFAULT_TSA_TRUST_LIST is non-empty (v0.4 ships the DigiCert pinned roots)", () => {
    expect(DEFAULT_TSA_TRUST_LIST.length).toBeGreaterThan(0);
    // The trust-list module guarantees three roots in v0.4; tsa-trust-list.test.ts
    // pins the exact identities and fingerprints. Here we only assert the
    // shape so the contract that callers see (non-empty default → enables
    // chain-to-root validation by default) is locked in.
  });
});
