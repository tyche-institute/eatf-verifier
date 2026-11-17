# Preparation of supabase-auth 2.34.1

This file records how the definitions in this folder were made for the part
`screened/`, before the protocol commit, with the toolkit of
`experiments/target-reach` used unchanged: every command run on the library,
its time, and what it gave. Every count below is taken from the files that
the toolkit wrote.

Abbreviations: T = `experiments/target-reach`, X =
`experiments/target-reach-extension`, S = `X/screened/subjects/supabase-auth`
(this folder), W = `X/work/supabase-auth` (clone, environment, downloads and
logs; `work/` is not tracked). Times are UTC on 2026-11-17, as printed by
`date -u` in the same command line; a range is given where a command printed
no time of its own.

## Result

The library was defined, the tests of its suite run were collected without an
error, and `verify` accepted the clone and the environment. No included block
has a target: all 16 end in a tie (section "Checks, blocks and targets").

| Count | Value | Source |
|---|---|---|
| checks | 64, all in subject files | `S/checks.json`, list `checks` (`role` "subject" in all 64); `W/logs/run-define-targets-verify.log`, line 2 |
| reachable checks | 12 | `S/checks.json`, field `reachable`; log line 2 |
| blocks in the 8 test files of the subject | 48 | `S/blocks.json`, `counts.blocks`; log line 2 |
| blocks in the test directory `tests` | 81, in 40 test files | `S/subject.json`, `scope_counts`; log line 2 |
| entry-point blocks | 16 | `S/blocks.json`, `counts.entry_point_blocks` |
| included blocks | 16, in 8 files | `S/blocks.json`, `counts.included`; log line 2 |
| included blocks that assert the class only | 4 | `S/blocks.json`, fields `match`, `match_unparsed`, `post` and `post_unparsed`, read with the rule of `T/reach/analyse.py`, lines 153-156 |
| targets in the assertion tier | 0 | `S/targets.json`, `counts` = `{"none: tie": 16}`; log line 4 |
| targets in the name tier | 0 | same |
| included blocks without a target | 16, reason "tie" | same; `rule_version` "reach-target-rule/2" |
| tests collected (suite run `all`, path `tests`) | 548, in 40 files; no collection error | `W/logs/collect.log`, last line "548 tests collected in 0.44s"; `W/logs/collect-per-file.txt` |

## Commands run on the library

Relative paths in the commands are relative to W.

| # | Time (UTC) | Command | What it gave |
|---|---|---|---|
| 1 | 13:52:02Z to 13:52:03Z | `curl -sS -o project.json https://pypi.org/pypi/supabase-auth/json` and `curl -sS -o release.json https://pypi.org/pypi/supabase-auth/2.34.1/json`, kept as `W/logs/pypi-supabase-auth-json-2026-11-17T135202Z.json` (SHA-256 d61bd6782849721ffb371bbbb4d94c2b90a5ccd49cea01d35f7de1732822dee3) and `W/logs/pypi-supabase-auth-2.34.1-json-2026-11-17T135203Z.json` (SHA-256 612f31b32adf4543705d16642812f38621441aea086a85a4874c021b663aa97f) | HTTP 200 for both. `info.version` 2.34.1; 62 versions, of which 3.0.0a1 (first file 2026-04-09T11:58:52Z) is the only pre-release; the 2 files of 2.34.1 (wheel 2026-11-06T15:23:01Z, sdist 2026-11-06T15:23:08Z, neither yanked) are the last upload of the project; `requires_python` ">=3.11"; `project_urls`: repository https://github.com/supabase/supabase-py, homepage https://github.com/supabase/supabase-py/tree/main/src/auth |
| 2 | 13:52:19Z | `git ls-remote --tags https://github.com/supabase/supabase-py` | `refs/tags/v2.34.1` = 416bffd0d95662912b307a13f5956b91b61d0c74 (`refs/tags/v2.34.0` = 5c3f2ed56258cd00d2081e2f5c263a5e09a33869) |
| 3 | 13:52:39Z to 13:52:40Z | `git clone --quiet https://github.com/supabase/supabase-py clone` | the clone `W/clone` |
| 4 | 13:52:40Z to 13:52:41Z | `git -C clone checkout --quiet 416bffd0d95662912b307a13f5956b91b61d0c74`; `git -C clone rev-parse HEAD`; `git -C clone describe --tags --exact-match HEAD`; `git -C clone tag --points-at HEAD`; `git -C clone log -1 --format='%H %cI %s'` | HEAD 416bffd0d95662912b307a13f5956b91b61d0c74, tag v2.34.1, commit time 2026-11-06T16:18:48+01:00, subject "chore(v2): release 2.34.1 (#1995)" |
| 5 | 13:52:41Z to 13:56:51Z | Reading only: `git status --short`, `ls`, `find`, `cat -n`, `sed -n` and `grep -n` on files of `W/clone` (the files cited in `S/draft.json`); `ss -ltn` | `git status --short` printed nothing; `ss -ltn`: no listener on the ports 9996 to 9999 of the test servers (`src/auth/tests/_async/clients.py`, lines 95-98) |
| 6 | 13:56:51Z | In `W/dist`: `curl -sS -o <file> <url>` for each of the 2 files of 2.34.1 listed in the release JSON (`W/dist/urls.txt`), each followed by `sha256sum -c` against the SHA-256 of the release JSON | `supabase_auth-2.34.1-py3-none-any.whl: OK` (45aa3334335926a8940beb89a9438386a9af0561d7315797e46c47b50d0c9620); `supabase_auth-2.34.1.tar.gz: OK` (d4d7d89ef16f55d1562b6408a361c1982d5f9764c43a64d18222655ee58c3207) |
| 7 | 13:57:04Z | `python3 -I compare_release.py dist/supabase_auth-2.34.1-py3-none-any.whl dist/supabase_auth-2.34.1.tar.gz clone/src/auth/src/supabase_auth clone/src/auth` (the script compares the SHA-256 of every file of the 2 archives with the clone and writes nothing; it is kept as `W/compare_release.py`, copied there at 14:09:34Z, SHA-256 7c66b9ed92d35754d30e52639f9f41052559806b31a778c601bf6487dacfdf73) | Wheel: 24 files under `supabase_auth/`, all 24 identical to the clone, no file on 1 side only. Sdist: 27 files, 26 identical to `clone/src/auth`; `PKG-INFO` is not in the clone |
| 8 | 13:57:04Z to 13:58:13Z | Reading only: `grep -n` and `sed -n` on `clone/src/auth/src/supabase_auth/_async/gotrue_client.py` and `_sync/gotrue_client.py`. `S/draft.json` written (file time 13:58:02Z) | the lines of `get_claims` cited in `S/draft.json` |
| 9 | 13:58:13Z | In X: `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3.12 -I -B T/reach/scope.py --draft S/draft.json --clone W/clone/src/auth` (output `W/logs/scope.log`) | exit 0; "scope: 23 subject files, 8 test files"; `S/subject.json` written, `scope_counts`: 40 test files and 81 blocks in the test directory, 8 test files with an included block |
| 10 | 13:58:24Z to 13:58:26Z | `/usr/bin/python3.12 -I -c <script>` that writes, with `tomllib`, the `[project]` dependencies and the `[dependency-groups]` group `tests` of `clone/src/auth/pyproject.toml` to `W/declared-requirements.txt`; `/usr/bin/python3.12 -m venv venv`; `venv/bin/python -m pip --version`; `venv/bin/python -m pip list --format=freeze` | 11 requirements: 3 dependencies (lines 19-23) and 8 of the group `tests` (lines 34-44). The environment is CPython 3.12.3 with pip 24.0 and no other package |
| 11 | 13:58:29Z to 13:58:35Z | `venv/bin/python -m pip install --disable-pip-version-check -r declared-requirements.txt` (output `W/logs/pip-install.log`) | exit 0; 34 packages installed (last line of the log); supabase-auth is not among them |
| 12 | 13:58:39Z | `ls` and `cat` of `venv/lib/python3.12/site-packages/*.pth`; `venv/bin/python -m pip freeze --disable-pip-version-check > S/requirements.txt` | 2 `.pth` files (section "Environment"); exit 0; `S/requirements.txt` holds 34 pins, none of a supabase package |
| 13 | 13:58:57Z to 13:58:58Z | `cp -a src tests pyproject.toml W/collect/copy/` (from `clone/src/auth`), then in `W/collect/copy`: `env -i PATH=W/venv/bin:/usr/bin:/bin HOME=$HOME LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=T/guard:W/collect/copy/src OFFLINE_OUT=W/logs/collect.offline.json W/venv/bin/python -m pytest -q -p no:cacheprovider -p reach_offline --rootdir=. --continue-on-collection-errors --collect-only tests` (output `W/logs/collect.log`) | exit 0; "548 tests collected in 0.44s" (last line); no collection error; 1 warning (lines 1-4): `PytestDeprecationWarning` of `pytest_asyncio/plugin.py:306`, 'The configuration option "asyncio_default_fixture_loop_scope" is unset.'; `T/guard/reach_offline.py` counted 0 attempts to reach another machine (`W/logs/collect.offline.json`) |
| 14 | 13:59:02Z | `grep '::' logs/collect.log`, `cut -d: -f1`, `sort`, `uniq -c` into `W/logs/collect-per-file.txt` | 548 node ids in 40 files: 237 in `tests/_async`, 237 in `tests/_sync`, 74 in `tests` itself |
| 15 | 13:59:02Z to 13:59:20Z | `find W/collect -name __pycache__`; `git -C clone status --porcelain --untracked-files=all --ignored` | nothing found; 0 lines |
| 16 | 13:59:20Z | In X: `PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3.12 -I -B T/reach/run.py define targets verify --subject S/subject.json --clone W/clone/src/auth --python W/venv/bin/python --work W --defs S --out X/screened/generated/supabase-auth` (output `W/logs/run-define-targets-verify.log`, whose times are the local time of the machine, UTC+1, as `T/reach/run.py`, line 117, prints them) | exit 0. define: "64 checks (64 in subject files, 12 reachable); 48 blocks in the 8 test files of the subject, 16 included in 8 files; the test directories hold 81 blocks in 40 test files". targets: "rule reach-target-rule/2; {"none: tie": 16}". verify: "commit 416bffd0d956, 23 subject files and 8 test files match, CPython 3.12.3". Written: `S/checks.json`, `S/blocks.json`, `S/targets.json` and `W/local.json`. These 3 steps do not use `--out` (`T/reach/run.py`, lines 140 and 726); `X/screened/generated` was not created |
| 17 | 14:04:14Z | `find clone/src/auth/src/supabase_auth -type f` (counted by extension; also for `.pyx`, `.c`, `.so`, `.pyd`); `sed -n 57,59p clone/src/auth/pyproject.toml`; `ls venv/lib/python3.12/site-packages`; `ss -ltn` | 23 `.py` files and `py.typed`, no other file; the build system `uv_build`; no supabase entry in site-packages; no listener on the ports 9996 to 9999 |
| 18 | 14:04:14Z to 14:07:27Z | Reading only: `grep -n`, `awk` and `sed -n` on the 8 test files of the subject, `tests/_async/clients.py`, `_async/gotrue_client.py`, `_sync/gotrue_client.py`, `src/auth/Makefile` and `src/auth/scripts/run-unasync.py`; a `/usr/bin/python3.12 -I -B -c` script with `tomllib` that compares `S/requirements.txt` with `clone/uv.lock` | sections "Environment" and "Points for the runs" |
| 19 | 14:07:27Z | `sed -n 104,171p clone/src/auth/src/supabase_auth/_async/gotrue_client.py` (the constructor of the client); `venv/bin/python -m pip show --disable-pip-version-check pytest-depends future-fstrings coverage` | no call of `_request` or `initialize` in the constructor; section "Environment" |
| 20 | 14:09:34Z to 14:12:52Z | Reading only: `sed -n` of `tests/_async/clients.py` (lines 93-112) and of the lines of the clone cited in this file; `grep -n` in the 3 `_sync` test files with an included block and in `tests/_sync/clients.py`; `git -C clone status --porcelain --untracked-files=all --ignored` at 14:12:52Z | the cited lines as quoted; 0 lines |

T was not changed: at 14:03:13Z, `git status --short --ignored -- experiments/target-reach`
showed only the ignored folders `reach/__pycache__/`, `recompute/out/` and
`work/`, and between 14:03:13Z and 14:04:14Z `find T -newermt
2026-11-17T13:50:00Z` found no file.

## The 6 decisions

From `S/draft.json`, which gives the source of each:

1. Release: 2.34.1, tag `v2.34.1`, commit
   416bffd0d95662912b307a13f5956b91b61d0c74 (commands 1, 2 and 4;
   `src/auth/pyproject.toml`, line 3; `src/auth/src/supabase_auth/version.py`,
   line 1).
2. Package: `supabase_auth`, under `source_root` "src" of the repository
   directory `src/auth` (`repository_directory`), so `--clone` is
   `W/clone/src/auth`, as `T/subjects/google-auth/subject.json` does with
   `repository_directory` "packages/google-auth" (`src/auth/pyproject.toml`,
   line 2; command 7).
3. Entry points: `get_claims` (`sdk-compliance.yaml`, lines 83-87;
   `CHANGELOG.md`, lines 42 and 161; `src/auth/docs/source/api/client.rst`,
   lines 4-9).
4. Rejection base: `AuthError` (`src/auth/src/supabase_auth/errors.py`,
   line 93).
5. Test directories: `tests` (`src/auth/Makefile`, lines 9-10;
   `src/auth/pyproject.toml`, lines 54-55).
6. Suite runs: 1 run, `all`, with the path `tests` (`src/auth/Makefile`,
   lines 5 and 9-10; `Makefile`, lines 71-72; `.github/workflows/ci.yml`,
   lines 62 and 104-105).

Other settings: `copy` is `src`, `tests` and `pyproject.toml` (the pytest
options, `asyncio_mode = "auto"`, are in `src/auth/pyproject.toml`, lines
54-55); `pytest_args` is `-p no:cacheprovider`, as in
`T/subjects/{joserfc,google-auth,authlib,jwcrypto,oauthlib}/draft.json`;
`python` is 3.12.3.

The screening (`T/selection/screening-results.json`, lines 855-889) named 5
entry points (lines 865-871: `get_claims`, `helpers.decode_jwt`,
`helpers.validate_exp`, `SyncGoTrueClient._fetch_jwks`,
`helpers.parse_jwks`) and counted 7 checks and 19 negative blocks, 4 of them
class-only (lines 880-883), with the checks counted on `helpers.py` and
`_sync/gotrue_client.py` (line 887). The draft names `get_claims` alone, the
function that the sources of decision 3 name. The other 4 are called by it:
`decode_jwt`, `validate_exp` and `_fetch_jwks` at lines 1359, 1371 and 1379
of `_async/gotrue_client.py`, and `parse_jwks` by `_fetch_jwks` at line 1334.

## Compiled extensions

None is needed to import the package from the source tree. The package
directory holds 23 `.py` files and `py.typed` and no `.pyx`, `.c`, `.so` or
`.pyd` file (command 17); the wheel of PyPI is tagged `py3-none-any`
(command 6) and holds the same 24 files (command 7); the build backend is
`uv_build` (`src/auth/pyproject.toml`, lines 57-59). The collection (command
13) imported `supabase_auth` from `W/collect/copy/src` through `PYTHONPATH`,
with nothing built. Nothing was built in the clone. The packages of the
environment with compiled code, pydantic-core, cryptography and cffi, were
installed from binary wheels (`W/logs/pip-install.log`: e.g.
`pydantic_core-2.50.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`,
`cryptography-50.0.2-cp311-abi3-manylinux_2_34_x86_64.whl`).

## Environment

- `S/requirements.txt` holds 34 pins (`pip freeze`, which leaves `pip` out):
  the versions that pip resolved from the declared ranges at the time of
  command 11, not those of a lock file. `verify` found the installed packages
  equal to them (command 16).
- 15 of the 34 pins differ from `clone/uv.lock`, the lock file of the
  repository (command 18): annotated-types 0.8.0 (lock 0.7.0), coverage
  7.17.3 (7.10.7), Faker 40.54.0 (37.11.0), iniconfig 2.3.1 (2.1.0), networkx
  3.7 (3.5), packaging 26.3 (25.0), pluggy 1.7.0 (1.6.0), pycparser 3.12
  (2.23), pydantic 2.14.3 (2.14.2), pydantic_core 2.50.4 (2.50.2), PyOTP
  2.12.0 (2.9.0), pytest-asyncio 1.5.0 (1.4.1.post1), pytest-cov 7.1.0
  (6.3.0), pytest-mock 3.17.0 (3.15.1), typing-inspection 0.4.5 (0.4.4). The
  other 19 are equal.
- pytest-depends 1.0.1 requires colorama, future-fstrings and networkx
  ("Requires: colorama, future-fstrings, networkx, pytest", command 19).
- 2 `.pth` files run at every start of the interpreter (command 12):
  `a1_coverage.pth` calls `coverage.process_startup` only when
  `COVERAGE_PROCESS_START` or `COVERAGE_PROCESS_CONFIG` is set, and
  `aaaaa_future_fstrings.pth` imports `future_fstrings` and calls
  `future_fstrings.register()`.

## Checks, blocks and targets

**Checks** (`S/checks.json`): 64, in `supabase_auth/_async/gotrue_client.py`
(30), `supabase_auth/_sync/gotrue_client.py` (30) and
`supabase_auth/helpers.py` (4); by class AuthSessionMissingError 24,
AuthImplicitGrantRedirectError 16, AuthInvalidCredentialsError 10,
AuthInvalidJwtError 10, UserDoesntExist 4. `rejection_classes` holds 11
classes. `other_raises` holds 47 raise statements: 40 "not a rejection
class", 5 "bare raise", 2 "re-raise of a bound exception".

The 12 reachable checks, with the lines of their raise statements (field
`lines`) and the literal message (field `template_parts`):

| Check | Class | Lines | Message |
|---|---|---|---|
| `_async.gotrue_client.AsyncGoTrueClient._call_refresh_token#1` | AuthSessionMissingError | 1148, 1151 | none |
| `_async.gotrue_client.AsyncGoTrueClient._fetch_jwks#1` | AuthInvalidJwtError | 1342 | "No matching signing key found in JWKS" |
| `_async.gotrue_client.AsyncGoTrueClient._fetch_jwks#2` | AuthInvalidJwtError | 1346 | "JWT has no valid kid" |
| `_async.gotrue_client.AsyncGoTrueClient.get_claims#1` | AuthInvalidJwtError | 1388 | "Invalid JWT signature" |
| `_sync.gotrue_client.SyncGoTrueClient._call_refresh_token#1` | AuthSessionMissingError | 1144, 1147 | none |
| `_sync.gotrue_client.SyncGoTrueClient._fetch_jwks#1` | AuthInvalidJwtError | 1332 | "No matching signing key found in JWKS" |
| `_sync.gotrue_client.SyncGoTrueClient._fetch_jwks#2` | AuthInvalidJwtError | 1336 | "JWT has no valid kid" |
| `_sync.gotrue_client.SyncGoTrueClient.get_claims#1` | AuthInvalidJwtError | 1378 | "Invalid JWT signature" |
| `helpers.parse_jwks#1` | AuthInvalidJwtError | 92 | "JWKS is empty" |
| `helpers.decode_jwt#1` | AuthInvalidJwtError | 204, 211 | "Invalid JWT structure" |
| `helpers.validate_exp#1` | AuthInvalidJwtError | 269 | "JWT has no expiration time" |
| `helpers.validate_exp#2` | AuthInvalidJwtError | 273 | "JWT has expired" |

**Blocks** (`S/blocks.json`): 48 in the 8 test files of the subject
(`test_client_flows.py` 11, `test_gotrue.py` 7, `test_jwks_and_refresh.py` 4
and `test_get_claims.py` 2, in each of `tests/_async` and `tests/_sync`). 32
are not included (field `exclusion`): 26 "no entry-point call", 4 "no
entry-point call" and "expects ?raises", 2 "no entry-point call" and "expects
RuntimeError". The 16 included blocks all have the form `with`, expect
`AuthInvalidJwtError` and carry no `post`, `post_unparsed` or
`match_unparsed`; they are the same 8 tests in `tests/_async` and in
`tests/_sync`:

| Test (in `tests/_async/` and in `tests/_sync/`) | `match` |
|---|---|
| `test_client_flows.py::test_get_claims_rejects_expired_token` | "JWT has expired" |
| `test_client_flows.py::test_get_claims_rejects_token_without_expiry` | "no expiration time" |
| `test_get_claims.py::test_get_claims_raises_auth_error_for_malformed_header` | none (class only) |
| `test_get_claims.py::test_get_claims_raises_auth_error_for_undecodable_token` | none (class only) |
| `test_gotrue.py::test_get_claims_raises_when_exp_claim_is_missing` | "JWT has no expiration time" |
| `test_jwks_and_refresh.py::test_get_claims_rejects_unknown_signing_key` | "No matching signing key" |
| `test_jwks_and_refresh.py::test_get_claims_rejects_empty_jwks` | "JWKS is empty" |
| `test_jwks_and_refresh.py::test_get_claims_rejects_invalid_signature` | "Invalid JWT signature" |

**Targets** (`S/targets.json`, rule `reach-target-rule/2`): no included
block has a target, and all 16 end in "tie". In every block:

- `C_class` holds the 10 reachable checks of class `AuthInvalidJwtError`.
- No candidate is excluded and none is positive (`excluded` and `positive`
  are empty, `C_assert` equals `C_class`, `C_pos` is empty).
  `T/reach/targets.py` gives a message assertion the verdict "maybe" when
  the shape of the message is not known (lines 123-126), and the shape is
  not known when the class of the check or one of its ancestors defines
  `__init__` or `__str__` (lines 94-111). `AuthInvalidJwtError`,
  `CustomAuthError` and `AuthError` define `__init__` (`S/checks.json`,
  `classes`; `errors.py`, lines 252, 132 and 94).
- The name of the test then scores the 10 candidates (`pool` "C_assert").
  The highest score is shared by `_async.gotrue_client.AsyncGoTrueClient.get_claims#1`
  and `_sync.gotrue_client.SyncGoTrueClient.get_claims#1`, with the same
  tokens, which always include "claim" and "get" (3.218876 in 14 blocks,
  4.828314 in the 2 blocks of `test_get_claims_rejects_invalid_signature`),
  so `tied` holds both and there is no target (lines 262-268).

The 2 tied checks are the raise statements of `get_claims` in the 2 forms of
the client, `_async/gotrue_client.py` line 1388 and `_sync/gotrue_client.py`
line 1378. The `_sync` files are generated from the `_async` files by `make
build-sync` (`src/auth/Makefile`, lines 42-45; `src/auth/scripts/run-unasync.py`,
lines 5-17), which covers both `src/supabase_auth` and `tests`.

## Points for the runs

- No case of this library has a target. In `T/PROTOCOL.md`, section 2, Q1
  and E4 concern the cases with a target (lines 25-26 and 46), and an
  expectation with 0 units to decide on is "not applicable" (lines 57-58).
  E5 is stated only where at least 9 of every 10 included blocks are
  class-only (lines 51-52); here 4 of 16 are.
- The project's own test target first starts the test servers of
  `src/auth/infra/docker-compose.yml` (`src/auth/Makefile`, lines 9 and
  19-20); the toolkit starts none. The clients of `tests/_async/clients.py`
  use `http://localhost` on the ports 9996 to 9999 (lines 95-111); no
  listener was on those ports during command 5 and at 14:04:14Z (command 17).
  By reading the sources (no test was run), the 16 included blocks need no
  server: 14 use an `httpx.MockTransport` (`tests/_async/test_client_flows.py`,
  lines 93-96; `test_get_claims.py`, lines 11-15; `test_jwks_and_refresh.py`,
  lines 63-66; and the same in `tests/_sync`), and the 2 of
  `test_gotrue.py` raise in `validate_exp` (`_async/gotrue_client.py`, line
  1371; `_sync/gotrue_client.py`, line 1361) before `get_claims` makes a
  request (lines 1375 and 1379; `_sync` lines 1365 and 1369).
- `T/reach/run.py` writes to T unless told otherwise: `--work` defaults to
  `T/work/<name>` (line 126), `--witnesses` to `T/witnesses/<name>` (lines
  144-145), and `pack` writes to `T/generated/<name>` without `--out` (line
  726); `T/reach/analyse.py` defaults `--work` and `--out` to T (lines
  847-848). `W/local.json` now holds the clone and the interpreter (written
  by `run.py`, lines 128-136).
- The warning of command 13 is printed by pytest-asyncio 1.5.0 because the
  pytest options of `src/auth/pyproject.toml` (lines 54-55) do not set
  `asyncio_default_fixture_loop_scope` (`W/logs/collect.log`, lines 1-4); the
  copy of every run carries the same options.
