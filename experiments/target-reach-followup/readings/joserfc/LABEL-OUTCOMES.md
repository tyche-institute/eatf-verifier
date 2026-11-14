# joserfc 1.8.0: the 8 cases that their agreed label does not decide

137 cases of `joserfc` have an agreed label that names a check: the 2 readings
of `labels/readings/joserfc/` give the block the same check. The labeled check
decides 129 of them. This file reads the other 8
(`generated/labels/joserfc/outcomes.csv`). The other 3 held-out libraries have
no such case: each of their 173 cases with an agreed label that names a check
is decided by it.

The columns "label fires" and "without the deciding check" are mechanical.
The second is the record of the case on the copy of the library from which
the check that decides the case is deleted: the check that raises there, or
"no exception". The reason of each case is a reading of the sources and is
reported as a reading. Line numbers refer to the commit of the subject
(`../target-reach/subjects/joserfc/subject.json`); library paths are relative
to `src/`; other paths are relative to the experiment directory. The number
in brackets is the execution of the block, as in the column `index`.

The 2 mechanical columns split the 8 cases into 2 groups of 4.

## Group 1: an earlier check stops the input (4 cases)

The labeled check does not fire. On the copy without the deciding check it
fires and decides the case. The input violates both checks, and the check
that the test does not describe comes first.

| Case | Agreed label | Decided by | Label fires | Without the deciding check |
|---|---|---|---|---|
| `TestJWECompact.test_ciphertext_exceeds_size#0` (`tests/jwe/test_compact.py:276`) | `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1` | `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | no | the labeled check |
| `TestJWECompact.test_header_exceeds_size#0` (`tests/jwe/test_compact.py:256`) | `_rfc7516.registry.JWERegistry.validate_protected_header_size#1` | `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | no | the labeled check |
| `TestCompact.test_payload_exceeded_size_error#0` (`tests/jws/test_compact.py:71`) | `_rfc7515.registry.JWSRegistry.validate_payload_size#1` | `_rfc7515.registry.JWSRegistry.validate_compact_value_size#1` | no | the labeled check |
| `TestJSON.test_b64_must_be_protected#1` (`tests/jws/test_json.py:166`) | `_rfc7797.json._is_payload_base64_encoded#1` | `registry.reject_unprotected_crit_header#2` | no | the labeled check |

**The 3 size tests.** Each test builds a compact value with 1 segment over
the limit of that segment and expects `ExceededSizeError`. The limit on the
whole compact value is the sum of the limits of the segments
(`joserfc/_rfc7516/registry.py`, lines 113 to 122: 1024 + 1024 + 64 + 65536 +
64 = 67712; `joserfc/_rfc7515/registry.py`, lines 104 to 107: 512 + 128000 +
1024 = 129536), and the check on the whole value runs before the checks on
the segments. The oversized segment of each test is longer than the limit on
the whole value as well: a ciphertext of 70000 characters before encoding,
a header of 1000 members, a payload of 128001 characters before encoding. The
whole-value check raises the same class, so the test passes, and the check on
the segment is not reached.

**`test_b64_must_be_protected#1`.** The protected header lists `b64` under
`crit`, and the unprotected header holds `b64`. The test is named for the rule
that `b64` must be a protected header, which `_is_payload_base64_encoded#1`
enforces. The check on critical headers that are not protected,
`reject_unprotected_crit_header#2`, rejects the input first, with the same
class.

Rules 2 and 3 give 3 of the 4 cases the labeled check as target, so these 3
are flags under both rules, in class A of `FLAGS-RULE3.md` and of
`../target-reach/readings/joserfc/FLAGS.md`. `test_header_exceeds_size#0` has
no target under either rule, so no flag marks it; the labels show it.
`repaired/joserfc/` holds, for each of the 4 tests, a variant that the labeled
check decides.

## Group 2: the input does not violate the labeled check (4 cases)

The labeled check does not fire, and on the copy without the deciding check
the case raises no exception. No check hides the labeled check: the input
passes it.

| Case | Agreed label | Decided by | Label fires | Without the deciding check |
|---|---|---|---|---|
| `TestJWTClaims.test_claim_jti#3 [0]` (`tests/jwt/test_claims.py:91`) | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | no | no exception |
| `TestJWTClaims.test_claim_jti#3 [1]` (`tests/jwt/test_claims.py:91`) | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | no | no exception |
| `TestJWTClaims.test_claim_jti#5` (`tests/jwt/test_claims.py:95`) | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | no | no exception |
| `TestJSON.test_unsupported_algorithm#0` (`tests/jws/test_json.py:137`) | `_rfc7515.registry.JWSRegistry.get_alg#1` | `_rfc7515.registry.JWSRegistry.get_alg#2` | no | no exception |

**`test_claim_jti#3` and `#5`.** The test function `test_claim_jti` holds 7
blocks. Its name names the claim, and `validate_jti#1`, the check that the
claim is a string (`joserfc/_rfc7519/claims.py`, lines 158 and 159), is the
only check whose message names `jti`. Blocks `#0` and `#1` pass a list and a
number, and that check decides them. Block `#3` passes the string `"wrong"`
against the options `value` and `values`, and block `#5` passes a blank
string for an essential claim; a string passes `validate_jti#1`, and
`check_value#1` rejects the value (lines 64 to 86). The name of the function
describes 1 of the checks that its blocks exercise.

**`test_unsupported_algorithm#0`.** `get_alg` holds 3 checks of the class
`UnsupportedAlgorithmError`: the algorithm "is not supported" (`#1`, line 83),
"is not allowed" (`#2`, line 87) and "is not recommended" (`#3`, line 90).
The test builds `JWSRegistry(algorithms=["HS512"])` and a value signed with
`HS256`. `HS256` is an algorithm that the library registers, so `#1` passes;
it is not in the list given to the registry, so `#2` rejects it. Both
readings chose `#1` by the word "unsupported" in the name of the test.

In these 4 cases the 2 readings agree, and each applies the instruction
(`labels/INSTRUCTION.md`): the label is the check that the words of the test
name, the values that the test builds are not read for it, and the order of
execution plays no part. The notes of reading A on the 3 rows say that another
check would run on the input. A label taken from the words of a test is
therefore not always the check that the input of the block is built for: a
test function has 1 name and can hold blocks for several checks, and 2 checks
of 1 class can fit 1 word. Agreement between 2 readings measures that the
instruction is applied the same way 2 times. It does not measure that the
label is the check a block is built for.

## Counts

Of the 137 cases of `joserfc` with an agreed label that names a check: 129
decided by the labeled check; 4 stopped by an earlier check that the labeled
check would follow (group 1); 4 whose input does not violate the labeled
check (group 2).
