# Protocol: checks that fire in no case, nested-header depth, and 7 more libraries

This text is fixed by the commit that adds it, before any of the runs it
describes. Right after that commit, a text that names it is time-stamped by 2
authorities, and a later commit adds the tokens in `timestamps/`. Section 5
says what had been done before the commit, and section 6 fixes the order of
what comes after it.

The 3 parts below were chosen after the results of `../target-reach/` and of
`../target-reach-followup/` had been read. They extend that replication and
are reported as an extension of it. "The first protocol" is
`../target-reach/PROTOCOL.md`. The terms check, rejection class, reachable,
block, included block, class-only block, target, tier, case, case of the
study, deciding check, fired check, outcome, flag, deletion, recorder run,
whole-suite run, control copy, time limit, sentinel and the oracles O_V,
O_Vfc, O_C, O_T and O_S keep the meaning that section 4 of the first protocol
gives them. "The toolkit" is the code in `../target-reach/reach/` and
`../target-reach/guard/`, which this experiment imports and does not change.
"The second computation" is `../target-reach/recompute/second.py` with
`../target-reach/recompute/compare.py`, used in the same way.

## 1. Purpose

The first study measured, on 4 held-out libraries, whether the check that
rejects the input of a negative test is the check that the test describes,
and which test oracles detect the deletion of each check that fires in those
tests (first protocol, section 1). This experiment adds 3 parts.

**Checks that fire in no case (`no-fire/`).** The first protocol deletes only
the checks that fire in at least 1 case of the study (section 4,
"Deletion", lines 361-367). In the 4 held-out libraries, 103 reachable checks
fire in no case: 39 of the 52 reachable checks of `google-auth`, 13 of 54 in
`oauthlib`, 12 of 36 in `authlib` and 39 of 81 in `joserfc`
(`../target-reach/generated/<name>/checks.csv`, columns `reachable` and
`cases_fired`). No run has shown whether the suite of a library detects the
deletion of 1 of them. This part deletes each of the 103 and runs the whole
suite on the copy. A sample of 20 of the 103, 5 per library, is read for
reachability: for each, an input through an entry point that makes a raise
statement of the check execute, or the reason from the source why no such
input exists.

**The depth of a nested header (`nested-depth/`).** A negative test of PyJWT
2.15.1 decodes a token whose header nests 1000 JSON arrays; its target is the
JSON check of `PyJWS._load` (`../mutation-adequacy-pyjwt/version-check/README.md`,
lines 8-15). On CPython 3.12.3, 3.13.14 and
3.14.6, `json.loads` parses that header and the next check rejects the token
(`../target-reach-followup/versions/README.md`, lines 28-42). The deepest
nesting that `json.loads` accepts with its C scanner is 9997, 9998 and 40121
arrays on these 3 interpreters (same file, lines 44-55). This part decodes
headers of 10000 and 50000 nested arrays through `jwt.decode` on the same 3
interpreters, with the JSON check as released and with the upstream change
that made it catch `RecursionError` reverted, and records which check rejects
each header, or that none does.

**7 more libraries (`screened/`).** `../target-reach/SELECTION.md` lists 7
candidates that pass the criteria I1 to I4 and were not needed (section 7,
lines 233-237). This part applies the toolkit to each of them, unchanged, as
the first protocol applies it to the 4 held-out libraries, but without any
reading: the outcomes of the cases are counted against the targets that the
rule assigns, the flags are counted and not read, and no witness test is
written. It adds a sweep of CPython 3.9 to 3.14 over the tests that hold the
included blocks, in the manner of `../target-reach-followup/versions/`.

Like the first study, this experiment reports counts per library and tests no
hypothesis. The 5 expectations of the first protocol are restated for the 7
libraries (section 2); no other part has an expectation.

## 2. Questions

- **No-fire.** For each of the 103 checks: does the whole suite detect its
  deletion, and which tests then do not pass? For each of the 20 sampled
  checks: does an input through an entry point reach a raise statement of the
  check, and if none can, why not?
- **Nested depth.** For each of 2 depths (10000 and 50000 arrays), 3
  interpreters (CPython 3.12.3, 3.13.14 and 3.14.6) and 2 variants of the JSON
  check (as released, and with the change reverted): which check rejects the
  header, if any?
- **Screened.** For each of the 7 libraries: Q1 and Q3 of the first protocol,
  and the first sentence of its Q2 (lines 25-32; its second sentence, whether
  the library accepts an input only without the check, is answered there by
  witness tests, which are not written here); how many of its reachable checks
  fire in no case; and, on each CPython from 3.9 to 3.14 that the release
  admits, which tests of its included blocks pass, and, on 3.12 and later,
  which check decides each case.

### Expectations stated in advance

For each of the 7 screened libraries, the 5 expectations of the first protocol
(section 2, lines 34-63) are restated unchanged: the same text, decided on the
same units, and reported per library as *held* or *not held* unless 1 of the 4
rules below gives another status. They are not hypothesis tests.

| | Expectation, for 1 library | Decided on |
|---|---|---|
| E1 | At least 1 deletion of a deciding check is not detected by O_V. | deletions of deciding checks |
| E2 | O_C detects at least 1 deletion of a deciding check that O_V does not. | deletions of deciding checks |
| E3 | The whole suite detects every deletion of a deciding check. | deletions of deciding checks |
| E4 | At least 1 case with a target is not decided by its target. | cases with a target |
| E5 | At least 1 case of a class-only block passes its own test after the deletion of its deciding check. | cases of class-only blocks whose deciding check is deleted and whose deletion run gives a record |

The 4 rules of the first protocol, applied by `../target-reach/reach/report.py`
and nowhere else:

- E5 is stated for a library in which at least 9 of every 10 included blocks
  are class-only; elsewhere it is reported as *not stated*. The shares come
  from the sources alone. For the 7, they are those of
  `screened/subjects/<name>/blocks.json` at this commit; this text does not
  restate them.
- An expectation with 0 units to be decided on in a library is reported as
  *not applicable*.
- A library in which a sentinel of the first protocol (section 4, lines
  461-482) does not hold gets no verdict: each of its 5 expectations is
  reported as *no verdict*, with the numbers of the sentinels that do not hold.
- The report is not written while a library named to it lacks the records of
  the whole suite.

A library reported as failed (section 3.3) gets no verdict and is not named to
`reach/report.py`. The report labels the libraries named to it as held out:
none of the 7 was used to build the toolkit or the rule, which were built on
PyJWT (first protocol, lines 20-21).

The expectations were written before the run of the first study, with the
counts of PyJWT and of the pilot in view (first protocol, lines 65-68). They
are restated here with the verdicts of the 4 held-out libraries known
(`../target-reach/generated/REPORT.md`, lines 84-88):

| | google-auth | oauthlib | authlib | joserfc |
|---|---|---|---|---|
| E1 | held (2 of 13) | held (7 of 47) | held (3 of 24) | held (12 of 53) |
| E2 | held (1 of 13) | held (7 of 47) | not held (0 of 24) | held (10 of 53) |
| E3 | held (13 of 13) | held (47 of 47) | not held (21 of 24) | not held (51 of 53) |
| E4 | held (2 of 15) | held (10 of 53) | held (12 of 30) | held (60 of 131) |
| E5 | not stated (0 of 17 included blocks assert the class alone) | not held (0 of 140) | held (3 of 40) | held (4 of 168) |

These 4 columns are a comparison and no test. No expectation is stated for
the checks that fire and never decide (as in the first protocol, lines 67-68),
for the checks that fire in no case, for the sample, for the depth runs or for
the sweep: these report counts.

## 3. Subjects

### 3.1 The 4 held-out libraries (`no-fire/`)

`google-auth` 2.62.2, `oauthlib` 4.0.1, `authlib` 1.9.5 and `joserfc` 1.8.0,
each at the commit, in the environment and with the definitions of
`../target-reach/subjects/<name>/` (first protocol, section 3, lines 75-80). No
definition of theirs changes, and the checks of this part are those of the
records of the first study.

| Library | Checks | Reachable | Reachable, fire in no case |
|---|---|---|---|
| google-auth | 100 | 52 | 39 |
| oauthlib | 88 | 54 | 13 |
| authlib | 39 | 36 | 12 |
| joserfc | 97 | 81 | 39 |

Source: the rows of `../target-reach/generated/<name>/checks.csv`, all of role
`subject`, with the columns `reachable` and `cases_fired`. The 103 checks of
the last column are the units of the part; `no-fire/sample.py` prints the same
4 counts and stops when their sum is not 103 (its lines 6-11 and 99-102). The
82 checks that are not reachable and fire in no case (48, 28, 3 and 3) are not
deleted: by the definition of reachability (first protocol, lines 208-212), no
entry point reaches them by name.

### 3.2 PyJWT (`nested-depth/`)

PyJWT 2.15.1 at commit `7d5ef55e42ce42221f58dc49943e92ccad1fa66a`
(`../target-reach/subjects/pyjwt-package/subject.json`, lines 4 and 7), from a
clone of its repository at that commit, as `../target-reach-followup/versions/`
ran it (`nested_header.py`, lines 50-57): each run takes a fresh copy of
`jwt/`, `tests/` and `pyproject.toml` (`nested-depth/depth_runs.py`, lines
8-11), in 2 variants:

- `released`: the package as released; the `except` clause of the JSON check
  (`jwt/api_jws.py`, line 373) reads `except (ValueError, RecursionError) as e:`;
- `before-fix`: a copy whose clause reads `except ValueError as e:`, as before
  upstream commit `0657369` ("Handle recursive JWS headers as decode errors",
  `../mutation-adequacy-pyjwt/version-check/README.md`, lines 10-14).

The 2 checks of the header are `api_jws.PyJWS._load#3`, the raise statement at
line 374 with the template "Invalid header string: {*}", and
`api_jws.PyJWS._load#4`, at line 377, "Invalid header string: must be a json
object" (`../target-reach/subjects/pyjwt-package/checks.json`). The earlier
studies call them `jws.header-json` and `jws.header-object`
(`../target-reach-followup/versions/nested_header.py`, line 53).

The interpreters are those of the follow-up, in the same versions and builds
of the same kind: CPython 3.12.3 of Ubuntu 24.04, and CPython 3.13.14 and
3.14.6, Linux x86_64 builds installed with uv
(`../target-reach-followup/versions/README.md`, lines 129-133). Each has an
environment without any package: PyJWT 2.15.1 needs none on these interpreters
(same file, lines 139-140; `nested-depth/depth_runs.py`, lines 44-49).

### 3.3 The 7 screened libraries (`screened/`)

The candidates of `../target-reach/SELECTION.md` that pass I1 to I4 and were
not needed, in rank order (section 7, lines 233-237), at the versions read at
the screening (section 9):

| Library | Version | Rank | Source in `SELECTION.md` |
|---|---|---|---|
| paramiko | 5.1.0 | 271 | line 294 |
| pycryptodome | 4.4.0 | 330 | line 298 |
| scramp | 1.5.0 | 383 | line 299 |
| ecdsa | 0.19.2 | 508 | line 303 |
| python-jose | 3.5.0 | 621 | line 307 |
| supabase-auth | 2.34.1 | 677 | line 309 |
| service-identity | 26.1.0 | 869 | line 316 |

Each library is defined in `screened/subjects/<name>/` in the way the 4
held-out libraries are defined in `../target-reach/subjects/<name>/`: by the 6
decisions of the first protocol (section 3, lines 82-112), except that the
release of decision 1 is the version of the table, at the commit of its tag.
The files are `draft.json` (the 6 decisions and the settings, each with its
source), `subject.json` (written by `reach/scope.py`), `checks.json`,
`blocks.json` and `targets.json` (written by `reach/run.py define targets`),
`requirements.txt` (the environment on CPython 3.12.3) and `PREPARATION.md`
(every command run on the library before this commit, with its time in UTC and
what it gave). They are part of this commit, and this text does not restate
them. They change after it only as a deviation (section 8).

**No selection.** The 7 are run whatever the toolkit counts for them: the
criteria of the selection are not applied again, and a library whose counts
under the toolkit differ from those of the screening (its `PREPARATION.md`) is
run all the same. Criterion I5, that the tests run offline (`SELECTION.md`,
lines 67-69), is not checked (line 237) and excludes no library: every pytest
call refuses outside connections, and a test that fails for that reason in the
first run of the baseline is an expected baseline failure (first protocol,
lines 298-305), which the report lists.

**No replacement.** A library whose tests cannot be run under the recorder
with its definitions and the toolkit unchanged is reported as failed, with the
reason, and no other library takes its place (first protocol, lines 134-137).
That the tests import the library from a copy and that its distribution is not
installed in the environment is a definition of the first protocol (lines
276-278), not a defect of the toolkit: a library that cannot be imported from a
copy without its installed distribution, or without compiled modules that its
sources do not hold, is reported as failed. A library whose `PREPARATION.md`
records, before this commit, that `verify` refuses it or that none of the test
files of its recorder runs can be collected from a copy goes through no step
of section 6, and that record is the record of its failure. A library that
fails in a step after this commit is reported as failed at that step. A defect
of the toolkit is not a reason to fail a library (section 8).

By this rule, 3 of the 7 go through no step. For `paramiko` and `scramp`, the
package reads the version of its installed distribution on import, so the test
files of their recorder runs stop at collection with
`importlib.metadata.PackageNotFoundError`
(`screened/subjects/paramiko/PREPARATION.md`, lines 20-34;
`screened/subjects/scramp/PREPARATION.md`, lines 22-33). For `pycryptodome`,
the package loads compiled modules that its commit does not hold, and all 20
test files of its recorder runs fail at collection with
`OSError: Cannot load native module`
(`screened/subjects/pycryptodome/PREPARATION.md`, lines 16-24). The other 4,
`ecdsa`, `python-jose`, `supabase-auth` and `service-identity`, are run.

## 4. Definitions

The definitions of section 4 of the first protocol (lines 146-482) apply
unchanged, to the 7 screened libraries as to the 4 held-out ones: every run
uses a fresh copy of the release made from a clone at its commit, the
environment pinned in `requirements.txt` on CPython 3.12.3 (except in the
sweep, 4.6), the same environment variables, the offline guard and the time
limits. This section adds only what the 3 parts need.

No run lets a library reach a git repository from its copies. Importing
`ecdsa` from a copy runs `git describe --dirty` in the first git repository
that git finds above the copy, which can rewrite the index of that repository
(`screened/subjects/ecdsa/PREPARATION.md`, section 6, item 1), and the
environment of the toolkit's pytest calls sets no variable that stops git from
looking (`../target-reach/reach/run.py`, lines 155-165). The runs of a library
whose import runs git, in its main run and in the sweep, therefore keep their
copies, records and logs in a work folder (`--work`) that no git repository
holds; its clone and its environment stay where they are, and nothing else of
the run changes. The sweep runs `ecdsa` in the same call as the other
libraries (section 6), so its whole work folder is such a folder; outside its
dry mode, the sweep script refuses a work folder that a git repository holds
(`screened/versions.py`, lines 91-93, and the check at the start of its
function `main`).

The `pytest_args` of each `subject.json` are used as written, and no option is
added to them. In particular, no seed is set for the random examples that
hypothesis draws in 5 of the 9 included blocks of `ecdsa`, for which neither
the library's configuration nor `pytest_args` sets one
(`screened/subjects/ecdsa/PREPARATION.md`, section 6, item 2): the tests run as
the library's own configuration runs them, and what follows for the sentinels
is stated in section 9.

### 4.1 A check that fires in no case

A check of a held-out library whose row in
`../target-reach/generated/<name>/checks.csv` has `reachable` = `yes` and
`cases_fired` = `0`. `cases_fired` counts the cases of the study, in the first
baseline recorder run of the first study, in which the check fires; the check
that decides a case counts as firing in it (`../target-reach/reach/analyse.py`,
lines 177, 234 and 236-240; `firing` in `../target-reach/reach/study.py`,
lines 34-42; first protocol, lines 338-347).

For each of the 7 screened libraries, the same definition applies to the
`checks.csv` that its own run writes. Its checks that fire in no case are
counted and listed, and not deleted.

### 4.2 Deletion, and detection by the whole suite

Each of the 103 checks is deleted as the first protocol deletes a check
(lines 361-363): in a fresh copy of the release, every raise statement of the
check is replaced by `pass`, and every line keeps its number
(`../target-reach/reach/delete.py`). Each deletion copy gets 1 whole-suite run
and no recorder run.

For each library, before its deletion copies, the whole suite runs on 2
unmodified copies, each fresh, as the step `whole-baseline` of
`../target-reach/reach/run.py` runs it (lines 576-600); each of these 2 runs
may take 7200 s and must end with its result files. The runs of the first
study are not reused. An unmodified control copy gets the same run as a
deletion copy. The time limit is 10 times the slower of the 2 unmodified runs,
and at least 60 s, for all the suite runs of a copy together; a run that
exceeds it, or of which a pytest call leaves no result file that can be read,
is repeated 1 time, alone, on a fresh copy; the copies run 10 at a time
(first protocol, lines 286-287 and 451-459).

A deletion is *detected by the whole suite* when at least 1 test that passes
in both unmodified runs does not pass in the run of the deletion copy (first
protocol, lines 413-416): it fails, ends with an error, is skipped or is
absent from the results. When the repeated run also exceeds the limit or
leaves no result, the deletion counts as detected by the whole suite (lines
455-456), and no failing test is listed for it. The *failing tests* of a
deletion are all the tests that pass in both unmodified runs and do not pass
on its copy, each with its outcome there and the suite run that holds it. The
deletions for which at least 1 failing test fails or ends with an error, and
not only is skipped or absent, are counted beside them.

`no-fire/nofire_deletions.py` makes these runs with the functions `verify`,
`whole_baseline`, `deletion_copy` and `whole_deletions` of
`../target-reach/reach/run.py`, unchanged. To record the exit status of each
pytest call, which `whole_run` does not keep, it wraps `whole_run` and
`subprocess.run` of that module in its own process, and both wrappers call the
originals unchanged (`no-fire/nofire_deletions.py`, lines 20-51).

The control copy is expected to end with its results and to lose no test that
passes in both unmodified runs, as sentinel 6 of the first protocol asks
(lines 478-480). A test that it loses is listed, and the counts of its library
are reported with this condition marked as not holding.

### 4.3 The sample

`no-fire/sample.py` draws 5 of the checks that fire in no case of each
held-out library: for each library, a fresh `random.Random(20261117)` samples
5 of its check identifiers, sorted as Python sorts strings (`no-fire/sample.py`,
lines 13-17 and 65-72). The draw reads nothing but `checks.csv`. Its output,
`no-fire/sample.csv`, holds 1 row per drawn check with its file, the first line
of each of its raise statements, its function, class and message template.
The draw was made before this commit, and its output is part of it (section
5).

### 4.4 A sampled check reached through an entry point

An *input through an entry point* is a call of a function or method of the
package that has the name of an entry point of the library's `subject.json`
(first protocol, decision 3, lines 88-89, and lines 208-212), with arguments that stand for
an artifact received from another party and with the settings that a caller
gives through the documented parameters of the library, such as keys,
options or a request validator. Nothing of the package, of its dependencies or
of its tests is changed, patched or replaced, and no other function of the
package is called directly. A setting that is not the default is listed with
the input.

Each input runs on a fresh, unmodified copy of the release, in the environment
of the first study (`../target-reach/subjects/<name>/requirements.txt`, CPython
3.12.3). A sampled check gets 1 of 3 results:

- *reached*: an input makes a raise statement of the check execute, as a
  tracer that records the execution of the line of the raise statement shows,
  or as the recorder of the toolkit, used as it is, shows by recording the
  check as fired; the exception that reaches the caller is recorded;
- *not reached*: the source shows that no input through an entry point can
  make a raise statement of the check execute; the reason names the file and
  line of each guard, call or condition on the way that excludes it;
- *undecided*: neither an input that reaches the check nor such a reason was
  found.

A reached check whose exception a handler catches inside the package is still
reached. Each input that is run is kept as a script that runs it, in
`no-fire/reach/<library>/`, named after the row of its check in
`no-fire/sample.csv` (1 to 20). `no-fire/reach/reach.csv` holds 1 row per
sampled check, in the order of `sample.csv`, with the columns `library`,
`check`, `result` (`reached`, `not reached` or `undecided`), `entry_point`,
`scripts`, `settings`, `exception` and `reason`; `no-fire/reach/READING.md`
gives, for each check, the source that its result rests on, by file and line.

### 4.5 What rejects a header

A *depth run* is 1 call of `jwt.decode(token, "secret", algorithms=["HS256"])`
(`jwt/api_jwt.py`, line 595) in a fresh interpreter, with a fresh copy of the
variant and the default recursion limit, in the environment that the toolkit
gives its pytest calls, with a stack size limit (`ulimit -s`) of 8192 KiB, that
of the depth measurement of the follow-up
(`../target-reach-followup/versions/README.md`, lines 44-46;
`nested-depth/depth_runs.py`, lines 18-26). The token is built as the
nested-header test of PyJWT builds its own (`tests/test_api_jws.py`, lines
634-645, at the commit of section 3.2), with a header of n nested JSON arrays,
n = 10000 or 50000, in place of 1000. Each of the 12 combinations of 2 depths,
3 interpreters and 2 variants is run 1 time. The record of a run gives the
interpreter (its path and version), the variant, the depth, the recursion
limit, the stack size limit that the run had, the time limit and the result.

The result of a depth run is 1 of 5, the values of `outcome` in
`nested-depth/depth_runs.py` (lines 27-38):

- *rejected by a check*: the call raises an exception whose raise site, the
  innermost frame of its traceback inside the copy (as for the deciding check,
  first protocol, lines 330-336), is a line of a raise statement of a check of
  `../target-reach/subjects/pyjwt-package/checks.json`; the record names the
  check, the line, and the class and message of the exception;
- *exception outside the checks*: the call raises an exception whose raise
  site is no such line, or whose traceback has no frame inside the copy, such
  as the `RecursionError` that escapes from `json.loads` at line 372 on CPython
  3.9 to 3.11 with the change reverted
  (`../mutation-adequacy-pyjwt/version-check/README.md`, line 35): no check
  rejects the header;
- *accepted*: the call returns;
- *interpreter failed*: the interpreter ends on a signal or without its
  record; the exit status, and the signal if any, are recorded;
- *timed out*: the run exceeds the time limit of the script, 60 s (its line
  108).

### 4.6 The interpreter sweep

The sweep runs the tests that hold the included blocks of each screened
library that is not reported as failed on CPython 3.9.25, 3.10.20, 3.11.15,
3.12.3, 3.13.14 and 3.14.6. It is made by `screened/versions.py`, which imports
`../target-reach/reach/run.py` and calls its functions unchanged (its lines
10-21).

**Interpreters.** A library is run on an interpreter when the
`Requires-Python` of its release (`info.requires_python` at
https://pypi.org/pypi/<distribution>/<version>/json) admits it. The
classifiers `Programming Language :: Python :: 3.N` of the release are
recorded beside each interpreter and exclude none. This is the option
`--support requires-python` of the script; its default rule would also exclude
an interpreter whose minor version the classifiers do not list
(`screened/versions.py`, lines 23-30). From the metadata fetched during the
preparation, read again on 2026-11-17 at 14:36:17Z:

| Library | `Requires-Python` | Classifiers | Interpreters run |
|---|---|---|---|
| ecdsa 0.19.2 | `!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*,!=3.5.*,>=2.6` | 3.6 to 3.13 | all 6 |
| python-jose 3.5.0 | `>=3.9` | 3.9 to 3.13 | all 6 |
| supabase-auth 2.34.1 | `>=3.11` | none | 3.11.15, 3.12.3, 3.13.14, 3.14.6 |
| service-identity 26.1.0 | `>=3.8` | 3.8 to 3.15 | all 6 |

The sources are https://pypi.org/pypi/ecdsa/0.19.2/json, fetched at 13:55:51Z
(`screened/subjects/ecdsa/PREPARATION.md`, line 57);
https://pypi.org/pypi/python-jose/json, fetched at 13:51:52Z, whose `info` is
that of 3.5.0, the latest release (`screened/subjects/python-jose/PREPARATION.md`,
lines 149 and 346-351); https://pypi.org/pypi/supabase-auth/2.34.1/json,
fetched at 13:52:03Z (`screened/subjects/supabase-auth/PREPARATION.md`, line
42); and https://pypi.org/pypi/service-identity/26.1.0/json, fetched at
13:53:10Z (`screened/subjects/service-identity/PREPARATION.md`, lines 32-36).
For `ecdsa` and `python-jose`, 3.14.6 is admitted by `Requires-Python` and not
listed by the classifiers. The sweep fetches the metadata again and keeps each
file with its SHA-256 (`screened/versions.py`, lines 288-305); a set of
interpreters that differs from the table is reported.

**Environments.** Each interpreter gets its own environment, made with
`uv venv` and `uv pip install --only-binary :all:`, from wheels only, as the
follow-up made its environments (`../target-reach-followup/versions/README.md`,
lines 94-96 and 133-137), from the pins of the library's `requirements.txt`. A
pin is kept when a file of that release that is not yanked admits the
interpreter by its `requires_python`; otherwise it is replaced by the latest
final release that has such a file, and every replacement is listed
(`screened/versions.py`, lines 31-43). For example, pytest 9.2.0 and 9.1.1
require Python 3.10 or later (`requires_python` at
https://pypi.org/pypi/pytest/9.2.0/json and
https://pypi.org/pypi/pytest/9.1.1/json, read on 2026-11-17 at 14:13Z), so on
3.9.25 pytest is at another version than on 3.12.3. No other replacement is
made: an interpreter whose environment cannot be made from wheels, or fails the
checks of the script (its lines 43-49), or on which the tests cannot be
collected, is reported with the error. On 3.12.3 the environment must also pass the
toolkit's check against `requirements.txt` (`environment_problems`,
`../target-reach/reach/run.py`, lines 279-305). `verify` itself is not run on
the other interpreters, since it requires the interpreter of `subject.json`
(`../target-reach-followup/versions/README.md`, lines 87-90).

**Selection.** On each interpreter, the tests are collected from a fresh copy
with the toolkit's pytest call. For each included block, the selection holds
the collected tests whose node id, without its parameters, is that of the
block's test function; when there are none, the collected tests of its file
with the function's name (a test that a class inherits); when there are none
either, the collected tests of its file whose function calls the block's
function, directly or through other functions of the file (a block in a
helper). A block that none of the 3 resolves is listed (`screened/versions.py`,
lines 56-69).

**Runs.** On every interpreter, the selected tests run 1 time without the
recorder, through the toolkit's suite run, with the options of `subject.json`
and the offline guard; the outcome of each test (passed, failed, error,
skipped or absent) and the message of its first failure or error are recorded
from the junit XML file of pytest (`screened/versions.py`, lines 70-77). On
3.12.3, 3.13.14 and 3.14.6 the selected tests then run 2 times under the
recorder, as the toolkit's `baseline` runs them: each run on a fresh copy,
with a time limit of 3600 s, and without the tests that failed in the run
without the recorder. Each case then gets its deciding check and its fired
checks (same file, lines 76-83). Below 3.12
the recorder cannot take the fired checks, which come from `sys.monitoring`,
present from Python 3.12 (`../target-reach/README.md`, lines 116-118), and the
sweep records outcomes only.

**Comparison.** 3.12.3 is the control. For each other interpreter the sweep
lists the tests whose outcome differs from the control. On 3.13.14 and 3.14.6
it also lists the cases whose deciding check in the first recorder run differs
from that of the control's first recorder run, or that only 1 of these 2 runs
holds. Within each of the 3 interpreters it lists the cases whose deciding
check differs between its 2 recorder runs. The first recorder run of the
control is compared in the same way with the first recorder run of the
library's main baseline, read from `screened/generated/<name>/records.tar.xz`,
the archive that `pack` writes (`screened/versions.py`, lines 84-88; the
default of its option `--generated` is `screened/generated/`), so the sweep
runs after the main runs (section 6).

**Outputs.** `screened/versions/<name>.json`, `interpreters.csv`,
`outcomes.csv` and `cases.csv` (`screened/versions.py`, lines 90-92). The
script writes the 3 tables from the libraries of its own call alone (the call
of `write_tables` at the end of its function `main`), so the sweep is 1 call
for all the libraries it runs (section 6).

## 5. What had been done before this commit

**On the 4 held-out libraries.** Their results in `../target-reach/` and in
`../target-reach-followup/` were known, with the readings of their flags and
of their undetected deletions. The 103 checks that fire in no case were
counted from the deposited `checks.csv` (section 3.1). It was known that 2 of
them, `oauthlib`'s `oauth2.rfc6749.endpoints.base.BaseEndpoint._raise_on_bad_method#1`
and `oauth2.rfc6749.endpoints.base.BaseEndpoint._raise_on_bad_post_request#1`
(`oauthlib/oauth2/rfc6749/endpoints/base.py`, lines 79-80 and 88-89, from
`../target-reach/subjects/oauthlib/checks.json`), are asserted by 2 tests of
`tests/oauth2/rfc6749/endpoints/test_error_responses.py` (lines 440-466 and
468-491 at the commit of the subject). Each calls an entry point inside a `try`
statement, calls `self.fail` after it and asserts on the exception in its
`except` clause; such a test holds no block of the first protocol, so the
recorder does not see what it asserts. It was also known that 1 of the sampled
checks, `joserfc`'s `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1`,
decides a repaired variant of a test of `joserfc`
(`../target-reach-followup/versions/README.md`, line 77).

The clones and environments of the 4 libraries were made, `verify` of the
toolkit was run on each, and the sample was drawn (`no-fire/sample.py`,
`no-fire/sample.csv`). `no-fire/nofire_deletions.py` was run in its dry mode
only, in which nothing runs on the copies: it lists the checks and the pytest
commands, runs the static `verify` and, with `--collect`, `pytest
--collect-only -q` on 1 unmodified copy with the options of each suite run
(its lines 73-81). `no-fire/README.md` describes this preparation, and
`preparation/tools/commands.tsv` logs each of its commands with its times in UTC (the
rows labeled `check-clone`, `sample` and `nofire-dry`, and `clone-`, `venv-`
or `verify-` followed by the name of 1 of the 4 libraries). No check that
fires in no case was deleted, no whole-suite run was made, and no input was
run for any sampled check.

**On PyJWT.** The earlier runs of the nested-header test were known:
`../mutation-adequacy-pyjwt/version-check/results.jsonl` (CPython 3.9.25 to
3.12.3), `../target-reach-followup/versions/results.jsonl` (3.12.3, 3.13.14
and 3.14.6) and `../target-reach-followup/versions/depth.jsonl` (the deepest
nesting on 3.9 to 3.14). The clone, the interpreters and the environments of
the part were installed, and `nested-depth/depth_runs.py` was run in its dry
mode only, which makes no copy and decodes nothing (its lines 64-66;
`preparation/tools/commands.tsv`, the rows labeled `interpreters`, `clone-pyjwt`,
`check-clone`, `venv-nested` and `depth-dry`). No header of 10000 or 50000
arrays was decoded.

**On the 7 screened libraries.** Only the steps that this protocol allows
before its commit were run: the release was found and cloned at its commit,
its environment was made, `pytest --collect-only -q` ran on its suite runs,
and `reach/scope.py` and `reach/run.py define targets verify` wrote and checked
`subject.json`, `checks.json`, `blocks.json` and `targets.json`. Their checks,
blocks, class-only blocks and targets were therefore known at this commit,
whereas in the first study the targets of the held-out libraries came with a
commit after the protocol commit (first protocol, lines 586-588;
`../target-reach/timestamps/README.md`, lines 39-49). The rule that assigned
them, `reach-target-rule/2`, reads no run and was not changed.
`screened/subjects/<name>/PREPARATION.md` lists every command run on each
library, with its time in UTC and what it gave; for some of the 7 it records
that their tests cannot be collected from a copy, and the rule of section 3.3
applies to them. `screened/versions.py` was not run on any of the 7: only in
its dry mode, which fetches nothing and makes no environment, copy or run (its
lines 96-102), on the synthetic package of the toolkit's tests, and in the
tests of `tests/` (`preparation/tools/commands.tsv`, the rows labeled
`synthetic-define`, `versions-dry-synthetic` and `unit-tests`).
No test of these libraries was run under the recorder or in a whole-suite run,
and no check of theirs was deleted.

**On the toolkit.** Nothing of `../target-reach/` was changed. The tests in
`tests/` run the scripts of this folder on the synthetic package
`../target-reach/tests/fixture/toy` and on synthetic files, never on a library
of the study (`tests/conftest.py`, lines 1-4).

## 6. Order of execution

1. This file, `README.md`, `DEVIATIONS.md`, the definitions of the 7
   libraries, the scripts of the 3 parts, the sample and `tests/` are committed
   in 1 commit. A text that names the commit is time-stamped by the 2
   authorities of `../target-reach/timestamps/`, freetsa.org and DigiCert
   (RFC 3161), and a later commit adds the tokens in `timestamps/`. No step
   below starts before both tokens are received.
2. A screened library whose `targets.json` is not part of this commit gets it
   from `reach/run.py targets` first; that file is committed and time-stamped
   in the same way before the library's `baseline`.
3. The 7 screened libraries, in rank order, except those reported as failed
   (section 3.3). For each: `verify`, `baseline`, `deletions`,
   `whole-baseline`, `whole-deletions` and `pack` of `reach/run.py`, then
   `reach/analyse.py`, with the outputs in `screened/generated/<name>/`; then
   the second computation on its records, with the outputs in
   `screened/recompute/<name>/`. After the 7, `reach/report.py` puts the
   libraries that gave outputs side by side and states the 5 expectations
   (`screened/generated/REPORT.md`). Then the sweep (4.6), in 1 call of
   `screened/versions.py` for the libraries that are not reported as failed,
   in rank order, with its outputs in `screened/versions/` and its work folder
   outside every git repository (section 4).
4. The 103 deletions, by `no-fire/nofire_deletions.py`, library by library in
   rank order (`google-auth`, `oauthlib`, `authlib`, `joserfc`): `verify`, the
   2 unmodified whole-suite runs, then the control copy and the deletion
   copies (4.2). The outputs are `no-fire/deletions-nofire.csv`, the summary of
   the run (`no-fire/summary.json`) and, per library, the records
   `whole/base.json` and `whole/deletions.json`, which the script copies from
   its work folder into `no-fire/records/<library>/whole/`
   (`no-fire/nofire_deletions.py`, lines 53-71).
5. The reading of the 20 sampled checks (4.4): for each, an input through an
   entry point is sought from the source and run on a fresh, unmodified copy,
   and it is recorded whether it reaches a raise statement of the check, or
   the reason from the source is given why no input reaches it. The outputs
   are `no-fire/reach/reach.csv`, `no-fire/reach/READING.md` and the scripts
   of the inputs (4.4). The reading uses no output of step 4 and may run while
   steps 3 and 4 run.
6. The depth runs, by `nested-depth/depth_runs.py` (4.5), with the records of
   the 12 runs in `nested-depth/results.jsonl`. They use no output of the steps
   before them and may run while those run.
7. The outputs, the reading of the sample and `DEVIATIONS.md` are committed,
   and the commit is time-stamped in the same way; a later commit adds the
   tokens.

Where the second computation and `reach/analyse.py` disagree on a count, the
rule of the first protocol applies (lines 619-623): the count that follows
section 4 of the first protocol stands, the other script is corrected, and
where that section does not decide, both counts are reported.

## 7. What is reported

Per screened library, as section 7 of the first protocol (lines 639-664)
reports a held-out library, without readings:

- checks, reachable checks, deciding checks, checks that fire and never
  decide, reachable checks that fire in no case; blocks, included blocks,
  class-only blocks; cases, cases left out;
- Q1: cases with a target by tier and their 4 outcomes against the targets of
  the rule; flags counted by tier and by outcome, and not read;
- Q2: deletions not detected under each oracle, for deciding checks and for
  checks that fire and never decide, with the withheld-as-failing columns, the
  deletions that exceeded the time limit, the runs that were repeated and the
  runs that ended without a record or a result; the deletions that the whole
  suite does not detect are listed, and no witness test is written for them;
- Q3: pinning by kind of block, with the cases not counted, by reason;
- the 5 expectations, each as held, not held, not applicable, not stated or
  no verdict;
- the expected baseline failures, the test files not collected, the tests
  deselected as copies and the copies that stay, the cases of nested blocks,
  the cases with a firing in another thread, and the refused connection
  attempts;
- the 7 sentinels, the deviations, and the result of the second computation;
- the sweep: per interpreter, the verdicts of `Requires-Python` and of the
  classifiers, whether it ran or the error that stopped it, the replacements
  of packages and the packages added to the pins, the blocks that the
  selection did not resolve, the outcomes of the selected tests, the tests
  whose outcome differs from 3.12.3, and, on 3.12.3, 3.13.14 and 3.14.6, the
  cases whose deciding check differs from 3.12.3 or between the 2 recorder
  runs; and the cases whose deciding check on 3.12.3 differs from that of the
  library's main baseline.

A library reported as failed is listed with its reason and the step at which
it failed.

For no-fire, per library: the 2 unmodified runs (the tests that pass in both,
those whose outcome differs between them, and the time limit), the control
copy, the deletions detected and not detected by the whole suite, those of them
for which a failing test fails or ends with an error, those that exceeded the
time limit, the runs that were repeated, the refused connection attempts and
the exit status of every pytest call; for each detected deletion, its failing
tests; and, for the 2 checks of `oauthlib` named in section 5, whether the
whole suite detects their deletion.

For the sample, per library and for each of the 20 checks: reached, not
reached or undecided, with the entry point, the input in short, the settings
that are not the default and the exception that reaches the caller, or the
guards that exclude every input.

For nested-depth, the table of the 12 runs, each with the fields of 4.5.

No statistical test is applied, no count is pooled across libraries, and no
rate is reported as an estimate for verifiers in general. The verdicts on the
expectations are tallied per library, never across libraries. Null results are
reported like any other: a library without a case or a deletion, a deletion
that no test detects, a sampled check that no input reaches, a header that no
check rejects.

## 8. Deviations

A *defect* is a crash of the toolkit, of the second computation or of a script
of this folder, or a contradiction between the code and a definition of this
protocol or of section 4 of the first protocol. A defect found during the run
is fixed and listed in `DEVIATIONS.md` with its date, the reason and the files
changed. Nothing of `../target-reach/` is changed: a defect of the toolkit or of
the second computation is fixed in a copy of the code concerned in this folder,
which every later run uses in place of the original, and the copy is deposited.
The outputs and the verdicts obtained before the fix are deposited beside the
new ones, marked as superseded; the outputs after the last fix are the result.
After a fix of the toolkit, PyJWT and the pilot are run again with the copy,
and any change of their outputs from those of `../target-reach/generated/` is
listed. The library in hand is run again from `baseline`, and so is every
library already run whose records the fix can change. `targets.json` is not
computed again unless the defect is in the inputs of the rule; then both
versions are deposited. The rule itself does not change.

A change of `reach/analyse.py`, of `reach/report.py` or of a script of this
folder after the protocol commit is a deviation of the same kind. Any other
departure from this file is listed in `DEVIATIONS.md` too.

## 9. Limits known in advance

- The limits of section 8 of the first protocol (lines 666-728) hold for the 7
  screened libraries as for the 4: matching is by name, only raise statements
  that construct a rejection class are checks, 1 deletion variant, and the
  rule can assign a wrong target. The counts that section gives for its 6
  libraries, of what the enumerations do not read, are not made for the 7.
- The flags of the 7 are not read. In the 4 held-out libraries, the readings
  put 81 of the 84 flags in class C, a target that the test does not describe
  (`../target-reach/README.md`, lines 210-212). The outcomes of the 7 are
  therefore outcomes against the targets of the rule, not against the checks
  that the tests describe.
- No witness test is written for the 7: a deletion that their whole suite does
  not detect shows nothing about what the library accepts without the check.
- The toolkit imports each library from a copy and refuses an environment that
  holds its distribution (first protocol, lines 276-278). A library whose
  import needs the metadata of its installed distribution, or compiled modules
  that its sources do not hold, cannot be run in this way (section 3.3); its
  failure shows nothing about its tests.
- With outside connections refused, a test of the 7 that needs another machine
  fails at baseline and is deselected; the check that every test has the same
  outcome with and without the refusal, made for the 4 held-out libraries
  (first protocol, lines 711-717), is not made for the 7. The toolkit starts
  no service: a test that needs a server that the project's own test setup
  starts first fails in both unmodified whole-suite runs and detects no
  deletion.
- A test that draws random inputs without a seed set by the configuration of
  its library or by `pytest_args` can make the 2 baseline records and the
  control copy differ; sentinel 1 then does not hold, and the library gets no
  verdict (section 2). A test with a time limit of its own can fail under the
  recorder alone if the recorder slows it; sentinel 2 then does not hold.
- For the 103 checks, the whole suite is the only oracle. A detection shows
  that some test needs a raise statement of the check, not that the test
  describes the check; a deletion that no test detects shows nothing about
  whether an input can reach the check.
- The sample is 5 checks per library whatever the number that fire in no case
  (39, 13, 12 and 39), 20 of the 103 in all; it gives no rate for a library. A
  check is reached by 1 input found by reading the source. A check not reached
  rests on a reading of the guards, which can be wrong, and an undecided check
  shows nothing.
- The 2 depths were chosen with `depth.jsonl` known: 10000 is just above the
  deepest nesting of 3.12.3 and 3.13.14 (9997 and 9998), and 50000 is above that
  of 3.14.6 (40121). The depth that `json.loads` reaches depends on the Python
  call depth of the call, and on 3.14 on the machine stack; 3 runs of the depth
  probe on 3.14.6 gave 40111, 40121 and 40139
  (`../target-reach-followup/versions/README.md`, lines 57-61). A result holds
  for the call and the stack size limit of its run. The call goes through
  `jwt.decode`, while the test and the earlier runs call `PyJWS().decode`
  (`../target-reach-followup/versions/nested_header.py`, line 126).
- 1 build of each interpreter, on 1 machine (Linux x86_64): 3.12.3 is the build
  of Ubuntu 24.04, the others are uv builds. Below 3.12 the sweep records no
  fired checks, and a package can be at another version than at 3.12.3 (4.6).
  The sweep runs the selected tests alone, not their whole files, and an
  interpreter for which a package of the environment has no wheel is not run.
  For `ecdsa` and `python-jose`, 3.14.6 is an interpreter that the release
  admits and whose version its classifiers do not list.
- The 7 libraries are the candidates that the first study did not need, ranks
  271 to 869 of the frame of `../target-reach/SELECTION.md` (download rank and
  a keyword filter, section 8): they are no sample of verifiers. They are not
  all independent of each other or of the subjects of the first study: the
  environment of a library can hold another subject as a dependency (its
  `requirements.txt`). Each library is counted on its own package alone.
- The time stamps show that a text naming the protocol commit existed at their
  time. They cannot show that nothing was run before; the statement of section
  5 rests on the records of the preparation: the `PREPARATION.md` of each
  screened library, `no-fire/README.md` and the log `preparation/tools/commands.tsv`,
  a copy of the log of the tools with the paths of the machine made relative
  to the root of the repository.
