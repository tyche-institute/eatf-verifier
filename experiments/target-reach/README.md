# Target reach: declared targets and check deletions on more verification libraries

The study in `../mutation-adequacy-pyjwt/` asked 2 questions about the negative
tests of PyJWT 2.15.1, without a mutation tool. Does the check that rejects
the input of a negative test match the check the test describes? And when a
check that rejects those inputs is deleted, which test oracles notice? Its
targets were labels written by hand.

This folder holds a toolkit that asks both questions of any Python
verification library that raises exceptions to reject, with the targets
assigned by a fixed rule, and an experiment that applies it to 4 more
libraries under a protocol fixed in advance.

## Status

The commit that adds this folder fixes `PROTOCOL.md`. Right after it, a text
that names the commit is time-stamped by 2 authorities, and a later commit
adds the tokens in `timestamps/`. Before the protocol, the toolkit was built
on PyJWT and exercised on a pilot, `jwcrypto` 1.6.1; section 5 of the
protocol says exactly what had been done on each subject. At the protocol
commit, no target had been computed, no test had been run under the recorder
and no check had been deleted on the 4 held-out libraries. Their targets
came with the commit after the tokens. Their outputs, readings and witness
tests, the deviations and the second computation came with the commit after
the run of 14 November 2026 ("Results on the 4 held-out libraries" below).

| Subject | Version | Role | Outputs |
|---|---|---|---|
| PyJWT, scope of the reference study | 2.15.1 | development; compared with the reference study | `generated/pyjwt/` |
| PyJWT, whole package | 2.15.1 | development; the row shown beside the others | `generated/pyjwt-package/` |
| jwcrypto | 1.6.1 | pilot | `generated/jwcrypto/`, `readings/jwcrypto/`, `witnesses/jwcrypto/` |
| google-auth | 2.62.2 | held out | `generated/google-auth/`, `readings/google-auth/` |
| oauthlib | 4.0.1 | held out | `generated/oauthlib/`, `readings/oauthlib/` |
| authlib | 1.9.5 | held out | `generated/authlib/`, `readings/authlib/`, `witnesses/authlib/` |
| joserfc | 1.8.0 | held out | `generated/joserfc/`, `readings/joserfc/`, `witnesses/joserfc/` |

`SELECTION.md` records how the 4 libraries and the pilot were chosen from the
1,000 most-downloaded projects of the Python Package Index, and why they are
4 and not 3.

## What the toolkit does

For 1 subject, defined in `subjects/<name>/subject.json`:

1. **Checks.** It lists the raise statements that construct a rejection
   class, grouped per function by class and message template, and marks those
   reachable by name from the entry points.
2. **Blocks.** It lists the negative-test blocks (`pytest.raises`,
   `assertRaises` and its variants, as a `with` statement or with a callable)
   and keeps those that call an entry point and expect rejection classes.
3. **Targets.** A fixed rule assigns each block the check it describes, from
   the expected classes, the block's assertions and the name of the test
   (`reach/targets.py`). It never reads a run.
4. **Baseline.** A pytest plugin records, for each execution of a block, the
   exception, the check that raised it, and every check that fired while the
   block was open, including those whose exception a handler caught.
5. **Deletions.** Each check that fires in those tests is deleted in a copy
   of the package: its raise statements become `pass`. The negative tests run
   on the copy under the recorder, and the whole suite runs on it without the
   recorder.
6. **Analysis.** `reach/analyse.py` reports, for each case with a target, 1 of
   4 outcomes, from "the target decides the case" to "the target does not
   fire"; which oracles detect each deletion; and whether the own test of a
   case fails when its deciding check is deleted. It writes its outputs and
   then exits with an error unless 7 sentinels hold.
7. **Witness tests.** For a deletion that the whole suite does not detect, a
   new test can be put in `witnesses/<name>/`. The `witness` step runs it on
   the unmodified copy and on the copy without the check. The file holds
   when every test of it passes on the first and at least 1 fails on the
   second.
8. **Report.** `reach/report.py` puts the subjects side by side and states the
   5 expectations of the protocol for each library. A library in which a
   sentinel does not hold gets no verdict.

Every pytest call of the study refuses and counts attempts to reach another
machine (`guard/reach_offline.py`).

`PROTOCOL.md`, section 4, defines every term.

## Layout

| Path | What it holds |
|---|---|
| `PROTOCOL.md` | Questions, expectations, subjects, definitions, what had been done before, order of execution, limits |
| `SELECTION.md` | Frame, criteria, screening of the 50 candidates, recount, releases, the 2 readings for `google-auth` |
| `selection/` | Scripts and data of the selection: the frame, the screening, the recount (`recount.sh`, `survey.py`, `recounts.txt`) and the offline check (`offline_check.py`, `offline-check.txt`) |
| `subjects/<name>/` | `draft.json` (the 6 decisions and their sources; `subjects/pyjwt` has none), `subject.json`, `checks.json`, `blocks.json`, `targets.json` (at the protocol commit, for PyJWT and the pilot only), `requirements.txt` (the environment the tests ran in) |
| `reach/__init__.py` | Makes `reach/` a package |
| `reach/scope.py` | Derives `subject.json` from `draft.json` |
| `reach/checks.py` | Lists the checks and the reachability by name |
| `reach/blocks.py` | Lists the negative-test blocks and their assertions |
| `reach/targets.py` | The target rule `reach-target-rule/2`; its header states the rule in full |
| `reach/recorder.py` | The pytest plugin |
| `reach/delete.py` | Replaces the raise statements of 1 check by `pass`, keeping every line number |
| `reach/run.py` | The steps `define`, `targets`, `verify`, `suite`, `baseline`, `deletions`, `whole-baseline`, `whole-deletions`, `witness`, `pack` |
| `reach/study.py` | The rules that the runner and the analysis share |
| `reach/analyse.py` | Writes `generated/<name>/` |
| `reach/report.py` | Writes `generated/REPORT.md` and `generated/report.json`: the subjects side by side and the 5 expectations |
| `guard/reach_offline.py` | The pytest plugin that refuses and counts outside connections |
| `validate_pyjwt.py` | Compares the PyJWT outputs with the reference study, which it only reads, and writes `generated/pyjwt/VALIDATION.md` |
| `tests/` | Unit and end-to-end tests of the toolkit on small synthetic packages |
| `generated/<name>/` | `SUMMARY.md`, `summary.json`, `cases.csv`, `checks.csv`, `deletions.csv`, `flags.csv`, `pinning.csv`, `undetected.csv`, `records.tar.xz` (the records that the analysis reads), `SHA256SUMS`; for `pyjwt` also `VALIDATION.md`, written by `validate_pyjwt.py` and not listed in `SHA256SUMS` |
| `readings/<name>/` | `FLAGS.md` and `UNDETECTED.md`: readings of the sources, with reasons, reported apart from the counts |
| `witnesses/<name>/` | Witness tests |
| `timestamps/` | Time-stamp tokens; added by the commit after the protocol commit |
| `recompute/` | The second computation of step 7 of the protocol: `second.py`, `compare.py`, `out/<name>/second.json` and `NOTES.md` |
| `DEVIATIONS.md` | Deviations from the protocol and corrections of committed texts |
| `.gitignore` | Keeps `work/` and `__pycache__/` out of the deposit |

`work/` (clones, copies, logs, raw records, virtual environments) is not
deposited; `records.tar.xz` holds the records the analysis reads. The result
files of the whole-suite runs, the logs and the timings are not in it.

## How to run

The toolkit needs the standard library of Python 3.12 or later. The recorder
imports pytest from the environment of the subject and takes the fired checks
from `sys.monitoring`, which exists from Python 3.12. The environment of a
subject is CPython 3.12.3 with the packages of its `requirements.txt` and
nothing else but `pip`; `verify` refuses any other.

    python3.12 -m venv <env> && <env>/bin/pip install -r subjects/<name>/requirements.txt
    git clone <repository of subject.json> <clone> && git -C <clone> checkout <commit of subject.json>

    export PYTHONHASHSEED=0
    python3 -I -B reach/run.py define targets verify baseline deletions \
        whole-baseline whole-deletions pack \
        --subject subjects/<name>/subject.json --clone <clone> --python <env>/bin/python
    python3 -I -B reach/analyse.py --subject subjects/<name>/subject.json

`--clone` and `--python` are remembered in `work/<name>/local.json`. Where
`subject.json` names a `repository_directory`, as for `google-auth`, `--clone`
is that directory inside the clone (`<clone>/packages/google-auth`). The
clone is only read: every run uses its own copy. `verify` refuses a clone
that is not at the commit, or whose copied paths hold a changed, untracked
or ignored file. `--workers` (default 10) sets the number of deletion copies
that run at a time, for the recorder runs and for the whole-suite runs. For a
subject whose `draft.json` exists, `reach/scope.py --draft
subjects/<name>/draft.json --clone <clone>` writes `subject.json` first.

The definitions in `subjects/` are those of the protocol, and `define`
writes the same files again. For PyJWT and the pilot the same holds for
`targets`. For the 4 held-out libraries, `targets` writes `targets.json` for
the first time after the protocol commit (`PROTOCOL.md`, section 6); a later
run starts from `verify`.

The analysis can also run from the deposited records alone:

    mkdir -p <dir> && tar -xJf generated/<name>/records.tar.xz -C <dir>
    python3 -I -B reach/analyse.py --subject subjects/<name>/subject.json --work <dir> --out <out>

The table across subjects, once every named subject has its outputs:

    python3 -I -B reach/report.py --held-out google-auth oauthlib authlib joserfc \
        --reference pyjwt-package --pilot jwcrypto

The tests of the toolkit, and the comparison with the reference study:

    PYTHONPATH=. <env with pytest>/bin/python -B -m pytest -q -p no:cacheprovider tests
    <env of pyjwt>/bin/python -I -B validate_pyjwt.py

## Before the protocol: PyJWT and the pilot

On PyJWT in the scope of the reference study, the toolkit finds the 44 checks
of that study and 2 more, the same 79 included blocks and the same raise site
for all 91 cases, and it gives the same detection for all 41 deletions under
each of the 3 oracles compared, O_V, O_Vfc and O_C
(`generated/pyjwt/VALIDATION.md`). The rule agrees with the hand label on all
47 blocks where both assign a target; it was developed with those labels in
view, so this is not an independent validation.

On PyJWT as a whole package, the target decides 48 of the 49 cases with a
target. 44 checks fire in the negative tests, each decides at least 1 case,
and the whole suite detects the deletion of all 44
(`generated/pyjwt-package/SUMMARY.md`).

On the pilot, 4 of the 14 cases with a target are not decided by it. In 3 of
them the target fires and a handler replaces its exception, and the test
fails without the target; the fourth is a wrong target
(`readings/jwcrypto/FLAGS.md`). The whole suite detects the deletion of all
16 deciding checks and misses 7 of the 17 checks that fire and never decide.
For 4 of the 7, a witness test shows that the library accepts, without the
check, an input that it rejects with it (`readings/jwcrypto/UNDETECTED.md`).

## Results on the 4 held-out libraries

The run of 14 November 2026 followed section 6 of the protocol.
`generated/REPORT.md` puts the 6 subjects side by side. No defect of the
toolkit was found, and all 7 sentinels hold in each library. `DEVIATIONS.md`
lists 1 departure from the order of execution and 2 corrections of committed
texts.

| | google-auth | oauthlib | authlib | joserfc |
|---|---|---|---|---|
| Cases with a target | 15 | 53 | 30 | 131 |
| Decided by the target | 13 | 43 | 18 | 71 |
| Flags: the target does not fire | 2 | 10 | 12 | 60 |
| Deletions of deciding checks | 13 | 47 | 24 | 53 |
| Not detected by O_V | 2 | 7 | 3 | 12 |
| Not detected by O_Vfc | 9 | 11 | 8 | 29 |
| Not detected by O_C | 1 | 0 | 3 | 2 |
| Not detected by O_T | 6 | 34 | 10 | 32 |
| Not detected by the whole suite | 0 | 0 | 3 | 2 |
| E1 | held | held | held | held |
| E2 | held | held | not held | held |
| E3 | held | held | not held | not held |
| E4 | held | held | held | held |
| E5 | not stated | not held | held | held |

**Flags.** In each of the 84 flagged cases the target does not fire. The
readings (`readings/<name>/FLAGS.md`) put 81 of them in class C: the rule
assigned a check that the test does not describe (2, 10, 12 and 57 cases).
In `joserfc`, 56 of the 57 come from 2 properties of the code that matching
by name does not see: checks called through `getattr` (51 cases) and a
function imported under an alias (5 cases). The other 3 flags of `joserfc`
are in class A: the test does not reach the check it describes, because an
earlier check of the same class rejects its input. For each of the 3, the
target decides the case on the copy without that earlier check. No flag is in
class B or D. The classes are a reading of the sources and are reported apart
from the counts.

**Deletions.** The verdict oracle O_V misses the deletion of 2 of 13, 7 of
47, 3 of 24 and 12 of 53 deciding checks. The whole suite detects every
deletion in `google-auth` and `oauthlib`. It misses 3 in `authlib` and 2 in
`joserfc`: after each of these deletions, a later statement rejects the
inputs of the tests with the same class. For 4 of the 5, a witness test
gives an input that the library rejects with the check and accepts without
it (`readings/<name>/UNDETECTED.md`). 1 of the 4 holds only under limits
other than the defaults of the library, and 1 only when the caller allows
the "none" algorithm. For the fifth, no input was found.

**Pinning.** When the check that decides a case is deleted, the own test of
the case still passes for 0 of 22, 0 of 142, 3 of 42 and 4 of 190 cases.

**Second computation.** The second script agrees with the first analysis on
all 956 compared counts of the 7 subjects (`recompute/NOTES.md`).

## Limits

`PROTOCOL.md`, section 8, lists the limits known in advance. The main ones:
matching is by name; only raise statements that construct a rejection class
are checks; 1 deletion variant; the rule can assign a wrong target; 4
libraries of 1 language and 1 family of protocols, 1 of them a subject under
1 of 2 readings of its rejection base, and 2 of them not independent of each
other.
