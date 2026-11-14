# authlib 1.9.5: the deletions that the whole suite does not detect

24 checks fire in the negative tests of the study, and all 24 decide at least
1 case. The whole suite (1211 tests that pass in both unmodified runs)
detects the deletion of 21 of them and misses 3. Each of the 3 decides
exactly 1 case and fires in no other; none of the 3 stands in a handler: the
column `in_handler` of `generated/authlib/deletions.csv` is "no" for all 3.
In each, the case that the check decides is still rejected after the
deletion, with the same class, by a statement that runs later on the same
path.

The facts below come from `generated/authlib/undetected.csv` (every case in
which the deleted check fires, before and after the deletion) and from
`generated/authlib/deletions.csv`. The last column of the table says "yes"
only where a witness file holds. A witness file is a file of new tests in
`witnesses/authlib/`; it *holds* when every test of it passes on the
unmodified copy and at least 1 of them fails on the copy without the check
(table of witness files in `generated/authlib/SUMMARY.md`). Each witness test
is written to fail only when the library accepts the input. The recorded
message of each of the 2 failures is "DID NOT RAISE" followed by the
rejection class: the call returned without an exception. Where no witness
file holds, the column says "no input found", and the reasons given below
are a reading of the sources. Line numbers refer to the commit of the
subject (`subjects/authlib/subject.json`, commit `42607cbc2135`).

| Deleted check | Cases in which it fires | After the deletion | Witness file | Does the deletion change what the library accepts? |
|---|---|---|---|---|
| `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2` | 1 | same class; no check decides (`authlib/jose/util.py:18`, "Invalid header string"); no other check fires | `test_json_signature_empty.py` holds | yes |
| `jose.rfc7519.claims.BaseClaims._validate_essential_claims#2` | 1 | same class, same message; `jose.rfc7519.claims.BaseClaims._validate_claim_value#1` fires and decides instead | `test_essential_claim_empty_value.py` holds | yes |
| `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#1` | 1 | same class; `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2` fires and decides instead | none | no input found |

Counts: 2 deletions change what the library accepts, each shown by a witness
file that holds; for 1 no such input was found.

## The 2 deletions with a witness file that holds

**`jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2`**
(`authlib/jose/rfc7515/jws.py`, lines 318 to 320) rejects a JSON
serialization of a JSON Web Signature (JWS) whose `"signature"` member is
missing or has a false value. It fires in `test_fail_deserialize_json#4`
(`tests/jose/test_jws.py`, lines 194 to 197), whose input
`{"payload": "YQ", "protected": "YQ"}` also carries a protected header that
decodes to `a`, which is not JSON. Without the check, line 323 runs and
`extract_header` rejects that header with "Invalid header string"
(`authlib/jose/util.py`, lines 15 to 18), a raise statement of a class held
in a parameter and so no check. By reading of lines 322 to 341: with a valid
protected header, the statements after the deleted raise turn the signature
into bytes and call `algorithm.verify`. A missing member (`None`) then fails
in `extract_segment` with a `TypeError` (`util.py`, line 26), which is no
rejection class; a member such as `0` fails as invalid base64url (`util.py`,
line 33); and an empty string, list or object becomes the empty signature
`b""`. For a keyed algorithm `verify` returns false on `b""` and the library
raises `BadSignatureError` (`jws.py`, lines 196 to 199). The "none" algorithm
is registered (`authlib/jose/rfc7518/jws_algs.py`, lines 25 to 37 and 205 to
206) and passes `_prepare_algorithm_key` when the caller lists it in
`algorithms` (`jws.py`, lines 268 to 273); its `verify` returns
`sig == b""`. The inputs that the check alone rejects are therefore those
whose protected header names an allowed "none" algorithm and whose signature
member is an empty string, list or object. The witness serializes content
under `{"alg": "none"}` with `JsonWebSignature(algorithms=["none"])`: the
compact form, whose signature is empty too, is accepted, and
`deserialize_compact` has no such check (lines 81 to 115); the flattened
JSON form that `serialize_json` produces carries `"signature": ""` and is
rejected. Without the check it is accepted.

**`jose.rfc7519.claims.BaseClaims._validate_essential_claims#2`**
(`authlib/jose/rfc7519/claims.py`, lines 54 to 60) rejects an essential claim
that is present with a false value. It fires in
`test_validate_expected_issuer_received_None#0` (`tests/jose/test_jwt.py`,
lines 238 to 243), whose options also require `iss` to be in `["foo"]`.
Without the check, `validate_iss` runs (lines 98 and 117) and
`_validate_claim_value#1` rejects `None` at line 74 with the same message,
"Invalid claim 'iss'". By reading of lines 62 to 78 and 91 to 227, the later
statements reject a false value only when the option names a non-empty
`value` or `values` (lines 68 to 74) or a `validate` function that refuses it
(lines 76 to 78), or when the claim is `exp`, `nbf` or `iat` and the value is
not a number (lines 174 to 207) or, for `exp`, is in the past. `validate_aud`
returns at once when the claim is false (lines 143 to 146), whatever values
the option names. The inputs that the check alone rejects are therefore an
essential claim with a false value under an option that names no value, an
essential `aud` with a false value under any option, and an essential `nbf`
or `iat` equal to `0`. The witness gives a token whose essential `sub` claim
is the empty string, under `{"sub": {"essential": True}}`; the same token with
`"alice"` is accepted. The library rejects it; without the check it is
accepted.

In both, the negative test that reaches the check gives an input that a later
statement rejects as well.

## The deletion for which no accepted input was found

**`jose.rfc7515.jws.JsonWebSignature._validate_json_jws#1`**
(`authlib/jose/rfc7515/jws.py`, lines 314 to 316) rejects a JWS JSON
serialization whose `"protected"` member is missing or has a false value. It
fires in `test_fail_deserialize_json#3` (`tests/jose/test_jws.py`, lines 189
to 192), whose input `{"payload": "YQ"}` has no signature either; without the
check, `_validate_json_jws#2` rejects it with the same class
(`undetected.csv`). By reading of lines 318 to 323: when a signature is
present, the statements after the deleted raise pass the protected value
through `to_bytes` (`authlib/common/encoding.py`, lines 6 to 15) to
`extract_header` (`authlib/jose/util.py`, lines 9 to 22), and a header must
decode to a JSON object before any later statement runs. No false value that
a JSON text can carry does: `null` stays `None` and fails at `util.py` line
10 with a `TypeError`, which is no rejection class but still a rejection;
`""`, `[]` and `{}` become `b""` and fail as "Invalid header string"
(line 18); `false`, `0` and `0.0` become the bytes of their text (`b"False"`,
`b"0"`, `b"0.0"`) and fail as invalid base64url (line 33). No witness test was written;
no input was found that the library accepts without the check. An object
built in code whose truth value is false while its bytes form a valid header
would reach the later statements; no serialization can carry such a value.

## What the deletions of this library show

The 3 deletions that the whole suite misses are all deletions of deciding
checks, each the deciding check of 1 case whose input carries a second
defect that a later statement rejects. For 2 of the 3, a test of a few lines
separates the library from the copy without the check; for the third, no
input was found, which shows nothing about it.
