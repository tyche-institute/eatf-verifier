# Changelog

## v0.5.0 — how far the first-failure code depends on guard order (2026-07-27)

- Add `experiments/ordering`. `guard_probe.py` evaluates each guard
  independently on the same package by calling the shipped public components
  once each; no verifier source is modified. Over the 25 packages of the
  decision-path and path-shadowing corpora, with ten guards each: 3 packages
  have no rejecting guard and the verifier accepts all three, 15 have exactly
  one, and **7 have more than one**, so for 7 of the 22 rejected packages the
  first-failure code depends on which violated guard is reached first. Largest
  fault set: 3.
- Two sentinels gate every run and both caught real defects during
  development: the accepting controls must have empty fault sets, and the set
  of packages this probe rejects must coincide with the set the shipped
  verifier rejects.
- **A prediction fixed before the harness existed is refuted and recorded as
  refuted.** Order-dependence is not confined to packages touching an entry the
  signed receipt names as a witness; the general mechanism is that one
  byte-level fault propagates to every downstream guard whose inputs depend on
  those bytes.
- The directory also carries `run_experiment.py`, a repair-peeling harness that
  was built, run and then withdrawn on its own evidence: it counts repairs
  rather than guards, and for this artifact the two come apart.
- No verifier behaviour changed. Suites unaffected: 31 TypeScript, 45 Python.

## v0.4.1 — reproducible evidence for path shadowing (2026-07-27)

Supersedes v0.4.0, whose CLI dependency pins still named `@eatf/verifier`
0.3.0, so a clean `npm ci` from that tag could not resolve the workspace and
failed on every CI job. Use this tag. Contents are otherwise identical.


- Add `experiments/path-shadowing`: four cases in two matched pairs from one
  valid seed, demonstrating on the shipped verifiers that a negative control
  can be correctly rejected by both implementations, with identical verdicts
  and identical failure codes, and still never reach the decision state it was
  written to test. Expected outcomes were frozen in the experiment's oracle
  before the run; all four predictions held.
- Add `experiments/jcs-boundary`: the same discipline applied to two RFC 8785
  implementations this project depends on but did not write — `canonicalize`
  3.0.0 and `rfc8785` 0.1.4. Ten inputs at the declared domain boundary, each
  classed against the clause that governs it; five return different outcomes.
  `canonicalize` emits output for two lone-surrogate inputs where RFC 8785
  section 3.2.2.2 requires termination; `rfc8785` rejects 2^54, which is
  exactly representable and which section 3.1 permits. The two cases the RFC
  leaves undefined are marked as controls and credited to the specification
  author's own 2018 and 2021 issue reports.
- Both new runners are offline and byte-deterministic across consecutive runs.
- Correct the record for the v0.3.0 calibration pilot: its per-case output was
  never deposited and the cross-language behaviour it exposed has since been
  aligned, so the run cannot be reproduced from any public commit. The fix
  commit `1a73f19` and its diff remain the evidence that the divergence
  existed. `experiments/path-shadowing` supersedes the pilot as the
  reproducible evidence for path shadowing.
- No verifier behaviour changed. Existing suites unaffected: 31 TypeScript,
  45 Python.

## v0.3.0 — decision-path research release (2026-07-25)

- Add stable machine-readable `failureCode` / `failure_code` values to both
  verifier APIs and JSON command output.
- Align TypeScript and Python rejection of non-object metadata, incomplete or
  erroneous ML-DSA pairs, numeric OVERT coverage, and witness references.
- Add a fixed 21-case model-based decision-path oracle spanning two accepting
  controls and 16 distinct rejection states.
- Preserve deterministic generated packages, a calibration-pilot record,
  confirmatory JSON/CSV results, and SHA-256 manifests.
- Record 21/21 oracle matches and 21/21 TypeScript/Python verdict-and-code
  matches, with zero boolean or first-code mismatches.
- Extend regression coverage to 31 TypeScript and 45 Python tests.

## v0.2.0 — toolkit hardening (2026-07-25)

- Present the repository as one focused AEP toolkit: sign, inspect, dual
  verification, schemas, conformance vectors, examples, and tamper demo.
- Enforce RFC 3161 SHA-256 message-imprint equality and embedded CMS
  SignerInfo verification; remove mismatched-imprint compatibility acceptance.
- Add caller-supplied signer-key pinning to both libraries and CLIs.
- Bound archive, entry, and expanded sizes; reject duplicate or nested ZIP
  names before verifier extraction.
- Make current signer output bind both payload and metadata using the profile
  canonical form; retain response-only support solely for labeled legacy reads.
- Sign exact OVERT receipt bytes separately and place the required-signature
  marker inside signed metadata, preventing receipt-field tampering or
  signature-removal downgrade in current packages.
- Replace divergent handwritten JCS routines with maintained TypeScript and
  Python RFC 8785 implementations plus shared numeric/Unicode boundary tests.
- Add `eatf-sign --print-digest` so producers can request a timestamp for the
  exact payload-plus-metadata canonical digest.
- Compile both Draft 2020-12 schemas in tests and validate every positive
  conformance package against them.
- Replace every positive vector's timestamp with a matching TEST-ONLY RFC 3161
  response and add an auditable regeneration script.
- Add one-command workspace setup and a full sign/inspect/dual-verify/tamper
  smoke test.
- Prepare publishable npm workspace manifests and correct the Python PQC extra
  to use the official `liboqs-python` distribution.
- Remove obsolete wrappers, stub examples, hosted-platform assumptions, and
  the unrelated BKT demonstrator.

## v0.1.2 — documentation reconciliation (2026-07-23)

- Rewrite `docs/aep-format.md` to match the shipped verifier exactly (real
  entry names `signature.sig` / `signature_pqc.sig` + `pqc_public_key.pem`,
  `response.txt` required, `timestamp.tsr` required, hash-view rule).
- Correct the conformance-vector count everywhere: 4 valid + 7 invalid.
- Rewrite `lib/README.md` to describe the implemented verifier (drop unshipped
  ECDSA-P256 / manifest-envelope / RFC 5280 path-validation prose).
- `schemas/README.md` updated to the two shipped schemas.
- Test-vector READMEs no longer reference an unshipped generator script.
- Source comments point at `docs/aep-format.md` (the in-tree format summary).

## v0.1.1 — reviewer-facing fixes (2026-07-23)

- Remove the stale in-tree SDK mirror (`sdks/eatf-verifier-ts`).
- `bin/eatf-verify-ts`: CommonJS launcher + ESM implementation; exits 1 on
  invalid packages and 2 on usage errors (previously could exit 0 silently).
- Apache-2.0 across all manifests; versions unified at 0.1.1.
- Neutral issuer default; repository homepages.
- `verify-expected.txt` regenerated from the actual Python verifier output.

## v0.1.0 — initial public open-core release (2026-07-23)

First public release of the EATF Agent Evidence Package (AEP) reference
verifiers as an open, self-contained project under Apache-2.0.

- TypeScript verifier library (`lib/`) and offline verifier SDK.
- Independent Python verifier (`lib-python/`).
- Offline CLIs: `eatf-verify`, `eatf-sign`, `eatf-inspect` (no network, no keys).
- JSON Schemas for the AEP package, claims, and OVERT receipt.
- Conformance test-vectors: 4 valid + 7 invalid (negative controls).
- Worked examples (minimal sign+verify, RFC 3161 timestamp, batch, private CA).
- Hybrid RSA-4096 + ML-DSA-65 (FIPS 204) signatures; RFC 3161 timestamps
  (structural verification).

Tests: Python 23/23, TypeScript 19/19.
