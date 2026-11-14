# Robustness of the mutation-adequacy results

The two studies next to this folder, `../mutation-adequacy/` (a verifier in a
Python and a TypeScript port) and `../mutation-adequacy-pyjwt/` (PyJWT 2.15.1),
are finished. This folder asks whether their conclusions depend on 4 choices
of the method: redundant mutants, the operators of 2 different mutation tools,
the target labels that took judgement, and the way a check is deleted.

All 4 analyses are **exploratory and post hoc**. They were defined in
`PROTOCOL.md` after the results of both studies were known (commit `708beec`,
time-stamped by 2 authorities, `timestamps/`), and they carry no prediction.
What the scripts do beyond the letter of the protocol is listed, dated, at its
end. Nothing here changes a file or a number of the two studies.

## What runs

- **A. Subsuming mutants** (`subsumption.py`). The counts of both studies are
  repeated over the mutants that no other mutant subsumes dynamically: a
  killed mutant is minimal under an oracle when no killed mutant has a kill
  set strictly inside its own. Reads deposited files only.
- **B. Operator classes that both tools have** (`shared_operators.py`). The
  comparison of the 2 ports is repeated on the 4 operator classes that mutmut
  3.8.1 and StrykerJS 9.6.1 share. Reads deposited files only.
- **C. Labels that rest on a test's name** (`label_sensitivity.py`). The
  target oracle O_T of the second study is scored again without the labels
  whose recorded basis is the test's name, and without every label whose
  basis mentions the name. Reads deposited files only.
- **D. A second way to delete a check that sits in a handler**
  (`handler_variant.py`). The second study deletes a check by replacing its
  raise statements with `pass`. For the checks that raise inside an `except`
  handler, variant R replaces the raise statement with a bare `raise`.
  PyJWT's negative tests run again on the new copies, with the recorder and
  the environment of the second study: 19 recorder runs.
- `summarise.py` copies the headline numbers of the 4 JSON summaries into
  `generated/SUMMARY.md` and writes `generated/SHA256SUMS`.

Each analysis was written once, run, and then recomputed by a second script
written without sight of the first; the two agree on every reported number.

## Result

The numbers are in `generated/SUMMARY.md`; each analysis has its own
`generated/<name>.md`, `.csv` and `.json`. Every sentinel passed.

- **A. Redundant mutants do not explain the verdict-only gap.** The gap is the
  set of mutants killed under O_C and not under O_V. Over all killed mutants
  it is 85 of 500 in the Python port (17.0%), 82 of 373 in the TypeScript port
  (22.0%) and 42 of 446 in PyJWT (9.4%). Over the minimal mutants it is 73 of
  131 (55.7%), 73 of 114 (64.0%) and 27 of 88 (30.7%). A gap mutant is in 16 of
  the 18, 19 of the 22 and 7 of the 27 distinct minimal kill sets.
  - A later guard decides for 5 of the 73 minimal gap mutants in the Python
    port (5 of 85 over all gap mutants) and for 33 of 73 in the TypeScript
    port (39 of 82).
  - In PyJWT, 9 minimal gap mutants move a case to a later check, 15 to an
    earlier one and 3 both ways. Over all 42 gap mutants the counts are 22, 17
    and 3.
- **B. Most of the difference between the ports comes from operators that
  only one tool has.** Over all operators a later guard decides for 5 of 85
  gap mutants in the Python port (5.9%) and 39 of 82 in the TypeScript port
  (47.6%). On the shared classes it is 2 of 39 (5.1%) and 8 of 36 (22.2%). The
  other 31 TypeScript mutants come from operators outside the table.
  - Without the mutants that only change a failure-code literal, the shared
    classes hold 7 gap mutants in the Python port, 2 of them later-guard, and
    20 in the TypeScript port, 8 of them later-guard. These counts are small.
- **C. The findings on PyJWT that rest on a name-based label.** With all 69
  labelled blocks, O_T fails on 1 of 81 cases on the unmutated library and 7
  mutants are killed under O_T and not under O_C.
  - Without the 7 blocks labelled from the name alone, the failing case stays
    (62 of 63) and all 7 mutants stay.
  - Without the 26 blocks whose basis mentions the name, the failing case is
    itself left out (44 of 44) and 5 of the 7 mutants stay.
  - The deletions of reached checks that O_T does not detect grow from 2 to 6
    to 15 of 41, because their cases lose their targets.
- **D. The re-raise variant changes no detection verdict.** 9 of the 41
  reached checks raise inside a handler; 8 of them are among the 16 deletions
  that O_V detects and the fail-closed oracle O_V^fc does not. Under variant R
  0 of the 45 verdicts (9 checks, 5 oracles) differ, and O_V^fc still misses
  21 of 41 deletions.
  - What changes is the exception. Under `pass`, 25 of the 26 changed cases
    raise `UnboundLocalError`. Under variant R they raise the error that the
    handler had caught, such as `TypeError` (9 cases) or `ValueError` (4).
  - Either way the case raises something, so an oracle that accepts any
    exception as a rejection does not see the deletion.

## Run it

A, B and C need Python 3.12 and the deposited files of the two studies:

```sh
python3 -I subsumption.py
python3 -I shared_operators.py
python3 -I label_sensitivity.py
```

D also needs the clone and the virtual environment of the second study, set
up as its README describes (`../mutation-adequacy-pyjwt/work/pyjwt` and
`work/venv`):

```sh
../mutation-adequacy-pyjwt/work/venv/bin/python -I handler_variant.py
python3 -I summarise.py
```

- Every script exits nonzero when a sentinel fails.
- D writes its copies and records to `work/`, which is not tracked, and takes
  about 3 s. No script writes into the folder of either study.
- Re-runs on 14 November 2026 reproduced `generated/` byte for byte.

## Files

| Path | Role |
|---|---|
| `PROTOCOL.md` | The 4 analyses as fixed before any script, and the dated deviations |
| `subsumption.py` | A: kill sets, minimal mutants, the gap over minimal mutants |
| `shared_operators.py` | B: both ports on the shared operator classes |
| `label_sensitivity.py` | C: O_T under 3 sets of labels |
| `handler_variant.py` | D: variant R, with a control and a re-run of the original variant |
| `summarise.py` | Writes `generated/SUMMARY.md` and `generated/SHA256SUMS` |
| `generated/` | Results: `SUMMARY.md`, and a `.md`, `.csv` and `.json` per analysis |
| `timestamps/` | RFC 3161 tokens for the protocol commit, with the commands that verify them |

## Limits

- **Post hoc.** The analyses were chosen after the results were known. They
  can weaken a conclusion of the two studies; they cannot confirm a
  prediction.
- **Subsumption is relative to the cases.** A mutant is minimal with respect
  to the negative cases of its study only. Mutants with equal kill sets are
  all kept, so the minimal mutants still hold duplicates; the number of
  distinct minimal kill sets is reported beside them.
- **The operator table matches classes, not single rewrites.** For example,
  18 of the 23 `MethodExpression` mutants remove a call, which mutmut does not
  do (deviation B.4). The shared-class rows compare similar sets of rewrites,
  not identical ones.
- **The basis of a label was recorded by the person who labelled.** Analysis C
  selects labels by that record. It does not replace a second rater.
- **One alternative deletion.** Variant R is one of several ways to delete a
  check in a handler, and it applies to 9 checks of one library.
