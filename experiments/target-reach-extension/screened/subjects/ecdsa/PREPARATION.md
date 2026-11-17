# ecdsa 0.19.2: preparation of the definitions

Part `screened/` of the runs, before the protocol commit. Paths are relative to
the root of this repository: T = `experiments/target-reach`, X =
`experiments/target-reach-extension`, S = `X/screened/subjects/ecdsa` (this
folder), W = `X/work/ecdsa` (clone, environment and logs, outside the deposit).
Times are UTC, all on 2026-11-17.

Nothing of the library ran except `pytest --collect-only` and the static steps
`define`, `targets` and `verify` of the toolkit. The library, its tests and the
toolkit are unchanged.

## Result

The library is defined, its suite run collects without error, and `verify`
accepts the clone and the environment. Each count below is read from the file
that the toolkit or pytest wrote; `W/prep/counts.json` holds them all
(written at 14:11:41Z by `count_ecdsa.py`, a copy of which is in `W/prep/`).

| Count | Value | Source |
|---|---|---|
| checks | 4 | `S/checks.json`, `checks` |
| reachable checks | 4 | `S/checks.json`, `checks[].reachable` |
| subject files | 16 | `S/subject.json`, `subject_files` |
| test files of the subject | 3 | `S/subject.json`, `tests` |
| blocks in those 3 test files | 67 | `S/blocks.json`, `counts.blocks` |
| blocks that call an entry point | 9 | `S/blocks.json`, `counts.entry_point_blocks` |
| included blocks | 9, all asserting the class alone | `S/blocks.json`, `counts.included`; `match`, `match_unparsed`, `post` and `post_unparsed` empty in all 9 |
| blocks in the test directories | 170 in 12 test files | `S/subject.json`, `scope_counts` |
| targets, assertion tier | 2 (`class` 2) | `S/targets.json`, `counts` |
| targets, name tier | 2 (`name` 2) | `S/targets.json`, `counts` |
| blocks without a target | 5 (`none: no name token matches` 3, `none: tie` 2) | `S/targets.json`, `counts` |
| tests collected | 2023, 0 errors | `W/prep/collect-only.log`, last line `2023 tests collected in 1.04s` |

**Against I3 and I4.** I3 asks for at least 5 checks that 1 verification call
can run, and I4 for at least 10 blocks (T/SELECTION.md lines 59-66). With these
definitions the package holds 4 checks in all and the suite 9 included blocks,
1 short of each. The screening counted 25 checks and 12 blocks
(`T/selection/screening-results.json`, the record of rank 508 from line 716:
`n_checks`, `n_negative_blocks`). It counted the raise statements of
`UnexpectedDER`, `MalformedSignature`, `ValueError` and `MalformedPointError`,
and 3 blocks of `test_eddsa.py` that expect `ValueError`; its `notes` say that
I4 passes only if `eddsa.PublicKey.verify` counts. Under T/PROTOCOL.md
(decision 4, lines 90-91; rejection classes, lines 177-183) these are no
rejection classes, since the documentation of the entry points names
`BadSignatureError` and `BadDigestError` alone (section 2). `S/checks.json`
lists the 140 other raise statements, each with the reason "not a rejection
class". T/SELECTION.md lists ecdsa as passing I1 to I4 on the screening count
(line 303) and as not counted again with the toolkit (lines 233-237). Whether
ecdsa stays among the subjects of the runs is open for the protocol commit;
nothing here decides it.

## 1. Commands run on the library

| # | Time | Command, in short | What it gave |
|---|---|---|---|
| 1 | 13:55:51Z | `curl -sS` of https://pypi.org/pypi/ecdsa/json and https://pypi.org/pypi/ecdsa/0.19.2/json, saved in `W/prep/` | HTTP 200 both, 65118 and 33933 bytes |
| 2 | 13:55:56Z | `python3 -I` reading the 2 files | section 2, decision 1 |
| 3 | 13:56:00Z | `git ls-remote --tags https://github.com/tlsfuzzer/python-ecdsa` | `refs/tags/python-ecdsa-0.19.2` = `bd66899550d7185939bf27b75713a2ac9325a9d3`, without a peeled entry |
| 4 | 13:56:08Z | `git clone --quiet https://github.com/tlsfuzzer/python-ecdsa W/clone`; `git -C W/clone checkout --quiet bd66899550d7185939bf27b75713a2ac9325a9d3`; `rev-parse`, `cat-file -t`, `log -1`, `describe --tags --exact-match HEAD`, `status --porcelain --untracked-files=all --ignored` | HEAD `bd66899550d7185939bf27b75713a2ac9325a9d3`; the tag is lightweight (`cat-file -t` gives `commit`); `describe` gives `python-ecdsa-0.19.2`; commit date 2026-03-26T10:50:34+01:00, subject "Merge commit from fork"; status empty |
| 5 | 13:56:13Z to 13:59:52Z | reading only (`ls`, `cat -n`, `grep -n`, `sed -n`) in `W/clone`: tox.ini, setup.cfg, setup.py, conftest.py, the requirement files, .github/workflows/ci.yml, README.md, docs/source/*.rst, src/ecdsa/*.py; `openssl version` | the sources of section 2; OpenSSL 3.0.13 30 Jan 2024 |
| 6 | 14:00:03Z | `S/draft.json` written | the decisions of section 2, before any count |
| 7 | 14:00:10Z | `python3 -I -B T/reach/scope.py --draft S/draft.json --clone W/clone` | exit 0; `scope: 16 subject files, 3 test files`; `S/subject.json` |
| 8 | 14:00:21Z | `/usr/bin/python3.12 -m venv W/venv` | exit 0 at 14:00:23Z; CPython 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]; pip 24.0 and nothing else |
| 9 | 14:00:27Z | `W/venv/bin/python -m pip install --disable-pip-version-check --no-input "six>=1.9.0" pytest hypothesis coverage`, log `W/prep/pip-install.log` | exit 0 at 14:00:29Z; installed coverage 7.17.3, hypothesis 6.170.15, iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, Pygments 2.21.0, pytest 9.2.0, six 1.17.0, sortedcontainers 2.4.0 |
| 10 | 14:00:37Z | `W/venv/bin/python -m pip freeze --disable-pip-version-check > S/requirements.txt`; `pip freeze --all`; `W/venv/bin/python -I -c` with `importlib.util.find_spec("ecdsa")` | 9 lines; `pip==24.0` besides; `find_spec` None: ecdsa is not importable from the environment |
| 11 | 14:00:59Z | `git ls-files` in `W/clone`, filtered for .c, .h, .pyx, .pxd, .so and .cpp; `grep -n "ext_modules\|Extension" setup.py`; `git -C W rev-parse --show-toplevel` | 0 files; no match; the top level above W is the root of this repository (section 6, item 1) |
| 12 | 14:01:14Z | a copy of `src` and `conftest.py` into `W/copies/collect-only` as `make_copy` does (T/reach/run.py lines 310-322), with `make_collect_copy.py` (a copy is in `W/prep/`) | 16 subject files and 3 test files checked against the clone, 0 differ |
| 13 | 14:01:14Z to 14:01:16Z | `pytest --collect-only -q` in that copy (section 4) | exit 0; 2023 tests collected; 0 errors |
| 14 | 14:01:23Z and 14:01:27Z | `find` in the copy, `grep` in the log | `.hypothesis/constants` in the copy; 2023 test ids, per file in section 4 |
| 15 | 14:01:47Z | the logs moved to `W/prep/`; `W/copies` deleted | |
| 16 | 14:01:59Z to 14:02:00Z | `cd X && env PYTHONHASHSEED=0 python3 -I -B T/reach/run.py define targets verify --subject S/subject.json --clone W/clone --python W/venv/bin/python --defs S --work W --out X/screened/generated/ecdsa`, log `W/prep/run-define-targets-verify.log` (its clock times are UTC+1) | exit 0; `S/checks.json`, `S/blocks.json`, `S/targets.json`, `W/local.json`; section 5 |
| 17 | 14:04Z to 14:15Z | reading only: `python3 -I` over the files of S; the 3 test files of the subject parsed with `ast`, for the decorators of their tests; `grep -n`, `sed -n` and `cat -n` in `W/clone`; `openssl version`; `openssl ecparam -list_curves` | sections 3 to 6; `prime192v1` listed |
| 18 | 14:11:41Z | `python3 -I count_ecdsa.py S W/clone W/prep/collect-only.log > W/prep/counts.json` | the counts of the table above |

## 2. Decisions and settings

`S/draft.json`, written at 14:00:03Z, before any count, gives the source of
each decision in its `*_source` fields.

1. **Release.** 0.19.2, at commit `bd66899550d7185939bf27b75713a2ac9325a9d3`
   (tag `python-ecdsa-0.19.2`). The PyPI JSON read at 13:55:51Z gives
   `info.version` 0.19.2, and the latest upload of all releases is that of
   0.19.2: the wheel `ecdsa-0.19.2-py2.py3-none-any.whl` at
   2026-03-26T09:58:15.808678Z (sha256
   `840f5dc5e375c68f36c1a7a5b9caad28f95daa65185c9253c0c08dd952bb7399`) and
   the sdist `ecdsa-0.19.2.tar.gz` at 2026-03-26T09:58:17.675780Z (sha256
   `62635b0ac1ca2e027f82122b5b81cb706edc38cd91c63dda28e4f3455a2bf930`),
   neither yanked. So it was also the latest release on 14 November 2026
   (T/PROTOCOL.md lines 84-85), and it is no pre-release. The project URL is
   http://github.com/tlsfuzzer/python-ecdsa (`info.project_urls`); the tag
   prefix `python-ecdsa-` is that of setup.cfg line 13. The commit is that of
   the screening record (`tag_or_commit`).
2. **Package directory.** `ecdsa` under the source root `src` (setup.py lines
   26-27: `packages=["ecdsa"]`, `package_dir={"": "src"}`).
3. **Entry points.** `verify` and `verify_digest`: `entry_points_source`.
4. **Rejection bases.** `BadDigestError` and `BadSignatureError`:
   `rejection_bases_source`. Decision 4 speaks of "the base class" (T/PROTOCOL.md
   lines 90-91); the 2 classes that the documentation names share no base but
   the built-in `Exception` (src/ecdsa/keys.py lines 38 and 53). The draft names
   both, as the recount of T names several classes where a library names
   several (T/selection/recount.sh lines 20, 22, 26 and 30). 2 readings were not
   taken and not counted: `BadSignatureError` alone (README.md lines 295-297
   name it alone for `verify`, but the docstring of `verify_digest` names
   `BadDigestError` as well, keys.py lines 718-720), and the built-in
   `Exception`, which would make every exception class of the package and
   every built-in exception class a rejection class (T/PROTOCOL.md lines
   177-180), parse errors included, which the documentation does not name as
   rejections.
5. **Test directories.** `src/ecdsa`: `test_directories_source` (tox.ini line 30).
6. **Suite runs.** 1 run, `all`, on `src/ecdsa`: `suite_runs_source` (tox.ini
   line 30; .github/workflows/ci.yml lines 83-86 and 340-342).

Settings: `copy` is `src` and `conftest.py`. The root conftest.py registers the
option `--fast` and the marker `slow` (conftest.py lines 1-11); the tests read
`--fast` from `sys.argv` (src/ecdsa/test_malformed_sigs.py lines 58, 161 and
165; src/ecdsa/test_pyecdsa.py lines 81 and 1029), and the suite run does not
pass it (tox.ini line 30). `pytest_args` is `-p no:cacheprovider`, as for every
subject of T (`T/subjects/*/subject.json`). `python` is 3.12.3, `distribution`
ecdsa, `source_root` src.

## 3. Environment

- `W/venv`, made by `/usr/bin/python3.12 -m venv` (command 8): CPython 3.12.3,
  pip 24.0; `W/venv/pyvenv.cfg` has `include-system-site-packages = false`.
- Declared dependency: `six>=1.9.0` (setup.py line 47; PyPI `requires_dist`).
  Test requirements: pytest and hypothesis, the deps of the tox environment
  py312 (tox.ini lines 9-10) that the CI runs for Python 3.12 (ci.yml lines
  83-86), and coverage (tox.ini line 29). The extras gmpy and gmpy2 (setup.py
  line 48) are not installed: tox.ini lines 11-12 install them only in the gmpy
  environments, not in py312.
- The library is not installed: `W/prep/pip-install.log` names no ecdsa,
  `find_spec("ecdsa")` is None (command 10), and `verify` checks it (section 5).
- `S/requirements.txt`: `pip freeze` (command 10), 9 lines.
- **Compiled extensions: none needed, none built.** The library is pure Python:
  its tree tracks no .c, .h, .pyx, .pxd, .so or .cpp file and setup.py declares
  no extension (command 11); the PyPI wheel is `py2.py3-none-any`, and the PyPI
  `summary` reads "ECDSA cryptographic signature library (pure python)". The
  optional compiled backend gmpy2 is not installed. The wheels that pip chose
  for hypothesis and coverage are binary (`cp312-cp312-manylinux...`,
  `W/prep/pip-install.log`); they belong to the environment, not to the library.
- A system program the tests call: `/usr/bin/openssl`, OpenSSL 3.0.13 30 Jan
  2024 (`which` at 13:55:43Z; `openssl version` at 13:59:27Z and 14:05:46Z).

## 4. Collection

Command 13, in the copy `W/copies/collect-only`, with absolute paths:

```
env -i PATH=W/venv/bin:/usr/bin:/bin HOME=$HOME LANG=C.UTF-8 LC_ALL=C.UTF-8 \
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=T/guard:W/copies/collect-only/src \
  OFFLINE_OUT=W/logs/collect-only.offline.json \
  OUTCOMES_OUT=W/logs/collect-only.outcomes.json \
  GIT_CEILING_DIRECTORIES=W/copies \
  W/venv/bin/python -m pytest --collect-only -q -p no:cacheprovider \
  -p reach_offline --rootdir=. --continue-on-collection-errors src/ecdsa \
  > W/logs/collect-only.log 2>&1
```

The environment variables are those of `Context.env` (T/reach/run.py lines
154-164), the offline plugin is `OFFLINE` (run.py line 92), and `PYTHONPATH` is
that of `Context.pythonpath` for a run without the recorder (run.py lines
166-174); `src/ecdsa` is the suite run `all`. `GIT_CEILING_DIRECTORIES` is not
in the toolkit's environment: it kept the import of ecdsa from running git in
this repository (section 6, item 1). The logs are now in `W/prep/`.

Result: exit 0; `2023 tests collected in 1.04s`; no other line of the log than
the test ids, a blank line and that summary; the offline guard counted 0
attempts (`collect-only.offline.json`), and `collect-only.outcomes.json` lists
no failed test and no failed collector. Test ids per file: test_curves.py 131,
test_der.py 93, test_ecdh.py 77, test_ecdsa.py 57, test_eddsa.py 87,
test_ellipticcurve.py 42, test_jacobi.py 77, test_keys.py 178,
test_malformed_sigs.py 205, test_numbertheory.py 257, test_pyecdsa.py 800,
test_sha3.py 19. Each of the 9 tests that hold an included block is collected
once.

Collection imports the test modules, which run `openssl ecparam -list_curves`
(src/ecdsa/test_ecdh.py lines 370-373; src/ecdsa/test_pyecdsa.py lines
1064-1066 and 1770-1772), and hypothesis wrote its cache `.hypothesis/constants`
in the copy (hypothesis/internal/constants_ast.py line 219 in the environment).
The copy was deleted at 14:01:47Z; the clone was not touched.

## 5. define, targets and verify

Command 16 printed:

```
define: 4 checks (4 in subject files, 4 reachable); 67 blocks in the 3 test files of the subject, 9 included in 3 files; the test directories hold 170 blocks in 12 test files
targets: rule reach-target-rule/2; {"class": 2, "name": 2, "none: no name token matches": 3, "none: tie": 2}
verify: commit bd66899550d7, 16 subject files and 3 test files match, CPython 3.12.3
```

`pack` was not run, so `X/screened/generated/ecdsa` does not exist.

**Checks** (`S/checks.json`, `rejection_classes` `BadDigestError`,
`BadSignatureError`), all in src/ecdsa/keys.py and all reachable:

| Check | Class | Message template | Lines |
|---|---|---|---|
| `keys._truncate_and_convert_digest#1` | BadDigestError | `this curve ({*}) is too short for the length of your digest ({*})` | 63-68 |
| `keys.VerifyingKey.verify#1` | BadSignatureError | `Signature verification failed` | 681 |
| `keys.VerifyingKey.verify_digest#1` | BadSignatureError | `Malformed formatting of signature` | 737 |
| `keys.VerifyingKey.verify_digest#2` | BadSignatureError | `Signature verification failed` | 741 |

`functions`: 322, 86 of them reachable. `other_raises`: 140, each "not a
rejection class": UnexpectedDER 55, ValueError 34, MalformedPointError 11,
NotThisMethod 8, UnknownCurveError 6, InvalidPointError 4, MalformedSignature 4,
InvalidCurveError 3, NoKeyError 2, NoCurveError 2, RSZeroError 2, TypeError 2,
JacobiError 2, SquareRootError 2, InvalidSharedSecretError 1,
NegativeExponentError 1, RuntimeError 1.

**Blocks** (`S/blocks.json`), blocks and included blocks per file:
test_keys.py 16 and 1, test_malformed_sigs.py 5 and 5, test_pyecdsa.py 46 and 3.
Each of the 58 excluded blocks has the reason "no entry-point call"; 56 of them
also expect a class that is no rejection class (UnexpectedDER 19,
MalformedPointError 18, ValueError 11, MalformedSignature 3, TypeError 2,
SubprocessError 2, UnknownCurveError 1), and the other 2 expect BadDigestError
around a call of `sign` (src/ecdsa/test_pyecdsa.py lines 690 and 1782).

**Included blocks and their targets** (`S/blocks.json`, `S/targets.json`; the
last column from the decorators of the test, read with `ast`):

| Block (file::test#k) | Line | Expects | Calls | Target | Tier, or reason for none | Under `@given` |
|---|---|---|---|---|---|---|
| test_keys.py::TestVerifyingKeyFromDer.test_ed25519_sig_verify_malformed#0 | 438 | BadSignatureError | verify | none | tie: verify#1, verify_digest#1 | no |
| test_malformed_sigs.py::test_fuzzed_der_signatures#0 | 176 | BadSignatureError | verify | verify_digest#1 | name | yes |
| test_malformed_sigs.py::test_random_der_ecdsa_sig_value#0 | 223 | BadSignatureError | verify | none | tie: verify#1, verify_digest#1 | yes |
| test_malformed_sigs.py::test_random_der_as_signature#0 | 321 | BadSignatureError | verify | verify_digest#1 | name | yes |
| test_malformed_sigs.py::test_random_bytes_as_signature#0 | 339 | BadSignatureError | verify | none | no name token matches | yes |
| test_malformed_sigs.py::test_fuzzed_string_signatures#0 | 377 | BadSignatureError | verify | none | no name token matches | yes |
| test_pyecdsa.py::ECDSA.test_basic#0 | 110 | BadSignatureError | verify | none | no name token matches | no |
| test_pyecdsa.py::ECDSA.test_verify_with_too_long_input#0 | 556 | BadDigestError | verify_digest | _truncate_and_convert_digest#1 | assertion (class) | no |
| test_pyecdsa.py::TooSmallCurve.test_verify_too_small_curve_dont_allow_truncate_raises#0 | 1804 | BadDigestError | verify | _truncate_and_convert_digest#1 | assertion (class) | no |

Check names in the table drop the prefix `keys.VerifyingKey.` or `keys.`.

## 6. What can make a run of the next stage fail or differ

1. **Importing ecdsa runs git in this repository.** src/ecdsa/__init__.py line
   104 calls versioneer's `get_versions()`. In a git checkout the version
   keywords are not expanded (src/ecdsa/_version.py line 25), so `_version.py`
   takes the root of the copy (lines 661-667) and runs there `git rev-parse
   --git-dir` and `git describe --tags --dirty --always --long --match
   python-ecdsa-*` (lines 255-277). A copy under `X/work` holds no `.git`, and
   git finds this repository's worktree above it (command 11). In a scratch
   repository outside this one, git 2.43.0 rewrote the index on that
   `describe` after the stat data of a file changed, and not on `rev-parse`
   (14:12:23Z). Every pytest call of the next stage would so run git here, can
   rewrite the index of this worktree or meet its lock while a commit is made,
   and gets a version string derived from this repository (no test file reads
   `__version__`). The environment of the toolkit (T/reach/run.py lines
   154-164) has no `GIT_CEILING_DIRECTORIES`. Copies outside any git
   repository (a `--work` outside X) avoid it, against the rule that work goes
   in `X/work`.
2. **hypothesis draws random examples.** 5 of the 9 included blocks are in
   tests under `@given` (src/ecdsa/test_malformed_sigs.py lines 173, 216, 317,
   335 and 374), with `max_examples` 10 (lines 164-168) and no seed: neither the
   library's configuration nor `pytest_args` sets one. The keys are random too
   (`SigningKey.generate`, src/ecdsa/test_pyecdsa.py lines 103 and 1795). Which
   check decides a case, and how many cases a block opens, can then differ
   between the 2 baseline recorder runs and the control copy, which sentinel 1
   asks to give identical records (T/PROTOCOL.md lines 470-471); 2 whole-suite
   runs can differ in the same way. The pytest plugin of hypothesis has the
   option `--hypothesis-seed` (`_hypothesis_pytestplugin.py` line 41 in the
   environment); T sets an option of this kind for 1 subject, `-p no:randomly`
   for pyjwt-package (`T/subjects/pyjwt-package/subject.json`). Whether to set
   one is open for the protocol commit.
3. **hypothesis deadline.** `deadline` is 5000 ms per example
   (src/ecdsa/test_malformed_sigs.py line 155, "because NIST521p are slow to
   verify", line 154). A slower run, under the `sys.monitoring` callbacks of the
   recorder (T/reach/recorder.py lines 19 and 37) for instance, can exceed it
   and fail a test that passes without the recorder.
4. **Status rules.** `MalformedPointError` inherits from `AssertionError`
   (src/ecdsa/errors.py line 1), so a test stopped by it counts as stopped on a
   failed assertion under status rule 3 (T/PROTOCOL.md lines 385-389;
   T/reach/recorder.py line 555): withheld, not crashed. hypothesis raises a
   `BaseExceptionGroup` when it finds several distinct failures
   (hypothesis/core.py line 1714 in the environment), which is no
   `AssertionError`: crashed, whatever it holds.
5. **OpenSSL.** The tests call the system `openssl`. It lists `prime192v1`
   (command 17), so the included block of `TooSmallCurve` (skip condition at
   src/ecdsa/test_pyecdsa.py lines 1790-1793) runs on this machine. Another
   OpenSSL can change which tests skip; `requirements.txt` does not record it.
6. **Files the tests write.** Tests make a directory `t` in the working
   directory (src/ecdsa/test_ecdh.py lines 398-400; src/ecdsa/test_pyecdsa.py
   lines 1305-1307 and 1573-1575), and hypothesis writes `.hypothesis/` there:
   in the copies, not in the clone, as long as every run works on a copy.
7. **Default paths.** The defaults of `run.py` (`--work` T/work/<name>, line
   126; witnesses T/witnesses/<name>, line 145; the archive of `pack`
   T/generated/<name>, line 726) and of `analyse.py` (`--work` and `--out`,
   lines 847-848) point into T. Every call for ecdsa needs `--work`, `--defs`,
   `--out` and, for `witness`, `--witnesses` under X. `X/.gitignore` did not
   exist at 14:10:43Z (`ls -la X`), so `X/work` is not yet ignored by git.
8. **Size.** The suite run collects 2023 tests, 800 of them in
   test_pyecdsa.py, some of which call `openssl`; its duration is unknown,
   since no test ran.
