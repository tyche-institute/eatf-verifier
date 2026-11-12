# Mutation adequacy of the deposited negative cases: protocol

Fixed on 2026-11-12, before any mutant was generated or executed. This text is
not edited after execution. Anything that changes once runs begin is recorded,
dated, under "Deviations" at the end.

## Question

The decision-path and path-shadowing experiments judge a negative case by the
state it reaches. This experiment asks the question from the other side: do the
deposited cases detect faults placed in the verifier, and which oracle keeps
that detection?

- **RQ-M1.** How many tool-generated mutants of each port are killed under a
  verdict-only oracle, a verdict-and-code oracle and a target-state oracle?
- **RQ-M2.** Which guards can be removed completely without any oracle noticing?
- **RQ-M3.** Does deleting a case's target guard separate the two naive
  path-shadowing cases from the refined ones? Does a mutation score?

## Subject

eatf-verifier `v0.5.0`, commit `b8240fda1349b4823928cd19159acbd4e22121f7`.

| Port | Files mutated |
|---|---|
| Python | `lib-python/eatf_verifier/verifier.py`, `overt.py`, `tsa.py` |
| TypeScript | `lib/src/verifier.ts`, `overt.ts`, `tsa.ts` |

These are the guard logic: the decision procedure and the two parsers whose
results it acts on. `guard-regions.json` records the SHA-256 of each file, and
the runner refuses to start if any file differs. The other modules are outside
the subject:

- `canonical`, `hash` and `rsa` are thin wrappers over library primitives. A
  fault there breaks the accepting cases and says nothing about the negatives.
- `mldsa` is never called, because no case carries a complete ML-DSA pair.
- `signer`, the command-line tools, `browser`, `index` and the TSA trust-list
  data are not on the verification path.

## Tools

- **Python:** mutmut 3.8.1, run with Python 3.12.3 and pytest 9.1.1 in a clean
  virtual environment. The full freeze is in `work/pip-freeze.txt` and is copied
  to `generated/`.
- **TypeScript:** StrykerJS 9.6.1 with the command test runner, run with Node
  v22.22.3. The TypeScript compiler comes from the toolkit's own lockfile, and
  Stryker is pinned in `stryker/package-lock.json`.

Each tool runs with its default mutation operators. No operator is disabled and
no mutant is removed by hand. The configuration sets only what the setup needs:

- **mutmut:** the three files to mutate, the test directory, and
  `use_git_change_detection = false`.
- **Stryker:** the three files to mutate, the build command, and
  `coverageAnalysis: "off"`, which the command runner requires.

## Suite under test

The suite is the 25 named cases as deposited: 21 in
`experiments/decision-path/oracle.json` and 4 in
`experiments/path-shadowing/oracle.json`.

- The decision-path packages are tracked in git.
- The runner regenerates the four path-shadowing packages with that
  experiment's own `build()` and checks them against the SHA-256 values in its
  `results.json`.

Some named cases share a package:

- `overt-signature-missing` and `refined-remove-receipt-signature` are the same
  package, and so are `timestamp-empty` and `refined-empty-timestamp`.
- `accept-profile`, `accept-profile-with-signer-pin` and `signer-pin-mismatch`
  are one package, verified under three invocations.

So the 25 named cases are 23 distinct (package, invocation) pairs over 21
distinct packages. Of the 23 rejected named cases, 21 are distinct. All 25 cases
are kept. Counts of cases are reported both as named and as distinct.

## Observation

For each program and case, the harness records one of two things:

- the pair (`valid`, failure code) returned by `verify`;
- the type of the exception raised.

It never reads the failure reason or the report.

## Oracles

For case *c*, the expected verdict and code are:

- for decision-path cases, `expected_valid` and `expected_code`;
- for path-shadowing cases, `false` and `predicted_observed_code`.

The target code is `expected_code` for decision-path cases and `targets_state`
for path-shadowing cases.

| Oracle | Holds on *c* when |
|---|---|
| O_V, verdict only | observed `valid` equals the expected verdict |
| O_C, verdict and code | observed (`valid`, code) equals the expected pair |
| O_T, target state | observed code equals the target code |

When the two unmutated ports agree, as the deposited results show, O_V is what
a boolean cross-port differential checks and O_C is what a code-level
differential checks.

- **Applicable cases.** S_O is the set of cases on which oracle O holds for the
  unmutated program. A case outside S_O is never counted as killing a mutant
  under O.
- **Kill.** A mutant is killed under O in either of two situations:
  - it raises on any case, times out, or fails to load;
  - O fails on some case in S_O.
- **Fail-closed variant O_V^fc.** An exception on a case is read as a rejection
  (`valid = false`). Timeouts and load failures still kill.
- **Load failures.** A mutant that fails before any case is evaluated is killed
  under every oracle, and that kill is attributed to no case.
- **Tool status mapping.**
  - Killed: mutmut `killed`, `timeout` and `segfault`; Stryker `Killed`,
    `Timeout` and `RuntimeError`.
  - Survived: mutmut `survived` and `no tests`; Stryker `Survived` and
    `NoCoverage`.
  - Excluded from every score, with the count reported: compile errors and
    anything else.
- **Equivalent mutants.** These are not identified by hand. Every oracle is
  scored over the same denominator, so equivalent mutants lower all scores
  alike and do not bias the differences between oracles.

## Mutant sets

1. **Tool mutants.** Everything mutmut and Stryker generate for the subject
   files.
2. **Guard deletions.** Eleven guards per port, defined in `guard-regions.json`:
   - Python: each `return _fail(...)` that carries one of the guard's codes is
     replaced by `pass`. For `1-zip`, the archive limit checks that raise
     `ValueError` are also replaced by `pass`.
   - TypeScript: the same, with `{}` in place of the statement and
     `// @ts-nocheck` prepended to the file.
   - A deletion leaves the rest of the program intact, so a case whose target
     guard is deleted reaches whatever comes next.

Each tool mutant is placed in a region of `guard-regions.json` by the first
original line it changes.

## Measures

- **Per port and oracle:** mutants generated, excluded, killed and survived,
  and the mutation score (killed / (generated - excluded)).
- **Per region:** the same counts.
- **Per case:** kills under each oracle, unique kills, and kills inside the
  case's own target region.
- **Per guard deletion:** detected or not under O_V, O_V^fc, O_C and O_T, and
  for every case, whether its observed state changed.
- **Gap without code literals.** The O_C minus O_V gap is reported twice: once
  for all mutants, and once without the mutants that only change a
  failure-code literal, since O_V cannot see those by construction.

## Sentinels

Each sentinel stops the analysis until its failure is explained.

1. On the unmutated program, both ports reproduce the deposited codes in
   `experiments/decision-path/generated/results/results.csv` and
   `experiments/path-shadowing/generated/results.csv`.
2. Each harness asserts O_C on all 25 cases. For every executed mutant, the
   tool's own killed or survived status must equal our O_C kill, recomputed
   from the recorded outcomes. Timeouts are taken from the tool.
3. kills(O_V) ⊆ kills(O_C) and kills(O_T) ⊆ kills(O_C). Given P1, both hold by
   construction, so they check the harness and the analysis, not the verifier.

## Predictions

Fixed before execution.

- **P1. Unmutated programs.** In both ports, O_V and O_C hold on 25 of 25
  cases. O_T holds on 23 of 25: it fails only on
  `naive-remove-receipt-signature` and `naive-empty-timestamp`. Python and
  TypeScript agree on (`valid`, code) for all 25.
- **P2. Guard deletion, in each port.**
  - Under O_V, the deletions of `3-metadata`, `4-canonical-form`, `5-digest`
    and `8a-overt-crosscheck` go undetected.
  - Under O_V, the deletions of `1-zip`, `2-required-entries`, `6-signer-pin`,
    `7-rsa`, `8b-receipt-signature`, `9-pqc` and `10-12-timestamp` are
    detected. `2-required-entries` is detected only through an exception, so
    it goes undetected under O_V^fc.
  - Under O_C and O_T, all 11 deletions are detected.
- **P3. Deleting the target guard.**
  - Deleting a case's target guard changes the observed state of each of the
    21 rejected cases on which O_T holds.
  - It changes neither naive case.
  - Deleting `8a-overt-crosscheck` changes both naive cases.
- **P4. The verdict-only gap.** In each port, kills(O_V) is a strict subset of
  kills(O_C), and the difference is at least 10% of kills(O_C).
- **P5. Kills by target region, in each port.**
  - (a) Neither naive case kills, under O_V or O_C, any tool mutant located in
    its target guard's region.
  - (b) Each of the 21 rejected cases on which O_T holds kills, under O_C, at
    least one tool mutant located in its target guard's region.

Exploratory analyses carry no prediction:

- kill rates by mutation operator;
- a comparison of region scores across the two ports;
- failure codes defined in the source against codes reached by the suite;
- O_V^fc on tool mutants.

## Order of execution

1. Commit this protocol and `guard-regions.json`.
2. Build the harnesses. Run them on the unmutated programs to check P1 and
   sentinel 1.
3. Run the guard deletions.
4. Run mutmut, then Stryker.
5. Run `analyse.py`, which writes `generated/` with `SHA256SUMS` and
   `SUMMARY.md`.

A refuted prediction is reported as refuted. It is not repaired by changing a
definition above.

## Deviations

None recorded at the time of fixing.

The entries below were added on 2026-11-12, during and after execution. None
changes a definition, an oracle, a prediction or the mutant sets above.

1. **Python environment, before any harness ran.** The first virtual
   environment could see the system site packages. It was deleted and rebuilt
   without them, with the versions now in `work/pip-freeze.txt`.
2. **Malformed results, before any harness ran.** This clarifies
   "Observation". Both harnesses record a result as the exception
   `MalformedResult(...)` when its verdict is not a boolean or its code is
   neither a string nor absent. Without this, the two ports would have
   recorded such results differently. It affects 2 Python and 4 TypeScript
   mutants.
3. **Deletion control, before the deletion stage ran.** The runner also puts
   an unmodified copy of each port through the same copy, compile and harness
   steps as the deletions. In both ports the control's observations equal the
   baseline.
4. **Stryker build, first Stryker attempt.** StrykerJS 9.6.1 runs the build
   command before it links `node_modules` into its sandbox, so the first
   attempt stopped at the build (`tsc: not found`, exit 127) before any mutant
   ran. The build command is now `stryker/build-sandbox.sh`, which links the
   original checkout's `node_modules` into the sandbox and then builds, and
   `symlinkNodeModules` is false. The reported run is the second attempt.
5. **Run settings the protocol does not name.**
   - mutmut ran with `--max-children 10`, and its configuration names the
     three files through `source_paths` and `only_mutate`.
   - Stryker ran with concurrency 8 and its sandbox under `work/stryker-tmp`.
     `work/` and `generated/` were excluded from the sandbox copy, and the JSON
     report went to `work/stryker/mutation.json`.
   - None of these settings changes the mutant set or the operators.
6. **Analysis, written after the runs.**
   - The two clauses of the kill rule are read together. A mutant that raises
     on any case is killed under O_V, O_C and O_T, but the raising case is
     credited only if it is in S_O. Under O_T this matters for 2 TypeScript
     mutants, which raise only on `naive-remove-receipt-signature`.
   - mutmut does not record operator names. `analyse.py` re-creates each
     mutant with mutmut's own generator, checks it against the mutant mutmut
     wrote (all 1149 match), and labels it with the operator that produced it.
   - Unique kills are reported twice: per named case, and with named cases
     that share a (package, invocation) pair merged.
   - One exploratory analysis was added that the list above does not contain:
     suite-level kills without the two naive cases, and without the two
     refined cases.
