# service-identity 26.1.0: preparation before the protocol commit

This folder holds the definitions of `service-identity` 26.1.0 (rank 869,
`T/SELECTION.md` line 316) for the part `screened/` of the runs, made with
the toolkit `T/reach/`, unchanged, before the protocol commit of these runs.
What ran: the clone, the environment, `pytest --collect-only`, and the
steps `define`, `targets` and `verify`, which read the sources and run
nothing (`T/PROTOCOL.md` lines 148-149). No test of the library ran, no
check was deleted, and no whole-suite run was made.

Paths, relative to the root of this repository (head
`e8859540f548beaf0ac360d6fe946f986dca43fe`, `git rev-parse HEAD`,
2026-11-17T14:09:51Z): T = `experiments/target-reach`;
X = `experiments/target-reach-extension`; S = `X/screened/subjects/service-identity`
(this folder); W = `X/work/service-identity` (the clone, the environment and
the logs `W/prep/*.log`; not part of the deposit). Every time is UTC on
2026-11-17 and comes from `date -u` in the log or the script of its command.

## 1. Files

| File | Written by | Time |
|---|---|---|
| `draft.json` | written from the files of the release (section 2), before any count | 13:57:37Z (file time) |
| `subject.json` | `T/reach/scope.py` | 13:58:04Z (`W/prep/scope.log`) |
| `requirements.txt` | `pip freeze` of the environment (section 3) | 13:58:32Z (`W/prep/freeze.log`) |
| `checks.json`, `blocks.json`, `targets.json` | `T/reach/run.py define targets` | 13:59:08Z (`W/prep/run-define-targets-verify.log`) |
| `PREPARATION.md` | this file | |

## 2. Release and decisions

**Release (decision 1, `T/PROTOCOL.md` lines 85-86).** The PyPI JSON API,
`https://pypi.org/pypi/service-identity/json`, read at 13:53:10Z (copy:
`W/pypi/service-identity.json`): latest version 26.1.0 (`info.version`); 12
releases, 0.1 to 26.1.0, none a pre-release (`releases`).
`https://pypi.org/pypi/service-identity/26.1.0/json`, read at the same time
(copy: `W/pypi/service-identity-26.1.0.json`), gives 2 files:
`service_identity-26.1.0-py3-none-any.whl`, uploaded
2026-05-30T12:04:53Z, SHA-256
`68c32dadbb69135fb951077677e07cd7f6031020f3a8c8f47a28cda8a0742118`, and
`service_identity-26.1.0.tar.gz`, uploaded 2026-05-30T12:04:55Z, SHA-256
`6358c52882c96e66ac4a55eb3a72c7dd4a70763f8cc6fa4e70abde2656f4bf3b`;
`requires_python` `>=3.8`; `requires_dist` `attrs>=19.1.0`,
`cryptography>=47`, `idna; extra == "idna"`. 26.1.0 was uploaded before
14 November 2026, so it is also the latest release on that date. The
repository is `https://github.com/pyca/service-identity` (`project_urls`,
key `GitHub`, same file). In the clone, `26.1.0` is an annotated tag,
object `27682f774e0339891f044c2d6febd3e9be2b33cf`, of the commit
`5025f92e3856e814bb5012ba4ed03b71320131d8`, "Prepare 26.1.0", committed
2026-05-30T13:50:32+02:00 (`git cat-file -t`, `git rev-parse`, `git show`,
13:53:30Z).

**Package directory (decision 2).** `src/service_identity`: the only entry
of `src/` at the commit (`ls src`, `git ls-files src`, 14:07:38Z), and the
name the tests import (`tests/test_packaging.py` line 5). In `draft.json`:
`source_root` `src`, `package` `service_identity`.

**Decisions 3 to 6.** Each is in `draft.json` with its source:

| Decision | Value | Source |
|---|---|---|
| 3. entry points | `verify_certificate_hostname`, `verify_certificate_ip_address`, `verify_hostname`, `verify_ip_address`, `verify_service_identity` | `entry_points_source` |
| 4. rejection base | `CertificateError` and `VerificationError` | `rejection_bases_source` |
| 5. test directories | `tests` | `test_directories_source` |
| 6. suite runs | `all`: `tests` | `suite_runs_source` |

The settings: `copy` is `src`, `tests` and `pyproject.toml`, which holds
the pytest configuration (`pyproject.toml` lines 96-101); `pytest_args` is
`-p no:cacheprovider`, as in `T/subjects/oauthlib/draft.json` lines 32-35;
`python` is 3.12.3 (`T/PROTOCOL.md` line 271).

### 2.1 Two readings that the counts depend on

**Rejection base.** Decision 4 asks for "the base class of the exceptions
the documentation of the entry points names as rejections"
(`T/PROTOCOL.md` lines 90-91). The docstrings of the 4 documented functions
name 2 classes (`src/service_identity/cryptography.py` lines 55-61 and
93-99, `pyopenssl.py` lines 39-47 and 74-81), and
`src/service_identity/exceptions.py` declares each as a direct subclass of
the built-in `Exception` (lines 62-63 and 74). The 2 are taken as 2
rejection bases, and `Exception` is not. The recount of the selection
names several classes as bases where a library names several
(`T/selection/recount.sh` lines 20, 22, 26 and 30; line 36 gives
`google-auth` under both of its bases); each of the 4 subjects of T has 1
base (`T/PROTOCOL.md` lines 75-80). What the reading changes, by the files
of section 5: the 12 included blocks expect `CertificateError` (3) or
`VerificationError` (9) (`blocks.json`, `expected`), so with only 1 of the
2 as the base 3 or 9 blocks would be included, below the 10 of criterion I4
(`T/SELECTION.md` lines 62-66). With `Exception` as the base, the 11 blocks
that expect `TypeError`, `ValueError` or `ImportError` still call no entry
point (`blocks.json`, `exclusion`), and the 12 raise statements that
`checks.json` lists apart (`other_raises`) would be of rejection classes;
the counts under that reading were not computed.

**Entry points.** `verify_service_identity` is a function of the module
`hazmat`, which the package exports (`src/service_identity/__init__.py`
lines 21-28) and to which the note of `docs/api.rst` points (lines 5-9); the
4 documented functions call it (`cryptography.py` lines 68 and 108,
`pyopenssl.py` lines 54 and 90). 6 of the 12 included blocks call it and no
other entry point, all in `tests/test_hazmat.py` (`blocks.json`,
`entry_calls`); without it, 6 blocks would be included, below 10. The
screening used the same 5 entry points
(`T/selection/screening-results.json` lines 1027-1033).

## 3. Environment

- `/usr/bin/python3.12 -m venv W/venv`, 13:58:14Z: CPython 3.12.3,
  pip 24.0, `include-system-site-packages = false` (`W/prep/venv.log`).
- `W/venv/bin/python -m pip install --disable-pip-version-check
  'attrs>=19.1.0' 'cryptography>=47' 'coverage[toml]>=5.0.2' pytest idna
  pyOpenSSL`, 13:58:22Z to 13:58:24Z: 13 packages, each from a wheel,
  nothing built (`W/prep/pip-install.log` lines 28-43). The list is the
  tox environment `py312-pyopenssl-idna` of `env_list` (`tox.ini` line 7):
  the dependencies (`pyproject.toml` lines 32-36), the dependency group
  `tests` (`pyproject.toml` line 52, `tox.ini` line 14), the extra `idna`
  (`tox.ini` lines 15-16) and `pyopenssl` (`tox.ini` lines 17-18). Without
  pyOpenSSL, `tests/test_pyopenssl.py`, which holds 2 included blocks, is
  skipped at import (line 32); without idna, 2 tests of
  `tests/test_hazmat.py` are skipped (lines 230 and 424).
- `W/venv/bin/python -m pip freeze --disable-pip-version-check >
  S/requirements.txt`, 13:58:32Z: 13 lines. The distribution
  `service-identity` is not installed, and `service_identity` cannot be
  imported without a copy (`W/prep/freeze.log`).
- Compiled extensions: none is needed to import from the source tree. A
  search of `W/clone`, `.git` aside, for `*.c`, `*.pyx`, `*.so`, `*.pyd`
  and `*.h` found no file (13:58:47Z), and the only wheel of the release is
  `py3-none-any` (section 2). Nothing was built in the clone.

## 4. Collection

The paths of `copy` were copied from `W/clone` to `W/prep/collect-copy`
(13:58:47Z, `W/prep/collect-only.log`), and in that copy:

    env -i PATH=W/venv/bin:/usr/bin:/bin HOME=$HOME LANG=C.UTF-8 LC_ALL=C.UTF-8 \
      PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=T/guard:<copy>/src \
      OUTCOMES_OUT=W/prep/collect-only.outcomes.json OFFLINE_OUT=W/prep/collect-only.offline.json \
      W/venv/bin/python -m pytest -q -p no:cacheprovider -p reach_offline --rootdir=. \
      --continue-on-collection-errors --collect-only tests

- Exit status 0 (`W/prep/collect-only.log`), "135 tests collected in
  0.05s" (`W/prep/collect-only.out`): `tests/test_cryptography.py` 16,
  `tests/test_hazmat.py` 106, `tests/test_packaging.py` 2,
  `tests/test_pyopenssl.py` 11.
- No collection error (`failed_collectors` and `failed_tests` empty,
  `W/prep/collect-only.outcomes.json`); 0 refused attempts to reach another
  machine (`W/prep/collect-only.offline.json`).
- The same call without `-q` and without the 2 output variables, 13:58:59Z,
  exit status 0 (`W/prep/collect-header.log`): Python 3.12.3, pytest 9.2.0,
  pluggy 1.7.0, OpenSSL 4.0.3 29 Sep 2026, pyOpenSSL 26.4.0,
  cryptography 50.0.2, configfile `pyproject.toml`
  (`W/prep/collect-header.out` lines 1-8).
- `tests/test_hazmat.py` imports the constant `CERT_EVERYTHING` from
  `test_cryptography.py` (line 34), no test, so no test is collected twice.

## 5. define, targets, verify

From T, 13:59:08Z:

    PYTHONHASHSEED=0 python3 -I -B reach/run.py define targets verify \
      --subject S/subject.json --clone W/clone --python W/venv/bin/python --work W --defs S

Exit status 0. It printed (`W/prep/run-define-targets-verify.log`):

    define: 8 checks (8 in subject files, 8 reachable); 37 blocks in the 3 test files of the subject, 12 included in 3 files; the test directories hold 38 blocks in 4 test files
    targets: rule reach-target-rule/2; {"class": 9, "name": 3}
    verify: commit 5025f92e3856, 5 subject files and 3 test files match, CPython 3.12.3

`--out` was not given: only `pack` reads it (`T/reach/run.py` lines 726 and
781). `W/local.json` holds the clone and the interpreter. After the run the
clone is at the commit with no changed, untracked or ignored file
(`git status --porcelain --untracked-files=all --ignored`, 14:05:49Z and
14:09:51Z), and T has no change (`git status --porcelain
--untracked-files=all -- experiments/target-reach`, 14:09:51Z).

Counts, from the files the toolkit wrote:

| Count | Value | Source |
|---|---|---|
| checks | 8, all in subject files | `checks.json`, `checks` |
| reachable checks | 8 | `checks.json`, `reachable` |
| checks by class | `CertificateError` 7, `VerificationError` 1 | `checks.json`, `class` |
| raise statements listed apart, of no rejection class | 12: `TypeError` 6, `ValueError` 4, `ImportError` 1, `AttributeError` 1 | `checks.json`, `other_raises` |
| reachable function definitions | 23 of 30 | `checks.json`, `functions` |
| blocks in the 3 test files of the subject | 37: `test_cryptography.py` 5, `test_hazmat.py` 30, `test_pyopenssl.py` 2; all `with` | `blocks.json`, `counts`, `blocks` |
| blocks that call an entry point | 12 | `blocks.json`, `counts` |
| included blocks | 12: `test_cryptography.py` 4, `test_hazmat.py` 6, `test_pyopenssl.py` 2 | `blocks.json`, `counts`, `included` |
| included blocks, class-only | 0: 3 give a pattern, 9 assert on the caught exception after the block | `blocks.json`, `match`, `post_unparsed`; the test of `T/reach/analyse.py` lines 153-156 |
| blocks not included | 25: 14 call no entry point; 11 call no entry point and expect `TypeError` (6), `ValueError` (4) or `ImportError` (1) | `blocks.json`, `exclusion` |
| test directories | 4 test files, 38 blocks; 3 test files with an included block | `subject.json`, `scope_counts` (lines 56-59) |
| targets | 12 of the 12 included blocks: assertion tier 9 (basis `class`), name tier 3 (basis `name`) | `targets.json`, `counts`, `tier`, `basis` |

The 38th block of the test directories is in `tests/test_packaging.py`
(lines 22-26): it expects `AttributeError` and calls no entry point, so that
file holds no included block and is no test file of the subject
(`subject.json`, `tests`).

The 8 checks (`checks.json`; lines of the raise statements in
`src/service_identity/`):

| Check | Class | Template | Lines |
|---|---|---|---|
| `cryptography.extract_patterns#1` | `CertificateError` | `{*}` | `cryptography.py` 165 |
| `hazmat.verify_service_identity#1` | `CertificateError` | `{*}` | `hazmat.py` 55 |
| `hazmat.verify_service_identity#2` | `VerificationError` | empty | `hazmat.py` 82 |
| `hazmat.DNSPattern.from_bytes#1` | `CertificateError` | `{*}` | `hazmat.py` 164 |
| `hazmat.IPAddressPattern.from_bytes#1` | `CertificateError` | `{*}` | `hazmat.py` 188 |
| `hazmat.URIPattern.from_bytes#1` | `CertificateError` | `{*}` | `hazmat.py` 212 |
| `hazmat.SRVPattern.from_bytes#1` | `CertificateError` | `{*}` | `hazmat.py` 248 |
| `hazmat._validate_pattern#1` | `CertificateError` | `{*}` | `hazmat.py` 453, 457, 461, 464 |

The targets (`targets.json`): `hazmat.verify_service_identity#2` for the 9
blocks of the assertion tier, the only reachable check of class
`VerificationError` (`C_class` and `C_assert` hold 1 check each); and
`hazmat.verify_service_identity#1` for the 3 blocks of the name tier. These
3 give the pattern "Certificate does not contain any \`subjectAltName\`s",
which excludes none of the 7 `CertificateError` checks (`C_assert` holds 7),
and the name of the test gives the single highest score, 2.100061, on the
tokens `cert` and `pattern`. The other 6 checks are the target of no block.

## 6. Against the screening

The screening record is `T/selection/screening-results.json` lines
1017-1052.

- Checks. The screening counted 17 checks, 11 of them of `CertificateError`
  (10) or `VerificationError` (1), from the entry
  `verify_certificate_hostname`, with `msg = ...; raise E(msg)` resolved to
  the assigned text (line 1050). The toolkit gives 8: 7 of
  `CertificateError` and 1 of `VerificationError`. The template replaces
  every computed part of the message with a placeholder (`T/PROTOCOL.md`
  lines 197-201), and a message held in a local variable gives `{*}`
  (`checks.json`). The 4 raise statements of `_validate_pattern` assign 4
  different texts to `msg` (`hazmat.py` lines 452-464) and are 1 check here;
  4 checks in their place would match the difference of 3 between the 10
  and the 7 `CertificateError` checks. The screening scripts were not run
  again. `TypeError`, `ValueError` and `ImportError` are no rejection
  classes under the 2 bases (`T/PROTOCOL.md` lines 177-183); their raise
  statements are listed apart.
- Blocks. The screening's 12 negative blocks, `test_hazmat.py` 6,
  `test_cryptography.py` 4, `test_pyopenssl.py` 2 (lines 1045 and 1050),
  match the 12 included blocks file by file. The screening counts 9 of them
  as class-only and 3 as asserting the message (lines 1046-1047).
  `T/PROTOCOL.md` counts an assertion on the caught exception after the
  block as asserting more than the class (lines 236-238), so here 0 of the
  12 are class-only. E5 is then reported as "not stated" for this library,
  which needs at least 9 of every 10 included blocks to be class-only
  (`T/PROTOCOL.md` lines 51-52, `T/reach/report.py` lines 114-116).
- Criterion I5 was not checked: no test ran. The screening's entry reads
  "Yes, likely ... Not run." (line 1049), and none of the 7 candidates was
  checked against I5 (`T/SELECTION.md` lines 233-237). The collection of
  section 4 made no attempt to reach another machine, which says nothing
  about the runs.

## 7. For the runs after the protocol commit

1. **Paths.** `run.py` and `analyse.py` write into T unless told otherwise:
   `--work` defaults to `T/work/service-identity` (`T/reach/run.py` line
   126), `--witnesses` to `T/witnesses/service-identity` (lines 144-145),
   `pack` without `--out` writes `T/generated/service-identity/records.tar.xz`
   (line 726), and `analyse.py` defaults to `T/work/service-identity` and
   `T/generated/service-identity` (`T/reach/analyse.py` lines 847-848).
   Every step needs `--subject S/subject.json --work W --defs S`, and
   `pack`, `witness` and `analyse.py` need `--out` or `--witnesses` inside
   X. `W/local.json` already names the clone and the interpreter
   (`T/reach/run.py` lines 128-138).
2. **A test expected to fail in the whole-suite runs** (from the sources;
   not run). `tests/test_packaging.py::TestLegacyMetadataHack::test_version`
   compares `metadata.version("service-identity")` with
   `service_identity.__version__` (lines 9-16), and `__version__` reads the
   metadata of the installed distribution
   (`src/service_identity/__init__.py` lines 31-38), while `verify` requires
   that the distribution is not installed (`T/PROTOCOL.md` lines 276-278).
   tox installs the package as a wheel (`tox.ini` line 12). The test is in
   the suite run `all` but in no test file of the subject, so it is in the
   whole-suite runs only. Sentinel 6 asks that the control copy loses no
   test that passes in both unmodified runs (`T/PROTOCOL.md` lines
   478-480).
3. **Other Python versions.** A run of the negative tests on CPython 3.9 to
   3.14, as `experiments/target-reach-followup/versions/` made one for its
   subjects (its `README.md` lines 129-140), cannot use the pins of
   `requirements.txt` below CPython 3.11. By
   `https://pypi.org/pypi/<name>/<version>/json` for each of its 13 lines,
   read at 14:06:29Z (copies in `W/pypi/pins/`): pytest 9.2.0,
   pluggy 1.7.0, iniconfig 2.3.1 and cffi 2.1.1 require Python `>=3.10`;
   coverage 7.17.3 and pycparser 3.12 `>=3.11`; cryptography 50.0.2
   `!=3.9.0,!=3.9.1,>=3.9`, with a `cp39-abi3` wheel; the other 6 `>=3.9`.
   The release itself requires `>=3.8` (`pyproject.toml` line 11). The
   environments for 3.9 and 3.10 need other pins.
4. **Order.** `targets.json` was written at 13:59:08Z, before the protocol
   commit of these runs; in T, `targets` ran after the protocol commit and
   its output was committed apart (`T/PROTOCOL.md` lines 586-588).
5. **The work folder.** `X/.gitignore` did not exist at 14:05:49Z
   (`ls -la X`) nor at 14:09:51Z (`test -e`). At 14:12:32Z no ignore rule of the repository covers `W/clone`, `W/venv`
   or `W/prep` (`git check-ignore -v`, exit status 1), and X is untracked
   (`git status --porcelain`). `W/clone` is itself a git repository
   (`W/clone/.git`).

## 8. Commands run on the library

Times in UTC, 2026-11-17, from `W/prep/*.log` or from `date -u` in the same
script. Paths as above.

| Time | Command | What it gave |
|---|---|---|
| 13:53:10Z | `curl -sS -A 'python-requests/2 (reach-extension)' -o W/pypi/service-identity.json https://pypi.org/pypi/service-identity/json`; the same for `https://pypi.org/pypi/service-identity/26.1.0/json` | the releases and the files of 26.1.0 (section 2) |
| 13:53:29Z | `git clone https://github.com/pyca/service-identity W/clone` | done at 13:53:30Z |
| 13:53:30Z | `git -C W/clone cat-file -t 26.1.0`; `git -C W/clone rev-parse 26.1.0 26.1.0^{commit}`; `git -C W/clone show -s --format='%H %cI %an %s' 26.1.0^{commit}` | annotated tag `27682f77…`, commit `5025f92e…`, 2026-05-30T13:50:32+02:00 |
| 13:53:37Z | `git -C W/clone -c advice.detachedHead=false checkout 5025f92e3856e814bb5012ba4ed03b71320131d8`; `git -C W/clone status --porcelain --untracked-files=all --ignored`; `git -C W/clone describe --tags --exact-match HEAD` | HEAD at the commit; no change; `26.1.0` |
| 13:53Z to 13:57Z | reading only: `pyproject.toml`, `tox.ini`, `docs/api.rst`, `docs/installation.md`, `README.md`, `CHANGELOG.md`, `.github/workflows/*.yml`, `src/service_identity/*.py`, `tests/*.py` | `draft.json`, 13:57:37Z |
| 13:58:04Z | from T: `PYTHONHASHSEED=0 python3 -I -B reach/scope.py --draft S/draft.json --clone W/clone` | `subject.json`: 5 subject files, 3 test files |
| 13:58:14Z | `/usr/bin/python3.12 -m venv W/venv` | CPython 3.12.3, pip 24.0 (13:58:16Z) |
| 13:58:22Z | `W/venv/bin/python -m pip install --disable-pip-version-check 'attrs>=19.1.0' 'cryptography>=47' 'coverage[toml]>=5.0.2' pytest idna pyOpenSSL` | 13 packages from wheels (13:58:24Z) |
| 13:58:32Z | `W/venv/bin/python -m pip freeze --disable-pip-version-check > S/requirements.txt`; a check with `importlib.metadata` and `importlib.util.find_spec` | 13 lines; distribution not installed; package not importable |
| 13:58:47Z | `find W/clone -path W/clone/.git -prune -o ( -name '*.c' -o -name '*.pyx' -o -name '*.so' -o -name '*.pyd' -o -name '*.h' ) -print` (just before the time was printed) | no file |
| 13:58:47Z | copy of `src`, `tests`, `pyproject.toml` to `W/prep/collect-copy`; `pytest -q ... --collect-only tests` (section 4) | exit status 0; 135 tests; no collection error; 0 refused attempts |
| 13:58:59Z | the same `pytest` call without `-q` | exit status 0; versions of section 4 (13:59:00Z) |
| 13:59:08Z | from T: `PYTHONHASHSEED=0 python3 -I -B reach/run.py define targets verify --subject S/subject.json --clone W/clone --python W/venv/bin/python --work W --defs S` | exit status 0; `checks.json`, `blocks.json`, `targets.json`, `W/local.json` (section 5) |
| 13:59:08Z to 14:07:38Z | reading only: `tests/test_packaging.py`, `tests/test_hazmat.py`, `tests/test_pyopenssl.py`, `tests/conftest.py`, `src/service_identity/__init__.py`, `src/service_identity/hazmat.py`; `ls src`; `git ls-files src tests` (14:07:38Z) | sections 2, 5 and 7 |
| 14:05:49Z | `ls -la X X/work`; `git -C W/clone status --porcelain --untracked-files=all --ignored`; `git -C W/clone rev-parse HEAD` | no `X/.gitignore`; no change; `5025f92e…` |
| 14:06:05Z | `curl -sS -A 'python-requests/2 (reach-extension)'` of `https://pypi.org/pypi/cryptography/json` and `https://pypi.org/pypi/attrs/json` | the Python versions of each release (section 7) |
| 14:06:29Z | the same `curl` of `https://pypi.org/pypi/<name>/<version>/json` for the 13 lines of `requirements.txt` | the Python versions of each pin (section 7) |
| 14:09:51Z | `git -C W/clone status --porcelain --untracked-files=all --ignored`; `git -C W/clone rev-parse HEAD`; in the repository, `git rev-parse HEAD` and `git status --porcelain --untracked-files=all -- experiments/target-reach`; `test -e X/.gitignore`; `stat` of the files of S; reading `tox.ini` lines 1-30, `src/service_identity/__init__.py` lines 19-38 and the release list of `W/pypi/service-identity.json` | no change; `5025f92e…`; head `e8859540…`; T unchanged; no `X/.gitignore`; the file times of section 1 |
| 14:12:32Z | reading `src/service_identity/hazmat.py` lines 440-465; in the repository, `git check-ignore -v` of `W/venv`, `W/clone`, `W/prep`, and `git status --porcelain -- experiments/target-reach-extension` | section 6; exit status 1 (not ignored); X untracked |
