# Protocol: follow-up analyses on the replication of `../target-reach/`

This text is fixed by the commit that adds it. Right after that commit, a text
that names it is time-stamped by 2 authorities, and a later commit adds the
tokens in `timestamps/`. Section 5 says what had been done before the commit on
each subject, and section 6 fixes the order of what comes after it.

The analyses below were chosen after the results of `../target-reach/` had been
read. They are follow-up analyses of that replication and are reported as such.
The terms check, block, case, target, deciding check, fired check, deletion,
recorder, whole suite and the oracles O_V, O_Vfc, O_C, O_T and O_S keep the
meaning that section 4 of `../target-reach/PROTOCOL.md` gives them. "The
toolkit" is the code in `../target-reach/reach/` and `../target-reach/guard/`,
which this experiment imports and does not change.

## 1. Questions

**Q1, labels.** In `../target-reach/` a program assigned the target of each
negative-test block. When the target of every included block of the 4 held-out
libraries is instead assigned by reading the test, 2 times and without sight of
any run, how often do the 2 readings agree? How often is the labeled check the
check that decides the case? Which cases are stopped by an earlier check than
the one their test describes? And how often does the program's target differ
from the label?

**Q2, rule.** The program takes as candidates the checks that are reachable by
name from the entry points. Does it make fewer errors when the checks whose
function runs under an entry point in the library's own suite are candidates
too, and what does that cost in cases that lose a target?

**Q3, mutants.** In the first study of this repository, 2 cases designed to stop
at an earlier check killed tool mutants that no other case killed, all in the
check that stopped them, so the mutation score fell when they were repaired.
Does the same hold for tests found in the libraries that stop at an earlier
check? What do such tests kill at the check they describe, and what does
repairing them change?

**Q4, recounts and interpreter versions.** Descriptive: counts recomputed from
the deposited outputs of `../target-reach/`, and tests run on later versions
of the interpreter.

## 2. Expectations

Each expectation is stated before the runs that test it. An expectation that
does not hold is reported as not held; no definition changes after the commit.

Labels:

- **L1.** For each of the 3 cases of joserfc that the reading in
  `../target-reach/readings/joserfc/FLAGS.md` put in class A, both readings
  give as label the target that the program assigned.
- **L2.** For every flag that the readings in `../target-reach/readings/` put
  in class C and that has an agreed label naming a check, the agreed label
  differs from the program's target.
- **L3.** Every case that its program target decides, and that has an agreed
  label naming a check, has that target as its label.

Rule:

- **T1.** In joserfc, the number of cases whose target does not decide them
  falls from 60 under rule 2 to 10 or fewer under rule 3.
- **T2.** The 3 class-A cases of joserfc keep their target under rule 3.
- **T3.** Among the cases of joserfc with a target under rule 3, at least 85%
  are decided by it (under rule 2: 71 of 131, 54%).

A note on the rule, written before any trace of a held-out library was made.
Under rule 2, 99 cases of joserfc have a target because 1 check of the expected
class is reachable by name. Under rule 3 more checks of a class are reachable,
so a part of these cases is expected to lose its target, among them cases that
the target decided. The report gives, for each library, the cases that gain,
keep, change and lose a target, and how many of each kind the target decides.

Mutants:

- **M1, the claim under test.** At least 1 test that holds a shadowed case has
  a unique kill at the check that decides the case.
- **M2.** No shadowed case detects, under O_C, a mutant that is at the check it
  describes and not at the check that decides it.
- **M3.** For each shadowed case that has a repaired variant, the variant
  kills at least 1 mutant at the check that the test describes. Where that
  check fires in no case of the baseline, the whole suite does not kill the
  deletion of the check, and the suite with the variant does.

A note on M1, written before any mutant of a held-out library was made. In 2
of the 3 class-A cases of joserfc, the check that the test describes and the
check that stops the input are size limits that raise the same class, and the
input exceeds both. A mutant that switches the earlier check off therefore
leaves the test passing. M1 is expected not to hold for these 2 cases; it is
kept as stated because it is the claim that the designed cases of the first
study support.

## 3. Subjects

The 4 held-out libraries of `../target-reach/`, each at the commit, in the
environment and with the definitions of `../target-reach/subjects/<name>/`:
google-auth 2.62.2, oauthlib 4.0.1, authlib 1.9.5 and joserfc 1.8.0. No
definition of a subject changes: the same checks, blocks, cases and records.

PyJWT 2.15.1 and jwcrypto 1.6.1 are the development subjects, as in
`../target-reach/`. Their results are reported apart and take no part in the
expectations.

## 4. Definitions

### 4.1 Labels

**Reading pack.** For 1 library: the files of the paths that `subject.json`
copies, read from the repository at the commit of the subject (`src/`);
`checks.tsv`, with every check of `checks.json` (id, file, function, class,
lines, message template, guard conditions) and without the field that says
whether a check is reachable; `classes.tsv`, the classes with their bases;
`blocks.tsv`, with every included block of `blocks.json`; a `labels.tsv` with
1 empty row per included block; and the instruction, `labels/INSTRUCTION.md`.
A pack holds no target, no record, no output of any run and no reading.
`labels/prepare.py` builds it, refuses a pack that holds a file of this
repository's experiments, and lists the files with their hashes.

**Reading.** 1 filled `labels.tsv` per library, made from the pack and the
instruction alone, with nothing run. The label of a block is the identifier
of 1 check, or `none`, or, for a block of a parametrized test, 1 of the 2 per
value of the parameter. The instruction fixes the labeling rule: the check
left when the checks of the expected class, the checks that can satisfy the
block's assertions and the checks that the test's name, docstring and
comments name are narrowed in that order. It forbids deciding by the order of
execution. The instruction is part of this commit and does not change.

**Parts.** A library with more than 50 included blocks is read in parts.
`labels/parts.py split --max-blocks 50` assigns each test file to a part, from
`blocks.tsv` alone; each part is made with a copy of the whole pack, and
`labels/parts.py join` takes each row from the part of its test file.

**2 readings.** Each library is read 2 times, as reading A and reading B.
Neither reading has the other's file. Neither has the targets of the program,
the records, the outputs of `../target-reach/` or its readings.
`labels/check_labels.py` checks the form of each file: every included block 1
time, a label that is a check of the pack or `none`, a basis, and a note for
`none`. A file that fails is returned for a correction of form, and the
correction is listed in `DEVIATIONS.md`.

**Agreement.** Per block, 1 of 4: both readings give the same label, which
names a check ("same check"); both give `none`; 1 gives a check and 1 gives
`none`; the 2 give different checks. 2 labels are the same when their texts
are equal after the values of a by-parameter label are sorted. The agreed
label of a block is the common label of the first 2 categories. Results that
need a label use the agreed labels only; the other blocks are listed with
both answers. The observed agreement and Cohen's kappa over the included
blocks are reported per library and for the 4 together, 2 times: with every
distinct label text as a category, and with the 2 categories "names a check"
and "none". No threshold is set.

**Outcome of a case with an agreed label that names a check.** From the
deposited records, the first that applies:

1. *decided by its label*: the label is the deciding check of the case;
2. *label fires and another check decides*;
3. *label fires and no check decides*: the case is decided by a statement
   that is not a check;
4. *label does not fire and no check decides*;
5. *deciding check not deleted or record missing*;
6. *label does not fire; case not observed on the copy without the deciding
   check*;
7. *label does not fire and decides once the deciding check is deleted*: on
   the copy without the deciding check of the case, the label decides the
   case;
8. *label does not fire and does not decide then either*.

Where the records of a library hold no fired checks, the cases not decided by
their label have the outcome *fired checks not recorded*.

A case of outcome 7 is called **shadowed**: 1 earlier check stops its input,
and the check that the test describes decides once that check is gone. The 3
class-A cases of joserfc meet the same condition with the program's target in
place of the label; they are included in the mutant analysis whatever the
labels say, and the report says for each shadowed case which of the 2 sources
shows it.

**Program against label.** Per case and per tier of the rule (assertion, name,
no target), for rule 2 and rule 3, 1 of 6: the program's target equals the
agreed label; differs from it; the program gives a target and the agreed
label is `none`; the program gives none and the agreed label names a check;
both give none; the block has no agreed label. The same is reported per
block and per basis of the rule.

**First reading.** `labels/first/<name>.tsv` holds, for each flag of
`../target-reach/`, the class (A, B, C) and the described check that the
reading deposited there gives. It is compared with the agreed labels and is
no input to them.

### 4.2 Rule 3

**Started under an entry point.** `trace/README.md`, which this commit fixes,
defines the terms. In short: in a run of the whole suite on the unmodified
copy, a function of the files of `checks.json` starts under an entry point
when, at 1 of its starts (the `PY_START` event of `sys.monitoring`), a
function of those files named like an entry point of the subject is on the
frame chain of the same thread, the starting function included.
`trace/plugin.py` records this in every suite run of `subject.json`; the
first traced run gives `reach.json`.

**Rule 3.** The code of the rule, `../target-reach/reach/targets.py`, is
unchanged. Its input changes in 1 place: a check is reachable when it is
reachable by name, as in rule 2, or when its function started under an entry
point. Tiers, bases and every constant stay as they are.

Rule 3 reads runs of the whole suite. It does not read the outcome of the
block that it assigns a target to: the trace records which functions start
under which entry points, not which check rejects in which test.

**Repeats.** The suite is run 3 times without the plugin and 3 times with it,
each on a fresh copy. The set of functions started under at least 1 entry
point must be the same in the 3 traced runs, and the tests that pass must be
those of the deposited whole-suite baseline; otherwise the step stops and the
difference is reported.

**Analysis.** The cases, the deciding checks and the deletion records are
those deposited in `../target-reach/generated/<name>/records.tar.xz`; only the
targets differ. A flag under rule 3 is a case with a target under rule 3 that
the target does not decide. Per library: the checks reachable by name, by
execution and by both; per case, whether it keeps, changes, gains or loses
its target, and whether the target decides it under each rule.

### 4.3 Mutants

**Libraries and files.** For each held-out library that has at least 1
shadowed case: the source files that hold the check that a shadowed case
describes (its agreed label, or the program's target for the 3 class-A cases)
or the check that decides it.

**Mutants.** In those files: every mutant that mutmut 3.8.1 creates with its
default operators ("tool mutants"), re-created by mutmut's own generator as
`mutants/README.md` describes, and the deletion of every check of
`checks.json` in those files, made by `../target-reach/reach/delete.py`
("deletions"), whether or not the check fires in a test. Each mutant is a copy
of the package in which 1 file differs from the unmodified one, with every
line number kept. Counts of mutants are of tool mutants; the deletions are
counted apart.

**Runs.** On each mutant copy: the negative tests under the recorder, the
whole suite, and the repaired variants. Time limits, the repeat of a run
without a result and the guard against outside connections are those of
`../target-reach/`, as `mutants/README.md` states them.

**Kills.** A test kills a mutant when it passes in both whole-suite runs on
unmodified copies and does not pass on the mutant copy. A mutant is killed by
the suite when a test kills it, or when its whole-suite run ends in a timeout
or without a result after the repeat; such a mutant gives no kill to any
test. A case detects a mutant under O_V, O_Vfc, O_C or O_T by the rules that
`../target-reach/` applies to a deletion copy.

**At a check.** The span of a check is, for each of its raise statements, the
lines of the raise statement together with the lines of its innermost guard:
the test of the enclosing `if` statement (the raise may stand in its body or
in its `else` part), or the header of the enclosing `except` clause, from
`except` to the end of the exception type (the guard that `checks.json`
records, found by the same function). A raise statement under no `if` and no
`except` has its own lines only. A mutant is at a check when at least 1 line
that it changes lies in the span; the deletion of a check is at that check. A
mutant is in the function of a check when every line that it changes lies in
the function that holds the check. `mutants/at_check.py` computes both.

**Unique kill.** A mutant is a unique kill of a test when the tests of the
whole suite that kill it are that 1 test. A test that runs in several suite
runs is 1 test. The suite kills 1 mutant fewer for each unique kill of a test
that is removed.

**Killed by a variant.** The variant does not pass on the mutant copy, in a
completed run of the extra tests.

**Repaired variant.** For a shadowed case: a new test with the assertion of
the original block and an input changed as little as possible, such that on
the unmodified library, with its default settings, the check that the test
describes decides the case. Where no such input is found, the reason is
recorded with the lines of the source that show it, and the case has no
variant. A variant is written and its deciding check verified before any
mutant of its library is run. The variants of the 3 class-A cases of joserfc
were written before this commit (section 5).

**Comparison cases.** In the mutated files: the cases with a program target
(rule 2) that the target decides, and that are not shadowed.

**Cases file.** `mutants/cases_file.py` lists the shadowed cases, from the
outcomes that `labels/analyse_labels.py` writes and from the class-A rows of
`labels/first/<name>.tsv`, with the files to mutate and the comparison cases.
It stops when a class-A row does not meet, in the deposited outputs of
`../target-reach/`, the condition of section 4.1.

**Reported.** For each shadowed case and each comparison case: the tool
mutants at the check it describes, at its deciding check, and at the
described check and not at the deciding check; of each group the ones that
the suite kills, that the case detects under O_C, on which the test of the
case does not pass in the recorder run, that its test kills, that are unique
kills of its test, and that the variant kills; the same for the deletion of
each of the 2 checks; and the counts in the functions of both checks and in
all mutated files. For each library: the mutants that the whole suite kills;
the same without the tests that hold a shadowed case; the same with each such
test replaced by its variant; and, for each check that a shadowed case
describes, the mutants at it that the suite does not kill and the variant
kills.

**Sentinels.** `mutants/README.md` lists 6 (S1 to S6). Among them: each
modified file differs from the unmodified one only inside 1 function and
keeps every line number; each tool mutant has the syntax tree of the mutant
that mutmut writes; the unmodified copies give the deposited baseline of
`../target-reach/`; and the deletion of each check that the deposited
`deletions.csv` of `../target-reach/` lists gives here what was recorded
there, under each oracle and in the whole suite. A sentinel that does not
hold is reported with its detail; the numbers of that library are then not
used before the cause is found and stated in `DEVIATIONS.md`.

### 4.4 Recounts

`recount/recount.py` computes, from the deposited outputs of `../target-reach/`
alone: O_T against the deciding checks that are the target of at least 1 case
they decide; the deletions of checks that fire and decide no case, per oracle;
the cases decided by a statement that is not a check; flags per tier and per
class of the first reading; and the flags whose own test passes on the copy
without the deciding check. `recount/README.md` defines each count. The
recounts have no expectation. They were first computed before this commit
(section 5).

### 4.5 Interpreter versions

The test of PyJWT that `../mutation-adequacy-pyjwt/version-check/` ran on
CPython 3.9 to 3.12 is run in the same way on 3.13 and 3.14; this was done
before this commit (section 5, `versions/`). After the commit, the tests that
hold a shadowed case, and their variants, are run on the unmodified library
under CPython 3.13 with the packages of the subject's environment, and the
check that decides each is recorded.

## 5. What had been done before this commit

On PyJWT and jwcrypto, the 2 libraries on which `../target-reach/` was
developed, the programs of this folder were written and tried:

- `labels/`: on PyJWT with the labels of the reference study, and on jwcrypto
  with a pack and made-up labels files (`labels/README.md`, section
  "Development runs").
- `trace/`: on both (`generated/trace/`), with rule 3 computed for both.
- `mutants/`: on PyJWT, for the 2 modules of the reference study
  (`generated/mutants/pyjwt-package/`): 1094 tool mutants and 46 deletions,
  with all 6 sentinels holding. On jwcrypto the tool mutants of 2 files were
  made (2508; sentinels S1 and S2 held) and their runs were stopped after 121
  mutants; no result of those runs was read, and nothing of them is
  deposited.
- `versions/`: the test of the nested header of PyJWT under CPython 3.12,
  3.13 and 3.14 (`versions/results.jsonl`).

On the 4 held-out libraries:

- Their results in `../target-reach/` were known, with its readings of the
  flags. While this protocol was written, the deposited outputs of joserfc
  were read again; they show that the case `test_header_exceeds_size#0` of
  `tests/jwe/test_compact.py`, to which the program gave no target, is decided
  by the same check as the class-A case `test_ciphertext_exceeds_size#0`.
- `recount/recount.py` had been run on their deposited outputs
  (`generated/recount/`).
- The flags of `../target-reach/readings/` had been transcribed into
  `labels/first/`, from the deposited `flags.csv`, `cases.csv`, `checks.json`
  and `FLAGS.md` of each library.
- For the 3 class-A cases of joserfc, repaired variants had been written in
  `repaired/joserfc/` and run on the unmodified library, together with the 3
  original tests and the whole suite, to read the check that decides each.
- `mutants/cases_file.py` had been run on their deposited outputs with an
  outcomes file that holds no row. It lists the 3 class-A cases of joserfc,
  the 4 files of their checks and 15 comparison cases in those files; for the
  other 3 libraries it lists nothing.
- An environment with CPython 3.13.14 and the packages of joserfc's
  environment had been prepared. Nothing had been run in it.
- No reading pack had been built and no label had been made for any of their
  blocks, by `labels/INSTRUCTION.md` or otherwise, apart from the first
  readings of the flags.
- No suite of theirs had been run under `trace/plugin.py`, and rule 3 had not
  been computed for any of them.
- No tool mutant of any of them had been made, and no check that the deposit
  does not already delete had been deleted.

## 6. Order of execution

1. This commit; time stamps; a commit with the tokens.
2. Labels. Packs are built for the 4 libraries and split into parts. Readings
   A and B are made. `labels/check_labels.py` checks each file for form only.
   The label files are committed as they are, the commit is time-stamped, and
   only then is any label compared with a record, a target or the other
   reading. A label is not changed after that commit.
3. Rule 3. The suites are traced, rule 3 is computed, and the analysis runs on
   the deposited records. This step uses no label and may run while step 2
   runs.
4. `labels/analyse_labels.py` runs for each library with the 2 readings, the
   targets of rule 2 and of rule 3.
5. Shadowed cases are listed (section 4.1, `mutants/cases_file.py`). For
   each one that has no variant yet, a variant is attempted and verified;
   `repaired/<name>/variants.tsv` names the variant of each case.
6. Mutants. Tool mutants and deletions are made for the files of section 4.3,
   run and analyzed.
7. Interpreter versions (section 4.5).
8. A second script, written from this protocol without sight of the first
   programs' analysis code, recomputes the counts of steps 3, 4 and 6 from
   their records, and every difference is resolved or reported.
9. Results, readings of the new flags and deviations are committed, and the
   commit is time-stamped.

A defect of a program found after step 1 is corrected, described in
`DEVIATIONS.md` with the change, and every run that used the program is
repeated. A sentinel that does not hold stops the step.

## 7. Outputs

| Path | What it holds |
|---|---|
| `labels/` | The instruction, the programs, the transcribed first readings |
| `labels/readings/<name>/A.tsv`, `B.tsv`, `parts.tsv` | The 2 readings and the parts |
| `generated/labels/<name>/` | Agreement, outcomes of the cases, program against label |
| `trace/` | The trace plugin, rule 3, its analysis |
| `generated/trace/<name>/` | Functions started under an entry point, targets of rule 3, the comparison with rule 2 |
| `mutants/` | The programs that make, run and score the mutants |
| `repaired/<name>/` | Repaired variants and their verification |
| `generated/mutants/<name>/` | Shadowed cases, mutated files, mutants, runs, kills per case and per test, mutants at each check, scores |
| `recount/`, `generated/recount/` | The recounts |
| `versions/` | Scripts and results for the interpreter versions |
| `recompute/` | The second computation |
| `timestamps/` | Tokens |
| `DEVIATIONS.md` | Deviations from this protocol |

`work/` (copies, environments, logs, raw records, reading packs) is not
deposited.

## 8. Limits known in advance

- The 2 readings follow 1 instruction and can share its blind spots.
  Agreement between them shows that the instruction can be applied
  consistently; it does not show that a label is right.
- A label uses the name, docstring and comments of a test and its assertions.
  A test that names nothing gets no label, so the labels cover a part of the
  blocks, and that part is not a random sample.
- A shadowed case is defined through 1 deletion: a case stopped by 2 earlier
  checks has outcome 8 and is not counted as shadowed.
- Rule 3 takes reachability from the library's own suite; a function that no
  test runs under an entry point stays reachable by name only. A run of the
  suite can differ from the next; section 4.2 states the repeats.
- Tool mutants come from 1 tool with its default operators, in the files of
  the shadowed cases only; the kills of a test at a check depend on which
  mutants the tool creates there.
- A repaired variant is 1 input among many; another input could kill other
  mutants.
- The follow-up was designed with the results of `../target-reach/` in view.
  The 4 libraries are held out for the labels, for rule 3 and for the mutants
  in the sense of section 5 only.
