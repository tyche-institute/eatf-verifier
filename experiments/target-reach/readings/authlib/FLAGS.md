# authlib 1.9.5: reading of the flags

A flag is a case with a target that the target does not decide. The columns
"target fires" and "own test without the target" are mechanical and come from
`generated/authlib/flags.csv`. The class is a reading of the sources, with its
reason, and is reported as a reading. Line numbers refer to the commit of the
subject (`subjects/authlib/subject.json`, commit `42607cbc2135`).

Classes: **A** the test does not reach its target; **B** the target fires and a
handler replaces its exception; **C** the target the rule assigned is not the
check the test describes; **D** cannot be decided from the sources. The
classes are tried in the order C, A, B, D, and a flag gets the first that
fits.

| Case | Target | Decided by | Target fires | Own test without the target | Class |
|---|---|---|---|---|---|
| `test_deserialize_json_fails_if_unprotected_header_contains_unknown_field_while_private_fields_restricted#0` (`tests/jose/test_jwe.py:382`) | `jose.rfc7515.jws.JsonWebSignature._reject_unprotected_crit#1` | `jose.rfc7516.jwe.JsonWebEncryption._validate_private_headers#1` | no | passes | C |
| `test_fail_deserialize_json#0` (`tests/jose/test_jws.py:182`) | `jose.rfc7515.jws.JsonWebSignature.deserialize_json#1` | `jose.util.ensure_dict#1` | no | fails | C |
| `test_fail_deserialize_json#1` (`tests/jose/test_jws.py:184`) | `jose.rfc7515.jws.JsonWebSignature.deserialize_json#1` | `jose.util.ensure_dict#1` | no | fails | C |
| `test_fail_deserialize_json#3` (`tests/jose/test_jws.py:191`) | `jose.rfc7515.jws.JsonWebSignature.deserialize_json#1` | `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#1` | no | fails | C |
| `test_fail_deserialize_json#4` (`tests/jose/test_jws.py:196`) | `jose.rfc7515.jws.JsonWebSignature.deserialize_json#1` | `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2` | no | fails | C |
| `test_invalid_input#0` (`tests/jose/test_jws.py:12`) | `jose.rfc7519.jwt.JsonWebToken.decode#1` | `jose.rfc7515.jws.JsonWebSignature.deserialize_compact#1` | no | target not deleted | C |
| `test_invalid_input#1` (`tests/jose/test_jws.py:14`) | `jose.rfc7519.jwt.JsonWebToken.decode#1` | no check (`authlib/jose/util.py:33`) | no | target not deleted | C |
| `test_invalid_input#2` (`tests/jose/test_jws.py:16`) | `jose.rfc7519.jwt.JsonWebToken.decode#1` | no check (`authlib/jose/util.py:18`) | no | target not deleted | C |
| `test_invalid_input#3` (`tests/jose/test_jws.py:18`) | `jose.rfc7519.jwt.JsonWebToken.decode#1` | no check (`authlib/jose/util.py:21`) | no | target not deleted | C |
| `test_invalid_input#4` (`tests/jose/test_jws.py:20`) | `jose.rfc7519.jwt.JsonWebToken.decode#1` | no check (`authlib/jose/util.py:33`) | no | target not deleted | C |
| `test_invalid_input#5` (`tests/jose/test_jws.py:22`) | `jose.rfc7519.jwt.JsonWebToken.decode#1` | no check (`authlib/jose/util.py:33`) | no | target not deleted | C |
| `test_invalid_input#6` (`tests/jose/test_jws.py:24`) | `jose.rfc7519.jwt.JsonWebToken.decode#1` | no check (`authlib/jose/util.py:33`) | no | target not deleted | C |

Counts: A 0, B 0, C 12, D 0.

All 12 targets were assigned in the name tier, with basis `name`
(`subjects/authlib/targets.json`). In none of the 12 cases does the target
fire.

## Reasons

**`test_deserialize_json_fails_if_unprotected_header_contains_unknown_field_while_private_fields_restricted#0`: C.**
The test builds a JSON Web Encryption (JWE) object with
`JsonWebEncryption(private_headers=set())`, adds the unknown field `"foo"` to
its unprotected header and expects `InvalidHeaderParameterNameError`
(`tests/jose/test_jwe.py`, lines 371 to 383). The name says the same: an
unknown field in the unprotected header while private fields are restricted.
The check this describes is `jose.rfc7516.jwe.JsonWebEncryption._validate_private_headers#1`,
which raises `InvalidHeaderParameterNameError(k)` for every header name outside
the registered names, the private names and the extra names of the algorithm
(`authlib/jose/rfc7516/jwe.py`, lines 745 to 759), and which
`JsonWebEncryption.deserialize_json` calls on the shared header, unprotected
part included (lines 557 and 564). The target is a method of the JSON Web
Signature (JWS) class, `JsonWebSignature._reject_unprotected_crit`, which
rejects a `crit` name in an unprotected JWS header
(`authlib/jose/rfc7515/jws.py`, lines 291 to 294); `jwe.py` never calls it.
The rule chose it because it shares 2 tokens with the name of the test,
"header" and "unprotected", against 1 for the JWE check
(`subjects/authlib/targets.json`, scores 1.386294 and 0.693147). The own test
passes without the target, as expected of a test that never reaches it.

**`test_fail_deserialize_json#0` and `#1`: C.** The 2 blocks give
`deserialize_json` the value `None` and the text `"[]"`
(`tests/jose/test_jws.py`, lines 182 to 185): inputs that are not a JSON
object. The check they describe is `jose.util.ensure_dict#1`, "Invalid
{structure_name}" (`authlib/jose/util.py`, lines 36 to 44): `None` fails in
`json_loads` and is rejected at line 41, `[]` parses to a list and is rejected
at line 44. `JsonWebSignature.deserialize_json` calls `ensure_dict` before any
other statement (`authlib/jose/rfc7515/jws.py`, line 179). The target,
`deserialize_json#1` ('Missing "payload" value', line 183), applies only to an
object without a payload, which is the input of block `#2` (`"{}"`, line 187),
the block of this test that the target does decide. The rule read only the
name of the test, `test_fail_deserialize_json`, which the 5 blocks share, and
gave all 5 the same target (tokens "deserialize" and "json", score 1.673976).
The own test fails without the target only because block `#2` needs it.

**`test_fail_deserialize_json#3`: C.** The comment "# missing protected"
(`tests/jose/test_jws.py`, line 189) and the input `{"payload": "YQ"}`
(line 190) describe `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#1`,
'Missing "protected" value' (`authlib/jose/rfc7515/jws.py`, lines 314 to
316), which decides the case. The target is the same name-tier assignment as
in blocks `#0` and `#1`; the object has a payload, so the target cannot apply.

**`test_fail_deserialize_json#4`: C.** The comment "# missing signature"
(`tests/jose/test_jws.py`, line 194) and the input
`{"payload": "YQ", "protected": "YQ"}` (line 195) describe
`jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2`, 'Missing
"signature" value' (`authlib/jose/rfc7515/jws.py`, lines 318 to 320), which
decides the case. The target is again the shared name-tier assignment.

**`test_invalid_input#0` to `#6`: C.** All 7 blocks call
`JsonWebSignature().deserialize(...)` on compact strings
(`tests/jose/test_jws.py`, lines 10 to 25). None of the strings begins with
`{`, so each goes to `deserialize_compact` (`authlib/jose/rfc7515/jws.py`,
lines 255 to 258). The target, `jose.rfc7519.jwt.JsonWebToken.decode#1`
("Invalid input segments length", `authlib/jose/rfc7519/jwt.py`, lines 101 to
108), belongs to `JsonWebToken.decode`, which the test never calls; the rule
chose it because its message holds both tokens of the name of the test,
"invalid" and "input" (score 3.060271). The inputs, read with their
comments, describe 1 rejection per segment:
- `#0`, `"a"`: 1 segment; `rsplit` cannot split it and
  `jose.rfc7515.jws.JsonWebSignature.deserialize_compact#1`, "Not enough
  segments", rejects it (`jws.py`, lines 95 to 100). This is the described
  check, and it decides the case.
- `#1`, `"a.b.c"`: the header segment `a` is not valid base64url;
  `extract_segment` raises `error_cls(f"Invalid {name} padding")`
  (`authlib/jose/util.py`, lines 29 to 33).
- `#2`, `"YQ.YQ.YQ"` (comment "# a"): the header decodes to `a`, which is not
  JSON; `extract_header` raises "Invalid header string" (`util.py`, lines 15
  to 18).
- `#3`, `"W10.a.YQ"` (comment "# []"): the header decodes to `[]`;
  `extract_header` raises "Header must be a json object" (`util.py`, lines 20
  to 21).
- `#4`, `"e30.a.YQ"` (comment "# {}") and `#5`, `"eyJhbGciOiJzIn0.a.YQ"`
  (header `{"alg":"s"}`): the header is an object and the payload segment `a`
  is not valid base64url; `util.py` line 33 rejects it through
  `_extract_payload` (`jws.py`, lines 106 and 352 to 353).
- `#6`, `"eyJhbGciOiJzIn0.YQ.a"`: header and payload decode; the signature
  segment `a` is rejected at `util.py` line 33 through `_extract_signature`
  (`jws.py`, lines 110 and 348 to 349).

For `#1` to `#6` the described rejection cannot be named by a check
identifier: the raise statements at `util.py` lines 18, 21 and 33 raise
`error_cls`, a class held in a parameter, which section 4 of the protocol
lists apart and does not count as a check. In every one of the 7 blocks the
described rejection lies on the path of `JsonWebSignature.deserialize`, and
the target does not. The target is not deleted because it fires in no case of
the study, so the own test without the target is not read.

## What the flags of this library show

All 12 flags are wrong targets of the rule, all in the name tier: the name of
the test pointed to a check that the test does not describe, and in 8 of the
12 to a check in a class that the test does not call (`JsonWebToken.decode`
for the 7 blocks of `test_invalid_input`, `JsonWebSignature` for the JWE
test). 4 flags come from 1 test, `test_fail_deserialize_json`, whose 5 blocks
share 1 name and so 1 target. No flag is a test whose input another check
rejects before the check it describes, and no flag involves a handler. The 5
targets of the assertion tier have no flag.
