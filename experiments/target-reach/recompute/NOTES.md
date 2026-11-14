# Second computation: notes

`PROTOCOL.md`, section 6, step 7, asks that every reported count be
recomputed from the deposited records by a second script, written from the
protocol without sight of `reach/analyse.py`, `reach/report.py` and
`reach/study.py`. This folder holds that script and its comparison with the
first analysis. It was written, compared and reviewed on the 3 development
subjects (`pyjwt`, `pyjwt-package` and `jwcrypto`), and then applied without
a change to the 4 held-out libraries (last section). In the sections before
the last, "the 3 subjects" are the development subjects.

| File | What it holds |
|---|---|
| `second.py` | The second computation for 1 subject: definitions beside `subject.json`, records from `records.tar.xz` |
| `compare.py` | The table that maps each compared count of `second.py` to its place in `generated/<name>/summary.json`; exits with 1 when a compared count differs |
| `out/<name>/second.json` | The output of `second.py` for each subject |
| `NOTES.md` | This file |

Both scripts use the standard library of Python 3.12 only and import nothing
from `reach/` or `guard/`.

    python3 -I -B recompute/second.py --subject subjects/<name>/subject.json \
        --records generated/<name>/records.tar.xz --out recompute/out/<name>/second.json
    python3 -I -B recompute/compare.py --second recompute/out/<name>/second.json \
        --first generated/<name>/summary.json

## Sources read

`second.py` was written from `PROTOCOL.md` and `README.md`, and from the
formats of the records and of the definitions as `reach/recorder.py`,
`reach/run.py`, `reach/checks.py`, `reach/blocks.py`, `reach/targets.py`,
`reach/delete.py` and `guard/reach_offline.py` give them. `reach/analyse.py`,
`reach/report.py`, `reach/study.py`, `validate_pyjwt.py` and `tests/` were
not read. Until the blind outputs were frozen, nothing under `generated/`
other than the 3 `records.tar.xz` files was read, and nothing under
`readings/` and `witnesses/`. The definitions (`checks.json`, `blocks.json`,
`targets.json`) are taken as given: the second script does not enumerate
checks or blocks from the sources again and does not apply the target rule
again.

## Freeze of the blind state

Before `summary.json` was read, the script and its 3 outputs were copied
aside and their SHA-256 values written:

    9e9a5a9e3182ddba56a914aca852a10fdcb8ba3f3d33c73fb55ec64831748d79  second.py
    84d2149e94cf3d878a6ed394bd8cf6e2fd1394d85267260219940e910728619c  pyjwt.json
    cc9aeb0b19de94e38ba4370faf4e5267820d44464d76e869c649b00023578eac  pyjwt-package.json
    e2f95b842223184ed19838219677a620e24b1d2fee502ab97e8e0d1c283198a4  jwcrypto.json

These copies are not deposited here; the values identify the blind version.

## First comparison

| Subject | Counts compared | Agree | Differ |
|---|---|---|---|
| pyjwt | 132 | 131 | 1 |
| pyjwt-package | 132 | 132 | 0 |
| jwcrypto | 142 | 142 | 0 |

The compared counts cover the checks, reachable checks, deciding checks,
checks that fire and never decide; blocks, included blocks, class-only
blocks; cases and cases left out; Q1 by tier and by outcome, and the flags;
Q2 per oracle for deciding checks and for checks that fire and never decide,
with the withheld-as-failing columns and the identifiers of the deletions
not detected, the time limit, the repeated runs, the runs without a record or
a result, the 5 inclusions, and the witness files; Q3 by kind of block, with
the cases not counted by reason, and the own test on the copy without the
target; the expected baseline failures, the files not collected, the copies
deselected and kept, nested cases, firings in other threads, the refused
connection attempts; and the 7 sentinels.

### Disagreement 1: blocks of `pyjwt`

- Second (blind): 179. First: 215.
- The blind script counted the blocks of the test files that hold at least 1
  included block (4 files). The first output counts the blocks of all 10 test
  files that `blocks.json` lists for `subjects/pyjwt`.
- Section 4, 'Block': "The block counts of a subject cover the test files of
  its recorder runs, which are the files with at least 1 included block;
  `scope_counts` in `subject.json` gives the number of test files and of
  blocks over the test directories. `subjects/pyjwt` names its test directory
  by hand, as the reference study did, and has no `scope_counts`." Section
  4, 'Runs': "A *recorder run* runs the test files of the subject".
- The recorder runs of `pyjwt` run its whole hand-named test directory: the
  baseline recorder record holds tests from all 10 files. The governing words
  are "the test files of its recorder runs"; the clause "which are the files
  with at least 1 included block" describes the subjects defined by the 6
  decisions (section 3: "the test files of the recorder runs are those that
  hold at least 1 included block"), and the next sentence names `pyjwt` as the
  subject whose directory is named by hand. The first value, 215, follows the
  protocol; the blind script misread the appositive clause as the
  definition.
- Change: `second.py` now counts the blocks of the test files of the
  recorder runs (`blocks_in_test_files_of_the_recorder_runs`, the files that
  `blocks.json` lists for the subject's test paths) and keeps the blind count
  under `blocks_in_test_files_with_an_included_block`. For `pyjwt-package`
  and `jwcrypto` both counts are equal (179 and 94). Because the clause can
  be read the other way for `pyjwt`, the sentence is also listed below.

No count of the first analysis was found to depart from the protocol.

## Final comparison

| Subject | Counts compared | Agree | Differ |
|---|---|---|---|
| pyjwt | 132 | 132 | 0 |
| pyjwt-package | 132 | 132 | 0 |
| jwcrypto | 142 | 142 | 0 |

`compare.py` exits with 0 on all 3 subjects. All 7 sentinels hold in both
computations for all 3 subjects.

The 5 expectations are not in `summary.json` (`reach/report.py` states
them) and are therefore not compared. The second computation gives:

| | pyjwt (reference scope) | pyjwt-package | jwcrypto |
|---|---|---|---|
| E1 | held (5 of 41) | held (7 of 44) | held (4 of 16) |
| E2 | held (2 of 41) | held (4 of 44) | held (4 of 16) |
| E3 | held (41 of 41) | held (44 of 44) | held (16 of 16) |
| E4 | held (1 of 49) | held (1 of 49) | held (4 of 14) |
| E5 | not stated (1 of 27; 29 of 79 included blocks class-only) | not stated (1 of 30; 29 of 79) | not held (0 of 42; 42 of 42) |

The columns for `pyjwt-package` and `jwcrypto` equal the 2 columns of the
table of section 2.

Counts of either file without a counterpart: the first output also gives
counts that section 7 does not name (targets by basis, cases in which another
check fires too, deletions in a handler, included blocks never run, tests
with cases, reached targets, and others); the second output also gives
per-item lists, the expectations, sub-counts by file role, and the detail of
each sentinel. `compare.py` lists them on every run. The flags by class (A to
D) are a reading of the sources and are not computed by either script.

## Sentences of the protocol that allow 2 readings

1. Section 4, 'Block': "The block counts of a subject cover the test files of
   its recorder runs, which are the files with at least 1 included block".
   For `pyjwt`, whose recorder runs cover a hand-named directory, the 2 parts
   of the sentence name different sets: 215 blocks in 10 files or 179 blocks
   in 4 files. The 3 subjects are otherwise unaffected.
2. Section 7: "checks, reachable checks". For `pyjwt`, which has an observed
   file, "checks" can mean all 80 checks or the 46 of the subject files, and
   "reachable checks" 54 or 46. Both computations report 80 and 54; the second
   also gives the counts in subject files.
3. Section 4, 'Status of a case': "A crash of any case counts as a detection
   under O_V, O_Vfc, O_C, O_T and O_S." Read literally, a crash detects under
   O_T even for a case without a target or not decided by its target, whereas
   'Oracles' asks that "the oracle holds for a case of the study at baseline".
   The second script takes the literal reading. No case crashed in any
   deletion run of the 3 subjects, so the reading changes no count.
4. Section 4, 'Status of a case': "a second set of columns, for the 4 case
   oracles O_V, O_Vfc, O_C and O_T, counts them as failing". The second script
   counts a withheld case as failing only for an oracle that holds for it at
   baseline (for O_T, a case decided by its target). 1 deletion has withheld
   cases (`api_jws.PyJWS._verify_signature#6`, in both PyJWT scopes); the
   counts agree under this reading.
5. Section 4, 'Status of a case', rule 2: "*withheld* when the test then
   stopped, a skip included". The second script reads "stopped" as a setup or
   a body that did not pass (failed or skipped). Rule 2 applies to 1 case of
   the 3 subjects: block 1 of `TestJWS::test_bad_secret` under the deletion
   of `api_jws.PyJWS._verify_signature#6`, in both PyJWT scopes. Its test
   has a failed block and its body then stopped on an `AssertionError`, so the
   case is withheld under either reading. Every other case of every deletion
   run of the 3 subjects is observed; no case is crashed or missing.
6. Section 2: the order of the 4 rules is not stated where 2 of them apply at
   once (a sentinel that does not hold, and E5 below the share of class-only
   blocks). The second script gives "no verdict" precedence. All sentinels
   hold here, so the order changes nothing.
7. Section 4, 'Sentinels', sentinel 2: "every test file is collected". It can
   be read on the baseline recorder run alone or also on the run without the
   recorder, whose files that cannot be collected are ignored by the recorder
   runs. The second script requires both; both are empty here.
8. Section 4, sentinel 5, and section 7, "the cases of nested blocks, the
   cases with a firing in another thread": these can be read over the cases
   of the study or over every recorded execution of an included block. The
   second script reports both; every count is 0 here, and every recorded
   execution is a case of the study.
9. Section 4, 'Pinning': "what the case does when the test still passes"
   names no categories. The first output labels the 1 such case of each PyJWT
   scope "same class, another check"; the second labels it by status and
   class ("observed: raises the class it raises at baseline"). The number of
   such cases agrees; the labels are not compared.

## Review of the second script against the protocol

A reading of `second.py` against `PROTOCOL.md` gave 8 findings. Each was
checked against the sentence of the protocol it cites, in its context. A
finding is accepted only where the code departs from the protocol; the reason
of every change is a sentence of the protocol. The version before this review
is identified by its SHA-256 value below and is not deposited here.

    e56090fb9742396f4e64d0578d6aa7bf0b9f4ec83d9b6f2e87407c599b4cdd7b  second.py (before the review)

### F1, sentinel 2 on the run without the recorder: accepted

- Section 4, sentinel 2: "In the baseline recorder run every test passes or
  is skipped, every test file is collected, and the tests deselected are the
  expected baseline failures." Section 4, 'Baseline': "A test file that
  pytest cannot collect in this run is ignored in every recorder run and
  listed."
- The script also failed sentinel 2 when the run without the recorder listed
  a file it could not collect. The sentence names the baseline recorder run,
  and the protocol provides for such a file: it is ignored and listed.
- Change: sentinel 2 reads the collection errors of the baseline recorder run
  only. The stricter reading (reading 7 below) is kept as an alternative
  status, with the verdicts it gives
  (`sentinels_alternative_readings`, `verdict_under_alternative_readings`).
- Counts: no file fails to collect in the 3 subjects; no count changed.

### F2, sentinel 4 and the control copy: accepted

- Section 4, 'Time limit': "The recorder run of a deletion copy or of the
  control copy may take 10 times ... When a run gives no record 2 times
  without both exceeding the limit, sentinel 4 does not hold".
- The script left the control copy out of sentinel 4. Change: the control
  copy is included.
- Counts: the control copy of each of the 3 subjects gave a record; no count
  changed.

### F3, sentinel 3 and a deletion that exceeded the time limit 2 times: accepted in part

- Section 4, 'Sentinels': "a sentinel whose other records are absent (the
  deletion runs, the control copy, the whole-suite runs) does not hold";
  section 5: "sentinel 3 needs the records of the deletion runs". Against
  this, sentinel 4 ("Every deletion run gave a record or exceeded the time
  limit 2 times") and 'Time limit' ("When both runs exceed the limit, the
  deletion counts as detected ... and its cases are counted apart") treat a
  deletion without a record after 2 time-outs as a regular outcome.
- The script follows the first sentence, which is a reading of the protocol,
  not a departure from it. The finding is right that section 4 does not
  decide between the 2 and that section 6, step 7, then asks for both
  ("Where section 4 does not decide, both counts are reported").
- Change: the primary status of sentinel 3 is unchanged; the status under
  which such a deletion is excused is added as an alternative reading, with
  the verdicts it gives (reading 10 below).
- Counts: no deletion run of the 3 subjects exceeded the time limit; no count
  changed.

### F4, sentinel 5 over every case: accepted

- Section 4, sentinel 5: "The check that decides a case is among the checks
  that fire in it." Section 4, 'Case': a case is "1 execution of an included
  block in 1 test"; "The *cases of the study* are the cases in which ...".
  'Deciding check' defines the raise site and "decides" for a case.
- The script decided sentinel 5 on the cases of the study. The sentence says
  "a case", which section 4 keeps apart from "case of the study". Change:
  sentinel 5 is decided on every recorded case; the list over the cases of
  the study stays in the detail. Reading 8 below no longer applies to
  sentinel 5.
- Counts: every recorded case of the 3 subjects is a case of the study;
  sentinel 5 holds under both scopes; no count changed.

### F5, runs repeated and runs that ended without a record or a result: accepted

- Section 4, 'Time limit': "A run that gives no record, because it exceeded
  the limit or because the interpreter ended before the record was written,
  is repeated 1 time" and "The summary lists every run that was repeated and
  every run that ended without a record or a result." Section 7: "the runs
  that were repeated and the runs that ended without a record or a result".
- The script counted 1 entry per copy whose final run failed. A run is
  repeated because it ended without a record or a result, so each first
  attempt that was repeated is such a run, and a copy that failed 2 times
  has 2 such runs. Change: `runs_that_ended_without_a_record_or_a_result`
  lists every such run (recorder and whole-suite, first and repeated
  attempts) and `runs_without_a_record_or_a_result` counts them; the count
  per copy stays as `copies_whose_final_run_ended_without_a_record_or_a_result`.
  The whole-suite runs that exceeded the time limit are now listed apart from
  those that left no result file (final run, and any attempt), and
  `compare.py` maps the 2 final-run lists to the 2 lists of the first output.
- Counts: no run of the 3 subjects was repeated; the count stays 0 in each.

### F6, outcomes per tier: accepted

- Section 4, 'Target': "Targets assigned from classes and assertions alone
  form the *assertion tier*, those that needed the name of the test the
  *name tier*. Counts are reported per tier."
- Change: `Q1/outcomes_by_tier` gives the 4 outcomes and the 5th value per
  tier. These counts are new; the first output has no counterpart.

| Subject | Tier | Decided by the target | Fires, another decides | Fires, none decides | Does not fire |
|---|---|---|---|---|---|
| pyjwt | assertion | 42 | 0 | 0 | 0 |
| pyjwt | name | 6 | 0 | 0 | 1 |
| pyjwt-package | assertion | 42 | 0 | 0 | 0 |
| pyjwt-package | name | 6 | 0 | 0 | 1 |
| jwcrypto | assertion | 6 | 0 | 0 | 0 |
| jwcrypto | name | 4 | 3 | 0 | 1 |

The 5th value, "not decided by the target", is 0 everywhere.

### F7, absent and empty manifest: accepted

- Section 4, sentinel 7: "The deleted checks are the checks of the subject
  files that fire in at least 1 case of the study." Sentinel 3: "Under the
  deletion of a check, that check fires in no case."
- With no check of the subject files firing in a case of the study, the
  manifest is present and empty, and both sentinels hold. The script treated
  an empty manifest as an absent one. Change: an absent manifest (records
  absent) still fails both sentinels; an empty one does not.
- Counts: the manifest of each of the 3 subjects is present and not empty; no
  count changed.

### F8, an empty pattern: accepted

- Section 4, 'Block': "A block *asserts more than the class* when it gives a
  pattern or the test asserts on the caught exception afterwards".
- `blocks.json` stores an absent pattern as null and a literal pattern as a
  string, the empty string included. The script read an empty pattern as no
  pattern. Change: a block gives a pattern when its stored pattern is not
  null.
- Counts: no block of the 3 subjects has an empty pattern; the class-only
  counts are unchanged (29 of 79 included blocks in both PyJWT scopes, 42 of
  42 in `jwcrypto`).

### Counts of section 7 named as missing

- The 4 outcomes per tier: added (F6).
- The whole-suite runs that exceeded the time limit, as a separate list, and
  the runs that ended without a record or a result, per run: added (F5).
- The flags by class (A to D): a reading of the sources (section 6, step 4);
  not computed.
- The deviations (`DEVIATIONS.md`): not derivable from the records; not
  computed.
- The result of the second computation: given by `compare.py` and this file,
  not by `second.py`.

### Comparison after the review

| Subject | Counts compared | Agree | Differ |
|---|---|---|---|
| pyjwt | 134 | 134 | 0 |
| pyjwt-package | 134 | 134 | 0 |
| jwcrypto | 144 | 144 | 0 |

`compare.py` exits with 0 on all 3 subjects. The 2 new rows are the
whole-suite lists of F5. No count of a development subject changed value;
the corrections act only on records that the 3 subjects do not hold (a file
not collected, a control copy or a deletion without a record, a repeated
run, an empty manifest, an empty pattern, a left-out case whose deciding
check does not fire). The paths of F1, F2, F3 and F5 were exercised on
altered copies of the `pyjwt-package` records outside this folder (a file
not collected; a control copy without a record 2 times; a deletion that
exceeded the time limit 2 times; a repeated recorder run and a repeated
whole-suite run), and each gave the status and the counts that the protocol
sentences above ask for. The paths of F4, F7 and F8 were not exercised on
altered records. All 7 sentinels hold
under the primary readings and under both alternative readings, and the 5
verdicts are unchanged.

### Sentences with 2 readings added by the review

10. Section 4, 'Sentinels', and sentinel 3, against sentinel 4 and 'Time
    limit': a deletion whose recorder run exceeded the time limit 2 times
    has no record. Under the first reading sentinel 3 does not hold (its
    records are absent); under the second the deletion is excused. Both
    statuses and the verdicts under both are reported.

Reading 7 above is now resolved by the sentence of sentinel 2 for the
primary status, and the stricter reading is reported beside it.

## The 4 held-out libraries

On 14 November 2026 at 09:51 UTC, after the first analysis of each held-out
library had been written, `second.py` and `compare.py` were applied to all 7
subjects in 1 pass. The 2 files are those of the section 'Comparison after
the review':

    1ca6864a53bfd45d689cecd5da12319611b506adc7f587e3dc10c3d7217a10dd  second.py
    65726dc8c9a7bd8256166f10528a08a9a4acca5296e889a4b76294c7302311a1  compare.py

Neither file was changed after it first read the records of a held-out
library.

| Subject | Counts compared | Agree | Differ | Absent from 1 file |
|---|---|---|---|---|
| pyjwt | 134 | 134 | 0 | 0 |
| pyjwt-package | 134 | 134 | 0 | 0 |
| jwcrypto | 144 | 144 | 0 | 0 |
| google-auth | 134 | 134 | 0 | 0 |
| oauthlib | 134 | 134 | 0 | 0 |
| authlib | 138 | 138 | 0 | 0 |
| joserfc | 138 | 138 | 0 | 0 |

`compare.py` exits with 0 on each subject. A subject with witness files has
2 more compared values per file. All 7 sentinels hold in both computations
for each of the 4 libraries, under the primary readings and under both
alternative readings.

The 5 expectations, as `second.py` derives them from the records:

| | google-auth | oauthlib | authlib | joserfc |
|---|---|---|---|---|
| E1 | held (2 of 13) | held (7 of 47) | held (3 of 24) | held (12 of 53) |
| E2 | held (1 of 13) | held (7 of 47) | not held (0 of 24) | held (10 of 53) |
| E3 | held (13 of 13) | held (47 of 47) | not held (21 of 24) | not held (51 of 53) |
| E4 | held (2 of 15) | held (10 of 53) | held (12 of 30) | held (60 of 131) |
| E5 | not stated (0 of 17 included blocks class-only) | not held (0 of 140) | held (3 of 40) | held (4 of 168) |

Status and counts equal those of `generated/report.json` for the 4 libraries,
for `pyjwt-package` and for `jwcrypto`.

The 4 outcomes per tier (F6), which the first output gives only as flags per
tier:

| Subject | Tier | Decided by the target | Fires, another decides | Fires, none decides | Does not fire |
|---|---|---|---|---|---|
| google-auth | name | 13 | 0 | 0 | 2 |
| oauthlib | assertion | 25 | 0 | 0 | 0 |
| oauthlib | name | 18 | 0 | 0 | 10 |
| authlib | assertion | 5 | 0 | 0 | 0 |
| authlib | name | 13 | 0 | 0 | 12 |
| joserfc | assertion | 46 | 0 | 0 | 53 |
| joserfc | name | 25 | 0 | 0 | 7 |

`google-auth` has no target of the assertion tier. The last column equals the
flags per tier of the first output (0 and 2, 0 and 10, 0 and 12, 53 and 7).

Which of the sentences with 2 readings the records of the 4 libraries
exercise:

- Readings 4 and 5 (withheld cases): 37 cases of 4 deletions of `oauthlib`
  are withheld; every other case of every deletion run of the 4 libraries is
  observed (286, 6,637, 1,152 and 10,450 cases). The columns that count
  withheld cases as failing equal the main columns, in both computations.
- Reading 3 (a crash under O_T): no case crashed in any deletion run.
- Readings 1 and 2: each library has its `scope_counts` and no observed
  file; the 2 block counts are equal (21, 98, 91 and 193).
- Readings 7, 8 and 10 and the paths of F1, F2, F3, F5 and F7: no test file
  failed to collect, no block is nested, no check fired in another thread,
  no run was repeated, no run exceeded the time limit, and every manifest is
  present and not empty.
- Reading 9: the labels of the cases whose test still passes are not
  compared; their numbers agree (0, 0, 3 and 4).

6 cases of the study of `authlib` are decided by no check: the statement
that raises their exception takes its class from a parameter
(`raise error_cls(...)` in `authlib/jose/util.py`), so it constructs no
rejection class by name and is not a check. Both computations leave these
cases out of the pinning counts (42 of 48 cases counted) and keep them among
the cases whose target does not fire.

Limits of this comparison. The second script takes `checks.json`,
`blocks.json` and `targets.json` as given. It reads whether the whole suite
detects a deletion from the outcome recorded for each whole-suite run,
because the result files of those runs are not in `records.tar.xz`. The
flags by class and the readings of the undetected deletions
(`readings/<name>/`) are not computed by either script.
