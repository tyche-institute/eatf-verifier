# test-vectors/ — conformance test vectors

`test-vectors/` holds eight subdirectories: seven vector trees plus `keys/`,
which carries the RSA keypairs the vectors and generators are built from
(`dev-rsa-4096`, `test-accepting-authority`, `test-granting-authority`,
`reauthoring-adversary-4096`, `untrusted-rsa-4096`) and no
vectors of its own. Of the seven vector trees, **two are gating** — they carry the
`verify=true/false` conformance contract and are the only trees the
`--conformance` harness appraises. **Five are behavioural** — they pin
*how* the verifier reports an outcome. Behavioural is not the same as
non-rejecting: three of the five trees contain packages the verifier
rejects, because the §4.2, §4.3 and §4.5 layers each gate part of their
surface.

Gating:

- `valid/` (11 vectors) — packages that MUST verify cleanly. Every
  implementation claiming v0.1 conformance must report `verify=true`
  for every package under this tree.
- `invalid/` (8 vectors) — packages that MUST fail verification. Each
  subdirectory exercises one specific failure mode and ships a
  `verify-expected.txt` carrying a `diagnostic=` line. That line is
  advisory, not contractual — see the caveat under the table below, where
  one vector's declared diagnostic no longer matches what either
  reference verifier reports.

Behavioural (not gating):

- `mandate/` (9 vectors) — pins the §4.5 detached-mandate outcomes.
  Six verify `false` (the binding family gates, in BOTH reference
  implementations) and three verify `true` (two appraisal outcomes plus
  the pre-§4.5 reference form). See the table below.
- `boundary/` (7 vectors) — pins the verifier's per-check
  `BoundaryReport` (`VerifyResult.boundary`): advisory failures,
  short-circuit shadows, unsigned fields, claimed-vs-computed
  overclaims. See [`boundary/README.md`](boundary/README.md).
- `voiding/` (11 vectors) — pins the §4.4 voiding-predicate verdicts and
  the two §4.3 accepting-authority outcomes that do NOT gate. Eight verify
  `true`; three verify `false` since the §4.3 binding family was promoted
  (2026-08-13).
- `acceptance/` (4 vectors) — pins the §4.3 accepting-authority binding
  family, one broken property per vector. **All 4 verify `false`**, in both
  reference implementations. See the table below.
- `warrant/` (8 vectors) — pins the §4.2 warrant outcomes. Four verify
  `false` (structural inconsistency) and four verify `true`
  (appraisal outcomes that are reported, not enforced).

Corpus totals, recomputed from the tree: **58 vectors — 32 verify
`valid:true` and 26 verify `valid:false`.**

`--conformance` derives the expected result from the path prefix and
skips anything that is neither `valid/` nor `invalid/`
(`expectedFromTreePath` returns `null`). The five behavioural trees are
exercised instead by the TypeScript suite — `lib/test/boundary-vectors.test.ts`,
`lib/test/voiding-vectors.test.ts`, `lib/test/warrant-vectors.test.ts`,
`lib/test/mandate-vectors.test.ts`, `lib/test/acceptance-vectors.test.ts`,
`lib/test/signer-pinning.test.ts` — since the `BoundaryReport` and the §4.2
and §4.4 outcome records are emitted only by the TypeScript verifier. The
§4.3 and §4.5 outcomes are the exception: both implementations gate them,
and `lib-python/tests/test_mandate.py` and
`lib-python/tests/test_acceptance.py` pin the Python side of the same
contract.

> **Vector counts are not coverage.** 58 vectors do not mean 58 ways a
> package can be rejected. Only the 19 gating vectors assert a
> `verify=true/false` contract; of the remaining 39, eighteen can flip
> `valid` at all — the four structural `warrant/` cases, the six
> binding-family `mandate/` cases, the four `acceptance/` cases, the three
> §4.3 rejections now in `voiding/`, and `boundary/short-circuit-shadow`.
> The rest pin *reporting* — an outcome
> the spec deliberately declines to enforce is still a vector, and its
> presence says nothing about how much of the failure surface is gated.
> One concrete gap is recorded under the gating table below.

## Vector layout

```
<vector-name>/
├── package.aep
├── verify-expected.txt      # the verify=true/false contract; 26 of the 58
│                            # also carry an advisory diagnostic= line
│                            # (8 invalid/, 6 mandate/, 4 warrant/,
│                            #  4 acceptance/, 3 voiding/, 1 boundary/)
├── expected-*.json          # behavioural trees: VerifyOptions + the outcome rows to pin
└── README.md                # what this vector exercises
```

`README.md` is present in `invalid/`, `boundary/`, and five of the eleven
`valid/` vectors; the `voiding/`, `warrant/`, `mandate/` and `acceptance/`
vectors carry their prose in the `description` field of their
`expected-*.json` instead.

## Gating vectors

| Vector                                             | Expected             | Exercises                                                                    |
|----------------------------------------------------|----------------------|------------------------------------------------------------------------------|
| `valid/valid-overt-profile/`                       | `verify=true`        | Full happy-path. OVERT foundational scope.                                   |
| `valid/mcp-tools-call-valid/`                      | `verify=true`        | OVERT `agentic-extended:mcp-tools-call`, policy decision `allow`.            |
| `valid/mcp-tools-call-denied-policy/`              | `verify=true`        | Same scope, policy decision `deny` — AEP authentic; call rejected by policy. |
| `valid/minimal-roundtrip/`                         | `verify=true`        | Round-trip baseline produced by `eatf-sign` from `test-vectors/keys/dev-rsa-4096`. |
| `valid/profile-canonical/`                         | `verify=true`        | Profile canonical form (§6): `metadata.json` signed via `canonical.bin` = response + LF + JCS(metadata). |
| `valid/co-located-authority/`                      | `verify=true`        | Both authority layers over the same signed bytes: a deontic `authorizing_principal` and a distinct epistemic `accepting_authority`. Both informational. |
| `valid/voided-and-authorized/`                     | `verify=true`        | Bound acceptance plus two voiding predicates that hold: `reg-atap` (`registry-status`, evaluated at both instants) and `telemetry-fresh` (judged once against `genTime`). |
| `valid/warranted-action/`                          | `verify=true`        | Accepted warrant: digest-bound, policy-linked, applicable, acceptance signature verifies. |
| `valid/mandated-action/`                           | `verify=true`        | §4.5 detached mandate signed by `test-granting-authority`: digest-bound to the protected bytes, signature verifies, in scope and in force. |
| `valid/mandated-and-accepted/`                     | `verify=true`        | Both authority layers live over the same bytes: a signed mandate (deontic) and an accepted warrant plus detached acceptance (epistemic). Three distinct keys. |
| `valid/mandated-denied-action/`                    | `verify=true`        | The two-layer package recording `policy_decision: deny` — authentic evidence of a denial, and the baseline of the rewrite test below. |
| `invalid/profile-form-policy-rewrite/`             | `verify=false`       | The deny→allow rewrite of `boundary/response-only-unsigned-policy-tamper`, applied to the profile-form two-layer package. Rejected by both implementations at the canonical-form gate. |
| `invalid/tampered-canonical-bin/`                  | `verify=false`       | `canonical.bin` byte-flipped after signing. Rejected at the canonical-form gate, *before* the hash comparison — see the caveat below. |
| `invalid/tampered-metadata/`                       | `verify=false`       | `metadata.policy_decision` changed; OVERT-inspired receipt cross-check fails.         |
| `invalid/bad-signature-classical/`                 | `verify=false`       | `signature.sig` byte-flipped; RSASSA-PKCS1-v1_5 verification fails.          |
| `invalid/untrusted-issuer/`                        | `verify=false`       | `public_key.pem` swapped for an unrelated valid RSA key.                     |
| `invalid/missing-canonical-bin/`                   | `verify=false`       | Required `canonical.bin` entry absent from the envelope.                     |
| `invalid/bad-timestamp/`                           | `verify=false`       | `timestamp.tsr` ASN.1 mangled; RFC 3161 token unparseable.                   |
| `invalid/tampered-overt-receipt/`                  | `verify=false`       | Hash-chain mismatch on `overt_receipt.json` (post-sign tamper).              |

> **Caveat — `tampered-canonical-bin` no longer exercises the hash chain,
> and its declared diagnostic is stale.** The generator flips one byte in
> `canonical.bin`. Because the baseline `canonical.bin` equals
> `response.txt`, the flipped bytes then match *neither* canonical form,
> so both reference verifiers reject at the canonical-form gate and never
> reach the hash comparison. Live diagnostic from both:
> `canonical.bin does not match a supported canonical form.` — while
> `invalid/tampered-canonical-bin/verify-expected.txt` still declares
> `diagnostic=Hash mismatch.` The `verify=false` contract is unaffected
> (which is why conformance passes), but two things follow: the declared
> diagnostic is wrong, and **no gating vector currently exercises the
> enforced hash-`sha256` path** — `boundary/short-circuit-shadow` is the
> only vector in the tree that reaches it, and it is not gating. Fixing
> this means changing the tamper so it preserves a canonical form while
> breaking the hash, which changes vector bytes downstream implementers
> may have pinned; it is deliberately not done here.

Six of the eight `invalid/` vectors are produced deterministically by
`scripts/generate-invalid-vectors.mjs` from the `minimal-roundtrip`
baseline (`tampered-overt-receipt` predates it, and
`profile-form-policy-rewrite` comes from
`scripts/generate-mandate-vectors.mjs`); regenerating produces
byte-identical files. The scripts live in the repo so any downstream
implementer can audit the tamper logic. The `boundary/`, `voiding/`,
`warrant/`, `mandate/` and `acceptance/` trees have their own generators
alongside it.

## Behavioural vectors

These do not participate in the conformance contract. Listed here
because `voiding/` and `warrant/` have no tree-level README of their own.

### `voiding/` — §4.4 outcomes, and the §4.3 packages that predate the gate

Per `docs/specs/aep-profile-v1.md`, **a `voided` verdict does not by
itself fail verification** (§4.4), so every §4.4 vector below verifies
`true` and what it pins is the reported outcome.

The five §4.3 accepting-authority packages in this tree predate the
2026-08-13 promotion of the §4.3 binding family, and they are kept here
because together they draw the enforced/advisory line: the three whose
*binding* is broken now verify `false`, while the two that exercise
temporal containment and role — the appraisal checks — still verify
`true`. The isolated single-property §4.3 negatives live in
`acceptance/`.

| Vector | verify | Pins |
|---|---|---|
| `voided-registry-at-signing/` | `true` | Registry entry withdrawn before `genTime`; both dual-time evaluations report `voided`. |
| `diverged-registry-status/` | `true` | Withdrawal falls between `genTime` and the snapshot instant: the pair `(atSigning=holds, now=voided)` is surfaced and never collapsed. |
| `forward-dated-withdrawal/` | `true` | Withdrawal effective after both instants — a correct comparison must NOT read the entry as withdrawn now. |
| `missing-snapshot-input/` | `true` | A `registry-status` predicate with no caller-supplied snapshot MUST yield `unknown` (`input_absent`), never `holds`. |
| `unknown-voiding-type/` | `true` | An unrecognised predicate type MUST yield `not-assessed` (`unknown_type`), never `holds`. |
| `stale-telemetry/` | `true` | Telemetry sampled far beyond its max age before `genTime`; predicate reports `voided`, judged offline against `genTime`. |
| `expired-acceptance/` | `true` | Acceptance authentic and bound, but its validity window closed before `genTime`: `temporalContainment=false`. Appraisal — the licence lapsed, the binding did not. |
| `authority-key-substitution/` | `true` | Acceptance signed with a substituted key: key binding passes, role verification against the caller's `authorityTrustList` fails — reported separately, and role never rejects. |
| `tampered-acceptance/` | `false` | `acceptance.json` rewritten post-signing: `keyBindingValid=false` and `boundToOutput=false`. Both gating checks fail. |
| `acceptance-policy-mismatch/` | `false` | Acceptance authentically signed and digest-matched, but its `policy_id` disagrees with metadata: `boundToOutput=false`. Authentic is not the same as bound. |
| `response-only-with-authority/` | `false` | Canonical-form overclaim: under the response-only form the whole block is rewritable, so `boundToOutput=false` and — as with §4.5 — the package is rejected. |

### `acceptance/` — §4.3 binding family

§4.3 splits like §4.5, and for the same reason. The binding family
(`accepting-authority-binding`, `accepting-authority-key-binding`)
**gates**, and so does the response-only form: §4.3 is surface added
after that form was frozen and carries no compatibility debt to it.
Temporal containment and role are appraisal — an expired acceptance is
authentic and bound, and role is undecidable from the package alone —
and both are exercised in `voiding/` above.

Like `mandate/`, this tree is a **two-implementation** contract:
`lib-python/tests/test_acceptance.py` pins the Python verdicts against
the same `verify-expected.txt` the TypeScript suite reads. Each vector
breaks exactly one property, so a rejection names one check.

| Vector | verify | Pins |
|---|---|---|
| `acceptance-signature-forged/` | `false` | `acceptance.sig` replaced with a real signature by the same authority over a *different* record. The packaged record is untouched, so binding passes and key binding alone fails. |
| `acceptance-stripped/` | `false` | `acceptance.json` / `acceptance.sig` removed after signing; `acceptance_digest` stays inside the signed metadata, so the package advertises an acceptance it does not carry. |
| `acceptance-digest-mismatch/` | `false` | The pair swapped for a different but entirely authentic acceptance by the same authority: key binding passes, output binding fails. Authenticity is not binding. |
| `acceptance-principal-substitution/` | `false` | Digest matches and the signature is real, but the record's `principal` is not the one the signed metadata names — cross-field binding is what catches it. |

### `warrant/` — §4.2 outcomes

§4.2 splits: a warrant-aware verifier **MUST reject** a package whose
warrant is structurally inconsistent with it (digest, policy linkage,
acceptance signature, presence), while an inapplicable, stale, or
unbound warrant is **reported and MUST NOT by itself fail verification**
— the output may inform but carries no warrant to compel.

| Vector | verify | Pins |
|---|---|---|
| `warrant-digest-mismatch/` | `false` | Warrant rewritten after signing; digest reference in signed metadata no longer matches. |
| `warrant-swap/` | `false` | Authentic, correctly accepted warrant for a *different* policy; only the policy-linkage check exposes it. |
| `warrant-acceptance-forged/` | `false` | Acceptance signature made with a different private key than the named principal's. |
| `warrant-acceptance-stripped/` | `false` | Warrant packaged with no acceptance block — no named acceptor, no policy backing. |
| `warrant-inapplicable-action/` | `true` | Warrant licenses a different action type; does not apply, package stays accepted. |
| `warrant-decision-void/` | `true` | Warrant licenses `allow` only; the `deny` output falls outside `applies_to`. |
| `warrant-stale/` | `true` | Warrant validity window ended before `genTime`: `fresh=false` reported. |
| `warrant-unbound/` | `true` | Response-only canonical form puts `warrant_digest` outside the signature: `bound=false` reported loudly. |

### `mandate/` — §4.5 outcomes

§4.5 splits like §4.2, with one deliberate difference: the binding family
(`mandate-digest`, `mandate-parse`, `mandate-bound`, `mandate-signature`)
**gates**, and so does the response-only form — an unbound *mandate* is
rejected where an unbound warrant is merely reported, because §4.5 is new
surface with no compatibility debt. Scope and temporal containment are
appraisal outcomes: reported, never rejecting.

Unlike `warrant/` and `voiding/`, this tree is a **two-implementation**
contract: both reference verifiers gate the mandate, and
`lib-python/tests/test_mandate.py` pins the Python verdicts against the
same `verify-expected.txt` the TypeScript suite reads.

| Vector | verify | Pins |
|---|---|---|
| `mandate-signature-forged/` | `false` | `mandate.sig` made with a different private key than the record's `public_key`. |
| `mandate-stripped/` | `false` | `mandate.json` / `mandate.sig` removed after signing; the digest reference stays inside the signed metadata. |
| `mandate-digest-mismatch/` | `false` | Granted scope widened after signing; the digest reference no longer matches. |
| `mandate-unbound/` | `false` | Response-only form leaves `mandate_digest` outside the signature — rejected, not reported. |
| `mandate-principal-substitution/` | `false` | An authentic mandate of a *different* authority; only the cross-binding to the signed block exposes it. |
| `mandate-subject-swap/` | `false` | An authentic mandate granted to a *different* subject agent. |
| `mandate-out-of-scope/` | `true` | Action outside `scope.action_types`: may inform, cannot compel. Reported. |
| `mandate-expired/` | `true` | Validity window closed before `genTime`: reported, package stays accepted. |
| `mandate-reference-only/` | `true` | The pre-§4.5 form — a principal named, no signed mandate claimed, every §4.5 check `not_determinate`. |

## Running conformance

```bash
cd lib && npm install && npm run build && cd ..
cd cli/eatf-verify && npm install && cd ../..

node cli/eatf-verify/bin/eatf-verify.js --conformance test-vectors/
```

Expected output:
```
PASS  package.aep  expected=false  actual=false  (RSA signature does not verify against public_key.pem.)
PASS  package.aep  expected=false  actual=false  (timestamp.tsr missing or empty.)
PASS  package.aep  expected=false  actual=false  (Missing required entry: canonical.bin.)
PASS  package.aep  expected=false  actual=false  (canonical.bin does not match a supported canonical form.)
PASS  package.aep  expected=false  actual=false  (canonical.bin does not match a supported canonical form.)
PASS  package.aep  expected=false  actual=false  (overt_receipt.json invalid: policy.decision does not match metadata.policy_decision.)
PASS  package.aep  expected=false  actual=false  (overt_receipt.json invalid: content_hash does not match hash.sha256.)
PASS  package.aep  expected=false  actual=false  (RSA signature does not verify against public_key.pem.)
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true
PASS  package.aep  expected=true  actual=true

Conformance: 11 verified, 8 rejected, 0 contract mismatches.
```

The 19 lines are the 11 `valid/` and 8 `invalid/` vectors; the 35
behavioural vectors are silently skipped by the path-prefix rule, so
they never appear in this output.

The Python verifier applies the same path-prefix rule and agrees vector
for vector:

```bash
cd lib-python && python3 -m eatf_verifier.cli --conformance ../test-vectors/
# Conformance: 11 verified, 8 rejected, 0 contract mismatches.
```

Implementations claiming v0.1 conformance run their own verifier
against every `valid/<vector>/package.aep` and every
`invalid/<vector>/package.aep` and report `PASS` (verify equals
expected) for every vector. The exact diagnostic text may differ
between implementations; the conformance contract only requires
the `verify=true|false` boolean.

More vectors will be added in successive 0.1.x point releases.

OVERT is an open standard published by Glacis Technologies, Inc.
(https://overt.is). This project is independent of Glacis Technologies and
carries no endorsement, certification, or conformance claim from them; the
`overt_receipt.json` entry these vectors exercise is OVERT-inspired and is
defined by `docs/specs/aep-profile-v1.md`, section 4.1.
