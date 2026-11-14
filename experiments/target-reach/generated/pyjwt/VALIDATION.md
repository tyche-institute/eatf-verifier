# Validation on PyJWT 2.15.1

Reference: `../mutation-adequacy-pyjwt/` (`checks.json`, `cases.json`, `generated/cases.csv`, `generated/deletions.csv`), read-only. Check ids are mapped through (function, raise numbers); the reference numbers raise statements from 0, this toolkit from 1, so 1 is added to the reference numbers.

## 1. Checks

- Reference checks in `jwt/api_jws.py` and `jwt/api_jwt.py`: 44.
- Toolkit checks in the 2 files: 46 (46 reachable).
- Equal as (function, raise numbers): 44; only in the toolkit: 2; only in the reference: 0.
- Classes differ on 0 common checks.
- Reference external checks in `jwt/algorithms.py` found among the observed file's reachable checks: 5 of 5 (the toolkit finds 8 reachable checks there).

Checks only in the toolkit (the reference lists their functions as outside the subject, since they only encode; the toolkit marks them reachable because `PyJWS._load` calls `jwt.encode("utf-8")` on its `jwt` argument, and the name rule `X.f` resolves `encode` to `PyJWS.encode`; `PyJWS.encode` is then reachable, and from it `PyJWT.encode` and `PyJWT._encode_payload`):

- `api_jws.PyJWS.encode#1` InvalidTokenError `Invalid 'crit' header: must be a list`, raise numbers [1], reachable: True
- `api_jws.PyJWS.encode#2` InvalidKeyError `{*}`, raise numbers [2], reachable: True

Toolkit reachable checks of `jwt/algorithms.py` that the reference does not list as external checks: `algorithms.Algorithm.check_crypto_key_type#1`, `algorithms.OKPAlgorithm.prepare_key#1`, `algorithms.RSAAlgorithm.prepare_key#1`. No case reaches them at baseline unless listed under 3.

## 2. Blocks

- Reference included blocks: 79 (of 212 `with pytest.raises` blocks, 82 calling a decode function).
- Toolkit included blocks: 79 (of 215 blocks, 82 with an entry-point call; the toolkit also counts the 3 callable-form `pytest.raises` uses of the suite, none of which is included).
- Equal as (file, test, k): 79; only in the toolkit: 0; only in the reference: 0.
- Blocks whose expected class was read through a local assignment in the test: `tests/test_api_jwt.py::TestJWT.test_decode_raises_clean_error_if_claim_is_non_numeric_type#0`.

## 3. Sites

- Reference baseline cases: 91; toolkit baseline cases: 91; reference cases absent from the toolkit record: 0; toolkit cases not in the reference: 0.
- Baseline site check equal (check level, segments ignored): 91 of 91; different: 0.

## 4. Targets

Rule `reach-target-rule/2`. Version 1 of the rule was written without the hand labels and gave 37 equal, 1 different, 1 rule only, 31 hand only and 9 neither. Version 2 was written after that comparison: an assertion that a message with a placeholder cannot satisfy now excludes the check, and a check whose literal message text satisfies an assertion is preferred before the name of the test is read. Reference hand labels: 69 of 79 included blocks; rule targets: 48 of 79. Unit: the included block (the block in `test_decode_raises_clean_error_if_claim_is_non_numeric_type` has 1 hand label per value of its `claim` parameter; it counts as equal only if all 3 equal the rule's target).

| Cell | Blocks |
|---|---|
| both, equal | 47 |
| both, different | 0 |
| rule only | 1 |
| hand only | 22 |
| neither | 9 |

By basis of the rule:

| Basis or reason | both, equal | both, different | rule only | hand only | neither |
|---|---|---|---|---|---|
| assert | 14 | 0 | 0 | 0 | 0 |
| assert+name | 4 | 0 | 0 | 0 | 0 |
| assert-literal | 19 | 0 | 0 | 0 | 0 |
| class | 8 | 0 | 0 | 0 | 0 |
| name | 2 | 0 | 1 | 0 | 0 |
| none: no name token matches | 0 | 0 | 0 | 14 | 8 |
| none: tie | 0 | 0 | 0 | 8 | 1 |

Both labelled, different:


Rule only (no hand label):

- `test_raise_exception_invalid_audience_list`: rule `api_jwt.PyJWT._validate_aud#6` (name); hand: InvalidAudienceError only; 'invalid audience' is one check's message and another check's condition

Hand only (the rule gives no target):

- `test_jwt_encode_decode_rejects_wrong_curve`: hand alg.ec-curve; rule: tie; top candidates ['algorithms.ECAlgorithm._validate_curve#1', 'api_jws.PyJWS.encode#2']
- `test_pyjwt_decode_enforces_short_hmac_key`: hand jws.key-length; rule: tie; top candidates ['api_jws.PyJWS._verify_signature#5', 'api_jws.PyJWS.encode#2']
- `test_pyjwt_decode_honors_per_call_enforce_minimum_key_length`: hand jws.key-length; rule: tie; top candidates ['api_jws.PyJWS._verify_signature#5', 'api_jws.PyJWS.encode#2']
- `test_pyjwt_decode_honors_per_call_enforce_minimum_key_length`: hand jws.key-length; rule: tie; top candidates ['api_jws.PyJWS._verify_signature#5', 'api_jws.PyJWS.encode#2']
- `test_decode_fails_when_alg_is_not_on_method_algorithms_param`: hand jws.alg-allowed; rule: tie; top candidates ['api_jws.PyJWS._verify_signature#2', 'api_jws.PyJWS._verify_signature#3']
- `test_decode_with_non_mapping_header_throws_exception`: hand jws.header-object; rule: no name token matches; top candidates ['api_jws.PyJWS._load#3', 'api_jws.PyJWS._load#4']
- `test_verify_signature_with_no_algo_header_throws_exception`: hand jws.alg-present; rule: no name token matches; top candidates ['api_jws.PyJWS._verify_signature#1', 'api_jws.PyJWS._verify_signature#2']
- `test_decode_invalid_header_padding`: hand jws.segment-encoding; rule: tie; top candidates ['api_jws.PyJWS._decode_base64url_segment#1', 'api_jws.PyJWS._load#3']
- `test_decode_deeply_nested_header_throws_decode_error`: hand jws.header-json; rule: no name token matches; top candidates ['api_jws.PyJWS._load#3', 'api_jws.PyJWS._load#4']
- `test_decode_invalid_payload_padding`: hand jws.segment-encoding; rule: tie; top candidates ['api_jws.PyJWS._decode_base64url_segment#1', 'api_jwt.PyJWT._decode_payload#1']
- `test_decode_rejects_detached_payload_for_attached_content`: hand jws.detached-requires-b64-false; rule: no name token matches; top candidates ['api_jws.PyJWS.decode_complete#2', 'api_jws.PyJWS.decode_complete#4']
- `test_decode_with_non_mapping_payload_throws_exception`: hand jwt.payload-object; rule: no name token matches; top candidates ['api_jwt.PyJWT._decode_payload#1', 'api_jwt.PyJWT._decode_payload#2']
- `test_decode_raises_clean_error_if_claim_is_non_numeric_type`: hand by parameter; rule: tie; top candidates ['api_jwt.PyJWT._validate_exp#1', 'api_jwt.PyJWT._validate_nbf#1']
- `test_decode_with_notbefore`: hand jwt.nbf-future; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_iat#2', 'api_jwt.PyJWT._validate_nbf#2']
- `test_decode_with_notbefore_with_leeway`: hand jwt.nbf-future; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_iat#2', 'api_jwt.PyJWT._validate_nbf#2']
- `test_check_audience_none_specified`: hand jwt.aud-unexpected; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_aud#1', 'api_jwt.PyJWT._validate_aud#3']
- `test_rasise_exception_on_partial_issuer_match`: hand jwt.iss-match; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_iss#2', 'api_jwt.PyJWT._validate_iss#3']
- `test_raise_exception_invalid_issuer`: hand jwt.iss-match; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_iss#2', 'api_jwt.PyJWT._validate_iss#3']
- `test_raise_exception_invalid_issuer_list`: hand jwt.iss-match; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_iss#2', 'api_jwt.PyJWT._validate_iss#3']
- `test_decode_missing_sub_but_required_claim`: hand jwt.required; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_aud#2', 'api_jwt.PyJWT._validate_iss#1']
- `test_decode_invalid_int_sub_claim`: hand jwt.sub-type; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_sub#1', 'api_jwt.PyJWT._validate_sub#2']
- `test_decode_missing_jti_when_required_claim`: hand jwt.required; rule: no name token matches; top candidates ['api_jwt.PyJWT._validate_aud#2', 'api_jwt.PyJWT._validate_iss#1']

## 5. Deletions

- Reference reached checks deleted: 41; toolkit deletions: 41; toolkit deletions not in the reference set: 0.
- Agreement on detection: O_V 41 of 41, O_Vfc 41 of 41, O_C 41 of 41.
- Not detected, reference: {"O_V": 5, "O_V^fc": 21, "O_C": 3, "O_T": 2, "O_S": 0}; toolkit: {"O_V": 5, "O_Vfc": 21, "O_C": 3, "O_T": 12, "O_S": 0, "suite": 0}.

Sentinels of `analyse.py`: all pass.

O_T and O_S, reported without comparison (O_T uses the rule's targets, O_S is the test's outcome here and the block's own assertions in the reference):

| Check | Toolkit id | O_T ref | O_T toolkit | O_S ref | O_S toolkit | suite toolkit |
|---|---|---|---|---|---|---|
| jws.alg-allowed | `api_jws.PyJWS._verify_signature#2` | yes | no | yes | yes | yes |
| jws.alg-present | `api_jws.PyJWS._verify_signature#1` | yes | no | yes | yes | yes |
| jws.alg-required | `api_jws.PyJWS.decode_complete#1` | yes | yes | yes | yes | yes |
| jws.alg-supported | `api_jws.PyJWS._verify_signature#4` | yes | yes | yes | yes | yes |
| jws.b64-empty-payload | `api_jws.PyJWS._load#5` | yes | yes | yes | yes | yes |
| jws.b64-requires-crit | `api_jws.PyJWS.decode_complete#3` | yes | yes | yes | yes | yes |
| jws.b64-requires-detached | `api_jws.PyJWS.decode_complete#4` | yes | yes | yes | yes | yes |
| jws.crit-list | `api_jws.PyJWS._validate_crit#1` | yes | yes | yes | yes | yes |
| jws.crit-present | `api_jws.PyJWS._validate_crit#4` | yes | yes | yes | yes | yes |
| jws.crit-strings | `api_jws.PyJWS._validate_crit#2` | yes | yes | yes | yes | yes |
| jws.crit-supported | `api_jws.PyJWS._validate_crit#3` | yes | yes | yes | yes | yes |
| jws.detached-requires-b64-false | `api_jws.PyJWS.decode_complete#2` | yes | no | yes | yes | yes |
| jws.header-json | `api_jws.PyJWS._load#3` | no | no | yes | yes | yes |
| jws.header-object | `api_jws.PyJWS._load#4` | yes | no | yes | yes | yes |
| jws.jwk-alg-match | `api_jws.PyJWS._verify_signature#3` | yes | yes | yes | yes | yes |
| jws.key-length | `api_jws.PyJWS._verify_signature#5` | yes | no | yes | yes | yes |
| jws.segment-encoding | `api_jws.PyJWS._decode_base64url_segment#1` | yes | yes | yes | yes | yes |
| jws.segments | `api_jws.PyJWS._load#2` | yes | yes | yes | yes | yes |
| jws.signature | `api_jws.PyJWS._verify_signature#6` | yes | yes | yes | yes | yes |
| jws.token-type | `api_jws.PyJWS._load#1` | yes | yes | yes | yes | yes |
| jwt.aud-claim-format | `api_jwt.PyJWT._validate_aud#6` | yes | yes | yes | yes | yes |
| jwt.aud-match | `api_jwt.PyJWT._validate_aud#7` | no | no | yes | yes | yes |
| jwt.aud-present | `api_jwt.PyJWT._validate_aud#2` | yes | yes | yes | yes | yes |
| jwt.aud-strict-claim-format | `api_jwt.PyJWT._validate_aud#4` | yes | yes | yes | yes | yes |
| jwt.aud-strict-match | `api_jwt.PyJWT._validate_aud#5` | yes | yes | yes | yes | yes |
| jwt.aud-strict-param | `api_jwt.PyJWT._validate_aud#3` | yes | yes | yes | yes | yes |
| jwt.aud-unexpected | `api_jwt.PyJWT._validate_aud#1` | yes | no | yes | yes | yes |
| jwt.exp-expired | `api_jwt.PyJWT._validate_exp#2` | yes | yes | yes | yes | yes |
| jwt.exp-type | `api_jwt.PyJWT._validate_exp#1` | yes | yes | yes | yes | yes |
| jwt.iat-future | `api_jwt.PyJWT._validate_iat#2` | yes | yes | yes | yes | yes |
| jwt.iat-type | `api_jwt.PyJWT._validate_iat#1` | yes | yes | yes | yes | yes |
| jwt.iss-match | `api_jwt.PyJWT._validate_iss#3` | yes | no | yes | yes | yes |
| jwt.iss-present | `api_jwt.PyJWT._validate_iss#1` | yes | yes | yes | yes | yes |
| jwt.jti-type | `api_jwt.PyJWT._validate_jti#1` | yes | yes | yes | yes | yes |
| jwt.nbf-future | `api_jwt.PyJWT._validate_nbf#2` | yes | no | yes | yes | yes |
| jwt.nbf-type | `api_jwt.PyJWT._validate_nbf#1` | yes | yes | yes | yes | yes |
| jwt.payload-json | `api_jwt.PyJWT._decode_payload#1` | yes | yes | yes | yes | yes |
| jwt.payload-object | `api_jwt.PyJWT._decode_payload#2` | yes | no | yes | yes | yes |
| jwt.required | `api_jwt.PyJWT._validate_required_claims#1` | yes | yes | yes | yes | yes |
| jwt.sub-match | `api_jwt.PyJWT._validate_sub#2` | yes | yes | yes | yes | yes |
| jwt.sub-type | `api_jwt.PyJWT._validate_sub#1` | yes | no | yes | yes | yes |

## 6. Unit tests

`tests/` on the synthetic package: 63 passed, 1 skipped (return code 0).
