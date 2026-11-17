# Checks that fire in no case: the sample and the deletions

This folder holds the scripts of the part `no-fire/` of `../PROTOCOL.md`
(sections 3.1, 4.1 to 4.4, and steps 4 and 5 of section 6) and the sample they
drew. Paths are relative to this folder; T is `../../target-reach`, the toolkit
of the first study. Times are UTC. `python3` is CPython 3.12.3 (first line of
`../preparation/tools/logs/sample.log`).

| File | What it is |
|---|---|
| `sample.py` | draws 5 of the checks that fire in no case of each held-out library (4.3) |
| `sample.csv` | its output: 20 rows, made before the protocol commit |
| `nofire_deletions.py` | deletes each of the 103 checks in its own copy and runs the whole suite on it (4.2) |
| `deletions-nofire.csv`, `summary.json`, `records/<library>/whole/` | outputs of `nofire_deletions.py`, made by the next stage |
| `reach/` | the reading of the 20 sampled checks (4.4), made by the next stage; no script of this folder writes it |

## The population

A check fires in no case when its row in `T/generated/<name>/checks.csv` has
`reachable` = `yes` and `cases_fired` = `0` (`sample.py`, lines 6-11 and
65-67; `nofire_deletions.py`, lines 12-18). Both scripts count it per library
and stop when the sum is not 103 (`sample.py`, lines 99-102). The run of
`sample.py` at 14:10:03Z read:

| Library | `T/generated/<name>/checks.csv`, SHA-256 | Rows | Fire in no case |
|---|---|---|---|
| google-auth | `9fd04884bc9cd9422feae99b553aee9f5ae58c11f507dcf170fa2a10678dd01d` | 100 | 39 |
| oauthlib | `b8458d4abc7d2d0b86e7b20e186a3343e32eb2e45890a279446b61f9184f1651` | 88 | 13 |
| authlib | `e1a915928623e0a1352ff08210a4f8712c14d0112b1ee275bd51eb2af00b645b` | 39 | 12 |
| joserfc | `1a53dec5f1ce298148f55bb4fd6358097f7d43fefa961303a7adcdbed29ee49d` | 97 | 39 |

Source: `../preparation/tools/logs/sample.log`, lines 2-5 and 6 (total 103).
`nofire_deletions.py --dry --collect` printed the same 4 counts in its run of
14:54:10Z (`../preparation/tools/logs/nofire-dry.txt`, lines 1-5).

## `sample.py`

    python3 -I -B sample.py [--generated DIR] [--subjects DIR] [--out FILE]
                            [--libraries NAME ...] [--expect-total N]

For each library, in the order google-auth, oauthlib, authlib, joserfc, a
fresh `random.Random(20261117)` draws 5 check ids with `.sample` from the
library's ids sorted as Python sorts strings (lines 13-17 and 70-72). The draw
reads nothing but `checks.csv`. The line numbers of the raise statements come
afterwards from `T/subjects/<name>/checks.json` (lines 25-31), whose SHA-256
the script prints:

| Library | `T/subjects/<name>/checks.json`, SHA-256 |
|---|---|
| google-auth | `b7803bae8ce11d88d17eddc17971db28935bd538dd0f3005d94cb659c46c09e7` |
| oauthlib | `d85a995c9d8eb040d5a2b93a1692b8206fdb7442385b9403a26da32d18319863` |
| authlib | `3208594ee8627cfe505c022cf74a491b367668769e232cfca30d933fffb4c7d0` |
| joserfc | `49eaea742bda9a5f6743061d8d8161e939d9639f46f8aec11f77611a99428e49` |

Source: `../preparation/tools/logs/sample.log`, lines 8, 10, 12 and 14.

`sample.csv` has the columns `library, check, file, line, function, class,
template, reachable` (lines 19-24); `line` joins with `;` the first line of
each raise statement of the check. It was written by `python3 -I -B sample.py`
at 14:10:03Z (exit status 0): 20 rows, SHA-256
`5637e6bc9241273992552eb79331b9e5095ee5c8e8b291afc718f2efeea3a8fa`
(`../preparation/tools/logs/sample.log`, last line). The same command writes the same
bytes again: the test `test_the_deposited_sample_is_reproduced` of
`../tests/test_sample.py` (lines 101-106) runs it and compares the files.

## `nofire_deletions.py`

    python3 -I -B nofire_deletions.py [--dry [--collect] [--check-deletions] [--no-verify]]
        [--libraries NAME ...] [--only NAME ...] [--expect-total N]
        [--clone NAME=DIR ...] [--python NAME=PYTHON ...] [--work DIR] [--workers N]
        [--out FILE] [--summary FILE] [--records DIR] [--toolkit DIR]
        [--subjects DIR] [--generated DIR]

It imports T's runner `reach/run.py` and calls its functions `verify`,
`whole_baseline`, `deletion_copy` and `whole_deletions` unchanged, library by
library (lines 20-43):

1. `verify`: the clone at the commit of `subject.json` and clean, the digests
   of the subject and test files, CPython 3.12.3, and the environment of
   `T/subjects/<name>/requirements.txt`;
2. `whole_baseline`: the whole suite on 2 fresh unmodified copies, the tests
   that pass in both runs, and the time limit, 10 times the slower run and at
   least 60 s;
3. the manifest of the deletion copies (`deletion_copy`, as T's step
   `deletions` makes its copies), in `<work>/<name>/records/deletions/manifest.json`;
4. `whole_deletions`: the whole suite on 1 fresh copy per check and on 1
   unmodified control copy, 10 copies at a time (T's `WORKERS`, `run.py` line
   105), with the repetition of a run that exceeds the time limit or leaves no
   result file.

T's `whole_run` does not keep the exit status of pytest; the script wraps
`whole_run` and `subprocess.run` of the loaded module in its own process and
notes each exit status, and both wrappers call the originals unchanged (lines
45-51).

Inputs: `T/generated/<name>/checks.csv`; `T/subjects/<name>/` (`subject.json`,
`checks.json`, `requirements.txt`); `T/generated/<name>/records.tar.xz`, whose
`records/whole/base.json` is printed beside the new baseline for comparison
only; the clones in `../work/no-fire/src/<name>` and the environments in
`../work/no-fire/venvs/<name>` (lines 83-84).

Outputs (lines 53-71 and 86-87):

- `deletions-nofire.csv`: 1 row for the control copy (`_control`) and 1 per
  check, with `returncode`, `detected`, `failing_tests` (each as
  `run|class::name (failed|skipped|absent)`), `timed_out`, `no_result`,
  `runs`, `first_run_returncode`, `tests_not_passing`, `failed_or_error`,
  `skipped`, `absent`, `detected_by_failure`, `refused_attempts` and
  `seconds`. `detected` is the definition of 4.2: a test that passes in both
  unmodified runs does not pass on the copy, or the run is broken twice.
  `detected_by_failure` is the narrower count of 4.2: at least 1 such test
  fails or ends with an error;
- `summary.json`: per library, the counts and time limit of the new
  baseline, the exit statuses of its 2 runs, T's deposited baseline beside
  it, the control row, the number detected and the checks not detected;
- `records/<library>/whole/base.json` and `whole/deletions.json`: T's records
  of the run, copied from `<work>/<name>/records/whole/`;
- in `../work/no-fire/<name>/` (not deposited, `../.gitignore` line 1): the
  copies, T's records with the junit XML file of every pytest call
  (`records/whole/xml/`, as T's `whole_run` names them, `run.py` line 542),
  and the output of every pytest call (`logs/whole/`).

The CSV file and the summary are written after each library, so that a stop
keeps the libraries before it. `--only NAME` runs some of the libraries again
and keeps the rows and summaries of the others from the files.

### The dry mode

`--dry` runs nothing on the copies: it prints the checks with the lines of
their raise statements, runs T's static `verify`, and prints every pytest
command of the run with its folder and environment, built as T's `whole_run`
builds them; `--collect` adds `pytest --collect-only -q` on 1 fresh
unmodified copy with the options of each suite run (lines 73-81). It was run
as `python3 -I -B nofire_deletions.py --dry --collect` at 14:17:31Z and again
at 14:54:10Z, both times with exit status 0 (`../preparation/tools/commands.tsv`,
lines 41 and 51). The log `../preparation/tools/logs/nofire-dry.txt` is that of the
second run; it gives (lines 6-8, 90-93, 123-126, 214-221 and 303; the
toolkit prints its times in local time, UTC+01:00):

| Library | Checks | `verify` | Collected | Pass in both deposited runs | Deposited time limit |
|---|---|---|---|---|---|
| google-auth | 39 | commit `50b1eb269f11`; 78 subject files, 1 test file | 2349 (`unit`) | 2349 | 836.1 s |
| oauthlib | 13 | commit `6e3aa05af929`; 75 subject files, 8 test files | 719 (`all`) | 717 | 60.0 s |
| authlib | 12 | commit `42607cbc2135`; 215 subject files, 3 test files | 249 (`core`), 215 (`jose`), 231 (`clients`), 467 (`flask`), 51 (`django`) | 1211 | 264.8 s |
| joserfc | 39 | commit `f345ff71cd6c`; 55 subject files, 11 test files | 310 (`all`) | 310 | 70.6 s |

The collection refused 0 outside connections in every suite run. The dry run
printed 175 pytest commands: per suite run, 2 unmodified runs, the control and
1 per check (google-auth 42, oauthlib 16, authlib 75, joserfc 42). The new
baseline, not the deposited one, decides which tests count (4.2): oauthlib and
authlib collect 2 tests more than pass in both deposited runs.

## Preparation of the clones and environments

| Time | Command | Result |
|---|---|---|
| 14:06:10Z to 14:06:16Z | `git clone --quiet --depth 1 --branch <tag> <repository> ../work/no-fire/src/<name>`: https://github.com/oauthlib/oauthlib `v4.0.1`, https://github.com/authlib/authlib `v1.9.5`, https://github.com/authlib/joserfc `1.8.0`; https://github.com/googleapis/google-cloud-python `google-auth-v2.62.2` with `--filter=blob:none --sparse`, then `git sparse-checkout set packages/google-auth` | exit 0; heads `6e3aa05af92978755939a18cb4dd655ced156c1e`, `42607cbc2135252a641a845e4ed7f94e3a922c47`, `f345ff71cd6c36452a4e11e47b805ad450a95dd8`, `50b1eb269f110a4b7ab09ffe5ae59c0151cd63c2` (`../preparation/tools/logs/clones.log`) |
| 14:06:23Z | `git rev-parse HEAD` and `git status --porcelain --untracked-files=all --ignored` in each clone | exit 0 |
| 14:06:35Z to 14:06:56Z | `/usr/bin/python3.12 -m venv ../work/no-fire/venvs/<name>`; `<venv>/bin/pip install --quiet --disable-pip-version-check -r T/subjects/<name>/requirements.txt` | exit 0 for the 4 |
| 14:09:30Z to 14:09:31Z | `python3 -I -B T/reach/run.py verify --subject T/subjects/<name>/subject.json --clone <clone> --python <venv>/bin/python --work <work>` | exit 0 for the 4 (`../preparation/tools/logs/verify-<name>.log`) |

Source: `../preparation/tools/commands.tsv`, which holds every command with its start,
end and exit status.

## The next stage

After the protocol commit and its 2 time-stamp tokens (`../PROTOCOL.md`,
section 6, step 1), from this folder:

    python3 -I -B nofire_deletions.py

runs the 4 libraries in rank order with the defaults above and writes the
outputs of step 4 of section 6. If it stops, the libraries it has not finished
run again with `--only`, for example:

    python3 -I -B nofire_deletions.py --only authlib joserfc

`--only` takes names from `--libraries` (default the 4, line 108). Before a
library runs, the script removes `records/whole/`, `records/deletions/` and
`copies/` of an earlier run from its work folder (lines 357-359). T's
`whole_deletions` makes every copy of a library before its first run and
leaves them in place (`run.py`, lines 620-621): about 40 copies for
google-auth and for joserfc.

## Tests

From `..`, with the environment `../work/tests-venv` (CPython 3.12.3, pytest
9.2.0):

    work/tests-venv/bin/python -B -m pytest -q -p no:cacheprovider tests

`tests/test_sample.py` and `tests/test_nofire_deletions.py` run the 2 scripts
on synthetic files and on the toolkit's synthetic package
`T/tests/fixture/toy`, never on a library of the study (`../tests/conftest.py`,
lines 1-4). The suite of `../tests/` gave 54 passed and 1 skipped in its
last run, at 15:10:45Z (`../preparation/tools/commands.tsv`, line 56;
`../preparation/tools/logs/unit-tests.txt`); the skipped test is the sweep of the toy
on the 6 interpreters, which runs only with `SWEEP_TOY=1`.
