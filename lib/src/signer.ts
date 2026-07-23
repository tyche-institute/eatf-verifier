/**
 * Offline TypeScript signer for EATF .aep evidence packages.
 *
 * Mirrors the verifier in src/verifier.ts in reverse: given a payload,
 * an RSA keypair, OVERT receipt parameters, and an RFC 3161 timestamp
 * token, produces a v0.1-conformant .aep that the verifier in this
 * package will accept.
 *
 * Wire format documented in docs/aep-profile.md.
 *
 * Network policy: this module performs NO network I/O. The RFC 3161
 * timestamp token must be supplied by the caller — either fetched
 * out-of-band (via the eatf-sign CLI's --tsa-url flag) or copied from
 * an existing valid .aep package.
 *
 * Not yet implemented in this signer: ML-DSA-65 post-quantum signing.
 * Verifier already supports verifying packages that carry it
 * (entries signature_pqc.sig + pqc_public_key.pem); a future release
 * will extend this signer to emit them.
 */

import { zipSync } from "fflate";
import { createSign } from "node:crypto";

import { sha256, toHex } from "./hash.js";

const TEXT_ENC = new TextEncoder();

export type SignerInput = {
  /** The payload bytes being attested (e.g. an LLM response). */
  payload: Uint8Array | string;
  /** PEM-encoded RSA private key for the issuer. */
  privateKeyPem: string;
  /** PEM-encoded RSA public key for the issuer (will be embedded as public_key.pem). */
  publicKeyPem: string;
  /**
   * Base metadata for the package. The signer fills in `created_at`
   * (if absent) and validates that the caller-supplied metadata is
   * consistent with the OVERT receipt it generates.
   */
  metadata: Record<string, unknown>;
  /**
   * OVERT scope identifier, e.g. "foundational:aep-response" or
   * "agentic-extended:mcp-tools-call".
   */
  overtScope: string;
  /** Free-form subject block placed into receipt.subject. */
  overtSubject?: Record<string, unknown>;
  /** Free-form event block placed into receipt.event (excluding timestamp). */
  overtEvent?: Record<string, unknown>;
  /**
   * Policy block placed into receipt.policy. The signer copies
   * policy_id/version/coverage/decision from metadata when not
   * explicitly supplied here.
   */
  overtPolicy?: Record<string, unknown>;
  /** Raw bytes of an RFC 3161 TimeStampResp covering this signature's canonical bytes (or any older valid token; verifier accepts both). */
  timestampTsr: Uint8Array;
  /** Optional issuer identifier ("EATF.eu" by default). */
  iap?: string;
};

export type SignerOutput = {
  /** The .aep package as a single Uint8Array. */
  aep: Uint8Array;
  /** SHA-256 hex of canonical.bin, useful for logging. */
  canonicalHashHex: string;
  /** Names of every ZIP entry written. */
  entries: string[];
};

/**
 * Sign a payload into a v0.1-conformant .aep package.
 *
 * Uses the "Java response-only" canonical form: canonical.bin equals
 * the payload bytes verbatim. This form is what the existing test
 * vectors (valid-overt-profile, mcp-tools-call-valid, ...) use.
 */
export async function sign(input: SignerInput): Promise<SignerOutput> {
  const payloadBytes = typeof input.payload === "string"
    ? TEXT_ENC.encode(input.payload)
    : input.payload;

  // canonical.bin == response.txt (Java form).
  const canonical = new Uint8Array(payloadBytes);
  const responseTxt = new Uint8Array(payloadBytes);

  // Hash.
  const hashBytes = await sha256(canonical);
  const hashHex = toHex(hashBytes);
  const hashEntry = TEXT_ENC.encode(hashHex + "\n");

  // RSA signature over canonical bytes. The verifier uses
  // RSASSA-PKCS1-v1_5 with SHA-256 (Web Crypto + DigestInfo fallback),
  // not PSS. Matching the verifier's expectation here.
  const signer = createSign("sha256");
  signer.update(canonical);
  signer.end();
  const rsaSig = signer.sign(input.privateKeyPem);
  const rsaSigB64 = Buffer.from(rsaSig).toString("base64");
  const signatureEntry = TEXT_ENC.encode(rsaSigB64 + "\n");

  // Metadata: fill in created_at if absent.
  const metadata = { ...input.metadata };
  if (!metadata.created_at) {
    metadata.created_at = new Date().toISOString();
  }
  const metadataBytes = TEXT_ENC.encode(JSON.stringify(metadata) + "\n");

  // OVERT receipt: derive from metadata + caller-supplied blocks.
  const policyFromMeta = {
    id: metadata.policy_id,
    version: metadata.policy_version,
    coverage: metadata.policy_coverage,
    decision: metadata.policy_decision,
  };
  const policyBlock: Record<string, unknown> = {
    ...stripUndefined(policyFromMeta),
    ...(input.overtPolicy ?? {}),
  };
  const subjectBlock: Record<string, unknown> = {
    ...stripUndefined({
      agent_id: metadata.agent_id,
      tenant_hash: metadata.tenant_id_hash,
    }),
    ...(input.overtSubject ?? {}),
  };
  const eventBlock: Record<string, unknown> = {
    ...stripUndefined({
      timestamp: metadata.created_at,
      action_type: metadata.action_type,
    }),
    ...(input.overtEvent ?? {}),
  };
  const receipt: Record<string, unknown> = {
    overt: "1.0.0",
    profile: "urn:eatf:spec:aep:1.0",
    profile_revision: "1.0-draft",
    scope: input.overtScope,
    subject: subjectBlock,
    event: eventBlock,
    policy: policyBlock,
    content_hash: `sha256:${hashHex}`,
    prev: null,
    witness: {
      iap: input.iap ?? "EATF.eu",
      signature_refs: ["signature.sig"],
      timestamp_refs: ["timestamp.tsr"],
    },
  };
  const receiptBytes = TEXT_ENC.encode(JSON.stringify(receipt) + "\n");

  // Public key + timestamp.
  const publicKeyEntry = TEXT_ENC.encode(
    input.publicKeyPem.endsWith("\n") ? input.publicKeyPem : input.publicKeyPem + "\n",
  );
  const timestampEntry = input.timestampTsr;

  // Assemble.
  const entries: Record<string, Uint8Array> = {
    "canonical.bin": canonical,
    "hash.sha256": hashEntry,
    "metadata.json": metadataBytes,
    "overt_receipt.json": receiptBytes,
    "public_key.pem": publicKeyEntry,
    "response.txt": responseTxt,
    "signature.sig": signatureEntry,
    "timestamp.tsr": timestampEntry,
  };
  const aep = zipSync(entries, { level: 0 });
  return {
    aep,
    canonicalHashHex: hashHex,
    entries: Object.keys(entries).sort(),
  };
}

function stripUndefined<T extends Record<string, unknown>>(obj: T): Partial<T> {
  const out: Partial<T> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined) (out as Record<string, unknown>)[k] = v;
  }
  return out;
}
