# Mutation adequacy of the deposited negative cases

The decision-path and path-shadowing experiments judge a negative case by the
state it reaches. This experiment asks the converse question: when faults are
placed in the verifier, do the deposited cases detect them, and under which
oracle?

Everything was fixed in `PROTOCOL.md` and `guard-regions.json` before any mutant
was generated (commit `9a55de0`): the research questions, the oracles, the kill
rule, the mutant sets and five predictions. Changes made once the runs began are
listed, dated, at the end of `PROTOCOL.md`.

## What runs

- **Subject.** eatf-verifier `v0.5.0`. In each port, the files mutated are the
  decision procedure and the two parsers whose results it acts on
  (`verifier`, `overt`, `tsa`).
- **Suite.** The 25 named cases of the two earlier experiments, as deposited:
  23 distinct (package, invocation) pairs over 21 distinct packages.
- **Tool mutants.** mutmut 3.8.1 for Python and StrykerJS 9.6.1 for TypeScript,
  each with its default operators and with no mutant removed.
- **Guard deletions.** For each of 11 guards, every statement that returns one
  of the guard's failure codes is deleted, with the rest of the program left
  intact. An unmodified control copy goes through the same steps.
- **Observation.** For each mutant and case, the harness records the verdict
  and failure code, or the type of the exception raised. It never reads the
  failure reason.
- **Oracles.** Each mutant is scored four ways:
  - O_V: verdict only.
  - O_V^fc: verdict only, with an exception read as a rejection.
  - O_C: verdict and failure code.
  - O_T: the failure code equals the case's target code.

## Result

All five predictions held in both ports, and every sentinel passed. The numbers
are in `generated/SUMMARY.md`, and `generated/summary.json` holds the details
behind each verdict.

- **Guard deletions (P2).** Under O_V, deleting any one of 4 guards out of 11
  goes undetected. Under O_V^fc, 5 go undetected. Under O_C and O_T, all 11
  deletions are detected. Each of the 4 undetected guards is backed by a later
  guard that rejects the same package with another code.
- **Tool mutants (P4).** Of 1149 Python mutants, O_C kills 500 and O_V kills
  415. Of 854 TypeScript mutants, O_C kills 373 and O_V kills 291.
- **Target regions (P5).** Neither naive path-shadowing case kills any mutant in
  the region of its own target guard. Their refined twins do. Every case that
  reaches its target kills at least one mutant there.
- **Suite-level score.** The suite-level mutation score does not separate the
  naive cases from the refined ones. The naive cases add kills of their own, and
  all of these lie in the region of the guard that shadows them.

## Run it

From the repository root, with Python 3.12 and Node 22:

```sh
npm ci
(cd experiments/mutation-adequacy/stryker && npm ci)
python3 -m venv experiments/mutation-adequacy/work/venv
experiments/mutation-adequacy/work/venv/bin/pip install -r experiments/mutation-adequacy/generated/pip-freeze.txt
experiments/mutation-adequacy/work/venv/bin/python experiments/mutation-adequacy/run_experiment.py all --max-children 10
experiments/mutation-adequacy/work/venv/bin/python experiments/mutation-adequacy/analyse.py
```

- The runner refuses to start if a subject file differs from the SHA-256 in
  `guard-regions.json`.
- It writes only to `work/`, which is not tracked. `analyse.py` reads `work/`
  and writes `generated/`.
- The reported run took 23 s for mutmut and 26 s for Stryker on a 24-core
  machine.
- `analyse.py` exits nonzero if a sentinel fails.

## Files

| Path | Role |
|---|---|
| `PROTOCOL.md` | Questions, oracles, kill rule, predictions and dated deviations |
| `guard-regions.json` | Guards, their failure codes, and the line regions of each subject file |
| `cases.py` | Builds the case manifest; rebuilds the 4 path-shadowing packages and checks their SHA-256 |
| `harness_py.py`, `harness-ts.mjs` | One harness per port. The Python one doubles as mutmut's test |
| `deletions.py`, `delete-ts.mjs` | Guard deletion on the syntax tree of each port |
| `run_experiment.py` | Runs the stages in the protocol's order |
| `mutmut.toml`, `stryker/` | Tool configuration, the Stryker lockfile and the sandbox build script |
| `analyse.py` | Scores every mutant under the four oracles and checks the predictions |
| `generated/` | Results: `SUMMARY.md`, `summary.json`, the CSV tables, `outcomes.jsonl`, `environment.json`, `SHA256SUMS` |

In `generated/`:

- `mutants.csv` has one row per tool mutant: its region, operator, tool status,
  kill under each oracle, and the cases credited with each kill.
- `outcomes.jsonl` holds the observed state of every case under every executed
  mutant, and under both baselines.
- `environment.json` records the tool versions and the SHA-256 of each
  experiment source file.

## Limits

- **Equivalent mutants.** These were not removed by hand. Many surviving mutants
  change only a failure reason or a report field, which no oracle here observes.
  So the absolute scores are low for every oracle, and the differences between
  oracles are the quantity of interest.
- **Region attribution.** A region is assigned by the first original line a
  mutant changes. A mutant that spans two regions is counted in the first.
- **Scope.** The suite is the deposited one, not a suite built for this
  experiment. Region `13-tsa-pin` has no case that targets it, and most of its
  mutants survive. That is a gap in the suite, not a result about the oracles.
