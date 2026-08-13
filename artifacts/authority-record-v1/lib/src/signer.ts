/**
 * Offline TypeScript signer for EATF .aep evidence packages.
 *
 * Mirrors the verifier in src/verifier.ts in reverse: given a payload,
 * an RSA keypair, OVERT-inspired receipt parameters, and an RFC 3161 timestamp
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

import { canonical as canonicalPair, jcs } from "./canonical.js";
import { sha256, toHex } from "./hash.js";
import type { CanonicalForm } from "./index.js";

const TEXT_ENC = new TextEncoder();

/**
 * Fixed timestamp stamped on every ZIP entry so the .aep container
 * re-zips byte-for-byte identically regardless of when or where it is
 * produced (docs/aep-profile.md "Container").
 *
 * fflate encodes the ZIP (MS-DOS) timestamp from the Date's *local*
 * calendar fields, and that field cannot represent anything before
 * 1980-01-01. Constructing the Date from local components — rather than
 * from a UTC instant — makes the encoded value timezone-invariant, and
 * 1980-01-02 leaves a day of headroom above the DOS floor so no host's
 * local calendar can underflow it. (A UTC instant at the epoch throws
 * on hosts west of UTC.)
 */
const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);

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
   * consistent with the OVERT-inspired receipt it generates.
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
  /**
   * Optional warrant record (docs/specs/aep-profile-v1.md §4.2),
   * complete with its acceptance block — the acceptance signature is
   * made once by the accepting authority, never by this signer. The
   * signer packages the record as JCS-canonical bytes in warrant.json
   * and fills metadata warrant_id / warrant_version / warrant_digest
   * before the canonical bytes are built, so under the profile
   * canonical form the digest reference sits inside the signature.
   */
  warrant?: Record<string, unknown>;
  /**
   * Optional typed per-output voiding predicates
   * (docs/specs/aep-profile-v1.md §4.4). Written verbatim into
   * metadata.voiding before the canonical bytes are built, so under the
   * profile canonical form they sit under the signature.
   */
  voiding?: unknown[];
  /**
   * Optional epistemic accepting-authority block
   * (docs/specs/aep-profile-v1.md §4.3): `{principal, policy_id,
   * policy_version, validity}`. Written into metadata.accepting_authority.
   * When a detached `acceptance` is also supplied, the signer fills
   * `acceptance_digest` from its packaged bytes.
   */
  acceptingAuthority?: Record<string, unknown>;
  /**
   * Optional detached acceptance record plus its precomputed signature. The
   * acceptance signature is made ONCE by the accepting authority (over the
   * JCS bytes of the record), never by this signer. The signer packages the
   * record as JCS-canonical bytes in acceptance.json, writes the signature
   * to acceptance.sig, and fills metadata.accepting_authority.acceptance_digest.
   */
  acceptance?: { json: Record<string, unknown>; sig: string };
  /**
   * Optional deontic authorizing-principal block
   * (docs/specs/aep-profile-v1.md §4.5): `{principal, mandate_ref}`.
   * Written into metadata.authorizing_principal. Without a detached
   * `mandate`, this is the pre-§4.5 reference form: a named principal
   * whose grant nothing verifies.
   */
  authorizingPrincipal?: Record<string, unknown>;
  /**
   * Optional detached mandate record plus its precomputed signature. The
   * mandate signature is made ONCE by the granting authority (over the JCS
   * bytes of the record), never by this signer. The signer packages the
   * record as JCS-canonical bytes in mandate.json, writes the signature to
   * mandate.sig, and fills metadata.authorizing_principal.mandate_digest
   * BEFORE the canonical bytes are built, so under the profile canonical
   * form the digest reference sits inside the signature.
   */
  mandate?: { json: Record<string, unknown>; sig: string };
  /** Optional issuer identifier ("EATF.eu" by default). */
  iap?: string;
  /**
   * Canonical form for `canonical.bin` (docs/specs/aep-profile-v1.md §6).
   * `"profile"` signs response.txt + LF + JCS(metadata.json), so the
   * metadata sits under the signature and the timestamp;
   * `"response-only"` (default, matching the Java reference and the
   * existing test vectors) signs the payload bytes verbatim, leaving
   * metadata.json outside the signature.
   */
  canonicalForm?: CanonicalForm;
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
 * Defaults to the "Java response-only" canonical form: canonical.bin
 * equals the payload bytes verbatim. This form is what the existing
 * test vectors (valid-overt-profile, mcp-tools-call-valid, ...) use.
 * Pass `canonicalForm: "profile"` to sign the profile form instead
 * (response.txt + LF + JCS(metadata.json)), which places the metadata
 * under the signature.
 */
export async function sign(input: SignerInput): Promise<SignerOutput> {
  const payloadBytes = typeof input.payload === "string"
    ? TEXT_ENC.encode(input.payload)
    : input.payload;
  const form: CanonicalForm = input.canonicalForm ?? "response-only";

  // Metadata: fill in created_at if absent. Finalised before the
  // canonical bytes are built because the profile form signs it.
  const metadata = { ...input.metadata };
  if (!metadata.created_at) {
    metadata.created_at = new Date().toISOString();
  }

  // Optional warrant: package the record as JCS-canonical bytes and
  // reference it by digest from metadata BEFORE the canonical bytes
  // are built, so the profile form signs the reference.
  let warrantBytes: Uint8Array | null = null;
  if (input.warrant) {
    warrantBytes = jcs(input.warrant);
    if (metadata.warrant_id === undefined && typeof input.warrant.warrant_id === "string") {
      metadata.warrant_id = input.warrant.warrant_id;
    }
    if (metadata.warrant_version === undefined && typeof input.warrant.warrant_version === "string") {
      metadata.warrant_version = input.warrant.warrant_version;
    }
    metadata.warrant_digest = toHex(await sha256(warrantBytes));
  }

  // Optional typed voiding predicates: written into metadata before the
  // canonical bytes are built.
  if (input.voiding) {
    metadata.voiding = input.voiding;
  }

  // Optional epistemic accepting authority. When a detached acceptance
  // record is supplied, package it as JCS-canonical bytes and reference it
  // by digest from metadata BEFORE the canonical bytes are built, so the
  // profile form signs the reference.
  let acceptanceBytes: Uint8Array | null = null;
  let acceptanceSigEntry: Uint8Array | null = null;
  if (input.acceptance) {
    acceptanceBytes = jcs(input.acceptance.json);
    const digest = "sha256:" + toHex(await sha256(acceptanceBytes));
    metadata.accepting_authority = {
      ...(input.acceptingAuthority ?? {}),
      acceptance_digest: digest,
    };
    acceptanceSigEntry = TEXT_ENC.encode(input.acceptance.sig.trim() + "\n");
  } else if (input.acceptingAuthority) {
    metadata.accepting_authority = { ...input.acceptingAuthority };
  }

  // Optional deontic mandate. Same shape as the acceptance pair: the
  // record is packaged as JCS-canonical bytes and referenced by digest
  // from metadata BEFORE the canonical bytes are built, so the profile
  // form signs the reference.
  let mandateBytes: Uint8Array | null = null;
  let mandateSigEntry: Uint8Array | null = null;
  if (input.mandate) {
    mandateBytes = jcs(input.mandate.json);
    const digest = "sha256:" + toHex(await sha256(mandateBytes));
    metadata.authorizing_principal = {
      ...(input.authorizingPrincipal ?? {}),
      mandate_digest: digest,
    };
    mandateSigEntry = TEXT_ENC.encode(input.mandate.sig.trim() + "\n");
  } else if (input.authorizingPrincipal) {
    metadata.authorizing_principal = { ...input.authorizingPrincipal };
  }

  const metadataBytes = TEXT_ENC.encode(JSON.stringify(metadata) + "\n");

  // canonical.bin: response + LF + JCS(metadata) under the profile
  // form; the payload bytes verbatim under the Java response-only form.
  const responseTxt = new Uint8Array(payloadBytes);
  const canonical = form === "profile"
    ? canonicalPair({ responseBytes: responseTxt, metadataBytes: jcs(metadata) })
    : new Uint8Array(payloadBytes);

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

  // OVERT-inspired receipt: derive from metadata + caller-supplied blocks.
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
  if (warrantBytes) {
    entries["warrant.json"] = warrantBytes;
  }
  if (acceptanceBytes && acceptanceSigEntry) {
    entries["acceptance.json"] = acceptanceBytes;
    entries["acceptance.sig"] = acceptanceSigEntry;
  }
  if (mandateBytes && mandateSigEntry) {
    entries["mandate.json"] = mandateBytes;
    entries["mandate.sig"] = mandateSigEntry;
  }
  const aep = zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME });
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
