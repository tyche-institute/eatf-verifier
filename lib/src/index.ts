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

export type VerifyResult = {
  valid: boolean;
  report: string[];
  failureReason: string | null;
  /** Indicates the ML-DSA-65 PQC signature verification result when present. */
  pqcValid: boolean | null;
  /** Parsed metadata.json from the package, when readable. */
  metadata: Record<string, unknown> | null;
  /** Parsed and profile-checked overt_receipt.json, when the optional entry is present. */
  overtReceipt: Record<string, unknown> | null;
  /**
   * Advisory issuer-name comparison for the embedded
   * RFC 3161 TSA signing cert. `null` when the caller passed no
   * `tsaTrustList`, the TSA itself was absent, or the embedded cert
   * could not be parsed. This field is informational and does not
   * represent RFC 5280 path validation.
   */
  tsaTrusted?: boolean | null;
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
   * TSA issuer-name comparison. When empty (default), the verifier
   * skips chain validation and {@link VerifyResult.tsaTrusted} is set
   * to `null`. When non-empty, the verifier checks that the TSA
   * signing cert's issuer DN matches one of the supplied roots.
   *
   * Full RFC 5280 path validation (NotBefore / NotAfter / KeyUsage /
   * EKU / Basic Constraints / CRL / OCSP) is not performed. The
   * advisory match is issuer DN against pinned certificate subject DN.
   */
  tsaTrustList?: string[];
};

export { verify } from "./verifier.js";
export {
  prepareCanonical,
  sign,
  type PreparedCanonical,
  type SignerInput,
  type SignerOutput,
} from "./signer.js";
export { canonical, jcs, type CanonicalPair } from "./canonical.js";
export {
  DEFAULT_TSA_TRUST_LIST,
  type TsaTrustResult,
} from "./tsa-trust-list.js";
export { inspectTsa, verifyTsaTrust, type TsaCheck } from "./tsa.js";
