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
 * Optional entries ride the same pipeline: the OVERT-inspired receipt is
 * cross-checked after the RSA step, the warrant (spec §4.2) right
 * after it, and warrant freshness once genTime and TSA trust are known.
 *
 * Each step appends to the report; a single failure short-circuits.
 *
 * Alongside the prose report, every step records a verdict against the
 * closed CHECK_REGISTRY (check-registry.ts) via recordCheck(); the
 * result carries the full per-check BoundaryReport — including the
 * registry tail a short-circuit never reached — so a relying party can
 * see what was assessed, what failed without gating (advisory checks),
 * and what was never looked at.
 */

import { unzipSync } from "fflate";

import { canonical, jcs } from "./canonical.js";
import { sha256, toHex } from "./hash.js";
import { decodeBase64, importRsaPublicKey, verifyRsa, verifyRsaDigestInfo } from "./rsa.js";
import { verifyMlDsa65 } from "./mldsa.js";
import { inspectTsa, verifyTsaTrust } from "./tsa.js";
import { DEFAULT_TSA_TRUST_LIST } from "./tsa-trust-list.js";
import { parseAndValidateOvertReceipt, type OvertReceipt } from "./overt.js";
import { parseAndCheckWarrant, type WarrantValidation } from "./warrant.js";
import { parseAndCheckMandate, type MandateValidation } from "./mandate.js";
import { evaluateVoiding } from "./voiding.js";
import { parseAndCheckAcceptance } from "./acceptance.js";
import {
  CHECK_REGISTRY,
  CHECK_REGISTRY_VERSION,
  checkRegistryDigest,
  type CheckId,
} from "./check-registry.js";
import type {
  AcceptingAuthorityResult,
  BoundaryReport,
  CanonicalForm,
  CheckReason,
  CheckVerdict,
  MandateResult,
  VerifyOptions,
  VerifyResult,
  VoidingVerdict,
  WarrantResult,
} from "./index.js";

const TEXT_DEC = new TextDecoder();

/** SHA-256 AlgorithmIdentifier OID expected in the TSA message imprint. */
const SHA256_IMPRINT_OID = "2.16.840.1.101.3.4.2.1";

export async function verify(
  input: Uint8Array | ArrayBuffer | Blob,
  opts: VerifyOptions = {},
): Promise<VerifyResult> {
  const report: string[] = [];
  const registryDigest = await checkRegistryDigest();
  const boundary = createBoundaryRecorder(registryDigest);
  const bytes = await toBytes(input);
  let metadata: Record<string, unknown> | null = null;
  let overtReceipt: OvertReceipt | null = null;

  let entries: Record<string, Uint8Array>;
  try {
    entries = unzipSync(bytes);
  } catch (e) {
    boundary.recordCheck("zip-structure", "fail");
    return fail(boundary, report, "Package is not a valid ZIP.", metadata);
  }
  boundary.recordCheck("zip-structure", "pass");
  report.push(`Package unzipped (${Object.keys(entries).length} entries).`);

  // Required entries.
  const required = ["response.txt", "canonical.bin", "hash.sha256", "signature.sig", "public_key.pem", "metadata.json", "timestamp.tsr"];
  for (const name of required) {
    if (!entries[name]) {
      boundary.recordCheck("required-entries", "fail");
      return fail(boundary, report, `Missing required entry: ${name}.`, metadata);
    }
  }
  boundary.recordCheck("required-entries", "pass");

  // Parse metadata.json for reporting + re-canonicalisation.
  try {
    metadata = JSON.parse(TEXT_DEC.decode(entries["metadata.json"]!)) as Record<string, unknown>;
  } catch {
    boundary.recordCheck("metadata-parse", "fail", { reason: "parse_failure" });
    return fail(boundary, report, "metadata.json is not valid JSON.", metadata);
  }
  boundary.recordCheck("metadata-parse", "pass");
  report.push("metadata.json parsed.");

  // Recompute supported canonical forms. The written AEP profile uses
  // response + LF + JCS(metadata); the current Java package generator still
  // emits response-only canonical bytes for sign-only bundles. Accept both,
  // then always verify hash/signatures over the embedded canonical.bin.
  const profileCanonical = canonical({
    responseBytes: entries["response.txt"]!,
    metadataBytes: jcs(metadata),
  });
  const packagedCanonical = entries["canonical.bin"]!;
  let canonicalForm: CanonicalForm;
  if (constantTimeEqual(profileCanonical, packagedCanonical)) {
    canonicalForm = "profile";
    boundary.recordCheck("canonical-profile", "pass");
    boundary.recordCheck("canonical-response-only", "not_assessed", { reason: "short_circuited" });
    report.push("Canonical bytes match AEP profile canonical form.");
  } else if (constantTimeEqual(entries["response.txt"]!, packagedCanonical)) {
    canonicalForm = "response-only";
    // The profile form was assessed and did not match; the package is
    // accepted anyway through the compatibility branch, so that
    // failure is advisory in this run.
    boundary.recordCheck("canonical-profile", "fail", { enforced: false });
    boundary.recordCheck("canonical-response-only", "pass");
    report.push("Canonical bytes match Java response-only canonical form.");
  } else {
    boundary.recordCheck("canonical-profile", "fail");
    boundary.recordCheck("canonical-response-only", "fail");
    return fail(boundary, report, "canonical.bin does not match a supported canonical form.", metadata);
  }
  const canonicalBytes = packagedCanonical;

  // Hash check.
  const expectedHashHex = TEXT_DEC.decode(entries["hash.sha256"]!).trim().toLowerCase();
  const actualHashBytes = await sha256(canonicalBytes);
  const actualHashHex = toHex(actualHashBytes);
  if (actualHashHex !== expectedHashHex) {
    boundary.recordCheck("hash-sha256", "fail");
    return fail(boundary, report, "Hash mismatch.", metadata, null, null, canonicalForm);
  }
  boundary.recordCheck("hash-sha256", "pass");
  report.push("SHA-256 hash matches.");

  // RSA signature verification.
  const rsaPem = TEXT_DEC.decode(entries["public_key.pem"]!);
  const rsaSigB64 = TEXT_DEC.decode(entries["signature.sig"]!).trim();
  const rsaSig = decodeBase64(rsaSigB64);
  let rsaPrimaryOk: boolean;
  let rsaFallbackOk: boolean | null;
  try {
    const key = await importRsaPublicKey(rsaPem);
    rsaPrimaryOk = await verifyRsa(key, rsaSig, canonicalBytes);
    rsaFallbackOk = rsaPrimaryOk ? null : verifyRsaDigestInfo(rsaPem, rsaSig, actualHashBytes);
  } catch (e) {
    boundary.recordCheck("rsa-signature", "not_determinate", { reason: "parse_failure" });
    boundary.recordCheck("rsa-digestinfo-fallback", "not_assessed", { reason: "short_circuited" });
    return fail(boundary, report, `RSA verify error: ${(e as Error).message}.`, metadata, null, null, canonicalForm);
  }
  if (rsaPrimaryOk) {
    boundary.recordCheck("rsa-signature", "pass");
    boundary.recordCheck("rsa-digestinfo-fallback", "not_assessed", { reason: "short_circuited" });
  } else if (rsaFallbackOk) {
    // Web Crypto refused the signature but the DigestInfo re-check
    // accepted it; the primary failure is advisory in this run.
    boundary.recordCheck("rsa-signature", "fail", { enforced: false });
    boundary.recordCheck("rsa-digestinfo-fallback", "pass");
  } else {
    boundary.recordCheck("rsa-signature", "fail");
    boundary.recordCheck("rsa-digestinfo-fallback", "fail");
    return fail(boundary, report, "RSA signature does not verify against public_key.pem.", metadata, null, null, canonicalForm);
  }
  report.push("RSA-4096 signature verified.");

  // Issuer key pinning (spec §8). The default trust model is
  // self-attestation: the package carries the key that verifies it, and
  // WITHOUT a caller-supplied list nothing distinguishes the issuer's key
  // from any other well-formed RSA key. A relying party that knows which
  // issuer it will accept supplies `trustedSignerPems`; membership then
  // GATES, on the pattern of the TSA trust list but enforcing rather than
  // reporting. Absent the list, the check is not assessed and the verdict
  // says so — a package re-authored end-to-end under a different key is
  // authentic evidence of a different issuer's claim, not of this one's.
  const signerTrustList = opts.trustedSignerPems ?? [];
  if (signerTrustList.length > 0) {
    const normalized = normalizePem(rsaPem);
    const pinned = signerTrustList.some((pem) => normalizePem(pem) === normalized);
    if (!pinned) {
      boundary.recordCheck("signer-key-pinned", "fail");
      return fail(
        boundary,
        report,
        "public_key.pem is not a member of the caller-supplied trustedSignerPems list.",
        metadata,
        null,
        null,
        canonicalForm,
      );
    }
    boundary.recordCheck("signer-key-pinned", "pass");
    report.push("Signing key pinned: public_key.pem is a member of the caller-supplied trust list.");
  } else {
    boundary.recordCheck("signer-key-pinned", "not_assessed", { reason: "option_disabled" });
  }

  const overt = parseAndValidateOvertReceipt(entries, metadata, expectedHashHex);
  overtReceipt = overt.receipt;
  if (overt.error) {
    boundary.recordCheck("overt-receipt", "fail");
    return fail(boundary, report, `overt_receipt.json invalid: ${overt.error}.`, metadata, null, overtReceipt, canonicalForm);
  }
  if (overtReceipt) {
    boundary.recordCheck("overt-receipt", "pass");
  } else {
    boundary.recordCheck("overt-receipt", "not_assessed", { reason: "input_absent" });
  }
  report.push(
    overtReceipt
      ? `OVERT-inspired receipt verified (${String(overtReceipt.scope)}).`
      : "OVERT-inspired receipt absent (optional profile entry).",
  );

  // Optional warrant.json cross-check (spec §4.2). Binding-family
  // inconsistencies reject like an inconsistent OVERT-inspired receipt;
  // applicability is an appraisal outcome that is reported and never
  // rejects. Freshness is judged later, once the RFC 3161 genTime and
  // the TSA trust verdict are known.
  const warrantCheck = await parseAndCheckWarrant(entries, metadata, canonicalForm);
  let warrant: WarrantResult | null = null;
  if (!warrantCheck.referenced) {
    boundary.recordCheck("warrant-digest", "not_assessed", { reason: "input_absent" });
    boundary.recordCheck("warrant-parse", "not_assessed", { reason: "input_absent" });
    boundary.recordCheck("warrant-bound", "not_assessed", { reason: "input_absent" });
    boundary.recordCheck("warrant-policy-link", "not_assessed", { reason: "input_absent" });
    boundary.recordCheck("warrant-applicability", "not_assessed", { reason: "input_absent" });
    boundary.recordCheck("warrant-acceptance-signature", "not_assessed", { reason: "input_absent" });
    report.push("Warrant absent (optional profile entry).");
  } else {
    warrant = toWarrantResult(warrantCheck);
    if (warrantCheck.errorCheck === "warrant-digest") {
      boundary.recordCheck("warrant-digest", "fail");
      return fail(boundary, report, `warrant.json invalid: ${warrantCheck.error}.`, metadata, null, overtReceipt, canonicalForm, warrant);
    }
    boundary.recordCheck("warrant-digest", "pass");
    if (warrantCheck.errorCheck === "warrant-parse") {
      boundary.recordCheck("warrant-parse", "fail", { reason: "parse_failure" });
      return fail(boundary, report, `warrant.json invalid: ${warrantCheck.error}.`, metadata, null, overtReceipt, canonicalForm, warrant);
    }
    boundary.recordCheck("warrant-parse", "pass");
    if (warrantCheck.bound) {
      boundary.recordCheck("warrant-bound", "pass");
    } else {
      // Assessed and failed, accepted anyway: response-only packages
      // stay accepted, so the unbound state is advisory — but under
      // that form metadata.warrant_digest itself is rewritable.
      boundary.recordCheck("warrant-bound", "fail", { enforced: false });
      report.push(
        "Warrant present but unbound: the response-only canonical form leaves metadata.warrant_digest outside signature.sig.",
      );
    }
    if (warrantCheck.errorCheck === "warrant-policy-link") {
      boundary.recordCheck("warrant-policy-link", "fail");
      return fail(boundary, report, `warrant.json invalid: ${warrantCheck.error}.`, metadata, null, overtReceipt, canonicalForm, warrant);
    }
    boundary.recordCheck("warrant-policy-link", "pass");
    if (warrantCheck.applicable === null) {
      boundary.recordCheck("warrant-applicability", "not_determinate", { reason: "input_absent" });
      report.push(
        "Warrant applicability not determinate: metadata.action_type or metadata.policy_decision absent.",
      );
    } else if (warrantCheck.applicable) {
      boundary.recordCheck("warrant-applicability", "pass");
    } else {
      boundary.recordCheck("warrant-applicability", "fail", { enforced: false });
      report.push(
        "Warrant does not apply to this action: the output may inform but carries no warrant to compel.",
      );
    }
    if (warrantCheck.errorCheck === "warrant-acceptance-signature") {
      boundary.recordCheck("warrant-acceptance-signature", "fail");
      return fail(boundary, report, `warrant.json invalid: ${warrantCheck.error}.`, metadata, null, overtReceipt, canonicalForm, warrant);
    }
    boundary.recordCheck("warrant-acceptance-signature", "pass");
    report.push(
      `Warrant verified (${String(warrantCheck.record?.["warrant_id"])}, accepted by ${String(
        (warrantCheck.record?.["acceptance"] as Record<string, unknown> | undefined)?.["authority_id"],
      )}).`,
    );
  }

  // Optional detached deontic mandate (spec §4.5). The four
  // binding-family checks GATE: a mandate whose bytes, record shape,
  // binding to the protected bytes, or signature is inconsistent makes
  // the verifier reject, and — unlike §4.2 and §4.3 — so does a mandate
  // carried under the response-only form, where its own digest
  // reference is rewritable. Scope is an appraisal outcome, reported
  // and never rejecting. Temporal containment is judged later, once the
  // RFC 3161 genTime is known.
  const mandateCheck = await parseAndCheckMandate(entries, metadata, canonicalForm);
  let mandate: MandateResult | null = null;
  if (!mandateCheck.referenced) {
    for (const id of MANDATE_BINDING_CHECKS) {
      boundary.recordCheck(id, "not_assessed", { reason: "input_absent" });
    }
    report.push("Authorizing principal absent (optional profile entry).");
  } else if (!mandateCheck.claimed) {
    // A deontic principal named without a signed mandate: the pre-§4.5
    // reference form. Legal, and nothing about it is verified.
    mandate = toMandateResult(mandateCheck);
    for (const id of MANDATE_BINDING_CHECKS) {
      boundary.recordCheck(id, "not_determinate", { enforced: false, reason: "input_absent" });
    }
    report.push(
      "Authorizing principal named without a signed mandate: the deontic layer is a reference only and nothing in it is verified.",
    );
  } else {
    mandate = toMandateResult(mandateCheck);
    if (mandateCheck.errorCheck === "mandate-digest") {
      boundary.recordCheck("mandate-digest", "fail");
      return fail(boundary, report, `mandate.json invalid: ${mandateCheck.error}.`, metadata, null, overtReceipt, canonicalForm, warrant, mandate);
    }
    boundary.recordCheck("mandate-digest", "pass");
    if (mandateCheck.errorCheck === "mandate-parse") {
      boundary.recordCheck("mandate-parse", "fail", { reason: "parse_failure" });
      return fail(boundary, report, `mandate.json invalid: ${mandateCheck.error}.`, metadata, null, overtReceipt, canonicalForm, warrant, mandate);
    }
    boundary.recordCheck("mandate-parse", "pass");
    if (mandateCheck.errorCheck === "mandate-bound") {
      boundary.recordCheck("mandate-bound", "fail");
      return fail(boundary, report, `mandate.json invalid: ${mandateCheck.error}.`, metadata, null, overtReceipt, canonicalForm, warrant, mandate);
    }
    boundary.recordCheck("mandate-bound", "pass");
    if (mandateCheck.errorCheck === "mandate-signature") {
      boundary.recordCheck("mandate-signature", "fail");
      return fail(boundary, report, `mandate.json invalid: ${mandateCheck.error}.`, metadata, null, overtReceipt, canonicalForm, warrant, mandate);
    }
    boundary.recordCheck("mandate-signature", "pass");
    if (mandateCheck.inScope === null) {
      boundary.recordCheck("mandate-scope", "not_determinate", { reason: "input_absent" });
      report.push(
        "Mandate scope not determinate: metadata.action_type or metadata.policy_id absent.",
      );
    } else if (mandateCheck.inScope) {
      boundary.recordCheck("mandate-scope", "pass");
    } else {
      boundary.recordCheck("mandate-scope", "fail", { enforced: false });
      report.push(
        "Action lies outside the granted mandate: the output may inform but carries no mandate to compel.",
      );
    }
    report.push(
      `Mandate verified (${String(mandateCheck.record?.["mandate_id"])}, granted by ${String(
        mandateCheck.record?.["principal"],
      )} to ${String(mandateCheck.record?.["subject"])}).`,
    );
  }

  // Optional ML-DSA-65 verification.
  let pqcValid: boolean | null = null;
  if (entries["signature_pqc.sig"] && entries["pqc_public_key.pem"]) {
    const pqcSigB64 = TEXT_DEC.decode(entries["signature_pqc.sig"]!).trim();
    const pqcSig = decodeBase64(pqcSigB64);
    const pqcPem = TEXT_DEC.decode(entries["pqc_public_key.pem"]!);
    try {
      pqcValid = await verifyMlDsa65(pqcPem, pqcSig, canonicalBytes);
      report.push(`ML-DSA-65 signature ${pqcValid ? "verified" : "FAILED"}.`);
      if (!pqcValid) {
        boundary.recordCheck("pqc-mldsa65", "fail");
        return fail(boundary, report, "ML-DSA-65 signature does not verify.", metadata, pqcValid, overtReceipt, canonicalForm, warrant, mandate);
      }
      boundary.recordCheck("pqc-mldsa65", "pass");
    } catch (e) {
      // A verify ERROR (as opposed to a clean false) does not fail the
      // package: pqcValid is set to false and verification continues.
      report.push(`ML-DSA-65 verify error: ${(e as Error).message}.`);
      pqcValid = false;
      boundary.recordCheck("pqc-mldsa65", "not_determinate", { enforced: false, reason: "parse_failure" });
    }
  } else {
    boundary.recordCheck("pqc-mldsa65", "not_assessed", { reason: "input_absent" });
    report.push("ML-DSA-65 entries absent (transitional v1 package).");
  }

  // v0.1: full RFC 3161 inspection via pkijs — message
  // imprint, SignerInfo signature against embedded cert, genTime,
  // signer DNs.
  const tsaB64 = TEXT_DEC.decode(entries["timestamp.tsr"]!).trim();
  const tsa = await inspectTsa(tsaB64, expectedHashHex);
  if (!tsa.tsaPresent) {
    boundary.recordCheck("tsa-present", "fail");
    return fail(boundary, report, "timestamp.tsr missing or empty.", metadata, pqcValid, overtReceipt, canonicalForm, warrant, mandate);
  }
  boundary.recordCheck("tsa-present", "pass");
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
  if (tsa.messageImprintMatches === true) {
    boundary.recordCheck("tsa-imprint", "pass");
  } else if (tsa.messageImprintMatches === false) {
    boundary.recordCheck("tsa-imprint", "fail");
    report.push("RFC 3161 message imprint does not match hash.sha256 (accepted for Java reference compatibility).");
  } else {
    boundary.recordCheck("tsa-imprint", "not_determinate", {
      reason:
        tsa.imprintAlgorithmOid && tsa.imprintAlgorithmOid !== SHA256_IMPRINT_OID
          ? "capability_absent"
          : "parse_failure",
    });
  }
  if (tsa.signatureVerified === false) {
    boundary.recordCheck("tsa-signerinfo", "fail");
    return fail(
      boundary,
      report,
      "RFC 3161 SignerInfo signature did not verify against the embedded cert.",
      metadata,
      pqcValid,
      overtReceipt,
      canonicalForm,
      warrant,
      mandate,
    );
  }
  if (tsa.signatureVerified === true) {
    boundary.recordCheck("tsa-signerinfo", "pass");
  } else {
    boundary.recordCheck("tsa-signerinfo", "not_determinate", { enforced: false, reason: "input_absent" });
  }

  // v0.1 — chain-to-root cross-check. Default trust list
  // is the three pinned DigiCert public roots used by the reference
  // profile; callers can opt out by passing `tsaTrustList: []` or
  // override them with roots for another external timestamp authority.
  let tsaTrusted: boolean | null = null;
  const trustList = opts.tsaTrustList ?? DEFAULT_TSA_TRUST_LIST;
  if (trustList.length > 0) {
    const trust = await verifyTsaTrust(tsa, trustList);
    tsaTrusted = trust.trusted;
    if (trust.trusted === true) {
      boundary.recordCheck("tsa-chain-to-root", "pass");
    } else if (trust.trusted === false) {
      boundary.recordCheck("tsa-chain-to-root", "fail");
    } else {
      boundary.recordCheck("tsa-chain-to-root", "not_determinate", { reason: "input_absent" });
    }
    report.push(
      `TSA chain-to-root: trusted=${trust.trusted}. ${trust.reason}`,
    );
  } else {
    boundary.recordCheck("tsa-chain-to-root", "not_assessed", { reason: "option_disabled" });
  }

  // Warrant freshness (spec §4.2): judged against the RFC 3161 genTime
  // and the validity window. A fresh verdict additionally needs the
  // TSA trust verdict — an untrusted clock can refute freshness (a
  // genTime outside the window is self-refuting) but never establish it.
  if (warrant && warrantCheck.validFrom && warrantCheck.validUntil) {
    if (!tsa.genTime) {
      boundary.recordCheck("warrant-freshness", "not_determinate", { reason: "parse_failure" });
      report.push("Warrant freshness not determinate: the timestamp genTime could not be read.");
    } else if (tsa.genTime < warrantCheck.validFrom || tsa.genTime > warrantCheck.validUntil) {
      warrant.fresh = false;
      boundary.recordCheck("warrant-freshness", "fail", { enforced: false });
      report.push(
        `Warrant not in force at signing time: genTime ${tsa.genTime.toISOString()} lies outside valid_from..valid_until.`,
      );
    } else if (tsaTrusted === true) {
      warrant.fresh = true;
      boundary.recordCheck("warrant-freshness", "pass");
      report.push("Warrant in force at signing time: genTime inside valid_from..valid_until under a trusted TSA.");
    } else {
      boundary.recordCheck("warrant-freshness", "not_determinate", {
        reason: trustList.length === 0 ? "option_disabled" : "input_absent",
      });
      report.push(
        "Warrant freshness not determinate: genTime lies inside valid_from..valid_until, but the TSA does not chain to a trusted root.",
      );
    }
  } else {
    boundary.recordCheck("warrant-freshness", "not_assessed", { reason: "input_absent" });
  }

  // Mandate temporal containment (spec §4.5): the RFC 3161 genTime against
  // the mandate's own validity window. Appraisal — an action taken outside
  // the window is reported, and the package stays accepted.
  if (mandate && mandateCheck.validFrom && mandateCheck.validUntil) {
    if (!tsa.genTime) {
      boundary.recordCheck("mandate-temporal", "not_determinate", { reason: "parse_failure" });
      report.push("Mandate temporal containment not determinate: the timestamp genTime could not be read.");
    } else {
      const inside =
        tsa.genTime >= mandateCheck.validFrom && tsa.genTime <= mandateCheck.validUntil;
      mandate.temporalContainment = inside;
      if (inside) {
        boundary.recordCheck("mandate-temporal", "pass", { enforced: false });
      } else {
        boundary.recordCheck("mandate-temporal", "fail", { enforced: false });
        report.push(
          `Mandate not in force at signing time: genTime ${tsa.genTime.toISOString()} lies outside valid_from..valid_until.`,
        );
      }
    }
  } else if (mandateCheck.referenced && !mandateCheck.claimed) {
    boundary.recordCheck("mandate-temporal", "not_determinate", { enforced: false, reason: "input_absent" });
  } else {
    boundary.recordCheck("mandate-temporal", "not_assessed", { reason: "input_absent" });
  }

  // Per-output voiding predicates (spec §4.4). Every predicate is evaluated
  // against caller-supplied inputs (a dated registry snapshot, a supersession
  // list) — never a network fetch — and emits a four-valued verdict. For
  // registry-status predicates the same snapshot is read twice, at genTime
  // and at the snapshot instant, and the pair is surfaced, never collapsed.
  // Informational: a "voided" verdict does not flip `valid` in this release.
  const voidingVerdicts: VoidingVerdict[] | null = evaluateVoiding(metadata, {
    genTime: tsa.genTime ?? null,
    registrySnapshot: opts.registrySnapshot,
    supersessionList: opts.supersessionList,
    tsaTrusted,
  });
  if (voidingVerdicts === null) {
    boundary.recordCheck("voiding-predicates", "not_assessed", { reason: "input_absent" });
  } else {
    boundary.recordCheck("voiding-predicates", "pass", { enforced: false });
    const voided = voidingVerdicts.filter((v) => v.verdict === "voided").length;
    const diverged = voidingVerdicts.filter(
      (v) => v.atSigning !== undefined && v.now !== undefined && v.atSigning !== v.now,
    ).length;
    report.push(
      `Voiding predicates evaluated (${voidingVerdicts.length}): ${voided} voided, ` +
        `${diverged} with a diverged at-signing/now pair (informational).`,
    );
  }

  // Epistemic accepting authority (spec §4.3). Key binding, output binding,
  // temporal containment, and role are reported separately; binding
  // verification and authorization appraisal stay distinct. The two
  // binding-family checks GATE, on the §4.5 rule and for the same reason:
  // §4.3 is surface added in this work and carries no compatibility debt, so
  // an acceptance that is forged, stripped, re-pointed, or carried under the
  // response-only form — where the whole block is rewritable — is REJECTED
  // rather than reported beside a `valid: true` verdict. Temporal containment
  // and role are appraisal and never reject.
  const acceptance = await parseAndCheckAcceptance(
    entries,
    metadata,
    canonicalForm,
    tsa.genTime ?? null,
    opts.authorityTrustList,
  );
  let acceptingAuthority: AcceptingAuthorityResult | null = null;
  if (!acceptance.referenced) {
    boundary.recordCheck("accepting-authority-binding", "not_assessed", { reason: "input_absent" });
    boundary.recordCheck("accepting-authority-key-binding", "not_assessed", { reason: "input_absent" });
    boundary.recordCheck("accepting-authority-temporal", "not_assessed", { reason: "input_absent" });
    boundary.recordCheck("accepting-authority-role", "not_assessed", { reason: "input_absent" });
    report.push("Accepting authority absent (optional profile entry).");
  } else {
    acceptingAuthority = {
      keyBindingValid: acceptance.keyBindingValid,
      boundToOutput: acceptance.boundToOutput,
      temporalContainment: acceptance.temporalContainment,
      roleVerified: acceptance.roleVerified,
    };
    recordTriState(boundary, "accepting-authority-binding", acceptance.boundToOutput);
    recordTriState(boundary, "accepting-authority-key-binding", acceptance.keyBindingValid);
    recordTriState(boundary, "accepting-authority-temporal", acceptance.temporalContainment);
    recordTriState(boundary, "accepting-authority-role", acceptance.roleVerified);
    if (acceptance.boundToOutput === false && canonicalForm !== "profile") {
      report.push(
        "Accepting authority present but unbound: the response-only canonical form leaves metadata.accepting_authority outside signature.sig.",
      );
    }
    report.push(
      `Accepting authority checked (keyBinding=${acceptance.keyBindingValid}, ` +
        `bound=${acceptance.boundToOutput}, temporal=${acceptance.temporalContainment}, ` +
        `role=${acceptance.roleVerified}) — binding and key binding gate; ` +
        `temporal containment and role are appraisal.`,
    );
    if (acceptance.errorCheck !== null) {
      return fail(
        boundary,
        report,
        `acceptance invalid: ${acceptance.error}.`,
        metadata,
        pqcValid,
        overtReceipt,
        canonicalForm,
        warrant,
        mandate,
        voidingVerdicts,
        acceptingAuthority,
        tsaTrusted,
      );
    }
  }

  return {
    valid: true,
    report,
    failureReason: null,
    canonicalForm,
    pqcValid,
    metadata,
    overtReceipt,
    warrant,
    tsaTrusted,
    voidingVerdicts,
    acceptingAuthority,
    mandate,
    boundary: boundary.finalize(canonicalForm, metadata),
  };
}

/**
 * The five §4.5 mandate checks that execute in the binding step, in
 * registry order. `mandate-temporal` is judged later, once the RFC 3161
 * genTime is known, and is recorded separately.
 */
const MANDATE_BINDING_CHECKS = [
  "mandate-digest",
  "mandate-parse",
  "mandate-bound",
  "mandate-signature",
  "mandate-scope",
] as const satisfies readonly CheckId[];

/** Project the parse-and-cross-check outcome onto VerifyResult.mandate. */
function toMandateResult(check: MandateValidation): MandateResult {
  return {
    claimed: check.claimed,
    present: check.present,
    bound: check.bound,
    signatureVerified: check.signatureVerified,
    inScope: check.inScope,
    temporalContainment: null,
    principal: check.record !== null && typeof check.record["principal"] === "string"
      ? (check.record["principal"] as string)
      : null,
  };
}

/**
 * Record one accepting-authority tri-state onto the boundary: true -> pass,
 * false -> fail, null -> not_determinate/input_absent.
 *
 * `enforced` follows the registry for pass and fail — true for the two
 * binding-family checks, false for temporal containment and role. A
 * `not_determinate` verdict is recorded `enforced: false` whatever the
 * registry says, because a property that could not be determined on this
 * input did not gate this run.
 */
function recordTriState(
  boundary: BoundaryRecorder,
  id:
    | "accepting-authority-binding"
    | "accepting-authority-key-binding"
    | "accepting-authority-temporal"
    | "accepting-authority-role",
  value: boolean | null,
): void {
  if (value === true) {
    boundary.recordCheck(id, "pass");
  } else if (value === false) {
    boundary.recordCheck(id, "fail");
  } else {
    boundary.recordCheck(id, "not_determinate", { enforced: false, reason: "input_absent" });
  }
}

/** Project the parse-and-cross-check outcome onto VerifyResult.warrant. */
function toWarrantResult(check: WarrantValidation): WarrantResult {
  return {
    present: check.present,
    bound: check.bound,
    policyLinked: check.policyLinked,
    applicable: check.applicable,
    acceptanceVerified: check.acceptanceVerified,
    fresh: null,
  };
}

type BoundaryRecorder = {
  recordCheck: (
    id: CheckId,
    verdict: CheckVerdict,
    extra?: { enforced?: boolean; reason?: CheckReason },
  ) => void;
  finalize: (
    canonicalForm: CanonicalForm | null,
    metadata: Record<string, unknown> | null,
  ) => BoundaryReport;
};

/**
 * Bookkeeping for the BoundaryReport. recordCheck() stores one verdict
 * per registry check; finalize() emits the full registry in order,
 * marking every check never recorded — the tail behind a short-circuit
 * — as not_assessed/short_circuited with enforced=false. `enforced`
 * defaults to the registry's defaultEnforced for pass/fail verdicts
 * and to false for verdicts that did not gate this run.
 */
function createBoundaryRecorder(registryDigest: string): BoundaryRecorder {
  const records = new Map<CheckId, { verdict: CheckVerdict; enforced: boolean; reason?: CheckReason }>();

  const recordCheck: BoundaryRecorder["recordCheck"] = (id, verdict, extra) => {
    const entry = CHECK_REGISTRY.find((c) => c.id === id)!;
    const gates = verdict === "pass" || verdict === "fail" || verdict === "not_determinate";
    records.set(id, {
      verdict,
      enforced: extra?.enforced ?? (gates ? entry.defaultEnforced : false),
      ...(extra?.reason ? { reason: extra.reason } : {}),
    });
  };

  const finalize: BoundaryRecorder["finalize"] = (canonicalForm, metadata) => {
    const checks = CHECK_REGISTRY.map((entry) => {
      const rec = records.get(entry.id) ?? {
        verdict: "not_assessed" as CheckVerdict,
        enforced: false,
        reason: "short_circuited" as CheckReason,
      };
      return { id: entry.id, clause: entry.clause, ...rec };
    });

    const unsignedFields =
      canonicalForm === "response-only" && metadata
        ? Object.keys(metadata).sort().map((k) => `metadata.${k}`)
        : [];

    let claimedSurface: BoundaryReport["claimedSurface"] = null;
    const rawClaim = metadata?.["claimed_assessment_surface"];
    if (Array.isArray(rawClaim)) {
      const claimed = rawClaim
        .filter((v): v is string => typeof v === "string")
        .slice()
        .sort();
      const ids = new Set<string>(CHECK_REGISTRY.map((c) => c.id));
      const unrecognized = claimed.filter((c) => !ids.has(c));
      const notAssessed = claimed.filter((c) => {
        if (!ids.has(c)) return false;
        const rec = records.get(c as CheckId);
        return !rec || rec.verdict === "not_assessed" || rec.verdict === "not_determinate";
      });
      claimedSurface = { claimed, unrecognized, notAssessed };
    }

    return {
      registryVersion: CHECK_REGISTRY_VERSION,
      registryDigest,
      checks,
      canonicalForm,
      unsignedFields,
      claimedSurface,
    };
  };

  return { recordCheck, finalize };
}

function fail(
  boundary: BoundaryRecorder,
  report: string[],
  failureReason: string,
  metadata: Record<string, unknown> | null,
  pqcValid: boolean | null = null,
  overtReceipt: OvertReceipt | null = null,
  canonicalForm: CanonicalForm | null = null,
  warrant: WarrantResult | null = null,
  mandate: MandateResult | null = null,
  // Carried only by the §4.3 gate, the one rejection that happens after the
  // voiding and accepting-authority steps have already produced outcomes.
  // A rejection must not silently drop evidence the run had in hand.
  voidingVerdicts: VoidingVerdict[] | null = null,
  acceptingAuthority: AcceptingAuthorityResult | null = null,
  tsaTrusted: boolean | null = null,
): VerifyResult {
  report.push("FAIL: " + failureReason);
  return {
    valid: false,
    report,
    failureReason,
    canonicalForm,
    pqcValid,
    metadata,
    overtReceipt,
    warrant,
    tsaTrusted,
    voidingVerdicts,
    acceptingAuthority,
    mandate,
    boundary: boundary.finalize(canonicalForm, metadata),
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

/** Collapse PEM whitespace so trust-list membership survives newline differences. */
function normalizePem(pem: string): string {
  return pem.replace(/\s+/g, "");
}

function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= (a[i]! ^ b[i]!);
  }
  return diff === 0;
}
