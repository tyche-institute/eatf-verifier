/**
 * Phase 1 step 1.20 v0.2 — RFC 3161 timestamp parsing + verification.
 *
 * <p>This module parses a base64-encoded TimeStampToken via {@code pkijs}
 * and performs four independent checks:
 *
 * <ol>
 *   <li><b>tsaPresent</b> — the token is non-empty and parses as
 *       {@code ContentInfo} with the CMS SignedData OID
 *       ({@code 1.2.840.113549.1.7.2}).</li>
 *   <li><b>messageImprintMatches</b> — the {@code TSTInfo.messageImprint
 *       .hashedMessage} octet string equals {@code SHA-256(expectedHashHex
 *       as ASCII)}. The EATF AEP profile (see {@code docs/specs/aep
 *       -profile-v1.md} §7) hashes the lower-case hex string of the
 *       canonical SHA-256, not the canonical bytes themselves; this is
 *       the deliberate compatibility point with Java's
 *       {@code RealTsaServiceImpl}.</li>
 *   <li><b>signatureVerified</b> — the embedded
 *       {@code SignerInfo.signature} validates against the embedded
 *       signing certificate's public key over the
 *       {@code signedAttributes} (CMS RFC 5652 §5.4). This is the
 *       "internally consistent" check: the entity holding the
 *       certificate did sign this messageImprint at this genTime.</li>
 *   <li><b>genTime</b> — the {@code TSTInfo.genTime} timestamp, returned
 *       as a JavaScript {@code Date} for downstream policy. Not a check
 *       in itself; the caller decides whether to enforce a window.</li>
 * </ol>
 *
 * <p>Trust-anchor chain validation is a <em>separate</em> step exposed
 * by {@link verifyTsaTrust} so an operator can opt in / out
 * independently of the internal-consistency checks.
 *
 * <p>v0.1-alpha shipped a regex-over-hex heuristic for
 * messageImprintMatches and left signatureVerified always {@code null}.
 * This module replaces both with deterministic ASN.1 parsing and a
 * real Web Crypto signature verify.
 */

import * as asn1js from "asn1js";
import {
  Certificate,
  ContentInfo,
  SignedData,
  setEngine,
  CryptoEngine,
} from "pkijs";

import { sha256 } from "./hash.js";
import { decodeBase64 } from "./rsa.js";
import type { TsaTrustResult } from "./tsa-trust-list.js";

// PKIjs requires an explicit crypto engine. In Node 20+ and modern
// browsers `globalThis.crypto.subtle` exists; we register it once
// per module load and keep the registration idempotent across hot
// reload + test runners.
let engineConfigured = false;
function configureEngine(): void {
  if (engineConfigured) return;
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new Error(
      "@eatf/verifier requires globalThis.crypto.subtle (Node 20+ or modern browser).",
    );
  }
  setEngine(
    "@eatf/verifier-engine",
    new CryptoEngine({ name: "@eatf/verifier-engine", crypto: globalThis.crypto, subtle }),
  );
  engineConfigured = true;
}

export type TsaCheck = {
  /** Token is non-empty and parses as RFC 3161 ContentInfo + SignedData. */
  tsaPresent: boolean;
  /** Imprint inside the token equals SHA-256 of the expected hash hex. */
  messageImprintMatches: boolean | null;
  /** SignerInfo signature verifies against the embedded cert's public key. */
  signatureVerified: boolean | null;
  /** Hash algorithm OID inside the imprint (typically 2.16.840.1.101.3.4.2.1 for SHA-256). */
  imprintAlgorithmOid: string | null;
  /** TSTInfo.genTime, as a JavaScript Date. */
  genTime: Date | null;
  /** Number of certificates embedded in the SignedData.certificates field. */
  embeddedCertCount: number;
  /** Subject DN of the embedded signing cert (informational). */
  signerSubject: string | null;
  /** Issuer DN of the embedded signing cert (informational). */
  signerIssuer: string | null;
  /** Total bytes of the DER-decoded token. */
  rawSizeBytes: number;
  /** Human-readable note when a step short-circuits. */
  note?: string;
};

const SHA256_OID = "2.16.840.1.101.3.4.2.1";
const CMS_SIGNED_DATA_OID = "1.2.840.113549.1.7.2";

function emptyCheck(note: string, rawSizeBytes = 0): TsaCheck {
  return {
    tsaPresent: false,
    messageImprintMatches: null,
    signatureVerified: null,
    imprintAlgorithmOid: null,
    genTime: null,
    embeddedCertCount: 0,
    signerSubject: null,
    signerIssuer: null,
    rawSizeBytes,
    note,
  };
}

export async function inspectTsa(
  timestampBase64: string,
  expectedHashHex: string,
): Promise<TsaCheck> {
  if (!timestampBase64 || !timestampBase64.trim()) {
    return emptyCheck("No timestamp.tsr in package.");
  }

  let der: Uint8Array;
  try {
    der = decodeBase64(timestampBase64.trim());
  } catch (e) {
    return emptyCheck(`timestamp.tsr is not valid base64: ${describeError(e)}`);
  }

  if (der.length < 32) {
    return emptyCheck("TSR too short to be a TimeStampToken.", der.length);
  }

  configureEngine();

  // ----- Parse outer ContentInfo -----
  let contentInfo: ContentInfo;
  try {
    const fresh = der.slice();
    const asn = asn1js.fromBER(fresh.buffer);
    if (asn.offset === -1) {
      return emptyCheck("Outer DER did not parse as ASN.1.", der.length);
    }
    contentInfo = new ContentInfo({ schema: asn.result });
  } catch (e) {
    return emptyCheck(`ContentInfo parse failed: ${describeError(e)}`, der.length);
  }

  if (contentInfo.contentType !== CMS_SIGNED_DATA_OID) {
    return emptyCheck(
      `Unexpected ContentInfo.contentType ${contentInfo.contentType} (want CMS SignedData ${CMS_SIGNED_DATA_OID}).`,
      der.length,
    );
  }

  // ----- Parse SignedData + extract TSTInfo eContent bytes -----
  let signedData: SignedData;
  let tstInfoBytes: Uint8Array;
  try {
    signedData = new SignedData({ schema: contentInfo.content });
    const eContent = signedData.encapContentInfo.eContent;
    if (!eContent) {
      return emptyCheck("SignedData.encapContentInfo has no eContent (detached?).", der.length);
    }
    const vb = eContent.valueBlock as unknown as {
      valueHexView?: Uint8Array;
      valueHex?: ArrayBuffer;
    };
    if (vb.valueHexView) {
      tstInfoBytes = vb.valueHexView;
    } else if (vb.valueHex) {
      tstInfoBytes = new Uint8Array(vb.valueHex);
    } else {
      return emptyCheck("Cannot extract eContent bytes from SignedData.", der.length);
    }
  } catch (e) {
    return emptyCheck(`SignedData parse failed: ${describeError(e)}`, der.length);
  }

  // ----- Extract TSTInfo fields -----
  let imprintHashBytes: Uint8Array | null = null;
  let imprintAlgorithmOid: string | null = null;
  let genTime: Date | null = null;
  try {
    const tstAsn = asn1js.fromBER(tstInfoBytes.slice().buffer);
    if (tstAsn.offset === -1) {
      return emptyCheck("TSTInfo did not parse as ASN.1.", der.length);
    }
    // TSTInfo ::= SEQUENCE {
    //   version            INTEGER,
    //   policy             OBJECT IDENTIFIER,
    //   messageImprint     MessageImprint,
    //   serialNumber       INTEGER,
    //   genTime            GeneralizedTime,
    //   ...optionals
    // }
    const tstSeq = tstAsn.result as asn1js.Sequence;
    const items = tstSeq.valueBlock.value;
    // messageImprint is the 3rd element (index 2): SEQUENCE { algId, octetString }
    const mi = items[2] as asn1js.Sequence;
    const algId = mi.valueBlock.value[0] as asn1js.Sequence;
    const oidObj = algId.valueBlock.value[0] as asn1js.ObjectIdentifier;
    imprintAlgorithmOid = oidObj.valueBlock.toString();
    const hashOctet = mi.valueBlock.value[1] as asn1js.OctetString;
    const hashView = (hashOctet.valueBlock as unknown as {
      valueHexView?: Uint8Array;
      valueHex?: ArrayBuffer;
    });
    if (hashView.valueHexView) {
      imprintHashBytes = new Uint8Array(hashView.valueHexView);
    } else if (hashView.valueHex) {
      imprintHashBytes = new Uint8Array(hashView.valueHex);
    }
    // genTime is index 4 (GeneralizedTime).
    const gtNode = items[4] as asn1js.GeneralizedTime;
    if (gtNode && typeof gtNode.toDate === "function") {
      genTime = gtNode.toDate();
    }
  } catch (e) {
    return emptyCheck(
      `TSTInfo field extraction failed: ${describeError(e)}`,
      der.length,
    );
  }

  // ----- Compare imprint to expected -----
  let messageImprintMatches: boolean | null = null;
  if (imprintHashBytes && imprintAlgorithmOid === SHA256_OID) {
    const tsaInput = new TextEncoder().encode(expectedHashHex);
    const expectedDigest = new Uint8Array(await sha256(tsaInput));
    messageImprintMatches = constantTimeEqual(imprintHashBytes, expectedDigest);
  }

  // ----- Extract signing cert + verify SignerInfo signature -----
  const certs = (signedData.certificates ?? []).filter(
    (c): c is Certificate => c instanceof Certificate,
  );
  let signerSubject: string | null = null;
  let signerIssuer: string | null = null;
  if (certs.length > 0) {
    signerSubject = describeDn(certs[0]!.subject.typesAndValues as DnTypeAndValue[]);
    signerIssuer = describeDn(certs[0]!.issuer.typesAndValues as DnTypeAndValue[]);
  }

  let signatureVerified: boolean | null = null;
  try {
    if (certs.length === 0) {
      signatureVerified = null;
    } else {
      // pkijs.SignedData.verify resolves to a boolean (true = OK,
      // false = signature mismatch). It throws on structural problems
      // (missing signed attributes, OID mismatches, etc.) which we
      // surface separately below.
      const ok = await signedData.verify({
        signer: 0,
        data: tstInfoBytes.slice().buffer,
        trustedCerts: certs,
      });
      signatureVerified = ok === true;
    }
  } catch (e) {
    signatureVerified = false;
    return {
      tsaPresent: true,
      messageImprintMatches,
      signatureVerified,
      imprintAlgorithmOid,
      genTime,
      embeddedCertCount: certs.length,
      signerSubject,
      signerIssuer,
      rawSizeBytes: der.length,
      note: `SignerInfo verify threw: ${describeError(e)}`,
    };
  }

  return {
    tsaPresent: true,
    messageImprintMatches,
    signatureVerified,
    imprintAlgorithmOid,
    genTime,
    embeddedCertCount: certs.length,
    signerSubject,
    signerIssuer,
    rawSizeBytes: der.length,
    note:
      signatureVerified === true
        ? "TSA signature verified against embedded cert. Trust-anchor chain validation is a separate step (verifyTsaTrust)."
        : signatureVerified === false
        ? "TSA signature did not verify against embedded cert. Treat as tampered."
        : "TSA signature not checked (no embedded cert).",
  };
}

/**
 * Cross-check the embedded signing cert chain against a pinned trust
 * list. This is independent of {@link inspectTsa}; an operator may
 * choose to require it (production) or skip it (dev / no trust anchors
 * pinned yet).
 *
 * <p>v0.2 does a minimal validation: the embedded signer's issuer DN
 * must match the subject DN of at least one provided trust-list root.
 * Full RFC 5280 path validation (NotBefore / NotAfter / KeyUsage /
 * EKU / Basic Constraints / CRL / OCSP) is v0.3 territory.
 *
 * @param check the result of {@link inspectTsa}
 * @param trustList PEM-encoded root certificates. Empty → skipped.
 */
export async function verifyTsaTrust(
  check: TsaCheck,
  trustList: string[],
): Promise<TsaTrustResult> {
  if (!check.tsaPresent || check.embeddedCertCount === 0) {
    return {
      trusted: null,
      reason: "TSA not present or no embedded cert; nothing to validate.",
      signerSubject: check.signerSubject ?? undefined,
      signerIssuer: check.signerIssuer ?? undefined,
    };
  }
  if (trustList.length === 0) {
    return {
      trusted: null,
      reason: "Empty trust list — chain-to-root check skipped. Pass roots to enforce.",
      signerSubject: check.signerSubject ?? undefined,
      signerIssuer: check.signerIssuer ?? undefined,
    };
  }
  configureEngine();
  for (const pem of trustList) {
    let rootCert: Certificate;
    try {
      rootCert = parsePemCert(pem);
    } catch (e) {
      return {
        trusted: false,
        reason: `Trust list entry failed to parse: ${describeError(e)}`,
      };
    }
    const rootSubject = describeDn(rootCert.subject.typesAndValues as DnTypeAndValue[]);
    if (rootSubject === check.signerIssuer) {
      return {
        trusted: true,
        reason: `Signer issuer matches pinned root (${rootSubject}).`,
        signerSubject: check.signerSubject ?? undefined,
        signerIssuer: check.signerIssuer ?? undefined,
      };
    }
  }
  return {
    trusted: false,
    reason: `Signer issuer "${check.signerIssuer}" does not match any pinned root.`,
    signerSubject: check.signerSubject ?? undefined,
    signerIssuer: check.signerIssuer ?? undefined,
  };
}

/* ------- helpers ------- */

function parsePemCert(pem: string): Certificate {
  const lines = pem.replace(/\r/g, "").split("\n").map((l) => l.trim());
  const b64 = lines.filter((l) => l && !l.startsWith("-----")).join("");
  const der = decodeBase64(b64);
  const asn = asn1js.fromBER(der.slice().buffer);
  if (asn.offset === -1) {
    throw new Error("PEM contents did not parse as ASN.1.");
  }
  return new Certificate({ schema: asn.result });
}

type DnTypeAndValue = {
  type: string;
  value: { valueBlock: { value: string } };
};

function describeDn(entries: DnTypeAndValue[]): string {
  const map: Record<string, string> = {
    "2.5.4.3": "CN",
    "2.5.4.6": "C",
    "2.5.4.7": "L",
    "2.5.4.8": "ST",
    "2.5.4.10": "O",
    "2.5.4.11": "OU",
    "1.2.840.113549.1.9.1": "emailAddress",
  };
  return entries
    .map((e) => {
      const label = map[e.type] ?? e.type;
      const v = e.value?.valueBlock?.value ?? "";
      return `${label}=${v}`;
    })
    .join(",");
}

function describeError(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i]! ^ b[i]!;
  return diff === 0;
}
