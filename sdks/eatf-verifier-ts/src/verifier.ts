/**
 * Phase 1 step 1.20: top-level verifier entry.
 *
 * Pipeline (mirrors the Java reference):
 *   1. Unzip the .aep package.
 *   2. Read required entries (response.txt, canonical.bin, hash.sha256,
 *      signature.sig, public_key.pem, metadata.json, timestamp.tsr).
 *   3. Recompute supported canonical forms and compare to canonical.bin.
 *   4. Hash canonical bytes with SHA-256; compare to hash.sha256.
 *   5. Verify RSA signature with public_key.pem.
 *   6. If PQC entries present, verify ML-DSA-65 signature.
 *   7. Structural-check the RFC 3161 timestamp.
 *
 * Each step appends to the report; a single failure short-circuits.
 */

import { unzipSync } from "fflate";

import { canonical, jcs } from "./canonical.js";
import { sha256, toHex } from "./hash.js";
import { decodeBase64, importRsaPublicKey, verifyRsa, verifyRsaDigestInfo } from "./rsa.js";
import { verifyMlDsa65 } from "./mldsa.js";
import { inspectTsa, verifyTsaTrust } from "./tsa.js";
import { DEFAULT_TSA_TRUST_LIST } from "./tsa-trust-list.js";
import { parseAndValidateOvertReceipt, type OvertReceipt } from "./overt.js";
import type { VerifyOptions, VerifyResult } from "./index.js";

const TEXT_DEC = new TextDecoder();

export async function verify(
  input: Uint8Array | ArrayBuffer | Blob,
  opts: VerifyOptions = {},
): Promise<VerifyResult> {
  const report: string[] = [];
  const bytes = await toBytes(input);
  let metadata: Record<string, unknown> | null = null;
  let overtReceipt: OvertReceipt | null = null;

  let entries: Record<string, Uint8Array>;
  try {
    entries = unzipSync(bytes);
  } catch (e) {
    return fail(report, "Package is not a valid ZIP.", metadata);
  }
  report.push(`Package unzipped (${Object.keys(entries).length} entries).`);

  // Required entries.
  const required = ["response.txt", "canonical.bin", "hash.sha256", "signature.sig", "public_key.pem", "metadata.json", "timestamp.tsr"];
  for (const name of required) {
    if (!entries[name]) {
      return fail(report, `Missing required entry: ${name}.`, metadata);
    }
  }

  // Parse metadata.json for reporting + re-canonicalisation.
  try {
    metadata = JSON.parse(TEXT_DEC.decode(entries["metadata.json"]!)) as Record<string, unknown>;
  } catch {
    return fail(report, "metadata.json is not valid JSON.", metadata);
  }
  report.push("metadata.json parsed.");

  // Recompute supported canonical forms. Three are accepted:
  //   1. AEP profile:        response + LF + JCS(metadata)
  //   2. Java response-only: response.txt alone (sign-only legacy bundles)
  //   3. Production composite: response_canonical + LF + claim_envelope,
  //      where hash.sha256 + RSA + ML-DSA all cover ONLY the
  //      response_canonical prefix. Mirrors the Python reference verifier
  //      ._resolve_response_canonical in the Python SDK. The claim
  //      envelope begins with `\n{"claim":"…` because `claim` is the
  //      alphabetical-first key in ClaimCanonical; locate the last such
  //      boundary and treat the prefix as the signed bytes.
  const profileCanonical = canonical({
    responseBytes: entries["response.txt"]!,
    metadataBytes: jcs(metadata),
  });
  const packagedCanonical = entries["canonical.bin"]!;
  let canonicalBytes: Uint8Array = packagedCanonical;
  if (constantTimeEqual(profileCanonical, packagedCanonical)) {
    report.push("Canonical bytes match AEP profile canonical form.");
  } else if (constantTimeEqual(entries["response.txt"]!, packagedCanonical)) {
    report.push("Canonical bytes match Java response-only canonical form.");
  } else {
    const boundary = findLastClaimBoundary(packagedCanonical);
    if (boundary > 0) {
      canonicalBytes = packagedCanonical.subarray(0, boundary);
      report.push(
        `Canonical bytes match production composite form (signed prefix = ${canonicalBytes.length} bytes; unsigned claim suffix = ${packagedCanonical.length - boundary} bytes).`,
      );
    } else {
      return fail(report, "canonical.bin does not match a supported canonical form.", metadata);
    }
  }

  // Hash check.
  const expectedHashHex = TEXT_DEC.decode(entries["hash.sha256"]!).trim().toLowerCase();
  const actualHashBytes = await sha256(canonicalBytes);
  const actualHashHex = toHex(actualHashBytes);
  if (actualHashHex !== expectedHashHex) {
    return fail(report, "Hash mismatch.", metadata);
  }
  report.push("SHA-256 hash matches.");

  // RSA signature verification.
  const rsaPem = TEXT_DEC.decode(entries["public_key.pem"]!);
  const rsaSigB64 = TEXT_DEC.decode(entries["signature.sig"]!).trim();
  const rsaSig = decodeBase64(rsaSigB64);
  let rsaOk: boolean;
  try {
    const key = await importRsaPublicKey(rsaPem);
    rsaOk = await verifyRsa(key, rsaSig, canonicalBytes);
    if (!rsaOk) {
      rsaOk = verifyRsaDigestInfo(rsaPem, rsaSig, actualHashBytes);
    }
  } catch (e) {
    return fail(report, `RSA verify error: ${(e as Error).message}.`, metadata);
  }
  if (!rsaOk) {
    return fail(report, "RSA signature does not verify against public_key.pem.", metadata);
  }
  report.push("RSA-4096 signature verified.");

  const overt = parseAndValidateOvertReceipt(entries, metadata, expectedHashHex);
  overtReceipt = overt.receipt;
  if (overt.error) {
    return fail(report, `overt_receipt.json invalid: ${overt.error}.`, metadata, null, overtReceipt);
  }
  report.push(
    overtReceipt
      ? `OVERT receipt verified (${String(overtReceipt.scope)}).`
      : "OVERT receipt absent (optional profile entry).",
  );

  // Optional ML-DSA-65 verification. Two signing conventions are accepted:
  //   (a) signature over the same canonical bytes as RSA — what the
  //       open-source eatf-sign CLI emits.
  //   (b) signature over the 32-byte SHA-256 digest — what the
  //       reference signing implementation emits
  //       (see PqcSignatureService.java: "sign the given 32-byte hash").
  // We try (a) first to match the reference profile; on failure we fall
  // back to (b). Reporting distinguishes the two so operators can tell.
  let pqcValid: boolean | null = null;
  if (entries["signature_pqc.sig"] && entries["pqc_public_key.pem"]) {
    const pqcSigB64 = TEXT_DEC.decode(entries["signature_pqc.sig"]!).trim();
    const pqcSig = decodeBase64(pqcSigB64);
    const pqcPem = TEXT_DEC.decode(entries["pqc_public_key.pem"]!);
    try {
      pqcValid = await verifyMlDsa65(pqcPem, pqcSig, canonicalBytes);
      if (pqcValid) {
        report.push("ML-DSA-65 signature verified over canonical bytes (reference profile).");
      } else {
        pqcValid = await verifyMlDsa65(pqcPem, pqcSig, actualHashBytes);
        if (pqcValid) {
          report.push("ML-DSA-65 signature verified over SHA-256 digest (production digest-signing profile).");
        } else {
          report.push("ML-DSA-65 signature FAILED against both canonical bytes and SHA-256 digest.");
          return fail(report, "ML-DSA-65 signature does not verify.", metadata, pqcValid, overtReceipt);
        }
      }
    } catch (e) {
      report.push(`ML-DSA-65 verify error: ${(e as Error).message}.`);
      pqcValid = false;
    }
  } else {
    report.push("ML-DSA-65 entries absent (transitional v1 package).");
  }

  // Phase 1.20 v0.2: full RFC 3161 inspection via pkijs — message
  // imprint, SignerInfo signature against embedded cert, genTime,
  // signer DNs.
  const tsaB64 = TEXT_DEC.decode(entries["timestamp.tsr"]!).trim();
  const tsa = await inspectTsa(tsaB64, expectedHashHex);
  if (!tsa.tsaPresent) {
    return fail(report, "timestamp.tsr missing or empty.", metadata, pqcValid, overtReceipt);
  }
  report.push(
    `RFC 3161 timestamp present (${tsa.rawSizeBytes} bytes, genTime=${
      tsa.genTime ? tsa.genTime.toISOString() : "unknown"
    }). ` +
      `Message imprint match: ${
        tsa.messageImprintMatches == null ? "could not determine" : tsa.messageImprintMatches
      }. SignerInfo signature: ${
        tsa.signatureVerified == null ? "no embedded cert" : tsa.signatureVerified
      }. Signer: ${tsa.signerSubject ?? "unknown"} (issued by ${tsa.signerIssuer ?? "unknown"}).`,
  );
  if (tsa.messageImprintMatches === false) {
    report.push("RFC 3161 message imprint does not match hash.sha256 (accepted for Java reference compatibility).");
  }
  if (tsa.signatureVerified === false) {
    return fail(
      report,
      "RFC 3161 SignerInfo signature did not verify against the embedded cert.",
      metadata,
      pqcValid,
      overtReceipt,
    );
  }

  // Phase 1.20 v0.4 — chain-to-root cross-check. Default trust list
  // is the three pinned DigiCert public roots (production EATF uses
  // timestamp.digicert.com); callers can opt out by passing
  // `tsaTrustList: []` or override with their own roots (e.g. a
  // partner-QTSP cert once Phase 1.24 lands).
  let tsaTrusted: boolean | null = null;
  const trustList = opts.tsaTrustList ?? DEFAULT_TSA_TRUST_LIST;
  if (trustList.length > 0) {
    const trust = await verifyTsaTrust(tsa, trustList);
    tsaTrusted = trust.trusted;
    report.push(
      `TSA chain-to-root: trusted=${trust.trusted}. ${trust.reason}`,
    );
  }

  return {
    valid: true,
    report,
    failureReason: null,
    pqcValid,
    metadata,
    overtReceipt,
    tsaTrusted,
  };
}

function fail(
  report: string[],
  failureReason: string,
  metadata: Record<string, unknown> | null,
  pqcValid: boolean | null = null,
  overtReceipt: OvertReceipt | null = null,
): VerifyResult {
  report.push("FAIL: " + failureReason);
  return { valid: false, report, failureReason, pqcValid, metadata, overtReceipt };
}

async function toBytes(input: Uint8Array | ArrayBuffer | Blob): Promise<Uint8Array> {
  if (input instanceof Uint8Array) return input;
  if (input instanceof ArrayBuffer) return new Uint8Array(input);
  if (typeof Blob !== "undefined" && input instanceof Blob) {
    return new Uint8Array(await input.arrayBuffer());
  }
  throw new Error("Unsupported input type for verifier; pass Uint8Array, ArrayBuffer, or Blob.");
}

function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= (a[i]! ^ b[i]!);
  }
  return diff === 0;
}

// The byte sequence `\n{"claim":"` marking the start of the unsigned
// claim envelope appended by the production AiEvidenceController.
const CLAIM_BOUNDARY: ReadonlyArray<number> = [
  0x0a, 0x7b, 0x22, 0x63, 0x6c, 0x61, 0x69, 0x6d, 0x22, 0x3a, 0x22,
];

function findLastClaimBoundary(bytes: Uint8Array): number {
  outer: for (let i = bytes.length - CLAIM_BOUNDARY.length; i > 0; i--) {
    for (let j = 0; j < CLAIM_BOUNDARY.length; j++) {
      if (bytes[i + j] !== CLAIM_BOUNDARY[j]) continue outer;
    }
    return i;
  }
  return -1;
}
