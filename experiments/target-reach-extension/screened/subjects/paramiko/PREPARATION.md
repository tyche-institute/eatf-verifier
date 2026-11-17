# paramiko 5.1.0: preparation before the protocol commit

Part `screened/` of the extension. Paths: `T` is `experiments/target-reach`
(its toolkit `reach/` was used unchanged), `X` is
`experiments/target-reach-extension`, `W` is `X/work/paramiko`, which holds
the clone (`W/clone`), the environment (`W/env`), the copies used for
collection (`W/collect/`), the helper scripts (`W/scripts/`) and the log of
every command with its full output (`W/logs/commands.log`). `X/work/` is not
deposited. Paths of the library are relative to the root of the clone.
Times are UTC, 17 November 2026.

## Result

1. **Defined; the static steps pass.** The 6 decisions of `T/PROTOCOL.md`,
   section 3 (lines 82-93), are in `draft.json`. `reach/scope.py` wrote
   `subject.json`, and `reach/run.py define targets verify` wrote
   `checks.json`, `blocks.json` and `targets.json` and verified the clone and
   the environment (14:12:39Z): 107 checks, 61 of them reachable; 5 included
   blocks in 2 test files; a target for 3 of the 5.
2. **The tests cannot be imported from a copy without the installed
   distribution, so none of them can be collected.** The tests import the
   library from the copy, and the environment does not hold the library
   (`T/PROTOCOL.md` lines 276-278; `T/README.md` lines 116-120); `verify`
   refuses an environment that holds it (`T/reach/run.py` lines 244-258).
   Without the distribution, `import paramiko` fails: `paramiko/__init__.py`
   line 21 is `__version__ = metadata.version("paramiko")`, which raises
   `importlib.metadata.PackageNotFoundError` when no metadata of the
   distribution `paramiko` is installed. `tests/conftest.py` line 12 imports
   `paramiko`, so pytest stops while it loads that file, with exit code 4,
   before it collects any test. This holds for the suite run of decision 6
   (`tests`: 14:10:52Z, and with the options of a whole-suite run at
   14:11:31Z and 14:14:35Z) and for the 2 test files of the recorder runs,
   `tests/test_client.py` and `tests/test_kex.py`, with the options of the
   toolkit's suite call (14:31:04Z). The output is quoted under "Collection".
3. **5 included blocks.** Criterion I4 of `T/SELECTION.md` (lines 62-66) asks
   for at least 10 negative-test blocks; the screening counted 10
   (`T/selection/screening-results.json` line 553), and `T/SELECTION.md`
   lines 233-237 state that the 7 candidates of this part were not counted
   again with the toolkit.

Nothing of the library, of its tests or of the toolkit was changed. Result 2
is the case that the paragraph "No replacement" of section 3 of
`X/PROTOCOL.md` names: a library that cannot be imported from a copy without
its installed distribution is reported as failed, and a `PREPARATION.md` that
records before the protocol commit that none of the test files of its
recorder runs can be collected from a copy is the record of that failure.

## Release, clone and package

| Fact | Value | Source |
|---|---|---|
| Release | 5.1.0, the latest version that is not a pre-release, and the version of the screening | https://pypi.org/pypi/paramiko/json, read 13:52:48Z (saved as `W/pypi/paramiko.json`, SHA-256 `e85fd7e9092fafd6c01737c1be2496048549f3a64a1cdd653160ebfe5fc4e946`): `info.version` 5.1.0; 153 versions, none a pre-release; the 8 versions `0.1-bulbasaur` to `0.9-ivysaur` are no PEP 440 versions. `T/selection/screening-results.json` line 514 (`version_examined`) |
| Upload | wheel 2026-10-18T02:38:49Z, sdist 2026-10-18T02:38:51Z, neither yanked; no file of any version uploaded later, so 5.1.0 was also the latest on 14 November 2026 | the same file, and https://pypi.org/pypi/paramiko/5.1.0/json, read 13:52:48Z (`W/pypi/paramiko-5.1.0.json`, SHA-256 `d605967cbc14adb4c9236ebda0046a14c537ca4b9f6ff8c1d6223db17179a530`) |
| Repository | https://github.com/paramiko/paramiko | `project_urls` `Source` of the PyPI JSON; `pyproject.toml` line 39 |
| Tag and commit | annotated tag `5.1.0`, tag object `f8d947066257b14732f98b5922e62abd02cb7c03`, commit `0e9ccb91e0f9a68f2587233d523ad7fe46e730fe`, "Cut 5.1.0", 2026-10-17T22:36:52-04:00 | `git ls-remote --tags`, 13:53:06Z; `git rev-parse`, `git cat-file -p 5.1.0` and `git log -1` in the clone, 13:53:17Z |
| Version at the commit | `version = "5.1.0"` | `pyproject.toml` line 4 |
| Clone | at the commit; `git status --porcelain --untracked-files=all --ignored` empty | 13:53:17Z, and again by `verify` at 14:12:39Z |
| Package | `paramiko`, at the root of the repository | `pyproject.toml` lines 50-51: `[tool.setuptools]` `packages = ["paramiko"]` |
| Release files and commit | the 42 files of `paramiko/` in the wheel `paramiko-5.1.0-py3-none-any.whl` are byte for byte the 42 files of `paramiko/` at the commit; the wheel's SHA-256 `d9fe6d67a9d0bbf3eb85b051d26ab850b678c02d060f32915b944e5ca6d0d9e1` is the digest that PyPI gives | download and comparison, 14:07:46Z |
| Compiled code | none, and nothing was built: of the 196 files of the commit, none is a C, C++, Cython, Rust, Fortran or Go source; the only build files are `pyproject.toml` and `MANIFEST.in`; `pyproject.toml` lines 45-51 build the package `paramiko` with setuptools; the wheel is tagged `py3-none-any` | `git ls-files`, 14:28:20Z |

## Decisions

`draft.json` gives each decision with its source. It was written at
14:10:10Z from the files named there, before `scope.py` and `define` ran, and
was not changed afterwards. Before the draft, the screening record of
paramiko was read, which names entry points and 10 blocks; no test was run.

1. Release: 5.1.0 at commit `0e9ccb91e0f9a68f2587233d523ad7fe46e730fe`
   (`release_source`).
2. Package: `paramiko` (`package_source`).
3. Entry points: `connect`, `missing_host_key`, `parse_next`,
   `read_message`, `start_client`, `start_server` (`entry_points_source`).
4. Rejection base: `SSHException` (`rejection_bases_source`).
5. Test directories: `tests`, `tests/agent.py`, `tests/auth.py`,
   `tests/pkey.py` (`test_directories_source`).
6. Suite runs: 1 run, `all`, on `tests` (`suite_runs_source`).

Settings that are no decisions: `copy` is `paramiko`, `tests` and
`pytest.ini` (`pytest.ini` holds the pytest configuration, lines 1-3, and
the repository has no `conftest.py` at its root); `pytest_args` is
`-p no:cacheprovider`, as in the drafts of `T/subjects/` (`pyjwt-package`
adds `-p no:randomly`); `python` 3.12.3; `distribution` paramiko;
`source_root` `.`.

## Environment

- Interpreter: `/usr/bin/python3.12 --version` gave Python 3.12.3
  (14:00:21Z); `/usr/bin/python3.12 -m venv W/env` ran from 14:00:21Z to
  14:00:23Z; in the environment, a probe gave CPython 3.12.3 and `pip list`
  gave pip 24.0 alone (14:00:23Z).
- Installed (14:00:29Z to 14:00:31Z): the 4 dependencies of
  `pyproject.toml` lines 11-16 (`bcrypt>=3.2`, `cryptography>=3.3`,
  `invoke>=2.0`, `pynacl>=1.5`) and the 3 packages of the dependency group
  `dev` (lines 57-80) that the tests import: `invoke>=2.2.1` (line 60;
  `tests/conftest.py` line 10, `tests/test_config.py` line 8),
  `pytest-relaxed>=2` (line 63; the plugin that `pytest.ini` relies on, and
  `tests/test_client.py` line 36) and `icecream>=2.1` (line 79;
  `tests/conftest.py` lines 8-9). pytest 9.2.0 came in as a dependency of
  pytest-relaxed (`pytest>=7`). The pip output names a wheel for each of
  the 17 packages; none was built.
- Left out, of the same group: `invocations` (imported by `tasks.py` only,
  lines 6-10), `pytest-xdist` ("for test dir watching and the inv guard
  task", lines 64-65), `flake8`, `black`, `codespell`, `coverage` (the
  runner of the task `coverage`, `tasks.py` line 66) and the documentation
  tools `alabaster`, `releases` and `watchdog` (lines 74-77). No file of
  `tests/` imports any of them: the modules outside the standard library
  that the `.py` files of `tests/` import are `cryptography`, `icecream`,
  `invoke`, `paramiko`, `pytest`, `pytest_relaxed` and `tests` (an `ast`
  listing, 14:28:02Z).
- `requirements.txt`: `pip freeze`, 14:00:37Z, 17 lines.
- `verify` (14:12:39Z) found the installed packages equal to
  `requirements.txt` and the distribution `paramiko` not installed.

## Commands run on the library

Each command was run through a wrapper that appends to `W/logs/commands.log`
the start and end time, the exit code, the working directory, the command
and its full output (`W/scripts/plog.sh` from 14:07:46Z on; before that, a
wrapper that wrote the same fields). The name and the address of the tagger
were removed from the logged tag object. The helper scripts ran from a
scratch folder outside the repository; `W/scripts/` holds byte-identical
copies, and the log writes that folder as `P` and the home directory as
`$HOME`. Besides these commands, the clone and the downloaded files were only
read (`cat`, `grep`, `sed`, `awk`, `git ls-files` and `ast` scripts),
between 13:53Z and 14:33Z.

| Start (UTC) | Command | What it gave |
|---|---|---|
| 13:52:48Z | `curl -sS -f` of https://pypi.org/pypi/paramiko/json and https://pypi.org/pypi/paramiko/5.1.0/json into `W/pypi/` | exit 0, the 2 files above |
| 13:53:06Z | `git ls-remote --tags https://github.com/paramiko/paramiko` | `refs/tags/5.1.0` `f8d947066257b14732f98b5922e62abd02cb7c03`, peeled `0e9ccb91e0f9a68f2587233d523ad7fe46e730fe` |
| 13:53:15Z | `git clone https://github.com/paramiko/paramiko W/clone` | exit 0 at 13:53:17Z |
| 13:53:17Z | `git -C W/clone checkout 0e9ccb91e0f9a68f2587233d523ad7fe46e730fe`; `rev-parse HEAD 5.1.0^{commit} 5.1.0`; `cat-file -p 5.1.0`; `log -1 --format='%H %cI %s'`; `status --porcelain --untracked-files=all --ignored` | HEAD is the commit of the tag; "Cut 5.1.0"; status empty |
| 14:00:21Z | `/usr/bin/python3.12 --version`; `/usr/bin/python3.12 -m venv W/env` | Python 3.12.3; exit 0 at 14:00:23Z |
| 14:00:23Z | `W/env/bin/python -I -c` (implementation and version); `-m pip --version`; `-m pip list` | CPython 3.12.3; pip 24.0; pip alone |
| 14:00:29Z | `W/env/bin/python -m pip install --no-input --disable-pip-version-check "bcrypt>=3.2" "cryptography>=3.3" "invoke>=2.0" "pynacl>=1.5" "invoke>=2.2.1" "pytest-relaxed>=2" "icecream>=2.1"` | 17 packages from wheels, exit 0 at 14:00:31Z |
| 14:00:37Z | `W/env/bin/python -m pip freeze` | `requirements.txt` |
| 14:07:46Z | `curl -sS -fL` of the wheel `paramiko-5.1.0-py3-none-any.whl` (its URL in the PyPI JSON) into `W/pypi/`; `python3 -I cmp_wheel.py` of the wheel and `W/clone` | SHA-256 as PyPI gives it; 42 of 42 files identical to the commit, none missing on either side |
| 14:10:24Z | `python3 -I -B T/reach/scope.py --draft X/screened/subjects/paramiko/draft.json --clone W/clone` | "scope: 42 subject files, 2 test files"; `subject.json` |
| 14:10:47Z | `python3 -I make_copy.py` into `W/collect/copy-1`: the `copy` paths of `subject.json` without `__pycache__`, `*.pyc` and `.pytest_cache`, as `make_copy` of `T/reach/run.py` (lines 310-321) copies them | 140 files |
| 14:10:52Z | in `W/collect/copy-1`: `env -i PATH=W/env/bin:/usr/bin:/bin HOME=$HOME LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 W/env/bin/python -m pytest --collect-only -q -p no:cacheprovider --rootdir=. tests` | exit 4; "ImportError while loading conftest"; no test collected |
| 14:11:31Z | the same, with `PYTHONPATH=T/guard` and the options of a whole-suite run (`T/reach/run.py` lines 548-550): `-q -p no:cacheprovider -p reach_offline --rootdir=. --tb=no --continue-on-collection-errors --collect-only tests` | exit 4, the same error |
| 14:11:56Z | `python3 -I extract_distinfo.py` of the wheel into `W/collect/distinfo-only` | the 5 files of `paramiko-5.1.0.dist-info` (`METADATA`, `RECORD`, `WHEEL`, `top_level.txt`, `licenses/LICENSE`); no module |
| 14:12:04Z | `make_copy.py` into `W/collect/copy-2`; there, the command of 14:10:52Z with `PYTHONPATH=W/collect/distinfo-only` added (a diagnostic outside the protocol, under "Collection") | exit 0 at 14:12:05Z; 565 tests collected, 3 warnings |
| 14:12:39Z | `PYTHONHASHSEED=0 python3 -I -B T/reach/run.py define targets verify --subject X/screened/subjects/paramiko/subject.json --clone W/clone --python W/env/bin/python --work W --defs X/screened/subjects/paramiko --out X/screened/generated/paramiko` | exit 0; the 3 lines quoted under "Counts"; `W/local.json` |
| 14:13:03Z | `python3 -I -B all_blocks.py`: the blocks of all 19 test files, by `enumerate_blocks` of `T/reach/blocks.py`, as `scope.py` lists them | 74 blocks, 7 call an entry point, 5 included |
| about 14:14Z | `python3 -I -B who_refers.py` (the functions that refer to a name, by `referenced_names` of `T/reach/checks.py`) | not in the log; the logged runs of 14:27:11Z and 14:32:46Z give the listings cited here |
| 14:14:35Z | in `W/collect/copy-1`, the command of 14:11:31Z with `OFFLINE_OUT=W/collect/offline-check.json` and `--junitxml=W/collect/junit-check.xml` | exit 4, the same error; neither file was written |
| 14:16:57Z | `python3 -I counts.py X/screened/subjects/paramiko` (reads the files of the toolkit) | the counts below |
| 14:27:11Z | `python3 -I -B who_refers.py T X/screened/subjects/paramiko/subject.json W/clone run _negotiate_keys start` | under "Reachability" |
| 14:28:02Z | `python3 -I -B imports.py W/clone/tests` | the 7 modules under "Environment" |
| 14:28:20Z | `python3 -I -B compiled.py W/clone` (`git ls-files` and the suffixes of the files) | 196 files; no native source; build files `MANIFEST.in` and `pyproject.toml` |
| 14:31:04Z | `make_copy.py` into `W/collect/copy-3`; there, the options of the toolkit's suite call (`T/reach/run.py` lines 338-339 and 345) on the 2 test files of `subject.json`: `env -i PATH=W/env/bin:/usr/bin:/bin HOME=$HOME LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=T/guard OFFLINE_OUT=W/collect/recorder-files.offline.json OUTCOMES_OUT=W/collect/recorder-files.outcomes.json W/env/bin/python -m pytest -q -p no:cacheprovider -p reach_offline --rootdir=. --tb=native -rfE --continue-on-collection-errors --collect-only tests/test_client.py tests/test_kex.py` | 140 files; exit 4 at 14:31:05Z, the same error; neither output file was written |
| 14:32:46Z | `python3 -I -B who_refers.py T X/screened/subjects/paramiko/subject.json W/clone _parse_kex_init _handler_table` | under "Reachability" |

## Counts

The 3 result lines that `reach/run.py` printed at 14:12:39Z (each line
begins with the clock time of the machine's zone, UTC+1, left out here):

    define: 107 checks (107 in subject files, 61 reachable); 10 blocks in the 2 test files of the subject, 5 included in 2 files; the test directories hold 74 blocks in 19 test files
    targets: rule reach-target-rule/2; {"class": 1, "name": 2, "none: no name token matches": 1, "none: tie": 1}
    verify: commit 0e9ccb91e0f9, 42 subject files and 2 test files match, CPython 3.12.3

| Count | Value | File and key |
|---|---|---|
| Subject files | 42 | `subject.json`, `subject_files` |
| Test files in the test directories | 19 | `subject.json`, `scope_counts.test_files_in_test_directories` |
| Blocks in the test directories | 74 | `subject.json`, `scope_counts.blocks_in_test_directories` |
| Test files with an included block | 2: `tests/test_client.py`, `tests/test_kex.py` | `subject.json`, `scope_counts.test_files_with_an_included_block` and `tests` |
| Checks | 107, all in subject files (role `subject`), in 20 files | `checks.json`, `checks` |
| Reachable checks | 61 | `checks.json`, `checks[].reachable` |
| Functions | 857, 456 of them reachable | `checks.json`, `functions` |
| Blocks in the 2 test files | 10 | `blocks.json`, `counts.blocks` |
| Blocks that call an entry point | 6 | `blocks.json`, `counts.entry_point_blocks` |
| Included blocks | 5: 3 in `tests/test_client.py` (lines 500, 568 and 584; `connect`; the `unittest` form), 2 in `tests/test_kex.py` (lines 565 and 587; `parse_next`; the `pytest` form); all 5 class-only | `blocks.json`, `counts.included`, `blocks[]` |
| Targets, assertion tier | 1: `SSHClientTest._client_host_key_bad#0` to `client.SSHClient.connect#1` (basis `class`: the only reachable check of `BadHostKeyException`) | `targets.json`, `blocks[]` (`tier`, `basis`, `target`, `C_class`) and `counts` |
| Targets, name tier | 2: `MLKEM768X25519Test.test_rejects_wrong_init_length#0` to `kex_mlkem.KexMLKEM768X25519._parse_hybrid_init#1`; `test_rejects_wrong_reply_length#0` to `kex_mlkem.KexMLKEM768X25519._parse_hybrid_reply#1` | the same |
| No target | 2: `SSHClientTest.test_banner_timeout#0`, a tie of 3 checks on the token `timeout` (`auth_handler.AuthHandler.wait_for_response#1`, `transport.Transport._send_user_message#1`, `transport.Transport.open_channel#2`); `SSHClientTest.test_reject_policy#0`, whose only name token, `policy`, matches no check | `targets.json`, `blocks[]` (`reason`, `scores`, `name_tokens`) |
| Tests collected | 0: pytest stops while it loads `tests/conftest.py` | the output of the commands of 14:10:52Z and 14:31:04Z (not a file of the toolkit) |

Over all 19 test files (14:13:03Z): 74 blocks, 7 call an entry point, 5
included. The 2 blocks that call an entry point and are not included expect
a class that is no rejection class: `tests/test_client.py` line 458
(`SocksToBeYou`, a subclass of `socket.error` that the test defines at
line 452) and `tests/test_transport.py` line 868 (`EOFError`).

## Collection

The output of the commands of 14:10:52Z, 14:11:31Z, 14:14:35Z and 14:31:04Z,
the same each time (the path of the copy written out in the log):

    ImportError while loading conftest '<copy>/tests/conftest.py'.
    tests/conftest.py:12: in <module>
        from paramiko import (
    paramiko/__init__.py:21: in <module>
        __version__ = metadata.version("paramiko")
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    E   importlib.metadata.PackageNotFoundError: No package metadata was found for paramiko

What it means for the steps after the protocol commit, from the toolkit's
code: `run.py baseline` (line 417) begins with `suite` (lines 379-397), the
run without the recorder, which needs the file named by `OUTCOMES_OUT`;
`guard/reach_offline.py` writes it, with the file named by `OFFLINE_OUT`,
when the session ends (lines 119-131). pytest stops before the session
begins, and the command of 14:31:04Z shows that neither file is written.
`baseline` would therefore stop with "suite: the run without the recorder
did not reach its end" (line 397), and `whole-baseline` with
"whole-baseline: a pytest call ended without its result file" (line 585;
the command of 14:14:35Z shows that the JUnit XML file is not written). Any
pytest call of these tests on any interpreter meets the same import when its
environment does not hold the distribution. `tests/test_util.py` line 101
asserts `paramiko.__version__ == metadata.version("paramiko")`.

**Diagnostic, outside the protocol; no result rests on it.** With only the
metadata of the wheel on the path (`W/collect/distinfo-only`, 5 files and no
module, so `paramiko` is still imported from the copy), the same command in
a fresh copy collected 565 tests and exited with 0 (14:12:04Z): the metadata
is all that the import lacks. Per file: `tests/agent.py` 34, `auth.py` 43,
`pkey.py` 54, `test_buffered_pipe.py` 4, `test_channelfile.py` 11,
`test_client.py` 36, `test_config.py` 120, `test_file.py` 15,
`test_hostkeys.py` 12, `test_kex.py` 16, `test_message.py` 5,
`test_packetizer.py` 3, `test_pkey.py` 40, `test_proxy.py` 11,
`test_sftp.py` 38, `test_sftp_big.py` 11, `test_ssh_exception.py` 9,
`test_transport.py` 97, `test_util.py` 6. The 3 warnings: a
`PytestRemovedIn10Warning` on the hook `pytest_configure` of
`pytest_relaxed/plugin.py` line 40 (old-style `trylast` mark); a
`PytestCollectionWarning` for the class `TestServer` of `tests/_util.py`
line 88, which has an `__init__`; a `PytestRemovedIn10Warning` on a
parametrization by an iterator in `tests/test_transport.py`,
`TestStrictKex::test_mode_agreement`. Such a path puts files on every
pytest call that are neither the copy nor the environment of
`requirements.txt`; it was not taken.

## Reachability

Reachability is a closure by name (`T/PROTOCOL.md` lines 208-212), and
section 8 states (lines 668-670) that "A check can be marked reachable that
no entry point runs, and the reverse." In this library, from `checks.json`
(`functions` and `checks`) and the listings of 14:27:11Z and 14:32:46Z:

- `start_client` and `start_server` start the thread of the transport with
  `self.start()` (`paramiko/transport.py` lines 694, 699, 763 and 768;
  `Transport` is a `threading.Thread`, line 154). No function of the package
  is named `start`, so the closure takes no step from there. `Transport.run`
  (line 2019) is reachable all the same: the reachable
  `SSHConfig._does_match` (`paramiko/config.py` line 351) calls `invoke.run`
  (line 398), and the name `run` stands for `Transport.run` and
  `AgentProxyThread.run` (`paramiko/agent.py`), both reachable.
- `Transport._negotiate_keys` (line 2204), `Transport._parse_kex_init`
  (line 2356) and `Transport._really_parse_kex_init` are not reachable. The
  only reference to `_negotiate_keys` is the handler table that
  `Transport.__init__` builds (lines 556-566, the entry at line 565), and the
  only reference to `_parse_kex_init` is in `_negotiate_keys`;
  `Transport.__init__` is not reachable. `Transport.run`, which is, hands a
  received KEXINIT to that table (lines 2089-2094). The 7 checks of
  `_parse_kex_init` (1 of `MessageOrderError`, "In strict-kex mode, but
  KEXINIT was not the first packet!", and 6 of `IncompatiblePeer`, such as
  "Incompatible ssh peer (no acceptable kex algorithm)") are therefore
  counted as not reachable.
- `connect` names `AgentClientProxy.connect` and `AgentServerProxy.connect`
  (`paramiko/agent.py` lines 270 and 321) besides `SSHClient.connect` and
  `Transport.connect`; all 4 are reachable, and so are the 5 checks of
  `paramiko/agent.py`.

## Differences from the screening

The screening record is `T/selection/screening-results.json` lines 511-559.

- Entry points (lines 521-527): `Transport.start_client`,
  `Transport.connect`, `SSHClient.connect`, `parse_next` of 5 key-exchange
  modules and `Packetizer.read_message`. Added here: `start_server` (the
  server side of the negotiation, `sites/docs/index.rst` lines 13-17) and
  `missing_host_key` (the policy that accepts or rejects an unknown host
  key, `paramiko/client.py` lines 797-804). No block of the 19 test files
  calls either name (14:13:03Z), so neither adds a block. Left out:
  `renegotiate_keys` (`paramiko/transport.py` line 1168), a request to
  switch keys rather than a call that submits a received artifact; of the
  names left out it is the nearest case.
- Rejection classes (lines 543-549): the record also lists
  `EOFError (packet layer)`. No docstring of an entry point names it
  (`paramiko/transport.py` lines 686-688, 751-753 and 1310-1311;
  `paramiko/client.py` lines 323-339; `paramiko/packet.py` lines 493-494),
  so it is no rejection class here; 1 block that calls an entry point
  expects it (`tests/test_transport.py` line 868, `test_handshake_timeout`).
- Checks: the record gives 35 (line 550), counted on 13 listed files with
  reachability set by hand (line 552); the toolkit counts 107, 61 of them
  reachable. The record counts the 7 checks of `_parse_kex_init`, 6 of them
  `IncompatiblePeer`, as reachable from the handshake (lines 519 and 552);
  the toolkit counts them as not reachable (section "Reachability").
- Blocks: the record counts 10 (line 553) with a pattern that also accepts
  the test helpers `_test_connection` and `server` (line 558). 5 of its 10
  are included (`tests/test_kex.py` lines 565 and 587;
  `tests/test_client.py` lines 500, 568 and 584). The other 5 reach the
  entry point only through such a helper, and under `T/PROTOCOL.md`
  lines 228-232 they call no entry point: `tests/test_client.py` line 317
  passes `self._test_connection` (defined at line 184; it calls `connect` at
  line 211), and `tests/test_transport.py` lines 1334, 1343, 1365 and 1418
  run `with server(...)` (`tests/_util.py` line 216; it calls `connect` at
  line 304). 2 further negative tests use the decorator `raises` of
  pytest-relaxed (`tests/test_client.py` lines 732 and 753;
  `pytest_relaxed/raises.py` lines 6-18), a form that is no block under
  `T/PROTOCOL.md` lines 214-216.

## Differences from the project's own test runs

These matter only for runs of the tests, which result 2 rules out.

- The task `test` adds `--verbose`, `--color=yes` and `--capture=sys`
  (`tasks.py` lines 38-44), and `coverage` runs it under
  `coverage run -m pytest` (line 66); none of them is taken. It runs pytest
  in a pseudo-terminal (`pty=True`, line 77); the toolkit does not.
- The task removes `SSH_AUTH_SOCK` from the environment (lines 67-74). The
  toolkit's pytest calls get `PATH`, `HOME`, `LANG`, `LC_ALL`,
  `PYTHONHASHSEED` and `PYTHONDONTWRITEBYTECODE` only (`T/reach/run.py`
  lines 155-165), so `SSH_AUTH_SOCK` is not passed either; `HOME` is.
- The suite run `all` includes the tests marked `slow` (`tests/_util.py`
  line 50), as the task `coverage` does (lines 80-85); the task `test`
  leaves them out unless `--include-slow` is given (lines 33-36 and 45-46).
- pytest-relaxed replaces the terminal reporter
  (`pytest_relaxed/plugin.py` lines 40-50) and collects every `.py` file of
  `tests/` whose name does not start with `_` (lines 12-37).
- The screening notes that some tests rely on thread timing
  (`T/selection/screening-results.json` line 557).

## Files

| File | SHA-256 when written |
|---|---|
| `draft.json` | `bf946d004696d57b7111fc679bb6fc23033b87d5e5029941f2429db46d71f10b` |
| `subject.json` | `28c3296555be988274a945aff3a6c1fe52211450e8ceae8d59d8c1fa2c8b0c6d` |
| `requirements.txt` | `240b5e08456dc009f6d84556cfda03840efd3e73badd10920f7b98da494c2f52` |
| `checks.json` | `b2b7cb0d83ce89fd077533f8f141662d7386a66d18ba82dd49b9278853eca81b` |
| `blocks.json` | `32e8a7954d754823b667cdd06066b9414e8463b9439fd10291898c34a38983e5` |
| `targets.json` | `561329e61005e79659f3302d90b61c83a9c33a9b3d7ddaead1887e1a6da249b5` |

`--out X/screened/generated/paramiko` was given for later steps; only `pack`
writes there (`T/reach/run.py` line 726), and that folder does not exist.
`W/local.json` holds the paths of the clone and of the interpreter for
`--work W`.
