/**
 * Closed, versioned registry of every check the verifier executes.
 *
 * The BoundaryReport on VerifyResult (see index.ts) gives a verdict for
 * EVERY entry listed here, in this order — including the checks a
 * short-circuited run never reached. The registry is the report's fixed
 * universe: it changes only together with its version, and
 * `docs/specs/assessment-surface-v1.json` maps the normative clauses of
 * `docs/specs/aep-profile-v1.md` onto it (or onto
 * `"no-executable-check"` for clauses no code executes). A CI-level
 * test (lib/test/assessment-surface.test.ts) two-set-diffs this
 * registry against that map, so a check cannot silently appear in — or
 * vanish from — the assessed surface: the denominator of "what was
 * assessed" is pinned to the spec surface, not to whatever set of
 * checks this verifier happens to ship.
 */

import { jcs } from "./canonical.js";
import { sha256, toHex } from "./hash.js";

/** Stable identifier of one verifier check. Closed set; see CHECK_REGISTRY. */
export type CheckId =
  | "zip-structure"
  | "required-entries"
  | "metadata-parse"
  | "canonical-profile"
  | "canonical-response-only"
  | "hash-sha256"
  | "rsa-signature"
  | "rsa-digestinfo-fallback"
  | "signer-key-pinned"
  | "overt-receipt"
  | "warrant-digest"
  | "warrant-parse"
  | "warrant-bound"
  | "warrant-policy-link"
  | "warrant-applicability"
  | "warrant-acceptance-signature"
  | "mandate-digest"
  | "mandate-parse"
  | "mandate-bound"
  | "mandate-signature"
  | "mandate-scope"
  | "pqc-mldsa65"
  | "tsa-present"
  | "tsa-imprint"
  | "tsa-signerinfo"
  | "tsa-chain-to-root"
  | "warrant-freshness"
  | "mandate-temporal"
  | "voiding-predicates"
  | "accepting-authority-binding"
  | "accepting-authority-key-binding"
  | "accepting-authority-temporal"
  | "accepting-authority-role";

export type CheckRegistryEntry = {
  id: CheckId;
  /**
   * The `docs/specs/aep-profile-v1.md` clause this check executes.
   * Must match the clause label of at least one row in
   * `docs/specs/assessment-surface-v1.json` that names this check.
   */
  clause: string;
  /**
   * Whether, under default VerifyOptions, a failing outcome of this
   * check makes verify() return `valid: false`. Checks with `false`
   * here are advisory/informational in v0.1: they are executed and
   * reported but do not gate validity.
   */
  defaultEnforced: boolean;
};

/**
 * Registry version. Bump on ANY change to the entry list or its
 * semantics; the assessment-surface map pins this version and the CI
 * diff fails until both move together.
 */
export const CHECK_REGISTRY_VERSION = "1.5.0";

/**
 * The verifier's checks, in control-flow order (lib/src/verifier.ts).
 */
export const CHECK_REGISTRY: readonly CheckRegistryEntry[] = [
  { id: "zip-structure", clause: "§2 container", defaultEnforced: true },
  { id: "required-entries", clause: "§3 required entries", defaultEnforced: true },
  { id: "metadata-parse", clause: "§3 metadata.json", defaultEnforced: true },
  { id: "canonical-profile", clause: "§6 canonicalisation", defaultEnforced: true },
  { id: "canonical-response-only", clause: "§6 compatibility note", defaultEnforced: true },
  { id: "hash-sha256", clause: "§3 hash.sha256", defaultEnforced: true },
  { id: "rsa-signature", clause: "§3 signature.sig", defaultEnforced: true },
  { id: "rsa-digestinfo-fallback", clause: "§3 signature.sig (DigestInfo fallback)", defaultEnforced: true },
  { id: "signer-key-pinned", clause: "§8 signer key pinning", defaultEnforced: true },
  { id: "overt-receipt", clause: "§4.1 overt_receipt.json", defaultEnforced: true },
  { id: "warrant-digest", clause: "§4.2 warrant binding", defaultEnforced: true },
  { id: "warrant-parse", clause: "§4.2 warrant record", defaultEnforced: true },
  { id: "warrant-bound", clause: "§4.2 warrant binding form", defaultEnforced: false },
  { id: "warrant-policy-link", clause: "§4.2 warrant linkage", defaultEnforced: true },
  { id: "warrant-applicability", clause: "§4.2 warrant applicability", defaultEnforced: false },
  { id: "warrant-acceptance-signature", clause: "§4.2 warrant acceptance", defaultEnforced: true },
  { id: "mandate-digest", clause: "§4.5 mandate binding", defaultEnforced: true },
  { id: "mandate-parse", clause: "§4.5 mandate record", defaultEnforced: true },
  { id: "mandate-bound", clause: "§4.5 mandate binding form", defaultEnforced: true },
  { id: "mandate-signature", clause: "§4.5 mandate signature", defaultEnforced: true },
  { id: "mandate-scope", clause: "§4.5 mandate scope", defaultEnforced: false },
  { id: "pqc-mldsa65", clause: "§4 PQC entries", defaultEnforced: true },
  { id: "tsa-present", clause: "§7 timestamp token", defaultEnforced: true },
  { id: "tsa-imprint", clause: "§7 message imprint", defaultEnforced: false },
  { id: "tsa-signerinfo", clause: "§7 TSA signature", defaultEnforced: true },
  { id: "tsa-chain-to-root", clause: "§7 TSA trust anchor", defaultEnforced: false },
  { id: "warrant-freshness", clause: "§4.2 warrant freshness", defaultEnforced: false },
  { id: "mandate-temporal", clause: "§4.5 mandate temporal containment", defaultEnforced: false },
  { id: "voiding-predicates", clause: "§4.4 voiding predicates", defaultEnforced: false },
  { id: "accepting-authority-binding", clause: "§4.3 accepting authority binding", defaultEnforced: true },
  { id: "accepting-authority-key-binding", clause: "§4.3 accepting authority key binding", defaultEnforced: true },
  { id: "accepting-authority-temporal", clause: "§4.3 accepting authority temporal containment", defaultEnforced: false },
  { id: "accepting-authority-role", clause: "§4.3 accepting authority role", defaultEnforced: false },
] as const;

let digestPromise: Promise<string> | null = null;

/**
 * SHA-256 hex over the JCS bytes of `{version, checks}` — a content
 * digest of the registry itself, echoed in every BoundaryReport so a
 * relying party can pin the exact check universe a report was computed
 * against. Cached per module load; the registry is immutable at runtime.
 */
export function checkRegistryDigest(): Promise<string> {
  if (!digestPromise) {
    digestPromise = sha256(
      jcs({ version: CHECK_REGISTRY_VERSION, checks: CHECK_REGISTRY }),
    ).then(toHex);
  }
  return digestPromise;
}
