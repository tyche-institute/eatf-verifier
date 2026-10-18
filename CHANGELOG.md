# Changelog

> **Terminology note.** Entries below use "OVERT receipt" as shorthand for the
> `overt_receipt.json` package entry. OVERT is an open standard published by
> Glacis Technologies, Inc. (https://overt.is); this project is independent of
> them, carries no endorsement or certification by them, and the entry is
> OVERT-inspired rather than claimed to be OVERT-conformant. See
> [README](README.md#overt-attribution-and-non-endorsement). Historical entries
> are left unedited so that the release record stays accurate.

## v0.7.1 — malformed ML-DSA entries are rejected, not crashed on (2026-10-18)

- **Fix both verifiers crashing on malformed ML-DSA entries instead of
  rejecting the package.** A `signature_pqc.sig` that is not base64 made
  `eatf-verify` exit 2 with a stack trace and `eatf-verify-py` exit 1 with a
  traceback and no JSON. A `pqc_public_key.pem` that neither parser can load,
  such as an RSA SubjectPublicKeyInfo or text that is not PEM, gave
  `PQC_VERIFY_ERROR` in TypeScript but crashed the Python verifier. v0.7.0 and
  earlier are affected, with or without `--pqc-signer-key`. Both verifiers now
  return `valid: false` with `pqcValid: false`: the new code
  `PQC_SIGNATURE_ENCODING`, which mirrors `RSA_SIGNATURE_ENCODING`, when the
  signature does not decode, and `PQC_VERIFY_ERROR` when the key cannot be
  used. The signature encoding is checked after the optional key pin and
  before the signature. Without a pin, a package with both an undecodable
  signature and an unusable key fails with `PQC_SIGNATURE_ENCODING`. With a
  pin, the pin check reports the key first (`PQC_VERIFY_ERROR` or
  `PQC_SIGNER_NOT_TRUSTED`, with `pqcValid: null`).
- **The Python verifier accepted an ML-DSA signature with a stray character in
  it.** Its lenient base64 decoder skipped bytes outside the alphabet, so a
  valid signature with one `!` inserted still verified, while TypeScript
  crashed on the same package. Both verifiers now apply one byte-level rule to
  `signature_pqc.sig`: TAB, LF, VT, FF, CR and space may appear anywhere, and
  the remaining bytes must be base64 with at most two trailing `=` and a length
  that is a multiple of four. Under that rule TypeScript also rejects a leading
  byte-order mark or a non-breaking space, which it used to accept, and both
  reject missing padding, which TypeScript reported as `PQC_SIGNATURE_INVALID`
  and Python crashed on. Signatures written by `eatf-sign` are unaffected,
  including ones re-wrapped at 64 columns.
- **An empty ML-DSA entry now counts as present in Python, as it already did
  in TypeScript.** Python treated a zero-byte `signature_pqc.sig` or
  `pqc_public_key.pem` as missing. An empty pair added to a classical-only
  package therefore verified in Python and failed in TypeScript, and an empty
  key next to a signature gave `PQC_PAIR_INCOMPLETE` in Python and
  `PQC_VERIFY_ERROR` in TypeScript. Both now return `PQC_VERIFY_ERROR`.
- When its `cryptography` backend has no ML-DSA support (OpenSSL builds older
  than 3.5), the Python verifier now returns `PQC_SUPPORT_UNAVAILABLE` with
  `pqcValid: null` instead of crashing.
- Not changed here: without a key pin, the two key parsers still disagree on
  some malformed spellings of `pqc_public_key.pem` that only one of them can
  load. For example, a bare base64 key without PEM armour verifies in Python
  and fails with `PQC_VERIFY_ERROR` in TypeScript.
- Regression tests built from the lab packages are in
  `lib/test/pqc-malformed.test.ts` and `lib-python/tests/test_pqc_malformed.py`,
  with the same cases in both; the signature cases run with and without a key
  pin. The conformance corpus (5 verified, 8 rejected), the 42 lab
  observations and the 21 decision-path cases give the same results as
  before.
- All npm workspaces and the Python package are 0.7.1, and `eatf-verify`,
  `eatf-sign` and `eatf-inspect --version` report 0.7.1.

## v0.7.0 — ML-DSA-65 signer-key pin and counted conformance (2026-10-18)

- **Fix `eatf-verify-py --conformance` on native Windows, which checked no
  vectors and passed.** It classified vectors by a `valid/` or `invalid/`
  string prefix, but `os.walk` joins paths with backslashes on Windows, so
  nothing matched. The run printed "Conformance: 0 verified, 0 rejected, 0
  contract mismatches." and exited 0. That is what the `windows-latest` CI job
  has printed since the step was added for v0.2.0 (run 30170210404, 25 July
  2026), next to the TypeScript line with the full count. The verifier itself
  was never affected: run one package at a time on Windows, it accepts the 5
  valid vectors and rejects the 8 invalid ones. The runner now compares path
  components.
- `--conformance` in both CLIs now exits 2 when it finds no vectors under
  `valid/` or `invalid/`, for example with a wrong root, a category directory
  or an empty tree. `eatf-verify-py` also exits 2 for a missing directory, as
  `eatf-verify` already did. A run that checked nothing no longer reads as a
  pass.
- The TypeScript CLI was not affected, because it builds its own paths with
  `/`. It now uses the same path-component comparison, so a future change to
  path joining cannot reintroduce the bug.
- CI now checks the conformance summary line ("5 verified, 8 rejected, 0
  contract mismatches") for both CLIs on Linux, macOS and Windows, not just the
  exit code. Regression tests are in `lib-python/tests/test_cli.py` and
  `cli/eatf-verify/test/conformance.test.mjs`; the latter now runs as part of
  `npm test`.
- The decision-path and ordering experiments now write POSIX paths into
  `SHA256SUMS` and `results.json` on every platform.
- **Fix the ordering experiment, which ran on a partial corpus and exited 0.**
  `experiments/ordering/run_experiment.py` and `guard_probe.py` analysed
  whatever packages they found. The four path-shadowing packages are not
  committed and exist only after `python
  experiments/path-shadowing/run_experiment.py`, so on a fresh clone both
  scripts analysed 21 packages instead of the 25 that the v0.5.0 figures
  cover. They rewrote their output in `experiments/ordering/generated/` without
  the `naive-*` and `refined-*` rows and exited 0. Both sentinels in
  `guard_probe.py` passed on the smaller set, because they check consistency,
  not coverage. Both scripts now take the case ids from
  `experiments/decision-path/oracle.json` and
  `experiments/path-shadowing/oracle.json`. If any declared package is missing,
  they exit 1 before writing anything and name the missing cases and the
  command that restores or produces them. The deposited results are unchanged:
  with all 25 packages present, both scripts reproduce the committed CSV files.
- **Fix: the ML-DSA-65 key was not pinned.** Through v0.6.1, `--signer-key` /
  `trustedSignerPems` / `trusted_signer_pems` covered only `public_key.pem`
  (RSA). `pqc_public_key.pem` was taken from the package itself, and nothing
  else in the package authenticates it. Replacing only `signature_pqc.sig`
  and `pqc_public_key.pem` with an unrelated ML-DSA-65 key's signature over
  the same `canonical.bin` was accepted by both verifiers with `valid=true`
  and `pqcValid=true`, under `if-present` and `--require-pqc`, and with the
  RSA key pinned. `--require-pqc` proved that an ML-DSA-65 signature existed,
  not whose key made it. Against a forger of the RSA half, the PQC half added
  nothing.
- Add an optional caller-supplied ML-DSA-65 key pin: `--pqc-signer-key <PEM>`
  in both CLIs (repeatable), `trustedPqcSignerPems` in TypeScript and
  `trusted_pqc_signer_pems` in Python. Pins are RFC 9881 SPKI or legacy
  raw-key PEM and are compared on the decoded 1952-byte FIPS 204 key, so an
  SPKI pin matches the same key in legacy raw-key form. Each pin must be
  exactly one PEM block, and both verifiers parse PEM text by the same rules;
  repeat the flag for several keys. A mismatch fails with the new code
  `PQC_SIGNER_NOT_TRUSTED`, before the ML-DSA signature is checked.
- A PQC pin implies the `required` policy: a package without an ML-DSA pair
  fails with `PQC_SIGNATURE_REQUIRED` even under `if-present`, so a
  classical-only package cannot bypass the pin. A pin that is not an ML-DSA-65
  public key makes the libraries throw (`ValueError` in Python) and the CLIs
  exit with status 2.
- Both CLIs print a warning to stderr when `--require-pqc` is used without
  `--pqc-signer-key`. Exit status and `--json` stdout do not change. Reports
  now say when ML-DSA-65 signer identity was not evaluated.
- Add the deterministic negative package `07-foreign-mldsa-key.aep` to the
  PQC lab, made from a second public seed, and a third lab policy, `pinned`
  (`--require-pqc` plus both signer keys, shipped under `keys/`). The lab now
  replays 42 observations: 7 packages × 3 policies × 2 verifiers. The
  v0.6.1 24 (packages 01–06 under `transitional` and `required`) are
  unchanged, and packages 01–06 and both corpus vectors are byte-identical.
  Only package 07 under `pinned` changes verdict.
- Publish `test-vectors/keys/dev-mldsa65.pem`, the public key of the
  workshop ML-DSA-65 signer. The shared conformance corpus is unchanged at 5
  accepted and 8 rejected packages.
- When a `--signer-key`, `--pqc-signer-key` or `--tsa-trust-list` file cannot be
  read, `eatf-verify-py` now exits 2 with a one-line message instead of 1
  with a traceback, and `eatf-verify` prints a one-line message instead of a
  stack trace.
- **Fix:** in v0.6.0 and v0.6.1 the ML-DSA-65 PEM parser could take cubic
  time on a crafted `pqc_public_key.pem`, a long whitespace run without an END
  line, because its pattern had three adjacent whitespace quantifiers. The
  TypeScript verifier ran it on every package with an ML-DSA pair. The pattern
  now has one body group and runs in linear time; it accepts the same PEM text
  as before.
- `eatf-verify` now exits 2 with "option X requires a value" when `--batch`,
  `--conformance`, `--signer-key`, `--pqc-signer-key` or `--tsa-trust-list` is
  the last argument. Before, a trailing `--batch` or `--conformance` was
  ignored and the other paths were verified.
- `examples/05-hybrid-mldsa65` now verifies with both signer keys pinned.
- All npm workspaces and the Python package are 0.7.0. `eatf-verify --version`
  reported 0.6.0 and `eatf-sign` / `eatf-inspect --version` reported 0.3.0; all
  three now report 0.7.0.

## v0.6.1 — portable conference download (2026-08-02)

- Include `run_lab.py` and `run.sh` in the deterministic conference ZIP so the
  downloaded six-package corpus can be replayed directly after one-time
  verifier setup.
- Let the runner locate a prepared checkout through `EATF_REPO_ROOT` or the
  installed command `PATH`, while preserving its repository-local behavior.
- Correct the quick start so downloaded-package commands no longer point back
  to repository copies.
- Add a CI check that extracts the built ZIP, verifies every listed SHA-256
  value, and replays all 24 cross-language policy observations from the
  extracted files.

## v0.6.0 — public hybrid ML-DSA-65 and downgrade lab (2026-08-02)

- Add hybrid RSA-4096 + ML-DSA-65 signing to the TypeScript library and
  `eatf-sign`, with RFC 9881 SubjectPublicKeyInfo output.
- Upgrade `@noble/post-quantum` to 0.6.1 and use `cryptography>=49` as the
  Python FIPS 204 backend, a third-party library separate from the TypeScript
  side's `@noble/post-quantum`. The positive vector is accepted by both
  implementations.
- Add explicit `if-present` and `required` PQC verification policies and the
  `--require-pqc` CLI flag in both languages.
- Expand the conformance corpus to 5 accepted and 8 rejected packages with a
  positive hybrid vector and a one-bit ML-DSA negative control.
- Add a deterministic six-package offline lab covering valid hybrid,
  ML-DSA tamper, pair stripping, legitimate classical transition, incomplete
  pair, and payload tamper paths under both policies.
- Add 45-, 60-, and 90-minute facilitator run sheets, checksums, an annotated
  no-network transcript, and a deterministic downloadable workshop bundle.
- Add a one-page PQC archive-migration worksheet in Markdown, HTML, and PDF.
- Reject unknown PQC policy values instead of silently treating them as the
  transition policy, and align the Python runtime version with the release.

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
- Python verifier (`lib-python/`), a second implementation by the same authors.
- Offline CLIs: `eatf-verify`, `eatf-sign`, `eatf-inspect` (no network, no keys).
- JSON Schemas for the AEP package, claims, and OVERT receipt.
- Conformance test-vectors: 4 valid + 7 invalid (negative controls).
- Worked examples (minimal sign+verify, RFC 3161 timestamp, batch, private CA).
- Hybrid RSA-4096 + ML-DSA-65 (FIPS 204) signatures; RFC 3161 timestamps
  (structural verification).

Tests: Python 23/23, TypeScript 19/19.
