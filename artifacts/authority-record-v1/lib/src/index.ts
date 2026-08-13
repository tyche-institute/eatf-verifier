/**
 * Offline TypeScript verifier for EATF .aep evidence packages.
 *
 * Runs in the browser via Web Crypto and in Node 20+ without any
 * backend round-trip. Implements the AEP wire-format profile.
 *
 * Public API:
 *
 *   import { verify } from "@eatf/verifier";
 *   const result = await verify(file);                   // Blob | Uint8Array
 *   if (result.valid) console.log("ok", result.report);
 *   else console.warn("fail", result.failureReason);
 *
 * The browser bundle at `@eatf/verifier/browser` re-exports the same
 * symbols with a Web-Crypto-only path (no Node polyfills).
 */

import type { CheckId } from "./check-registry.js";

/**
 * Which supported canonical form the package's `canonical.bin` matched.
 *
 * - `"profile"`: the AEP profile form (`response.txt` + LF +
 *   JCS(`metadata.json`), spec §6). The signature and timestamp cover
 *   the metadata.
 * - `"response-only"`: the legacy Java form (`canonical.bin` equals
 *   `response.txt` verbatim). Accepted for compatibility, but the
 *   whole of `metadata.json` lies OUTSIDE `signature.sig`,
 *   `hash.sha256`, and the RFC 3161 timestamp — callers that rely on
 *   signed metadata must check for `"profile"` here.
 */
export type CanonicalForm = "profile" | "response-only";

/**
 * Per-check verdict vocabulary.
 *
 * - `"pass"` / `"fail"`: the check executed and reached an outcome.
 * - `"not_assessed"`: the check never executed in this run (the reason
 *   code says why — short-circuited by an earlier failure, input
 *   absent, option disabled).
 * - `"not_determinate"`: the check executed but could not reach an
 *   outcome (e.g. the TSA token carries no embedded certificate, so
 *   the SignerInfo signature can be neither confirmed nor refuted).
 */
export type CheckVerdict = "pass" | "fail" | "not_assessed" | "not_determinate";

/** Machine reason code for a non-pass/fail verdict, where applicable. */
export type CheckReason =
  | "input_absent"
  | "capability_absent"
  | "option_disabled"
  | "parse_failure"
  | "short_circuited";

export type BoundaryCheck = {
  id: CheckId;
  /** The aep-profile-v1.md clause this check executes (from the registry). */
  clause: string;
  verdict: CheckVerdict;
  /**
   * Whether this check's outcome counted toward `valid` in THIS run:
   * `true` for gating checks that executed; `false` for advisory
   * checks (executed, but a failure is reported without failing the
   * package) and for checks that never executed.
   */
  enforced: boolean;
  reason?: CheckReason;
};

/**
 * The verifier's own account of what it did and did not assess,
 * computed from control flow — never from anything the package claims
 * about itself. One entry per CHECK_REGISTRY check, in registry order,
 * on every result (success or failure).
 */
export type BoundaryReport = {
  /** CHECK_REGISTRY_VERSION the report was computed against. */
  registryVersion: string;
  /** SHA-256 hex content digest of the registry (checkRegistryDigest()). */
  registryDigest: string;
  checks: BoundaryCheck[];
  /** Mirrors VerifyResult.canonicalForm; see {@link CanonicalForm}. */
  canonicalForm: CanonicalForm | null;
  /**
   * Top-level metadata.json fields that lie OUTSIDE `signature.sig`,
   * `hash.sha256`, and the RFC 3161 imprint under the matched
   * canonical form, as `"metadata.<field>"`. Empty under the profile
   * form and when verification failed before the canonical-form check.
   * (`overt_receipt.json` is outside the signature in BOTH forms and
   * is cross-checked via its `content_hash` only.)
   */
  unsignedFields: string[];
  /**
   * Producer-claimed assessment surface, when metadata.json carries a
   * `claimed_assessment_surface` string array (experimental; not yet
   * part of the spec's §5 field table). `claimed` echoes the sorted
   * claim; `unrecognized` lists claimed ids absent from the registry;
   * `notAssessed` lists claimed registry checks this run did NOT
   * bring to a pass/fail outcome — a non-empty value is a
   * claimed-vs-computed overclaim. `null` when the field is absent.
   */
  claimedSurface: {
    claimed: string[];
    unrecognized: string[];
    notAssessed: string[];
  } | null;
};

/**
 * Warrant cross-check outcome for the optional warrant.json entry
 * (aep-profile-v1.md §4.2). Binding verification and authorization
 * appraisal are separate verifier decisions: an inconsistent warrant
 * (digest, record shape, policy linkage, acceptance signature) fails
 * verification like an inconsistent OVERT-inspired receipt, while applicability
 * and freshness are appraisal outcomes that are reported and never
 * reject — an output whose warrant does not apply may inform but
 * carries no warrant to compel.
 */
export type WarrantResult = {
  /** A warrant.json entry exists in the package. */
  present: boolean;
  /**
   * The warrant digest reference sits under `signature.sig`: `true`
   * only when the digest matched AND the package uses the profile
   * canonical form. Always `false` under `"response-only"`, where
   * `metadata.warrant_digest` itself is rewritable; `null` when the
   * check was not reached.
   */
  bound: boolean | null;
  /** policy_ref matches the metadata policy fields (and the warrant_id/warrant_version echoes). */
  policyLinked: boolean | null;
  /**
   * metadata `action_type` and `policy_decision` fall inside the
   * warrant's `applies_to` lists. `null` when either metadata field is
   * absent or the check was not reached.
   */
  applicable: boolean | null;
  /** acceptance.signature verifies over JCS(warrant minus signature) against acceptance.public_key. */
  acceptanceVerified: boolean | null;
  /**
   * RFC 3161 genTime inside valid_from..valid_until, under a TSA that
   * chains to a trusted root. Never `true` while `tsaTrusted` is not
   * `true`; `false` when even the claimed genTime lies outside the
   * window; `null` when not determinable or not reached.
   */
  fresh: boolean | null;
};

/**
 * Four-valued verdict for one typed voiding predicate
 * (docs/specs/aep-profile-v1.md §4.4).
 *
 * - `"holds"`: the voiding condition did NOT fire — the output still holds.
 * - `"voided"`: the voiding condition fired — the output is voided/degraded.
 * - `"unknown"`: the predicate is a known type but could not be evaluated
 *   (its caller-supplied input is absent, or a required fact is missing).
 * - `"not-assessed"`: the predicate type is unknown to this verifier, or is
 *   an attested-only predicate. An unknown type NEVER defaults to `"holds"`.
 */
export type VoidingVerdictValue = "holds" | "voided" | "unknown" | "not-assessed";

/**
 * The evaluated verdict for one metadata.voiding entry.
 *
 * For `registry-status` predicates the evaluation is DUAL-TIME: the same
 * caller-supplied dated registry snapshot is evaluated twice — once at the
 * package's RFC 3161 genTime (`atSigning`) and once at the snapshot's
 * caller-supplied evaluation instant (`now`). The pair is surfaced and is
 * NEVER collapsed to one boolean; `verdict` echoes the `now` evaluation as
 * the operative current-time answer while both members stay visible. This
 * imports the dual-time temporal-validation pattern of AdES signature
 * validation (ETSI EN 319 102-1) and eIDAS status determination
 * (ETSI TS 119 615) with the polarity inverted — the divergence between the
 * two evaluations is the reportable object, not a rescue path.
 */
export type VoidingVerdict = {
  id: string;
  /** The predicate type as declared in metadata (may be an unknown type). */
  type: string;
  verdict: VoidingVerdictValue;
  /** Dual-time only: the verdict evaluated at the RFC 3161 genTime. */
  atSigning?: VoidingVerdictValue;
  /** Dual-time only: the verdict evaluated at the caller-supplied snapshot instant. */
  now?: VoidingVerdictValue;
  /** Machine reason for an unknown / not-assessed verdict, where applicable. */
  reason?: string;
};

/**
 * Accepting-authority cross-check outcome for the optional per-output
 * epistemic accepting authority (docs/specs/aep-profile-v1.md §4.3). Every
 * field is reported SEPARATELY: key binding and role are distinct verifier
 * decisions, and binding verification is separate from authorization
 * appraisal. `boundToOutput` and `keyBindingValid` GATE: a `false` on
 * either makes verify() return `valid: false`. `temporalContainment` and
 * `roleVerified` are appraisal and never reject — the licence lapsing is
 * not the binding breaking, and role is undecidable from the package
 * alone. A `null` (not determinable on this input) never gates.
 */
export type AcceptingAuthorityResult = {
  /**
   * A detached acceptance.json's acceptance.sig verifies (PKCS#1 v1.5 RSA,
   * SHA-256) over its JCS bytes against its embedded public_key. `null` when
   * no detached acceptance.json is packaged (nothing to verify).
   */
  keyBindingValid: boolean | null;
  /**
   * The acceptance is cryptographically bound to THIS output: the
   * accepting_authority block sits under the signature (profile canonical
   * form) and, when a detached acceptance.json is packaged, its digest
   * matches metadata.accepting_authority.acceptance_digest and its
   * principal/policy fields agree. `false` under the response-only form
   * (the whole block is unsigned and rewritable — the overclaim guard).
   */
  boundToOutput: boolean | null;
  /**
   * The RFC 3161 genTime lies inside accepting_authority.validity
   * (not_before..not_after). `null` when the window or the genTime could
   * not be read.
   */
  temporalContainment: boolean | null;
  /**
   * The accepting authority's key is a member of a caller-supplied
   * authorityTrustList — reported SEPARATELY from key binding. Attested-only
   * (`null`) unless the caller supplies a trust list, mirroring the TSA
   * trust-list tri-state.
   */
  roleVerified: boolean | null;
};

/**
 * Detached deontic mandate outcome for the optional `mandate.json` /
 * `mandate.sig` pair (docs/specs/aep-profile-v1.md §4.5).
 *
 * This is the one authority layer whose binding family GATES: a claimed
 * mandate whose digest, record, binding to the protected bytes, or
 * signature does not hold makes verification fail, exactly as an
 * inconsistent OVERT-inspired receipt does. Scope and temporal containment are
 * appraisal outcomes — reported, never rejecting.
 *
 * `claimed` separates the two states a `metadata.authorizing_principal`
 * block can be in. A block that names a principal without carrying a
 * digest reference or packaged bytes claims no signed mandate: it is the
 * pre-§4.5 reference form, every check reports `not_determinate`, and
 * nothing about the deontic layer is verified.
 */
export type MandateResult = {
  /** A signed mandate is claimed: a digest reference, packaged bytes, or both. */
  claimed: boolean;
  /** A mandate.json entry exists in the package. */
  present: boolean;
  /**
   * The digest reference sits under `signature.sig` (profile canonical
   * form) and the record's principal / mandate_id / subject agree with
   * the signed metadata block. `false` under the response-only form,
   * where the reference is itself rewritable — and, unlike the §4.2
   * warrant and the §4.3 acceptance, that state is rejected rather than
   * reported.
   */
  bound: boolean | null;
  /** mandate.sig verifies (PKCS#1 v1.5 RSA, SHA-256) over JCS(mandate.json). */
  signatureVerified: boolean | null;
  /**
   * The attested `action_type` and `policy_id` fall inside the granted
   * `scope`. `null` when either metadata field is absent or the check
   * was not reached. An action outside the mandate may inform; it
   * carries no mandate to compel.
   */
  inScope: boolean | null;
  /**
   * The RFC 3161 genTime lies inside the mandate's
   * `valid_from`..`valid_until`. `null` when not determinable or not
   * reached.
   */
  temporalContainment: boolean | null;
  /** The granting authority named in the record, when one parsed. */
  principal: string | null;
};

export type VerifyResult = {
  valid: boolean;
  report: string[];
  failureReason: string | null;
  /**
   * The canonical form that `canonical.bin` matched, or `null` when
   * verification failed before the canonical-form check. See
   * {@link CanonicalForm} for what each value binds.
   */
  canonicalForm: CanonicalForm | null;
  /** Indicates the ML-DSA-65 PQC signature verification result when present. */
  pqcValid: boolean | null;
  /** Parsed metadata.json from the package, when readable. */
  metadata: Record<string, unknown> | null;
  /** Parsed and profile-checked overt_receipt.json, when the optional entry is present. */
  overtReceipt: Record<string, unknown> | null;
  /**
   * Warrant cross-check outcome, when the package carries (or its
   * metadata references) a warrant.json entry and verification reached
   * the warrant step. `null` for packages without a warrant and for
   * runs that failed earlier. See {@link WarrantResult}.
   */
  warrant: WarrantResult | null;
  /**
   * v0.1: trust-anchor cross-check result for the embedded
   * RFC 3161 TSA signing cert. `null` when the caller passed no
   * `tsaTrustList`, the TSA itself was absent, or the embedded cert
   * could not be parsed. Operators that need chain-to-root validation
   * inspect this field; in v0.2 it is informational and does not
   * fail `valid`.
   */
  tsaTrusted?: boolean | null;
  /**
   * Per-output voiding verdicts (docs/specs/aep-profile-v1.md §4.4), one
   * entry per metadata.voiding predicate, in declared order. `null` when the
   * package carries no voiding predicates or verification failed before the
   * voiding step. Informational in this release; a `"voided"` verdict does
   * not flip `valid`. See {@link VoidingVerdict}.
   */
  voidingVerdicts: VoidingVerdict[] | null;
  /**
   * Accepting-authority cross-check (docs/specs/aep-profile-v1.md §4.3),
   * when the package carries a metadata.accepting_authority block and
   * verification reached the accepting-authority step. `null` otherwise.
   * Carried onto a REJECTING result too, when the §4.3 gate is what
   * rejected: a rejection must not drop the evidence the run had in hand.
   * See {@link AcceptingAuthorityResult}.
   */
  acceptingAuthority: AcceptingAuthorityResult | null;
  /**
   * Detached deontic mandate cross-check (docs/specs/aep-profile-v1.md
   * §4.5), when the package carries a metadata.authorizing_principal
   * block or a mandate.json entry and verification reached the mandate
   * step. `null` otherwise. See {@link MandateResult}.
   */
  mandate: MandateResult | null;
  /**
   * Per-check assessment boundary for this run. Always present; see
   * {@link BoundaryReport} and lib/src/check-registry.ts. Serialised
   * form specified by schemas/boundary-report-v1.schema.json.
   */
  boundary: BoundaryReport;
};

export type VerifyOptions = {
  /**
   * If true, the verifier verifies only that the package is well-formed
   * (hash matches signature input, signature parses) without consulting
   * any external trust list. Default: true. v0.2 will add an optional
   * trust-list check against the public-key history mirror.
   */
  offlineOnly?: boolean;

  /**
   * Optional explicit list of trusted RSA public keys (PEM) for the
   * signer. If empty (default), the verifier extracts the public key
   * from the package itself.
   */
  trustedSignerPems?: string[];

  /**
   * v0.1: PEM-encoded root certificates pinned for RFC 3161
   * TSA chain-to-root validation. When empty (default), the verifier
   * skips chain validation and {@link VerifyResult.tsaTrusted} is set
   * to `null`. When non-empty, the verifier checks that the TSA
   * signing cert's issuer DN matches one of the supplied roots.
   *
   * For now, full RFC 5280 path validation (NotBefore / NotAfter /
   * KeyUsage / EKU / Basic Constraints / CRL / OCSP) is not performed
   * — that is v0.3 territory. The match is on issuer-DN against
   * pinned root subject-DN.
   */
  tsaTrustList?: string[];

  /**
   * Optional caller-supplied dated registry snapshot for evaluating
   * `registry-status` (and `mandate-revocation`) voiding predicates
   * (docs/specs/aep-profile-v1.md §4.4). `bytes` is a JSON registry
   * document; `date` is the caller-supplied evaluation instant ("now")
   * against which the snapshot is read for the current-time member of the
   * dual-time verdict pair. Never fetched over the network — verification
   * stays offline-deterministic, and every verdict is explicitly relative
   * to this named snapshot. When absent, registry-status predicates yield
   * `"unknown"`, never `"holds"`.
   */
  registrySnapshot?: { bytes: Uint8Array; date: string };

  /**
   * Optional caller-supplied list of superseded artifact identifiers for
   * evaluating `artifact-supersession` voiding predicates. When absent,
   * such predicates yield `"unknown"`, never `"holds"`.
   */
  supersessionList?: string[];

  /**
   * Optional caller-supplied list of trusted accepting-authority public
   * keys (PEM) for role verification of the epistemic accepting authority
   * (docs/specs/aep-profile-v1.md §4.3). Mirrors {@link tsaTrustList}: when
   * empty (default), role assertion is attested-only and
   * {@link AcceptingAuthorityResult.roleVerified} is `null`; when non-empty,
   * the verifier checks the accepting authority's key against the list and
   * reports the result SEPARATELY from key binding.
   */
  authorityTrustList?: string[];
};

export { verify } from "./verifier.js";
export { sign, type SignerInput, type SignerOutput } from "./signer.js";
export {
  CHECK_REGISTRY,
  CHECK_REGISTRY_VERSION,
  checkRegistryDigest,
  type CheckId,
  type CheckRegistryEntry,
} from "./check-registry.js";
export type { CanonicalPair } from "./canonical.js";
export {
  parseAndCheckWarrant,
  type WarrantRecord,
  type WarrantValidation,
} from "./warrant.js";
export {
  evaluateVoiding,
  type VoidingContext,
} from "./voiding.js";
export {
  parseAndCheckAcceptance,
  type AcceptanceValidation,
} from "./acceptance.js";
export {
  parseAndCheckMandate,
  type MandateRecord,
  type MandateValidation,
} from "./mandate.js";
export {
  DEFAULT_TSA_TRUST_LIST,
  type TsaTrustResult,
} from "./tsa-trust-list.js";
export { inspectTsa, verifyTsaTrust, type TsaCheck } from "./tsa.js";
