# jwcrypto 1.6.1 (pilot): the deletions that the whole suite does not detect

33 checks fire in the negative tests of the study. The whole suite (163 tests)
detects the deletion of 26 of them and misses 7. All 7 are checks that fire and
never decide a case: each fires during a call made in the body of a `try`
statement whose handler catches every exception, and the exception the test
sees is raised after that handler. None of the 7 stands in a handler itself:
the column `in_handler` of `generated/jwcrypto/deletions.csv` is "no" for
all 7.

The facts below come from `generated/jwcrypto/undetected.csv` (every case in
which the deleted check fires, before and after the deletion) and from
`generated/jwcrypto/deletions.csv`. The last column of the table says "yes"
only where a witness file holds. A witness file is a file of new tests in
`witnesses/jwcrypto/`; it *holds* when every test of it passes on the
unmodified copy and at least 1 of them fails on the copy without the check
(`generated/jwcrypto/SUMMARY.md`, table of witness files). Each witness test
is written to fail only when the library accepts the input. The recorded
message of each of the 4 failures is "DID NOT RAISE" followed by the
rejection class: the call returned without an exception. Where no witness
file holds, the column says "no input found", and the reasons given below
are a reading of the sources. Line numbers refer to the commit of the
subject (`subjects/jwcrypto/subject.json`).

| Deleted check | Cases in which it fires | After the deletion | Witness file | Does the deletion change what the library accepts? |
|---|---|---|---|---|
| `jwa._AesKw._get_key#2` | 2 | same class, same deciding check, same message; no other check fires | `test_key_wrap_key_length.py` holds | yes |
| `jwa._RSA.unwrap#1` | 1 | same class, same deciding check, same message; no other check fires | `test_content_key_length.py` holds | yes |
| `jwe.JWE._jwa_keymgmt#1` | 1 | same class, same deciding check, same message; `jwe.JWE._jwa_enc#1` fires instead | `test_key_management_algorithm.py` holds | yes |
| `jws.JWS._merge_check_headers#1` | 1 | same class, same deciding check; the logged reason changes; no other check fires | `test_unknown_critical_header.py` holds | yes |
| `jwa._RSA._check_key#1` | 3 | same class, same deciding check, same message; no other check fires | `test_rsa_token_with_another_key_type.py` does not hold | no input found |
| `jwe.JWE._decrypt#2` | 1 | same class, same deciding check, same message; `jwe.JWE._decrypt#3` fires instead | none | no input found |
| `jwe.JWE._decrypt#5` | 1 | same class, same deciding check; the logged reason changes; no other check fires | none | no input found |

Counts: 4 deletions change what the library accepts, each shown by a witness
file that holds; for 3 no such input was found.

## The 4 deletions with a witness file that holds

**`jwa._AesKw._get_key#2`** (`jwcrypto/jwa.py`, lines 495 to 496) rejects a
wrapping key whose length is not the length the key-wrap algorithm names. It
fires in `TestJWE.test_decrypt_keyset#0` and
`TestJWE.test_multiple_recipients_keyset#0`, where a key set holds keys of
other lengths. Each key is tried and fails, and the case ends with "Key Not
found in JWKSet". Without the check the keys are still tried and still fail,
because the wrapped key does not open under another key. The witness gives a
token whose header names the 256-bit algorithm and whose content-encryption
key is wrapped with a 128-bit key. The library rejects it; without the check
it is accepted.

**`jwa._RSA.unwrap#1`** (`jwcrypto/jwa.py`, lines 420 to 421) rejects a
content-encryption key whose length is not the length the content-encryption
algorithm names. It fires in `TestJWT.test_decrypt_keyset#2`, while the keys
of a set are tried on a token that none of them opens. The witness gives a
token whose header names the Advanced Encryption Standard in Galois/Counter
Mode with a 128-bit key and which carries a 256-bit key. The library rejects
it; without the check it is accepted.

**`jwe.JWE._jwa_keymgmt#1`** (`jwcrypto/jwe.py`, lines 120 to 121) rejects a
key-management algorithm that is not in the list the caller allows. It fires
in `TestJWE.test_A5#0` (`jwcrypto/tests.py`, line 1517). That test allows only
`A256KW`, so neither the key-management algorithm of the token nor its
content-encryption algorithm is allowed, and the check of the second list,
`jwe.JWE._jwa_enc#1`, rejects the token when the first is deleted. The witness
gives a token whose key-management algorithm is outside the allowed list and
whose content-encryption algorithm is inside it. The library rejects it;
without the check it is accepted.

**`jws.JWS._merge_check_headers#1`** (`jwcrypto/jws.py`, lines 229 to 232)
rejects a protected header that lists a critical header parameter the library
does not know. It fires in `TestJWS.test_E#0` (`jwcrypto/tests.py`, line 1082),
which verifies the negative example of Request for Comments (RFC) 7515,
Appendix E, with no key. Without the check the verification still fails, now
for the missing key: the logged reason changes from the critical header to
"Unrecognized key type".
The witness gives an object with a valid signature whose protected header
lists an unknown critical parameter. The library rejects it; without the check
it is accepted.

In each of the 4, the negative test that reaches the check gives an input that
something else rejects as well.

## The 3 deletions for which no accepted input was found

**`jwa._RSA._check_key#1`** (`jwcrypto/jwa.py`, lines 404 to 405) rejects a
key that is not a Rivest-Shamir-Adleman (RSA) key when the algorithm is an RSA
algorithm. It fires in 3 cases of `TestJWT`, where a key set holds keys of
several types. By reading: without the check the statements that follow fail
on the key of another type, with an error that is not a rejection class, and
both callers catch every exception (the loop over a key set in
`JWE._decrypt`, lines 395 to 407, and `JWE.decrypt`, lines 463 to 477). The
attempt `test_rsa_token_with_another_key_type.py` gives a token for an RSA
key, under 2 RSA algorithms, a symmetric key and an elliptic-curve key
outside a key set: all 4 tests pass with and without the check. The deletion
changes the logged reason; no input was found that the library accepts
without it.

**`jwe.JWE._decrypt#2`** (`jwcrypto/jwe.py`, lines 390 to 392) rejects a token
whose key identifier names no key of the set. By reading of lines 386 to 410:
without the check the loop runs over an empty list of keys, so no key is
tried and this recipient gives no plaintext. In the case where the check
fires, `jwe.JWE._decrypt#3` then raises the same class. The 2 checks differ
in their message, which reaches the caller only through the log of the
decryption. No witness test was written; no input was found that the library
accepts without the check.

**`jwe.JWE._decrypt#5`** (`jwcrypto/jwe.py`, lines 426 to 430) rejects
compressed data that expand beyond the limit on the output size. Line 427
discards the plaintext before the raise statement. The deletion replaces the
raise statement alone, so the plaintext is still discarded and `JWE.decrypt`
rejects the token because no plaintext was produced (lines 479 to 483). The
rejection survives through the statement before the raise, not through
another check; a deletion of the whole branch was not tried. No witness test
was written; no input was found that the library accepts under this deletion.

## What the pilot shows

The deletions of the 16 deciding checks are all detected by the whole suite.
The 7 that it misses are all among the 17 checks that fire and never decide,
which the raise site alone does not see. For 4 of the 7, a test of a few lines
separates the library from the copy without the check; for the other 3, no
input was found, which shows nothing about them.
