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
and no check had been deleted on the 4 held-out libraries. Their targets,
outputs and readings, the deviations and the results come with later commits.

| Subject | Version | Role | Outputs |
|---|---|---|---|
| PyJWT, scope of the reference study | 2.15.1 | development; compared with the reference study | `generated/pyjwt/` |
| PyJWT, whole package | 2.15.1 | development; the row shown beside the others | `generated/pyjwt-package/` |
| jwcrypto | 1.6.1 | pilot | `generated/jwcrypto/`, `readings/jwcrypto/`, `witnesses/jwcrypto/` |
| google-auth | 2.62.2 | held out | after the protocol |
| oauthlib | 4.0.1 | held out | after the protocol |
| authlib | 1.9.5 | held out | after the protocol |
| joserfc | 1.8.0 | held out | after the protocol |

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
| `reach/report.py` | Writes `generated/REPORT.md`: the subjects side by side and the 5 expectations |
| `guard/reach_offline.py` | The pytest plugin that refuses and counts outside connections |
| `validate_pyjwt.py` | Compares the PyJWT outputs with the reference study, which it only reads, and writes `generated/pyjwt/VALIDATION.md` |
| `tests/` | Unit and end-to-end tests of the toolkit on small synthetic packages |
| `generated/<name>/` | `SUMMARY.md`, `summary.json`, `cases.csv`, `checks.csv`, `deletions.csv`, `flags.csv`, `pinning.csv`, `undetected.csv`, `records.tar.xz` (the records that the analysis reads), `SHA256SUMS`; for `pyjwt` also `VALIDATION.md`, written by `validate_pyjwt.py` and not listed in `SHA256SUMS` |
| `readings/<name>/` | `FLAGS.md` and `UNDETECTED.md`: readings of the sources, with reasons, reported apart from the counts |
| `witnesses/<name>/` | Witness tests |
| `timestamps/` | Time-stamp tokens; added by the commit after the protocol commit |
| `DEVIATIONS.md` | Deviations from the protocol; written during the run |
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

## Limits

`PROTOCOL.md`, section 8, lists the limits known in advance. The main ones:
matching is by name; only raise statements that construct a rejection class
are checks; 1 deletion variant; the rule can assign a wrong target; 4
libraries of 1 language and 1 family of protocols, 1 of them a subject under
1 of 2 readings of its rejection base, and 2 of them not independent of each
other.
