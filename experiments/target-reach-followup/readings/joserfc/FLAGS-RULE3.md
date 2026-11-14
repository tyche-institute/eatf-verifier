# joserfc 1.8.0: reading of the flags under rule 3

A flag under rule 3 is a case with a target under `reach-target-rule/3` that
the target does not decide. `joserfc` has 16 (`generated/trace/joserfc/analysis/flags.csv`);
the other 3 held-out libraries have, under rule 3, the flags that they have
under rule 2, which `../target-reach/readings/` reads. Of the 16, 5 are flags
under rule 2 with the same target and keep the class of
`../target-reach/readings/joserfc/FLAGS.md`; 11 are new: their rule-2 target
decided them, and rule 3 gives them another target. This file reads the 11.

The columns "target fires" and "own test without the target" are mechanical
and come from `generated/trace/joserfc/analysis/flags.csv`; the column "agreed
label" comes from `generated/labels/joserfc/rule-vs-label.csv`. The class is a
reading of the sources, with its reason, and is reported as a reading. The
classes and their order are those of `../target-reach/readings/joserfc/FLAGS.md`:
**A** the test does not reach its target; **B** the target fires and a handler
replaces its exception; **C** the target the rule assigned is not the check
the test describes; **D** cannot be decided from the sources; tried in the
order C, A, B, D. Line numbers refer to the commit of the subject
(`../target-reach/subjects/joserfc/subject.json`); library paths are relative
to `src/`; other paths are relative to the experiment directory. The number
in brackets is the execution of the block, as in the column `index`.

## The 5 flags under both rules

| Case | Target (both rules) | Decided by | Class in the first reading |
|---|---|---|---|
| `TestJWECompact.test_ciphertext_exceeds_size#0` (`tests/jwe/test_compact.py:276`) | `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1` | `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | A |
| `TestJWEJSON.test_decode_multiple_recipients#1` (`tests/jwe/test_json.py:192`) | `_rfc7516.message._perform_decrypt#2` | `_rfc7516.message._perform_decrypt#1` | C |
| `TestCompact.test_payload_exceeded_size_error#0` (`tests/jws/test_compact.py:71`) | `_rfc7515.registry.JWSRegistry.validate_payload_size#1` | `_rfc7515.registry.JWSRegistry.validate_compact_value_size#1` | A |
| `TestJSON.test_b64_must_be_protected#1` (`tests/jws/test_json.py:166`) | `_rfc7797.json._is_payload_base64_encoded#1` | `registry.reject_unprotected_crit_header#2` | A |
| `TestRFC7797.test_compact_missing_alg#0` (`tests/jws/test_rfc7797.py:51`) | `_rfc7516.compact.extract_compact#1` | `_rfc7515.compact.decode_header#1` | C |

For `test_compact_missing_alg#0` the basis of the target changes from the
exception class (rule 2) to the name (rule 3); the target is the same.

## The 11 new flags

All 11 are in `tests/jwt/test_claims.py`, in the name tier, and all 11 are
decided by `_rfc7519.claims.BaseClaimsRegistry.check_value#1`, which was
their target under rule 2 (basis: exception class). That check covers the 5
statements `raise InvalidClaimError(claim_name)` of `check_value`
(`joserfc/_rfc7519/claims.py`, lines 64, 71, 73, 84 and 86): the value is
blank, or it does not match the option `value` or `values`. The 7 methods
`JWTClaimsRegistry.validate_<claim>` are called through
`getattr(self, "validate_" + key, None)` (line 102), so their checks are
reachable by execution only and are candidates under rule 3, not under rule 2.

| Case | Target under rule 3 | Target fires | Own test without the target | Agreed label | Class |
|---|---|---|---|---|---|
| `TestJWTClaims.test_claim_jti#3 [0]` (`tests/jwt/test_claims.py:91`) | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | C |
| `TestJWTClaims.test_claim_jti#3 [1]` (`tests/jwt/test_claims.py:91`) | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | C |
| `TestJWTClaims.test_claim_jti#5` (`tests/jwt/test_claims.py:95`) | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | C |
| `TestJWTClaims.test_validate_aud#1` (`tests/jwt/test_claims.py:174`) | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | none agreed (1 reading: `check_value#1`; 1: no label) | C |
| `TestJWTClaims.test_validate_aud#2` (`tests/jwt/test_claims.py:175`) | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | none agreed (1 reading: `check_value#1`; 1: no label) | C |
| `TestJWTClaims.test_validate_aud#3` (`tests/jwt/test_claims.py:183`) | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | C |
| `TestJWTClaims.test_validate_aud#4` (`tests/jwt/test_claims.py:184`) | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | C |
| `TestJWTClaims.test_validate_list_inclusion#1` (`tests/jwt/test_claims.py:255`) | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | C |
| `TestJWTClaims.test_validate_list_inclusion#2` (`tests/jwt/test_claims.py:256`) | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | C |
| `TestJWTClaims.test_validate_list_inclusion#4` (`tests/jwt/test_claims.py:263`) | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | C |
| `TestJWTClaims.test_validate_list_inclusion#5` (`tests/jwt/test_claims.py:264`) | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | C |

### Reasons

**`test_claim_jti#3`, 2 executions (line 91).** The registry is built with
the option `{"value": "expected"}` and then `{"values": ["expected",
"other"]}`, and the claims are `{"jti": "wrong"}`. The target,
`validate_jti#1`, is the type check of `validate_jti` (lines 158 and 159:
"Claim 'jti' must be a string"). The value is a string, so that check passes,
and `validate_jti` calls `check_value` (line 160), which rejects a value that
does not match the option. The block describes the value options, not the
type of the claim. The rule chose `validate_jti#1` by the name tokens `claim`
and `jti`. Class C.

**`test_claim_jti#5` (line 95).** The registry is built with
`{"essential": True}` and the claims are `{"jti": ""}`. A blank string passes
the type check; `check_value` rejects the blank value (line 64). The block
describes the blank value of an essential claim. Class C.

For these 3 cases both readings of the labels give `validate_jti#1`, the
check that rule 3 chose. The instruction for the labels takes the label from
the words of the test and not from its input, and the test function is named
for the claim. The records show that the check does not fire, and that the
case raises nothing on the copy without `check_value#1`
(`generated/labels/joserfc/outcomes.csv`: "label does not fire and does not
decide then either"). The label and the target of the rule follow the name of
the test function; the input of the block violates the value check.
`LABEL-OUTCOMES.md` reads these cases with the other cases that their agreed
label does not decide.

**`test_validate_aud#1` to `#4` (lines 174, 175, 183 and 184).** The claims
are `{"aud": "b"}` and `{"aud": ["b"]}` against the option `value` `"a"`,
then `{"aud": "c"}` and `{"aud": ["c"]}` against the option `values`
`["a", "b"]`; the comments of the test say "invalid value" and "use option
values". The target, `validate_aud#1`, rejects a value that is neither a
string nor a list of strings (lines 175 to 180). Each of the 4 values is a
string or a list of strings, so `validate_aud` calls `check_value` (line
176), which rejects the value. The blocks describe the value options. The
rule chose `validate_aud#1` by the name tokens `aud` and `validate`. Class C.

**`test_validate_list_inclusion#1`, `#2`, `#4` and `#5` (lines 255, 256, 263
and 264).** The claim is `custom_claim`, which has no method
`validate_custom_claim`; line 102 finds none and line 106 calls
`check_value`. `validate_aud` is not called at all. The rule chose
`validate_aud#1` by the name tokens `list` and `validate`. Class C.

## Counts

Of the 16 flags of `joserfc` under rule 3: class A 3, class C 13 (2 from the
first reading and the 11 above), classes B and D 0.
