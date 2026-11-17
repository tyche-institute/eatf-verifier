# pycryptodome 4.4.0: preparation

Part `screened/` of the extension, written before the protocol commit. Paths: M is the repository root,
T = M/experiments/target-reach, X = M/experiments/target-reach-extension, S = X/screened/subjects/pycryptodome
(this folder) and W = X/work/pycryptodome (clone, environment and logs; not committed). Times are UTC. The
toolkit of T was used unchanged; the clone, the tests of the library and T were not changed. Nothing ran on the
library but cloning, the environment, `pytest --collect-only` and the static steps `define`, `targets` and
`verify` (no test, no deletion, no whole-suite run).

## Result

- **Defined, and `verify` accepts it.** S holds `draft.json`, `subject.json`, `requirements.txt`, `checks.json`,
  `blocks.json` and `targets.json`. `T/reach/run.py define targets verify` ended with exit 0 and the line
  "verify: commit 3a016ab7269b, 132 subject files and 20 test files match, CPython 3.12.3"
  (W/prep/run-define-targets-verify.log, line 6).
- **The tests cannot be collected from a copy.** `pytest --collect-only` on the suite run collects 393 tests from
  13 of the 96 test files and fails on the other 83, each with `OSError: Cannot load native module`
  (W/collect/collect-only.log, line 1350; W/collect/outcomes.json, `failed_collectors`, 83 entries). The 83 hold
  all 20 test files of `subject.json`, the files of the 74 included blocks. The reason: the package loads its
  compiled modules from files next to its own (lib/Crypto/Util/_raw_api.py, lines 492-514, raises this
  `OSError`; lib/Crypto/Util/_file_system.py, lines 25-28, gives the path), and the commit holds none (0 files
  `*.so`, `*.pyd`, `*.dll` or `*.dylib` under lib/, command of 14:00:43Z below); setup.py builds them (59
  `Extension(` entries; line 27 imports setuptools). pyproject.toml, lines 94-95, says so: "Plain "pytest" runs
  the self-tests of the installed package (the sources in lib/ lack the compiled extensions)".
- **What follows for the runs (not decided here).** A copy made by `run.py` holds only the paths of `copy`
  (T/reach/run.py, lines 310-322), so the suite run and the recorder runs would miss the same 83 test files, and
  sentinel 2 ("every test file is collected", T/PROTOCOL.md, lines 472-474) could not hold. Each of the 3 ways to
  give a copy its compiled modules departs from the toolkit or from these definitions: built inside the clone,
  they are files of the copied paths that the commit does not hold, which `verify` refuses (T/reach/run.py,
  lines 215-226); installed from the released wheel, the distribution is installed, which `verify` refuses
  (lines 244-257); built inside each copy, they need a step that `run.py` does not have (its steps, lines
  767-769) and setuptools, which is not in requirements.txt. A C compiler and the headers of CPython 3.12 are on
  this machine (`/usr/bin/gcc`, `/usr/include/python3.12/Python.h`, 14:06:16Z). T/PROTOCOL.md, lines 134-137:
  "A library whose tests cannot be run under the recorder without changing 1 of the 6 decisions is reported as
  failed, with the reason."

## Release, repository and commit

| Fact | Value | Source |
|---|---|---|
| Release of decision 1 | 4.4.0: the latest release on 14 November 2026 (first file uploaded 2026-11-07T11:04:16Z; the next, 4.5.0, 2026-11-15T13:02:52Z); none of 3.24.0 to 4.5.0 is a pre-release or yanked | https://pypi.org/pypi/pycryptodome/json, read 2026-11-17T13:51:57Z (W/pypi/pycryptodome.json, SHA-256 c242aacf410123682c990cc5fd48616b53531fd543c1d1dd58477766eb4ab9c2), `releases` |
| Latest release now | 4.5.0 | same file, `info.version` |
| Python and dependencies of 4.4.0 | requires_python ">=3.9"; requires_dist only the extra `test` (pytest, pycryptodome-test-vectors); 31 files, among them the wheel `cp39-abi3-manylinux2014_x86_64` | https://pypi.org/pypi/pycryptodome/4.4.0/json, read 2026-11-17T13:51:57Z (W/pypi/pycryptodome-4.4.0.json, SHA-256 293da569165c754b5f88cf2419e468bddf03b935be28860263cfe0253b5107e0) |
| Repository | https://github.com/Legrandin/pycryptodome | same file, `info.project_urls.Source`; T/selection/screening-results.json, record of pycryptodome |
| Tag and commit | `v4.4.0`, a lightweight tag on 3a016ab7269b9a43cd14016989011c5051487b77 (committed 2026-11-07T10:33:36+01:00, "Merge branch 'hpke-unseal-seq'"); `v4.5.0` is 71fc83368a55a34a05481724f54cab8b20e134f9 | `git ls-remote --tags`, 2026-11-17T13:52:17Z; in the clone, `git cat-file -t v4.4.0` = commit and `git log -1`, 13:52:32Z |
| Version in the sources | `version_info = (4, 4, "0")` | lib/Crypto/__init__.py, line 22 |

The screening record gives the same repository and "v4.4.0 (3a016ab7269b9a43cd14016989011c5051487b77)"
(T/selection/screening-results.json).

## Definitions

`draft.json` (written 2026-11-17T13:59:47Z, before any count of the toolkit) gives the 6 decisions of
T/PROTOCOL.md, section 3, and the settings, each decision with its source in the documentation or the
configuration of the library. In short:

1. Release 4.4.0 at commit 3a016ab7269b9a43cd14016989011c5051487b77 (above).
2. Package `Crypto` in the source root `lib` (setup.py, lines 325-326).
3. Entry points, as names: `verify`, `hexverify`, `decrypt_and_verify`, `unseal`, `bcrypt_check`
   (Doc/src/signature/signature.rst, lines 25-37; Doc/src/guides/hashing.rst, lines 92-103;
   Doc/src/cipher/aes.rst, lines 36-43 and 175-182; Doc/src/guides/public_key_encryption.rst, lines 50-60;
   Doc/src/io/kdf_limits.rst, lines 145-152; Doc/src/protocol/kdf.rst, lines 101-124). `new`, `decrypt`, key
   import and unpadding are not entry points (draft.json, `entry_points_source`).
4. Rejection base `ValueError` (Doc/src/exceptions.rst, lines 6-15, and the docstrings named in
   `rejection_bases_source`). `define` found 10 classes below it in the package (checks.json,
   `rejection_classes`): DeserializeError, IncorrectPassphraseError, KdfIterationLimitError, KdfLimitError,
   KdfMemoryLimitError, MessageLimitReachedError, MessageTooLongError, PassphraseRequiredError, PbesError,
   UnsupportedEccFeature.
5. Test directory `lib/Crypto/SelfTest` (pyproject.toml, lines 93-97: `testpaths = ["Crypto.SelfTest"]`).
6. 1 suite run, `all` = `lib/Crypto/SelfTest` (INSTALL.rst, lines 9-16; .github/workflows/integration.yml,
   lines 41-61; lib/Crypto/SelfTest/__init__.py, lines 41 and 56, and __main__.py, line 34). The second test step
   of the workflow (lines 66-74, `--skip-slow-tests`) runs only for Python 3.15.

Settings: `copy` = `lib`, `pyproject.toml` (the file holds the pytest configuration, lines 93-97);
`pytest_args` = `-p no:cacheprovider` (as in T/subjects/joserfc/draft.json, and as lib/Crypto/SelfTest/__init__.py,
line 41, calls pytest); `python` = 3.12.3; `source_root` = `lib`.

Readings that a run of the next stage meets:

- The tests live inside the package. `T/reach/scope.py` counts the 16 modules of `Crypto/SelfTest/` that are not
  test files as subject files (subject.json, `subject_files`, 16 of 132: `__init__.py`, `__main__.py`,
  `loader.py`, `plugin.py`, `st_common.py`, `Cipher/common.py`, `Hash/common.py` and the 9 `__init__.py` of the
  sub-packages). They hold 1 check, `SelfTest.loader.load_test_vectors_wycheproof#1` (loader.py, lines 222-224),
  not reachable (checks.json).
- pyproject.toml, line 96, adds `-p Crypto.SelfTest.plugin --pyargs` to every pytest call made in a copy. With
  them, the path argument of the suite run still collects (below), and the plugin loads from the copy (header
  line "pycryptodome-test-vectors 1.0.29", lib/Crypto/SelfTest/plugin.py, lines 31-37). The plugin adds the
  option `--skip-slow-tests` (lines 18-20); the suite run does not pass it, as the first test step of the
  workflow does not.
- The screening counted 1 entry point, `DSS.verify`: 7 checks and 11 negative blocks, 6 class-only
  (T/selection/screening-results.json). The definition here gives the same for DSS (checks.json: 7 checks
  `Signature.DSS.DssSigScheme.verify#1` to `#7`; blocks.json: 11 included blocks in test_dss.py, 6 class-only)
  and 74 included blocks in all.

## Environment

- `/usr/bin/python3.12 -m venv W/venv` (14:00:06Z to 14:00:08Z, exit 0): CPython 3.12.3, pip 24.0 and nothing
  else.
- `W/venv/bin/python -m pip install -r W/clone/requirements-test.txt` (14:00:11Z to 14:00:22Z, exit 0). The file
  is the test requirements of the repository (lines 1-2: `pytest`, `pycryptodome-test-vectors==1.0.29`), the 2
  names of the extra `test` (pyproject.toml, lines 36-37); 4.4.0 has no other dependency (PyPI, above). The
  package itself is not installed, and no compiled module was built.
- `W/venv/bin/python -m pip freeze > S/requirements.txt` (14:00:26Z, exit 0): iniconfig 2.3.1, packaging 26.3,
  pluggy 1.7.0, pycryptodome-test-vectors 1.0.29, Pygments 2.21.0, pytest 9.2.0 (SHA-256
  eb93e7146ab229348d298713ca4b4708877a9933a8b814a193f4051beeeedacf). pytest 9.2.0 and pluggy 1.7.0 are the pins
  of T/subjects/joserfc, oauthlib, authlib and google-auth (their requirements.txt).
- The pin 1.0.29 is the one of the repository (requirements-test.txt, line 2); the latest
  pycryptodome-test-vectors is 1.0.32 (https://pypi.org/pypi/pycryptodome-test-vectors/json, read
  2026-11-17T13:57:09Z). 1.0.29 declares no dependency
  (https://pypi.org/pypi/pycryptodome-test-vectors/1.0.29/json, same time).
- cffi is not installed. The workflow tests each CPython version of its matrix with and without it
  (.github/workflows/integration.yml, lines 11-12 and 37-39); the environment here is the entry `cffi: no`.

## Collection

A copy W/collect/copy of the 2 paths of `copy` (`cp -a`; identical to the clone by `diff -r` and `cmp`), and the
environment that `run.py` gives a run without the recorder (T/reach/run.py, lines 155-175):

```
cd W/collect/copy
env -i PATH=W/venv/bin:/usr/bin:/bin HOME=$HOME LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONHASHSEED=0 \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=T/guard:W/collect/copy/lib \
  OFFLINE_OUT=W/collect/offline.json OUTCOMES_OUT=W/collect/outcomes.json \
  W/venv/bin/python -m pytest -q -p no:cacheprovider -p reach_offline --rootdir=. \
  --continue-on-collection-errors --collect-only lib/Crypto/SelfTest
```

It ran from 14:00:55Z to 14:00:58Z, exit 1: "393 tests collected, 83 errors in 2.36s" (W/collect/collect-only.log,
line 1350). The same without `-q` (14:01:36Z to 14:01:39Z, exit 1, W/collect/collect-header.log) prints
"platform linux -- Python 3.12.3, pytest-9.2.0, pluggy-1.7.0", "pycryptodome-test-vectors 1.0.29",
"configfile: pyproject.toml" and "collected 393 items / 83 errors" (lines 2-6). The offline guard of T
(T/guard/reach_offline.py, lines 126-130) wrote 0 failed tests and 83 failed collectors (outcomes.json) and 0
connection attempts (offline.json). The clone stayed clean, and the copy stayed identical to it.

Tests collected (collect-only.log, the test ids by file):

| Test file (under lib/Crypto/SelfTest/) | Tests |
|---|---|
| Math/test_Numbers.py | 194 |
| Util/test_asn1.py | 105 |
| PublicKey/test_RSA.py | 22 |
| Util/test_Padding.py | 17 |
| PublicKey/test_ElGamal.py | 12 |
| PublicKey/test_DSA.py | 11 |
| Util/test_number.py | 8 |
| Math/test_nat.py | 7 |
| Math/test_Primality.py | 6 |
| Util/test_Counter.py | 6 |
| Protocol/test_rfc1751.py | 2 |
| Util/test_rfc1751.py | 2 |
| Random/test_random.py | 1 |

Importing these 13 files did not fail; lib/Crypto/Math/Numbers.py, lines 32-40, for instance, falls back to Python
code when its compiled module is missing.

The 83 files not collected, by the first missing module of each (collect-only.log, the first `E` line of each
"ERROR collecting" section):

| Missing compiled module | Test files |
|---|---|
| Crypto.Util._cpuid_c | 63 |
| Crypto.Hash._SHA1 | 5 |
| Crypto.Util._strxor | 3 |
| Crypto.Hash._MD5 | 2 |
| Crypto.Cipher._ARC4, _raw_arc2, _raw_blowfish, _raw_cast, _raw_des, _raw_des3 | 1 each |
| Crypto.Hash._BLAKE2b, _MD2, _MD4, _RIPEMD160 | 1 each |

The 20 test files of `subject.json` are among them: test_dss, test_pkcs1_15 and test_pss stop at
`Crypto.Hash._SHA1`, test_mldsa at `Crypto.Hash._MD5`, test_BLAKE2 at `Crypto.Hash._BLAKE2b`, and the other 15
at `Crypto.Util._cpuid_c`.

## define, targets, verify

```
cd W; export PYTHONHASHSEED=0
python3 -I -B T/reach/run.py define targets verify --subject S/subject.json --clone W/clone \
  --python W/venv/bin/python --work W --defs S --out X/screened/generated/pycryptodome
```

It ran from 14:02:06Z to 14:02:09Z, exit 0 (W/prep/run-define-targets-verify.log; the log prints local times,
UTC+1). `--out` is read only by the step `pack` (T/reach/run.py, lines 726 and 781), and nothing was written
there.

| Count | Value | Source |
|---|---|---|
| Checks | 777, all in subject files | checks.json, `checks` (role `subject`) |
| Reachable checks | 400 | checks.json, `reachable` |
| Blocks in the 20 test files of the subject | 376 | blocks.json, `counts.blocks` |
| Blocks with an entry-point call | 86 | blocks.json, `counts.entry_point_blocks` |
| Included blocks | 74, in 20 test files | blocks.json, `counts.included` |
| Blocks in the test directory | 1173, in 96 test files | subject.json, `scope_counts` |
| Targets, assertion tier | 5 (`assert-literal` 5) | targets.json, `counts`, and the `tier` of each row |
| Targets, name tier | 11 (`name` 11) | same |
| No target | 58 (`none: tie` 38, `none: no name token matches` 20) | same |
| Checks that are a target | 9 | targets.json, `target` |
| Tests collected | 393, in 13 of 96 test files; 0 in the 20 test files of the subject | collect-only.log, line 1350; outcomes.json |

The rule is `reach-target-rule/2` (targets.json, `rule_version`). The toolkit's own line:
"define: 777 checks (777 in subject files, 400 reachable); 376 blocks in the 20 test files of the subject, 74
included in 20 files; the test directories hold 1173 blocks in 96 test files" (log, line 2) and "targets: rule
reach-target-rule/2; {"assert-literal": 5, "name": 11, "none: no name token matches": 20, "none: tie": 38}"
(line 4).

From blocks.json, with no run: of the 376 blocks, all `with pytest.raises`, 290 call no entry point
(`exclusion`: 174 for that alone, 114 that also expect TypeError, 2 that also expect AttributeError); of the 86
that call one, 10 expect TypeError, 2 expect `exc`, a name that `define` does not resolve to a class (`expects
?exc`; Protocol/test_KDF.py, lines 710 and 713; T/reach/blocks.py, lines 398-404), and 74 are included.
The included blocks call `verify` 43 times, `decrypt_and_verify` 15, `unseal` 8, `bcrypt_check` 5 and
`hexverify` 3 (`entry_calls`), and expect ValueError (71) or KdfIterationLimitError (3) (`expected`). By the
predicate of T/reach/analyse.py, lines 153-156, 56 of the 74 are class-only and 18 assert more; T/PROTOCOL.md,
lines 51-52, states E5 only where at least 9 in 10 are class-only.

Included blocks by test file (blocks.json):

| Test file (under lib/Crypto/SelfTest/) | Included blocks |
|---|---|
| Signature/test_mldsa.py | 16 |
| Signature/test_dss.py | 11 |
| Protocol/test_HPKE.py | 7 |
| Protocol/test_KDF.py | 5 |
| Cipher/test_CCM.py | 4 |
| Signature/test_pss.py | 4 |
| Cipher/test_ChaCha20_Poly1305.py | 3 |
| Cipher/test_GCM.py | 3 |
| Cipher/test_OCB.py | 3 |
| PublicKey/test_ECC_secp256k1.py | 3 |
| Cipher/test_EAX.py | 2 |
| Cipher/test_SIV.py | 2 |
| Hash/test_BLAKE2.py | 2 |
| Hash/test_KMAC.py | 2 |
| Hash/test_Poly1305.py | 2 |
| Cipher/test_KW.py | 1 |
| PublicKey/test_ECC_Ed448.py | 1 |
| PublicKey/test_ECC_NIST.py | 1 |
| Signature/test_eddsa.py | 1 |
| Signature/test_pkcs1_15.py | 1 |

## Commands run on the library

Times: the output of `date -u` in the command where it printed one, else the time the command was issued.
Commands that only read the clone or a downloaded file are grouped.

| Time (UTC) | Command | What it gave |
|---|---|---|
| 13:51:57Z | `curl -sS -o W/pypi/pycryptodome.json https://pypi.org/pypi/pycryptodome/json`; the same for `/pycryptodome/4.4.0/json` | HTTP 200, 1545826 and 33982 bytes |
| 13:52:02Z to 13:52:12Z | `python3 -I` reads of the 2 files; `sha256sum` | releases and upload times (table above) |
| 13:52:17Z to 13:52:18Z | `git ls-remote --tags https://github.com/Legrandin/pycryptodome.git` | `v4.4.0` 3a016ab7…, no peeled entry; `v4.5.0` 71fc8336… |
| 13:52:27Z to 13:52:32Z | `git clone --quiet https://github.com/Legrandin/pycryptodome.git W/clone` | done |
| 13:52:32Z | `git -C W/clone -c advice.detachedHead=false checkout --quiet 3a016ab7269b9a43cd14016989011c5051487b77`; `rev-parse HEAD`, `cat-file -t v4.4.0`, `log -1`, `status --porcelain --untracked-files=all --ignored`, `remote -v` | HEAD at the commit; tag type commit; status empty |
| 13:52:36Z to 13:53:23Z | reads (`ls`, `cat -n`, `grep`) of the clone: .gitignore, pyproject.toml, requirements-test.txt, MANIFEST.in, .github/workflows/integration.yml, lib/Crypto/SelfTest/{__init__,__main__,plugin,st_common,loader}.py, lib/Crypto/__init__.py, lib/Crypto/Util/_raw_api.py, lib/Crypto/Util/_file_system.py | sources of `draft.json` |
| 13:55:14Z to 13:56:59Z | reads of Doc/src (signature/signature.rst, exceptions.rst, `grep` for verify, authentic, unseal and bcrypt_check), of the definitions of the 5 names in lib/Crypto, of the docstrings of DSS.py, HMAC.py, _mode_gcm.py, HPKE.py, _mode_kw.py and KDF.py, of test_vectors/, setup.py and INSTALL.rst | sources of `draft.json` |
| 13:57:09Z | `curl` of https://pypi.org/pypi/pycryptodome-test-vectors/1.0.29/json, https://pypi.org/pypi/pycryptodome-test-vectors/json and https://pypi.org/pypi/pytest/json into W/pypi | HTTP 200 3 times; 1.0.29, 1.0.32, 9.2.0 |
| 13:57:21Z to 13:59:40Z | reads: `__version__` of test_vectors/pycryptodome_test_vectors/__init__.py, `git log -1` of 2 files, Doc/src (aes.rst, public_key_encryption.rst, hashing.rst, signatures.rst, kdf_limits.rst, kdf.rst), docstrings of the entry points, INSTALL.rst lines 1-20, setup.py lines 320-330, lib/Crypto/Cipher/PKCS1_OAEP.py, oaep.py, HPKE.py | sources of `draft.json` |
| 13:59:47Z | `python3 -I write_draft.py S/draft.json` (a script outside M that writes the JSON of the decisions, indent 1) | S/draft.json |
| 13:59:55Z to 13:59:57Z | `python3 -I -B T/reach/scope.py --draft S/draft.json --clone W/clone` | exit 0; "scope: 132 subject files, 20 test files"; S/subject.json |
| 14:00:01Z | `python3 -I` read of subject.json; `git -C W/clone status --porcelain --untracked-files=all --ignored` | status empty |
| 14:00:06Z to 14:00:08Z | `/usr/bin/python3.12 --version`; `/usr/bin/python3.12 -m venv W/venv`; `pip --version`; `pip list` | Python 3.12.3; exit 0; pip 24.0 only |
| 14:00:11Z to 14:00:22Z | `W/venv/bin/python -m pip install --disable-pip-version-check --no-input -r W/clone/requirements-test.txt` | exit 0; 6 packages installed |
| 14:00:26Z | `W/venv/bin/python -m pip freeze --disable-pip-version-check > S/requirements.txt` | exit 0; 6 pins |
| 14:00:43Z to 14:00:46Z | `find W/clone/lib` for `*.so`, `*.pyd`, `*.dll`, `*.dylib`; `grep -c 'Extension(' setup.py`; reads of lib/Crypto/Math/Numbers.py | 0 files; 59 |
| 14:00:55Z to 14:00:58Z | `cp -a W/clone/lib W/clone/pyproject.toml W/collect/copy/`, `diff -r`, `cmp`; `pytest -q ... --collect-only lib/Crypto/SelfTest` (section Collection) | copy identical; exit 1; 393 tests collected, 83 errors |
| 14:01:06Z to 14:01:27Z | `python3 -I` and `grep` reads of outcomes.json, offline.json and collect-only.log; `sha256sum` | the counts of section Collection |
| 14:01:36Z to 14:01:39Z | `git -C W/clone status ...`, `diff -r -q`; the same `pytest --collect-only` without `-q` | status empty; exit 1; header lines |
| 14:02:06Z to 14:02:09Z | `python3 -I -B T/reach/run.py define targets verify ...` (section define, targets, verify) | exit 0; S/checks.json, S/blocks.json, S/targets.json, W/local.json |
| 14:04:01Z to 14:11:55Z | `python3 -I -B` reads of checks.json, blocks.json, targets.json, subject.json, outcomes.json and the PyPI files; `grep` and `git` reads of the clone (`tag --points-at HEAD`, `rev-parse`, `log -1`, `status`, `diff -r -q`) | the counts above; clone clean, copy identical |
| 14:06:16Z | `command -v gcc cc clang`; `ls /usr/include/python3.12/Python.h` | all present |
| 14:12:45Z to 14:12:52Z | reads of .github/workflows/integration.yml, lines 1-75 | the matrix and the 2 test steps |

## Open

- Whether pycryptodome is reported as failed under "No replacement" (T/PROTOCOL.md, lines 134-137) or its copies
  get the compiled modules by a stated change; nothing here builds them.
- The latest release is now 4.5.0 (2026-11-15). 4.4.0 is the release of decision 1 (the latest on 14 November
  2026) and the version read at screening.
