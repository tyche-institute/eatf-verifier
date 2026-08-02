/**
 * v0.1: top-level verifier entry.
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
import { parseAndValidateOvertReceipt, type OvertReceipt } from "./overt.js";
import type { FailureCode, VerifyOptions, VerifyResult } from "./index.js";

const TEXT_DEC = new TextDecoder();
const MAX_ARCHIVE_BYTES = 64 * 1024 * 1024;
const MAX_ENTRY_BYTES = 16 * 1024 * 1024;
const MAX_EXPANDED_BYTES = 32 * 1024 * 1024;
const MAX_ENTRIES = 32;

export async function verify(
  input: Uint8Array | ArrayBuffer | Blob,
  opts: VerifyOptions = {},
): Promise<VerifyResult> {
  const report: string[] = [];
  const bytes = await toBytes(input);
  let metadata: Record<string, unknown> | null = null;
  let overtReceipt: OvertReceipt | null = null;

  if (bytes.byteLength > MAX_ARCHIVE_BYTES) {
    return fail(
      report,
      "ZIP_ARCHIVE_LIMIT",
      "Package exceeds the 64 MiB archive safety limit.",
      metadata,
    );
  }

  let entries: Record<string, Uint8Array>;
  try {
    let entryCount = 0;
    let expandedBytes = 0;
    const names = new Set<string>();
    entries = unzipSync(bytes, {
      filter: (file) => {
        entryCount += 1;
        expandedBytes += file.originalSize;
        if (entryCount > MAX_ENTRIES) throw new Error("too many ZIP entries");
        if (file.originalSize > MAX_ENTRY_BYTES) throw new Error("ZIP entry too large");
        if (expandedBytes > MAX_EXPANDED_BYTES) throw new Error("expanded ZIP too large");
        if (
          file.name.includes("/") ||
          file.name.includes("\\") ||
          file.name.includes("\0")
        ) {
          throw new Error("AEP entries must use flat, safe names");
        }
        if (names.has(file.name)) throw new Error("duplicate ZIP entry");
        names.add(file.name);
        return true;
      },
    });
  } catch (e) {
    return fail(
      report,
      "ZIP_INVALID_OR_UNSAFE",
      `Package failed ZIP parsing or safety limits: ${(e as Error).message}.`,
      metadata,
    );
  }
  report.push(`Package unzipped (${Object.keys(entries).length} entries).`);

  // Required entries.
  const required = ["response.txt", "canonical.bin", "hash.sha256", "signature.sig", "public_key.pem", "metadata.json", "timestamp.tsr"];
  for (const name of required) {
    if (!entries[name]) {
      return fail(
        report,
        "REQUIRED_ENTRY_MISSING",
        `Missing required entry: ${name}.`,
        metadata,
      );
    }
  }

  // Parse metadata.json for reporting + re-canonicalisation.
  try {
    const parsed = JSON.parse(TEXT_DEC.decode(entries["metadata.json"]!)) as unknown;
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return fail(
        report,
        "METADATA_NOT_OBJECT",
        "metadata.json is not a JSON object.",
        metadata,
      );
    }
    metadata = parsed as Record<string, unknown>;
  } catch {
    return fail(
      report,
      "METADATA_INVALID_JSON",
      "metadata.json is not valid JSON.",
      metadata,
    );
  }
  report.push("metadata.json parsed.");

  // Recompute supported canonical forms. Current signers use response + LF +
  // JCS(metadata). Response-only verification is read-only compatibility for
  // packages produced by early Java tooling; it does not authenticate metadata.
  let profileCanonical: Uint8Array;
  try {
    profileCanonical = canonical({
      responseBytes: entries["response.txt"]!,
      metadataBytes: jcs(metadata),
    });
  } catch (e) {
    return fail(
      report,
      "METADATA_NOT_CANONICALIZABLE",
      `metadata.json cannot be represented as RFC 8785 JCS: ${(e as Error).message}.`,
      metadata,
    );
  }
  const packagedCanonical = entries["canonical.bin"]!;
  if (constantTimeEqual(profileCanonical, packagedCanonical)) {
    report.push("Canonical bytes match AEP profile canonical form.");
  } else if (constantTimeEqual(entries["response.txt"]!, packagedCanonical)) {
    report.push(
      "Canonical bytes match legacy response-only form; metadata is not signature-bound.",
    );
  } else {
    return fail(
      report,
      "CANONICAL_FORM_MISMATCH",
      "canonical.bin does not match a supported canonical form.",
      metadata,
    );
  }
  const canonicalBytes = packagedCanonical;

  // Hash check.
  const expectedHashHex = TEXT_DEC.decode(entries["hash.sha256"]!).trim().toLowerCase();
  const actualHashBytes = await sha256(canonicalBytes);
  const actualHashHex = toHex(actualHashBytes);
  if (actualHashHex !== expectedHashHex) {
    return fail(report, "HASH_MISMATCH", "Hash mismatch.", metadata);
  }
  report.push("SHA-256 hash matches.");

  // RSA signature verification.
  const rsaPem = TEXT_DEC.decode(entries["public_key.pem"]!);
  if (opts.trustedSignerPems && opts.trustedSignerPems.length > 0) {
    const packagedKey = normalizedPemBody(rsaPem);
    const trusted = opts.trustedSignerPems.some(
      (pem) => normalizedPemBody(pem) === packagedKey,
    );
    if (!trusted) {
      return fail(
        report,
        "SIGNER_NOT_TRUSTED",
        "Signer public key is not in the caller-supplied trust set.",
        metadata,
      );
    }
    report.push("Signer public key matched the caller-supplied trust set.");
  } else {
    report.push("Signer identity trust not evaluated (no trustedSignerPems supplied).");
  }
  const rsaSigB64 = TEXT_DEC.decode(entries["signature.sig"]!).trim();
  let rsaSig: Uint8Array;
  try {
    rsaSig = decodeBase64(rsaSigB64);
  } catch (e) {
    return fail(
      report,
      "RSA_SIGNATURE_ENCODING",
      `signature.sig is not valid base64: ${(e as Error).message}.`,
      metadata,
    );
  }
  let rsaOk: boolean;
  let rsaKey: CryptoKey;
  try {
    rsaKey = await importRsaPublicKey(rsaPem);
    rsaOk = await verifyRsa(rsaKey, rsaSig, canonicalBytes);
    if (!rsaOk) {
      rsaOk = verifyRsaDigestInfo(rsaPem, rsaSig, actualHashBytes);
    }
  } catch (e) {
    return fail(
      report,
      "RSA_VERIFY_ERROR",
      `RSA verify error: ${(e as Error).message}.`,
      metadata,
    );
  }
  if (!rsaOk) {
    return fail(
      report,
      "RSA_SIGNATURE_INVALID",
      "RSA signature does not verify against public_key.pem.",
      metadata,
    );
  }
  report.push("RSA-4096 signature verified.");

  const overt = parseAndValidateOvertReceipt(entries, metadata, expectedHashHex);
  overtReceipt = overt.receipt;
  if (overt.error) {
    return fail(
      report,
      "OVERT_INVALID",
      `overt_receipt.json invalid: ${overt.error}.`,
      metadata,
      null,
      overtReceipt,
    );
  }
  report.push(
    overtReceipt
      ? `OVERT receipt verified (${String(overtReceipt.scope)}).`
      : "OVERT receipt absent (optional profile entry).",
  );
  const receiptSignatureName = metadata.overt_receipt_signature;
  if (receiptSignatureName !== undefined) {
    if (receiptSignatureName !== "overt_receipt.sig") {
      return fail(
        report,
        "OVERT_SIGNATURE_MARKER_INVALID",
        "metadata.overt_receipt_signature must equal overt_receipt.sig.",
        metadata,
        null,
        overtReceipt,
      );
    }
    const receiptBytes = entries["overt_receipt.json"];
    const receiptSignatureBytes = entries["overt_receipt.sig"];
    if (!receiptBytes || !receiptSignatureBytes || !overtReceipt) {
      return fail(
        report,
        "OVERT_SIGNATURE_REQUIRED",
        "Signed metadata requires overt_receipt.json and overt_receipt.sig.",
        metadata,
        null,
        overtReceipt,
      );
    }
    try {
      const receiptSig = decodeBase64(TEXT_DEC.decode(receiptSignatureBytes).trim());
      if (!(await verifyRsa(rsaKey, receiptSig, receiptBytes))) {
        return fail(
          report,
          "OVERT_SIGNATURE_INVALID",
          "OVERT receipt signature does not verify against public_key.pem.",
          metadata,
          null,
          overtReceipt,
        );
      }
    } catch (e) {
      return fail(
        report,
        "OVERT_SIGNATURE_ERROR",
        `OVERT receipt signature verify error: ${(e as Error).message}.`,
        metadata,
        null,
        overtReceipt,
      );
    }
    report.push("OVERT receipt signature verified (required by signed metadata).");
  } else if (entries["overt_receipt.sig"]) {
    return fail(
      report,
      "OVERT_SIGNATURE_UNMARKED",
      "Unmarked overt_receipt.sig is not accepted.",
      metadata,
      null,
      overtReceipt,
    );
  } else if (overtReceipt) {
    report.push(
      "Legacy OVERT receipt is cross-checked but not separately signature-bound.",
    );
  }

  // Optional ML-DSA-65 verification.
  let pqcValid: boolean | null = null;
  const hasPqcSignature = Boolean(entries["signature_pqc.sig"]);
  const hasPqcKey = Boolean(entries["pqc_public_key.pem"]);
  if (hasPqcSignature !== hasPqcKey) {
    return fail(
      report,
      "PQC_PAIR_INCOMPLETE",
      "ML-DSA-65 signature and public-key entries must be supplied together.",
      metadata,
      pqcValid,
      overtReceipt,
    );
  }
  if (!hasPqcSignature && opts.pqcPolicy === "required") {
    return fail(
      report,
      "PQC_SIGNATURE_REQUIRED",
      "Verification policy requires a complete ML-DSA-65 signature pair.",
      metadata,
      pqcValid,
      overtReceipt,
    );
  }
  if (hasPqcSignature && hasPqcKey) {
    const pqcSigB64 = TEXT_DEC.decode(entries["signature_pqc.sig"]!).trim();
    const pqcSig = decodeBase64(pqcSigB64);
    const pqcPem = TEXT_DEC.decode(entries["pqc_public_key.pem"]!);
    try {
      pqcValid = await verifyMlDsa65(pqcPem, pqcSig, canonicalBytes);
      report.push(`ML-DSA-65 signature ${pqcValid ? "verified" : "FAILED"}.`);
      if (!pqcValid) {
        return fail(
          report,
          "PQC_SIGNATURE_INVALID",
          "ML-DSA-65 signature does not verify.",
          metadata,
          pqcValid,
          overtReceipt,
        );
      }
    } catch (e) {
      pqcValid = false;
      return fail(
        report,
        "PQC_VERIFY_ERROR",
        `ML-DSA-65 verify error: ${(e as Error).message}.`,
        metadata,
        pqcValid,
        overtReceipt,
      );
    }
  } else {
    report.push("ML-DSA-65 entries absent (transitional v1 package).");
  }

  // v0.1: full RFC 3161 inspection via pkijs — message
  // imprint, SignerInfo signature against embedded cert, genTime,
  // signer DNs.
  const tsaB64 = TEXT_DEC.decode(entries["timestamp.tsr"]!).trim();
  const tsa = await inspectTsa(tsaB64, expectedHashHex, canonicalBytes);
  if (!tsa.tsaPresent) {
    return fail(
      report,
      "TSA_MISSING_OR_INVALID",
      "timestamp.tsr missing or empty.",
      metadata,
      pqcValid,
      overtReceipt,
    );
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
  if (tsa.messageImprintMatches !== true) {
    return fail(
      report,
      tsa.messageImprintMatches === false
        ? "TSA_IMPRINT_MISMATCH"
        : "TSA_IMPRINT_UNVERIFIABLE",
      tsa.messageImprintMatches === false
        ? "RFC 3161 message imprint does not match hash.sha256."
        : "RFC 3161 message imprint could not be validated as SHA-256.",
      metadata,
      pqcValid,
      overtReceipt,
    );
  }
  if (tsa.signatureVerified !== true) {
    return fail(
      report,
      tsa.signatureVerified === false
        ? "TSA_SIGNATURE_INVALID"
        : "TSA_CERT_MISSING",
      tsa.signatureVerified === false
        ? "RFC 3161 SignerInfo signature did not verify against the embedded certificate."
        : "RFC 3161 token does not contain a verifiable embedded signing certificate.",
      metadata,
      pqcValid,
      overtReceipt,
    );
  }

  // Optional issuer-name pin. This is intentionally not described as
  // RFC 5280 path validation: verifyTsaTrust compares the embedded
  // signer's issuer DN with explicitly supplied root subjects.
  let tsaTrusted: boolean | null = null;
  const trustList = opts.tsaTrustList ?? [];
  if (trustList.length > 0) {
    const trust = await verifyTsaTrust(tsa, trustList);
    tsaTrusted = trust.trusted;
    report.push(
      `TSA issuer-name pin: matched=${trust.trusted}. ${trust.reason}`,
    );
  }

  return {
    valid: true,
    report,
    failureReason: null,
    failureCode: null,
    pqcValid,
    metadata,
    overtReceipt,
    tsaTrusted,
  };
}

function fail(
  report: string[],
  failureCode: FailureCode,
  failureReason: string,
  metadata: Record<string, unknown> | null,
  pqcValid: boolean | null = null,
  overtReceipt: OvertReceipt | null = null,
): VerifyResult {
  report.push("FAIL: " + failureReason);
  return {
    valid: false,
    report,
    failureReason,
    failureCode,
    pqcValid,
    metadata,
    overtReceipt,
  };
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

function normalizedPemBody(pem: string): string {
  return pem
    .split(/\r?\n/)
    .filter((line) => !line.startsWith("-----"))
    .join("")
    .replace(/\s+/g, "");
}
