# How the subjects were selected

This file records how the 4 libraries of the experiment were chosen. Every
step named here was finished before `PROTOCOL.md` was committed. The files it
points to are in `selection/`.

## 1. Frame

The frame is the list of the 1,000 most-downloaded projects of the Python
Package Index (PyPI) over 30 days, from the public snapshot
`top-pypi-packages.min.json` of the `top-pypi-packages` project
(<https://hugovk.github.io/top-pypi-packages/>).

| | |
|---|---|
| `last_update` field of the snapshot | 2026-11-01 06:41:05 |
| Secure Hash Algorithm 256 (SHA-256) digest of the snapshot file | `3e958a64ebe1de0b6a4ab4c6b465d481f350fd1dfa926c639add36eb34dabc1e` |
| Read and joined with PyPI metadata | 14 November 2026, 02:38 Coordinated Universal Time (UTC) |

`selection/build_frame.py` reads the snapshot, fetches the metadata of each
project from PyPI and writes `selection/frame-top1000.json`. Its output is
`selection/frame-run.txt`: 1,000 projects, 0 metadata errors.

## 2. Candidates

A project is a candidate when its name, its PyPI summary or its PyPI keywords
match this pattern, which was fixed before the list was read:

```
jwt|jose|jws|jwk|paseto|macaroon|signature|signing|signed|verif|token|oauth|openid|oidc|saml|webauthn|fido|dnssec|x\.?509|certificate|pki|tls|ssl|ssh|crypt|hmac|otp|kerberos|ntlm|attest|sigstore|in-toto|notary|pgp|gpg|dkim|auth
```

50 of the 1,000 projects match.

The filter reads metadata only, so it misses a verifier whose metadata names
none of these words. 3 such projects were noticed afterwards and are outside
the frame of candidates: `itsdangerous` (rank 147), `dnspython` (rank 122) and
`rsa` (rank 157). They were not screened. Verifiers of narrower use, such as
`signxml`, `pysaml2`, `sigstore`, `webauthn`, `pyhanko` or `certvalidator`,
are not among the 1,000 most-downloaded projects at all.

## 3. Inclusion criteria

The criteria were fixed before the screening and applied in this order; the
first one that fails excludes the candidate.

- **I1.** Third-party open-source project with a public source repository and
  a released version.
- **I2.** The package itself contains Python code (not only a binding to
  compiled code) implementing a function that takes an artifact received from
  another party (a token, a signed or authenticated message, a signature, a
  certificate or chain, a protocol request or response, a record set) and
  either accepts it or rejects it by raising an exception. A function that
  returns True or False or a status object does not count. Pure signing,
  encoding or client-side request construction does not count. Parsing alone
  (rejecting malformed syntax of a general data format) does not count;
  verification of authenticity, integrity, validity period, issuer or
  audience, signature, or protocol rules does.
- **I3.** The Python code that 1 such verification call can run holds at
  least 5 checks. A check is the raise statements in 1 function that raise
  the same rejection exception class with the same message template.
- **I4.** The package's own test suite at the latest release holds at least
  10 negative-test blocks that call such a function and expect a rejection
  exception. A block is `with pytest.raises(E)`, `pytest.raises(E, callable)`,
  `with self.assertRaises(E)`, `self.assertRaises(E, callable)` or the
  `assertRaisesRegex` form.
- **I5.** The tests run offline on CPython 3.12, unmodified and without any
  recorder. A candidate that fails I5 is replaced by the next one in rank
  order.

The subjects were to be the first 3 candidates in rank order that pass all 5
criteria. They are 4. Whether `google-auth` passes I4 depends on a reading of
its rejection base, and that reading was made with its tests in view (section
6). Under the reading that was made, the first 3 are `google-auth`,
`oauthlib` and `authlib`; under the other, `google-auth` fails I4 and the
first 3 are `oauthlib`, `authlib` and `joserfc`. All 4 are subjects, and each
is reported on its own.

PyJWT (rank 36) passes the criteria too; it is the development subject of the
toolkit and is not one of the 4.

The replacement clause of I5 belongs to the selection and was not used: all 4
pass I5. After the protocol is fixed, no library is replaced (`PROTOCOL.md`,
section 3).

## 4. Screening

Every candidate was screened read-only. For 32 candidates the source was
read, and small scripts that parse files with Python's `ast` module counted
checks and blocks. The other 18 were excluded at I2 without their source,
from the description at PyPI or the documentation alone: what they are (a
tokenizer, a parser, a compiled extension, typing stubs, a build tool and
the like) decides I2. No candidate was installed, imported or run during the
screening. `selection/screening-results.json` holds 1 record per candidate:
the version read, the evidence for I2, the entry points, the files of the
verification path, the counts and the criterion that excludes the candidate.
The records are as the screening wrote them, except that 7 sentences were
put in the passive voice afterwards. `selection/screening-scripts/` holds
the scripts.

Result: 27 candidates fail I2, 5 fail I3, 5 fail I4 and 13 pass I1 to I4.
Section 9 lists all 50.

## 5. Recount with the toolkit

The screening counted with its own scripts and on the files a reader chose.
The selection depends on a few verdicts only: an exclusion above rank 267
that turned out wrong would change the subjects. So every candidate above
rank 267 that fails I3 or I4, and the 2 bindings among those that fail I2,
were counted again with the toolkit's own enumerators, together with PyJWT
and the 4 selected libraries. `selection/survey.py` does the count,
`selection/recount.sh` names the 11 projects and their tags, and
`selection/recounts.txt`, its output, gives the commit of each. The count is
static: nothing is run.

| Project | Rank | Screening verdict | Recount | Verdict after the recount |
|---|---|---|---|---|
| urllib3 2.8.0 | 6 | fails I4 | 9 reachable checks; 338 blocks, 7 call an entry point, 5 included | fails I4 |
| cryptography 50.0.2 | 9 | fails I3 | 8 reachable checks: 6 in the Fernet functions, 2 in the one-time-password functions; 1 call runs at most 4; 19 included blocks, all class-only | fails I3, by 1 check |
| truststore 0.10.5 | 94 | fails I3 | no count: the package defines no exception class and raises classes of the standard `ssl` module, so its code holds no check as defined here | fails I3 |
| pyopenssl 26.4.0 | 166 | fails I2 | 9 checks, 0 reachable from the verification functions | fails I2 |
| pynacl 1.6.2 | 184 | fails I2 | 14 reachable checks over the box, secret-box, signing and password-hash functions; 1 call runs at most 4 | fails I2, and would fail I3 |
| msal 1.39.0 | 194 | fails I4 | 28 reachable checks; 62 blocks, 4 included | fails I4 |
| pyjwt 2.15.1 | 36 | passes | 57 reachable checks; 79 included blocks, 50 assert more than the class | passes |
| google-auth 2.62.2, base `ValueError` | 77 | passes | 52 reachable checks; 20 blocks call the entry point, 17 included, all 17 assert more than the class | passes |
| google-auth 2.62.2, base `GoogleAuthError` | 77 | not screened under this reading | 169 reachable checks; 20 blocks call the entry point, 3 included | fails I4 |
| oauthlib 4.0.1 | 131 | passes | 54 reachable checks; 73 included blocks, 2 assert more than the class | passes |
| authlib 1.9.5 | 248 | passes | 36 reachable checks; 43 included blocks, 2 assert more than the class | passes |
| joserfc 1.8.0 | 267 | passes | 81 reachable checks; 138 included blocks, 5 assert more than the class | passes |

The closest call is `cryptography`. A call of `Fernet.decrypt` reaches 3
checks, and through `MultiFernet.decrypt` 4: 1 check short of I3. Had it
passed, it would have been the first subject. Its 19 included blocks all
assert the class alone.

`truststore` leaves the decision to the operating system. The screening
counted 4 groups of raise statements on its verification path, and an earlier
state of the toolkit 3 checks, 2 of them reachable; under every count it
fails I3.

The table gives the counts of the toolkit as committed. An earlier state of
the toolkit matched classes by bare name and gave other counts for some
projects. The largest difference is `authlib`: 69 reachable checks and 70
included blocks then, 36 and 43 now. The OpenID Connect and OAuth 2 modules of
`authlib` 1.9.5 take their claims validation, and its exception classes, from
`joserfc`. A block that expects an exception class of `joserfc` is not
included, because that class is no class of the package `authlib`: 21 blocks
expect `joserfc.errors.InvalidClaimError` and 6
`joserfc.errors.MissingClaimError`. No verdict differs between the 2 counts.

The other candidates above rank 267 fail I2 on what they are (a client that
signs requests, 2 tokenizers, a password hasher in compiled code, a parser, a
transport adapter, a store for a token cache and a client-side helper): no
count decides those verdicts.

## 6. Releases, the rejection base of google-auth, and criterion I5

**Releases.** The version of a subject is its latest release at PyPI that is
not a pre-release, at the commit of its tag in the project's repository. The
releases were read from PyPI's JavaScript Object Notation (JSON) interface on
14 November 2026 at 03:45 UTC and again at 07:31 UTC, with the same result.

| Subject | Rank | Version | Uploaded to PyPI (UTC) | Tag | Commit |
|---|---|---|---|---|---|
| google-auth | 77 | 2.62.2 | 2026-11-10 15:50:53 | `google-auth-v2.62.2` | `50b1eb269f110a4b7ab09ffe5ae59c0151cd63c2` |
| oauthlib | 131 | 4.0.1 | 2026-10-31 09:52:56 | `v4.0.1` | `6e3aa05af92978755939a18cb4dd655ced156c1e` |
| authlib | 248 | 1.9.5 | 2026-11-05 16:13:16 | `v1.9.5` | `42607cbc2135252a641a845e4ed7f94e3a922c47` |
| joserfc | 267 | 1.8.0 | 2026-11-03 10:45:56 | `1.8.0` | `f345ff71cd6c36452a4e11e47b805ad450a95dd8` |

PyPI also lists pre-releases of `google-auth` (3.0.0.dev0) and of `authlib`
(1.10.0b1); they do not count.

**The rejection base of google-auth.** The entry point is `decode` of
`google/auth/jwt.py`. Its docstring names 2 exceptions:
`google.auth.exceptions.InvalidValue`, "if value validation failed", and
`google.auth.exceptions.MalformedError`, "if schema validation failed".
`google/auth/exceptions.py` declares both with 2 bases:
`DefaultCredentialsError`, a subclass of the package's base class
`GoogleAuthError`, and the built-in `ValueError`. So the documentation
supports 2 readings of "the base class of the exceptions the documentation
names": `GoogleAuthError` and `ValueError`.

Of the 20 blocks of the tests that call `decode`, 14 expect `ValueError`, 2
`InvalidValue` and 1 `MalformedError`; the other 3 name `TypeError`, 1 of them
beside `ValueError`. With `ValueError` as the base, 17 blocks are included.
With `GoogleAuthError`, 3 are, and `google-auth` fails I4. The base
`ValueError` was chosen after the tests had been read, because the tests
expect it. `selection/recounts.txt` gives the counts under each reading and
under both bases together.

**Criterion I5.** I5 was checked on each of the 4, on PyJWT and on the pilot,
in an environment of its own (CPython 3.12.3, packages pinned in
`subjects/<name>/requirements.txt`), with the test files unmodified and
without the recorder. `selection/offline_check.py` runs every suite run 1
time plainly and 1 time with `guard/reach_offline.py`, which refuses and
counts every attempt to reach another machine. I5 holds when every test has
the same outcome in both runs. `selection/offline-check.txt` is the output,
of 14 November 2026, 06:55 to 06:59 UTC.

| Subject | Suite runs | Outcome of both runs | Tests with another outcome | Refused attempts |
|---|---|---|---|---|
| google-auth | 1 | 2,349 passed | 0 | 9 |
| oauthlib | 1 | 717 passed, 2 skipped, 21 subtests passed | 0 | 0 |
| authlib | 5 | 1,211 passed, 2 skipped | 0 | 0 |
| joserfc | 1 | 310 passed, 91 subtests passed | 0 | 0 |
| PyJWT, package scope | 1 | 471 passed, 4 skipped | 0 | 0 |
| jwcrypto, the pilot | 1 | 163 passed | 0 | 0 |

The 9 refused attempts of `google-auth` are name lookups. 7 look up
`test.invalid`, in 4 tests named `test_connection_error`, which expect the
connection to fail. 2 look up `iamcredentials.googleapis.com`, from a
background thread that a test of the credentials starts. Every test passes
with and without the refusal.

All 4 pass I5, and so do PyJWT and the pilot.

An earlier check of I5 had run, on `google-auth`, `oauthlib` and `authlib`,
the test files that hold included blocks 1 time and the whole suite 2 times,
plainly. Its records came from an earlier state of the toolkit and were
removed. `PROTOCOL.md`, section 5, lists every run made on the 4 libraries
before the protocol.

## 7. The pilot and the candidates not used

`jwcrypto` 1.6.1 (rank 875, tag `v1.6.1`, commit
`c10aa4343f9ce2e68caaf20aef9d2c5f6d0c4d71`) served as the pilot: the whole
procedure was run on it before the protocol was fixed, to exercise the
toolkit on a library whose tests use the `unittest` forms. It was chosen as
the lowest-ranked candidate that passes I1 to I4, so that the pilot takes
none of the candidates that the rank order could make a subject. Its results
are reported as a pilot, not as a held-out subject.

Between `joserfc` and the pilot, the candidates that pass I1 to I4 are, in
rank order: `paramiko` (271), `pycryptodome` (330), `scramp` (383), `ecdsa`
(508), `python-jose` (621), `supabase-auth` (677) and `service-identity`
(869). None of them was counted again with the toolkit, none was checked
against I5, and nothing of them was run.

## 8. What this selection does not give

The 4 subjects are the highest-ranked candidates of a keyword frame that meet
the criteria. They are no random sample of verifiers, and all 4 come from 1
ecosystem and 1 language. All 4, like PyJWT and the pilot, verify JSON Web
Tokens or OAuth requests: 1 family of protocols.

The 4 are not independent of one another. `authlib` and `joserfc` are
maintained in 1 organisation, and `authlib` 1.9.5 requires `joserfc`: the
environment of `authlib` holds `joserfc` 1.8.0, the release that is the
fourth subject. The subject `authlib` counts the checks of the package
`authlib` alone; a rejection that `joserfc` raises inside a test of `authlib`
is no check of `authlib`, and its exception is no rejection class of
`authlib`. The 43 included blocks of `authlib` are all in the tests of its
module `authlib.jose`, which the release itself marks as deprecated in favour
of `joserfc` (`authlib/jose/__init__.py`).

`google-auth` is a subject under 1 of the 2 readings of its rejection base
(section 6).

The criteria favour libraries that reject by raising and that test rejections
with the standard block forms; a verifier that returns False, or whose tests
use their own helpers, is outside the frame by construction.

## 9. All 50 candidates

"Version read" is the version whose source the screening read or, for a
candidate excluded at I2 without its source (section 4), the version whose
description it read; "not needed" stands where the screening recorded no
version. The counts behind each
verdict are in `selection/screening-results.json`, as the screening wrote
them; where the recount of section 5 gives another count, the recount is the
one the selection relies on.

| Rank | Project | Version read | Verdict | Note |
|---|---|---|---|---|
| 6 | urllib3 | 2.8.0 | fails I4 | 6 blocks call the hostname check and expect a rejection; the toolkit's recount finds 5 included blocks |
| 9 | cryptography | 50.0.2 | fails I3 | the Python code of 1 Fernet call holds at most 4 checks; the larger verifiers are compiled code |
| 36 | pyjwt | 2.15.1 | passes I1 to I4 | development subject of this study |
| 77 | google-auth | 2.62.2 | passes I1 to I4 | selected; passes I4 under 1 of the 2 readings of its rejection base (section 6) |
| 94 | truststore | 0.10.5 | fails I3 | the operating system decides; the Python code holds fewer than 5 checks |
| 123 | requests-oauthlib | 2.0.0 | fails I2 | a client that builds and signs requests |
| 131 | oauthlib | 4.0.1 | passes I1 to I4 | selected |
| 154 | tiktoken | not needed | fails I2 | a tokenizer for language models |
| 156 | tokenizers | not needed | fails I2 | a tokenizer for language models |
| 166 | pyopenssl | 26.4.0 | fails I2 | a binding: the verification runs in compiled code |
| 184 | pynacl | 1.6.2 | fails I2 | a binding: the verification runs in compiled code |
| 189 | bcrypt | not needed | fails I2 | a compiled extension; `checkpw` returns True or False |
| 194 | msal | 1.39.0 | fails I4 | 4 blocks call a verification function and expect a rejection |
| 229 | asn1crypto | 1.5.1 | fails I2 | a parser and serializer; it verifies nothing |
| 242 | google-auth-httplib2 | 0.4.4 | fails I2 | a transport adapter; it verifies no received artifact |
| 247 | msal-extensions | 1.3.1 | fails I2 | stores a token cache on disk; it verifies no received artifact |
| 248 | authlib | 1.9.5 | passes I1 to I4 | selected |
| 255 | google-auth-oauthlib | 1.5.0 | fails I2 | client-side helper; it verifies no received artifact |
| 267 | joserfc | 1.8.0 | passes I1 to I4 | selected |
| 271 | paramiko | 5.1.0 | passes I1 to I4 | passes; not needed |
| 278 | asttokens | not needed | fails I2 | developer tooling for syntax trees |
| 298 | griffelib | not needed | fails I2 | documentation tooling |
| 325 | pytokens | 0.4.1 | fails I2 | a tokenizer for Python source |
| 330 | pycryptodome | 4.4.0 | passes I1 to I4 | passes; not needed |
| 383 | scramp | 1.5.0 | passes I1 to I4 | passes; not needed |
| 434 | requests-aws4auth | 1.4.0 | fails I2 | signs outgoing requests |
| 442 | pycryptodomex | 3.24.2 | fails I4 | 6 blocks for `DSS.verify`, which holds 6 checks; the EdDSA verification (7 checks) has 0 blocks, and the CCM mode, which reaches about 8 checks only if its length checks count, has 2 |
| 497 | nltk | 3.10.4 | fails I2 | natural-language toolkit |
| 508 | ecdsa | 0.19.2 | passes I1 to I4 | passes; not needed |
| 528 | dateparser | not needed | fails I2 | date parsing |
| 561 | pyotp | 2.10.0 | fails I2 | `verify` returns True or False |
| 598 | passlib | 1.7.4 | fails I3 | 4 checks under the rejection-class reading |
| 621 | python-jose | 3.5.0 | passes I1 to I4 | passes; not needed |
| 659 | sentencepiece | not needed | fails I2 | a tokenizer for language models |
| 677 | supabase-auth | 2.34.1 | passes I1 to I4 | passes; not needed |
| 700 | oauth2client | 4.1.3 | fails I4 | 5 blocks; archived project |
| 704 | sqlmodel | 0.0.50 | fails I2 | a database layer |
| 730 | griffe | not needed | fails I2 | documentation tooling |
| 748 | adal | 1.2.7 | fails I2 | checks no authenticity, validity period, issuer or audience |
| 849 | id | 1.6.1 | fails I3 | 4 checks: the audience claim only |
| 867 | oscrypto | 1.3.0 | fails I4 | the TLS handshake (14 checks) has 0 blocks of the defined forms: its tests use a context manager of their own; the signature verification functions have 10 blocks but hold 1 check |
| 869 | service-identity | 26.1.0 | passes I1 to I4 | passes; not needed |
| 875 | jwcrypto | 1.6.1 | passes I1 to I4 | passes; used as the pilot |
| 884 | aws-requests-auth | 0.4.3 | fails I2 | signs outgoing requests |
| 891 | pydata-google-auth | 1.9.1 | fails I2 | client-side credential helper |
| 894 | flask-login | 0.6.3 | fails I2 | the cookie check returns the payload or None |
| 912 | msoffcrypto-tool | 6.1.0 | fails I3 | no call path reaches 5 checks |
| 955 | prek | 0.5.10 | fails I2 | a Git hook manager, not Python verification code |
| 957 | cmake | not needed | fails I2 | ships build-tool binaries |
| 997 | types-pyopenssl | 24.1.0.20240722 | fails I2 | typing stubs without function bodies |
