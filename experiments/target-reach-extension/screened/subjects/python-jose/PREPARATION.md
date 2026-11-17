# python-jose 3.5.0: preparation

This folder holds the definitions of `python-jose` 3.5.0 for the part `screened/`: `draft.json`;
`subject.json`, written from it by `reach/scope.py`; `requirements.txt`, the environment; and
`checks.json`, `blocks.json` and `targets.json`, written by the steps `define` and `targets` of
`reach/run.py`. The library was defined, its tests were collected and `verify` passed. Nothing else
ran on it: no test under the recorder, no deletion, no whole-suite run.

Paths: `T` is `experiments/target-reach` (the toolkit, used unchanged), `X` is
`experiments/target-reach-extension`, `S` is this folder (`X/screened/subjects/python-jose`) and `W`
is `X/work/python-jose`, which holds the clone, the environment and the logs and is not deposited.
The commands ran with absolute paths; the prefix of the machine is left out below, and `<home>`
stands for the home directory. Times are UTC, on 2026-11-17. A range is the start and the end that
`date -u` printed inside the command or, for a row of several commands, the starts of the first and
of the last; a single time is the start of the command.

## Counts

The counts come from the files of this folder, read by `W/prep/count.py` (output
`W/prep/counts.txt`), or from the output of the command named.

| Count | Value | Source |
|---|---|---|
| Checks | 99, all in subject files | `checks.json`, list `checks`: 99 entries, each with `"role": "subject"` |
| Reachable checks | 55 | `checks.json`, list `checks`: 55 entries with `"reachable": true` |
| Rejection classes | 12 | `checks.json`, `rejection_classes` (line 6719) |
| Raises of other classes (not checks) | 31 | `checks.json`, `other_raises`: 31 entries, each "not a rejection class" |
| Blocks in the test files of the subject | 58, in 5 files | `blocks.json`, `counts.blocks` (lines 2049-2053) and `test_files` |
| Blocks that call an entry point | 44 | `blocks.json`, `counts.entry_point_blocks` |
| Included blocks | 44 | `blocks.json`, `counts.included` |
| Included blocks, class-only | 40 | `blocks.json`: included blocks with no `match`, `match_unparsed`, `post` or `post_unparsed`, the test of `T/reach/analyse.py`, lines 153-156 |
| Test directories: test files, blocks | 18, 91 | `subject.json`, `scope_counts` (lines 67-71) |
| Targets, assertion tier | 2 | `targets.json`, `counts` (lines 3635-3641): `assert-literal` 2, no `class` and no `assert`; the tiers are `constants.assertion_tier` (lines 3580-3584) and `constants.name_tier` (lines 3586-3589) |
| Targets, name tier | 18 | same: `assert+name` 1, `name` 17 |
| Included blocks without a target | 24 | same: `none: tie` 19, `none: no name token matches` 5 |
| Tests collected, suite run `compatibility` (`tests`) | 470, in 18 files | `W/prep/collect-suite.log`, line 510 |
| Tests collected, the 5 test files of `subject.json` | 256 | `W/prep/collect-recorder-files.log`, line 289 |

## Files of this folder

| File | SHA-256 | Written by | Time |
|---|---|---|---|
| `draft.json` | `a4133b0553536685b7a3aa44440f0fd19ef6737b8584de68f4a9d6e3dca28fe8` | from the sources it names | 13:58:22Z; `test_directories_source` rewritten 13:59:22Z |
| `subject.json` | `bb85b87348500ffca390641bbd00536c03739a00f54375aafd4570ef57edb0b3` | `T/reach/scope.py` | 13:59:27Z-13:59:28Z |
| `requirements.txt` | `a162224ecd4a9186f7a6d5ea8fb76743944ed35bffd6b6edc86e3b4841362f9c` | `pip freeze` in `W/venv` | 13:58:52Z, copied 13:58:56Z |
| `checks.json` | `7605ca601c0c940ffe3af4913e919631f2f91bfd9aaa55120ce5e9b3fad3f7fc` | `T/reach/run.py define` | 14:02:47Z |
| `blocks.json` | `99fc7d1efa2b5f7de7d9b2710bee910f812423396e8c39bb0c46c692a0695bcb` | `T/reach/run.py define` | 14:02:47Z |
| `targets.json` | `f23f2e984bdbd389c9c0c000ee5b701bb2538bac4c33345396cc355cf8c7873e` | `T/reach/run.py targets` | 14:02:47Z |

The digests are those `sha256sum` printed at 14:05:23Z.

## Decisions

The 6 decisions of `T/PROTOCOL.md`, section 3, are in `draft.json`, each with its source:

| Decision | Value | Key of the source |
|---|---|---|
| Release | 3.5.0, tag `3.5.0`, commit `018b310ddb8b50dcfd09a0c152117835a21dd656` | `release_source` |
| Package directory | `jose`, at the root of the repository (`source_root` `.`) | `package_source` |
| Entry points | `decode`, `decrypt`, `verify` | `entry_points_source` |
| Rejection base | `JOSEError` | `rejection_bases_source` |
| Test directories | `tests` | `test_directories_source` |
| Suite runs | 1 run, `compatibility`, on `tests` | `suite_runs_source` |

The values were written at 13:58:22Z, before the first step of the toolkit (13:58:31Z), the
environment (13:58:38Z) and the collection (13:59:48Z). The edit of 13:59:22Z changed only the text
of `test_directories_source`. The drafts of `T/subjects/` have no key for the sources of the release
and of the package; `release_source` and `package_source` are additions of this draft. `scope.py`
carries them into `subject.json` (24 keys) and `define` into the key `subject` of `checks.json`; no
file of `T/reach/` reads them (`grep` for both names, between 14:08:58Z and 14:11:39Z).

The decisions with an alternative:

- **Entry points.** The screening (`T/selection/screening-results.json`, record at line 810)
  counted `jose.jwt.decode` and `jose.jws.verify` and notes: "jwe.decrypt (JWEError family) also
  exists and was not counted." The definitions add `decrypt`. `docs/jwe/api.rst` documents
  `jose.jwe` as `docs/jwt/api.rst` and `docs/jws/api.rst` document `jose.jwt` and `jose.jws`, and the
  docstring of `decrypt` says that it raises `JWEError` "If there is an exception verifying the
  token" (`jose/jwe.py`, lines 61 and 71-72). `T/subjects/joserfc/draft.json` (`decrypt_compact`,
  `decrypt_json`, lines 10-18) and `T/subjects/jwcrypto/draft.json` (`decrypt`, lines 10-16) count
  their decryption functions too. An entry point is a name (`T/PROTOCOL.md`, section 4, lines
  208-212). The definitions with the 3 names are `decode` at `jose/jwt.py:66`; `decrypt` at
  `jose/jwe.py:60`, `jose/backends/base.py:40` and `jose/backends/cryptography_backend.py:478`;
  `verify` at `jose/jws.py:52`, `jose/backends/base.py:15`,
  `jose/backends/cryptography_backend.py:142`, `:311` and `:576`, `jose/backends/ecdsa_backend.py:103`,
  `jose/backends/native.py:61` and `jose/backends/rsa_backend.py:206` (`grep`, 13:55:52Z). 6 of the
  44 included blocks call `decrypt` and no other entry point (`blocks.json`, `entry_calls`).
- **Rejection base.** The docstrings of the entry points name `JWTError`, `ExpiredSignatureError`
  and `JWTClaimsError` (`jose/jwt.py`, lines 120-123), `JWSError` (`jose/jws.py`, lines 64-65) and
  `JWEError` (`jose/jwe.py`, lines 71-72). `JOSEError` (`jose/exceptions.py`, line 1) is the base
  class of all of them and of every other exception class of the module (lines 5-54). Each of the 6
  drafts of `T/subjects/` names 1 base class as well, for example `JoseError` for joserfc and
  authlib, `JWException` for jwcrypto and `PyJWTError` for pyjwt-package. The alternative, `JWTError`, `JWSError` and `JWEError`, would leave
  out `JWKError` (`jose/exceptions.py`, line 29), the class of 39 of the 99 checks, 2 of them
  reachable, and the expected class of 1 included block (`checks.json`, `blocks.json`).
- **Suite runs.** For Python 3.12, `tox.ini` lists 4 environments (`[gh-actions]`, line 13), each
  with 1 pytest call from the root of the repository (line 20 and lines 44-52);
  `.github/workflows/ci.yml` runs tox (line 44).

  | Environment | Marker expression | Extras | Uninstalled |
  |---|---|---|---|
  | `base` | `not (cryptography or pycryptodome or backend_compatibility)` (line 46) | none | none |
  | `cryptography-only` | `not (pycryptodome or backend_compatibility)` (line 48) | `cryptography` (line 54) | `ecdsa`, `rsa` (line 41) |
  | `pycryptodome-norsa` | `not (cryptography or backend_compatibility)` (line 50) | `pycryptodome` (line 55) | `rsa` (line 43) |
  | `compatibility` | none (line 52) | `cryptography`, `pycryptodome` (lines 29-32 and 56) | none |

  A subject has 1 environment, and `verify` holds it to `requirements.txt` (`T/reach/run.py`, lines
  241-243 and 279-305). The suite run is the call of `compatibility` without its coverage options.
  It selects every test, so it holds every test that the 3 other calls select. The alternative, 4
  suite runs with the 3 marker expressions as `args` (`T/reach/run.py`, line 549), would run those
  tests a second time in the same environment, not in the environments of `tox.ini`; the 5 suite
  runs of `T/subjects/authlib/draft.json` cover 5 separate directories. With `cryptography`
  installed, `jose/backends/__init__.py` (lines 3-24) binds `RSAKey`, `ECKey`, `AESKey` and `HMACKey`
  to the classes of `jose/backends/cryptography_backend.py`; without it, as in `base`, to
  `rsa_backend.RSAKey`, `ecdsa_backend.ECDSAECKey`, `None` and `native.HMACKey`. In the 1
  environment, the other backends run through the tests that name their classes, such as the
  parameters `ECDSAECKey` and `CryptographyECKey` of
  `tests/algorithms/test_EC.py::TestECAlgorithm::test_key_too_short` (`W/prep/collect-suite.log`,
  lines 24-25).
- **Test directories.** `tests`: `pytest.ini` sets no `testpaths`, and pytest reads it ahead of the
  section `[tool:pytest]` of `setup.cfg` (pytest 9.2.0, `_pytest/config/findpaths.py`, lines 80 and
  240-252); `tox.ini` runs pytest without a path (line 20); every test file of the repository is
  under `tests/` (13:59:27Z). `setup.cfg` names the same directory (line 72).
- **Copy.** `jose`, `tests` and `pytest.ini`, the configuration that pytest reads (markers, lines
  2-7). `setup.cfg` is not copied, so its `addopts = --cov-report term-missing --cov jose` (line 71)
  reaches no run.
- `pytest_args` `-p no:cacheprovider` and `python` `3.12.3` are those of the drafts of `T/subjects/`.

## Environment

- CPython 3.12.3 (`/usr/bin/python3.12`) and a virtual environment `W/venv` without the system site
  packages, with pip 24.0 as created and not upgraded.
- Installed: the `install_requires` of `setup.cfg` (lines 36-39); the extras `cryptography` (lines
  45-46) and `pycryptodome` (lines 49-50) of `compatibility`; `pytest` and `pytest-cov`, the `deps` of
  every environment of `tox.ini` (lines 35-37). The 15 pins are in `requirements.txt`. Every package
  came as a wheel (`W/prep/pip-install.log`, lines 31-48).
- Not installed: `python-jose` itself, which `verify` checks (`T/reach/run.py`, lines 244-257); the
  extra `pycrypto` (`setup.cfg`, lines 47-48), which no environment of `tox.ini` installs (lines
  53-56); tox and the lint tools (`tox.ini`, lines 58-68).
- No compiled extension is needed: `git ls-files jose` lists 15 files, all `.py`, and `setup.py`,
  `setup.cfg` and `pyproject.toml` hold no `ext_modules` and no `Extension(` (13:58:05Z). The tests
  import `jose` from the root of the copy, and nothing was built. The compiled code of the
  environment is that of the wheels of `cffi`, `coverage`, `cryptography` and `pycryptodome`.

## Commands

| Time | Command | What it gave |
|---|---|---|
| 13:51:52Z | `curl -sS -o pypi-python-jose.json -w '%{http_code}\n' https://pypi.org/pypi/python-jose/json`, then 2 reads of the file with `python3 -I` (13:51:52Z, 13:51:56Z); copy at `W/prep/pypi/python-jose.json`, SHA-256 `45158e5be7642c8f692179aebb6297d0c6f6bfa2f803862871678dc29c147b97` | HTTP 200. Version 3.5.0, not yanked, `requires_python` `>=3.9`; `project_urls` Source `https://github.com/mpdavis/python-jose/`. By upload time 3.5.0 is the last release: wheel 2025-05-28T17:31:52.802629Z (SHA-256 `abd1202f23d34dfad2c3d28cb8617b90acf34132c7afd60abd0b0b7d3cb55771`), sdist 2025-05-28T17:31:54.288302Z (SHA-256 `fb4eaa44dbeb1c26dcc69e4bd7ec54a1cb8dd64d3b4d81ef08d90ff453f2b01b`) |
| 13:52:00Z-13:52:01Z | `git ls-remote --tags https://github.com/mpdavis/python-jose` | `refs/tags/3.5.0` is `018b310ddb8b50dcfd09a0c152117835a21dd656`, with no `^{}` line: a lightweight tag |
| 13:52:42Z-13:52:43Z | `git clone https://github.com/mpdavis/python-jose W/clone` | exit 0 |
| 13:52:47Z | in `W/clone`: `git cat-file -t 3.5.0`; `git rev-parse '3.5.0^{commit}'`; `git log -1 --format='%H %ci %s' '3.5.0^{commit}'`; `git rev-parse HEAD` | `commit`; `018b310ddb8b50dcfd09a0c152117835a21dd656`; "2025-05-28 13:25:04 -0400 Prepare release 3.5.0 (#388)"; the branch `master` was at the same commit |
| 13:52:47Z | `git -c advice.detachedHead=false checkout 018b310ddb8b50dcfd09a0c152117835a21dd656`; `git status --porcelain --untracked-files=all --ignored` | exit 0, "HEAD is now at 018b310 Prepare release 3.5.0 (#388)"; no output |
| 13:52:51Z | `git ls-files` | 66 files |
| 13:52:53Z-13:55:52Z | reads with `cat -n`, `sed -n` and `grep -n` of `pytest.ini`, `tox.ini`, `setup.cfg`, `setup.py`, `pyproject.toml`, the 3 files `requirements*.txt`, `MANIFEST.in`, `.gitignore`, `.github/workflows/ci.yml`, `README.rst`, the pages of `docs/`, `jose/__init__.py`, `jose/exceptions.py`, `jose/jwt.py`, `jose/jws.py`, `jose/jwe.py` and `jose/backends/__init__.py`; `grep` for the definitions named `decode`, `decrypt` and `verify` in `jose` | the sources named in `draft.json` and above |
| 13:58:05Z | `grep` for `ext_modules` and `Extension(` in `setup.py`, `setup.cfg` and `pyproject.toml`; `git ls-files jose` by extension; `grep` for the classes of `jose` | no match; 15 files, all `.py` |
| 13:58:22Z | `S/draft.json` written | the 6 decisions and their sources |
| 13:58:31Z | `python3 -I -B T/reach/scope.py --draft S/draft.json --clone W/clone` (in `W`) | exit 0, "scope: 15 subject files, 5 test files"; `S/subject.json` |
| 13:58:38Z | `/usr/bin/python3.12 --version` | Python 3.12.3 |
| 13:58:38Z-13:58:40Z | `/usr/bin/python3.12 -m venv W/venv`; `W/venv/bin/python -I -c` with the interpreter probe of `T/reach/run.py` (line 264); `pip --version`; `pip list` | exit 0; `pyvenv.cfg`: version 3.12.3, `include-system-site-packages = false`; `CPython 3.12.3`; pip 24.0, the only package |
| 13:58:44Z-13:58:47Z | `W/venv/bin/python -m pip install --disable-pip-version-check 'ecdsa!=0.15' 'rsa>=4.0,<5.0,!=4.4,!=4.1.1' 'pyasn1>=0.5.0' 'cryptography>=3.4.0' 'pycryptodome>=3.3.1,<4.0.0' pytest pytest-cov` (log `W/prep/pip-install.log`) | exit 0; 15 packages, all from wheels |
| 13:58:52Z | `W/venv/bin/python -m pip freeze --disable-pip-version-check` | 15 pins (`W/prep/pip-freeze.txt`) |
| 13:58:56Z | copy of the pins to `S/requirements.txt`; `sha256sum` | `a162224ecd4a9186f7a6d5ea8fb76743944ed35bffd6b6edc86e3b4841362f9c` |
| 13:59:00Z-13:59:10Z | reads of `W/venv/lib/python3.12/site-packages/_pytest/config/findpaths.py` (pytest 9.2.0, SHA-256 `048e1ee62ae92fa2b34f3d2ff55b19dca3104fc41c94061f9632615aed9ba1ea`) | line 80: `pytest.ini` files "are always the source of configuration"; lines 240-252: the configuration files "in precedence order", `pytest.ini` (line 248) before `setup.cfg` (line 252) |
| 13:59:22Z | `S/draft.json`: `test_directories_source` rewritten with that source | no value changed |
| 13:59:27Z | `git -C W/clone ls-files` for the names `test_*.py` and `*_test.py`; `S/draft.json` parsed | 18 files under `tests/`, 0 elsewhere; the draft parses |
| 13:59:27Z-13:59:28Z | `scope.py` as at 13:58:31Z | the same output; `S/subject.json` written again |
| 13:59:43Z | `cp -a` of `W/clone/jose`, `W/clone/tests` and `W/clone/pytest.ini` to `W/collect`; `diff -r`; `cmp` | identical; 37 files, as many as `git ls-files jose tests pytest.ini` |
| 13:59:48.366Z-13:59:48.675Z | the collection below, on `tests` | exit 0; 470 tests |
| 13:59:52Z | `grep` in `W/logs/collect-suite.log` | the counts per file and the warnings below |
| 14:00:03.439Z-14:00:03.671Z | the collection below, on the 5 test files of `subject.json` | exit 0; 256 tests |
| 14:00:17Z | `mv` of `W/logs`, `W/pypi` and `W/collect` to `W/prep`, `W/prep/pypi` and `W/prep/collect-copy` | `W/logs` is left to `run.py` (`T/reach/run.py`, line 143) |
| 14:02:01Z | `git -C W/clone status --porcelain --untracked-files=all --ignored`; `git -C W/clone rev-parse HEAD` | no output; `018b310ddb8b50dcfd09a0c152117835a21dd656` |
| 14:02:47.263Z-14:02:47.549Z | `T/reach/run.py define targets verify`, below | exit 0 |
| 14:02:57Z | `find T -newer S/subject.json`; `ls -d` of `T/work/python-jose`, `T/generated/python-jose`, `T/witnesses/python-jose` and `T/subjects/python-jose`; the status of the clone | no output; none of the 4 exists; no output |
| 14:05:23.816Z-14:05:23.838Z | the counting script, from a temporary folder; `sha256sum S/*` | `W/prep/counts.txt`; the digests above |
| between 14:07:48Z and 14:08:58Z | `grep` of `Requires-Python` in the `METADATA` of each package of `W/venv` | below, under "For the next stage" |
| 14:08:58.146Z-14:08:58.168Z | `python3 -I -B W/prep/count.py S`, the same script (SHA-256 `4756581e48eec4c65c29eae388cab5ad33fcb1ec67303b879bab38a815d3c646`) | `W/prep/counts.txt`, the same bytes as at 14:05:23Z |
| between 14:08:58Z and 14:11:39Z | `grep -rn` for `release_source` and `package_source` in `T/reach/*.py` | no match |
| 14:11:39Z | `find T -newer W/prep/pypi/python-jose.json` (a file of 13:52:42Z); `git status --porcelain -- experiments/target-reach` | no output; no output |
| 14:13:51Z | `git log -- experiments/target-reach-extension`; `git ls-files experiments/target-reach-extension` | no output: no file of `X` is committed |
| 14:20:59Z | `sha256sum S/*` | the 6 digests of the table above, unchanged |
| 14:21:43Z | `grep -n` in `W/clone`: `python_requires` and the classifiers of Python in `setup.cfg`, `envlist` and `py3` in `tox.ini`, `python-version` in `.github/workflows/ci.yml` | `>=3.9` (line 35) and 3.9 to 3.13 (lines 24-28); `py{39,310,311,312,313,py3}` (line 4) and 3.9 to 3.13 (lines 10-14); 3.9 to 3.13 and `pypy3.9` (line 18) |
| 14:22:11Z | `python3 -I` reading `requires_python` and the classifiers in `W/prep/pypi/python-jose.json`; `grep` of `Requires-Python` in the `METADATA` of `W/venv` | `>=3.9`, and 3.9 to 3.13; the requirements given under "For the next stage" |
| 14:22:48Z | `git --no-optional-locks grep -n -I` in `W/clone` for `3\.14`, `py314` or `3_14` | no match (exit 1) |
| 14:23:39Z | `grep -rn -I` in `W/clone/tests` for `urlopen`, `import requests`, `http.client`, `socket` and `urllib`, then for `open(`, `tmp_path`, `tmpdir`, `mkstemp` and `NamedTemporaryFile`; `head` of `W/venv/lib/python3.12/site-packages/ecdsa/_version.py` | no line; no line; a file generated by versioneer 0.21 that returns a fixed JSON string, version 0.19.2, and contains no `git` |
| 14:23:57Z | the same `git grep` with `-F` and the 3 patterns `3.14`, `py314` and `3_14`; as a control, `3.13` and `py313`; status and `HEAD` of the clone | no match (exit 1); 7 lines, among them `setup.cfg`, line 28, and `.github/workflows/ci.yml`, line 18; no output, and `018b310ddb8b50dcfd09a0c152117835a21dd656` |

## Collection

The 2 calls ran in `W/prep/collect-copy` (`W/collect` at the time), the copy of 13:59:43Z, so that
the clone stayed clean. They use the variables and the options of the pytest calls of
`T/reach/run.py` (`Context.env`, lines 155-165; the offline module on `PYTHONPATH`, lines 167-175;
`pytest_command`, lines 333-339; `whole_run`, lines 548-550), with `--collect-only` and without the
options of reporting:

    cd W/collect
    env -i PATH=W/venv/bin:/usr/bin:/bin HOME=<home> LANG=C.UTF-8 LC_ALL=C.UTF-8 \
      PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=T/guard OFFLINE_OUT=<file> \
      W/venv/bin/python -m pytest --collect-only -q -p no:cacheprovider -p reach_offline \
      --rootdir=. --continue-on-collection-errors <paths>

| Paths | Time | Exit | Collected | Collection errors | Warnings | Refused connections |
|---|---|---|---|---|---|---|
| `tests`, the paths of the suite run `compatibility` | 13:59:48.366Z-13:59:48.675Z | 0 | 470 tests, 18 files | 0 | 5 | 0 |
| the 5 files of `tests` in `subject.json`, the paths of the steps `suite`, `baseline` and `deletions` | 14:00:03.439Z-14:00:03.671Z | 0 | 256 tests | 0 | 4 | 0 |

Sources: `W/prep/collect-suite.log` (line 510; warnings, lines 472-509),
`W/prep/collect-recorder-files.log` (line 289; warnings, lines 258-288), and `"attempts": 0` in
`W/prep/collect-suite.offline.json` and `W/prep/collect-recorder-files.offline.json`. No
`__pycache__` and no `.pytest_cache` was written in the copy (`find`, after each call).

The warnings are all `PytestRemovedIn10Warning: Passing a non-Collection iterable to parametrize is
deprecated` (pytest 9.2.0, `_pytest/python.py`, line 144), for
`tests/algorithms/test_EC.py::TestECAlgorithm::test_key_too_short` (a generator),
`tests/algorithms/test_RSA_compat.py::TestBackendRsaCompatibility::test_key_wrap_parity` and
`tests/test_jwe.py::TestEncrypt::test_encrypt_decrypt_rsa_kw`, `::test_encrypt_decrypt_aes_kw` and
`::test_encrypt_decrypt_dir_kw` (filter objects). The second call lacks the one of
`test_RSA_compat.py`, which is not a test file of the subject.

| Test file | Tests collected | Blocks | Included | Included, class-only |
|---|---|---|---|---|
| `tests/algorithms/test_AES.py` | 6 | | | |
| `tests/algorithms/test_AES_compat.py` | 9 | 2 | 2 | 2 |
| `tests/algorithms/test_EC.py` | 18 | 7 | 1 | 1 |
| `tests/algorithms/test_EC_compat.py` | 20 | | | |
| `tests/algorithms/test_HMAC.py` | 3 | | | |
| `tests/algorithms/test_HMAC_compat.py` | 12 | | | |
| `tests/algorithms/test_RSA.py` | 21 | | | |
| `tests/algorithms/test_RSA_compat.py` | 120 | | | |
| `tests/algorithms/test_base.py` | 6 | | | |
| `tests/rfc/test_rfc7520.py` | 3 | | | |
| `tests/test_asn1.py` | 4 | | | |
| `tests/test_backends.py` | 4 | | | |
| `tests/test_firebase.py` | 3 | | | |
| `tests/test_jwe.py` | 125 | 6 | 4 | 2 |
| `tests/test_jwk.py` | 10 | | | |
| `tests/test_jws.py` | 43 | 17 | 15 | 15 |
| `tests/test_jwt.py` | 61 | 26 | 22 | 20 |
| `tests/test_utils.py` | 2 | | | |

The tests come from the node ids of `W/prep/collect-suite.log` (`grep`, 13:59:52Z), the blocks from
`blocks.json`; the blocks of the 13 files without an included block are counted only in
`scope_counts` (91 blocks in the 18 files).

## define, targets, verify

    cd W
    PYTHONHASHSEED=0 TZ=UTC /usr/bin/python3 -I -B T/reach/run.py define targets verify \
      --subject S/subject.json --clone W/clone --python W/venv/bin/python \
      --work W --defs S --out X/screened/generated/python-jose

14:02:47.263Z-14:02:47.549Z, exit 0 (`W/prep/run-define-targets-verify.log`):

    14:02:47 == define
    14:02:47 define: 99 checks (99 in subject files, 55 reachable); 58 blocks in the 5 test files of the subject, 44 included in 5 files; the test directories hold 91 blocks in 18 test files
    14:02:47 == targets
    14:02:47 targets: rule reach-target-rule/2; {"assert+name": 1, "assert-literal": 2, "name": 17, "none: no name token matches": 5, "none: tie": 19}
    14:02:47 == verify
    14:02:47 verify: commit 018b310ddb8b, 15 subject files and 5 test files match, CPython 3.12.3

- `PYTHONHASHSEED=0` and `python3 -I -B` are those of `T/README.md` (lines 125-128). `TZ=UTC` sets
  only the clock of the printed lines (`T/reach/run.py`, line 117).
- `--work W` replaces the default `T/work/python-jose`, and `--defs S` names the folder of
  `subject.json`, which is also the default (`T/reach/run.py`, lines 125-126); `checks.json`,
  `blocks.json` and `targets.json` are written there (lines 147-153 and 204). `--out` is read only by
  `pack` (line 726) and created nothing. `W/local.json` holds `clone` and `python` and nothing else
  (lines 128-136).
- `verify` (lines 208-261) found the clone at the commit, its copied paths without a changed,
  untracked or ignored file, the SHA-256 digests of `checks.json` and `blocks.json` in the 15 subject
  files and the 5 test files, CPython 3.12.3, exactly the packages of `requirements.txt` besides
  `pip`, no distribution `python-jose` and no importable module `jose` from `/`.
- In `T`, `targets` writes the `targets.json` of the 4 held-out libraries for the first time after
  the protocol commit (`T/README.md`, lines 143-145; `T/PROTOCOL.md`, section 6, item 2). This
  `targets.json` was written at 14:02:47Z, when no file of `X` was committed (14:13:51Z).

## Checks

| Subject file | Checks | Reachable |
|---|---|---|
| `jose/backends/cryptography_backend.py` | 28 | 5 |
| `jose/backends/ecdsa_backend.py` | 6 | 0 |
| `jose/backends/native.py` | 4 | 0 |
| `jose/backends/rsa_backend.py` | 7 | 1 |
| `jose/jwe.py` | 18 | 16 |
| `jose/jwk.py` | 1 | 1 |
| `jose/jws.py` | 13 | 13 |
| `jose/jwt.py` | 22 | 19 |

The other 7 of the 15 subject files hold no check. By class (checks, reachable): `JWKError` 39, 2;
`JWEError` 16, 12; `JWSError` 12, 12; `JWTClaimsError` 12, 12; `JWEParseError` 9, 9; `JWTError` 9, 6;
`JWSSignatureError` 1, 1; `ExpiredSignatureError` 1, 1. `checks.json` lists 136 functions, 86 of
them reachable. Source: `checks.json`, by `W/prep/count.py`.

## Blocks and targets

The 44 included blocks are all `pytest.raises` items of `with` statements. They call `decode` (23),
`verify` (15) or `decrypt` (6) and expect `JWTError` (22), `JWSError` (15), `JWEError` (4),
`JWEParseError` (2) or `JWKError` (1). 4 assert more than the class: 2 with a pattern and 2 with an
assertion after the block. Of the 14 blocks that are not included, `blocks.json` gives the reason
"no entry-point call" for 13 and "no entry-point call; expects ?ExceptionType" for 1.

20 blocks have a target, 16 distinct checks, all reachable (`targets.json`, `checks.json`):

| Block | Target | Basis |
|---|---|---|
| `tests/algorithms/test_EC.py::test_incorrect_public_key_hmac_signing#0` | `jwk.construct#1` | `name` |
| `tests/test_jwe.py::TestDecrypt.test_non_json_header_is_parse_error#0` | `jwe._jwe_compact_deserialize#4` | `name` |
| `tests/test_jwe.py::TestEncrypt.test_jwe_zip_with_excessive_data#0` | `jwe._decompress#1` | `assert-literal` |
| `tests/test_jws.py::TestJWS.test_invalid_algorithm#0` | `jws._verify_signature#5` | `name` |
| `tests/test_jws.py::TestJWS.test_not_enough_segments#0` | `jws._load#1` | `name` |
| `tests/test_jws.py::TestJWS.test_header_invalid_padding#0` | `jws._load#2` | `name` |
| `tests/test_jws.py::TestJWS.test_header_not_json#0` | `jws._load#4` | `name` |
| `tests/test_jws.py::TestJWS.test_claims_invalid_padding#0` | `jws._sign_header_and_claims#1` | `name` |
| `tests/test_jws.py::TestHMAC.test_wrong_key#0` | `jws._verify_signature#3` | `name` |
| `tests/test_jws.py::TestRSA.test_wrong_key#0` | `jws._verify_signature#3` | `name` |
| `tests/test_jws.py::TestLoad.test_header_not_mapping#0` | `jws._load#4` | `name` |
| `tests/test_jwt.py::TestJWT.test_invalid_claims_json#0` | `jwt.decode#3` | `assert+name` |
| `tests/test_jwt.py::TestJWT.test_invalid_claims#0` | `jwt.decode#3` | `assert-literal` |
| `tests/test_jwt.py::TestJWT.test_iat_not_int#0` | `jwt._validate_iat#1` | `name` |
| `tests/test_jwt.py::TestJWT.test_aud_list_is_strings#0` | `jwt._validate_aud#1` | `name` |
| `tests/test_jwt.py::TestJWT.test_aud_not_string_or_list#0` | `jwt._validate_aud#1` | `name` |
| `tests/test_jwt.py::TestJWT.test_iss_invalid#0` | `jwt._validate_iss#1` | `name` |
| `tests/test_jwt.py::TestJWT.test_sub_invalid#0` | `jwt._validate_sub#2` | `name` |
| `tests/test_jwt.py::TestJWT.test_jti_invalid#0` | `jwt._validate_jti#1` | `name` |
| `tests/test_jwt.py::TestJWT.test_require#0` | `jwt._validate_claims#1` | `name` |

The screening gave other numbers by another count: 29 checks of `jose/jwt.py` and `jose/jws.py` and
37 blocks for `decode` and `verify`, 35 class-only (`T/selection/screening-results.json`, the record
at line 810, `n_checks`, `n_negative_blocks`, `n_blocks_class_only` and `how_counted`).

## For the next stage

- Every later step of `T/reach/run.py` needs `--work W` and `--defs S`, which `W/local.json` does
  not keep; `pack` needs `--out` (default `T/generated/python-jose`, line 726) and `witness` needs
  `--witnesses` (default `T/witnesses/python-jose`, line 145). `T/reach/analyse.py` takes `--work`,
  `--defs` and `--out`, whose defaults are under `T` (lines 839-848).
- The steps `suite`, `baseline` and `deletions` run pytest on the 5 test files of `subject.json`
  (`T/reach/run.py`, lines 333-345, 360, 423 and 481); `whole-baseline` and `whole-deletions` run
  the suite run `compatibility` on `tests` (`whole_run`, lines 526-550; lines 581 and 626).
- `requirements.txt` holds pins that need a Python later than 3.9: `cffi` 2.1.1, `iniconfig` 2.3.1,
  `pluggy` 1.7.0 and `pytest` 9.2.0 need 3.10 or later, `coverage` 7.17.3 and `pycparser` 3.12 need
  3.11 or later (`Requires-Python` in their `METADATA` in `W/venv`, read between 14:07:48Z and
  14:08:58Z and again at 14:22:11Z). The CPython 3.9 to 3.14 sweep needs other pins for 3.9 and
  3.10.
- The release asks for Python 3.9 or later (`python_requires`, `setup.cfg`, line 35;
  `requires_python` in `W/prep/pypi/python-jose.json`) and names 3.9 to 3.13: in its classifiers
  (`setup.cfg`, lines 24-28, and the same in the PyPI file), in `tox.ini` (lines 4 and 10-14) and in
  the matrix of `.github/workflows/ci.yml` (line 18). No tracked file of the release contains
  `3.14`, `py314` or `3_14` (`git grep`, 14:22:48Z and 14:23:57Z). Whether 3.14.6 belongs to the
  sweep therefore depends on which of these declarations it reads.
- The environment holds `ecdsa` 0.19.2 and `pycryptodome` 3.24.1 (`requirements.txt`), 2 of the
  libraries of `screened/` (`T/SELECTION.md`, lines 303 and 298), the second at another version
  than the 4.4.0 of the screening. `ecdsa` is installed from its wheel, whose `ecdsa/_version.py`
  returns a fixed version string and contains no `git` (14:23:39Z). The 99 checks are all in the
  subject files of `python-jose` (`checks.json`: each of role `subject`).
- The test files name no network module and open no file (`grep` in `W/clone/tests`, 14:23:39Z).
- The 5 parametrizations named under "Collection" depend on a support of pytest that the name of the
  warning, `PytestRemovedIn10Warning`, gives as removed in pytest 10.
