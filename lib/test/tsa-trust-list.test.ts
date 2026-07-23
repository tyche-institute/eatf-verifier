/**
 * v0.1 — guards the three pinned DigiCert root PEMs
 * against silent mutation.
 *
 * Each public-root PEM is checked against the SHA-256 fingerprint
 * DigiCert publishes at
 * {@code https://www.digicert.com/kb/digicert-root-certificates.htm}.
 * An accidental byte edit anywhere in the trust-list module fails
 * the corresponding assertion immediately, which is precisely the
 * intent — a trust anchor that silently drifted from upstream is
 * a security regression, not a refactor.
 *
 * Also asserts that {@link DEFAULT_TSA_TRUST_LIST} is non-empty (v0.4
 * promoted it from the v0.2 empty placeholder) and that each entry
 * parses cleanly into a pkijs {@link Certificate}.
 */

import { createHash } from "node:crypto";

import { Certificate } from "pkijs";
import * as asn1js from "asn1js";
import { describe, expect, it } from "vitest";

import {
  DEFAULT_TSA_TRUST_LIST,
  DIGICERT_ASSURED_ID_ROOT_CA_PEM,
  DIGICERT_GLOBAL_ROOT_CA_PEM,
  DIGICERT_ROOT_FINGERPRINTS,
  DIGICERT_TRUSTED_ROOT_G4_PEM,
} from "../src/tsa-trust-list.js";

/** Strip PEM markers and decode base64 → DER. */
function pemToDer(pem: string): Uint8Array {
  const b64 = pem
    .replace(/-----BEGIN [^-]+-----/g, "")
    .replace(/-----END [^-]+-----/g, "")
    .replace(/\s+/g, "");
  return Uint8Array.from(Buffer.from(b64, "base64"));
}

/** Canonical uppercase colon-separated SHA-256 fingerprint format. */
function sha256ColonFingerprint(der: Uint8Array): string {
  const hex = createHash("sha256").update(der).digest("hex").toUpperCase();
  return (hex.match(/.{2}/g) ?? []).join(":");
}

describe("DEFAULT_TSA_TRUST_LIST (v0.4)", () => {
  it("is non-empty — ships the three DigiCert public roots", () => {
    expect(DEFAULT_TSA_TRUST_LIST).toHaveLength(3);
    expect(DEFAULT_TSA_TRUST_LIST).toContain(DIGICERT_GLOBAL_ROOT_CA_PEM);
    expect(DEFAULT_TSA_TRUST_LIST).toContain(DIGICERT_ASSURED_ID_ROOT_CA_PEM);
    expect(DEFAULT_TSA_TRUST_LIST).toContain(DIGICERT_TRUSTED_ROOT_G4_PEM);
  });

  it("every entry parses as a pkijs Certificate (no PEM corruption)", () => {
    for (const pem of DEFAULT_TSA_TRUST_LIST) {
      const der = pemToDer(pem);
      const asn = asn1js.fromBER(der.slice().buffer);
      expect(asn.offset).toBeGreaterThan(-1);
      const cert = new Certificate({ schema: asn.result });
      expect(cert.subject.typesAndValues.length).toBeGreaterThan(0);
    }
  });
});

describe("DigiCert root fingerprints", () => {
  const cases: Array<[keyof typeof DIGICERT_ROOT_FINGERPRINTS, string]> = [
    ["DigiCertGlobalRootCA", DIGICERT_GLOBAL_ROOT_CA_PEM],
    ["DigiCertAssuredIDRootCA", DIGICERT_ASSURED_ID_ROOT_CA_PEM],
    ["DigiCertTrustedRootG4", DIGICERT_TRUSTED_ROOT_G4_PEM],
  ];

  it.each(cases)(
    "%s — SHA-256 matches DigiCert's published fingerprint",
    (rootName, pem) => {
      const expected = DIGICERT_ROOT_FINGERPRINTS[rootName];
      const actual = sha256ColonFingerprint(pemToDer(pem));
      expect(actual).toEqual(expected);
    },
  );
});
