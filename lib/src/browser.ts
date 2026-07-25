/**
 * v0.1: browser-only re-export.
 *
 * The Node entry also exports the reference signer, which uses
 * `node:crypto`. This browser subpath deliberately exports only the
 * Web-Crypto verification surface.
 */

export { verify } from "./verifier.js";
export type { VerifyOptions, VerifyResult } from "./index.js";
export {
  DEFAULT_TSA_TRUST_LIST,
  type TsaTrustResult,
} from "./tsa-trust-list.js";
export { inspectTsa, verifyTsaTrust, type TsaCheck } from "./tsa.js";
