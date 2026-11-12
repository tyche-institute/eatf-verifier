# Mutation adequacy of PyJWT's negative tests

The first subject of this study, in `../mutation-adequacy/`, is a verifier
whose negative cases come from the verifier's own author. This experiment asks
the same questions of a library that others wrote and tested: PyJWT 2.15.1.
Its decoder rejects a token by raising an exception, and several of its checks
share an exception class.

Everything was fixed in `PROTOCOL.md`, `checks.json` and `cases.json` before
any mutant was generated and before any case was observed (commit `608e2fd`):
the research questions, the checks, the cases and their targets, the oracles,
the kill rule, the mutant sets and five predictions. Changes made once the runs
began are listed, dated, at the end of `PROTOCOL.md`.

## What runs

- **Subject.** PyJWT 2.15.1, commit `7d5ef55e42ce42221f58dc49943e92ccad1fa66a`,
  MIT licence. The files mutated are `jwt/api_jws.py` and `jwt/api_jwt.py`.
  The subject is the 27 functions of these files that a decode can run.
- **Checks.** 44 checks in the two files, sharing 13 exception classes, and 5
  external checks in `jwt/algorithms.py` that are observed but not mutated.
- **Cases.** Every run of a `pytest.raises` block of PyJWT's own tests that
  calls a decode function and expects a PyJWTError: 79 blocks in 76 tests,
  run 91 times. 81 cases have a target check. No test is added or changed.
- **Tool mutants.** mutmut 3.8.1 with its default operators and no mutant
  removed: 1094 mutants, 880 of them in subject functions.
- **Check deletions.** For each of the 44 checks, every raise statement of the
  check is replaced by `pass`. An unmodified control copy goes through the
  same steps.
- **Observation.** A pytest plugin, `plugin/s2_recorder.py`, wraps
  `pytest.raises` and records, for each case, the exception's class, message,
  `claim` attribute and cause, and the raise site, mapped to a check. It then
  lets the test continue.
- **Oracles.** Each mutant is scored five ways:
  - O_V: the case raised a PyJWTError.
  - O_V^fc: the case raised any exception.
  - O_C: the case raised the class that the unmutated library raises.
  - O_T: the raise site is the case's target check.
  - O_S: the test's own assertions on the exception hold.

## Result

Two predictions held and three were refuted, and every sentinel passed. The
numbers are in `generated/SUMMARY.md`, and `generated/summary.json` holds the
details behind each verdict.

- **Unmutated library (P1), refuted.** Every case raises a PyJWTError, and the
  tests' own assertions hold on every case. O_T fails on 1 of the 81 cases
  with a target: the test of a deeply nested header was labelled with the JSON
  check, but on Python 3.12.3 `json.loads` parses that header, and the check
  that the header is a JSON object rejects it.
- **Check deletions (P2), held.** 41 of the 44 checks are reached by some case.
  Of those 41 deletions, 5 go undetected under O_V, 21 under O_V^fc, 3 under
  O_C, 2 under O_T and none under O_S.
  - Each of the 3 deletions that O_C misses leaves its cases to another check
    of the same class: `jws.crit-strings` to `jws.crit-supported`, and
    `jwt.aud-strict-param` and `jwt.aud-strict-claim-format` to
    `jwt.aud-strict-match`. O_T and O_S detect all 3.
  - O_T misses `jws.header-json` and `jwt.aud-match` because no case on which
    O_T holds targets them.
  - 16 deletions are detected under O_V only through exceptions that are not
    PyJWTErrors, and so go undetected under O_V^fc.
- **The class does not identify the check (P3), held.** 7 tool mutants are
  killed under O_T and not under O_C. In each, a case is rejected by another
  check of the same class.
- **The rejection-only gap (P4), refuted.** Of the 880 subject mutants, O_C
  kills 446 and O_V kills 404, a strict subset. The difference, 42, is 9.4% of
  O_C's kills; the prediction was at least 10%.
- **Kills by target function (P5), refuted.** Of the 77 cases on which O_T
  holds and whose target is in the two files, 76 kill a mutant of their
  target's function under O_T.
  The exception is the second block of `test_bad_secret`, which repeats the
  first block's decode. Whenever a mutant changes that outcome, the assertion
  after the first block stops the test, and the second block is withheld.
- **Scores.** Of the 880 subject mutants, O_V^fc kills 378, O_V 404, O_C 446,
  O_T 451 and O_S 538. mutmut itself, running the whole suite, kills 643.
  O_S kills 92 mutants that O_C does not; 78 of them change only the
  arguments of an exception in a raise statement, which O_V, O_C and O_T
  cannot see.

## Run it

From this directory, with Python 3.12.3:

```sh
git clone https://github.com/jpadilla/pyjwt work/pyjwt
git -C work/pyjwt checkout 7d5ef55e42ce42221f58dc49943e92ccad1fa66a
python3 -m venv work/venv
work/venv/bin/pip install -r generated/pip-freeze.txt
cp generated/pip-freeze.txt work/pip-freeze.txt
work/venv/bin/python -I run_s2.py verify suite baseline deletions mutmut mutants
work/venv/bin/python -I analyse_s2.py
```

- `run_s2.py verify` refuses to continue if the clone is not at the commit
  above or has changes, if a subject or test file differs from the SHA-256 in
  `checks.json` or `cases.json`, if the Python version or the installed
  packages differ from the reported ones, or if a `jwt` package can be
  imported from the virtual environment itself.
- The clone used for the reported run also holds an ignored
  `PyJWT.egg-info` directory. Every run uses a copy of `jwt/`, `tests/` and
  `pyproject.toml` only, so it never enters a run.
- The runner writes only to `work/`, which is not tracked. `analyse_s2.py`
  reads `work/` and writes `generated/`.
- The reported run took 25 s for mutmut and 340 s for the 881 recorder runs
  of the subject mutants on an Intel Core i9-12900K (16 cores, 24 logical
  CPUs), 10 runs at a time.
- `analyse_s2.py` exits nonzero if a sentinel fails.

## Files

| Path | Role |
|---|---|
| `PROTOCOL.md` | Questions, oracles, kill rule, predictions and dated deviations |
| `define_s2.py` | Writes `checks.json` and `cases.json` from the subject's source and tests |
| `checks.json` | The checks, their raise statements, classes and decode order; the subject functions |
| `cases.json` | The included blocks, their targets with the basis of each label, and their assertions |
| `plugin/s2_recorder.py` | The pytest plugin that records each case |
| `run_s2.py` | Runs the stages in the protocol's order |
| `analyse_s2.py` | Scores every mutant and deletion under the five oracles and checks the predictions |
| `generated/` | Results: `SUMMARY.md`, `summary.json`, the CSV tables, `outcomes.jsonl`, `environment.json`, `pip-freeze.txt`, `SHA256SUMS` |

In `generated/`:

- `mutants.csv` has one row per tool mutant: its function, operator, tool
  status, kill under each oracle, and the number of cases credited.
- `deletions.csv` has one row per check deletion, and `deletion-cases.csv` one
  row per case whose class, raise site or message changed under a deletion.
- `cases.csv` gives each case's target, baseline class and site, and its kills
  under each oracle; `p5.csv` gives the kills behind P5.
- `functions.csv` and `operators.csv` give the kills by subject function and
  by mutation operator.
- `outcomes.jsonl` holds what the oracles read for every case in every run:
  the two baseline runs, the control, the run with no mutant active, the 44
  deletions and the 880 subject mutants. Its first line describes each case
  and its baseline observation; each later line gives a run's state and, for
  each case, its observation, or null where it equals the baseline.
- `environment.json` records the tool versions, the mutmut run and the SHA-256
  of each experiment source file.

## Limits

- **Equivalent mutants.** These were not removed by hand, so the absolute
  scores are low for every oracle. The differences between oracles are the
  quantity of interest.
- **Targets.** The target of each block was assigned by one author from the
  test text alone, before any observation. 10 blocks have none, and the
  label of 1 case proved wrong on the Python version used.
- **Scope.** One library, its own tests, two of its files, and one Python
  version. The suite was written by PyJWT's developers, not for this
  experiment.
