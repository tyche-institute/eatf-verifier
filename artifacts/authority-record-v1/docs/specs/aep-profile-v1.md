# AEP (Action Evidence Package) Profile, v1

> **Operator update (2026-05-14).** This open specification is published
> by **Tyche Institute** (Estonian non-profit, registration in progress)
> for the EATF research project.
> Compatible implementations are encouraged. This is a self-published
> research draft representing the maintainer's analysis; it does not
> constitute a formal commitment, regulatory filing, or legal opinion.
> Substantive byte-level rules are unchanged in this revision.

**Version:** 1.0-draft, dated 2026-05-12 (operator-entity revision 2026-05-14). Comment period open through 2026-08-12.
**Stable identifier:** `urn:eatf:spec:aep:1.0`
**Status:** open specification for the `.aep` evidence package emitted by the EATF reference implementation. Compatible implementations are encouraged.
**Owner:** Tyche Institute (Estonian non-profit, registration in progress), maintainer of the EATF research project.

---

## 1. Purpose

Define, at the byte level, the contents and canonicalisation rules of an
`.aep` (Action Evidence Package) so an independent verifier can:

1. Recompute the canonical bytes from the included payload.
2. Verify the canonical-bytes hash matches the embedded `hash.sha256`.
3. Verify the embedded RSA signature against the embedded public key.
4. Verify the embedded ML-DSA-65 signature against the embedded PQC public key.
5. Parse the embedded RFC 3161 timestamp token and validate it.
6. Resolve the agent identity, model id, policy id, policy version, and
   attestation id without any network call.

This document is referenced from the EATF Framework Operations
Statement (`docs/legal/framework-operations.md`). The verifier reference
implementation lives in `lib/src/verifier.ts` (package `@eatf/verifier`,
re-exported as `verify` from `lib/src/index.ts`); see section 12.

EATF is not an eIDAS trust service under Regulation (EU) 910/2014
Article 3(16); the AEP format documented here is a technical
self-attestation envelope, not a Qualified Electronic Attestation of
Attributes (QEAA) under Article 3(45).

## 2. Container format

A v1 `.aep` package is a **ZIP archive** (PKZIP, store or deflate). The
archive contains a flat directory of named files; nested directories
are forbidden in v1. Maximum uncompressed size: 10 MB (mirrors the
public verifier endpoint limit set in Phase 0 step 0.8).

The default file extension is `.aep`. Implementations MAY accept `.zip`
when the manifest is unambiguous.

## 3. Required entries

Every v1 package MUST include the following entries with these exact
names (case-sensitive, no path prefix):

| Entry | Content | Format |
|---|---|---|
| `response.txt` | The textual payload that was attested (the AI response text or governed action description). | UTF-8 text. No BOM. Line endings preserved as-issued. |
| `canonical.bin` | The canonical byte sequence produced from `response.txt` by the canonicalisation rules in section 4. Hash is computed over **these** bytes. | Opaque binary. |
| `hash.sha256` | Lower-case hex SHA-256 of `canonical.bin`. | ASCII, 64 hex characters, optional trailing newline. |
| `signature.sig` | Base64 (standard alphabet, with padding) of the PKCS#1 v1.5 RSA signature over `canonical.bin`. Inner digest algorithm: SHA-256. | ASCII. |
| `public_key.pem` | PEM-encoded RSA public key used to verify `signature.sig`. | ASCII, BEGIN/END PUBLIC KEY headers. |
| `metadata.json` | Machine-readable attestation metadata. See section 5. | UTF-8 JSON, canonicalised per section 4.4. |
| `timestamp.tsr` | Base64 of the RFC 3161 TimeStampToken issued for `hash.sha256` (the hex string is hashed again per RFC 3161 inside the TSA request; the verifier matches both). | ASCII. |

## 4. Optional entries (REQUIRED when PQC is enabled)

When the issuing TSP is configured to emit post-quantum signatures (an
issuer-side setting, enabled by default in the EATF reference signer from
Phase 1.9 onwards), the following entries MUST be present:

| Entry | Content | Format |
|---|---|---|
| `signature_pqc.sig` | Base64 of the ML-DSA-65 signature over `canonical.bin`. | ASCII. |
| `pqc_public_key.pem` | PEM-encoded ML-DSA-65 public key. | ASCII, BEGIN/END PUBLIC KEY headers. |
| `pqc_algorithm.json` | JSON object describing the PQC algorithm: `{"algorithm":"ML-DSA-65","oid":"2.16.840.1.101.3.4.3.18","level":3}`. | UTF-8 JSON. |

A v1 package without PQC entries is valid for backward compatibility
with pre-Phase-1.9 deployments. A v2 (planned) will make PQC mandatory.

Other optional entries:

| Entry | Content |
|---|---|
| `policy_coverage.json` | Per-rule policy evaluation report (attest mode only). |
| `agent_manifest.json` | A snapshot of the agent identity manifest that authorised this attestation. |
| `disclosure.json` | Article 50 transparency disclosure metadata (Phase 2.6). |
| `overt_receipt.json` | OVERT-inspired profile receipt binding the package hash, scope, subject, event, policy, and witness file references. |
| `warrant.json` | Warrant record: an authority-accepted statement that outputs the named policy evaluates to a listed decision are licensed for a listed action class, referenced by digest from `metadata.json`. See section 4.2. |
| `acceptance.json` | Detached epistemic acceptance record of the named accepting authority (`metadata.accepting_authority`), bound by digest. See section 4.3. |
| `acceptance.sig` | Base64 PKCS#1 v1.5 RSA signature (inner digest SHA-256) over the JCS bytes of `acceptance.json`, verifiable against its embedded `public_key`. See section 4.3. |
| `mandate.json` | Detached deontic mandate record of the granting authority named in `metadata.authorizing_principal`, bound by digest. See section 4.5. |
| `mandate.sig` | Base64 PKCS#1 v1.5 RSA signature (inner digest SHA-256) over the JCS bytes of `mandate.json`, verifiable against its embedded `public_key`. See section 4.5. |

### 4.1 `overt_receipt.json` schema

> **OVERT attribution and non-endorsement.** OVERT is an open standard
> published by Glacis Technologies, Inc. (https://overt.is). Tyche Institute
> and the EATF project are independent of Glacis Technologies: there is no
> affiliation, partnership, sponsorship, funding, certification, or
> endorsement in either direction. The entry specified in this section is an
> OVERT-inspired, receipt-shaped object defined by this specification. It is
> not claimed to be OVERT-conformant, it has not been reviewed, certified, or
> approved by Glacis Technologies, and nothing in this document should be read
> as a statement by them. Entry and field names that mention or resemble OVERT
> terminology (`overt_receipt.json`, `overt`, `witness.iap`) are wire-format
> identifiers of this profile, not conformance claims.

`overt_receipt.json` is an additive profile entry. It does not create a new
package type and does not replace any required `.aep` entry. Verifiers that do
not understand this entry MAY ignore it; verifiers that process it MUST reject
the package if the receipt is present and inconsistent with the rest of the
package.

Minimum schema:

```json
{
  "overt": "1.0.0",
  "profile": "urn:eatf:spec:aep:1.0",
  "profile_revision": "1.0-draft",
  "scope": "foundational:aep-response",
  "subject": {
    "agent_id": "urn:eatf:tenant:<tenantId>:agent:<slug>",
    "tenant_hash": "sha256:<tenant-binding-hash>",
    "system": "eatf-aep",
    "revision": "1.0-draft"
  },
  "event": {
    "type": "eatf.response",
    "timestamp": "2026-05-14T12:00:00Z",
    "action_type": "sign"
  },
  "policy": {
    "id": "atap-basic",
    "version": "1.0",
    "coverage": 1.0,
    "decision": "allow"
  },
  "content_hash": "sha256:<64 lowercase hex chars from hash.sha256>",
  "prev": null,
  "witness": {
    "iap": "EATF.eu",
    "signature_refs": ["signature.sig"],
    "timestamp_refs": ["timestamp.tsr"]
  }
}
```

Required fields:

| Field | Requirement |
|---|---|
| `overt` | MUST equal `1.0.0` for this profile revision. |
| `profile` | MUST equal `urn:eatf:spec:aep:1.0`. |
| `profile_revision` | MUST identify the AEP draft/release that generated the receipt. |
| `scope` | MUST be a non-empty assessment scope string. Current EATF generators use `foundational:aep-response`, `agentic-extended:atap-action`, or `agentic-extended:mcp-tools-call`. |
| `subject.agent_id` | MUST match `metadata.json.agent_id` when metadata carries an agent identifier. MAY be `null` for sign-only response packages. |
| `subject.tenant_hash` | MUST match `metadata.json.tenant_id_hash` when present. MUST NOT contain a raw tenant id. |
| `event.timestamp` | MUST match `metadata.json.created_at` when present. |
| `event.action_type` | MUST match `metadata.json.action_type` when present. |
| `policy.version` | MUST match `metadata.json.policy_version` when present. |
| `policy.coverage` | MUST match `metadata.json.policy_coverage` when present. |
| `policy.decision` | SHOULD be `allow`, `deny`, or equivalent policy-engine status when metadata carries `policy_decision`; MUST match that metadata field when present. |
| `content_hash` | MUST equal `sha256:` followed by the lower-case value of `hash.sha256`. |
| `prev` | MAY be `null`; otherwise SHOULD name the previous attestation id or digest in an evidence chain. |
| `witness.iap` | MUST identify the independent attestation provider that issued or preserved the package. |
| `witness.signature_refs` | MUST be a non-empty array of flat filenames in the same package. Each referenced file MUST exist and be non-empty. |
| `witness.timestamp_refs` | MUST be an array of flat filenames in the same package. It MAY be empty for transitional packages without a timestamp. |

A verifier that processes the receipt MUST compare `content_hash` to `hash.sha256`, compare
the metadata-bound fields above, and confirm every referenced witness file is
present in the flat ZIP namespace. Unknown receipt fields MUST be ignored for
forward compatibility.

### 4.2 `warrant.json` schema

`warrant.json` is an additive profile entry
(`schemas/warrant-v1.schema.json`). It does not create a new package type and
does not replace any required `.aep` entry. Verifiers that do not understand
warrants MAY ignore it; warrant-aware verifiers MUST reject the package if a
warrant is present and inconsistent with the rest of the package. The packaged
bytes MUST be the RFC 8785 (JCS) canonical form of the warrant record, and
`metadata.json` MUST carry a `warrant_digest` field equal to the lower-case hex
SHA-256 of those bytes (with optional `warrant_id` / `warrant_version` echoes
that MUST match the record when present); the record's
`policy_ref.policy_id` / `policy_ref.policy_version` MUST equal the metadata
`policy_id` / `policy_version`; and `acceptance.signature` MUST verify as a
PKCS#1 v1.5 RSA signature (inner digest SHA-256) over the JCS bytes of the
warrant with `acceptance.signature` removed, against `acceptance.public_key`.
Binding verification and authorization appraisal are separate verifier
decisions: a metadata `action_type` or `policy_decision` outside `applies_to`,
or an RFC 3161 `genTime` outside `valid_from`..`valid_until`, is reported —
the output may inform but carries no warrant to compel — and MUST NOT by
itself fail verification. Because the warrant is bound through
`metadata.json`, the binding holds only under the profile canonical form of
section 6; under the response-only compatibility form the verifier MUST report
the warrant as unbound. The accepting authority is a named principal with a
verifiable key binding under the same self-attestation trust model as
`public_key.pem` (section 1); nothing in this profile establishes it as a
legally constituted authority. The soundness of the licensed inference and the
key-to-principal binding of the accepting authority are attested, never
machine-checked; `void_if` entries are recorded (partitioned into machine
predicates and attested text) but their predicates are not evaluated by the
v0.1 verifiers.

### 4.3 `accepting_authority` and the detached `acceptance.json` / `acceptance.sig`

`metadata.accepting_authority` is an additive metadata block
(`schemas/aep-v1.schema.json`) naming the **epistemic** accepting authority:
the named principal that accepted, once, that outputs under this policy
version license their action class. It is deliberately distinct from the
**deontic** authorizing principal (who granted the mandate to act) — one
output can carry both, a two-layer authority record. The accepting authority
is a named principal with a verifiable key binding under the same
self-attestation trust model as `public_key.pem` (section 1); **nothing in
this profile establishes it as a legally constituted authority.**

Binding verification and authorization appraisal are **separate verifier
decisions**, and the verifier reports each outcome separately. Two of the
four **GATE**, and two are appraisal:

- **Key binding — GATES.** When the optional detached `acceptance.json` /
  `acceptance.sig` pair is packaged, `acceptance.sig` MUST verify as a PKCS#1
  v1.5 RSA signature (inner digest SHA-256) over the RFC 8785 (JCS) bytes of
  `acceptance.json`, against the record's embedded `public_key`. A packaged
  acceptance whose signature does not verify makes verification **fail**: a
  package MUST NOT be accepted while advertising an acceptance its named
  authority did not sign.
- **Output binding — GATES.** The acceptance is bound to *this* output only
  under the profile canonical form (section 6): the block is under the
  signature, and a packaged `acceptance.json` MUST match
  `accepting_authority.acceptance_digest` (`sha256:` + the lower-case hex
  SHA-256 of its JCS bytes) with its `principal` / `policy_id` /
  `policy_version` agreeing. Under the response-only compatibility form the
  whole block is unsigned and rewritable, so an acceptance carried there is
  bound to nothing. An acceptance that is not bound to this output makes
  verification **fail** — including the response-only case, on the section
  4.5 rule and for the same reason: sections 4.3 and 4.5 are surface added
  after the response-only form was frozen and carry no compatibility
  obligation to it. (Section 4.2, which does, still reports rather than
  rejects.)
- **Temporal containment.** The RFC 3161 `genTime` is checked against
  `accepting_authority.validity` (`not_before`..`not_after`); a `genTime`
  outside the window is reported and MUST NOT by itself fail verification.
  What lapsed is the licence, not the binding, and the `genTime` it is judged
  against is only as good as a trust anchor the package cannot supply.
- **Role.** Role assertion is attested-only unless the caller supplies an
  `authorityTrustList`, the exact mirror of the TSA trust-list tri-state;
  when supplied, the accepting authority's key is checked for membership and
  the result is reported **separately from key binding**. It MUST NOT by
  itself fail verification: it is undecidable from the package alone.

A property that is not determinable on the input at hand never gates. An
absent `accepting_authority`, and a signed inline claim carrying no detached
record, are both legal.

### 4.4 `voiding` predicates

`metadata.voiding` is an additive array of typed, machine-evaluable per-output
voiding predicates (`schemas/aep-v1.schema.json`). Each entry — `{id, type,
subject, on_true}` — is a condition that, when it holds, voids or degrades the
output. It refines, from workflow level to output level, the untyped
workflow-level defeaters that predate this profile. The verifier evaluates
every predicate at verify time and emits a **four-valued verdict** per entry:
`holds` (the condition did not fire), `voided` (it fired), `unknown` (a known
type whose caller-supplied input or a required fact is absent), and
`not-assessed` (an unknown type, or an attested-only predicate). **An unknown
type MUST yield `not-assessed`, never `holds`.**

External state is a **caller-supplied input** — a digested, dated registry
snapshot (`registrySnapshot`), a supersession list (`supersessionList`) —
exactly like the TSA trust list, **never a network fetch**, so verification
stays offline-deterministic and every verdict is explicitly relative to a
named snapshot.

For `registry-status` predicates the verifier evaluates the **same** snapshot
**twice**: once at the package's RFC 3161 `genTime` and once at the snapshot's
caller-supplied evaluation instant. The pair `(atSigning, now)` is surfaced
and **MUST NOT be collapsed** to one boolean. This **imports** the dual-time
temporal-validation semantics of AdES signature validation (ETSI EN 319 102-1)
and eIDAS status determination (ETSI TS 119 615) — with the polarity
inverted: where those procedures collapse the two evaluations into a single
indication, here the **divergence** between them is the reportable object.
The semantics are imported, not invented.

All of section 4.4 is informational in this release: a `voided` verdict does
not by itself fail verification.

### 4.5 `authorizing_principal` and the detached `mandate.json` / `mandate.sig`

`metadata.authorizing_principal` is an additive metadata block
(`schemas/aep-v1.schema.json`) naming the **deontic** authorizing principal:
the authority that granted the subject agent a mandate to act. It is the
counterpart of the epistemic accepting authority of section 4.3, and one
output can carry both — a two-layer authority record.

A block that names a principal and nothing else is the **reference form**: it
claims no signed mandate, and a verifier MUST report every mandate check as
not determinate rather than as a pass. A block that carries
`mandate_digest`, or a package that carries a `mandate.json` entry, claims a
**signed mandate**, and the obligations below apply.

A mandate is a once-authored, versioned grant, signed by the granting
authority with a key of its own — a principal distinct from the package
issuer (`public_key.pem`) and from the accepting authority of sections
4.2–4.3. It travels as RFC 8785 (JCS) canonical bytes in `mandate.json`, with
a detached PKCS#1 v1.5 RSA signature (inner digest SHA-256) in `mandate.sig`.

- **Digest binding.** `authorizing_principal.mandate_digest` MUST equal
  `sha256:` followed by the lower-case hex SHA-256 of `mandate.json` as
  packaged. A digest reference without the entry, an entry without the
  reference, or a mismatch is inconsistent and MUST be rejected.
- **Record.** The packaged bytes MUST be the JCS canonical form of a record
  with the required fields of `schemas/mandate-v1.schema.json` (`mandate_id`,
  `mandate_version`, `principal`, `subject`, `granted_at`, `statement`,
  `scope`, `valid_from`, `valid_until`, `public_key`).
- **Binding to the protected bytes.** A claimed mandate MUST be bound to the
  bytes `signature.sig` covers: the package MUST use the profile canonical
  form of section 6, and the record's `mandate_id` / `principal` / `subject`
  MUST equal the signed metadata's `authorizing_principal.mandate_ref` /
  `authorizing_principal.principal` / `agent_id`. A mandate carried under the
  response-only compatibility form MUST be rejected: there its own digest
  reference lies outside the signature and is rewritable. **This obligation
  is deliberately stricter than the corresponding obligations of sections 4.2
  and 4.3**, which report an unbound warrant or acceptance and accept the
  package. Section 4.5 is new surface and carries no compatibility debt to
  the response-only form.
- **Signature.** `mandate.sig` MUST verify as a PKCS#1 v1.5 RSA signature
  (inner digest SHA-256) over the JCS bytes of `mandate.json`, against the
  record's embedded `public_key`. A package cannot assert a mandate its named
  granting authority never signed, and a failure here MUST be rejected.
- **Scope.** The attested `action_type` and `policy_id` are checked against
  `scope.action_types` and `scope.policy_ids`. An action outside the granted
  scope is reported — it may inform, it cannot compel — and MUST NOT by
  itself fail verification.
- **Temporal containment.** The RFC 3161 `genTime` is checked against
  `valid_from`..`valid_until`; a `genTime` outside the window is reported and
  MUST NOT by itself fail verification.

The granting authority is a named principal with a verifiable key binding
under the same self-attestation trust model as `public_key.pem` (section 1);
**nothing in this profile establishes it as a legally constituted authority,
and whether the grant it makes is lawful is attested, never machine-checked.**

## 5. `metadata.json` schema

The metadata file is the primary integration point for downstream
tooling (CLI, WASM verifier, GRC connectors). v1 fields:

```json
{
  "schema": "urn:eatf:spec:aep:metadata:1.0",
  "attestation_id": "att_01HXY...ULID",
  "uuid": "0c45db8d-1bf2-4f7e-9c8f-f7e2c5f7f76e",
  "tenant_id_hash": "f3a1c7...",          // SHA-256 of the tenant numeric id; never the raw id
  "agent_id": "urn:eatf:tenant:<tenantId>:agent:medical-assistant-7a3c",
  "model": "gpt-4o-2025-08-06",
  "policy_id": "atap-basic",
  "policy_version": "1.0",
  "created_at": "2026-05-12T11:23:45Z",   // RFC 3339 / ISO 8601 UTC
  "canonicalisation": "eatf-canonical-1",
  "hash_algorithm": "SHA-256",
  "rsa_key_id": "kid_rsa_2026-01",
  "pqc_key_id": "kid_mldsa65_2026-01",
  "tsa_url": "https://freetsa.org/tsr",
  "issuer": {
    "name": "EATF.eu",
    "url": "https://eatf.eu",
    "tsps_version": "urn:eatf:tsps:1.0"
  }
}
```

Fields are REQUIRED unless explicitly optional. Implementations MUST
ignore unknown fields (forward-compatibility). The `tenant_id_hash`
intentionally avoids leaking the raw tenant integer; an auditor with the
tenant's secret can verify the binding, an unrelated reader cannot
enumerate tenants.

### 5.1 `agent_id` URN scheme

> **Normative.** Phase 2 v0.1 onwards.

The `agent_id` field carries a tenant-bound URN of the form

```
urn:eatf:tenant:<tenantId>:agent:<slug>
```

where:

- `<tenantId>` is a stable opaque identifier issued by the tenant
  directory (typically a UUID; ≤128 characters).
- `<slug>` is a sanitised, lowercase, dash-separated rendering of the
  agent name. The slug character set is `[a-z0-9-]`; runs of any
  other character collapse to a single dash; leading and trailing
  dashes are trimmed; the slug is bounded to ≤56 characters so that
  an optional disambiguation suffix can be appended without
  exceeding the 64-character agent-portion budget.
- On collision inside a tenant, generators append `-` followed by 8
  hexadecimal characters of entropy.

Legacy identifiers of the form `urn:uuid:<random>` remain valid for
agents registered before this scheme came into force; verifiers MUST
accept both forms. New registrations MUST emit the tenant-bound form
unless no tenant context is available at generation time (e.g.
fixture seeding outside an HTTP request), in which case the legacy
form is permitted as a documented fallback.

The URN binding asserts structural independence: every attested
action visibly names the tenant scope at the identifier level,
without requiring the verifier to consult any external registry.

## 6. Canonicalisation rules

The canonical byte sequence is produced by the following deterministic
algorithm, identified as `eatf-canonical-1`:

1. **Source.** Concatenate, in order: `response.txt` UTF-8 bytes, a
   single LF (`0x0A`) separator, the canonical JSON form of
   `metadata.json` (section 4.4). Implementations MUST NOT include any
   other entries in the canonical bytes.
2. **JSON canonicalisation.** RFC 8785 (JCS):
   - All object members sorted by codepoint of the key.
   - No insignificant whitespace.
   - Numbers serialised per ECMA-404 with no trailing zeros.
   - Strings as JSON strings (escape only what the spec requires).
   - No BOM, UTF-8.
3. **Line endings in `response.txt`.** Preserved verbatim. Implementations
   that perform any normalisation MUST do it BEFORE building the package
   and document the rule in the package's `metadata.canonicalisation`.
4. **The result of step 1 is `canonical.bin`.** It is what the hash and
   the signatures are computed over.

A verifier MUST refuse a package if the recomputed canonical bytes do
not match the embedded `canonical.bin`.

**Compatibility note — response-only canonical form.** The reference
verifiers additionally accept a legacy form in which `canonical.bin`
equals the `response.txt` bytes verbatim, as emitted by the current
Java package generator for sign-only bundles. The consequence of that
form is that the whole of `metadata.json` — including
`policy_id`, `policy_version`, and `policy_decision` — lies outside
`signature.sig`, `hash.sha256`, and the RFC 3161 message imprint: the
signature binds only the response, and the metadata can be rewritten
without invalidating the package (the optional OVERT-inspired receipt
cross-check catches only the fields it echoes). Verification still
succeeds, but the result reports which form matched
(`canonicalForm: "profile" | "response-only"` in the TypeScript
verifier); relying parties that depend on signed metadata MUST check
for the profile form rather than treating the two forms as equivalent.

## 7. RFC 3161 timestamp profile

The TSA token is issued over the **hex string** of `hash.sha256`, not
over the raw bytes of `canonical.bin`. The verifier's contract:

1. Decode `timestamp.tsr` from Base64.
2. Parse as a `TimeStampToken` per RFC 3161.
3. Confirm the `messageImprint.hashAlgorithm` is `2.16.840.1.101.3.4.2.1`
   (SHA-256).
4. Confirm `messageImprint.hashedMessage` equals the SHA-256 of the
   ASCII representation of `hash.sha256` (including any trailing newline
   present in the file — recommended to omit).
5. Verify the TSA's signature using the TSA certificate carried in the
   token (or out-of-band trust list — EATF's public TSA cert is
   published at `https://eatf.eu/.well-known/tsa-cert.pem`).

When the issuing TSA is an EATF deployment's local RFC 3161 server,
the genTime is the backend wall clock with a documented drift bound
of ±2 seconds. When the deployment is configured to chain through a
third-party qualified TSA, that TSA's own genTime applies. EATF
itself does not operate as a TSA; the deployment chooses its TSA.

## 8. X.509 certificate profile for signing keys

EATF signing certificates conform to RFC 5280 with:

- Algorithm: `sha256WithRSAEncryption` (1.2.840.113549.1.1.11) for RSA-4096.
- For ML-DSA-65 keys, distribution today is raw PEM (no X.509 wrapping
  pending IETF adoption of ML-DSA OIDs in the LAMPS WG draft); v2 of
  this profile will switch to X.509-wrapped distribution when the LAMPS
  draft stabilises.
- Subject CN: `urn:eatf:signer:<keyId>` where `<keyId>` matches the
  `rsa_key_id` / `pqc_key_id` field in `metadata.json`.
- Validity: rotated annually (Phase 1.10 introduces ceremony automation).
- Extended key usage: `id-kp-codeSigning` plus a custom OID
  `1.3.6.1.4.1.99999.1.1` for "eatf-aep-signing" (placeholder; we will
  request a real OID from IANA as part of the Phase 2 ETSI TR
  submission in step 2.13).

### 8.1 Signer key pinning

`public_key.pem` is carried inside the package it verifies, so the default
trust model is **self-attestation** (section 1): the signature establishes
that whoever holds that key signed these bytes, and nothing more. A package
re-authored end to end under a different key — canonical bytes, hash,
signature and public key all recomputed — is authentic evidence of a
different issuer's claim, and the profile's other obligations cannot tell
the two apart, because none of them names an expected issuer.

A relying party that knows which issuer it accepts supplies that expectation
as a caller-supplied input, on the pattern of the section 7 TSA trust list:

- When the caller supplies a non-empty trusted-signer list, the verifier MUST
  check `public_key.pem` for membership and MUST **reject** a package whose
  signing key is not a member. Membership comparison ignores PEM whitespace.
- When the caller supplies no list, the check is **not assessed**, the
  verdict records that reason, and the package's issuer is attested only.

Unlike the section 7 trust-anchor check, which reports, this one gates: a
package from an unexpected issuer is not a weaker verdict about this issuer's
claim, it is a verdict about someone else's.

## 9. Ledger entry format

Each evidence package is logged to the per-tenant hash-chained ledger.
The ledger entry is itself signed and timestamped. The block format
below is normative; **no reference implementation of the ledger ships in
this repository** — it is a service-side concern, and the verifiers in
section 12 neither produce nor check ledger blocks. Block fields:

```text
block_index        : long, monotonically increasing per tenant from 0
tenant_id          : UUID/long, scoped lock per Phase 0 step 0.5
previous_hash      : SHA-256 hex of the previous block (genesis = 64 × "0")
merkle_root        : SHA-256 hex of the Merkle root over events in this block
current_hash       : SHA-256 hex over (index ‖ previous_hash ‖ merkle_root ‖ timestamp)
event_count        : integer
created_at         : RFC 3339 timestamp
signing_key_id     : kid present in metadata.rsa_key_id of the signer
signature_pqc      : Base64 ML-DSA-65 signature over the block hash (optional, PQC mode)
```

A verifier rebuilds the chain from index 0 and the embedded keys to
confirm tamper-evidence.

## 10. Versioning

The profile version is recorded in `metadata.schema`. Bump rules:

- **Minor (1.x → 1.y, y > x):** purely additive fields; existing
  verifiers MUST still accept the package.
- **Major (1 → 2):** breaking format change. v2 is planned to (a) make
  PQC entries mandatory, (b) move to X.509-wrapped ML-DSA keys, (c)
  introduce a streaming canonicalisation for >10 MB payloads.

## 11. Conformance levels

A v1 package is **strict conformant** if it includes every REQUIRED
entry, satisfies every canonicalisation rule, and validates against the
verifier reference implementation linked in section 1.

A package is **transitional conformant** if PQC entries are missing
(pre-Phase-1.9 EATF deployments).

A package is **non-conformant** otherwise.

## 12. Reference implementations

- TypeScript (`lib/`, package `@eatf/verifier`): authoritative reference.
  `cli/eatf-verify` loads `lib/dist/index.js`, so `--conformance` runs
  this implementation. It is also the only one that emits the
  `BoundaryReport` and the section 4.2–4.4 outcome records in v0.1.
- Python (`lib-python/eatf_verifier/`): second implementation, with its
  own `--conformance` runner using the same path-prefix rule. It is
  expected to agree with the TypeScript runner vector for vector; both
  currently report `8 verified, 7 rejected, 0 contract mismatches`.
- Packaging targets live under `sdks/` (`eatf-cli`, `eatf-verifier-ts`,
  `python-sdk`).

Earlier drafts of this section named a Java `backend/` shaded JAR as the
authoritative reference. No `backend/` tree has ever been present in this
repository (it was carried over from the pre-release codebase), so that
pointer never resolved here; the same applies to the
`sdks/go-verifier/` path, which does not exist.

## 13. Test vectors

Authoritative test vectors live at `test-vectors/`. Two trees carry the
conformance contract; a v1-conformant verifier MUST produce the expected
result on every vector in them:

- `valid/`: packages that MUST verify cleanly.
- `invalid/`: packages that MUST fail verification, each exercising one
  failure mode and shipping a `verify-expected.txt` with the expected
  diagnostic.

Three further trees are **behavioural, not gating**. They pin *how* an
outcome is reported rather than the `verify` boolean, and most of their
vectors verify `true` on purpose:

- `boundary/`: pins the per-check `BoundaryReport` (advisory failures,
  short-circuit shadows, unsigned fields, claimed-vs-computed overclaims).
- `voiding/`: pins the section 4.3 accepting-authority outcomes and the
  section 4.4 voiding-predicate verdicts, none of which flip `valid`.
- `warrant/`: pins the section 4.2 warrant outcomes — structural
  inconsistency (digest, policy linkage, acceptance signature, presence)
  fails verification; inapplicability, staleness, and unboundness are
  reported without failing it.

The reference runner derives the expectation from the path prefix and
appraises `valid/` and `invalid/` only; the behavioural trees are
exercised by the TypeScript test suite under `lib/test/`. Per-vector
tables, the live conformance output, and the current vector counts are
maintained in [`test-vectors/README.md`](../../test-vectors/README.md) —
counts are deliberately not duplicated here, because they change with
every point release.

## 14. Related documents

- `docs/legal/framework-operations.md` — Framework Operations Statement
  (non-TSP description of how the reference implementation is operated).
- `docs/legal/threat-model.md` — STRIDE threat model.
- `docs/legal/project-sustainability-plan.md` — open-source
  sustainability commitments (replaces the earlier Termination Plan).
- `docs/legal/disclosure-policy.md` — coordinated disclosure policy.
- `docs/specs/etsi-tr-aep-profile-draft.md` — ETSI TR submission draft
  (research draft).
- `test-vectors/README.md` — conformance vectors, per-vector tables, and
  the live conformance output.

## 15. Changelog

| Version | Date | Notes |
|---|---|---|
| 1.0-draft+mandate | 2026-08-13 | Added section 4.5: the detached `mandate.json` / `mandate.sig` pair giving the deontic `authorizing_principal` block a signed, independently keyed body. The binding family gates verification; scope and temporal containment are reported. |
| 1.0-draft+overt | 2026-05-14 | Added optional `overt_receipt.json` schema and receipt-aware verifier obligations. |
| 1.0-draft | 2026-05-12 | Initial Phase 1 step 1.2 draft. Comment period open. |
