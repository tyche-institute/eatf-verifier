/**
 * Offline TypeScript signer for EATF .aep evidence packages.
 *
 * Mirrors the verifier in src/verifier.ts in reverse: given a payload,
 * an RSA keypair, OVERT receipt parameters, and an RFC 3161 timestamp
 * token, produces an .aep that the verifier in this package will accept.
 *
 * Wire format documented in ../docs/aep-format.md.
 *
 * Network policy: this module performs NO network I/O. The RFC 3161
 * timestamp response must be supplied by the caller and must cover
 * the SHA-256 digest of this package's canonical bytes.
 *
 * Not yet implemented in this signer: ML-DSA-65 post-quantum signing.
 * Verifier already supports verifying packages that carry it
 * (entries signature_pqc.sig + pqc_public_key.pem); a future release
 * will extend this signer to emit them.
 */

import { zipSync } from "fflate";
import { createSign } from "node:crypto";

import { canonical as buildCanonical, jcs } from "./canonical.js";
import { sha256, toHex } from "./hash.js";
import { inspectTsa } from "./tsa.js";
import { verify } from "./verifier.js";

const TEXT_ENC = new TextEncoder();
const OVERT_RECEIPT_SIGNATURE = "overt_receipt.sig";

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
  /** Raw bytes of an RFC 3161 TimeStampResp covering this package's canonical SHA-256 digest. */
  timestampTsr: Uint8Array;
  /** Optional issuer identifier ("eatf-verifier" by default). */
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

export type PreparedCanonical = {
  /** Exact bytes written as response.txt. */
  responseBytes: Uint8Array;
  /** Final metadata object, including an auto-generated created_at if needed. */
  metadata: Record<string, unknown>;
  /** Exact profile bytes written as canonical.bin. */
  canonicalBytes: Uint8Array;
  /** SHA-256 hex of canonicalBytes. */
  canonicalHashHex: string;
};

/**
 * Prepare the deterministic portion of an AEP before requesting an RFC 3161
 * timestamp. CLI callers should supply created_at explicitly so a later sign()
 * call reconstructs the same digest.
 */
export async function prepareCanonical(
  payload: Uint8Array | string,
  inputMetadata: Record<string, unknown>,
): Promise<PreparedCanonical> {
  const responseBytes = typeof payload === "string"
    ? TEXT_ENC.encode(payload)
    : new Uint8Array(payload);
  const metadata = { ...inputMetadata };
  if (!metadata.created_at) {
    metadata.created_at = new Date().toISOString();
  }
  metadata.overt_receipt_signature = OVERT_RECEIPT_SIGNATURE;
  const canonicalBytes = buildCanonical({
    responseBytes,
    metadataBytes: jcs(metadata),
  });
  const canonicalHashHex = toHex(await sha256(canonicalBytes));
  return { responseBytes, metadata, canonicalBytes, canonicalHashHex };
}

/**
 * Sign a payload into an .aep package.
 *
 * New packages use the AEP profile canonical form:
 * response.txt || LF || RFC 8785 JCS(metadata.json). This binds both
 * the payload and metadata to the hash, RSA signature, and RFC 3161
 * timestamp. Verifiers retain read-only support for legacy packages
 * whose canonical.bin contains response.txt alone.
 */
export async function sign(input: SignerInput): Promise<SignerOutput> {
  // Finalise metadata before canonicalisation so it is cryptographically
  // bound to the package. metadata.json remains human-readable; verification
  // parses it and reconstructs the RFC 8785 representation.
  const prepared = await prepareCanonical(input.payload, input.metadata);
  const payloadBytes = prepared.responseBytes;
  const metadata = prepared.metadata;
  const metadataBytes = TEXT_ENC.encode(JSON.stringify(metadata) + "\n");
  const canonical = prepared.canonicalBytes;
  const responseTxt = new Uint8Array(payloadBytes);

  // Hash.
  const hashHex = prepared.canonicalHashHex;
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
      iap: input.iap ?? "eatf-verifier",
      signature_refs: ["signature.sig", OVERT_RECEIPT_SIGNATURE],
      timestamp_refs: ["timestamp.tsr"],
    },
  };
  const receiptBytes = TEXT_ENC.encode(JSON.stringify(receipt) + "\n");
  const receiptSigner = createSign("sha256");
  receiptSigner.update(receiptBytes);
  receiptSigner.end();
  const receiptSig = receiptSigner.sign(input.privateKeyPem);
  const receiptSignatureEntry = TEXT_ENC.encode(
    Buffer.from(receiptSig).toString("base64") + "\n",
  );

  // Public key + timestamp. The package stores the raw RFC 3161 response
  // as base64 text so both verifier implementations consume one wire form.
  const publicKeyEntry = TEXT_ENC.encode(
    input.publicKeyPem.endsWith("\n") ? input.publicKeyPem : input.publicKeyPem + "\n",
  );
  const timestampBase64 = Buffer.from(input.timestampTsr).toString("base64");
  const timestampCheck = await inspectTsa(timestampBase64, hashHex, canonical);
  if (
    !timestampCheck.tsaPresent ||
    timestampCheck.messageImprintMatches !== true ||
    timestampCheck.signatureVerified !== true
  ) {
    throw new Error(
      "RFC 3161 timestamp must parse, match canonical.bin SHA-256, and carry a verifiable embedded signing certificate.",
    );
  }
  const timestampEntry = TEXT_ENC.encode(timestampBase64 + "\n");

  // Assemble.
  const entries: Record<string, Uint8Array> = {
    "canonical.bin": canonical,
    "hash.sha256": hashEntry,
    "metadata.json": metadataBytes,
    "overt_receipt.json": receiptBytes,
    [OVERT_RECEIPT_SIGNATURE]: receiptSignatureEntry,
    "public_key.pem": publicKeyEntry,
    "response.txt": responseTxt,
    "signature.sig": signatureEntry,
    "timestamp.tsr": timestampEntry,
  };
  const aep = zipSync(entries, { level: 0 });
  const selfCheck = await verify(aep, { tsaTrustList: [] });
  if (!selfCheck.valid) {
    throw new Error(
      `Refusing to emit an AEP that fails self-verification: ${selfCheck.failureReason ?? "unknown failure"}`,
    );
  }
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
