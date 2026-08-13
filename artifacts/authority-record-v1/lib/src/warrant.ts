/**
 * Optional warrant.json parse-and-cross-check, on the overt.ts pattern
 * (docs/specs/aep-profile-v1.md §4.2, schemas/warrant-v1.schema.json).
 *
 * A warrant is a once-authored, versioned record stating that outputs
 * a named policy evaluates to a listed decision are licensed for a
 * listed action class, carried as JCS-canonical bytes and bound by
 * digest from metadata.json. Its acceptance block names the principal
 * that accepted the warrant, with a signature over the JCS bytes of
 * the warrant minus the signature itself.
 *
 * Binding verification and authorization appraisal are SEPARATE
 * verifier decisions. Binding-family inconsistencies (digest, record
 * shape, policy linkage, acceptance signature) make a warrant-aware
 * verifier reject the package, exactly as an inconsistent OVERT
 * receipt does. Appraisal outcomes (applicability, freshness) are
 * reported and never reject: an output whose warrant does not apply
 * may inform but carries no warrant to compel.
 *
 * The accepting authority is a named principal with a verifiable key
 * binding — the same self-attestation trust model as public_key.pem.
 * Nothing here establishes it as a legally constituted authority, and
 * the soundness of the licensed inference is attested, never
 * machine-checked. void_if entries are shape-validated (the
 * machine/attested partition stays explicit) but their predicates are
 * not evaluated in this release.
 */

import { jcs } from "./canonical.js";
import { sha256, toHex } from "./hash.js";
import { decodeBase64, importRsaPublicKey, verifyRsa } from "./rsa.js";
import { isRecord, textAt, valueAt } from "./overt.js";

const TEXT_DEC = new TextDecoder();

export type WarrantRecord = Record<string, unknown>;

/** The warrant sub-check an inconsistency belongs to (registry check id). */
export type WarrantErrorCheck =
  | "warrant-digest"
  | "warrant-parse"
  | "warrant-policy-link"
  | "warrant-acceptance-signature";

export type WarrantValidation = {
  /** A warrant.json entry (or a metadata reference to one) exists. */
  referenced: boolean;
  /** The warrant.json entry itself is present in the package. */
  present: boolean;
  /** Parsed warrant record, when parseable. */
  record: WarrantRecord | null;
  /** First inconsistency; non-null makes a warrant-aware verifier reject. */
  error: string | null;
  /** Which sub-check the inconsistency belongs to. */
  errorCheck: WarrantErrorCheck | null;
  /** metadata.warrant_digest matches SHA-256 of the packaged bytes. */
  digestOk: boolean | null;
  /** Digest reference sits under the signature (profile canonical form). */
  bound: boolean | null;
  /** policy_ref and the metadata warrant_id/warrant_version echoes match. */
  policyLinked: boolean | null;
  /**
   * metadata action_type and policy_decision fall inside applies_to.
   * null when either metadata field is absent (not determinable).
   */
  applicable: boolean | null;
  /** acceptance.signature verifies over JCS(warrant minus signature). */
  acceptanceVerified: boolean | null;
  /** Parsed validity window, for the genTime freshness check. */
  validFrom: Date | null;
  validUntil: Date | null;
};

function absent(): WarrantValidation {
  return {
    referenced: false,
    present: false,
    record: null,
    error: null,
    errorCheck: null,
    digestOk: null,
    bound: null,
    policyLinked: null,
    applicable: null,
    acceptanceVerified: null,
    validFrom: null,
    validUntil: null,
  };
}

function failAt(
  base: WarrantValidation,
  errorCheck: WarrantErrorCheck,
  error: string,
): WarrantValidation {
  return { ...base, error, errorCheck };
}

export async function parseAndCheckWarrant(
  entries: Record<string, Uint8Array>,
  metadata: Record<string, unknown>,
  canonicalForm: "profile" | "response-only",
): Promise<WarrantValidation> {
  const bytes = entries["warrant.json"];
  const digestField = typeof metadata["warrant_digest"] === "string"
    ? (metadata["warrant_digest"] as string).trim().toLowerCase()
    : null;
  const referenced =
    (bytes !== undefined && bytes.length > 0) ||
    digestField !== null ||
    typeof metadata["warrant_id"] === "string" ||
    typeof metadata["warrant_version"] === "string";
  if (!referenced) {
    return absent();
  }

  const out: WarrantValidation = {
    ...absent(),
    referenced: true,
    present: bytes !== undefined && bytes.length > 0,
  };

  // Binding: the digest reference and the packaged bytes must exist
  // together and agree.
  if (!out.present) {
    out.digestOk = false;
    return failAt(out, "warrant-digest", "warrant.json entry is missing but metadata references a warrant");
  }
  if (digestField === null) {
    out.digestOk = false;
    return failAt(out, "warrant-digest", "metadata.warrant_digest is missing");
  }
  const actualDigest = toHex(await sha256(bytes!));
  if (actualDigest !== digestField) {
    out.digestOk = false;
    return failAt(out, "warrant-digest", "digest does not match metadata.warrant_digest");
  }
  out.digestOk = true;

  // Record: valid JSON, JCS-canonical bytes, required shape.
  let record: WarrantRecord;
  try {
    const parsed = JSON.parse(TEXT_DEC.decode(bytes)) as unknown;
    if (!isRecord(parsed)) {
      return failAt(out, "warrant-parse", "record must be a JSON object");
    }
    record = parsed;
  } catch {
    return failAt(out, "warrant-parse", "record is not valid JSON");
  }
  out.record = record;
  const canonicalBytes = jcs(record);
  if (!bytesEqual(canonicalBytes, bytes!)) {
    return failAt(out, "warrant-parse", "record bytes are not in JCS canonical form");
  }
  const shapeError = validateShape(record);
  if (shapeError) {
    return failAt(out, "warrant-parse", shapeError);
  }
  out.validFrom = new Date(textAt(record, "valid_from")!);
  out.validUntil = new Date(textAt(record, "valid_until")!);
  if (Number.isNaN(out.validFrom.getTime()) || Number.isNaN(out.validUntil.getTime())) {
    out.validFrom = null;
    out.validUntil = null;
    return failAt(out, "warrant-parse", "valid_from/valid_until must be RFC 3339 timestamps");
  }

  // Binding form: the digest reference lies inside the signed canonical
  // bytes only under the profile form. Response-only packages stay
  // accepted; the unbound state is reported, not rejected.
  out.bound = canonicalForm === "profile";

  // Linkage: the warrant is written against THIS package's policy.
  const linkageError =
    compareToMetadata(record, ["policy_ref", "policy_id"], metadata, "policy_id", true) ??
    compareToMetadata(record, ["policy_ref", "policy_version"], metadata, "policy_version", true) ??
    compareToMetadata(record, ["warrant_id"], metadata, "warrant_id", false) ??
    compareToMetadata(record, ["warrant_version"], metadata, "warrant_version", false);
  if (linkageError) {
    out.policyLinked = false;
    return failAt(out, "warrant-policy-link", linkageError);
  }
  out.policyLinked = true;

  // Applicability: appraisal, never a rejection.
  const actionType = textAt(metadata, "action_type");
  const decision = textAt(metadata, "policy_decision");
  if (actionType === null || decision === null) {
    out.applicable = null;
  } else {
    const actionTypes = valueAt(record, ["applies_to", "action_types"]) as string[];
    const decisions = valueAt(record, ["applies_to", "policy_decisions"]) as string[];
    out.applicable = actionTypes.includes(actionType) && decisions.includes(decision);
  }

  // Acceptance: the named principal's signature over the JCS bytes of
  // the warrant with acceptance.signature removed. Produced by our own
  // tooling, so no DigestInfo fallback is needed here.
  const acceptance = record["acceptance"];
  if (!isRecord(acceptance)) {
    out.acceptanceVerified = false;
    return failAt(out, "warrant-acceptance-signature", "acceptance block is missing");
  }
  for (const field of ["authority_id", "accepted_at", "signature", "public_key"]) {
    if (textAt(acceptance, field) === null) {
      out.acceptanceVerified = false;
      return failAt(out, "warrant-acceptance-signature", `acceptance.${field} is required`);
    }
  }
  const unsigned: WarrantRecord = { ...record, acceptance: { ...acceptance } };
  delete (unsigned["acceptance"] as Record<string, unknown>)["signature"];
  try {
    const key = await importRsaPublicKey(acceptance["public_key"] as string);
    const sig = decodeBase64((acceptance["signature"] as string).trim());
    out.acceptanceVerified = await verifyRsa(key, sig, jcs(unsigned));
  } catch {
    out.acceptanceVerified = false;
    return failAt(out, "warrant-acceptance-signature", "acceptance.public_key or acceptance.signature could not be parsed");
  }
  if (!out.acceptanceVerified) {
    return failAt(out, "warrant-acceptance-signature", "acceptance.signature does not verify against acceptance.public_key");
  }

  return out;
}

/** Required-shape validation per schemas/warrant-v1.schema.json. */
function validateShape(record: WarrantRecord): string | null {
  for (const field of ["warrant_id", "warrant_version", "inference_form", "statement", "valid_from", "valid_until"]) {
    if (textAt(record, field) === null) {
      return `${field} is required`;
    }
  }
  if (textAt(record, "policy_ref", "policy_id") === null || textAt(record, "policy_ref", "policy_version") === null) {
    return "policy_ref must carry policy_id and policy_version";
  }
  for (const key of ["action_types", "policy_decisions"]) {
    const list = valueAt(record, ["applies_to", key]);
    if (!Array.isArray(list) || list.length === 0 || list.some((v) => typeof v !== "string" || v.trim() === "")) {
      return `applies_to.${key} must be a non-empty array of strings`;
    }
  }
  const voidIf = record["void_if"];
  if (voidIf !== undefined) {
    if (!Array.isArray(voidIf)) {
      return "void_if must be an array";
    }
    for (const entry of voidIf) {
      if (!isRecord(entry)) {
        return "void_if entries must be objects";
      }
      const kind = textAt(entry, "kind");
      if (kind === "machine") {
        if (textAt(entry, "predicate") === null) return "void_if machine entries require a predicate";
      } else if (kind === "attested") {
        if (textAt(entry, "text") === null) return "void_if attested entries require a text";
      } else {
        return "void_if entries must be kind machine or attested";
      }
    }
  }
  return null;
}

function compareToMetadata(
  record: WarrantRecord,
  recordPath: string[],
  metadata: Record<string, unknown>,
  metadataKey: string,
  metadataRequired: boolean,
): string | null {
  const metadataValue = textAt(metadata, metadataKey);
  if (metadataValue === null) {
    return metadataRequired
      ? `metadata.${metadataKey} is missing but the warrant references a policy`
      : null;
  }
  if (textAt(record, ...recordPath) !== metadataValue) {
    return `${recordPath.join(".")} does not match metadata.${metadataKey}`;
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
