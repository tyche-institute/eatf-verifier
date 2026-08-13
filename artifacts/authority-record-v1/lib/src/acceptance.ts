/**
 * Optional per-output epistemic accepting authority
 * (docs/specs/aep-profile-v1.md §4.3), on the overt.ts / warrant.ts
 * parse-and-cross-check pattern.
 *
 * `metadata.accepting_authority` names the principal that accepted, once,
 * that outputs under this policy version license their action class. This is
 * the EPISTEMIC layer — deliberately distinct from the DEONTIC authorizing
 * principal (who granted the mandate to act). An optional detached
 * acceptance.json / acceptance.sig pair carries the accepting authority's
 * signed acceptance record, bound to the package by
 * `accepting_authority.acceptance_digest`.
 *
 * Every outcome is reported SEPARATELY — key binding and role are distinct
 * verifier decisions, and binding verification is separate from
 * authorization appraisal:
 *
 *   keyBindingValid     acceptance.sig verifies over JCS(acceptance.json)
 *                       against the record's embedded public_key.
 *   boundToOutput       the acceptance is cryptographically bound to THIS
 *                       output: the block is under the signature (profile
 *                       form) and, when a detached record is packaged, its
 *                       digest and principal/policy fields agree. False
 *                       under the response-only form — the whole block is
 *                       unsigned and rewritable (the overclaim guard).
 *   temporalContainment the RFC 3161 genTime is inside the acceptance
 *                       validity window.
 *   roleVerified        attested-only (null) unless the caller supplies an
 *                       authorityTrustList; the exact mirror of the TSA
 *                       trust-list tri-state.
 *
 * The accepting authority is a named principal with a verifiable key binding
 * under the same self-attestation trust model as public_key.pem; nothing
 * here establishes it as a legally constituted authority.
 *
 * Two of the four GATE, on the §4.5 mandate rule and for the same reason.
 * §4.3 is surface added in this work: it has never shipped in a release, so
 * it carries no compatibility debt, and an acceptance that cannot be shown
 * to belong to these bytes must not be reported beside a `valid: true`
 * verdict.
 *
 *   accepting-authority-binding      GATES. A stripped, re-pointed,
 *                                    cross-field-substituted or
 *                                    response-only-carried acceptance is
 *                                    bound to nothing, and the package is
 *                                    REJECTED rather than reported.
 *   accepting-authority-key-binding  GATES. A packaged acceptance whose
 *                                    detached signature does not verify
 *                                    against its own embedded key is forged,
 *                                    and the package is REJECTED.
 *   accepting-authority-temporal     APPRAISAL, never rejecting — the mirror
 *                                    of `mandate-temporal` and
 *                                    `warrant-freshness`. An expired
 *                                    acceptance is authentic and bound; what
 *                                    lapsed is its licence, and the genTime
 *                                    it is judged against is only as good as
 *                                    a TSA trust anchor the package cannot
 *                                    supply.
 *   accepting-authority-role         APPRAISAL, never rejecting: undecidable
 *                                    from the package alone. Without a
 *                                    caller-supplied authorityTrustList
 *                                    there is nothing to decide membership
 *                                    against, and role stays attested-only.
 *
 * A tri-state that is `null` — the property was not determinable on this
 * input — never gates: an absent acceptance and a bare inline claim are both
 * legal, and neither is a failure.
 */

import { jcs } from "./canonical.js";
import { sha256, toHex } from "./hash.js";
import { decodeBase64, importRsaPublicKey, verifyRsa } from "./rsa.js";
import { isRecord, textAt } from "./overt.js";
import type { CanonicalForm } from "./index.js";

const TEXT_DEC = new TextDecoder();

/** The §4.3 sub-check a gating inconsistency belongs to (registry check id). */
export type AcceptanceErrorCheck =
  | "accepting-authority-binding"
  | "accepting-authority-key-binding";

export type AcceptanceValidation = {
  /** metadata.accepting_authority is present. */
  referenced: boolean;
  /** A detached acceptance.json entry is present in the package. */
  present: boolean;
  /** Parsed acceptance record, when a detached acceptance.json parses. */
  record: Record<string, unknown> | null;
  keyBindingValid: boolean | null;
  boundToOutput: boolean | null;
  temporalContainment: boolean | null;
  roleVerified: boolean | null;
  /** First gating inconsistency; non-null makes the verifier reject. */
  error: string | null;
  /** Which of the two gating sub-checks the inconsistency belongs to. */
  errorCheck: AcceptanceErrorCheck | null;
};

function none(): AcceptanceValidation {
  return {
    referenced: false,
    present: false,
    record: null,
    keyBindingValid: null,
    boundToOutput: null,
    temporalContainment: null,
    roleVerified: null,
    error: null,
    errorCheck: null,
  };
}

export async function parseAndCheckAcceptance(
  entries: Record<string, Uint8Array>,
  metadata: Record<string, unknown>,
  canonicalForm: CanonicalForm,
  genTime: Date | null,
  authorityTrustList: string[] | undefined,
): Promise<AcceptanceValidation> {
  const authority = metadata["accepting_authority"];
  if (!isRecord(authority)) {
    return none();
  }

  const out: AcceptanceValidation = { ...none(), referenced: true };

  const bytes = entries["acceptance.json"];
  const sigBytes = entries["acceptance.sig"];
  out.present = bytes !== undefined && bytes.length > 0;

  // Parse the detached record, when present.
  let record: Record<string, unknown> | null = null;
  if (out.present) {
    try {
      const parsed = JSON.parse(TEXT_DEC.decode(bytes)) as unknown;
      if (isRecord(parsed)) {
        record = parsed;
      }
    } catch {
      record = null;
    }
    out.record = record;
  }

  // --- key binding: acceptance.sig over JCS(acceptance.json) -----------
  // Reported separately from role. Only meaningful with a detached record.
  let keyBindingError: string | null = null;
  if (out.present) {
    if (record === null) {
      out.keyBindingValid = false;
      keyBindingError = "acceptance.json is not valid JSON";
    } else if (sigBytes === undefined || sigBytes.length === 0) {
      out.keyBindingValid = false;
      keyBindingError = "acceptance.sig entry is missing";
    } else {
      const pem = textAt(record, "public_key");
      const sigB64 = TEXT_DEC.decode(sigBytes).trim();
      if (pem === null || sigB64 === "") {
        out.keyBindingValid = false;
        keyBindingError = "acceptance.public_key or acceptance.sig is empty";
      } else {
        try {
          const key = await importRsaPublicKey(pem);
          out.keyBindingValid = await verifyRsa(key, decodeBase64(sigB64), jcs(record));
          if (!out.keyBindingValid) {
            keyBindingError =
              "acceptance.sig does not verify against the acceptance's public_key";
          }
        } catch {
          out.keyBindingValid = false;
          keyBindingError = "acceptance.public_key or acceptance.sig could not be parsed";
        }
      }
    }
  }

  // --- boundToOutput: bound to THIS output ------------------------------
  // Requires the profile canonical form (metadata under the signature). The
  // response-only form leaves the whole accepting_authority block unsigned
  // and rewritable — the overclaim guard.
  const digestField = textAt(authority, "acceptance_digest");
  let bindingError: string | null = null;
  if (canonicalForm !== "profile") {
    out.boundToOutput = false;
    bindingError =
      "the response-only canonical form leaves metadata.accepting_authority outside signature.sig";
  } else if (out.present) {
    if (record === null) {
      out.boundToOutput = false;
      bindingError = "acceptance.json is not a JSON object";
    } else {
      const actualDigest = "sha256:" + toHex(await sha256(jcs(record)));
      const digestOk = digestField !== null && actualDigest === digestField.trim().toLowerCase();
      const mismatchedField = digestOk
        ? (["principal", "policy_id", "policy_version"] as const).find(
            (key) => !crossFieldOk(record!, authority, key),
          ) ?? null
        : null;
      out.boundToOutput = digestOk && mismatchedField === null;
      if (!digestOk) {
        bindingError =
          digestField === null
            ? "acceptance.json is packaged but metadata.accepting_authority.acceptance_digest is missing"
            : "digest does not match accepting_authority.acceptance_digest";
      } else if (mismatchedField !== null) {
        bindingError = `acceptance ${mismatchedField} does not match accepting_authority.${mismatchedField}`;
      }
    }
  } else {
    // Profile form, inline claim only: a dangling digest reference (a digest
    // named but no packaged record) is unbound; a bare signed claim is bound.
    out.boundToOutput = digestField === null;
    if (!out.boundToOutput) {
      bindingError =
        "acceptance.json entry is missing but metadata references an acceptance_digest";
    }
  }

  // --- temporalContainment: genTime inside the validity window ----------
  const validity = authority["validity"];
  if (isRecord(validity) && genTime !== null) {
    const notBeforeText = textAt(validity, "not_before");
    const notAfterText = textAt(validity, "not_after");
    if (notBeforeText !== null && notAfterText !== null) {
      const notBefore = new Date(notBeforeText);
      const notAfter = new Date(notAfterText);
      if (!Number.isNaN(notBefore.getTime()) && !Number.isNaN(notAfter.getTime())) {
        out.temporalContainment =
          genTime.getTime() >= notBefore.getTime() && genTime.getTime() <= notAfter.getTime();
      }
    }
  }

  // --- roleVerified: attested-only unless a trust list is supplied ------
  // Reported SEPARATELY from key binding.
  if (authorityTrustList && authorityTrustList.length > 0) {
    const pem = record !== null ? textAt(record, "public_key") : null;
    if (pem === null) {
      out.roleVerified = false;
    } else {
      const normalized = normalizePem(pem);
      out.roleVerified = authorityTrustList.some((t) => normalizePem(t) === normalized);
    }
  }

  // --- the gate ---------------------------------------------------------
  // Every outcome above is computed and reported first: the boundary report
  // carries all four verdicts whether or not the package is rejected, so a
  // reader sees WHY it was rejected and what else held. Only then do the two
  // binding-family checks decide the verdict, in registry order. Temporal
  // containment and role never reach here.
  if (out.boundToOutput === false) {
    out.error = bindingError ?? "the acceptance is not bound to this output";
    out.errorCheck = "accepting-authority-binding";
  } else if (out.keyBindingValid === false) {
    out.error = keyBindingError ?? "the acceptance signature does not verify";
    out.errorCheck = "accepting-authority-key-binding";
  }

  return out;
}

function crossFieldOk(
  record: Record<string, unknown>,
  authority: Record<string, unknown>,
  key: string,
): boolean {
  const a = textAt(record, key);
  const b = textAt(authority, key);
  return a !== null && b !== null && a === b;
}

/** Collapse PEM whitespace so trust-list membership is not defeated by newlines. */
function normalizePem(pem: string): string {
  return pem.replace(/\s+/g, "");
}
