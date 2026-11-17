# The reading of the 20 sampled checks

Section 4.4 of `../../PROTOCOL.md` defines the reading; `reach.csv` holds its 20 results, in the order of `../sample.csv`, with the columns of section 4.4 and the input in short, which section 7 reports. Each library's reading follows, as it was written, with the scripts of its inputs in the folder of the library. In the readings and in the docstrings of their scripts, `X` is this experiment's folder, `experiments/target-reach-extension`, and `T` is `experiments/target-reach`.

After the reading, 3 things were done to these files, and nothing else. The 4 files `reach.csv` of the libraries were put together into `reach.csv`, in the order of the sample; the columns that some of them added beyond section 4.4 and the input (`row`, `fires` or `fired`, `record`, `source_lines`) were left out, since the order, the result and `scripts` carry the first 3 and the sections below give the source lines of each check. The 4 files `READING.md` were put together into this file, each under the heading of its library, with its headings 1 level lower. The paths of the machine in the JSON records of `authlib/` and in `authlib/name-paths.txt` were made relative (`../../DEVIATIONS.md`, entry 3). The SHA-256 values that the sections below give for those files are those of the files before these changes.

## google-auth


The reading of google-auth, done under `X/PROTOCOL.md`, section 4.4. `X` is
`experiments/target-reach-extension` and `T` is `experiments/target-reach`, both
in the worktree `eatf-verifier-mutation`. The library is google-auth 2.62.2, tag
`google-auth-v2.62.2`, commit `50b1eb269f110a4b7ab09ffe5ae59c0151cd63c2`, with
the entry point `decode` (`T/subjects/google-auth/subject.json`). Paths of the
library are relative to the root of its copy; `jwt.py` stands for
`google/auth/jwt.py`, and so on for the other files under `google/auth/`.

### Results

| Row of `sample.csv` | Check | Raise statement | Result | Fires |
|---|---|---|---|---|
| 1 | `auth.aws.RequestSigner.get_request_options#1` | `google/auth/aws.py:126` | not reached | does not fire |
| 2 | `auth._agent_identity_utils.parse_certificate#1` | `google/auth/_agent_identity_utils.py:329` | not reached | does not fire |
| 3 | `auth.crypt._python_rsa.RSASigner.from_string#1` | `google/auth/crypt/_python_rsa.py:190` | not reached | does not fire |
| 4 | `auth.credentials.AnonymousCredentials.apply#1` | `google/auth/credentials.py:606` | not reached | does not fire |
| 5 | `auth.credentials.AnonymousCredentials.refresh#1` | `google/auth/credentials.py:595` | not reached | does not fire |

The column `result` of `reach.csv` uses the 3 values of section 4.4 of the
protocol (reached, not reached, undecided); the column `fires` uses those of the
task (fires, does not fire, undecided). For these 5 checks they agree: no input
through an entry point executed a line of the raise statement of a sampled
check, and the tracer recorded no firing of one.

Each result is *not reached* because the source shows that no input through an
entry point can make the raise statement execute; the reason of each, by file
and line, is in its section below and in the column `reason`. The runs agree
with the source: in the 5 scripts (32, 34, 34, 29 and 29 inputs), no input
entered the function of the sampled check (`check_function_entered_by_an_input`
is false in each `<n>.json`), and each control, run last, executed the raise
line 1 time and fired the check.

### What was done (UTC, 2026-11-17)

The times come from `date -u` in the session, from the session's record of its
commands, from the modification times of the files written, and from the
fields `started`, `child_started` and `child_ended` of each `<n>.json`.

| Time | Step |
|---|---|
| 15:29:16Z to 15:30:40Z | Start. Read the description of the task, then `X/PROTOCOL.md` in full: commit `0796d80a8b34fe2915f48fd92c1485735b2a6fec`, committed at 15:27:46Z; both of its time-stamp tokens carry 15:27:56Z (`X/timestamps/README.md`). Then `X/no-fire/README.md`, `X/no-fire/sample.csv` (rows 1 to 5 are the checks of google-auth) and `X/DEVIATIONS.md` (no deviation recorded). |
| 15:30:48Z to 15:31:29Z | Read `T/subjects/google-auth/subject.json`, `draft.json` and `requirements.txt`, `T/work/google-auth/local.json`, the decisions and definitions of the first protocol (`T/PROTOCOL.md`), and the toolkit: `T/reach/run.py` (the environment of its pytest calls, lines 155-165; `make_copy` and `make_copy_check`, lines 310-330) and `T/reach/checks.py` (reachability by name). In the clone, `git rev-parse HEAD` gave the commit of `subject.json`. 2 `git status --porcelain` commands were run before the scripts existed: at 15:30:48Z in the repository of the worktree, and at 15:31:11Z in the clone, with `--untracked-files=all --ignored` (no output: the clone is clean). Neither rewrote an index: the clone's `.git/index` keeps the time 2026-11-14T06:12:46Z, the worktree's index the time 2026-11-17T15:28:05Z. The folder `.git` of the clone itself carries the time 15:31:11Z, so the command in the clone created and removed an entry there; no entry below that folder is newer than 2026-11-15T00:00:00Z (`find -mindepth 1 -newermt`, at 16:10:08Z). The scripts use only `git rev-parse HEAD`, with `GIT_OPTIONAL_LOCKS=0`. |
| 15:31:42Z | Created `X/no-fire/reach/google-auth/` and `X/work/reach/google-auth/`. |
| 15:31:46Z to 15:38:36Z | Read the source of the package (the lines are in the column `source_lines` of `reach.csv` and in the sections below) and `T/reach/recorder.py` (the definition of a firing, lines 32-36 and 237-270; the raise site, lines 194-210; the tool ids, lines 218-227). |
| 15:34:45Z | Ran `python3 -I -B name_chains.py > name_chains.txt`. |
| 15:42:46Z to 15:42:59Z | First run of `1.py` to `5.py`. |
| 15:43:12Z to 15:51:41Z | Checked again the source lines of the package and of the toolkit that `reach.csv` and this file cite. |
| 15:52:41Z to 15:52:46Z | Changed docstrings of `reach_common.py` only: its line references to the recorder and its description of the census. |
| 15:53:13Z to 15:53:14Z | Second run of `1.py` to `5.py`, each on a fresh copy; it gave the same result for each check as the first run. |
| 15:56:23Z | Wrote `reach.csv`. |
| 15:59:45Z to 16:03:14Z | Wrote this file. |
| 16:07:45Z to 16:07:49Z | Changed docstrings of `3.py`, `4.py` and `5.py` only: the wording of the purpose of the control (`3.py`) and of why no input is targeted at the check (`4.py`, `5.py`). |
| 16:08:02Z to 16:08:03Z | Third run of `1.py` to `5.py`, each on a fresh copy. The `<n>.json` files are those of this run. Against the second run, each record differs only in its 3 times and in the messages of C08, C23 and C24, which carry the times of the token or the current time; every result, exception class, raise site and entered function is the same. |
| 16:10:08Z | Counted the entries below the folder `.git` of the clone that are newer than 2026-11-15 (0). |
| after 16:10:08Z | Updated this section (its sources of times, the row of 15:30:48Z and the rows from 15:53:13Z). |

### Copy, environment and tracer

- **Clone, only read.** `T/work/src/google-auth/packages/google-auth`. Each
  script checks, with `git -C <clone> rev-parse HEAD` and
  `GIT_OPTIONAL_LOCKS=0`, that the clone is at the commit of `subject.json`
  (`clone_head` in `<n>.json`).
- **Fresh, unmodified copy.** Each script removes `X/work/reach/google-auth/copy`
  and makes it again from the clone as the toolkit's `make_copy` does
  (`T/reach/run.py`, lines 310-322): the paths `google`, `tests` and
  `tests_async` of `subject.json`, without `__pycache__`, `*.pyc` and
  `.pytest_cache` (`reach_common.py`, lines 100-121). It then checks the SHA-256
  of the 78 subject files against `T/subjects/google-auth/checks.json`, as
  `make_copy_check` does (lines 325-330), before and after the run
  (`subject_files_checked_before` and `subject_files_checked_after`: 78 and 78
  in each `<n>.json`).
- **Environment of the first study.** The inputs run in a child process,
  `T/work/venvs/google-auth/bin/python -I -B` (CPython 3.12.3, `child_python`),
  with the environment variables that the toolkit gives its pytest calls
  (`T/reach/run.py`, lines 155-165), in the folder `X/work/reach/google-auth/`.
  `google.auth`, `google.auth.jwt` and `google.auth._jwt_async` are imported
  from the copy, which the child checks (`reach_common.py`, lines 548-555).
- **Artifacts.** Tokens are signed with the key files of the copy's
  `tests/data/` (`privatekey.pem`, `es256_privatekey.pem`,
  `es384_privatekey.pem`) through the `cryptography` package of the environment,
  never through a function of google-auth. The certificates and public keys given
  as `certs` are files of the same folder: `public_cert.pem`, `other_cert.pem`,
  `privatekey.pub`, `es256_public_cert.pem`, `es256_publickey.pem`,
  `es384_publickey.pem` (`reach_common.py`, class `Artifacts`, lines 236-297).
- **Tracer** (`reach_common.py`, class `Tracer`, lines 396-545). It uses
  `sys.monitoring` with tool id 4 or 3, the ids that the recorder claims
  (`T/reach/recorder.py`, lines 218-227), and records, for each input:
  LINE events at the lines of the raise statement of the sampled check, from
  `checks.json` (`raise_line_executed`, `raise_line_hits`); RAISE events at a
  `RAISE_VARARGS` instruction on a line of a raise statement of any check of
  `checks.json`, with an exception whose class has the check's bare class name,
  which is a firing as the recorder defines it (`fired`); PY_START events of
  code in the package (`entered`). The exception that reaches the caller is
  recorded with its class, its message and its raise site, the innermost frame
  of its traceback in the package, read as the recorder's `site` reads it.
- **What an input is.** A call of `google.auth.jwt.decode` (`jwt.py:234`) or
  `google.auth._jwt_async.decode` (`_jwt_async.py:71`), the only 2 functions of
  the package named `decode`, with a token as the artifact and settings given
  through the documented parameters `certs`, `verify`, `audience` and
  `clock_skew_in_seconds`. Nothing of the package, of its dependencies or of its
  tests is changed, patched or replaced, and no input calls another function of
  the package. The non-default settings of each input are listed with it
  (`settings` in `<n>.json`, and the tables below).
- **Control.** Each script ends with a control, which is no input through an
  entry point: the function of the check, called directly with a value that the
  check rejects. It shows that the tracer records the raise statement when it
  executes.

### The inputs

#### The census C01 to C29

Each of the 5 scripts runs, after its targeted inputs, the same 29 inputs
(`census` in `reach_common.py`, lines 308-391). They give every condition of
`decode` in `jwt.py` (lines 260-330), and of the functions of that file that it
calls (lines 121-171 and 191-231), both of its outcomes, except the true outcome
of line 273: `es` is imported in this environment (lines 63-75), so ES256 and
ES384 are keys of `_ALGORITHM_TO_VERIFIER_CLASS` and never reach that line.
Their outcomes were the same in the 5 scripts. The token is RS256, signed with
`tests/data/privatekey.pem`, unless the table says otherwise.

| Input | Entry point | Artifact | Non-default settings | Ends with |
|---|---|---|---|---|
| C01 | `jwt.decode` | valid token | `certs`: `public_cert.pem` (str) | returns the payload |
| C02 | `jwt.decode` | valid token with kid 1, as bytes | `certs`: `{'1': public_cert.pem (bytes)}` | returns the payload |
| C03 | `jwt.decode` | valid token without kid | `certs`: `{'a': other_cert.pem, 'b': public_cert.pem}` | returns the payload |
| C04 | `jwt.decode` | valid token | `certs`: `privatekey.pub` (BEGIN RSA PUBLIC KEY) | returns the payload |
| C05 | `jwt.decode` | valid ES256 token (`es256_privatekey.pem`) | `certs`: `es256_public_cert.pem` | returns the payload |
| C06 | `jwt.decode` | valid ES384 token (`es384_privatekey.pem`) | `certs`: `es384_publickey.pem` | returns the payload |
| C07 | `jwt.decode` | token with a wrong signature | `verify=False` | returns the payload |
| C08 | `jwt.decode` | header.payload, no signature | `certs`: `public_cert.pem` | `MalformedError`, `jwt.py:149` (`auth.jwt._unverified_decode#1`) |
| C09 | `jwt.decode` | header segment `A` | `certs`: `public_cert.pem` | `binascii.Error`, `_helpers.py:291` (outside checks) |
| C10 | `jwt.decode` | header of the bytes ff fe | `certs`: `public_cert.pem` | `MalformedError`, `jwt.py:130` (`auth.jwt._decode_jwt_segment#1`) |
| C11 | `jwt.decode` | header `[]` | `certs`: `public_cert.pem` | `MalformedError`, `jwt.py:162` (`auth.jwt._unverified_decode#2`) |
| C12 | `jwt.decode` | payload `"x"` | `certs`: `public_cert.pem` | `MalformedError`, `jwt.py:167` (`auth.jwt._unverified_decode#3`) |
| C13 | `jwt.decode` | alg HS256 | `certs`: `public_cert.pem` | `InvalidValue`, `jwt.py:280` (`auth.jwt.decode#2`) |
| C14 | `jwt.decode` | alg `["RS256"]` | `certs`: `public_cert.pem` | `InvalidValue`, `jwt.py:280` (`auth.jwt.decode#2`) |
| C15 | `jwt.decode` | token with kid 2 | `certs`: `{'1': public_cert.pem}` | `MalformedError`, `jwt.py:290` (`auth.jwt.decode#3`) |
| C16 | `jwt.decode` | valid token | none (`certs=None`) | `TypeError`, `crypt/__init__.py:77` (outside checks), which `jwt.py:304-306` lets through |
| C17 | `jwt.decode` | valid token | `certs`: `es256_publickey.pem` | `InvalidValue`, `jwt.py:307` (`auth.jwt.decode#4`) |
| C18 | `jwt.decode` | valid ES256 token | `certs`: `public_cert.pem` | `InvalidValue`, `jwt.py:307` (`auth.jwt.decode#4`) |
| C19 | `jwt.decode` | signature of 256 bytes 0x30 | `certs`: `public_cert.pem` | `MalformedError`, `jwt.py:313` (`auth.jwt.decode#5`) |
| C20 | `jwt.decode` | ES256 token, signature of 10 bytes | `certs`: `es256_publickey.pem` | `MalformedError`, `jwt.py:313` (`auth.jwt.decode#5`) |
| C21 | `jwt.decode` | valid token | `certs`: `'not a key'` | `ValueError` from cryptography, `crypt/_cryptography_rsa.py:82` (outside checks) |
| C22 | `jwt.decode` | token without iat | `certs`: `public_cert.pem` | `MalformedError`, `jwt.py:209` (`auth.jwt._verify_iat_and_exp#1`) |
| C23 | `jwt.decode` | token issued 3600 s ahead | `certs`: `public_cert.pem` | `InvalidValue`, `jwt.py:219` (`auth.jwt._verify_iat_and_exp#2`) |
| C24 | `jwt.decode` | token expired 3600 s ago | `certs`: `public_cert.pem` | `InvalidValue`, `jwt.py:231` (`auth.jwt._verify_iat_and_exp#3`) |
| C25 | `jwt.decode` | token expired 100 s ago | `certs`: `public_cert.pem`; `clock_skew_in_seconds=600` | returns the payload |
| C26 | `jwt.decode` | valid token, aud `audience` | `certs`: `public_cert.pem`; `audience='other'` | `InvalidValue`, `jwt.py:324` (`auth.jwt.decode#6`) |
| C27 | `jwt.decode` | valid token, aud `audience` | `certs`: `public_cert.pem`; `audience=['x', 'audience']` | returns the payload |
| C28 | `_jwt_async.decode` | valid token | `certs`: `public_cert.pem` | returns the payload |
| C29 | `_jwt_async.decode` | valid token, aud `audience` | `certs`: `public_cert.pem`; `audience='other'` | `InvalidValue`, `jwt.py:324` (`auth.jwt.decode#6`) |

The exception classes without a module are those of `google.auth.exceptions`;
`TypeError` and `ValueError` are built-in. The raise site is the innermost frame
of the traceback in the package; in parentheses, the check of `checks.json`
whose raise statement it is, or "outside checks".

#### What a call of `decode` can execute

Over the 5 runs, the inputs entered the same 21 functions of the package
(`functions_entered_by_the_inputs`, the same in each `<n>.json`; the line is the
first line of the code object, which for a decorated method is the line of its
decorator). From the source, these 21 are all the functions of the package that
a call of an entry point can execute:

| Function (first line) | Calls that it makes (line) |
|---|---|
| `jwt.decode` (`jwt.py:234`) | `_unverified_decode` (260); `dict.get` on the header (267, 268); dict lookups in `_ALGORITHM_TO_VERIFIER_CLASS` (271) and `certs` (288), `certs.values()` (295); `crypt.verify_signature` (301); `_verify_iat_and_exp` (316); `dict.get` on the payload (320); exception classes (274, 280, 290, 307, 313, 324) |
| `_jwt_async.decode` (`_jwt_async.py:71`) | `jwt.decode` (94) |
| `jwt._unverified_decode` (`jwt.py:133`) | `_helpers.to_bytes` (146), `_helpers.padded_urlsafe_b64decode` (155), `_decode_jwt_segment` (158, 159), `MalformedError` (149, 162, 167) |
| `jwt._decode_jwt_segment` (`jwt.py:121`) | `_helpers.padded_urlsafe_b64decode` (123), `json.loads` (125), `MalformedError` (127) |
| `jwt._verify_iat_and_exp` (`jwt.py:191`) | `_helpers.utcnow` and `_helpers.datetime_to_secs` (204), `MalformedError` (209), `InvalidValue` (219, 231) |
| `crypt.verify_signature` (`crypt/__init__.py:56`) | `verifier_cls.from_string` (78), `verifier.verify` (79) |
| `rsa.RSAVerifier.from_string` (`crypt/rsa.py:57`) | `cls.__new__` (72), `_cryptography_rsa.RSAVerifier.from_string` (73) |
| `rsa.RSAVerifier.verify` (`crypt/rsa.py:53`) | `self._impl.verify` (55), that is `_cryptography_rsa.RSAVerifier.verify` |
| `_cryptography_rsa.RSAVerifier.from_string` (`crypt/_cryptography_rsa.py:58`) | `_helpers.to_bytes` (73), cryptography (76, 79, 82), `cls(pubkey)` (84) |
| `_cryptography_rsa.RSAVerifier.__init__` (`crypt/_cryptography_rsa.py:46`) | none |
| `_cryptography_rsa.RSAVerifier.verify` (`crypt/_cryptography_rsa.py:49`) | `_helpers.to_bytes` (51), cryptography (53) |
| `es.EsVerifier.from_string` (`crypt/es.py:101`) | `_helpers.to_bytes` (116), cryptography (119, 122, 125), `TypeError` (128), `cls(pubkey)` (130) |
| `es.EsVerifier.__init__` (`crypt/es.py:80`) | `_ESAttributes.from_key` (82) |
| `es._ESAttributes.from_key` (`crypt/es.py:52`) | `from_curve` (56) |
| `es._ESAttributes.from_curve` (`crypt/es.py:58`) | the `__init__` that `dataclass` generates for `_ESAttributes` (65, 68; its fields are lines 48-50) |
| `es.EsVerifier.verify` (`crypt/es.py:84`) | `_helpers.to_bytes` (87, 94), cryptography (92, 96) |
| `_helpers.to_bytes` (`_helpers.py:159`) | `InvalidValue` (178) |
| `_helpers.padded_urlsafe_b64decode` (`_helpers.py:278`) | `to_bytes` (289), `base64.urlsafe_b64decode` (291) |
| `_helpers.utcnow` (`_helpers.py:111`) | `datetime` (122, 123) |
| `_helpers.datetime_to_secs` (`_helpers.py:147`) | `calendar.timegm` (156) |
| `exceptions.GoogleAuthError.__init__` (`exceptions.py:21`) | the `__init__` of the next class of the MRO, a built-in one in these runs (22); `dict.get` (23) |

`verifier_cls` is the value that `jwt.py:271` takes from
`_ALGORITHM_TO_VERIFIER_CLASS` (lines 70 and 74-75): `rsa.RSAVerifier`
(`crypt/__init__.py:53`) for RS256, `es.EsVerifier` for ES256 and ES384; no
parameter of `decode` sets it. The header and the payload are what `json.loads`
returns (`jwt.py:125`), and lines 161 and 166 require them to be mappings, so
the 3 `get` calls are `dict.get`. Beyond these 21 functions, a call of `decode`
runs only the generated `__init__` of `_ESAttributes` (3 fields, no call), the
standard library (`json`, `base64`, `calendar`, `datetime`) and functions of
`cryptography`, which get only bytes and objects of `cryptography` from these
calls. The tracer does not see the generated `__init__`, whose code belongs to
no file of the package.

After the inputs, 23 modules of `google` were loaded
(`google_modules_loaded_after_the_inputs`, the same in the 5 runs).
`google.auth.aws` (row 1), `google.auth._agent_identity_utils` (row 2) and
`google.auth.crypt._python_rsa` (row 3) were not among them.
`google.auth.credentials` (rows 4 and 5) was loaded, since `jwt.py` imports it
(line 53), but neither of its 2 sampled functions was entered.

#### The targeted inputs

| Row | Input | Entry point | Artifact | Non-default settings | Ends with |
|---|---|---|---|---|---|
| 1 | T1 | `jwt.decode` | valid token, aud `http://sts.us-east-1.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15` | `certs`: `public_cert.pem`; `audience` = the same URL | returns the payload |
| 1 | T2 | `jwt.decode` | valid token, iss and aud `https://` | `certs`: `public_cert.pem`; `audience` = the URL of T1 | `InvalidValue`, `jwt.py:324` (`auth.jwt.decode#6`) |
| 1 | T3 | `_jwt_async.decode` | the token of T1 | as T1 | returns the payload |
| 2 | T1 | `jwt.decode` | valid token | `certs=b''` | `ValueError` from cryptography ("Unable to load PEM file. ..."), `crypt/_cryptography_rsa.py:82` |
| 2 | T2 | `jwt.decode` | valid token | `certs=''` | the same |
| 2 | T3 | `jwt.decode` | valid token with kid 1 | `certs={'1': b''}` | the same |
| 2 | T4 | `jwt.decode` | valid ES256 token | `certs=b''` | the same, at `crypt/es.py:125` |
| 2 | T5 | `_jwt_async.decode` | valid token | `certs=b''` | as T1 |
| 3 | T1 | `jwt.decode` | valid token | `certs`: the RSA key of `privatekey.pem` as a PKCS #8 PEM block with 1 byte 00 after the DER | `ValueError` from cryptography ("Valid PEM but no BEGIN PUBLIC KEY/END PUBLIC KEY delimiters. ..."), `crypt/_cryptography_rsa.py:82` |
| 3 | T2 | `jwt.decode` | valid token with kid 1 | `certs`: `{'1': the block of T1}` | as T1 |
| 3 | T3 | `jwt.decode` | valid ES256 token | `certs`: the block of T1 | the same, at `crypt/es.py:125` |
| 3 | T4 | `jwt.decode` | valid token | `certs`: the block without the byte 00 | as T1 |
| 3 | T5 | `_jwt_async.decode` | valid token | `certs`: the block of T1 | as T1 |

Rows 4 and 5 have no targeted input: no parameter of `decode` can carry a
credentials object or a token for one (sections below).

#### The controls

| Row | Call (no input through an entry point) | Raise line executed | Exception | Fires |
|---|---|---|---|---|
| 1 | `RequestSigner('us-east-1').get_request_options(credentials, <the URL of T1>, 'POST')` | `aws.py:126`, 1 time | `InvalidResource`, "Invalid AWS service URL" | yes |
| 2 | `parse_certificate(b'')` | `_agent_identity_utils.py:329`, 1 time | `ValueError`, "Certificate bytes cannot be empty or None." | yes |
| 3 | `_python_rsa.RSASigner.from_string(<the block of row 3, T1>)` | `crypt/_python_rsa.py:190`, 1 time | `InvalidValue`, `('Unused bytes', b'\x00')` | yes |
| 4 | `AnonymousCredentials().apply({}, token='token')` | `credentials.py:606`, 1 time | `InvalidValue`, "Anonymous credentials don't support tokens." | yes |
| 5 | `AnonymousCredentials().refresh(None)` | `credentials.py:595`, 1 time | `InvalidOperation`, "Anonymous credentials cannot be refreshed." | yes |

The control of row 3 shows that the PEM block of its targeted inputs is one that
the check rejects. The credentials of the control of row 1 are
`aws.AwsSecurityCredentials('AKIDEXAMPLE', 'secret')`.

### Each check

#### Row 1: `auth.aws.RequestSigner.get_request_options#1`, not reached

`aws.py:126`, `raise exceptions.InvalidResource("Invalid AWS service URL")`,
under `if not uri.hostname or uri.scheme != "https":` (line 125), in
`RequestSigner.get_request_options` (line 89).

The package calls `get_request_options` only at `aws.py:767`, in
`aws.Credentials.retrieve_subject_token` (line 717). Neither entry point takes
or builds a credentials object or a request signer: `jwt.decode` has the
parameters `token`, `certs`, `verify`, `audience` and `clock_skew_in_seconds`
(`jwt.py:234`), and `_jwt_async.decode` only calls it (`_jwt_async.py:94`).
None of the 21 functions that a call of `decode` can execute calls
`retrieve_subject_token` or `get_request_options`. A URL that a token carries
in its claims is only compared with the audience (`jwt.py:323`), never parsed:
T1 and T3 return the payload, T2 stops at `jwt.py:324`.

#### Row 2: `auth._agent_identity_utils.parse_certificate#1`, not reached

`_agent_identity_utils.py:329`,
`raise ValueError("Certificate bytes cannot be empty or None.")`, under
`if not cert_bytes:` (line 328), in `parse_certificate` (line 312).

The package calls `parse_certificate` only at `_agent_identity_utils.py:303`
and 438, `aio/transport/mtls.py:205`, `identity_pool.py:576` and
`transport/_mtls_helper.py:899`; none of these lines is in the 21 functions
that a call of `decode` can execute. A certificate that the caller gives as
`certs` (`jwt.py:285-297`) goes to `verifier_cls.from_string`
(`crypt/__init__.py:78`), which parses it with the `cryptography` package
(`crypt/_cryptography_rsa.py:76` and 82, through `crypt/rsa.py:73`;
`crypt/es.py:119` and 125). An empty certificate stops there, with a
`ValueError` of `cryptography` that reaches the caller (T1 to T5).

#### Row 3: `auth.crypt._python_rsa.RSASigner.from_string#1`, not reached

`crypt/_python_rsa.py:190`, `raise exceptions.InvalidValue("Unused bytes",
remaining)`, under `if remaining != b"":` (line 189), in the PKCS #8 branch
`elif marker_id == 1:` (line 187) of `RSASigner.from_string` (line 164).

Of the 21 functions that a call of `decode` can execute, 2 make a call named
`from_string`: `crypt/__init__.py:78` calls `verifier_cls.from_string`, where
`verifier_cls` is `rsa.RSAVerifier` or `es.EsVerifier` (`jwt.py:70`, 74-75 and
271; `crypt/__init__.py:53`) and no parameter of `decode` sets it; and
`crypt/rsa.py:73` calls `_cryptography_rsa.RSAVerifier.from_string`, after
building the object with `cls.__new__` (line 72), so that `RSAVerifier.__init__`
does not run. The module `_python_rsa` is imported only inside
`rsa.RSAVerifier.__init__` and `rsa.RSASigner.__init__` (`crypt/rsa.py:46` and
97), which no call of `decode` executes; it was not loaded after the inputs.
The PEM block that the check rejects (control of row 3), given as `certs`,
stops in `cryptography` at `crypt/_cryptography_rsa.py:82` or `crypt/es.py:125`
(T1 to T5).

#### Row 4: `auth.credentials.AnonymousCredentials.apply#1`, not reached

`credentials.py:606`,
`raise exceptions.InvalidValue("Anonymous credentials don't support tokens.")`,
under `if token is not None:` (line 605), in `AnonymousCredentials.apply`
(line 597).

Neither entry point takes a credentials object or a token for one
(`jwt.py:234`; `_jwt_async.py:71` and 94), and none of the 21 functions that a
call of `decode` can execute calls `apply`, `before_request` or `refresh`. The
chain of names by which the toolkit reaches the check (section below) passes
through `_credentials_async.Credentials.before_request` before `apply`, and
even there the call is `self.apply(headers)`, without a token
(`_credentials_async.py:73`, as `credentials.py:247` is);
`AnonymousCredentials.before_request` does nothing (`credentials.py:608-609`).

#### Row 5: `auth.credentials.AnonymousCredentials.refresh#1`, not reached

`credentials.py:595`,
`raise exceptions.InvalidOperation("Anonymous credentials cannot be refreshed.")`,
the whole body of `AnonymousCredentials.refresh` (line 592), with no guard: it
executes when and only when that method is called.

Neither entry point takes a credentials object (`jwt.py:234`;
`_jwt_async.py:71` and 94), and none of the 21 functions that a call of
`decode` can execute calls `refresh`.

### Why the toolkit counts these checks as reachable

`name_chains.py` applies the toolkit's own functions `functions`,
`referenced_names` and `plain_name` (`T/reach/checks.py`, imported unchanged) to
the subject files of the clone: a function refers to every name it calls and to
every attribute name it mentions, and a name stands for every function of that
name. From the 2 functions named `decode`, this closure holds 505 of the 892
functions of the subject files (`name_chains.txt`). A shortest chain to each of
the 5 checks:

| Row | Functions of the chain, with the name of each link (`name_chains.txt`) | The link that the source excludes |
|---|---|---|
| 1 | `jwt.decode` (`get`) `AsyncAuthorizedSession.get` (`request`) `AsyncAuthorizedSession.request` (`refresh`) `CredentialsWithRegionalAccessBoundary.refresh` (`_perform_refresh_token`) `external_account.Credentials._perform_refresh_token` (`retrieve_subject_token`) `aws.Credentials.retrieve_subject_token` (`get_request_options`) `RequestSigner.get_request_options` | the first: `get` at `jwt.py:267`, 268 and 320 is `dict.get` |
| 2 | `jwt.decode` (`get`) `AsyncAuthorizedSession.get` (`request`) `AsyncAuthorizedSession.request` (`check_parameters_for_unauthorized_response`) `aio/transport/mtls.check_parameters_for_unauthorized_response` (`parse_certificate`) `parse_certificate` | the first, as in row 1 |
| 3 | `jwt.decode` (`verify_signature`) `crypt.verify_signature` (`from_string`) `_python_rsa.RSASigner.from_string` | the second: `from_string` at `crypt/__init__.py:78` is `rsa.RSAVerifier.from_string` or `es.EsVerifier.from_string` |
| 4 | `jwt.decode` (`get`) `AsyncAuthorizedSession.get` (`request`) `AsyncAuthorizedSession.request` (`before_request`) `_credentials_async.Credentials.before_request` (`apply`) `AnonymousCredentials.apply` | the first, as in row 1 |
| 5 | `jwt.decode` (`get`) `AsyncAuthorizedSession.get` (`request`) `AsyncAuthorizedSession.request` (`refresh`) `AnonymousCredentials.refresh` | the first, as in row 1 |

`AsyncAuthorizedSession` is in `aio/transport/sessions.py`. The toolkit follows
names, not calls, and each chain holds a link that is no call; this is why
`sample.csv` has `reachable` = `yes` for these 5 checks although no call of
`decode` can execute them.

### Limits

- The 5 results rest on the source. The runs add that 29 to 34 inputs per
  check, which take every outcome of every condition of `decode` that this
  environment admits, entered none of the 5 functions.
- The arguments are of the types that the documentation of `decode` names
  (`jwt.py:237-251`): the token as str (as bytes in C02, which
  `_unverified_decode` accepts, `jwt.py:137` and 146), `certs` as str, bytes
  or a mapping of key ids to str or bytes, `verify` as bool, `audience` as str
  or list, `clock_skew_in_seconds` as int. An argument object with methods of its
  own (a subclass of str, a mapping with its own `__getitem__`) would run code
  of the caller rather than stand for an artifact or a setting, and is not an
  input through an entry point in the sense of section 4.4.
- The branch at `jwt.py:273-278` cannot be taken in this environment; it is on
  the way to none of the 5 checks.
- The inputs of 1 script share 1 fresh copy and 1 process. The digests of the
  78 subject files after each run show that the copy was not changed.

### Files

In `X/no-fire/reach/google-auth/`:

- `reach.csv`: 1 row per check, in the order of `sample.csv`, with the columns
  of section 4.4 (`library`, `check`, `result`, `entry_point`, `scripts`,
  `settings`, `exception`, `reason`) and those that the task adds (`input`,
  `fires`, `source_lines`).
- `1.py` to `5.py`: 1 script per check, named after its row of `sample.csv`.
  Each runs its targeted inputs, the census and its control and writes
  `<n>.json`: `python3 -I -B <n>.py`, from any folder.
- `reach_common.py`: the code that the 5 scripts share (copy, environment,
  artifacts, census, tracer).
- `1.json` to `5.json`: the record of each run (`inputs`, `control`,
  `functions_entered_by_the_inputs`, `google_modules_loaded_after_the_inputs`,
  `inputs_that_reach_the_check`, times, digests, command).
- `name_chains.py` and its output `name_chains.txt`.
- `READING.md`: this file.

In `X/work/reach/google-auth/`: `copy/` (the fresh copy of the last run),
`<n>.child.json` (the record of each child process) and `<n>.child.log` (its
output, empty).

The protocol names 1 file `no-fire/reach/reach.csv` and 1 file
`no-fire/reach/READING.md` for the 20 checks; the task asks for the files of
each library in `no-fire/reach/<library>/`, and this folder holds those of
google-auth.

## oauthlib


Rows 6 to 10 of `no-fire/sample.csv`, 5 of the 13 checks of `oauthlib` that
fire in no case (`PROTOCOL.md`, section 3.1, line 153), taken under `PROTOCOL.md`,
section 4.4, as step 5 of section 6. Paths of this experiment are relative to
the folder of `PROTOCOL.md`; `T` is `../target-reach`. Paths of the library
are relative to the root of a copy of `oauthlib` 4.0.1 at commit
`6e3aa05af92978755939a18cb4dd655ced156c1e`; every line number is a line of
that release.

### Result

All 5 checks are **reached**. For each, 1 input through an entry point makes
a raise statement of the check execute; the tracer records a firing of the
check under the test of the recorder; the exception reaches the caller, since
no handler of the package catches it on the way; and the raise statement of
the check is the raise site of that exception.

| Row | Check | Entry point | Input in short | Exception that reaches the caller |
|---|---|---|---|---|
| 6 | `oauth2.rfc6749.grant_types.authorization_code.AuthorizationCodeGrant.validate_token_request#9` | `AuthorizationCodeGrant.validate_token_request` | a token request of the authorization code grant without `redirect_uri`, from a client registered without a default redirect URI | `MissingRedirectURIError` (`invalid_request`, "Missing redirect URI.", 400) at `oauthlib/oauth2/rfc6749/grant_types/authorization_code.py:510` |
| 7 | `oauth2.rfc6749.endpoints.base.BaseEndpoint._raise_on_bad_method#1` | `TokenEndpoint.validate_token_request`, on a `WebApplicationServer` | a token request sent with GET | `InvalidRequestError` (`invalid_request`, "Unsupported request method GET", 400) at `oauthlib/oauth2/rfc6749/endpoints/base.py:79` |
| 8 | `oauth2.rfc6749.grant_types.base.GrantTypeBase.validate_grant_type#1` | `AuthorizationCodeGrant.validate_token_request` | a token request of the authorization code grant from a client allowed the client credentials grant only | `UnauthorizedClientError` (`unauthorized_client`, no description, 400) at `oauthlib/oauth2/rfc6749/grant_types/base.py:162` |
| 9 | `oauth2.rfc8628.grant_types.device_code.DeviceCodeGrant.validate_token_request#1` | `DeviceCodeGrant.validate_token_request` | a device access token request without `grant_type` | `InvalidRequestError` (`invalid_request`, "Request is missing grant type.", 400) at `oauthlib/oauth2/rfc8628/grant_types/device_code.py:125` |
| 10 | `oauth2.rfc8628.grant_types.device_code.DeviceCodeGrant.validate_device_code#3` | `DeviceCodeGrant.validate_token_request` | a device access token request with a device code of which the provider holds no record | `InvalidGrantError` (`invalid_grant`, no description, 400) at `oauthlib/oauth2/rfc8628/grant_types/device_code.py:202` |

`reach.csv` holds 1 row per check, in the order of the sample, with the
columns of section 4.4 (`library`, `check`, `result`, `entry_point`,
`scripts`, `settings`, `exception`, `reason`), followed by `row`, `input`,
`fired`, `record` and `source_lines`. `result` takes the words of section 4.4
(`reached`, `not reached`, `undecided`); `fired` says whether a RAISE event of
the call passed the firing test described below (`fires`, `does not fire`,
`undecided`). For all 5 rows, `result` is `reached` and `fired` is `fires`.

### What was done (times in UTC)

- 15:29Z. `PROTOCOL.md` read in full. The 2 time-stamp tokens of the protocol
  commit `0796d80a8b34fe2915f48fd92c1485735b2a6fec` (committed at 15:27:46Z;
  the tokens committed in `d36893e29f3fec7a83b33a20778fe06a8c40ff95` at
  15:28:05Z) verified with the commands of `timestamps/README.md`, lines
  25-29: `Verification: OK` for the token of freetsa.org and for that of
  DigiCert, both with the time `Nov 17 15:27:56 2026 GMT`. The source of the
  library was opened, and the inputs were sought and run, after this.
- 15:35:25Z. `verify` of the toolkit, unchanged:
  `python3 -I -B T/reach/run.py verify --subject T/subjects/oauthlib/subject.json
  --clone T/work/src/oauthlib --python T/work/venvs/oauthlib/bin/python
  --work work/reach/oauthlib/verify`. Output: `verify: commit 6e3aa05af929,
  75 subject files and 8 test files match, CPython 3.12.3`; exit status 0.
  `verify` also checks that the installed packages are those of
  `T/subjects/oauthlib/requirements.txt` and that the library itself is not
  installed in the environment (first protocol, `T/PROTOCOL.md`, lines
  269-278).
- 15:40:23Z. `6.py` run once. Its record was then replaced, because
  `trace_input.py` was changed to give paths relative to the root of the
  repository and to record the environment of the process; the input, the
  result (reached, raise line 510 executed, the check fired) and the exception
  (`MissingRedirectURIError` at line 510) were the same as in the run below.
- 15:48:31Z. `6.py` to `10.py` run, 1 after the other, each on its own fresh
  copy `work/reach/oauthlib/copy/<n>`; each started and ended within that
  second and exited with status 0 (reached). These runs wrote the records
  `<n>.record.json`.
- 15:53:08Z. `reach_csv.py` wrote `reach.csv` from the 5 records. It checks
  the SHA-256 of the sample against `no-fire/README.md` and the check and row
  of each record against the sample.
- 15:53:58Z. `git status` with `GIT_OPTIONAL_LOCKS=0`, which writes nothing:
  no change under `T`, in `no-fire/sample.csv` or in `PROTOCOL.md`; the
  clone has no changed, untracked or ignored file in the paths `oauthlib` and
  `tests` and is at `6e3aa05af92978755939a18cb4dd655ced156c1e`; the copies
  lie under `work/`, which `.gitignore` (line 1) leaves out.
- 15:55:17Z. This file written; then read again against the source, the
  records, the tests of the library and the protocol, and corrected, until
  16:05:54Z. No script was run again and no record changed after 15:53:08Z.

### How each input is run

Each script `<n>.py` holds the input for row `<n>` and calls `main` of
`trace_input.py`. The scripts were run with the interpreter of the first
study:

```sh
env -i PATH=T/work/venvs/oauthlib/bin:/usr/bin:/bin HOME="$HOME" LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    T/work/venvs/oauthlib/bin/python -I -B no-fire/reach/oauthlib/<n>.py
```

`main` does, in this order:

1. reads row `<n>` of the sample and the definition of its check in
   `T/subjects/oauthlib/checks.json` (raise statements, class, function), and
   stops when the file and the function of the sample differ from it;
2. checks that the interpreter is CPython 3.12.3 from the environment
   `T/work/venvs/oauthlib` (record: `interpreter`);
3. checks the clone `T/work/src/oauthlib` with the git commands of `verify`
   (`T/reach/run.py`, lines 211-226), with `GIT_OPTIONAL_LOCKS=0`: at the
   commit of `subject.json`, and no changed, untracked or ignored file in the
   paths that a copy takes (record: `clone`);
4. makes the copy `work/reach/oauthlib/copy/<n>` anew: the paths `oauthlib`
   and `tests` of `subject.json`, without `__pycache__`, `*.pyc` and
   `.pytest_cache`, as `make_copy` of `T/reach/run.py` makes it (lines
   310-322), and checks the SHA-256 of the 75 subject files against
   `checks.json`, as `make_copy_check` does (lines 325-330) (record: `copy`);
5. puts the copy first on `sys.path` and imports the package from it (record:
   `copy.package_imported_from`); then the script builds, from the copy, the
   argument and the object that receives the call: an `oauthlib.common.Request`
   for the HTTP request received from the client, and the grant or the
   pre-configured server with its request validator, by the library's
   documented constructors. A request validator of a script is a subclass of
   the library's `RequestValidator`, the documented parameter for these
   settings. It gives its own answers only for methods that the library
   leaves to the provider (they raise `NotImplementedError`, "Subclasses must
   implement this method."); where it overrides a method that has a default,
   it calls the library's method and returns its answer unchanged. It logs
   the answer of each method that it overrides (record: `validator_calls`).
   Nothing of the package, of its dependencies or of its tests is changed,
   patched or replaced;
6. makes the 1 call of the entry point with the tracer on, and with it off
   before and after. The tracer is `sys.monitoring` of Python 3.12, tool id 3
   (4 when 3 is taken), with LINE and RAISE events: LINE records every line of
   the package that executes during the call (record: `lines_executed`), and
   RAISE every exception raised in, or passing through, a frame of the
   package (record: `raise_events`). A RAISE event is a firing of the check
   under the test of `on_raise` in `T/reach/recorder.py` (lines 237-270): the
   instruction at its offset is `RAISE_VARARGS`, its line is a line of a raise
   statement of the check, and the class of the exception has the check's
   class name;
7. takes the exception that reaches the caller and its raise site, the
   innermost frame of its traceback inside the package directory, as `site`
   of `T/reach/recorder.py` takes it (lines 194-210), with the check whose
   raise statement holds that line (record: `exception`, `decides`);
8. writes `<n>.record.json`.

The check is reached when a line of 1 of its raise statements executes during
the call (record: `raise_lines_executed`, `result`).

In the records of rows 7, 8 and 10, a second RAISE event follows the firing,
at the line of the call in the calling frame of the package
(`oauthlib/oauth2/rfc6749/endpoints/token.py:118`,
`oauthlib/oauth2/rfc6749/grant_types/authorization_code.py:460`,
`oauthlib/oauth2/rfc8628/grant_types/device_code.py:147`). It is the same
exception passing through that frame: its instruction is no `RAISE_VARARGS`
(the record names it `CACHE`), so it is no firing, as the recorder leaves
such events out (`T/reach/recorder.py`, lines 238-242).

**Environment of the process.** The variables are those that the toolkit
gives a pytest call (`T/reach/run.py`, lines 155-165: `PATH` with the
environment's `bin` first, then `/usr/bin:/bin`; `HOME`; `LANG=C.UTF-8`;
`LC_ALL=C.UTF-8`; `PYTHONHASHSEED=0`; `PYTHONDONTWRITEBYTECODE=1`), apart
from the 2 `PYTHON*` variables: `-B` has
the effect of `PYTHONDONTWRITEBYTECODE=1`, and `-I` makes Python ignore every
`PYTHON*` variable, so string hashing was randomized in these runs (record:
`interpreter.hash_randomization` is `true`; `interpreter.environment_variables`
lists `HOME`, `LANG`, `LC_ALL` and `PATH`). The first protocol asks these
variables, and the offline module `T/guard/reach_offline.py`, of every pytest
call (`T/PROTOCOL.md`, lines 278-280 and 289-296); these runs call no pytest,
and the offline module, a pytest plugin (`T/reach/run.py`, lines 52-55 and
91-92), was not loaded. A result `reached` rests on a line that executed in
the recorded run.

### The 5 checks

#### Row 6: `AuthorizationCodeGrant.validate_token_request#9`

- **Check.** `raise errors.MissingRedirectURIError(request=request)` at
  `oauthlib/oauth2/rfc6749/grant_types/authorization_code.py:510`.
- **Entry point.** `AuthorizationCodeGrant.validate_token_request`
  (`authorization_code.py:436`), called on an `AuthorizationCodeGrant` built
  with the request validator of `6.py`.
- **Input.** `POST https://server.example.com/token`, with the HTTP Basic
  credentials of the client `s6BhdRkqt3` and the body
  `grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA`, without
  `redirect_uri`. By the provider's records in `6.py`, the code was issued to
  this client by an authorization request without `redirect_uri`, and the
  client is registered without a default redirect URI.
- **Settings that are not the default.** The grant gets no argument besides
  the request validator. The validator answers, from the records of the
  script, `authenticate_client` (True, after it sets `request.client`),
  `validate_grant_type` (True), `validate_code` (True; it sets `request.user`
  and `request.scopes`) and `get_default_redirect_uri` (None); the library has
  no default for these 4 (`oauthlib/oauth2/rfc6749/request_validator.py`,
  lines 81, 499, 481 and 143 raise `NotImplementedError`).
  `client_authentication_required`, `get_code_challenge` and
  `is_pkce_required` keep the library's answers (True, None and False: lines
  39, 645 and 616).
- **Path, from the source and the trace.** In `authorization_code.py`: 442
  `grant_type` is `authorization_code`; 445 no `pre_token` validator; 448 a
  code is present; 452-453 no duplicate `client_id`, `grant_type` or
  `redirect_uri`; 457 client authentication passes
  (`oauthlib/oauth2/rfc6749/grant_types/base.py` 223-224:
  `client_authentication_required` answers True; then 184-196:
  `authenticate_client` answers True, `request.client` has a `client_id`, and
  `request.client_id` is taken from it at 196); 460 `validate_grant_type`
  passes (`base.py` 157-159); 464-465 `validate_code` answers True; 471
  `get_code_challenge` answers None, so 473 skips the PKCE tests; 492
  `is_pkce_required` answers False; 497-498 `request.user` and
  `request.scopes` are set; 504 the request carries no `redirect_uri`, so
  505-507 ask `get_default_redirect_uri`, which answers None; 508 log; 509 no
  redirect URI; 510 raise. The comment at 501-503 gives the rule: "REQUIRED,
  if the "redirect_uri" parameter was included in the authorization request
  as described in Section 4.1.1, and their values MUST be identical."
- **Calls of the validator, in order.** `client_authentication_required`
  True, `authenticate_client` True, `validate_grant_type` True,
  `validate_code` True, `get_code_challenge` None, `is_pkce_required` False,
  `get_default_redirect_uri` None.
- **Exception that reaches the caller.**
  `oauthlib.oauth2.rfc6749.errors.MissingRedirectURIError`, a subclass of
  `InvalidRequestFatalError` (`errors.py` 157-163 and 170-171): error
  `invalid_request`, description "Missing redirect URI.", status 400. Raise
  site `authorization_code.py:510`, the check itself; 1 RAISE event, the
  firing.
- **Record.** `6.record.json`.

#### Row 7: `BaseEndpoint._raise_on_bad_method#1`

- **Check.** `raise InvalidRequestError(request=request,
  description=('Unsupported request method %s' %
  request.http_method.upper()))` at
  `oauthlib/oauth2/rfc6749/endpoints/base.py:79-80`.
- **Entry point.** `TokenEndpoint.validate_token_request`
  (`oauthlib/oauth2/rfc6749/endpoints/token.py:117`), called on a
  `WebApplicationServer`
  (`oauthlib/oauth2/rfc6749/endpoints/pre_configured.py:96`), which inherits
  it.
- **Input.** `GET
  https://server.example.com/token?grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA`,
  without a body.
- **Settings that are not the default.** None. The server is built as
  `WebApplicationServer(RequestValidator())` with the library's
  `RequestValidator`, unchanged; the call reaches none of its methods (the
  record holds no line of a `request_validator.py`). The caller does not set
  `valid_request_methods`.
- **Path, from the source and the trace.** `token.py` 118 calls
  `_raise_on_bad_method`. `base.py` 76 reads `self.valid_request_methods`. On
  a `WebApplicationServer` the name resolves to the class attribute
  `('POST',)` of `IntrospectEndpoint`
  (`oauthlib/oauth2/rfc6749/endpoints/introspect.py:39`): the method
  resolution order is `WebApplicationServer`, `AuthorizationEndpoint`,
  `IntrospectEndpoint`, `TokenEndpoint`, `ResourceEndpoint`,
  `RevocationEndpoint`, `BaseEndpoint`, `object`, and the classes in it that
  define the name are `IntrospectEndpoint`, `TokenEndpoint` (`token.py:61`)
  and `RevocationEndpoint` (`revocation.py:28`), each with `('POST',)`, and
  `BaseEndpoint` with a property (`base.py` 26-28) (record: `facts`, read
  from the class dictionaries, so that no function of the package ran). The
  property is therefore not used (the trace has no line of it), the value is
  not None, and the `ValueError` of `base.py:77` is not raised (it is no
  check: `T/subjects/oauthlib/checks.json` lists it among `other_raises`, as
  not a rejection class). 78: `GET` is not in `('POST',)`; 79-80 raise.
- **Exception that reaches the caller.**
  `oauthlib.oauth2.rfc6749.errors.InvalidRequestError`: error
  `invalid_request`, description "Unsupported request method GET", status
  400. Raise site `base.py:79`, the check itself. The second RAISE event, at
  `token.py:118`, is the exception passing through the frame of the entry
  point.
- **Record.** `7.record.json`.

#### Row 8: `GrantTypeBase.validate_grant_type#1`

- **Check.** `raise errors.UnauthorizedClientError(request=request)` at
  `oauthlib/oauth2/rfc6749/grant_types/base.py:162`.
- **Entry point.** `AuthorizationCodeGrant.validate_token_request`
  (`oauthlib/oauth2/rfc6749/grant_types/authorization_code.py:436`), which
  calls `GrantTypeBase.validate_grant_type` at 460. The 4 other grants call it
  from their own `validate_token_request` too
  (`client_credentials.py:109`, `refresh_token.py:98`,
  `resource_owner_password_credentials.py:180`, and
  `oauthlib/oauth2/rfc8628/grant_types/device_code.py:141`).
- **Input.** `POST https://server.example.com/token`, with the HTTP Basic
  credentials of the client `s6BhdRkqt3` and the body
  `grant_type=authorization_code&code=SplxlOBeZQQYbYS6WxSbIA&redirect_uri=https%3A%2F%2Fclient.example.com%2Fcb`.
  By the provider's records in `8.py`, the client is allowed the client
  credentials grant only.
- **Settings that are not the default.** The grant gets no argument besides
  the request validator. The validator answers `authenticate_client` (True,
  after it sets `request.client`) and `validate_grant_type` (False); the
  library has no default for these 2 (`request_validator.py`, lines 81 and
  499). `client_authentication_required` keeps the library's answer, True
  (line 39).
- **Path, from the source and the trace.** In `authorization_code.py`: 442,
  445, 448 and 452-453 as in row 6; 457 client authentication passes as in
  row 6 (`base.py` 223-224 and 184-196); 460 calls `validate_grant_type`
  (`base.py:152`): 157 `client_id`; 158-159 the validator answers False for
  the grant type `authorization_code`; 160-161 log; 162 raise.
- **Calls of the validator, in order.** `client_authentication_required`
  True, `authenticate_client` True, `validate_grant_type` False.
- **Exception that reaches the caller.**
  `oauthlib.oauth2.rfc6749.errors.UnauthorizedClientError`: error
  `unauthorized_client`, description empty (the class sets none,
  `errors.py` 305-310, and `OAuth2Error.description` is `''`, line 18),
  status 400. Raise site `base.py:162`, the check itself. The second RAISE
  event, at `authorization_code.py:460`, is the exception passing through the
  frame of the entry point.
- **Record.** `8.record.json`.

#### Row 9: `DeviceCodeGrant.validate_token_request#1`

- **Check.** `raise rfc6749_errors.InvalidRequestError("Request is missing
  grant type.", request=request)` at
  `oauthlib/oauth2/rfc8628/grant_types/device_code.py:125-127`.
- **Entry point.** `DeviceCodeGrant.validate_token_request`
  (`device_code.py:116`), called on a `DeviceCodeGrant` built with the
  library's request validator of the device flow.
- **Input.** `POST https://server.example.com/token`, with the body
  `device_code=GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS&client_id=1406020730`
  and no `grant_type`. The device code is that of the example response in
  `oauthlib/oauth2/rfc8628/endpoints/device_authorization.py:173`, the client
  identifier that of `examples/device_code_flow.py:76` of the clone.
- **Settings that are not the default.** The request validator is the
  library's `oauthlib.oauth2.rfc8628.request_validator.RequestValidator`,
  unchanged, where the grant's default would be the `RequestValidator` of
  rfc6749 (`oauthlib/oauth2/rfc6749/grant_types/base.py:83`); the call reaches
  none of its methods. No other argument.
- **Path, from the source and the trace.** In `device_code.py`: 121 no
  `pre_token` validator; 124 `getattr(request, "grant_type", None)` is None:
  the body carries no `grant_type`, and a `Request` answers None for a
  parameter that it knows and that the request does not carry
  (`oauthlib/common.py` 360-397 and 399-401); 125-127 raise. Lines 125 and
  126 executed; line 127 holds only the closing parenthesis and has no line
  event.
- **Exception that reaches the caller.**
  `oauthlib.oauth2.rfc6749.errors.InvalidRequestError`: error
  `invalid_request`, description "Request is missing grant type.", status
  400. Raise site `device_code.py:125`, the check itself; 1 RAISE event, the
  firing.
- **Record.** `9.record.json`.

#### Row 10: `DeviceCodeGrant.validate_device_code#3`

- **Check.** `raise rfc6749_errors.InvalidGrantError(request=request)` at
  `oauthlib/oauth2/rfc8628/grant_types/device_code.py:202`.
- **Entry point.** `DeviceCodeGrant.validate_token_request`
  (`device_code.py:116`), which calls `DeviceCodeGrant.validate_device_code`
  at 147.
- **Input.** `POST https://server.example.com/token`, with the HTTP Basic
  credentials of the client `1406020730` and the body
  `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code&device_code=GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS`.
  By the provider's records in `10.py`, the client is confidential and allowed
  the device flow, and no device code is on record.
- **Settings that are not the default.** The grant gets no argument besides
  the request validator, a subclass of the library's request validator of the
  device flow. It answers `authenticate_client` (True, after it sets
  `request.client`), `validate_grant_type` (True) and `validate_device_code`
  (None); the library has no default for these 3
  (`oauthlib/oauth2/rfc6749/request_validator.py`, lines 81 and 499;
  `oauthlib/oauth2/rfc8628/request_validator.py`, line 63). None is the answer
  that the library documents for this case
  (`oauthlib/oauth2/rfc8628/request_validator.py`, lines 49-50: "Returning
  ``None`` (or any unrecognized value) is treated as an unknown or invalid
  ``device_code`` and raises ``InvalidGrantError``."). The validator keeps
  the library's `client_authentication_required`, True (line 25).
- **Path, from the source and the trace.** In `device_code.py`: 121 no
  `pre_token` validator; 124 `grant_type` is present; 129 it is
  `urn:ietf:params:oauth:grant-type:device_code`; 132-133 no duplicate
  `grant_type` or `scope`; 138 client authentication passes
  (`oauthlib/oauth2/rfc6749/grant_types/base.py` 223-224 and 184-196); 141
  `validate_grant_type` passes (`base.py` 157-159); 147 calls
  `validate_device_code`: 164 a device code is present; 169-171 the
  validator answers None; 172 None is not `"authorized"`; 189 the map of the
  4 recognized statuses (lines 20-28) has no entry for None, so 190 does not
  raise; 196 the status is None, so nothing is logged; 202 raise.
- **Calls of the validator, in order.** `client_authentication_required`
  True, `authenticate_client` True, `validate_grant_type` True,
  `validate_device_code` None.
- **Exception that reaches the caller.**
  `oauthlib.oauth2.rfc6749.errors.InvalidGrantError`: error `invalid_grant`,
  description empty (`errors.py` 292-302), status 400. Raise site
  `device_code.py:202`, the check itself. The second RAISE event, at
  `device_code.py:147`, is the exception passing through the frame of the
  entry point.
- **Record.** `10.record.json`.

### Notes

- **Row 7 and section 5 of the protocol.** Row 7 is 1 of the 2 checks that
  section 5 names (lines 532-538). Of the 2 tests that section 5 cites, the
  one that asserts the message of this check is `test_invalid_request_method`
  (`tests/oauth2/rfc6749/endpoints/test_error_responses.py`, lines 440-466;
  its assertions, `self.assertIn('Unsupported request method',
  ire.description)`, are at lines 452, 459 and 466). It calls
  `create_token_response` of a `WebApplicationServer`, a
  `LegacyApplicationServer` and a `BackendApplicationServer` (built at lines
  27, 29 and 30), with the methods `GET`, `pUt`, `dEleTe` and `paTcH` as
  written, in lower case and in upper case (lines 441-442).
  `create_token_response` is not an entry point of `subject.json` by name,
  and it calls the entry point `validate_token_request` at `token.py:92`. The
  input of `7.py` calls the entry point itself, on the class of the test's
  first server.
- **Row 9 and the pre-configured servers.** From the source, not run: the
  token endpoint of the pre-configured `Server` sends a token request
  without `grant_type` to its default grant (`token.py` 77-79 and 110-111),
  which is the authorization code grant (`pre_configured.py` 79 and 81); that
  grant rejects it with `UnsupportedGrantTypeError` (`authorization_code.py`
  442-443), and its `create_token_response` returns the error response
  (285-307). The device grant's own `create_authorization_response`
  (`device_code.py` 38-59) and `create_token_response` (204-233), whose names
  are not entry points, call `validate_token_request` and turn an
  `OAuth2Error` into an error response (48-50 and 225-227). The input of
  `9.py` calls the entry point of the device grant itself, which section 4.4
  counts as an input through an entry point.
- **Where these files are.** Section 4.4 names 1 `no-fire/reach/reach.csv`
  and 1 `no-fire/reach/READING.md` for the 20 checks. The table and this file
  are in `no-fire/reach/oauthlib/`, beside the scripts, for the 5 checks of
  `oauthlib`; the 8 columns of section 4.4 come first in `reach.csv`, so that
  its rows can be put in the one table unchanged.

### Files

In `no-fire/reach/oauthlib/`:

- `6.py`, `7.py`, `8.py`, `9.py`, `10.py`: the input of each check, named
  after its row in the sample;
- `trace_input.py`: what the 5 scripts share (the checks of the interpreter
  and the clone, the copy, the tracer, the record);
- `6.record.json` to `10.record.json`: the record of each run (times, input,
  settings, calls of the validator, lines executed in the package, RAISE
  events, the exception that reaches the caller and its traceback);
- `reach_csv.py` and `reach.csv`: the table, written from the records;
- `READING.md`: this file.

In `work/reach/oauthlib/` (left out by `.gitignore`): `verify/local.json`,
written by `verify`, and the copies `copy/6` to `copy/10` of the last runs.

## authlib


Step 5 of `PROTOCOL.md` (section 6) for the library `authlib`, under
definition 4.4. Paths are relative to `experiments/target-reach-extension/`;
`../target-reach/` is the toolkit of the first study. A path that starts with
`authlib/`, `docs/`, `tests/` or `README.md` is a path of the release: the
clone `../target-reach/work/src/authlib` at commit
`42607cbc2135252a641a845e4ed7f94e3a922c47` (Authlib 1.9.5, tag `v1.9.5`),
which this task only read. All times are UTC, on 2026-11-17.

Files that define the task, read before anything was run:

| file | SHA-256 |
|---|---|
| `PROTOCOL.md` (commit `0796d80a8b34fe2915f48fd92c1485735b2a6fec`, 15:27:46Z) | `3005f7e6402790ccf748b08e2474743b5fff8c0f7a8932444b29e84c58e38315` |
| `no-fire/sample.csv` | `5637e6bc9241273992552eb79331b9e5095ee5c8e8b291afc718f2efeea3a8fa` |
| `../target-reach/subjects/authlib/subject.json` | `4e2f930de9e1eb94358c32ea60e5f992ad36d1f44b8ed6a0bb491985c1c35af8` |
| `../target-reach/subjects/authlib/checks.json` | `3208594ee8627cfe505c022cf74a491b367668769e232cfca30d933fffb4c7d0` |
| `../target-reach/reach/checks.py` | `174c90a10df577f1f8f7bec1c0798ba00c7d3155e31fe63d14f740dc8b51bf26` |

The entry points of `subject.json` are names: `decode`, `deserialize`,
`deserialize_compact`, `deserialize_json` and `validate`. The package has 18
functions with these names: 3 of `JsonWebSignature`, 3 of
`JsonWebEncryption`, `JsonWebToken.decode` and 11 methods `validate`
(`no-fire/reach/authlib/name-paths.txt`, lines 8-26).

### Results

| row | check | result | entry points of the inputs | raise lines executed | exception that reaches the caller |
|---|---|---|---|---|---|
| 11 | `jose.rfc7515.jws.JsonWebSignature._validate_crit_headers#1` | reached | `JsonWebSignature.deserialize_compact` (a); `JsonWebToken.decode`, as `authlib.jose.jwt.decode` (b) | 303 in a and b | `InvalidHeaderParameterNameError`, from `authlib/jose/rfc7515/jws.py:303` |
| 12 | `jose.drafts._jwe_algorithms.ECDH1PUAlgorithm.generate_keys_and_prepare_headers#1` | not reached | none | none | none from the check (supporting run a: `UnsupportedAlgorithmError`, from `authlib/jose/rfc7516/jwe.py:701`) |
| 13 | `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#3` | reached | `JsonWebSignature.deserialize_json` (a); `JsonWebSignature.deserialize` (b) | 326 in a and b | `DecodeError`, from `authlib/jose/rfc7515/jws.py:326` |
| 14 | `jose.rfc7517.base_key.Key.check_key_op#1` | reached | `JsonWebSignature.deserialize_compact` (a); `JsonWebEncryption.deserialize_compact` (b, c) | 85 in a; 88 in b and c | `InvalidUseError`, from `authlib/jose/rfc7517/base_key.py:85` (a) and `:88` (b, c) |
| 15 | `jose.rfc7516.jwe.JsonWebEncryption.get_header_zip#1` | reached | `JsonWebEncryption.deserialize_compact` (a, b); `JsonWebEncryption.deserialize` (c); `JsonWebToken.decode` (d) | 730 in a and c; 728 in b and d | `UnsupportedCompressionAlgorithmError`, from `authlib/jose/rfc7516/jwe.py:730` (a, c) and `:728` (b, d) |

4 checks reached, 1 not reached, 0 undecided. In every input that reached its
check, the exception raised there is the one that reaches the caller: its
raise site, the innermost frame of the traceback inside the copy, is the line
of the check. The table with the columns of 4.4 is
`no-fire/reach/authlib/reach.csv`.

### What was done

- 15:29:16Z: start. Read `PROTOCOL.md` in full, the 5 rows of `authlib` in
  `no-fire/sample.csv`, `subject.json`, `checks.json`,
  `../target-reach/reach/checks.py` and, in `../target-reach/reach/run.py`,
  `make_copy` and `make_copy_check` (lines 310-330) and the environment of the
  pytest calls (lines 155-165).
- 15:35:17Z: `../target-reach/reach/run.py verify`, unchanged, on the clone and
  the environment, with its work folder `work/reach/authlib/verify`: "commit
  42607cbc2135, 215 subject files and 3 test files match, CPython 3.12.3"
  (`work/reach/authlib/verify.log`, whose stamps are local time, UTC+1).
- 15:35:52Z: `no-fire/reach/authlib/name-paths.py` wrote `name-paths.txt`.
  With the toolkit's `checks.py`, imported and not changed, it gives the chain
  by name from an entry point to each check and every function that refers to
  the name of the function of each check: 1301 functions, 510 reachable by
  name, and each of the 5 checks reachable by name, as `checks.json` says.
- 15:39:35Z: a trial run of an earlier `11.py`
  (`work/reach/authlib/11.trial.json`); not a result.
- 15:52:04Z-15:52:06Z: a run of `11.py` to `15.py`, superseded. Its outputs
  lost the name of each input (the description of the input was written under
  the same key). The shared harness was fixed (the key is now `name`); the
  scripts, outputs and error files of that run are kept in
  `work/reach/authlib/superseded-1552/`.
- 15:52:46Z-15:52:47Z: run of `11.py` to `15.py`; final for rows 11 to 14.
- 16:02:09Z: run of `15.py` with input d added (and the docstring and settings
  of b and d stated with their sources); final for row 15. The script, output
  and error file of the 15:52:47Z run, with inputs a to c, are kept in
  `work/reach/authlib/superseded-15-before-d/`; its results for a, b and c are
  the same as those of the final run.
- 16:06:22Z: `reach.csv`, corrected at 16:10:20Z (the number of `validate`
  methods in row 12 is 11, not 10); then this file.

Each command, with its start, end and exit status, is in
`work/reach/authlib/commands.tsv`. Every run ended with status 0 and wrote
nothing on its own standard error (the files `work/reach/authlib/<n>.err` are
empty).

### Method, and how it meets 4.4

Each script `no-fire/reach/authlib/<n>.py`, where `<n>` is the row of its check
in `no-fire/sample.csv`, runs all the inputs of the check, each on its own
fresh copy:

1. It makes a fresh copy of the release in `work/reach/authlib/copy`, as
   `make_copy` makes one (`../target-reach/reach/run.py`, lines 310-330): the
   paths of `copy` in `subject.json` (`authlib`, `tests`, `pyproject.toml`),
   without `__pycache__`, `*.pyc` and `.pytest_cache`. It stops unless all 215
   subject files of the copy have the SHA-256 that `checks.json` gives them.
2. It runs the input in a new interpreter of the environment of the first
   study, `../target-reach/work/venvs/authlib/bin/python` (CPython 3.12.3 and
   cryptography 50.0.2, as each output records), with `-I -B`, from the copy,
   with the copy first on `sys.path` and the environment variables of the
   toolkit's pytest calls (`PATH`, `HOME`, `LANG` and `LC_ALL` set to
   `C.UTF-8`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`; `run.py`, lines
   155-165). The child stops unless `authlib` is imported from the copy; each
   output records the file it was imported from.
3. In the child, the artifact (a token or a JSON text) and the keys are built
   with the standard library and `cryptography` only, without any function of
   the package. A tracer (`sys.settrace`) records each execution of a line of a
   raise statement of the check in the copy's file, the functions of that file
   that are entered and the number of line events in it. The entry point is
   then called, and what reaches the caller is recorded: the exception, with
   its class, its text and its raise site, or the value returned.

Each input calls a method with the name of an entry point (`decode`,
`deserialize`, `deserialize_compact` or `deserialize_json`) with a token or a
text that stands for an artifact received from another party. The settings
are those a caller gives through the documented parameters of the library:
the key, which has no default; the constructor of the class whose method is
called (`JsonWebSignature`, `JsonWebEncryption` or `JsonWebToken`, with
`algorithms`); and, in row 12, `sender_key`. Keys are passed as bytes or as JWK
dicts, never through a function of the package. Apart from importing
`authlib.jose` and constructing that instance, no function of the package is
called directly, and nothing of the package, its dependencies, its tests, the
toolkit or the sample was changed. A setting that is not the default is
listed with its input, in the output and in `reach.csv`. The one run that does
not meet 4.4 (row 12, run b) says so in its output (`"within_4_4": false`,
with the reason), and the field `reached` of each output counts only the
inputs that meet 4.4.

The recorder of `../target-reach/reach/` was not used; the tracer is the
instrument. Importing `authlib.jose` emits the package's warning
"AuthlibDeprecationWarning: authlib.jose module is deprecated, please use
joserfc instead." (`authlib/jose/__init__.py`, lines 34-36), which each output
keeps in the field `stderr` of each input.

### Row 11: `JsonWebSignature._validate_crit_headers#1`, reached

The check is `raise InvalidHeaderParameterNameError("crit")` at
`authlib/jose/rfc7515/jws.py:303`, under the guard of lines 300-302: the
protected header holds "crit" (line 297) and its value is not a list of
strings.

- a: `JsonWebSignature().deserialize_compact(token, key)`, with a compact JWS
  whose protected header is `{"alg":"HS256","crit":"kid","kid":"k1"}` ("crit"
  a string), signed with HMAC-SHA-256 under the key, a 32-byte secret.
  `deserialize_compact` (line 81) decodes the protected header (line 102) and
  calls `_validate_crit_headers` (line 103) before the key is prepared and the
  signature verified (lines 112-113).
- b: the same token and key through `authlib.jose.jwt.decode(token, key)`. The
  package's own `JsonWebToken` (`authlib/jose/__init__.py`, lines 55-72) passes
  a text with 2 dots to `JsonWebSignature.deserialize_compact`
  (`authlib/jose/rfc7519/jwt.py`, lines 101-104).

Recorded (`11.json`): line 303 executed once in a (14 line events in the file)
and once in b (12). `InvalidHeaderParameterNameError`,
"invalid_header_parameter_name: Invalid Header Parameter Name: crit", raised in
`JsonWebSignature._validate_crit_headers` at line 303, reaches the caller in
both. No setting differs from the default.

### Row 12: `ECDH1PUAlgorithm.generate_keys_and_prepare_headers#1`, not reached

The check is `raise InvalidEncryptionAlgorithmForECDH1PUWithKeyWrappingError()`
at `authlib/jose/drafts/_jwe_algorithms.py:127`, under the guard of line 126
(the content encryption algorithm is not a `CBCHS2EncAlgorithm`), in
`ECDH1PUAlgorithm.generate_keys_and_prepare_headers` (line 125). The method
prepares the keys and headers of a message that is being encrypted. The source
shows that no input through an entry point can make line 127 run:

1. Only the encrypting methods call it. In the whole package the name
   `generate_keys_and_prepare_headers` is referred to only at
   `authlib/jose/rfc7516/jwe.py:116`, in `JsonWebEncryption.serialize_compact`,
   and at `jwe.py:335`, in `JsonWebEncryption.serialize_json`
   (`name-paths.txt`, lines 51-53), besides its definitions
   (`drafts/_jwe_algorithms.py:125`, `authlib/jose/rfc7516/models.py:42`) and 2
   comments (`jwe.py`, lines 105 and 313). Both calls are under the condition
   that the algorithm is a `JWEAlgorithmWithTagAwareKeyAgreement` with a key
   size (`jwe.py`, lines 108-111 and 326-329), and the only subclass of that
   class is `ECDH1PUAlgorithm` (`drafts/_jwe_algorithms.py:16`;
   `authlib/jose/rfc7516/models.py:36`).
2. No entry point reaches the encrypting methods. In the whole package,
   `serialize_compact` and `serialize_json` of `JsonWebEncryption` are called
   only by `JsonWebEncryption.serialize` (`jwe.py`, lines 443 and 445) and by
   `JsonWebToken.encode` (`authlib/jose/rfc7519/jwt.py:76`; line 78 is the
   branch of `JsonWebSignature`). No module of the package refers to the name
   `serialize`. No module calls `JsonWebToken.encode`: the package constructs
   1 `JsonWebToken`, `authlib.jose.jwt` (`authlib/jose/__init__.py`, lines
   55-72); inside `authlib/jose` the only call of a method named `encode` is
   `padded_hex.encode` (`authlib/jose/rfc7518/util.py:7`), on a string; outside
   `authlib/jose` the package imports from it only 4 key classes
   (`authlib/_joserfc_helpers.py`, lines 13-16), and its 7 calls of
   `jwt.encode` are those of joserfc (`from joserfc import jwt` at
   `authlib/oauth2/rfc7523/assertion.py:3`, `authlib/oauth2/rfc7523/token.py:3`,
   `authlib/oauth2/rfc9068/token.py:3`, `authlib/oidc/core/grants/code.py:12`,
   `authlib/oidc/core/grants/implicit.py:4`,
   `authlib/oidc/core/grants/util.py:3` and `authlib/oidc/core/userinfo.py:1`,
   with the calls at lines 53, 83, 212, 87, 171, 144 and 80 of the same files).
   The toolkit counts the check as reachable through a chain by name
   (`name-paths.txt`, lines 40-50): `JsonWebSignature.deserialize`
   (`authlib/jose/rfc7515/jws.py:239`), `to_bytes` (`jws.py:255`), the name
   `encode` (`authlib/common/encoding.py`, lines 12 and 14),
   `JsonWebToken.encode`, `JsonWebEncryption.serialize_compact`, line 116. The
   link at `encoding.py` is `str.encode`: line 12 runs only when `x` is a `str`
   (line 11), and line 14 calls `encode` on `str(x)`. The entry points that
   decrypt (`JsonWebEncryption.deserialize_compact`, `deserialize_json` and
   `deserialize`, and `JsonWebToken.decode` for a text with 4 dots) unwrap the
   content key with `alg.unwrap` (`jwe.py`, lines 487-499 and 613-627) and call
   no serializer; and none of the 11 methods `validate` (`name-paths.txt`,
   lines 15 and 17-26) refers in its body to the names `encode`, `serialize`,
   `serialize_compact`, `serialize_json` or
   `generate_keys_and_prepare_headers`.
3. ECDH-1PU is not in the registry. `get_header_alg` raises
   `UnsupportedAlgorithmError` for an "alg" that is not in `ALG_REGISTRY`
   (`jwe.py`, lines 700-701); the encrypting methods call it at lines 90 and
   295, before lines 116 and 335, and the decrypting ones at 471 and 559. The
   package fills the registry only with the algorithms of RFC 7518
   (`authlib/jose/__init__.py:42`; `authlib/jose/rfc7518/__init__.py`, lines
   19-26). ECDH-1PU enters it only through `register_jwe_draft`
   (`authlib/jose/drafts/__init__.py`, lines 10-16) or `register_jwe_alg_draft`
   (`drafts/_jwe_algorithms.py`, lines 214-216), which no module of the package
   calls or imports; only the tests call one
   (`tests/jose/test_jwe.py:23`, `tests/jose/test_ecdh_1pu.py:19`,
   `tests/jose/test_chacha20.py:8`). The 107 files of `docs/` other than the
   `.svg` images name neither function, nor `authlib.jose.drafts`, ECDH-1PU or
   `sender_key` (they name `authlib.oauth2.drafts`, another module), and
   `README.md:73` lists ECDH-1PU as not done. A call of a registration
   function by a caller is a direct call of a function of the package that is
   not an entry point, which 4.4 excludes.
4. On the one path of the package that encrypts a JWT, there is no sender key.
   `JsonWebToken.encode` calls `self._jwe.serialize_compact(header, text, key)`
   without `sender_key` (`jwt.py:76`), and `serialize_compact` raises
   `ValueError` for an algorithm with tag-aware key agreement when `sender_key`
   is None (`jwe.py`, line 94 and lines 733-738), before line 116.
5. Code that the caller gives runs as the caller's code. A callable key or a
   `decode` function given by the caller runs inside an entry point
   (`jws.py`, lines 107-108 and 275-276; `jwe.py`, lines 509-510 and 763-764;
   `jwt.py`, lines 96-97). A serializer or a registration function called from
   there is a direct call of a function of the package that is not an entry
   point.

The package's own tests reach line 127 only through `serialize_compact`,
after registering the draft algorithms (`tests/jose/test_ecdh_1pu.py`, line 19,
and the test at lines 1217-1252).

Runs that support this reason and are not its basis (`12.py`, output
`12.json`):

- a, an input through an entry point:
  `JsonWebEncryption().deserialize_compact(token, key, sender_key=sender)`,
  with a compact JWE whose protected header is
  `{"alg":"ECDH-1PU+A128KW","enc":"A128GCM","epk":...}`, made with
  `cryptography` by ECDH-1PU with key wrapping as the package derives it on the
  receiving side (`drafts/_jwe_algorithms.py`, lines 47-80 and 99-114); `key`
  is the recipient's private P-256 JWK and `sender_key` the sender's public
  P-256 JWK, the parameter of `deserialize_compact` for this algorithm
  (`jwe.py`, lines 447 and 454-455). `UnsupportedAlgorithmError`
  ("unsupported_algorithm: "), raised in `JsonWebEncryption.get_header_alg`
  at `jwe.py:701`, reaches the caller; no line of the check's file ran (0 line
  events), and its module was not imported.
- b, outside 4.4 and kept as support only: the same call after
  `authlib.jose.drafts.register_jwe_draft(JsonWebEncryption)`, as the tests
  do. The payload is returned and line 127 does not run. The functions of the
  check's file that ran are `ECDH1PUAlgorithm.prepare_key` (2 times) and
  `unwrap`, `deliver_at_recipient`, `compute_shared_key`, `compute_fixed_info`
  and `compute_derived_key` (1 time each): even with the algorithm
  registered, a decrypting entry point does not enter
  `generate_keys_and_prepare_headers`.

### Row 13: `JsonWebSignature._validate_json_jws#3`, reached

The check is `raise DecodeError('Invalid "header" value')` at
`authlib/jose/rfc7515/jws.py:326`, under the guard of line 325: the member
"header" (read at line 324) is present, not empty and not a JSON object.
Before line 325, `_validate_json_jws` requires "protected" (lines 314-316) and
"signature" (lines 318-320) and decodes the protected header (lines 322-323).

- a: `JsonWebSignature().deserialize_json(text, key)`, with a flattened JWS
  JSON serialization (text): protected header `{"alg":"HS256"}`, an
  HMAC-SHA-256 signature under the key (a 32-byte secret) and `"header":
  "k1"`. `deserialize_json` (line 168) makes the text a dict (line 179),
  requires "payload" (lines 181-183) and, for an object without "signatures"
  (line 190), calls `_validate_json_jws` (line 192).
- b: `JsonWebSignature().deserialize(text, key)`, with a general JWS JSON
  serialization (text) whose 1 member of "signatures" has the same protected
  header and signature and `"header": ["kid","k1"]`. `deserialize` passes a
  text that starts with "{" and ends with "}" to `deserialize_json` (lines
  255-257), which calls `_validate_json_jws` for each member of "signatures"
  (lines 208-209).

Recorded (`13.json`): line 326 executed once in a (23 line events in the file)
and once in b (31). `DecodeError`, 'Invalid "header" value: ', raised in
`JsonWebSignature._validate_json_jws` at line 326, reaches the caller in both.
No setting differs from the default.

### Row 14: `Key.check_key_op#1`, reached

The check is the 2 statements `raise InvalidUseError()` of `Key.check_key_op`
(`authlib/jose/rfc7517/base_key.py`, lines 68-88): at line 85 for "sign" or
"verify" (line 83) when "use" is not "sig" (line 84), and at line 88 for
"decrypt", "encrypt", "wrapKey" or "unwrapKey" (line 86) when "use" is not
"enc" (line 87). Both need a "use" that is not empty (lines 81-82). The
earlier guards of the method (lines 74-76 for "key_ops", 78-79 for a private
operation on a public key) do not apply to these inputs.

- a: `JsonWebSignature().deserialize_compact(token, jwk)`, with a compact JWS
  whose protected header is `{"alg":"HS256"}`, validly signed, and as key the
  JWK `{"kty":"oct","k":<the 32-byte secret>,"use":"enc"}`.
  `HMACAlgorithm.verify` calls `key.get_op_key("verify")`
  (`authlib/jose/rfc7518/jws_algs.py:66`), reached from
  `authlib/jose/rfc7515/jws.py:113`, and `OctKey.get_op_key` calls
  `check_key_op` (`authlib/jose/rfc7518/oct_key.py:59`).
- b: `JsonWebEncryption().deserialize_compact(token, jwk)`, with a compact JWE
  whose protected header is `{"alg":"dir","enc":"A128GCM"}`, the payload
  encrypted with AES-128-GCM under a 16-byte key, and as key the JWK
  `{"kty":"oct","k":<that key>,"use":"sig"}`. `DirectAlgorithm.unwrap` calls
  `key.get_op_key("decrypt")` (`authlib/jose/rfc7518/jwe_algs.py:42`), reached
  from `authlib/jose/rfc7516/jwe.py:499`.
- c: `JsonWebEncryption().deserialize_compact(token, jwk)`, with a compact JWE
  whose protected header is `{"alg":"ECDH-ES","enc":"A128GCM","epk":...}`,
  where the ephemeral public key of the sender carries `"use":"sig"`, encrypted
  for the recipient's P-256 key by ECDH-ES in the direct key agreement mode;
  the key is the recipient's private JWK, without "use".
  `ECDHESAlgorithm.unwrap` imports the "epk" of the received header and calls
  `epk.get_op_key("wrapKey")` (`jwe_algs.py`, lines 302-303), and
  `AsymmetricKey.get_op_key` calls `check_key_op`
  (`authlib/jose/rfc7517/asymmetric_key.py:42`). Here the "use" that the check
  rejects comes from the received token, not from the key of the caller.

Recorded (`14.json`): line 85 executed once in a (55 line events in the file),
and line 88 once in b (56) and once in c (69). `InvalidUseError`, "invalid_use:
Key 'use' is not valid for your usage", raised in `Key.check_key_op`, reaches
the caller in all 3. No setting differs from the default; the key has none.

### Row 15: `JsonWebEncryption.get_header_zip#1`, reached

The check is the 2 statements `raise UnsupportedCompressionAlgorithmError()`
of `JsonWebEncryption.get_header_zip` (`authlib/jose/rfc7516/jwe.py`, lines
724-731): at line 728 when the header holds "zip" (line 725) and the instance
has a list of algorithms without that value (line 727), and at line 730 when
the value is not in `ZIP_REGISTRY` (line 729), which holds only "DEF"
(`authlib/jose/rfc7518/__init__.py:26`; `authlib/jose/rfc7518/jwe_zips.py`,
lines 10-12). `deserialize_compact` calls it at line 473 and
`deserialize_json` at line 561, after `get_header_alg` and `get_header_enc`
and before the key is used (lines 482 and 574).

- a: `JsonWebEncryption().deserialize_compact(token, key)`, with a compact JWE
  whose protected header is `{"alg":"dir","enc":"A128GCM","zip":"XYZ"}`, the
  payload encrypted with AES-128-GCM under the key, a 16-byte secret.
- b: `JsonWebEncryption(algorithms=["dir","A128GCM"]).deserialize_compact(token, key)`,
  with a compact JWE whose protected header is
  `{"alg":"dir","enc":"A128GCM","zip":"DEF"}`, the payload compressed with
  DEFLATE and encrypted. Setting not the default: `algorithms`
  (`jwe.py`, lines 49-51), a list without "DEF". The class is in the API
  reference (`docs/jose/specs/rfc7516.rst`, lines 17-19, an `autoclass` of
  sphinx.ext.autodoc, `docs/conf.py:31`), and the documentation shows the
  parameter for `JsonWebSignature` (`docs/jose/jws.rst:110`) and for
  `JsonWebToken` (`docs/jose/jwt.rst`, lines 87-92;
  `docs/upgrades/changelog.rst`, lines 509-512).
- c: `JsonWebEncryption().deserialize(text, key)`, with a JWE JSON
  serialization in the general syntax (text): the protected header of a, 1
  recipient with an empty encrypted key and the payload encrypted under the
  key. `deserialize` passes a text that starts with "{" and ends with "}" to
  `deserialize_json` (lines 679-681).
- d: `JsonWebToken(["dir","A128GCM"]).decode(token, key)`, with the token of b.
  `algorithms` of `JsonWebToken` has no default
  (`authlib/jose/rfc7519/jwt.py:37`) and goes to its `JsonWebEncryption` (line
  39). The package's own `authlib.jose.jwt` holds only JWS algorithms
  (`authlib/jose/__init__.py`, lines 55-72), and the changelog says to pass
  this parameter to use JWT with JWE algorithms
  (`docs/upgrades/changelog.rst`, lines 509-512). `decode` makes the key a
  loader (`jwt.py`, lines 96-99) and passes a text with 4 dots to
  `JsonWebEncryption.deserialize_compact` (lines 105-106).

Recorded (`15.json`): line 730 executed once in a (30 line events in the file)
and once in c (47), and line 728 once in b (29) and once in d (29).
`UnsupportedCompressionAlgorithmError`, "unsupported_compression_algorithm:
Unsupported 'zip' value in header", raised in
`JsonWebEncryption.get_header_zip`, reaches the caller in all 4. Settings that
are not the default: `algorithms` in b, and the list of algorithms of
`JsonWebToken` in d.

### Notes

- Terms. The description of this task names the results "fires", "does not fire"
  and "undecided"; this file and `reach.csv` use the terms of 4.4, `reached`,
  `not reached` and `undecided`, with the same meaning.
- Columns. `reach.csv` has the 8 columns of 4.4 in their order (`library`,
  `check`, `result`, `entry_point`, `scripts`, `settings`, `exception`,
  `reason`), then 2 that the description of the task asks for: `input` (the input in short) and
  `source_lines` (the source lines read for the check).
- Merging. 4.4 names 1 table and 1 file for the 20 checks,
  `no-fire/reach/reach.csv` and `no-fire/reach/READING.md`. This task writes
  only in `no-fire/reach/authlib/` and `work/reach/authlib/`; its 5 rows and
  this file are for merging into those 2.
- Scripts. Each `<n>.py` is its head (`work/reach/authlib/parts/head-<n>.py`)
  followed by the harness (`work/reach/authlib/parts/harness.py`, SHA-256
  beginning `f7cc849becc84317`), the same in all 5. Section 8 of
  `PROTOCOL.md` counts a change of a script of this folder after the protocol
  commit as a deviation. The 2 changes of these scripts after a run (the fix of
  the harness after the run of 15:52:04Z-15:52:06Z, and input d of row 15
  after the run of 15:52:47Z) are for `DEVIATIONS.md`, which this task does
  not write. The superseded outputs are kept beside the new ones, as section 8
  asks.
- Time stamps. `work/reach/authlib/verify.log` stamps local time (UTC+1): its
  16:35:17 is 15:35:17Z.

SHA-256 of the files of `no-fire/reach/authlib/` other than this one:

| file | SHA-256 |
|---|---|
| `11.py` | `3c05e701d3c3a92585224fbb0b65944e3058f7c85c9b8396457f069e1e6d5529` |
| `12.py` | `9f775b5c37e1a525536b24bc9e238ddb19282688fc47e01c6f053e508087cd61` |
| `13.py` | `01a1e00b064560ed3681bf40ab4ff129d84def9da868701d49b017a8c05b643b` |
| `14.py` | `4e9d68b0f1dbb221f0ef54b60de29d965de6ad4fb2c045834db13c27d6e22838` |
| `15.py` | `162d37751ba62e235235b7eff032073dd28c7802bc2594c7bc7319b8644df4e7` |
| `11.json` | `cf44f39cf07039bdd5cd303b63dc691eda9a8b01eaca2bf233cf7d6d3cdf80b5` |
| `12.json` | `bd1a868d36d6bfc7a8bf7e42af41f2da6a729e69b9418af2d016bdad6d3b6242` |
| `13.json` | `b9e839e891cb613aebf8f21d687bd6c69244751b97df10db532dd2603400ad69` |
| `14.json` | `a04f0298c8208595c0f32127084297c474ac492f8a058c9b5f7def724ad802e2` |
| `15.json` | `ef081dd363d3bdbf29b29a1bbde7cecf924b6fba08d1d0a8863561059a4391e7` |
| `name-paths.py` | `21b55bbf0abb44c59e171a4719bc6745342d8434c4b5b44adb0d8dbd7efff0e1` |
| `name-paths.txt` | `6980156f69836a69ba33c93a684142508e43772a5c51714e7af16f66377e0a83` |
| `reach.csv` | `ecf3f02d508a250d17ac99d010cb005425ce69dd7e0a4f4e0337db4cd7c34762` |

## joserfc


Step 5 of section 6 of `PROTOCOL.md` (section 4.4) for joserfc 1.8.0, at
commit `f345ff71cd6c36452a4e11e47b805ad450a95dd8`, the clone of the first
study (`../target-reach/work/src/joserfc`, source root `src/`). In this file,
paths of the source are relative to the package folder `src/joserfc/`; in
`reach.csv` they start with `joserfc/`. Paths of the deposit are relative to
`experiments/target-reach-extension/` unless they start with `../`.

### Results

| Row | Check | Raise statement | Result | Fired | Entry point | Exception that reaches the caller |
|---|---|---|---|---|---|---|
| 16 | `_rfc7516.message.decrypt_recipient#1` | `_rfc7516/message.py:249` | reached | fires | `jwe.decrypt_compact` | InvalidEncryptedKeyError, the object raised at the check |
| 17 | `_keys.JWKRegistry.import_key#1` | `_keys.py:70` | not reached | does not fire | none | closest inputs: KeyParameterError from `_rfc7517/models.py:61`; ValueError from `jwk.py:103` |
| 18 | `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1` | `_rfc7516/registry.py:140` | reached | fires | `jwe.decrypt_compact` | ExceededSizeError, the object raised at the check |
| 19 | `_rfc7516.registry.JWERegistry._check_algorithm#1` | `_rfc7516/registry.py:186` | reached | fires | `jwe.decrypt_compact` | UnsupportedAlgorithmError, the object raised at the check |
| 20 | `_rfc7516.registry.JWERegistry._check_algorithm#2` | `_rfc7516/registry.py:190` | reached | fires | `jwe.decrypt_compact`, with `algorithms` | UnsupportedAlgorithmError, the object raised at the check |

4 reached, 1 not reached, 0 undecided. In `reach.csv`, `result` uses the
words of section 4.4 (reached, not reached, undecided) and `fired` the words
of the task (fires, does not fire, undecided): reached is fires.

### What was done (2026-11-17, UTC)

| Time | Step |
|---|---|
| 15:29:10Z | Task started. |
| 15:29:52Z | `PROTOCOL.md` read in full. The commit that fixed it, `0796d80a8b34fe2915f48fd92c1485735b2a6fec`, has 2 time-stamp tokens of 15:27:56Z, from freetsa.org and DigiCert (`timestamps/README.md`), both in place before this task started. |
| 15:30:12Z to 15:30:35Z | The sample (`no-fire/sample.csv`, rows 16 to 20), the definitions of joserfc (`../target-reach/subjects/joserfc/`) and the runner of the toolkit (`../target-reach/reach/run.py`) read. |
| 15:30:28Z | `git status` run in the clone (see Incidents). |
| 15:31:40Z to 15:51:29Z | The source of joserfc read in the clone (the lines of each result are listed below), with the recorder (`../target-reach/reach/recorder.py`, lines 194-210 and 237-264) and the function table of the toolkit (`../target-reach/reach/checks.py`, lines 874-898). |
| 15:51:33Z | The 2 folders of this task made: `no-fire/reach/joserfc/` and `work/reach/joserfc/`. |
| 15:52:54Z to 15:54:49Z | `reach_harness.py` and the scripts `16.py` to `20.py` written. |
| 15:54:51Z to 15:55:06Z | First pass of the 5 scripts. `name-paths.py` written and run at 15:55:49Z and 15:56:08Z. |
| 15:56:36Z | A bytecode folder left by the first pass removed (see Incidents). |
| 15:57:44Z to 15:57:47Z | Second pass of the 5 scripts and of `name-paths.py`: the same results. |
| 15:59:58Z to 16:12:08Z | Every file and line named in the reasons checked again in the copy, and the 55 Python files of the package scanned (row 17); `reach_csv.py` written; `reach.csv` written at 16:12:08Z. |
| 16:13Z | `reach_harness.py` changed so that the records name the interpreter of the environment by its own path and hold `sys.prefix` and the files of the 2 dependencies (see Incidents). |
| 16:13:57.846Z to 16:14:00.797Z | Final pass of the 5 scripts: the records `16.json` to `20.json`, 24 runs. The results are those of the 2 earlier passes, whose records these replace. |
| 16:14:00.896Z | `name-paths.txt` written again, byte for byte as at 15:57:47Z; then `reach.csv` written again from the final records, byte for byte as at 16:12:08Z. |
| 16:14Z to 16:15Z | Nothing under `../target-reach/` has a modification time after 15:51:00Z (120163 entries walked); no file of the environment `../target-reach/work/venvs/joserfc` changed on 2026-11-17. |
| 16:16:56Z | This file written. |

No output of step 4 was opened: `no-fire/deletions-nofire.csv`,
`no-fire/summary.json` and `no-fire/records/` were not read (section 6,
step 5).

### How the inputs were run

**Inputs.** Each input is a call of `joserfc.jwe.decrypt_compact`
(`jwe.py:96`), whose name is an entry point of `subject.json` (decode,
decrypt_compact, decrypt_json, deserialize_compact, deserialize_json,
validate, validate_compact). Its first argument is a token that stands for one
received from another party; the other arguments are settings that a caller
gives through documented parameters: the key (`private_key`) and, for row 20,
`algorithms`. The key object is made before the call with the documented
import of its class (`OctKey.import_key`, `ECKey.import_key`), outside the
trace. The tokens are built with the dependencies of the environment
(`cryptography` for AES-GCM and P-256, `pycryptodome` for XChaCha20-Poly1305),
not with the package, from fixed keys, nonces and plaintexts written in each
script. The ECDH-ES token of row 17 derives its key as
`derive_key_for_concat_kdf` does (`_rfc7518/derive_key.py` 15-54: Concat KDF
with SHA-256, AlgorithmID "A128GCM", empty apu and apv, 128 bits), and its
control decrypts. Nothing of the package, of its dependencies, of its tests
or of the toolkit is changed, patched or replaced.

**Copy.** For every run, `reach_harness.py` deletes and makes again
`work/reach/joserfc/copy` as `make_copy` of `../target-reach/reach/run.py`
(lines 310-322) does: the items `src`, `tests` and `pyproject.toml` of `copy`
in `subject.json`, without `__pycache__`, `*.pyc` and `.pytest_cache`. It
compares the 55 subject files with `sha256` of `checks.json` and the 11 test
files with `test_files_sha256` of `blocks.json`, and stops at a difference.
The copy held 136 files with the same tree digest
(`e1ffb7ad4c3d648cc22da93f1f90005341f8b5a3ad956607b04d63483133fb3e`) before
and after each of the 24 runs, and no `__pycache__`. The commit of the clone
is read from `.git/HEAD`, without a git command, and equals `commit` of
`subject.json`.

**Environment.** The interpreter is `../target-reach/work/venvs/joserfc/bin/python`
(a link to `/usr/bin/python3.12`; `pyvenv.cfg` sets
`include-system-site-packages = false`): CPython 3.12.3 with the packages that
`requirements.txt` pins (cffi 2.1.1, cryptography 50.0.2, iniconfig 2.3.1,
packaging 26.3, pluggy 1.7.0, pycparser 3.12, pycryptodome 4.4.0, pygments
2.21.0, pytest 9.2.0) and no other, by the rule of `environment_problems`
(`run.py`, lines 278-305). In every run `sys.prefix` is the venv, and
`cryptography` and `Crypto` come from its `site-packages`; `joserfc` comes
from the copy, and the run stops if it does not. Each run is
`<venv>/bin/python -I -B <n>.py --inner <case> <copy>`, in the copy, with the
environment variables of `run.py` (lines 155-165). `-I` makes the interpreter
ignore the `PYTHON*` variables, so `PYTHONHASHSEED=0` among them has no effect
and hash randomization is on (flag 1 in every record).

**Repeats.** Each case ran 2 times, each in a fresh interpreter on a fresh
copy. For all 12 cases, the 2 records are equal in the input facts, the
outcome, the firings, the raise events, the functions entered, the lines
executed and the warnings. Every run returned 0 and raised no warning.

**Firing.** Only the call of the entry point is traced, with `sys.monitoring`
and the tool ids of the recorder (4, then 3). A RAISE event is a firing of a
check by the rule of the recorder (`recorder.py`, lines 237-264): the frame of
the event runs the code object of the event, its line is a line of a raise
statement of the check, the exception has the bare class name of the check,
and the instruction at the offset is `RAISE_VARARGS`. The records also hold
every line of the package executed during the call. The exception that
reaches the caller is recorded with its class and message, the innermost
frame of its traceback inside the package (as `site` of the recorder, lines
194-210), its frames in the package, and whether it is the object raised at
the check.

### Row 16: `_rfc7516.message.decrypt_recipient#1`, reached

Check: `raise InvalidEncryptedKeyError()` at `_rfc7516/message.py:249`.

Input (`16.py`, case `input`, final run 16:13:57.846Z): `decrypt_compact(token,
key)`, the key an OctKey of the 16 bytes 0x00 to 0x0f, no other setting. The
token is a JWE Compact Serialization with the header
`{"alg":"dir","enc":"A128GCM"}`, sealed with the key, with 16 bytes in its
second segment, the JWE Encrypted Key, which is to be empty with direct
encryption (the comment at `_rfc7516/message.py` 245-247). Segments of 39, 22,
16, 66 and 22 characters.

Run: the check fires. InvalidEncryptedKeyError ("invalid_encrypted_key: JWE
Encrypted Key value SHOULD be an empty octet sequence") reaches the caller,
the object raised at line 249. Frames in the package: `jwe.py:136`,
`_rfc7516/message.py` 101, 128, 124, 249.

Path in the source: `jwe.py` 123-126 take the default registry
(`_rfc7516/registry.py` 196); 128 `extract_compact` (`_rfc7516/compact.py`
37-48: the sizes pass; 49-56: the header has alg and enc; 75: the 16 bytes
become `recipient.encrypted_key`); 131 `guess_key` returns the OctKey
(`jwk.py` 82-83); 132 `check_use` passes, the key has no "use"
(`_rfc7517/models.py` 220-222); 136 `perform_decrypt`, then
`_rfc7516/message.py` 101; 107 `get_enc("A128GCM")` passes
(`_rfc7516/registry.py` 185, 188, 192: registered and recommended,
`_rfc7518/jwe_encs.py` 83, 114); 110 `check_iv` passes (12 bytes, `iv_size`
96: `_rfc7516/models.py` 204-207, `_rfc7518/jwe_encs.py` 82); 117 the header
protection check passes (203-206); 120 `check_header` passes
(`_rfc7516/registry.py` 97-111); 123 `get_alg("dir")` passes (recommended,
`_rfc7518/jwe_algs.py` 42); 124 `decrypt_recipient`: 244 `direct_mode` is
true, since dir has no key size (`_rfc7516/models.py` 238, 246-248;
`_rfc7518/jwe_algs.py` 39-51); 248 the encrypted key is not empty; 249 raise.
The handler at `_rfc7516/message.py` 126 catches the error (a JoseError,
`errors.py` 7-20, 178-180); 127 `verify_all_recipients` is true by default
(`_rfc7516/registry.py` 74, 84), so 128 raises the same object again, and
`perform_decrypt` (99-103) catches only InvalidExchangeKeyError.

Control (`control-empty-encrypted-key`): the same token with an empty second
segment decrypts to the 49-byte plaintext.

Source lines read: `jwe.py` 96-137; `_rfc7516/compact.py` 36-77; `jwk.py`
63-103; `_rfc7517/models.py` 205-222; `_rfc7516/message.py` 99-155, 203-206,
242-285; `_rfc7516/registry.py` 48-111, 154-196; `_rfc7516/models.py`
204-207, 234-262; `_rfc7518/jwe_algs.py` 39-51; `_rfc7518/jwe_encs.py`
79-117; `registry.py` 182-230; `errors.py` 7-20, 178-180.

### Row 17: `_keys.JWKRegistry.import_key#1`, not reached

Check: `raise MissingKeyTypeError("Missing key type")` at `_keys.py:70`, in
`JWKRegistry.import_key` (55-79), when `data` is a dict without "kty" and
`key_type` is None (66-70).

Reason: no input through an entry point can make line 70 execute. The calls,
guards and conditions on the way:

1. Callers of the function. `JWKRegistry.import_key` is called at 2 places of
   the package: `jwk.py:162`, the last line of the module function
   `jwk.import_key` (126-162), and `_keys.py:178`, in `KeySet.import_key_set`
   (169-185), through `registry_cls = JWKRegistry` (115). Neither name is an
   entry point.
2. No caller of those 2. A scan of the 55 Python files of the package finds
   the name `import_key_set` only at its definition (`_keys.py:170`), and the
   name `import_key` at: definitions (`jwk.py` 107, 111, 115, 119, 123, 126;
   `_rfc7517/models.py` 270; `_rfc7518/ec_key.py` 153; `_rfc7518/oct_key.py`
   79; `_rfc7518/rsa_key.py` 137; `_rfc8037/okp_key.py` 159); calls on a key
   class (`_keys.py` 79; `jwk.py` 151, 156; `super()` at `_rfc7518/ec_key.py`
   163, `_rfc7518/oct_key.py` 85, `_rfc7518/rsa_key.py` 147,
   `_rfc8037/okp_key.py` 181); docstrings (`_keys.py` 45; `jwe.py` 183;
   `jws.py` 334); a comment (`_rfc7518/jws_algs.py` 68); a string of `__all__`
   (`jwk.py` 43); and the 2 calls of item 3. The `getattr` calls of the
   package (`_rfc7518/jwe_algs.py` 259, `_rfc7518/jwe_encs.py` 41,
   `_rfc7518/jws_algs.py` 61, 92, 143, `_rfc7519/claims.py` 102) select hash
   functions and claim validators. No class statement names `JWKRegistry`
   (defined at `_keys.py:32`) as a base.
3. The key data of a token that the package imports is the "epk" header,
   at `_rfc7518/jwe_algs.py:225` (ECDH-ES, `decrypt_agreed_upon_key`, 217-227)
   and at `drafts/jwe_ecdh_1pu.py:95` (ECDH-1PU, whose `register_ecdh_1pu`,
   110-115, is never called; `drafts/__init__.py` is empty). Both call
   `import_key` on the caller's key: `recipient_key.import_key(headers["epk"])`.
4. The caller's key. `guess_key` (`jwk.py` 63-103) returns an OctKey, RSAKey,
   ECKey or OKPKey (82-83) or a key of a KeySet that the caller gives
   (84-101), and raises ValueError for anything else (103); what a key
   callable returns (59-60, 77-78) goes through the same tests.
   `check_key_type` (`_rfc7518/jwe_algs.py` 224; `_rfc7516/models.py` 250-252)
   lets only the key types EC and OKP pass (`_rfc7518/jwe_algs.py` 185): of the
   classes of the package, ECKey (`_rfc7518/ec_key.py` 110-111) and OKPKey
   (`_rfc8037/okp_key.py` 114-117).
5. Their import. `ECKey.import_key` (`_rfc7518/ec_key.py` 152-164) and
   `OKPKey.import_key` (`_rfc8037/okp_key.py` 158-182) pass a dict to
   `super().import_key` (163, 181), which is `BaseKey.import_key`
   (`_rfc7517/models.py` 269-282): CurveKey (337) and AsymmetricKey (317),
   between them, define no `import_key`. The "epk" is a dict there, since
   `check_header` (`_rfc7516/message.py:120`; `_rfc7516/registry.py` 103-104)
   validates it with `is_jwk` (`_rfc7518/jwe_algs.py` 187; `registry.py`
   43-45, 71, 83, 189-197). `BaseKey.import_key` checks the dict with
   `validate_dict_key` (276-277, 263-267), raises KeyParameterError at
   `_rfc7517/models.py:61` when "kty" is missing ("kty" is required,
   `registry.py:143`), and otherwise imports it with the binding of its class
   (278-279). It does not call `JWKRegistry.import_key`.

The closest inputs, run to show where they stop (`17.py`, final runs from
16:13:58.352Z):

- `input`: `decrypt_compact(token, key)`, the key an ECKey on P-256, no other
  setting; the token is an ECDH-ES + A128GCM compact JWE for that key whose
  "epk" has only crv, x and y. KeyParameterError ("key_parameter: 'kty' is
  required") reaches the caller, raised at `_rfc7517/models.py:61`, a raise
  line of the check `_rfc7517.models.NativeKeyBinding.validate_dict_key_registry#1`,
  which fires. Frames: `jwe.py:136`, `_rfc7516/message.py` 101, 128, 124, 253,
  `_rfc7518/jwe_algs.py:225`, `_rfc7518/ec_key.py:163`, `_rfc7517/models.py`
  277, 265, 61. No line of `_keys.py` executed.
- `input-b`: the same call with the well-formed token and the key given as a
  JWK dict without "kty" (crv, d, x, y). ValueError ("Invalid key") reaches
  the caller from `jwk.py:103`, through `jwe.py:131`. No line of `_keys.py`
  executed.

Controls, not inputs of the result:

- `control-epk-with-kty`: the well-formed token, whose header differs from
  that of `input` only by the "kty" member of "epk", decrypts with the ECKey
  to the 49-byte plaintext.
- `control-import-key-set`: a direct call of
  `KeySet.import_key_set({"keys": [a P-256 public JWK without "kty"]})`. Line
  70 executes and the check fires; MissingKeyTypeError reaches the caller,
  since `_keys.py:179` catches only InvalidKeyTypeError, of which
  MissingKeyTypeError is no subclass (`errors.py` 46-51). Lines of `_keys.py`
  executed: 66, 67, 70, 171, 173, 177, 178, 179.
- `control-key-callable`: `decrypt_compact(token, resolve)`, where `resolve` is
  a key callable of the caller (`jwk.py` 59-60, 77-78) that returns
  `KeySet.import_key_set({"keys": [the private JWK without "kty"]})`. Line 70
  executes and the check fires; MissingKeyTypeError reaches the caller
  through `jwe.py:131`, `jwk.py:78`, `_keys.py` 178, 70.

The 2 controls fire the check only through a call of `KeySet.import_key_set`
made by the caller's own code. Section 4.4 excludes such a call from an
input: "no other function of the package is called directly". In
`control-key-callable` the entry point only calls the caller's function back
(`jwk.py:78`); the call that reaches line 70 is made by that function, not by
the package. Whether a key callable that calls a function of the package is a
setting is left open (see Open).

Why the toolkit counts the check reachable: its closure is by name
(`checks.py`, lines 874-898), and the attribute name `import_key` at
`_rfc7518/jwe_algs.py:225` stands for every definition of that name,
`JWKRegistry.import_key` among them (`name-paths.txt`).

Source lines read: `_keys.py` 29-200; `jwk.py` 28-162; `jwe.py` 96-137,
165-192, 250-278; `jws.py` 324-340; `_rfc7516/message.py` 99-155, 242-285;
`_rfc7516/registry.py` 97-111; `_rfc7516/models.py` 234-262;
`_rfc7518/jwe_algs.py` 184-227, 243-260; `_rfc7518/ec_key.py` 108-166;
`_rfc7518/oct_key.py` 69-87; `_rfc7518/rsa_key.py` 103-104, 134-149;
`_rfc7518/jws_algs.py` 64-72; `_rfc8037/okp_key.py` 112-183;
`_rfc7517/models.py` 55-85, 263-284, 295, 317, 337; `_rfc7518/derive_key.py`
1-54; `_rfc7519/claims.py` 98-104; `registry.py` 43-45, 68-112, 136-146,
182-230; `drafts/jwe_ecdh_1pu.py` 1-30, 84-116; `errors.py` 1-60; and the scan
of item 2, over all 55 Python files of the package, for `import_key`,
`import_key_set`, `getattr`, `JWKRegistry`, `registry_cls` and the bases of
every class statement.

### Row 18: `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1`, reached

Check: `raise ExceededSizeError(f"Ciphertext size exceeds {self.max_ciphertext_length} bytes.")`
at `_rfc7516/registry.py:140`.

Input (`18.py`, case `input`, final run 16:13:59.450Z): `decrypt_compact(token,
key)`, the key an OctKey of the 16 bytes 0x10 to 0x1f, no other setting. The
token is a compact JWE with the header `{"alg":"dir","enc":"A128GCM"}` of a
49153-byte plaintext sealed with the key: segments of 39, 0, 16, 65538 and 22
characters, 65619 characters in all.

Run: the check fires. ExceededSizeError ("exceeded_size: Ciphertext size
exceeds 65536 bytes.") reaches the caller, the object raised at line 140.
Frames: `jwe.py:128`, `_rfc7516/compact.py:47`, `_rfc7516/registry.py:140`.

Path in the source: `jwe.py` 123-126 take the default registry; 128
`extract_compact`: `_rfc7516/compact.py` 37 `validate_compact_value_size`
passes (65619 characters; the maximum is 1024 + 1024 + 64 + 65536 + 64 =
67712, `_rfc7516/registry.py` 56-64, 113-122); 39-41, 5 segments; 44-46, the
protected header (39 characters), the encrypted key (0) and the
initialization vector (16) pass (`_rfc7516/registry.py` 124-136); 47
`validate_ciphertext_size(ciphertext_segment)`: 139, the segment has 65538
characters, more than `max_ciphertext_length` 65536 (62); 140 raise. The
limit applies to the base64url segment, not to the decoded ciphertext (49153
bytes), although the comment at line 61 reads "max ciphertext's size in
bytes"; the JSON serializations reach the same line through
`_rfc7516/json.py:117`. No handler lies between line 140 and the caller:
`compact.py` 47 comes before the `try` at 49, and `decrypt_compact` has none.

Control (`control-at-limit`): a 49152-byte plaintext gives a segment of 65536
characters (65617 in all) and decrypts.

Source lines read: `jwe.py` 96-137; `_rfc7516/compact.py` 36-77;
`_rfc7516/registry.py` 55-68, 113-152; `_rfc7516/json.py` 107-122;
`errors.py` 7-20, 163-167.

### Row 19: `_rfc7516.registry.JWERegistry._check_algorithm#1`, reached

Check: `raise UnsupportedAlgorithmError(f"Algorithm of '{name}' is not supported")`
at `_rfc7516/registry.py:186`.

Input (`19.py`, case `input`, final run 16:13:59.960Z): `decrypt_compact(token,
key)`, the key an OctKey of the 32 bytes 0x20 to 0x3f, no other setting. The
token is a compact JWE with the header `{"alg":"dir","enc":"XC20P"}`, sealed
with the key by the XChaCha20-Poly1305 of pycryptodome with a 24-byte nonce:
segments of 36, 0, 32, 66 and 22 characters.

Run: the check fires. UnsupportedAlgorithmError ("unsupported_algorithm:
Algorithm of 'XC20P' is not supported") reaches the caller, the object raised
at line 186. Frames: `jwe.py:136`, `_rfc7516/message.py` 101, 107,
`_rfc7516/registry.py` 172, 186.

Path in the source: `jwe.py` 123-126 take the default registry; 128
`extract_compact` passes (sizes; the header has alg and enc); 131-132 the key
is accepted; 136 `perform_decrypt`, then `_rfc7516/message.py` 101; 107
`registry.get_enc("XC20P")`, `_rfc7516/registry.py` 171-172; 185, XC20P is not
in the registry of "enc"; 186 raise. The package defines XC20P only in
`drafts/jwe_chacha20.py` 34 and never calls `register_chacha20_poly1305`
(39-41), while `setup_jwe_algorithms` (`jwa.py` 93-102, called at `jwe.py:49`)
registers the models of `_rfc7518/jwe_encs.py` 110-117 (`jwa.py` 22-23,
98-99) through `JWERegistry.register` (`_rfc7516/registry.py` 91-95). Line 107
lies outside the handler of `_rfc7516/message.py` 118-128, and
`perform_decrypt` (99-103) catches only InvalidExchangeKeyError. Had the draft
been registered, XC20P would still stop under the default settings, at 192-193,
since its model is not recommended (`drafts/jwe_chacha20.py` 12).

Source lines read: `jwe.py` 44-52, 96-137; `_rfc7516/compact.py` 36-77;
`_rfc7516/message.py` 99-110; `_rfc7516/registry.py` 48-52, 91-95, 166-193;
`jwa.py` 18-26, 90-102; `_rfc7518/jwe_encs.py` 79-117;
`drafts/jwe_chacha20.py` 1-41; `drafts/__init__.py` (0 bytes); `errors.py`
7-20, 91-96.

### Row 20: `_rfc7516.registry.JWERegistry._check_algorithm#2`, reached

Check: `raise UnsupportedAlgorithmError(f"Algorithm of '{name}' is not allowed")`
at `_rfc7516/registry.py:190`.

Input (`20.py`, case `input`, final run 16:14:00.317Z): `decrypt_compact(token,
key, algorithms=["dir", "A256GCM"])`, the key an OctKey of the 16 bytes 0x40
to 0x4f. The setting that is not the default is `algorithms` (default None),
the documented parameter "a collection (list, tuple, or set) of allowed
algorithms" (`jwe.py:118`); `registry` and `sender_key` are not given. The
token is a compact JWE with the header `{"alg":"dir","enc":"A128GCM"}`,
sealed with the key.

Run: the check fires. UnsupportedAlgorithmError ("unsupported_algorithm:
Algorithm of 'A128GCM' is not allowed") reaches the caller, the object raised
at line 190. Frames: `jwe.py:136`, `_rfc7516/message.py` 101, 107,
`_rfc7516/registry.py` 172, 190.

Path in the source: `jwe.py` 123-124, `algorithms` is given, so a new
JWERegistry holds it as `allowed` (`_rfc7516/registry.py` 83), with the models
registered on the class (48-52, 91-95); 128 `extract_compact` passes; 131-132
the key is accepted; 136 `perform_decrypt`, then `_rfc7516/message.py` 101;
107 `get_enc("A128GCM")`, `_rfc7516/registry.py` 171-172; 185, A128GCM is
registered; 188, `allowed` is set; 189, A128GCM is not in it; 190 raise. Line
107 lies outside the handler of `_rfc7516/message.py` 118-128, and
`perform_decrypt` (99-103) catches only InvalidExchangeKeyError.

Control (`control-default-settings`): with the default settings (`allowed` is
None, 191-193) the same token decrypts to the 49-byte plaintext.

Source lines read: `jwe.py` 96-137; `_rfc7516/compact.py` 36-77;
`_rfc7516/message.py` 99-110; `_rfc7516/registry.py` 48-52, 70-95, 166-193;
`errors.py` 7-20, 91-96.

### The name chains of the toolkit (`name-paths.txt`)

`name-paths.py` builds the function table with the toolkit's own code
(`ModuleTable`, `functions`, `plain_name` and `referenced_names` of
`../target-reach/reach/checks.py`, imported and not changed) over the subject
files of the copy, and searches breadth first from the functions that have
the name of an entry point. It finds 402 functions, 285 of them reachable:
the same 2 sets as `functions` of `checks.json`. For each check it prints 1
shortest chain of names, with the line of each reference:

- Row 16: `decrypt_compact` (`jwe.py:96`), `perform_decrypt` (136),
  `_perform_decrypt` (`_rfc7516/message.py:101`), `decrypt_recipient` (124).
  The input follows this chain.
- Row 17: the chain of row 16, then `decrypt_agreed_upon_key`
  (`_rfc7516/message.py` 253, 264) and `import_key` (`_rfc7518/jwe_algs.py:225`
  to `_keys.py:56`; the table has 11 other definitions of the name). The last
  step exists only by name: at run time, line 225 calls the `import_key` of
  the class of the caller's key (row 17, items 4 and 5).
- Row 18: `decrypt_compact`, `extract_compact` (`jwe.py:128`),
  `validate_ciphertext_size` (`_rfc7516/compact.py:47`). The input follows
  this chain.
- Rows 19 and 20: `validate_compact` (`jws.py:125`), `get_alg` (`jws.py:144`,
  `registry.get_alg` on the registry of the JWS call, a JWSRegistry by default,
  line 140; the name also stands for `JWERegistry.get_alg`), `_check_algorithm`
  (`_rfc7516/registry.py:160`). The inputs reach the 2 checks by another
  call: `decrypt_compact`, `perform_decrypt`, `_perform_decrypt`, then
  `get_enc` (`_rfc7516/message.py:107`, `_rfc7516/registry.py:172`).

### Files

In `no-fire/reach/joserfc/`:

- `reach_harness.py`: the shared code of the scripts (copy, checks of the
  definitions and of the environment, runs, tracer, records).
- `16.py` to `20.py`: 1 script per check. `python3 -I <n>.py` runs its cases
  and writes `<n>.json`.
- `16.json` to `20.json`: the records of the final pass (16:13:57.846Z to
  16:14:00.797Z).
- `name-paths.py` and `name-paths.txt`: the name chains of the toolkit.
- `reach_csv.py`: writes `reach.csv` from the records and the reasons, and
  stops if a record disagrees with a row. `python3 -I -B reach_csv.py`.
- `reach.csv`: 1 row per check, in the order of the sample; the columns of
  section 4.4 (`library`, `check`, `result`, `entry_point`, `scripts`,
  `settings`, `exception`, `reason`), then `row`, `input`, `fired`, `record`
  and `source_lines`.
- `READING.md`: this file.

In `work/reach/joserfc/` (ignored by `.gitignore` of the extension): `copy/`,
the copy of the last run; each run makes it again.

### Incidents

1. At 15:30:28Z, `git status` was run in the clone
   (`../target-reach/work/src/joserfc`) to see whether it was clean, without
   `GIT_OPTIONAL_LOCKS=0`. The modification time of its `.git` folder became
   15:30:28Z; no file inside `.git` has a modification time of 2026-11-17
   (`index`: 2026-11-14T06:12:46Z), and the 55 subject files and 11 test files
   of every copy match the digests of the definitions. No git command was run
   after it; the commit is read from `.git/HEAD`.
2. The first pass (15:54:51Z to 15:55:06Z) left
   `no-fire/reach/joserfc/__pycache__/reach_harness.cpython-312.pyc`: the
   outer `python3 -I` ignores `PYTHONDONTWRITEBYTECODE`. The folder was removed
   at 15:56:36Z; the scripts and `name-paths.py` now set
   `sys.dont_write_bytecode`, and no `__pycache__` was left after the later
   passes. A probe of the interpreter of the environment ran once with `-I` but
   without `-B` before 15:49:15Z; no file of the environment changed on
   2026-11-17.
3. The records of the first 2 passes named the interpreter by the target of
   the link of the venv (`/usr/bin/python3.12`), because the path helper of the
   harness followed links; the command itself named
   `../target-reach/work/venvs/joserfc/bin/python`. At 16:13Z the helper was
   changed not to follow links, and each record now also holds `sys.prefix`
   and the files of `cryptography` and `Crypto`. The final pass gave the same
   results.

### Open

- Section 4.4 and section 6, step 5, name 1 file `no-fire/reach/reach.csv` and
  1 file `no-fire/reach/READING.md`; the task asks for 1 of each per library.
  These are per library, with the columns of section 4.4 first, so that the 4
  files can be put together in the order of the sample.
- Row 17: whether a key callable that calls a function of the package
  (`control-key-callable`) is a setting. If it is, row 17 is reached through
  `decrypt_compact` with such a callable; under the wording of section 4.4
  ("no other function of the package is called directly") it is not, and the
  result rests on the guards above. The same holds for a key set that a caller
  receives from another party (a JWK Set) and imports with
  `KeySet.import_key_set` before the call: a key without "kty" in it executes
  line 70 in that import (`control-import-key-set`), before any entry point
  runs, and `import_key_set` is not an entry point of `subject.json`. Section
  9: "A check not reached rests on a reading of the guards, which can be
  wrong".
