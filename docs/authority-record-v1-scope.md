# Root verifier and the authority-record corpus

The root toolkit (`lib/`, `lib-python/`, 0.7.3) and the frozen study artifact in
[`artifacts/authority-record-v1/`](../artifacts/authority-record-v1/) (its own
TypeScript library and Python 0.2.1, frozen on 2026-08-13) are two lines of
one verifier. They share an author and a corpus. Agreement between them is a
consistency check, not independent validation.

The root verifier rejects every package that the artifact's 58-vector corpus
marks `verify=true`. This page states why, with the bytes, and what each line's
verdict on that corpus means.

## Summary

- **Cause: the corpus's timestamp tokens, judged by two different contracts.**
  Every RFC 3161 token in the corpus (57 of 58 vectors carry one that parses)
  has no embedded TSA certificate, and none has its imprint over
  `hash.sha256`, which is what both lines compare it with. The imprint is the
  SHA-256 of an RSA signature value: the package's own `signature.sig` in 6
  vectors, and that of `valid/valid-overt-profile` in the other 51. The
  frozen line treats an imprint mismatch as advisory ("accepted for Java
  reference compatibility") and a SignerInfo without a certificate as not
  determinable, so it accepts. The root line has required imprint equality
  and a verified SignerInfo since v0.2.0 (commit `902d338`, 2026-07-25), so it
  rejects at the timestamp: `TSA_IMPRINT_MISMATCH`, or
  `TSA_IMPRINT_UNVERIFIABLE` for the one SHA-512 imprint. Neither line misreads
  the bytes.
- **Not one vector: all 32 `verify=true` vectors.** The 26 `verify=false`
  vectors agree on the verdict, but 17 of them agree for a different reason
  (see the control run).
- **Scope.** The root line does not implement the authority-record checks of
  the artifact's profile (§4.2 warrant, §4.3 accepting authority, §4.5
  mandate). With valid tokens it accepts the 17 vectors those checks reject.
- **Two latent defects in the frozen line** (recorded below, not changed:
  the artifact is frozen and checksummed). Its TypeScript verifier cannot
  verify the SignerInfo of any certificate-bearing token, and its two
  implementations compute the imprint differently.
- **Two root Python defects, fixed here.** It did not compare the signed
  message-digest attribute with the TSTInfo, so a token's genTime or imprint
  could be edited after signing. It also reported a non-SHA-256 imprint as a
  mismatch where TypeScript reports it as not determinable.

## The bytes of `valid/mandated-action`

| Field | Value |
|---|---|
| `hash.sha256` = SHA-256(`canonical.bin`) | `0f7368ea2f391c4c7715423a4ba40d6274ddc14bdb061715d70fe93d2f84ec8f` |
| Token `messageImprint` (SHA-256) | `289d4b68c3d6763a624853c2a1a077168ede2f4cce1f118efd1ed8d0626a811a` |
| SHA-256 of the ASCII hex of `hash.sha256` | `69ddf37bbb971f2267f4336d71ad3417ba07e3c67efd1ed51405e9df3010a9db` |
| Same, with the trailing LF | `c3461c760023a33ec905c8252e329b4a801bc6c0f8f18dc4b9b1252b2d9fe03f` |
| Token genTime, policy | `2026-01-01T00:00:00Z`, `1.2.3.4.5.6` |
| Embedded certificates | 0 |
| SHA-256 of the token DER | `ab57489acb964ffd271ce3d84d39e61919a9f9eb4d156ad209ac352de0bc715d` |

The imprint matches neither reading of `hash.sha256`. The same token DER sits
in 52 of the 58 vectors: the mandate, acceptance, voiding, warrant and
profile-canonical generators in `artifacts/authority-record-v1/scripts/` copy
it "verbatim from valid-overt-profile/package.aep", and the boundary and
invalid generators start from packages that already carry it. One vector carries a
copy with the imprint algorithm changed to SHA-512
(`boundary/not-determinate-imprint-alg`), four carry two other certificate-less
tokens, and `invalid/bad-timestamp` carries none. The imprint `289d4b68…`
matches no `hash.sha256` in this repository's history either: on 2026-10-22,
of the 138 `.aep` blobs reachable from `git rev-list --all`, 134 carry a
`hash.sha256`; none of their 41 distinct values produces it under any of the
three readings above (the 32 bytes, the ASCII hex, the ASCII hex with LF).

What the imprint does match is the SHA-256 of the base64-decoded
`signature.sig` of `valid/valid-overt-profile`, an RSA signature value that
`invalid/tampered-overt-receipt` shares. Time-stamping the signature value is
a common convention, but neither line nor the profile's §7 compares the
imprint with it. Six vectors carry a token over their own `signature.sig`:
those two and the four that carry the two other tokens. The other 51 carry a
token over another package's signature. `lib-python/tests/test_authority_record_scope.py`
pins this split.

The root `test-vectors/` went through the same history differently: on
2026-07-25 `scripts/regenerate-test-timestamps.py` re-stamped them with the
TEST-ONLY TSA in `test-vectors/keys/`, and each now carries a token whose
imprint equals its `hash.sha256`. The artifact was frozen from code that
kept the older tokens.

## Three imprint readings

| Line | Imprint compared with | Mismatch | No TSA certificate |
|---|---|---|---|
| Root TypeScript and Python 0.7.3 ([`aep-format.md`](aep-format.md) step 9) | the 32 bytes of `hash.sha256` | rejects | rejects (`TSA_CERT_MISSING`) |
| Artifact TypeScript ([profile spec](../artifacts/authority-record-v1/docs/specs/aep-profile-v1.md) §7) | SHA-256 of the ASCII hex of `hash.sha256` | reports, accepts | not determinable, accepts |
| Artifact Python 0.2.1 | the 32 bytes of `hash.sha256` | reports, accepts | not determinable, accepts |

A token re-issued over the 32 bytes of `hash.sha256` matches for the root
lines and for artifact Python; a token re-issued over the ASCII hex matches
only for artifact TypeScript. Both were tried on `valid/mandated-action`.

## Control run: replace only `timestamp.tsr`

`scripts/authority-record-crosscheck.py` copies the corpus and replaces only
`timestamp.tsr` in each package with a token from the TEST-ONLY TSA in
`test-vectors/keys/dev-tsa-rsa-3072`. The token is issued over the package's
`hash.sha256` and copies genTime, serial number and policy from the original,
so time-dependent appraisals see the same inputs. Every other ZIP entry stays
byte-identical.

- The root lines then accept `valid/mandated-action`: the token was the only
  reason they rejected it. `lib-python/tests/test_authority_record_scope.py`
  pins this.
- The root lines accept 17 vectors that the frozen line rejects on a
  `mandate.json`, `warrant.json` or acceptance check: class S below.
- Frozen TypeScript then rejects all 32 vectors it accepted before, with
  "RFC 3161 SignerInfo signature did not verify against the embedded cert."
  It passes the TSTInfo bytes to PKIjs as the timestamped data, and PKIjs
  compares the token's imprint with a digest of that data, so no genuine
  token can pass. Root commit `902d338` fixed this in `lib/src/tsa.ts` by
  passing `canonical.bin`; the artifact kept the earlier code. Class D.

## What each verdict means

- The frozen line reproduces the measurements of *Valid Is a Floor, Not a
  Ceiling*: run it on its own corpus, as its README says. Its `valid: true`
  on these vectors includes a failed, non-enforced imprint check.
- A root verdict on this corpus says nothing about §4.2, §4.3 or §4.5. With
  the shipped tokens the root lines reject every vector at the timestamp;
  with valid tokens they check the envelope only.
- A corpus that both lines accept would need re-issued tokens and a fixed
  SignerInfo call in the artifact's TypeScript, which is a new artifact
  version, not an edit of this one.

## Reproduce

```bash
npm ci && npm run build
(cd artifacts/authority-record-v1/lib && npm ci && npm run build)
python3 -m venv /tmp/xc && /tmp/xc/bin/pip install "cryptography>=49" "asn1crypto>=1.5" "rfc8785>=0.1.4,<0.2"
/tmp/xc/bin/python scripts/authority-record-crosscheck.py
```

Use an interpreter without `eatf-verifier` installed, or one where both
Python lines resolve from their source trees: the script runs each line in a
subprocess with `PYTHONPATH` set to that line and stops if another install
shadows it. It exits 1 if any vector is unexplained.

## Table

Generated by `scripts/authority-record-crosscheck.py` on 2026-10-22. "Imprint
over `hash.sha256`" is read from the token by the script, not by a verifier.
Classes:

- **T** — the shipped token's imprint is not over `hash.sha256`; root rejects
  at the timestamp, the frozen line accepts.
- **S** — root does not implement §4.2/§4.3/§4.5; seen in the control run.
- **D** — frozen TypeScript cannot verify a certificate-bearing token.
- **E** — no disagreement; all four reject on the same envelope check.

| Vector | Expected | Imprint over `hash.sha256` | root-py | root-ts | ar-py | ar-ts | root-py (control) | root-ts (control) | ar-py (control) | ar-ts (control) | Class |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `acceptance/acceptance-digest-mismatch` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `acceptance/acceptance-principal-substitution` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `acceptance/acceptance-signature-forged` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `acceptance/acceptance-stripped` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `boundary/advisory-fail-imprint` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `boundary/boundary-suppressed-tsa` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `boundary/claimed-surface-overclaim` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `boundary/not-determinate-imprint-alg` | true | no | false `TSA_IMPRINT_UNVERIFIABLE` | false `TSA_IMPRINT_UNVERIFIABLE` | true | true | true | true | true | false | T, D |
| `boundary/reauthored-package-issuer-substitution` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `boundary/response-only-unsigned-policy-tamper` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `boundary/short-circuit-shadow` | false | no | false `HASH_MISMATCH` | false `HASH_MISMATCH` | false | false | false `HASH_MISMATCH` | false `HASH_MISMATCH` | false | false | E |
| `invalid/bad-signature-classical` | false | no | false `RSA_SIGNATURE_INVALID` | false `RSA_SIGNATURE_INVALID` | false | false | false `RSA_SIGNATURE_INVALID` | false `RSA_SIGNATURE_INVALID` | false | false | E |
| `invalid/bad-timestamp` | false | no | false `TSA_MISSING_OR_INVALID` | false `TSA_MISSING_OR_INVALID` | false | false | false `TSA_MISSING_OR_INVALID` | false `TSA_MISSING_OR_INVALID` | false | false | E |
| `invalid/missing-canonical-bin` | false | no | false `REQUIRED_ENTRY_MISSING` | false `REQUIRED_ENTRY_MISSING` | false | false | false `REQUIRED_ENTRY_MISSING` | false `REQUIRED_ENTRY_MISSING` | false | false | E |
| `invalid/profile-form-policy-rewrite` | false | no | false `CANONICAL_FORM_MISMATCH` | false `CANONICAL_FORM_MISMATCH` | false | false | false `CANONICAL_FORM_MISMATCH` | false `CANONICAL_FORM_MISMATCH` | false | false | E |
| `invalid/tampered-canonical-bin` | false | no | false `CANONICAL_FORM_MISMATCH` | false `CANONICAL_FORM_MISMATCH` | false | false | false `CANONICAL_FORM_MISMATCH` | false `CANONICAL_FORM_MISMATCH` | false | false | E |
| `invalid/tampered-metadata` | false | no | false `OVERT_INVALID` | false `OVERT_INVALID` | false | false | false `OVERT_INVALID` | false `OVERT_INVALID` | false | false | E |
| `invalid/tampered-overt-receipt` | false | no | false `OVERT_INVALID` | false `OVERT_INVALID` | false | false | false `OVERT_INVALID` | false `OVERT_INVALID` | false | false | E |
| `invalid/untrusted-issuer` | false | no | false `RSA_SIGNATURE_INVALID` | false `RSA_SIGNATURE_INVALID` | false | false | false `RSA_SIGNATURE_INVALID` | false `RSA_SIGNATURE_INVALID` | false | false | E |
| `mandate/mandate-digest-mismatch` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `mandate/mandate-expired` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `mandate/mandate-out-of-scope` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `mandate/mandate-principal-substitution` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `mandate/mandate-reference-only` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `mandate/mandate-signature-forged` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `mandate/mandate-stripped` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `mandate/mandate-subject-swap` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `mandate/mandate-unbound` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `valid/co-located-authority` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/mandated-action` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/mandated-and-accepted` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/mandated-denied-action` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/mcp-tools-call-denied-policy` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/mcp-tools-call-valid` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/minimal-roundtrip` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/profile-canonical` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/valid-overt-profile` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/voided-and-authorized` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `valid/warranted-action` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `voiding/acceptance-policy-mismatch` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `voiding/authority-key-substitution` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `voiding/diverged-registry-status` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `voiding/expired-acceptance` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `voiding/forward-dated-withdrawal` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `voiding/missing-snapshot-input` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `voiding/response-only-with-authority` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `voiding/stale-telemetry` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `voiding/tampered-acceptance` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `voiding/unknown-voiding-type` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `voiding/voided-registry-at-signing` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `warrant/warrant-acceptance-forged` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `warrant/warrant-acceptance-stripped` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `warrant/warrant-decision-void` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `warrant/warrant-digest-mismatch` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `warrant/warrant-inapplicable-action` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `warrant/warrant-stale` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |
| `warrant/warrant-swap` | false | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | false | false | true | true | false | false | S |
| `warrant/warrant-unbound` | true | no | false `TSA_IMPRINT_MISMATCH` | false `TSA_IMPRINT_MISMATCH` | true | true | true | true | true | false | T, D |

Verdicts equal to verify-expected.txt (shipped): root-py 26/58, root-ts 26/58, ar-py 58/58, ar-ts 58/58.
Verdicts equal to verify-expected.txt (re-stamped): root-py 41/58, root-ts 41/58, ar-py 58/58, ar-ts 26/58.
Classes: D 32, E 9, S 17, T 32.
Unexplained disagreements: 0.
