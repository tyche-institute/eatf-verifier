/**
 * Detached deontic mandate: `mandate.json` / `mandate.sig`
 * (docs/specs/aep-profile-v1.md §4.5, schemas/mandate-v1.schema.json).
 *
 * `metadata.authorizing_principal` names the DEONTIC principal — the
 * authority that granted the subject agent a mandate to act. Until this
 * release the block was a bare reference: a principal name and a
 * `mandate_ref` string, additive, carrying no validity semantics and
 * gated on by nothing. This module gives the block a signed body.
 *
 * A mandate is a once-authored, versioned grant, signed by the granting
 * authority with a key of its own — a principal DISTINCT from both the
 * package issuer (`public_key.pem`) and the epistemic accepting
 * authority of §4.2/§4.3. It travels as JCS-canonical bytes in
 * `mandate.json`, with a detached PKCS#1 v1.5 RSA signature (inner
 * digest SHA-256) in `mandate.sig`, and is bound to the package by
 * `authorizing_principal.mandate_digest`.
 *
 * Four binding-family checks GATE verification; two appraisal checks are
 * reported and never reject:
 *
 *   mandate-digest     the packaged bytes match the digest reference.
 *   mandate-parse      the record is JCS-canonical JSON of the required shape.
 *   mandate-bound      the digest reference lies inside the protected
 *                      bytes (profile canonical form) AND the record's
 *                      principal / mandate_id / subject agree with the
 *                      signed metadata block. GATES: unlike §4.2 and
 *                      §4.3, a mandate that is not bound to the bytes the
 *                      signature covers is rejected rather than reported.
 *                      §4.5 is new surface and carries no compatibility
 *                      obligation to the response-only form, in which
 *                      `mandate_digest` is itself rewritable.
 *   mandate-signature  mandate.sig verifies over JCS(mandate.json)
 *                      against the record's embedded public_key.
 *   mandate-scope      the attested action_type and policy_id fall
 *                      inside the granted scope. Appraisal: an action
 *                      outside the mandate may inform, it cannot compel.
 *   mandate-temporal   the RFC 3161 genTime lies inside the mandate's
 *                      validity window. Appraisal, judged later in the
 *                      pipeline once genTime is known.
 *
 * A named principal with no signed mandate stays legal and is reported
 * as such: every check goes `not_determinate` and nothing is claimed.
 * The granting authority is a named principal with a verifiable key
 * binding, on the same self-attestation trust model as `public_key.pem`;
 * nothing here establishes it as a legally constituted authority, and
 * whether the grant it makes is lawful is attested, never machine-checked.
 */

import { jcs } from "./canonical.js";
import { sha256, toHex } from "./hash.js";
import { decodeBase64, importRsaPublicKey, verifyRsa } from "./rsa.js";
import { isRecord, textAt, valueAt } from "./overt.js";
import type { CanonicalForm } from "./index.js";

const TEXT_DEC = new TextDecoder();

export type MandateRecord = Record<string, unknown>;

/** The mandate sub-check an inconsistency belongs to (registry check id). */
export type MandateErrorCheck =
  | "mandate-digest"
  | "mandate-parse"
  | "mandate-bound"
  | "mandate-signature";

export type MandateValidation = {
  /** metadata.authorizing_principal exists, or a mandate.json entry does. */
  referenced: boolean;
  /** A signed mandate is claimed: a digest reference or packaged bytes. */
  claimed: boolean;
  /** The mandate.json entry itself is present in the package. */
  present: boolean;
  /** Parsed mandate record, when parseable. */
  record: MandateRecord | null;
  /** First inconsistency; non-null makes the verifier reject. */
  error: string | null;
  /** Which sub-check the inconsistency belongs to. */
  errorCheck: MandateErrorCheck | null;
  /** authorizing_principal.mandate_digest matches SHA-256 of the packaged bytes. */
  digestOk: boolean | null;
  /**
   * The digest reference sits under signature.sig (profile canonical
   * form) and the record's principal / mandate_id / subject agree with
   * the signed metadata block.
   */
  bound: boolean | null;
  /** mandate.sig verifies over JCS(mandate.json) against the record's public_key. */
  signatureVerified: boolean | null;
  /**
   * metadata action_type and policy_id fall inside scope. null when
   * either metadata field is absent (not determinable).
   */
  inScope: boolean | null;
  /** Parsed validity window, for the genTime containment check. */
  validFrom: Date | null;
  validUntil: Date | null;
};

function absent(): MandateValidation {
  return {
    referenced: false,
    claimed: false,
    present: false,
    record: null,
    error: null,
    errorCheck: null,
    digestOk: null,
    bound: null,
    signatureVerified: null,
    inScope: null,
    validFrom: null,
    validUntil: null,
  };
}

function failAt(
  base: MandateValidation,
  errorCheck: MandateErrorCheck,
  error: string,
): MandateValidation {
  return { ...base, error, errorCheck };
}

export async function parseAndCheckMandate(
  entries: Record<string, Uint8Array>,
  metadata: Record<string, unknown>,
  canonicalForm: CanonicalForm,
): Promise<MandateValidation> {
  const principalBlock = metadata["authorizing_principal"];
  const bytes = entries["mandate.json"];
  const sigBytes = entries["mandate.sig"];
  const present = bytes !== undefined && bytes.length > 0;
  const block = isRecord(principalBlock) ? principalBlock : null;
  if (block === null && !present) {
    return absent();
  }

  const digestField = block !== null ? textAt(block, "mandate_digest") : null;
  const out: MandateValidation = {
    ...absent(),
    referenced: true,
    claimed: present || digestField !== null,
    present,
  };

  // A principal named without a signed mandate stays legal: the block is
  // the pre-§4.5 reference form. Nothing is verified and nothing is
  // claimed — every check reports not_determinate upstream.
  if (!out.claimed) {
    return out;
  }

  // --- mandate-digest ---------------------------------------------------
  if (!present) {
    out.digestOk = false;
    return failAt(out, "mandate-digest", "mandate.json entry is missing but metadata references a mandate");
  }
  if (digestField === null) {
    out.digestOk = false;
    return failAt(
      out,
      "mandate-digest",
      "mandate.json is packaged but metadata.authorizing_principal.mandate_digest is missing",
    );
  }
  const actualDigest = "sha256:" + toHex(await sha256(bytes!));
  if (actualDigest !== digestField.trim().toLowerCase()) {
    out.digestOk = false;
    return failAt(out, "mandate-digest", "digest does not match authorizing_principal.mandate_digest");
  }
  out.digestOk = true;

  // --- mandate-parse ----------------------------------------------------
  let record: MandateRecord;
  try {
    const parsed = JSON.parse(TEXT_DEC.decode(bytes)) as unknown;
    if (!isRecord(parsed)) {
      return failAt(out, "mandate-parse", "record must be a JSON object");
    }
    record = parsed;
  } catch {
    return failAt(out, "mandate-parse", "record is not valid JSON");
  }
  out.record = record;
  if (!bytesEqual(jcs(record), bytes!)) {
    return failAt(out, "mandate-parse", "record bytes are not in JCS canonical form");
  }
  const shapeError = validateShape(record);
  if (shapeError) {
    return failAt(out, "mandate-parse", shapeError);
  }
  out.validFrom = new Date(textAt(record, "valid_from")!);
  out.validUntil = new Date(textAt(record, "valid_until")!);
  if (Number.isNaN(out.validFrom.getTime()) || Number.isNaN(out.validUntil.getTime())) {
    out.validFrom = null;
    out.validUntil = null;
    return failAt(out, "mandate-parse", "valid_from/valid_until must be RFC 3339 timestamps");
  }

  // --- mandate-bound ----------------------------------------------------
  // The digest reference must lie inside the bytes signature.sig covers,
  // and the record must be the one the signed metadata names. Under the
  // response-only form metadata.authorizing_principal — mandate_digest
  // included — is rewritable, so a mandate carried there is bound to
  // nothing. §4.5 rejects that rather than reporting it.
  if (canonicalForm !== "profile") {
    out.bound = false;
    return failAt(
      out,
      "mandate-bound",
      "the response-only canonical form leaves authorizing_principal.mandate_digest outside signature.sig",
    );
  }
  const crossFieldError =
    crossField(record, "mandate_id", block!, "mandate_ref") ??
    crossField(record, "principal", block!, "principal") ??
    crossField(record, "subject", metadata, "agent_id");
  if (crossFieldError) {
    out.bound = false;
    return failAt(out, "mandate-bound", crossFieldError);
  }
  out.bound = true;

  // --- mandate-signature ------------------------------------------------
  if (sigBytes === undefined || sigBytes.length === 0) {
    out.signatureVerified = false;
    return failAt(out, "mandate-signature", "mandate.sig entry is missing");
  }
  const pem = textAt(record, "public_key");
  const sigB64 = TEXT_DEC.decode(sigBytes).trim();
  if (pem === null || sigB64 === "") {
    out.signatureVerified = false;
    return failAt(out, "mandate-signature", "mandate.public_key or mandate.sig is empty");
  }
  try {
    const key = await importRsaPublicKey(pem);
    out.signatureVerified = await verifyRsa(key, decodeBase64(sigB64), jcs(record));
  } catch {
    out.signatureVerified = false;
    return failAt(out, "mandate-signature", "mandate.public_key or mandate.sig could not be parsed");
  }
  if (!out.signatureVerified) {
    return failAt(out, "mandate-signature", "mandate.sig does not verify against the mandate's public_key");
  }

  // --- mandate-scope ----------------------------------------------------
  // Appraisal, never a rejection.
  const actionType = textAt(metadata, "action_type");
  const policyId = textAt(metadata, "policy_id");
  if (actionType === null || policyId === null) {
    out.inScope = null;
  } else {
    const actionTypes = valueAt(record, ["scope", "action_types"]) as string[];
    const policyIds = valueAt(record, ["scope", "policy_ids"]) as string[];
    out.inScope = actionTypes.includes(actionType) && policyIds.includes(policyId);
  }

  return out;
}

/** Required-shape validation per schemas/mandate-v1.schema.json. */
function validateShape(record: MandateRecord): string | null {
  for (const field of [
    "mandate_id",
    "mandate_version",
    "principal",
    "subject",
    "granted_at",
    "statement",
    "valid_from",
    "valid_until",
    "public_key",
  ]) {
    if (textAt(record, field) === null) {
      return `${field} is required`;
    }
  }
  for (const key of ["action_types", "policy_ids"]) {
    const list = valueAt(record, ["scope", key]);
    if (!Array.isArray(list) || list.length === 0 || list.some((v) => typeof v !== "string" || v.trim() === "")) {
      return `scope.${key} must be a non-empty array of strings`;
    }
  }
  return null;
}

function crossField(
  record: MandateRecord,
  recordKey: string,
  other: Record<string, unknown>,
  otherKey: string,
): string | null {
  const a = textAt(record, recordKey);
  const b = textAt(other, otherKey);
  if (b === null) {
    return `${otherKey} is missing but a signed mandate is claimed`;
  }
  if (a !== b) {
    return `mandate ${recordKey} does not match ${otherKey}`;
  }
  return null;
}

function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}
