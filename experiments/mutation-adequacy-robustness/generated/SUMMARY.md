# Robustness of the mutation-adequacy results: summary

Written by `summarise.py` from the four JSON summaries in this folder; it adds no number of its own. All four analyses are **exploratory and post hoc**: they were defined after the results of both studies were known and carry no prediction (`../PROTOCOL.md`, with its dated deviations).

## A. Subsuming mutants

A killed mutant is minimal under an oracle when no killed mutant has a kill set strictly inside its own. The gap is the set of mutants killed under O_C and not under O_V.

| Subject | Gap | Kills O_C | Gap / kills | Minimal under O_C | Minimal gap | Minimal gap / minimal | Distinct minimal kill sets | With a gap mutant |
|---|---|---|---|---|---|---|---|---|
| python | 85 | 500 | 17.0% | 131 | 73 | 55.7% | 18 | 16 |
| typescript | 82 | 373 | 22.0% | 114 | 73 | 64.0% | 22 | 19 |
| pyjwt | 42 | 446 | 9.4% | 88 | 27 | 30.7% | 27 | 7 |

Which check decides, over all gap mutants and over the minimal ones:

| Subject | Set | Mutants | Earlier | Later | Same | No defined code | Mixed |
|---|---|---|---|---|---|---|---|
| python | all gap | 85 | 1 | 5 | 23 | 56 | 0 |
| python | minimal gap | 73 | 1 | 5 | 22 | 45 | 0 |
| python | all gap, no code literal | 40 | 1 | 5 | 23 | 11 | 0 |
| python | minimal gap, no code literal | 34 | 1 | 5 | 22 | 6 | 0 |
| typescript | all gap | 82 | 1 | 39 | 26 | 16 | 0 |
| typescript | minimal gap | 73 | 1 | 33 | 25 | 14 | 0 |
| typescript | all gap, no code literal | 66 | 1 | 39 | 26 | 0 | 0 |
| typescript | minimal gap, no code literal | 59 | 1 | 33 | 25 | 0 | 0 |
| pyjwt | all gap | 42 | 17 | 22 | 0 | 0 | 3 |
| pyjwt | minimal gap | 27 | 15 | 9 | 0 | 0 | 3 |

Kill sets per subject and oracle:

| Subject | Oracle | Killed | Distinct kill sets | Minimal | Distinct minimal kill sets |
|---|---|---|---|---|---|
| python | O_V | 415 | 39 | 60 | 14 |
| python | O_C | 500 | 47 | 131 | 18 |
| python | O_T | 496 | 42 | 135 | 17 |
| typescript | O_V | 291 | 33 | 42 | 13 |
| typescript | O_C | 373 | 53 | 114 | 22 |
| typescript | O_T | 356 | 47 | 106 | 20 |
| pyjwt | O_V | 404 | 139 | 76 | 28 |
| pyjwt | O_V^fc | 378 | 85 | 86 | 24 |
| pyjwt | O_C | 446 | 158 | 88 | 27 |
| pyjwt | O_T | 451 | 149 | 84 | 26 |
| pyjwt | O_S | 538 | 192 | 163 | 45 |

Spread:

- python: 12 guard regions hold a gap mutant, 10 a minimal gap mutant.
- typescript: 11 guard regions hold a gap mutant, 11 a minimal gap mutant.
- pyjwt: 9 functions hold a gap mutant, 8 a minimal gap mutant.

Details: `subsumption.md`, `subsumption.csv`, `subsumption.json`.

## B. Operator classes that both tools have

The Python port was mutated by mutmut 3.8.1, the TypeScript port by StrykerJS 9.6.1. Shared classes are those of the table fixed in PROTOCOL.md; the last row of each port holds the operators outside it.

All mutants:

| Port | Group | Mutants | Kills O_V | Kills O_C | Gap | Later guard | Later-guard share |
|---|---|---|---|---|---|---|---|
| python | all operators | 1149 | 415 | 500 | 85 | 5 | 5.9% |
| python | shared classes | 477 | 147 | 186 | 39 | 2 | 5.1% |
| python | outside the table | 672 | 268 | 314 | 46 | 3 | 6.5% |
| typescript | all operators | 854 | 291 | 373 | 82 | 39 | 47.6% |
| typescript | shared classes | 440 | 147 | 183 | 36 | 8 | 22.2% |
| typescript | outside the table | 414 | 144 | 190 | 46 | 31 | 67.4% |

Without code-literal mutants:

| Port | Group | Mutants | Kills O_V | Kills O_C | Gap | Later guard | Later-guard share |
|---|---|---|---|---|---|---|---|
| python | all operators | 1075 | 415 | 455 | 40 | 5 | 12.5% |
| python | shared classes | 425 | 147 | 154 | 7 | 2 | 28.6% |
| python | outside the table | 650 | 268 | 301 | 33 | 3 | 9.1% |
| typescript | all operators | 828 | 291 | 357 | 66 | 39 | 59.1% |
| typescript | shared classes | 414 | 147 | 167 | 20 | 8 | 40.0% |
| typescript | outside the table | 414 | 144 | 190 | 46 | 31 | 67.4% |

Details: `shared-operators.md`, `shared-operators.csv`, `shared-operators.json`.

## C. Labels that rest on a test's name

A block left out of a label set is a block without a target. The first row is the second study as deposited.

| Label set | Labelled blocks | Blocks left out | Cases with target | P1: O_T holds | Reached deletions undetected under O_T | kills(O_T) | kills(O_C) | O_T and not O_C | O_C and not O_T | P5 |
|---|---|---|---|---|---|---|---|---|---|---|
| all | 69 | 0 | 81 | 80 of 81 | 2 of 41 | 451 | 446 | 7 | 2 | 76 of 77 |
| without name-only | 62 | 7 | 63 | 62 of 63 | 6 of 41 | 442 | 446 | 7 | 11 | 59 of 60 |
| without any name | 43 | 26 | 44 | 44 of 44 | 15 of 41 | 396 | 446 | 5 | 55 | 41 of 42 |

Details: `label-sensitivity.md`, `label-sensitivity.csv`, `label-sensitivity.json`.

## D. A second way to delete a check that sits in a handler

Of the 41 reached checks, 9 have a raise statement inside an `except` handler. Of the 16 deletions that O_V detects and O_V^fc does not, 8 are handler checks. Variant R replaces a raise statement in a handler by a bare `raise`. 19 recorder runs.

Detection verdicts that differ between the two variants: 0 of 45 (handler checks x oracles).

| Oracle | Undetected among the reached checks, original | With the handler checks by variant R |
|---|---|---|
| O_V | 5 | 5 |
| O_V^fc | 21 | 21 |
| O_C | 3 | 3 |
| O_T | 2 | 2 |
| O_S | 0 | 0 |

What the changed cases raise, summed over the handler checks:

- original (`pass`): 26 changed cases: builtins.UnboundLocalError 25, no exception 1.
- variant R (bare `raise`): 26 changed cases: builtins.TypeError 9, binascii.Error 4, builtins.ValueError 4, builtins.OverflowError 3, builtins.KeyError 1, builtins.NotImplementedError 1, builtins.RecursionError 1, builtins.UnicodeDecodeError 1, json.decoder.JSONDecodeError 1, no exception 1.

Details: `handler-variant.md`, `handler-variant.csv`, `handler-variant-cases.csv`, `handler-variant.json`.

## Sentinels

Recorded as passed in the JSON summaries: A 16, B 3, C 20, D 10.
