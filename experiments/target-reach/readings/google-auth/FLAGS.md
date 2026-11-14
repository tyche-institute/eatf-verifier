# google-auth 2.62.2: reading of the flags

A flag is a case with a target that the target does not decide. The columns
"target fires" and "own test without the target" are mechanical and come from
`generated/google-auth/flags.csv`. The class is a reading of the sources, with
its reason, and is reported as a reading. Line numbers refer to the commit of
the subject (`subjects/google-auth/subject.json`, commit
`50b1eb269f110a4b7ab09ffe5ae59c0151cd63c2`); files are cited by their path in
`packages/google-auth`.

Classes: **A** the test does not reach its target; **B** the target fires and a
handler replaces its exception; **C** the target the rule assigned is not the
check the test describes; **D** cannot be decided from the sources. The
classes are tried in the order C, A, B, D, and a flag gets the first that
fits.

| Case | Target | Decided by | Target fires | Own test without the target | Class |
|---|---|---|---|---|---|
| `test_decode_bad_token_not_json#0` (`tests/test_jwt.py:230`) | `auth.jwt.decode#5` | `auth.jwt._decode_jwt_segment#1` | no | passes | C |
| `test_decode_no_cert#0` (`tests/test_jwt.py:329`) | `auth.crypt._python_rsa.RSASigner.from_string#2` | `auth.jwt.decode#3` | no | target not deleted | C |

Counts: A 0, B 0, C 2, D 0.

## Reasons

**How the rule chose.** Both blocks expect `ValueError` and match a message
pattern after the block. Every check of the package class `MalformedError`
gets the verdict "maybe" on a message pattern, never "yes": the class inherits
from `GoogleAuthError`, which defines `__init__` (`google/auth/exceptions.py`,
lines 18 to 23 and 79), and the rule then does not take the text of the
exception to be its message argument (`reach/targets.py`, `shape_known`). No
candidate has a literal part that satisfies the pattern (`C_pos` is empty in
`subjects/google-auth/targets.json` for both blocks), so the name of the test
broke the tie over 47 candidates, basis `assert+name`, name tier.

**`test_decode_bad_token_not_json#0`: C.** The test builds a token of 3
segments, each the base64 encoding of `123!` (`tests/test_jwt.py`, line 229),
calls `jwt.decode` and asserts that the message matches "Can\'t parse segment"
(line 232). `123!` is not JSON, and the name says "not json". The check the
test describes is `auth.jwt._decode_jwt_segment#1`: `_decode_jwt_segment`
catches the `ValueError` of `json.loads` and raises `MalformedError` "Can't
parse segment: {0}" (`google/auth/jwt.py`, lines 121 to 130). It is called on
the header at line 158, from `_unverified_decode`, which `decode` calls first
(line 260). The rule gave the target `auth.jwt.decode#5`, "Could not verify
token signature." (line 313), which scored highest on the tokens "decode",
"not" and "token" of the name; its message cannot match the pattern of the
test. The check that decides the case is the described check. Without the
target the test still passes, as expected for a check the test never reaches.

**`test_decode_no_cert#0`: C.** The test signs a token with the fixture
`signer`, whose key identifier is "1" (`tests/test_jwt.py`, lines 54 to 56 and
136), passes a mapping of certificates that holds only key identifier "2"
(line 328) and asserts that the message matches "Certificate for key id 1 not
found" (line 331). The check the test describes is `auth.jwt.decode#3`: when
`certs` is a mapping and the header names a key identifier that the mapping
lacks, `decode` raises `MalformedError` "Certificate for key id {} not found."
(`google/auth/jwt.py`, lines 285 to 292). The rule gave the target
`auth.crypt._python_rsa.RSASigner.from_string#2`, "No key could be detected."
(`google/auth/crypt/_python_rsa.py`, line 196), a check on parsing a private
key in Privacy-Enhanced Mail (PEM) format; it scored highest on the single
token "no" of the name. `jwt.decode` never constructs a signer, and the
target fires in no case of the study, so it was not deleted
(`generated/google-auth/checks.csv`). The check that decides the case is the
described check.

## What the flags of this library show

Both flags are wrong targets of the rule, both in the name tier, where the
name of the test broke a tie over 47 candidates that the message pattern did
not narrow. In both, the check that decides the case is the check the test
describes, by its name, its input and its message pattern. No flag is a test
whose input another check rejects first, and none is a target replaced by a
handler.
