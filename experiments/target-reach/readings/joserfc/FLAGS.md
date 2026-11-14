# joserfc 1.8.0: reading of the flags

A flag is a case with a target that the target does not decide. The columns
"target fires" and "own test without the target" are mechanical and come from
`generated/joserfc/flags.csv`. The class is a reading of the sources, with its
reason, and is reported as a reading. Line numbers refer to the commit of the
subject (`subjects/joserfc/subject.json`). Where a block runs more than 1
time in its test, the number in brackets is the execution of the block, as in
the column `index` of `flags.csv`; the rows follow the order of that file.

Classes: **A** the test does not reach its target; **B** the target fires and a
handler replaces its exception; **C** the target the rule assigned is not the
check the test describes; **D** cannot be decided from the sources. The
classes are tried in the order C, A, B, D, and a flag gets the first that
fits.

| Case | Target | Decided by | Target fires | Own test without the target | Class |
|---|---|---|---|---|---|
| `TestJWECompact.test_ciphertext_exceeds_size#0` (`tests/jwe/test_compact.py:276`) | `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1` | `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | no | target not deleted | A |
| `TestJWEJSON.test_decode_multiple_recipients#1` (`tests/jwe/test_json.py:192`) | `_rfc7516.message._perform_decrypt#2` | `_rfc7516.message._perform_decrypt#1` | no | target not deleted | C |
| `TestCompact.test_no_invalid_header#0` (`tests/jws/test_compact.py:51`) | `_rfc7516.compact.extract_compact#3` | `_rfc7515.compact.decode_header#2` | no | passes | C |
| `TestCompact.test_no_invalid_header#1` (`tests/jws/test_compact.py:55`) | `_rfc7516.compact.extract_compact#1` | `_rfc7515.compact.decode_header#1` | no | passes | C |
| `TestCompact.test_payload_exceeded_size_error#0` (`tests/jws/test_compact.py:71`) | `_rfc7515.registry.JWSRegistry.validate_payload_size#1` | `_rfc7515.registry.JWSRegistry.validate_compact_value_size#1` | no | passes | A |
| `TestJSON.test_b64_must_be_protected#1` (`tests/jws/test_json.py:166`) | `_rfc7797.json._is_payload_base64_encoded#1` | `registry.reject_unprotected_crit_header#2` | no | fails | A |
| `TestRFC7797.test_compact_invalid_value_length#0` (`tests/jws/test_rfc7797.py:45`) | `_rfc7516.compact.extract_compact#3` | `_rfc7797.compact.extract_rfc7515_compact#1` | no | passes | C |
| `TestRFC7797.test_compact_missing_alg#0` (`tests/jws/test_rfc7797.py:51`) | `_rfc7516.compact.extract_compact#1` | `_rfc7515.compact.decode_header#1` | no | passes | C |
| `TestRFC7797.test_invalid_header#0` (`tests/jws/test_rfc7797.py:48`) | `_rfc7516.compact.extract_compact#3` | `_rfc7515.compact.decode_header#2` | no | passes | C |
| `TestJWTClaims.test_claim_aud#0` (`tests/jwt/test_claims.py:104`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | C |
| `TestJWTClaims.test_claim_aud#1` (`tests/jwt/test_claims.py:105`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | C |
| `TestJWTClaims.test_claim_aud#2` (`tests/jwt/test_claims.py:106`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_aud#1` | no | passes | C |
| `TestJWTClaims.test_claim_iss#0` (`tests/jwt/test_claims.py:55`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iss#1` | no | passes | C |
| `TestJWTClaims.test_claim_iss#1` (`tests/jwt/test_claims.py:56`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iss#1` | no | passes | C |
| `TestJWTClaims.test_claim_iss#2` (`tests/jwt/test_claims.py:57`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iss#1` | no | passes | C |
| `TestJWTClaims.test_claim_iss#3` (`tests/jwt/test_claims.py:59`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iss#1` | no | passes | C |
| `TestJWTClaims.test_claim_jti#0` (`tests/jwt/test_claims.py:75`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#1` (`tests/jwt/test_claims.py:76`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [0]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [1]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [10]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [11]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [12]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [13]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [14]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [2]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [3]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [4]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [5]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [6]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [7]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [8]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#2 [9]` (`tests/jwt/test_claims.py:84`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_jti#6` (`tests/jwt/test_claims.py:98`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_jti#1` | no | fails | C |
| `TestJWTClaims.test_claim_sub#0` (`tests/jwt/test_claims.py:67`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_sub#1` | no | passes | C |
| `TestJWTClaims.test_claim_sub#1` (`tests/jwt/test_claims.py:68`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_sub#1` | no | passes | C |
| `TestJWTClaims.test_claim_sub#2` (`tests/jwt/test_claims.py:69`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_sub#1` | no | passes | C |
| `TestJWTClaims.test_claim_sub#3` (`tests/jwt/test_claims.py:70`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_sub#1` | no | passes | C |
| `TestJWTClaims.test_decode_then_validate_a_token_that_never_expires#0` (`tests/jwt/test_claims.py:241`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_exp#1` | no | passes | C |
| `TestJWTClaims.test_int_claims#0` (`tests/jwt/test_claims.py:159`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_exp#1` | no | passes | C |
| `TestJWTClaims.test_int_claims#1` (`tests/jwt/test_claims.py:160`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_nbf#1` | no | passes | C |
| `TestJWTClaims.test_int_claims#2` (`tests/jwt/test_claims.py:161`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iat#1` | no | passes | C |
| `TestJWTClaims.test_int_claims#4` (`tests/jwt/test_claims.py:165`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_nbf#1` | no | passes | C |
| `TestJWTClaims.test_validate_iat#0` (`tests/jwt/test_claims.py:214`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iat#1` | no | passes | C |
| `TestJWTClaims.test_validate_nbf#0` (`tests/jwt/test_claims.py:220`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_nbf#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [0]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_exp#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [1]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_exp#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [10]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iat#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [11]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iat#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [12]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iat#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [13]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iat#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [14]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_iat#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [2]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_exp#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [3]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_exp#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [4]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_exp#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [5]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_nbf#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [6]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_nbf#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [7]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_nbf#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [8]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_nbf#1` | no | passes | C |
| `TestJWTClaims.test_validate_time_claims_must_be_finite#0 [9]` (`tests/jwt/test_claims.py:229`) | `_rfc7519.claims.BaseClaimsRegistry.check_value#1` | `_rfc7519.claims.JWTClaimsRegistry.validate_nbf#1` | no | passes | C |

Counts: A 3, B 0, C 57, D 0.

## Reasons

**The 51 flags of the claims tests: C.** `JWTClaimsRegistry.validate` hands
each claim to the method `validate_<name>` found with `getattr`, and only a
claim without such a method to `check_value` (`joserfc/_rfc7519/claims.py`,
lines 100 to 106). The type and time checks of the registered claims sit in
those methods: `validate_iss#1` (line 138), `validate_sub#1` (line 151),
`validate_jti#1` (line 159), `validate_aud#1` (lines 178 to 180),
`validate_exp#1` (line 192), `validate_nbf#1` (lines 207 and 209) and
`validate_iat#1` (lines 219 and 221). No call names them, so none is
reachable by name (`reachable` is false for all 7 in
`subjects/joserfc/checks.json`), and the only reachable check of class
`InvalidClaimError` is `BaseClaimsRegistry.check_value#1` (lines 64 to 86).
The rule gave it to each of the blocks below from the class alone (basis `class`, assertion tier, a
candidate set of 1 in `subjects/joserfc/targets.json`). `check_value` rejects
a blank value, a value outside `values` or a value other than `value`, and
returns at once for a claim that has no option (lines 58 to 60). The inputs
of these blocks are wrong types or wrong times:

- `test_claim_aud` [blocks `#0` to `#2`] (`tests/jwt/test_claims.py`, lines
  101 to 106) gives `aud` the values `1`, `True` and `{"a": "b"}` with the
  only option `essential`. The test describes the type check
  `validate_aud#1`; `check_value` accepts all 3 values, since none is blank
  and no `value` or `values` is set.
- `test_claim_iss` [blocks `#0` to `#3`] (lines 53 to 62) gives `iss` the
  values `True`, `["a"]`, `{"a": "b"}` and `1`, and block `#3` asserts that
  the description names `'iss'`. The test describes `validate_iss#1`, "Claim
  'iss' must be a StringOrURI value"; `check_value` accepts the 4 values.
- `test_claim_sub` [blocks `#0` to `#3`] (lines 65 to 70): the same for
  `sub`, with `1`, `True`, `["a"]` and `{"a": "b"}`; the test describes
  `validate_sub#1`.
- `test_claim_jti` blocks `#0` and `#1` (lines 73 to 76) give `["expected"]`
  and `1` to a registry with no option, for which `check_value` returns at
  once; the test describes `validate_jti#1`, "Claim 'jti' must be a string".
  Block `#2` (lines 78 to 87) runs 15 times: 3 option sets (none, `value`,
  `values`) times 5 values that are not strings (`None`, `1`, `True`,
  `["other", "expected"]`, `{"jti": "expected"}`), and asserts that the
  exception names the claim `jti` and that its description holds `'jti'`.
  The loop over option sets, with the empty set first, shows that the block
  describes the rejection of a value that is not a string whatever the
  options, which is `validate_jti#1`: under the empty option set
  (executions 0 to 4) `check_value` cannot reject, and under `value` or
  `values` it accepts the list `["other", "expected"]` (lines 69 to 70 and
  82 to 83; executions 8 and 13). Block `#6` (line 98) gives `[]` under
  `allow_blank`, which `check_value` accepts (line 63); it is rejected
  because it is not a string, `validate_jti#1`.
- `test_decode_then_validate_a_token_that_never_expires#0` (lines 237 to
  241) validates a decoded `exp` of NaN (not a number) with no option. The comment and the
  name describe `validate_exp#1`, "Claim 'exp' must be a NumericDate value",
  through `_validate_numeric_time` (lines 225 to 229).
- `test_int_claims` blocks `#0`, `#1` and `#2` (lines 159 to 161) give the
  string `"s"` to `exp`, `nbf` and `iat`; block `#4` (line 165) gives an
  `nbf` 100 s in the future. No option is set. The blocks describe
  `validate_exp#1`, `validate_nbf#1`, `validate_iat#1` and `validate_nbf#1`
  ("The token is not yet valid", line 209).
- `test_validate_iat#0` (line 214) and `test_validate_nbf#0` (line 220) give
  a time 1000 s ahead with a leeway of 500 s and no option: they describe
  `validate_iat#1` (line 221) and `validate_nbf#1` (line 209).
- `test_validate_time_claims_must_be_finite#0` (lines 222 to 229) runs 15
  times over `exp`, `nbf` and `iat` with NaN, both infinities, `True` and
  `False`, and no option. The comment and the name describe the NumericDate
  checks `validate_exp#1` (executions 0 to 4), `validate_nbf#1` (5 to 9) and
  `validate_iat#1` (10 to 14).

In every one of the 51 cases the check that decides is the check the test
describes. The own test passes without `check_value#1` for all but the 18
cases of `test_claim_jti`, whose blocks at lines 91 and 95, with the options
`value`, `values` and `essential`, need it.

**The 5 flags of the JSON Web Signature (JWS) compact tests: C.** `jws.deserialize_compact` calls
`extract_compact` (`joserfc/jws.py`, line 186), which `jws.py` imports as an
alias of `extract_rfc7515_compact` from `joserfc/_rfc7797/compact.py`
(lines 31 to 33 of `jws.py`). That function rejects a value that does not
have 3 segments (`_rfc7797/compact.py`, lines 46 to 48, check
`_rfc7797.compact.extract_rfc7515_compact#1`) and decodes the header with
`decode_header` (line 57), which raises `MissingAlgorithmError` when `alg` is
absent and `DecodeError` "Invalid header" when the header is not base64url
JSON (`joserfc/_rfc7515/compact.py`, lines 47 to 54, checks
`_rfc7515.compact.decode_header#1` and `#2`). Reachability goes by name, and
the only function definition named `extract_compact` is the one of JSON Web
Encryption (JWE) in `joserfc/_rfc7516/compact.py`, lines 36 to 77; so
`extract_rfc7515_compact` and `decode_header` are not reachable
(`checks.json`), and the candidates of the rule were the JWE checks
`_rfc7516.compact.extract_compact#1` (line 52, `MissingAlgorithmError`) and
`#3` (line 56, `DecodeError` "Invalid header"), which no JWS call runs.

- `TestCompact.test_no_invalid_header#0` (`tests/jws/test_compact.py`, lines
  49 to 51), comment "invalid base64": the header `abc` fails
  `urlsafe_b64decode` (`joserfc/util.py`, lines 28 to 34), and the test
  describes `decode_header#2`. The rule chose the JWE check by the tokens
  `header` and `invalid` of the name (name tier).
- `TestCompact.test_no_invalid_header#1` (lines 53 to 55), comment "no alg
  value": the header `{"a": "b"}` describes `decode_header#1`. The rule had 1
  reachable candidate of class `MissingAlgorithmError`, the JWE check
  (assertion tier).
- `TestRFC7797.test_compact_invalid_value_length#0`
  (`tests/jws/test_rfc7797.py`, lines 44 to 45) gives `a.b.c.d.e`, 5
  segments: the test describes `extract_rfc7515_compact#1`, "Invalid JSON
  Web Signature" (name tier).
- `TestRFC7797.test_invalid_header#0` (lines 47 to 48) gives `a.b.c`, whose
  header of 1 character cannot be decoded (`joserfc/util.py`, lines 28 to
  30): the test describes `decode_header#2` (name tier).
- `TestRFC7797.test_compact_missing_alg#0` (lines 50 to 51) gives the header
  `e30`, which is `{}`: the test describes `decode_header#1` (assertion
  tier).

The own test passes without the target in all 5, because the JWE check
never runs on these inputs.

**`TestJWEJSON.test_decode_multiple_recipients#1`: C.** The block
(`tests/jwe/test_json.py`, lines 191 to 198) decrypts a token with 2
recipients, under `verify_all_recipients=False`, with a fresh symmetric key
that opens neither. Each recipient fails, the handler drops the error
(`joserfc/_rfc7516/message.py`, lines 126 to 128), the set of content
keys stays empty, and `_perform_decrypt#1` raises "Invalid recipients"
(lines 133 to 134). That is the check the input describes. The target
`_perform_decrypt#2`, "Multiple 'cek' found" (lines 136 to 137), needs 2
different content keys; the rule took it from the token `multiple` of the
test name, which refers to the 2 recipients.

**`TestJWECompact.test_ciphertext_exceeds_size#0`: A.** The test
(`tests/jwe/test_compact.py`, lines 272 to 276) builds a compact JWE whose
ciphertext segment is the encoding of 70000 bytes, 93334 characters, against
a limit of 65536 (`joserfc/_rfc7516/registry.py`, line 62). Its name and
input describe `validate_ciphertext_size#1` (lines 138 to 140), the target.
Before the segments are checked, `extract_compact` checks the whole value
(`joserfc/_rfc7516/compact.py`, line 37) against the sum of the 5 segment
limits, 67712 characters, and `validate_compact_value_size#1` (lines 113 to
122 of the registry) rejects it first. The target never fires in a case of
the study and was not deleted. On the copy without the deciding check the
target decides this case (`generated/joserfc/undetected.csv`).

**`TestCompact.test_payload_exceeded_size_error#0`: A.** The test
(`tests/jws/test_compact.py`, lines 67 to 71) builds a compact JWS whose
payload segment is the encoding of 128001 bytes, 170668 characters, against
a limit of 128000 (`joserfc/_rfc7515/registry.py`, line 53). Its name and
input describe `validate_payload_size#1` (lines 113 to 115), the target.
`extract_rfc7515_compact` checks the whole value first
(`joserfc/_rfc7797/compact.py`, line 44), and
`validate_compact_value_size#1` (registry, lines 104 to 107; limit 129536)
rejects it. Without the target the own test still passes; without the
deciding check the target decides this case (`undetected.csv`).

**`TestJSON.test_b64_must_be_protected#1`: A.** The test
(`tests/jws/test_json.py`, lines 158 to 166) puts `b64` in the unprotected
header twice: block `#0` with a protected header `{"alg": "HS256"}`, block
`#1` with a protected header that also lists `b64` in `crit`. The name and
both inputs describe the rule that `b64` must be protected, which is the
target `_rfc7797.json._is_payload_base64_encoded#1`, "'b64' header MUST be
protected" (`joserfc/_rfc7797/json.py`, lines 114 to 115); it decides block
`#0` (`generated/joserfc/cases.csv`). In block `#1`, `_is_payload_base64_encoded`
first calls `check_json_member_headers` (line 113), which calls
`reject_unprotected_crit_header` (`joserfc/_rfc7515/json.py`, line 169), and
that function rejects any name listed in `crit` that stands in the
unprotected header and not in the protected one
(`joserfc/registry.py`, lines 224 to 230, check
`registry.reject_unprotected_crit_header#2`), with the text "'b64' header
MUST be protected". The target is not reached. On the copy without the
deciding check the target decides block `#1` and the test still passes
(`generated/joserfc/pinning.csv`); the own test fails without the target
because block `#0` needs it.

## What the flags of this library show

57 of the 60 flags are wrong targets of the rule, 53 of them in the
assertion tier and 4 in the name tier. 51 of the 53 have the same target,
`check_value#1`: the type and time checks of the claims registry are called
through `getattr` and are not reachable by name, so `check_value#1` was the
only candidate of its class. The other 2 of the assertion tier and 3 of the
name tier are JWS compact tests: the alias of `extract_compact` in `jws.py`
leaves the JWS checks unreachable by name, and the rule took checks of the
JWE function of that name. The 4th of the name tier took another check of
the function that decides, from a token of the test name. In all 57 the
check that decides is the check the test describes. The other 3 flags, all
in the name tier, are tests that describe their target and whose input
another check rejects first: 2 size tests whose inputs exceed the limit on
the whole compact value as well, and 1 test whose input the check on
protected critical headers rejects before the `b64` rule. No flag has a
target that fires.
