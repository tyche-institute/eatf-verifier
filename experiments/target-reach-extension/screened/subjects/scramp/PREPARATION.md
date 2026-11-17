# scramp 1.5.0: preparation of the definitions

This file records how the definitions in this folder were made: every command run on the library, its
time and what it gave. Paths are relative to the root of the repository: `T` is
`experiments/target-reach` (the toolkit, used unchanged), `X` is `experiments/target-reach-extension`,
`D` is `X/screened/subjects/scramp` (this folder) and `W` is `X/work/scramp`, which holds the clone, the
environment, the copies and the logs of this preparation and is not part of the definitions. All times
are UTC on 17 November 2026; the clock times inside the logs of `T/reach/run.py` are the local time of
the machine, UTC+1 (row 43).

Nothing ran on the library but the clone, the environment, `pytest --collect-only -q` and the static
steps `define`, `targets` and `verify` of `T/reach/run.py`. No test function ran, under the recorder or
without it, and nothing was deleted.

## 1. Result

1. **Defined.** `D` holds `draft.json` (the 6 decisions of `T/PROTOCOL.md` lines 82-93, each with its
   source, and the settings of lines 100-105), `subject.json` (written by `T/reach/scope.py`),
   `requirements.txt` (`pip freeze` of the environment) and `checks.json`, `blocks.json` and
   `targets.json` (written by `T/reach/run.py define targets`). `verify` accepts the clone, the
   definitions and the environment (section 5).
2. **The tests cannot be collected from the copy.** `src/scramp/__init__.py` line 8 is
   `__version__ = version("scramp")`, with `version` from `importlib.metadata` (line 1): on import, the
   package reads its version from the metadata of an installed distribution `scramp`. The runs import
   the library from a copy of the release and do not install it (`T/PROTOCOL.md` lines 276-278).
   `verify` refuses an environment in which the distribution is installed (`T/reach/run.py` lines
   244-257) and a clone whose copied paths hold a file that is not one of the commit (lines 215-226),
   so a copy cannot carry that metadata either. `test/test_scramp.py`, the only test file of the
   subject (`D/subject.json`, `tests`) and the file of the 3 included blocks, imports `scramp` (its line
   7) and fails at collection with `importlib.metadata.PackageNotFoundError: No package metadata was
   found for scramp`; collected alone, it gives `no tests collected, 1 error` (section 4).
   `test/test_import_all.py` fails the same way, and `test/test_utils.py` does when it is collected
   alone or first. No case of the study can run. None of the 6 decisions and none of the settings of
   `draft.json` can supply the metadata that line 8 reads. The project runs its own tests under tox
   (`README.md` lines 732-736), whose configuration (`pyproject.toml` lines 44-111) has no
   `skip_install` (row 40). `T/PROTOCOL.md` lines 134-135: "A library whose tests cannot be run under
   the recorder without changing 1 of the 6 decisions is reported as failed, with the reason." The
   library, its tests and the toolkit were not changed.
3. **I4.** With the 4 public entry points of the documentation, `define` includes 3 blocks
   (`D/blocks.json`, `counts`), fewer than the 10 of criterion I4 (`T/SELECTION.md` lines 62-66). The
   screening counted 10 blocks with a larger set of entry points: the 4 methods, the internal step
   functions, `_check_client_key` and the message parsers (`T/selection/screening-results.json` lines
   652 and 657). It noted: "Public entry points only: 3 blocks (set_server_first line 954,
   set_client_final line 1090, set_server_final with match= line 1538)" (line 658). The 3 blocks that
   `define` includes are these 3.
4. **No compiled extension.** The wheel `scramp-1.5.0-py3-none-any.whl` of PyPI holds the 3 modules of
   `src/scramp` and its `dist-info` directory, nothing else, and the SHA-256 of its 3 modules equal those
   that `D/checks.json` records for the files of the commit (section 3, rows 19 and 36). Nothing was
   built.

## 2. Counts

Every count is taken from the files that the toolkit wrote in `D`.

| Count | Value | Source |
|---|---|---|
| Subject files | 3: `scramp/__init__.py`, `scramp/core.py`, `scramp/utils.py` | `subject.json`, `subject_files` |
| Observed files | 0 | `subject.json`, `observed_files` |
| Test files of the subject | 1: `test/test_scramp.py` | `subject.json`, `tests`; `blocks.json`, `test_files` |
| Test directories | 4 test files, 31 blocks, 1 test file with an included block | `subject.json`, `scope_counts` |
| Checks | 91, all in subject files, all of class `ScramException` | `checks.json`, `checks` (`role`, `class`) |
| Reachable checks | 29: 28 in `scramp/core.py`, 1 in `scramp/utils.py` | `checks.json`, `checks` (`reachable`) |
| Function definitions | 102, of which 25 reachable | `checks.json`, `functions` |
| Raise statements listed apart | 2: `scramp/core.py` line 164, `TypeError` ("not a rejection class"); line 579, a bare `raise` | `checks.json`, `other_raises` |
| Blocks in the test files of the subject | 27 | `blocks.json`, `counts` (`blocks`) |
| Blocks that call an entry point | 3 | `blocks.json`, `counts` (`entry_point_blocks`) |
| Included blocks | 3: 2 assert only the class, 1 asserts more (`match=`) | `blocks.json`, `counts` (`included`) and `blocks` (`match`, `post`); `T/reach/analyse.py` lines 153-156 |
| Targets in the assertion tier | 0 | `targets.json`, `counts` |
| Targets in the name tier | 1 | `targets.json`, `counts` (`name`: 1) |
| Blocks without a target | 2, both by a tie | `targets.json`, `counts` (`none: tie`: 2) |

The included blocks (`blocks.json`, `blocks`: `header_span`, `entry_calls`, `expected`, `match`;
`targets.json`, `blocks`: `target`, `tier`, `reason`, `tied`):

| Block of `test/test_scramp.py` | Lines | Entry point called | Expected | Asserts more than the class | Target |
|---|---|---|---|---|---|
| `test_client_order#0` | 954 | `set_server_first` | `ScramException` | no | none: 13 checks tie |
| `test_server_order#0` | 1090 | `set_client_final` | `ScramException` | no | none: 11 checks tie |
| `test_ScramClient_set_server_final_missing_param#0` | 1538-1542 | `set_server_final` | `ScramException` | yes | `core._set_client_final#3`, name tier |

Of the 24 blocks that are not included, 23 call no entry point and 1 calls no entry point and expects
`TypeError` (`blocks.json`, `exclusion`). The 29 reachable checks are in 11 functions:
`_set_client_first` (5), `Gs2Header.from_str` (4), `IterationCount.from_str` (4), `_check_stage` (3),
`_set_client_final` (3), `_set_server_first` (3), `_check_client_key` (2), `_set_server_final` (2),
`ScramServer._set_mechanism` (1), `ScramServer.set_client_first` (1) and `b64dec` (1). Of the 62 checks
that are not reachable, 41 are in `__init__` methods, 10 of them in `Message.__init__`; no `__init__` is
reachable, and no function definition of the subject files has the name of 1 of its 22 classes
(`checks.json`, `functions` and `classes`). Reachability follows the names that a function calls or
mentions, from the function definitions that have the name of an entry point (`T/PROTOCOL.md` lines
208-212); lines 668-670 list the limits of this matching by name.

## 3. Commands run on the library

`T`, `X`, `D` and `W` as above. The outputs named are in `W/prep/` and `W/collect/`.

| # | Time | Command | What it gave |
|---|---|---|---|
| 1 | 13:51:34Z | `/usr/bin/python3.12 --version` | `Python 3.12.3` |
| 2 | 13:52:00Z | `curl -sS -o scramp.json https://pypi.org/pypi/scramp/json`; `curl -sS -o scramp-1.5.0.json https://pypi.org/pypi/scramp/1.5.0/json` (in `W/prep/pypi/`) | HTTP 200 and 200; SHA-256 97306326f0ebfe5c4e79d8a09edac846e5669997857acdc2e7a3fc018d977b5c and 0c0f33e40817e2f2252e0ad6a36578e7fae0326e537df5193e1fc957f6c66996 |
| 3 | 13:52:05Z, 13:52:09Z | `python3 -I -c` reads of the 2 files | latest version 1.5.0; 28 versions, 0.0.0 to 1.5.0; `project_urls` Homepage https://codeberg.org/tlocke/scramp; `requires_python` `>=3.11`; `requires_dist` `asn1crypto>=1.5.1`; files of 1.5.0: the wheel, uploaded 2026-10-25T17:43:17.870373Z, SHA-256 8280608f568e81da9e9c9d69cac1331b836622d9b48bf5c5e400e16129c6d1fa, and the sdist, uploaded 2026-10-25T17:43:19.122702Z, SHA-256 21b88a54bc4b656f57de9f0f6be531ca99f7efe49220bbd083b84cf88748e395 |
| 4 | 13:52:14Z | `git ls-remote --tags https://codeberg.org/tlocke/scramp` | exit 0; 56 lines; `refs/tags/1.5.0` afe02849b18a83af1a16f250efe326e6c5af2556 (annotated tag), `refs/tags/1.5.0^{}` 58a281a2b0570834a39e78dcc9d52aa8245c0aea |
| 5 | 13:52:20Z | `git clone --quiet https://codeberg.org/tlocke/scramp W/clone` | exit 0 at 13:52:25Z |
| 6 | 13:52:25Z | `git -C W/clone checkout --quiet 58a281a2b0570834a39e78dcc9d52aa8245c0aea`; `git rev-parse HEAD`; `git describe --tags --exact-match`; `git cat-file -p 1.5.0`; `git log -1` | exit 0; HEAD 58a281a2b0570834a39e78dcc9d52aa8245c0aea, tag `1.5.0`; tag message "version 1.5.0"; commit time 2026-10-25T17:41:52Z |
| 7 | 13:52:31Z | `git -C W/clone ls-files` | 11 files: `.gitignore`, `LICENSE`, `README.md`, `pyproject.toml`, `src/scramp/__init__.py`, `src/scramp/core.py`, `src/scramp/utils.py`, `test/test_import_all.py`, `test/test_readme.py`, `test/test_scramp.py`, `test/test_utils.py` |
| 8 | 13:52:34Z | `cat -n pyproject.toml .gitignore`; `wc -l README.md src/scramp/*.py test/*.py` (in `W/clone`) | the build backend `hatchling.build` (`pyproject.toml` lines 2-3), the tox configuration (lines 44-111); `README.md` 917 lines, `core.py` 1209, `test/test_scramp.py` 1543 |
| 9 | 13:53:21Z | `cat -n test/test_import_all.py test/test_readme.py src/scramp/__init__.py`; `sed -n 1,40p test/test_scramp.py`; `sed -n 1,30p test/test_utils.py` | `src/scramp/__init__.py` line 8 `__version__ = version("scramp")`; `test/test_readme.py` lines 6-7 run `doctest.testfile` on `../README.md` |
| 10 | 13:54:30Z | search for `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`, `setup.py` and `conftest.py` in `X/work` and each of its parent directories | none |
| 11 | 13:54:34Z | `cat -n src/scramp/utils.py`; `grep -n` of the classes, `def set_`, `def _set_`, `raise` and imports of `src/scramp/core.py` | `utils.py` line 38 `class ScramException(Exception)`; `core.py` `class ScramClient` line 457 (`set_server_first` 543, `set_server_final` 565), `class ScramServer` line 584 (`set_client_first` 609, `set_client_final` 649) |
| 12 | 13:55:00Z | `grep -n` of the imports, `mocker`, `importorskip`, `skipif` and `xfail` in `test/*.py`; `grep -c mocker test/test_scramp.py` | the fixture `mocker` in `test/test_utils.py` lines 67 and 79 and in 12 lines of `test/test_scramp.py`, the first at line 552 |
| 13 | 13:55:05Z | `curl` of https://pypi.org/pypi/NAME/json for asn1crypto, pytest, pytest-mock, pluggy, iniconfig, packaging and Pygments | latest versions 1.5.1, 9.2.0, 3.17.0, 1.7.0, 2.3.1, 26.3 and 2.21.0 |
| 14 | 13:56:22Z | `git -C W/clone status --porcelain --untracked-files=all --ignored`; `date -u -d @1792950154` (the tagger time of row 6) | empty; tag time 2026-10-25T17:42:34Z |
| 15 | 13:56:42Z | `curl` of https://files.pythonhosted.org/packages/1f/10/a32f434a66d8c0b3c09a9e314213591017d2a96ec3bd2568717669e582c9/scramp-1.5.0.tar.gz; `sha256sum`; `tar -xzf`; `cmp` of each file with `W/clone` | HTTP 200; SHA-256 21b88a54bc4b656f57de9f0f6be531ca99f7efe49220bbd083b84cf88748e395, the digest of PyPI; 12 files: `PKG-INFO` and the 11 files of the commit, each identical |
| 16 | 13:56:48Z | `/usr/bin/python3.12 --version`; `/usr/bin/python3.12 -m venv W/venv`; `W/venv/bin/python -m pip list` | `Python 3.12.3`; done at 13:56:50Z; CPython 3.12.3, pip 24.0 and no other package |
| 17 | 13:56:54Z | `W/venv/bin/python -m pip install --disable-pip-version-check 'asn1crypto>=1.5.1' pytest pytest-mock`; `pip freeze` | exit 0 at 13:56:55Z; "Successfully installed asn1crypto-1.5.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.2.0 pytest-mock-3.17.0" (`W/prep/pip-install.log`); 7 pins (`W/prep/pip-freeze.txt`) |
| 18 | 13:57:04Z, 13:57:10Z | `grep -n` of `README.md`, `src/scramp/*.py` and `pyproject.toml` for the lines that `draft.json` cites | the lines cited in `draft.json` |
| 19 | 13:57:41Z | `python3 -I -c` read of all files of `scramp.json`; `curl` of https://files.pythonhosted.org/packages/ff/62/231ee179d8995d28981414432bf79492f0b909f5820452b77f422fdce259/scramp-1.5.0-py3-none-any.whl; `sha256sum`; list of its members | 56 files, none yanked, no version with a pre-release part; the last 2 uploads are those of 1.5.0; HTTP 200; SHA-256 8280608f568e81da9e9c9d69cac1331b836622d9b48bf5c5e400e16129c6d1fa, the digest of PyPI; members `scramp/__init__.py`, `scramp/core.py`, `scramp/utils.py` and `scramp-1.5.0.dist-info/` `METADATA`, `WHEEL`, `licenses/LICENSE`, `RECORD` |
| 20 | 13:58:09Z | `D/draft.json` written | the decisions and settings of section 6 |
| 21 | 13:58:16Z | from `T`, with `PYTHONHASHSEED=0`: `python3 -I -B reach/scope.py --draft D/draft.json --clone W/clone` | exit 0; "scope: 3 subject files, 1 test files" (`W/prep/scope.log`) |
| 22 | 13:58:19Z | `python3 -I -c` read of `D/subject.json` | `subject_files`, `observed_files`, `tests` and `scope_counts` of section 2 |
| 23 | 13:58:26Z | `W/venv/bin/python -m pip freeze --disable-pip-version-check > D/requirements.txt`; `cmp` with `W/prep/pip-freeze.txt` | 7 pins, identical |
| 24 | 13:58:45Z | `cp -a W/clone/src W/clone/test W/clone/README.md W/collect/copy/`; collect-only of `test` (section 4) | exit 1; "8 tests collected, 2 errors in 0.08s" |
| 25 | 13:59:03Z | collect-only of `test/test_scramp.py`, then of `test/test_utils.py` (section 4) | exit 1, "no tests collected, 1 error in 0.06s"; exit 1, "no tests collected, 1 error in 0.03s" |
| 26 | 13:59:12Z | from `T`, with `PYTHONHASHSEED=0`: `python3 -I -B reach/run.py define targets verify --subject D/subject.json --defs D --work W --clone W/clone --python W/venv/bin/python` | exit 0; section 5 |
| 27 | 13:59:23Z to 13:59:43Z | `python3 -I -c` reads of `D/checks.json`, `D/blocks.json` and `D/targets.json` | the counts of section 2 |
| 28 | 14:00:09Z | `grep -n` of `src/scramp/*.py` and `test/*.py` for `NoneType`, `match` statements and other syntax of recent Python versions | `src/scramp/utils.py` line 21 and `src/scramp/core.py` line 10 import `NoneType` from `types`; `core.py` line 859 `match k:` |
| 29 | 14:00:27Z to 14:00:36Z | `python3 -I`, a scan of every raise statement of the 3 subject files with the module `ast` against the lines of `D/checks.json` (the first call stopped on an error of the scan itself, which was corrected) | 93 raise statements: 91 are the lines of the 91 checks, 1 for each check; 2 are the raises listed apart; none is missing |
| 30 | 14:01:03Z | `uv python list --only-installed` | CPython 3.12.3 (`/usr/bin/python3.12`), 3.11.15, 3.10.20 and 3.9.25, the last 3 managed by uv |
| 31 | 14:01:11Z | CPython 3.9.25 and 3.10.20, `-I -c`: `ast.parse` of the 3 subject files and `hasattr(types, "NoneType")` | 3.9.25: `core.py` does not parse ("invalid syntax" at line 859), `utils.py` and `__init__.py` parse, no `types.NoneType`; 3.10.20: the 3 files parse, `types.NoneType` exists |
| 32 | 14:01:41Z | from `T`: `python3 -I -B reach/run.py define targets --subject D/subject.json --defs W/prep/define-again --work W`; `cmp` of the 3 files with those of `D` | exit 0; the same 2 output lines as row 26; the 3 files identical |
| 33 | 14:01:46Z | `find T -newermt '2026-11-17 13:45:00Z'`; `git status --short` of the repository | no file of `T` changed; the only untracked path is `X` |
| 34 | 14:02:27Z | in `W/clone`: `grep -rn` of `docutils`, `ruff`, `twine`, `validate_pyproject`, `validate-pyproject`, `import build`, `from build` in `*.py`; `grep -n asn1crypto src/scramp/*.py test/*.py` | no match (exit 1); `asn1crypto` imported by `src/scramp/core.py` lines 12-13 only |
| 35 | 14:03:29Z | collect-only of `test/test_utils.py test/test_import_all.py test/test_readme.py test/test_scramp.py` (section 4) | exit 1; "1 test collected, 3 errors in 0.08s" |
| 36 | 14:12:49Z | `python3 -I` with `zipfile` and `hashlib`: SHA-256 of each member of the wheel of row 19 against `D/checks.json`, `sha256` | the 3 modules equal: 92a3227318a1e73a4877f2dc7950d855a291895d48077319b98bafad41e81c91, f240176fe1c07861c37ed195b25e9b52356a5457888ab2c942cf30285420973a, 9fcd0a398ab9a09ab0e72b81afb5a6a27eba239796d3f3ea54864461ab61464b |
| 37 | 14:13:04Z, 14:17:29Z | `python3 -I -c` counts of `D/checks.json` by function; names of its classes and functions | the counts of section 2 |
| 38 | 14:13:13Z to 14:13:22Z | `awk` and `grep -n` of `README.md`: the lines that `draft.json` cites, the headings, the release notes | as cited in `draft.json` and here |
| 39 | 14:14:13Z | `sha256sum` of the 6 files of `D`; `find T -newermt '2026-11-17 13:45:00Z'`; `git status --short` | the digests of section 5; no file of `T` changed |
| 40 | 14:16:03Z | `wc -l pyproject.toml`; `grep -n 'tool.pytest\|skip_install\|package =' pyproject.toml`; the search of row 10 in `W`, `W/collect` and `W/collect/copy`; `sed -n` of the lines cited in sections 4 and 6 | 111 lines; no match (exit 1); no file found |
| 41 | 14:20:45Z | `grep -n` of lines 615-731 of `README.md` (API Docs) for names that start with `_`; `wc -l README.md src/scramp/*.py test/*.py` | no match (exit 1); the line counts of row 8 |
| 42 | 14:22:19Z | `git -C W/clone status --porcelain --untracked-files=all --ignored`; `git -C W/clone rev-parse HEAD`; `sha256sum` of the files of `D`; `find T -newermt '2026-11-17 13:45:00Z'`; `git status --short` of the repository | empty; 58a281a2b0570834a39e78dcc9d52aa8245c0aea; the digests of section 5; no file of `T` changed; the only untracked path is `X` |
| 43 | 14:27:18Z | `date +%z`; `cat -A W/prep/run-define-targets-verify.log`; `sed -n 10p W/clone/pyproject.toml` | `+0100`; the clock time 14:59:12 on each of the 6 lines of the log of row 26; `requires-python = ">=3.11"` |
| 44 | 14:30:23Z | the commands of row 42 again, at the end of the preparation | the same results |

## 4. Collection

From `W/collect/copy`, a copy of the paths of `copy` (row 24), with the environment of `T/reach/run.py`
lines 155-175 (`PATH`, `HOME`, `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `PYTHONHASHSEED=0`,
`PYTHONDONTWRITEBYTECODE=1`, and as `PYTHONPATH` the folder `T/guard` and the source root of the copy)
and the 2 output files of the offline module `T/guard/reach_offline.py` (`OFFLINE_OUT`, `OUTCOMES_OUT`):

    env -i PATH=W/venv/bin:/usr/bin:/bin HOME=... LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONHASHSEED=0 \
        PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=T/guard:W/collect/copy/src \
        OFFLINE_OUT=W/collect/offline.NAME.json OUTCOMES_OUT=W/collect/outcomes.NAME.json \
        W/venv/bin/python -m pytest -q -p no:cacheprovider -p reach_offline --rootdir=. \
        --continue-on-collection-errors --collect-only PATHS

The options are those of `T/reach/run.py` lines 338-339 with `--collect-only` and without `--tb=native`
and `-rfE`.

| Time | Paths | Exit | Summary line of pytest | Collected | Collectors that failed (`outcomes` file) |
|---|---|---|---|---|---|
| 13:58:45Z | `test`, the path of the suite run `all` | 1 | 8 tests collected, 2 errors in 0.08s | `test/test_readme.py::test_readme` and 7 tests of `test/test_utils.py` | `test/test_import_all.py`, `test/test_scramp.py` |
| 13:59:03Z | `test/test_scramp.py`, the `tests` of `subject.json` | 1 | no tests collected, 1 error in 0.06s | none | `test/test_scramp.py` |
| 13:59:03Z | `test/test_utils.py` | 1 | no tests collected, 1 error in 0.03s | none | `test/test_utils.py` |
| 14:03:29Z | `test/test_utils.py test/test_import_all.py test/test_readme.py test/test_scramp.py` | 1 | 1 test collected, 3 errors in 0.08s | `test/test_readme.py::test_readme` | `test/test_import_all.py`, `test/test_scramp.py`, `test/test_utils.py` |

Each error is the same import error. For `test/test_scramp.py` (`W/collect/collect-all.log` lines
51-64, without the 3 lines that hold only `^` markers):

    test/test_scramp.py:7: in <module>
        from scramp import (
    src/scramp/__init__.py:8: in <module>
        __version__ = version("scramp")
    /usr/lib/python3.12/importlib/metadata/__init__.py:889: in version
        return distribution(distribution_name).version
    /usr/lib/python3.12/importlib/metadata/__init__.py:862: in distribution
        return Distribution.from_name(distribution_name)
    /usr/lib/python3.12/importlib/metadata/__init__.py:399: in from_name
        raise PackageNotFoundError(name)
    E   importlib.metadata.PackageNotFoundError: No package metadata was found for scramp

`test/test_import_all.py` fails the same way from its line 1, `from scramp import *` (lines 24-37 of the
same log). `test/test_utils.py` imports `scramp.utils` (its line 5); its 7 tests are collected when the
whole directory `test` is collected, and not when the file is collected alone or before the other files.
`test/test_readme.py` (lines 5-11) runs the examples of `README.md` with `doctest.testfile`; the name
`../README.md` is relative to the directory of the test module (`/usr/lib/python3.12/doctest.py` lines
2017-2024), and the examples import the package (`README.md` line 86). It was not run. In each call the
offline module counted 0 connection attempts (`attempts` in the 4 `offline` files).

## 5. define, targets and verify

Row 26, exit 0. Its output (`W/prep/run-define-targets-verify.log`):

    define: 91 checks (91 in subject files, 29 reachable); 27 blocks in the 1 test files of the subject, 3 included in 1 files; the test directories hold 31 blocks in 4 test files
    targets: rule reach-target-rule/2; {"name": 1, "none: tie": 2}
    verify: commit 58a281a2b057, 3 subject files and 1 test files match, CPython 3.12.3

`--defs D` puts `checks.json`, `blocks.json` and `targets.json` beside `subject.json` and reads
`D/requirements.txt` (`T/reach/run.py` lines 125, 148-153, 189-190, 204 and 241-243). `--work W` keeps
the file `local.json` (the clone and the interpreter) in `W` (lines 126-136) instead of
`T/work/scramp`. The repeat of row 32 wrote the same 3 files. SHA-256 of the files of `D` (rows 39 and 42):

| File | SHA-256 |
|---|---|
| `blocks.json` | 2083fd4a6f5bc89693ccbec551cc496a2354f02ed14e57a410669f32786e41bc |
| `checks.json` | 08599419e24bc09a327f2f3dad7a43a145a8182c660cdebfc524483b8a0c1e15 |
| `draft.json` | 0bd977d19deba2127e6295066acdac83d985025ebc7396bddbfe2a84a972002a |
| `requirements.txt` | 3cc44c5784cf96b7aca4fb04a363ec8b015ef36118a5866f24766e7df258b0b4 |
| `subject.json` | 1dba0528590f15f6ec41231cc12d85bc8c48284543724eb15aac725ef931a39f |
| `targets.json` | b686f9226bbaf9471d0e45e7c41aa22f59f4293776583474975227c69090e871 |

## 6. Decisions and settings

Each decision of `draft.json` gives its source in the field that ends in `_source`. `draft.json` also
gives the sources of the release and of the package (`release_source`, `package_source`), which
`scope.py` copies into `subject.json`.

- **Release** (`T/PROTOCOL.md` lines 85-86): 1.5.0, tag `1.5.0`, commit
  58a281a2b0570834a39e78dcc9d52aa8245c0aea (rows 2-6). No file of any version was uploaded after
  2026-10-25T17:43:19.122702Z (row 19), so 1.5.0 was also the latest release on 14 November 2026.
- **Entry points**: the 4 methods that the API docs of `README.md` give for setting a received message:
  `ScramClient.set_server_first` and `set_server_final` (lines 658 and 660), `ScramServer.set_client_first`
  and `set_client_final` (lines 723 and 725). The API docs name `scramp.MECHANISMS`, `scramp.ScramClient`,
  `scramp.ScramMechanism` and `scramp.ScramServer` (lines 617, 621, 663 and 719), and no name that
  starts with `_` (row 41), so the internal step functions and `_check_client_key` of the screening
  (`T/selection/screening-results.json` lines 632-642) are not entry points here (decision 3, "the
  names of the public functions or methods through which a received artifact is submitted for
  verification", `T/PROTOCOL.md` lines 88-89).
- **Rejection base**: `ScramException`, which the examples "Server Error" and "Avoiding User
  Enumeration" catch around `set_client_first`, `set_client_final` and `set_server_final`
  (`README.md` lines 467-471, 538-541 and 549-552) and which the release notes of 1.4.4 name for a
  malformed message (lines 850-851); `src/scramp/utils.py` line 38.
- **Test directories**: `test`, the path of the pytest call of tox (`pyproject.toml` lines 78-84;
  `README.md` lines 732-736).
- **Suite runs**: 1 run, `all`, on `test`: tox has 1 environment (`envlist = ["py"]`, `pyproject.toml`
  line 46) with 1 pytest call, `pytest -v -x "-W error" test` (lines 78-84). The run keeps the path and
  not the options, as the subjects of `T` keep the paths of their calls without their options:
  `--cov=oauthlib` (`T/subjects/oauthlib/draft.json` line 31), `--showlocals --full-trace`
  (`pyproject.toml` line 139 of joserfc at commit f345ff71cd6c36452a4e11e47b805ad450a95dd8) and
  `--capture=no --strict-markers` under `coverage run` (`tox.ini` line 15 of jwcrypto at commit
  c10aa4343f9ce2e68caaf20aef9d2c5f6d0c4d71); no suite run of a `draft.json` or `subject.json` of `T`
  has options of its own, `args` (`grep -rn '"args"'` of `T/subjects/*/draft.json` and
  `T/subjects/*/subject.json`, 13:52:44Z: no match). `-x` stops the call at its first failure and
  `-W error` turns warnings into errors; whether a test of scramp emits a warning is not known without
  a run.
- **Settings** (`T/PROTOCOL.md` lines 100-105): `copy` is `src`, `test` and `README.md`; `README.md` is
  read by `test/test_readme.py` (section 4); `pyproject.toml` holds no pytest configuration (row 40),
  and no pytest configuration file exists in `W/collect/copy` or any of its parent directories (rows 10
  and 40). `pytest_args` is `-p no:cacheprovider`, which every `subject.json` of `T` holds; the 2 of
  PyJWT add `-p no:randomly` (read of `T/subjects/*/subject.json`, 14:27:18Z), and pytest-randomly is
  not in this environment (`D/requirements.txt`). `source_root` is `src` (row 7). `python` is 3.12.3.
  `distribution` is `scramp` (`pyproject.toml` line 6).
- **Environment** (rows 16, 17 and 23): CPython 3.12.3 from `/usr/bin/python3.12`, with the dependency
  of the package, `asn1crypto >= 1.5.1` (`pyproject.toml` line 23), and the 2 packages of the deps of
  tox that the pytest call needs, `pytest` and `pytest-mock` (lines 104-105; `pytest-mock` gives the
  fixture `mocker`, row 12). Not installed: `ruff`, `docutils`, `build`, `twine` and
  `validate-pyproject` (lines 106-110), which no Python file of the commit imports (row 34) and which
  serve the other commands of tox (lines 50-77 and 85-99), as `T/subjects/joserfc/requirements.txt`
  holds `pytest` and not `mypy`, `pytest-cov`, `ruff` or `pre-commit` of the dev group of joserfc
  (`pyproject.toml` lines 54-62 of joserfc at the commit above). The library itself is not installed
  (`T/PROTOCOL.md` lines 276-278), and no `requirements.txt` of `T` pins its own library (`grep` of each
  `T/subjects/NAME/requirements.txt` for the `distribution` of its `subject.json`, 14:20:45Z: 0 pins in
  each of the 7).

## 7. Other versions of CPython

`pyproject.toml` line 10 (row 43) and PyPI (row 3) give `requires-python = ">=3.11"`. CPython 3.9.25 cannot parse
`src/scramp/core.py`, whose line 859 is a `match` statement, and has no `types.NoneType`, which
`src/scramp/utils.py` line 21 and `src/scramp/core.py` line 10 import; CPython 3.10.20 parses the 3
subject files and has `types.NoneType` (row 31). Nothing was imported or run with them. This machine has
no CPython 3.13 or 3.14 (row 30).

## 8. For the later steps

From the code of the toolkit and of pytest 9.2.0 in `W/venv`; nothing of this was run.

- `T/reach/run.py` and `T/reach/analyse.py` write into `T` unless `--work W` is given (`run.py` line
  126, `analyse.py` line 847: default `T/work/scramp`) and, for `pack` and `analyse.py`, `--out`
  (`run.py` line 726, `analyse.py` line 848: default `T/generated/scramp`). `--defs` defaults to `D`
  (`run.py` line 125, `analyse.py` line 846).
- `suite` runs the files of `tests` (`run.py` lines 345 and 389) and records the files of the
  collectors that failed as `not_collected` (lines 400-401 and 405); `test/test_scramp.py` would be one
  of them (section 4). It stops only when pytest cannot collect the test paths at all (lines 403-404).
  A recorder run adds `--ignore=test/test_scramp.py` (lines 342-344) and still names the file (line
  345). When pytest collects the files of a directory, it skips the `--ignore` check for a file given
  on the command line (`_pytest/main.py` lines 584-586; lines 716-719 define these initial paths), so
  the recorder runs would meet the import error of section 4. Sentinel 2 asks that every test file is
  collected (`T/PROTOCOL.md` lines 472-474).
- The whole-suite runs run `test` (`subject.json`, `suite_runs`), whose collection gave 8 tests and 2
  errors (section 4).
