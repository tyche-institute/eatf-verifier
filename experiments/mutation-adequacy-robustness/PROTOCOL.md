# Robustness of the mutation-adequacy results: protocol

Fixed on 2026-11-14, before any script of this folder was written or run.
This text is not edited after execution; anything that changes is recorded,
dated, under "Deviations" at the end.

The two studies in `../mutation-adequacy/` (a verifier in two ports) and
`../mutation-adequacy-pyjwt/` (PyJWT 2.15.1) are finished and their results are
known. Nothing here changes them. This folder adds four analyses that ask
whether their conclusions depend on choices of the method: on redundant
mutants, on the operators of two different mutation tools, on the labels that
took judgement, and on the way a check is deleted. All four are **exploratory
and post hoc**: they were defined after the results of both studies had been
seen, and they carry no prediction.

Analyses A, B and C read only deposited files of the two studies and run
nothing of either subject. Analysis D runs PyJWT's negative tests again, on new
deletion copies, with the recorder and the environment of the second study.

## A. Subsuming mutants

Mutation tools generate redundant mutants, and counts over all mutants can
overstate or understate a difference between oracles. Following the notion of
dynamic subsumption, the counts are repeated over the mutants that no other
mutant subsumes.

For a subject (the Python port, the TypeScript port, PyJWT) and an oracle O:

- **Kill set.** K_O(m) is the set of cases credited with killing mutant m
  under O, by the kill rule of the mutant's own study. A mutant killed without
  a credited case (a timeout, a load failure, a crash attributed to no case)
  has the kill set {T}, where T is one element that is not a case.
- **Subsumption.** A killed mutant m is *minimal* under O when no killed mutant
  m' has K_O(m') strictly inside K_O(m). The minimal mutants are those that
  no other mutant strictly subsumes dynamically; mutants with equal kill sets
  are all kept. The number of distinct kill sets among the minimal mutants is
  the size of a subsuming set with one representative per kill set.
- **Reported** per subject and oracle (O_V, O_C, O_T; for PyJWT also O_V^fc and
  O_S): killed mutants, distinct kill sets, minimal mutants, distinct minimal
  kill sets.
- **The verdict-only gap over minimal mutants.** G is the set of mutants killed
  under O_C and not under O_V (the gap of each study). Reported beside
  |G| / kills(O_C): the number of minimal mutants under O_C that are in G, as a
  share of the minimal mutants under O_C; and the number of distinct minimal
  kill sets under O_C that hold at least one mutant of G.
- **Which check decides, over minimal mutants.** The classification that each
  study already made of its gap mutants (the direction: a later check, the
  same check, an earlier check, no defined code or no check) is tabulated
  again for the gap mutants that are minimal under O_C.
- **Spread.** The number of distinct guard regions (first study) or functions
  (second study) that hold a gap mutant, and that hold a minimal gap mutant.

Sentinel: for every subject and oracle, the number of mutants with a nonempty
kill set equals the number of killed mutants that the study's own summary
reports. If it does not, the analysis stops.

## B. Operator classes that both tools have

The two ports of the verifier were mutated by different tools, mutmut 3.8.1
and StrykerJS 9.6.1, whose operators differ. The first study reports that a
later guard decides for many more gap mutants in the TypeScript port than in
the Python port. This analysis repeats that comparison on the operator classes
that both tools have.

The correspondence, fixed here from the tools' own operator definitions:

| Class | mutmut 3.8.1 | StrykerJS 9.6.1 |
|---|---|---|
| operator replacement | `swap_op` | `ArithmeticOperator`, `EqualityOperator`, `LogicalOperator`, `UnaryOperator`, `AssignmentOperator` |
| boolean literal and negation | `name`, `remove_unary_ops` | `BooleanLiteral` |
| string literal | `string` | `StringLiteral` |
| method swap | `symmetric_string_methods_swap`, `unsymmetrical_string_methods_swap` | `MethodExpression` |

Operators outside the table have no counterpart in the other tool:
`arg_removal`, `assignment`, `augmented_assignment`, `number`, `keywords`,
`if_exp` on one side; `ConditionalExpression`, `BlockStatement`,
`ArrayDeclaration`, `ObjectLiteral`, `ArrowFunction`, `OptionalChaining`,
`Regex`, `UpdateOperator` on the other.

Reported per port, for all operators and for the shared classes only: subject
mutants, kills under O_V and O_C, gap mutants, and the gap mutants by
direction, with the later-guard share of the gap. The same is given per class.

## C. Labels that rest on a test's name

In the second study each included block got its target check from the class
it asserts, from its assertions on the message or attributes, and, where
those left several checks, from the test's name; `cases.json` records the
basis of each label. The step that reads the name took judgement and was
applied once. This analysis asks what the target oracle O_T reports when the
labels that depend on the name are set aside.

Three sets of labels, selected by the recorded basis alone:

- **all**: the 69 labelled blocks, as in the study;
- **without name-only**: without the blocks whose basis is the name alone
  (the basis text begins with `name:`);
- **without any name**: without every block whose basis mentions the name
  (the basis text contains `name:`).

A block left out of a set is treated as a block without a target. Reported for
each set: labelled blocks and cases with a target; the cases on which O_T
holds on the unmutated library (prediction P1 of the study); the deletions of
reached checks that O_T does not detect; kills(O_T); the mutants killed under
O_T and not under O_C (P3), and under O_C and not under O_T; and the cases of
P5. The row for **all** must reproduce the study's own numbers, or the
analysis stops.

## D. A second way to delete a check that sits in a handler

The second study deletes a check by replacing each of its raise statements
with `pass`. When the raise statement sits in an `except` handler, `pass`
swallows the error that the handler had caught, the value being read is never
assigned, and the decode fails a few lines later with `UnboundLocalError`.
That outcome is a property of the deletion operator. This analysis deletes
the same checks a second way.

- **Handler checks.** The checks, among the 41 reached ones, that have at
  least one raise statement lexically inside an `except` handler.
- **Variant R (re-raise).** In a copy of the package, each raise statement of
  the check that sits in a handler is replaced by a bare `raise`, on the same
  lines, so the handler lets the caught error pass on unchanged; a raise
  statement of the same check outside any handler is replaced by `pass` as
  before.
- Each variant copy runs under the recorder of the second study, with its
  environment, selection of tests and settings, next to a control copy without
  any change. Raise sites are mapped by line number against the unmodified
  source, because a bare `raise` keeps the line count and the raise count.
- **Reported** for every handler check, under the original variant (from the
  deposited results) and under variant R: detected or not under O_V, O_V^fc,
  O_C, O_T and O_S; the cases changed; and the classes of the exceptions that
  the changed cases raise. And for the 41 reached checks together: the
  deletions that O_V^fc does not detect when the handler checks are deleted by
  variant R and the others as before.

Sentinels: the control copy gives the same record as the study's baseline,
apart from timing; and under the original variant, re-run here on fresh
copies, every handler check gives the oracle results of the deposited
`deletions.csv`.

## Files

`subsumption.py` (A), `shared_operators.py` (B), `label_sensitivity.py` (C),
`handler_variant.py` (D) write `generated/` with one CSV and one JSON summary
per analysis, `SUMMARY.md` and `SHA256SUMS`. D writes its runs to an untracked
`work/`. No script changes a file of the two studies.

## Order of execution

1. Commit this protocol.
2. Write and run A, B and C on the deposited files.
3. Write and run D.
4. Commit the scripts and `generated/`.

## Deviations

None recorded at the time of fixing.

### Recorded on 2026-11-14, after the runs

The text above is unchanged. Each analysis was written once, run, and then
recomputed by a second script written without sight of the first; the two agree
on every reported number. What the scripts do beyond, or beside, the letter of
the text above:

**A. Subsuming mutants.**

1. *PyJWT kill sets.* They are rebuilt from the deposited `outcomes.jsonl` with
   the second study's own functions, imported from `analyse_s2.py` without
   writing into its folder. The rebuilt kill flag, number of credited cases and
   moves of every subject mutant equal `mutants.csv`.
2. *One direction per PyJWT gap mutant.* The second study classified the moves
   of cases, not mutants. Here a gap mutant takes the single kind of move among
   its cases, or `mixed` when its cases moved in different directions (3
   mutants). The study's own counts over case runs are reported beside it.
3. *Directions of the verifier, twice.* As in the first study, the table is
   given over all gap mutants and again without the mutants that only change a
   failure-code literal.
4. *Spread.* The unit for the verifier is a region of `guard-regions.json`,
   and that file also names the unguarded region `shared`. In the Python port
   `shared` holds 2 gap mutants, neither minimal: 12 regions hold a gap mutant
   when `shared` is counted, 11 when only guards are, and 10 hold a minimal gap
   mutant either way. The TypeScript counts (11 and 11) do not involve it.
5. *More sentinels.* Beside the sentinel of the text, the script stops when the
   verifier's kill sets differ from a recomputation from `outcomes.jsonl`, when
   a gap set differs from `gap-directions.csv`, or when PyJWT's gap and moves
   differ from that study's `summary.json`.

**B. Operator classes that both tools have.**

1. *A second reading.* The text does not say whether the mutants that only
   change a failure-code literal are counted. Every count is given over all
   subject mutants and, as a supplement, without those mutants, the subset on
   which the first study compared the directions.
2. *A complement row.* The operators that the text lists as having no
   counterpart are reported as one more row per port, so that the rows add up;
   a sentinel checks the sum.
3. *An empty operator.* `unsymmetrical_string_methods_swap` produced no mutant
   in the Python port, whose method-swap class holds 3 mutants.
4. *How exact the table is.* The table was checked against the operator
   definitions of both tools after the run and left as fixed. It matches
   classes, not single rewrites. The 25 `keywords` mutants of the Python port
   all negate `is` or `in` (14 and 11), which is what `EqualityOperator` does
   to `===`, yet `keywords` stands among the operators without a counterpart.
   18 of the 23 `MethodExpression` mutants remove a call, which mutmut does not
   do. 11 of the 76 `EqualityOperator` mutants negate a relational operator,
   where `swap_op` only moves its boundary. The shared-class rows therefore
   compare similar, not identical, sets of rewrites.

**C. Labels that rest on a test's name.**

1. *The parametrized block.* `test_decode_raises_clean_error_if_claim_is_non_numeric_type`
   has 1 recorded basis per value of its parameter, each of the form
   `name: ...; message contains ...`. The text defines the name-only labels
   both as "the basis is the name alone" and as "the basis text begins with
   `name:`"; for this block the two differ. The script follows the second,
   operational wording, value by value, so the block (12 cases) is left out of
   both reduced sets: 7 blocks are left out of "without name-only" and 26 of
   "without any name".
2. *Scoring.* O_T and O_C are scored by the second study's own functions,
   imported from `analyse_s2.py`, on observations rebuilt from `outcomes.jsonl`.
   The kill rule is unchanged when labels are set aside: a crash of any case, a
   load failure or a timeout still kills under O_T.
3. *One more input.* `checks.json` of the second study is read for the function
   of each target check, which P5 needs.

**D. A second way to delete a check that sits in a handler.**

1. *No write into the second study.* Its `verify` step is repeated check for
   check inside `handler_variant.py` with git and the interpreter told not to
   write (`--no-optional-locks`, `-B`); everything else is imported from
   `run_s2.py` and `analyse_s2.py` unchanged.
2. *The first sentinel.* The control copy is compared with the study's baseline
   record through that study's `normalise()`, which sets aside the line numbers
   of frames and the environment block as well as timing. For an unmodified
   copy the line numbers are the same in any case.
3. *Raise sites under variant R.* A bare `raise` re-raises the caught error, so
   the innermost frame inside the package is the statement of the `try` body
   and no check is the raise site of a changed case. The mapping by line agrees
   with the recorder's own numbering at every raise site of every run.
4. *Counting the runs.* 19 recorder runs: 1 control and, for each of the 9
   handler checks, 1 copy per variant. `runs.states` in `handler-variant.json`
   counts the 18 variant runs.

**Files.**

1. *A fifth script.* The text says that the 4 analysis scripts write
   `SUMMARY.md` and `SHA256SUMS`. A fifth script, `summarise.py`, writes both.
   It reads only the 4 JSON summaries, copies their headline numbers and adds
   none of its own.
2. *Added with the results.* `README.md`, and `timestamps/` with the RFC 3161
   tokens of 2 time-stamping authorities for the commit that fixed the text
   above (`708beec`, 2026-11-14 02:46:40 UTC).
