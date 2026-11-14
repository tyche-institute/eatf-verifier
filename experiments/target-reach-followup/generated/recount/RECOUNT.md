# Recount from the deposited outputs of target reach

Computed by `recount/recount.py` from the deposited files of `../target-reach` (`generated/<name>/`, `subjects/<name>/`, `readings/<name>/FLAGS.md`). No library was run. `recount/README.md` defines every count. The last column is the sum over the 4 held-out libraries (google-auth, oauthlib, authlib, joserfc).

Sentinels: 315, of which 315 hold.

## Reproduced deposited counts

|  | pyjwt | pyjwt-package | jwcrypto | google-auth | oauthlib | authlib | joserfc | held out, total |
|---|---|---|---|---|---|---|---|---|
| cases | 91 | 91 | 42 | 22 | 142 | 48 | 190 | 402 |
| cases with a target | 49 | 49 | 14 | 15 | 53 | 30 | 131 | 229 |
| decided by the target | 48 | 48 | 10 | 13 | 43 | 18 | 71 | 145 |
| flags | 1 | 1 | 4 | 2 | 10 | 12 | 60 | 84 |
| deciding checks | 44 | 44 | 16 | 13 | 47 | 24 | 53 | 137 |
| deletions of deciding checks not detected by O_V | 5 | 7 | 4 | 2 | 7 | 3 | 12 | 24 |
| deletions of deciding checks not detected by O_Vfc | 21 | 23 | 6 | 9 | 11 | 8 | 29 | 57 |
| deletions of deciding checks not detected by O_C | 3 | 3 | 0 | 1 | 0 | 3 | 2 | 6 |
| deletions of deciding checks not detected by O_T | 12 | 14 | 11 | 6 | 34 | 10 | 32 | 82 |
| deletions of deciding checks not detected by whole suite | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 5 |

## 1. O_T against its own denominator

|  | pyjwt | pyjwt-package | jwcrypto | google-auth | oauthlib | authlib | joserfc | held out, total |
|---|---|---|---|---|---|---|---|---|
| deciding checks | 44 | 44 | 16 | 13 | 47 | 24 | 53 | 137 |
| deciding checks deleted | 41 | 44 | 16 | 13 | 47 | 24 | 53 | 137 |
| all deleted deciding checks: not detected by O_V | 5 | 7 | 4 | 2 | 7 | 3 | 12 | 24 |
| all deleted deciding checks: not detected by O_Vfc | 21 | 23 | 6 | 9 | 11 | 8 | 29 | 57 |
| all deleted deciding checks: not detected by O_C | 3 | 3 | 0 | 1 | 0 | 3 | 2 | 6 |
| all deleted deciding checks: not detected by O_T | 12 | 14 | 11 | 6 | 34 | 10 | 32 | 82 |
| all deleted deciding checks: not detected by O_S | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 5 |
| all deleted deciding checks: not detected by suite | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 5 |
| all deleted deciding checks: not detected by whole suite | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 5 |
| targeted deciding checks | 30 | 30 | 4 | 7 | 13 | 14 | 21 | 55 |
| targeted deciding checks: deleted | 29 | 30 | 4 | 7 | 13 | 14 | 21 | 55 |
| targeted deciding checks: not detected by O_V | 4 | 5 | 1 | 1 | 3 | 0 | 5 | 9 |
| targeted deciding checks: not detected by O_Vfc | 15 | 16 | 2 | 4 | 4 | 2 | 11 | 21 |
| targeted deciding checks: not detected by O_C | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| targeted deciding checks: not detected by O_T | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| targeted deciding checks: not detected by O_S | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| targeted deciding checks: not detected by suite | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| targeted deciding checks: not detected by whole suite | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| deciding checks that are the target of no case | 14 | 14 | 12 | 5 | 33 | 10 | 32 | 80 |
| deciding checks that are the target of no case: deleted | 12 | 14 | 12 | 5 | 33 | 10 | 32 | 80 |
| deciding checks that are the target of no case: not detected by O_V | 1 | 2 | 3 | 1 | 4 | 3 | 7 | 15 |
| deciding checks that are the target of no case: not detected by O_Vfc | 6 | 7 | 4 | 5 | 7 | 6 | 18 | 36 |
| deciding checks that are the target of no case: not detected by O_C | 0 | 0 | 0 | 1 | 0 | 3 | 2 | 6 |
| deciding checks that are the target of no case: not detected by O_T | 12 | 14 | 11 | 5 | 33 | 10 | 32 | 80 |
| deciding checks that are the target of no case: not detected by O_S | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 5 |
| deciding checks that are the target of no case: not detected by suite | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 5 |
| deciding checks that are the target of no case: not detected by whole suite | 0 | 0 | 0 | 0 | 0 | 3 | 2 | 5 |
| deciding checks that are a target only of cases they do not decide | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 |
| deciding checks that are a target only of cases they do not decide: deleted | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 |
| deciding checks that are a target only of cases they do not decide: not detected by O_V | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| deciding checks that are a target only of cases they do not decide: not detected by O_Vfc | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| deciding checks that are a target only of cases they do not decide: not detected by O_C | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| deciding checks that are a target only of cases they do not decide: not detected by O_T | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 |
| deciding checks that are a target only of cases they do not decide: not detected by O_S | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| deciding checks that are a target only of cases they do not decide: not detected by suite | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| deciding checks that are a target only of cases they do not decide: not detected by whole suite | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cases decided by their target (O_T holds at baseline) | 48 | 48 | 10 | 13 | 43 | 18 | 71 | 145 |

## 2. Checks that fire and never decide

|  | pyjwt | pyjwt-package | jwcrypto | google-auth | oauthlib | authlib | joserfc | held out, total |
|---|---|---|---|---|---|---|---|---|
| checks that fire and never decide | 0 | 0 | 17 | 0 | 0 | 0 | 2 | 2 |
| deleted | 0 | 0 | 17 | 0 | 0 | 0 | 2 | 2 |
| not detected by O_V | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 |
| not detected by O_Vfc | 0 | 0 | 8 | 0 | 0 | 0 | 2 | 2 |
| not detected by O_C | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| not detected by O_T | 0 | 0 | 16 | 0 | 0 | 0 | 2 | 2 |
| not detected by O_S | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| not detected by suite | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| not detected by whole suite | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |

jwcrypto: `jwa._AesKw._get_key#2`, `jwa._EcdhEs.unwrap#1`, `jwa._RSA._check_key#1`, `jwa._RSA.unwrap#1`, `jwe.JWE._decrypt#1`, `jwe.JWE._decrypt#2`, `jwe.JWE._decrypt#3`, `jwe.JWE._decrypt#4`, `jwe.JWE._decrypt#5`, `jwe.JWE._jwa_enc#1`, `jwe.JWE._jwa_keymgmt#1`, `jwe.JWE.deserialize#1`, `jws.JWS._merge_check_headers#1`, `jws.JWS._verify#3`, `jws.JWS._verify#7`, `jws.JWS.deserialize#1`, `jws.JWSCore.verify#1`

joserfc: `_rfc7518.ec_key.ECKey.exchange_derive_key#1`, `_rfc8037.okp_key.OKPKey.exchange_derive_key#1`

## 3. Cases decided by a statement that is not a check

|  | pyjwt | pyjwt-package | jwcrypto | google-auth | oauthlib | authlib | joserfc | held out, total |
|---|---|---|---|---|---|---|---|---|
| cases | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 6 |

### authlib

| case | index | file | line | statement | kind | class label in checks.json | reason in checks.json | guard in checks.json |
|---|---|---|---|---|---|---|---|---|
| `tests/jose/test_jws.py::test_invalid_input#1` | 0 | `authlib/jose/util.py` | 33 | `raise error_cls(msg) from exc` | other raise | `?error_cls` | not a rejection class | `except (TypeError, binascii.Error) as exc` |
| `tests/jose/test_jws.py::test_invalid_input#2` | 0 | `authlib/jose/util.py` | 18 | `raise error_cls(f"Invalid header string: {e}") from e` | other raise | `?error_cls` | not a rejection class | `except ValueError as e` |
| `tests/jose/test_jws.py::test_invalid_input#3` | 0 | `authlib/jose/util.py` | 21 | `raise error_cls("Header must be a json object")` | other raise | `?error_cls` | not a rejection class | `not isinstance(header, dict)` |
| `tests/jose/test_jws.py::test_invalid_input#4` | 0 | `authlib/jose/util.py` | 33 | `raise error_cls(msg) from exc` | other raise | `?error_cls` | not a rejection class | `except (TypeError, binascii.Error) as exc` |
| `tests/jose/test_jws.py::test_invalid_input#5` | 0 | `authlib/jose/util.py` | 33 | `raise error_cls(msg) from exc` | other raise | `?error_cls` | not a rejection class | `except (TypeError, binascii.Error) as exc` |
| `tests/jose/test_jws.py::test_invalid_input#6` | 0 | `authlib/jose/util.py` | 33 | `raise error_cls(msg) from exc` | other raise | `?error_cls` | not a rejection class | `except (TypeError, binascii.Error) as exc` |

The pinning table of authlib has 2 denominators. The 48 cases of the study include 6 whose raise site is no check (the rows above); pinning deletes the deciding check of a case, so these 6 have nothing to delete and are not counted, and 0 cases have a deciding check that was not deleted. That leaves 42 counted cases (42 in summary.json). Among the class-only cases the same difference holds: 46 class-only cases of the study, 6 of them without a deciding check, 40 class-only cases in the pinning table.

## 4. Flags per tier and per class

The classes are a reading of the sources (`readings/<name>/FLAGS.md`) and are reported apart from the mechanical counts. PyJWT has no reading of its flag.

|  | pyjwt | pyjwt-package | jwcrypto | google-auth | oauthlib | authlib | joserfc | held out, total |
|---|---|---|---|---|---|---|---|---|
| assertion tier: cases with a target | 42 | 42 | 6 | 0 | 25 | 5 | 99 | 129 |
| assertion tier: decided by the target | 42 | 42 | 6 | 0 | 25 | 5 | 46 | 76 |
| assertion tier: flags | 0 | 0 | 0 | 0 | 0 | 0 | 53 | 53 |
| assertion tier: flags of class A | not read | not read | 0 | 0 | 0 | 0 | 0 | 0 |
| assertion tier: flags of class B | not read | not read | 0 | 0 | 0 | 0 | 0 | 0 |
| assertion tier: flags of class C | not read | not read | 0 | 0 | 0 | 0 | 53 | 53 |
| assertion tier: flags of class D | not read | not read | 0 | 0 | 0 | 0 | 0 | 0 |
| name tier: cases with a target | 7 | 7 | 8 | 15 | 28 | 25 | 32 | 100 |
| name tier: decided by the target | 6 | 6 | 4 | 13 | 18 | 13 | 25 | 69 |
| name tier: flags | 1 | 1 | 4 | 2 | 10 | 12 | 7 | 31 |
| name tier: flags of class A | not read | not read | 0 | 0 | 0 | 0 | 3 | 3 |
| name tier: flags of class B | not read | not read | 3 | 0 | 0 | 0 | 0 | 0 |
| name tier: flags of class C | not read | not read | 1 | 2 | 10 | 12 | 4 | 28 |
| name tier: flags of class D | not read | not read | 0 | 0 | 0 | 0 | 0 | 0 |

### Flags whose own test still passes on the copy without the deciding check

| subject | case | index | class (reading) | deleted deciding check | class raised then | site then | what the case does |
|---|---|---|---|---|---|---|---|
| authlib | `tests/jose/test_jws.py::test_fail_deserialize_json#3` | 0 | C | `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#1` | `authlib.jose.errors.DecodeError` | `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2` | same class, another check |
| authlib | `tests/jose/test_jws.py::test_fail_deserialize_json#4` | 0 | C | `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2` | `authlib.jose.errors.DecodeError` | `other raise (authlib/jose/util.py:18 raise error_cls(f"Invalid header string: {e}") from e)` | same class, other raise |
| joserfc | `tests/jwe/test_compact.py::TestJWECompact.test_ciphertext_exceeds_size#0` | 0 | A | `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | `joserfc.errors.ExceededSizeError` | `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1` | same class, another check |
| joserfc | `tests/jws/test_compact.py::TestCompact.test_payload_exceeded_size_error#0` | 0 | A | `_rfc7515.registry.JWSRegistry.validate_compact_value_size#1` | `joserfc.errors.ExceededSizeError` | `_rfc7515.registry.JWSRegistry.validate_payload_size#1` | same class, another check |
| joserfc | `tests/jws/test_json.py::TestJSON.test_b64_must_be_protected#1` | 0 | A | `registry.reject_unprotected_crit_header#2` | `joserfc.errors.UnsupportedHeaderError` | `_rfc7797.json._is_payload_base64_encoded#1` | same class, another check |

## 5. PyJWT: the flag and the pinning passes

### pyjwt

| case | test | target | deciding check | target fires | own test without the target | block asserts | pattern | assertions after the block |
|---|---|---|---|---|---|---|---|---|
| `tests/test_api_jwt.py::TestJWT.test_raise_exception_invalid_audience_list#0` | `tests/test_api_jwt.py::TestJWT::test_raise_exception_invalid_audience_list` | `api_jwt.PyJWT._validate_aud#6` | `api_jwt.PyJWT._validate_aud#7` | no | passes | class only |  | `[]` |

| case whose own test passes without its deciding check | deleted check | block asserts | pattern | assertions after the block | class raised then | site then |
|---|---|---|---|---|---|---|
| `tests/test_api_jws.py::TestJWS.test_decodes_with_jwk_and_mismatched_algorithm#0` | `api_jws.PyJWS._verify_signature#2` | class only |  | `[]` | `jwt.exceptions.InvalidAlgorithmError` | `api_jws.PyJWS._verify_signature#3` |

### pyjwt-package

| case | test | target | deciding check | target fires | own test without the target | block asserts | pattern | assertions after the block |
|---|---|---|---|---|---|---|---|---|
| `tests/test_api_jwt.py::TestJWT.test_raise_exception_invalid_audience_list#0` | `tests/test_api_jwt.py::TestJWT::test_raise_exception_invalid_audience_list` | `api_jwt.PyJWT._validate_aud#6` | `api_jwt.PyJWT._validate_aud#7` | no | passes | class only |  | `[]` |

| case whose own test passes without its deciding check | deleted check | block asserts | pattern | assertions after the block | class raised then | site then |
|---|---|---|---|---|---|---|
| `tests/test_api_jws.py::TestJWS.test_decodes_with_jwk_and_mismatched_algorithm#0` | `api_jws.PyJWS._verify_signature#2` | class only |  | `[]` | `jwt.exceptions.InvalidAlgorithmError` | `api_jws.PyJWS._verify_signature#3` |

## 6. Checks inside an except handler

|  | pyjwt | pyjwt-package | jwcrypto | google-auth | oauthlib | authlib | joserfc | held out, total |
|---|---|---|---|---|---|---|---|---|
| checks in a handler | 16 | 19 | 19 | 6 | 4 | 4 | 15 | 29 |
| of them deciding | 9 | 9 | 2 | 3 | 2 | 3 | 12 | 20 |
| cases they decide | 26 | 26 | 4 | 9 | 2 | 4 | 32 | 47 |
| of them deleted | 9 | 9 | 3 | 3 | 2 | 3 | 12 | 20 |

## Sentinels

All 315 sentinels hold. Per subject they cover: the counts of summary.json reproduced from the CSV files; the CSV files against the first baseline record, targets.json and each other; and the reading FLAGS.md against the flags. The totals over the 4 held-out libraries equal the fixed values 402, 229, 145, 84, 137 and 24, 57, 6, 82, 5.

