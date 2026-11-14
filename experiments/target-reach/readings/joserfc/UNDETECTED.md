# joserfc 1.8.0: the deletions that the whole suite does not detect

55 checks fire in the negative tests of the study. The whole suite (310 tests
that pass in both unmodified runs) detects the deletion of 53 of them and
misses 2. Both are deciding checks, and neither stands in a handler: the
column `in_handler` of `generated/joserfc/deletions.csv` is "no" for both.
Each is the check on the length of a whole compact serialization, which runs
before the checks on the lengths of its segments, and each case in which it
fires has a segment that also exceeds its own limit.

The facts below come from `generated/joserfc/undetected.csv` (every case in
which the deleted check fires, before and after the deletion) and from
`generated/joserfc/deletions.csv`. The last column of the table says "yes"
only where a witness file holds. A witness file is a file of new tests in
`witnesses/joserfc/`; it *holds* when every test of it passes on the
unmodified copy and at least 1 of them fails on the copy without the check.
Each witness test is written to fail only when the library accepts the
input. The recorded message of each of the 2 failures is "DID NOT RAISE
ExceededSizeError": the call returned without an exception. Line numbers
refer to the commit of the subject (`subjects/joserfc/subject.json`).

| Deleted check | Cases in which it fires | After the deletion | Witness file | Does the deletion change what the library accepts? |
|---|---|---|---|---|
| `_rfc7515.registry.JWSRegistry.validate_compact_value_size#1` | 1 | same class; `_rfc7515.registry.JWSRegistry.validate_payload_size#1` decides, with the message on the payload size | `test_jws_compact_length_with_separators.py` holds | yes, under the default limits |
| `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | 2 | same class; `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1` decides 1 case and `_rfc7516.registry.JWERegistry.validate_protected_header_size#1` the other, each with its own message | `test_jwe_compact_length_with_separators.py` holds | yes, under a registry whose limits on the initialization vector and the tag are those of A128GCM; under the default limits no input found |

Counts: 2 deletions change what the library accepts, each shown by a witness
file that holds; 1 of the 2 only under limits other than the defaults.

## The 2 deletions

**`_rfc7515.registry.JWSRegistry.validate_compact_value_size#1`**
(`joserfc/_rfc7515/registry.py`, lines 104 to 107) rejects a compact JSON Web
Signature (JWS) longer than the sum of the limits on the header, the payload
and the signature, 512 + 128000 + 1024 = 129536 characters by default
(lines 50 to 55). It is called first in `extract_rfc7515_compact`
(`joserfc/_rfc7797/compact.py`, line 44), which `jws.deserialize_compact`
calls. It fires in 1 case, `TestCompact.test_payload_exceeded_size_error#0`
(`tests/jws/test_compact.py`, line 71), whose payload segment of 170668
characters exceeds its own limit. After the deletion the raise statement is
`pass`, the value is split into 3 segments (lines 46 to 48), and the segment
checks run (lines 52 to 55): `validate_payload_size#1` (registry, lines 113
to 115) rejects the same input with the same class. By reading, the deleted
check alone rejects exactly the values of 3 segments in which the header has
at most 512 characters, the signature at most 1024 and the payload at most
128000 (or none), while the whole value, which counts the 2 separators, has
more than 129536: the 3 segments together have 129535 or 129536 characters.
Every other value that the check rejects is rejected without it, by the
count of segments (line 48) or by a segment check. Such values exist and
verify: a header of 512 characters, a payload of 128000 and an RS256
signature of 768 bytes (1024 characters) from a 6144-bit Rivest-Shamir-
Adleman (RSA) key. The witness gives that value, 129538 characters long;
the control, with a payload of 127996 characters, gives 129534 and is
accepted. The library rejects the first; without the check it is accepted.

**`_rfc7516.registry.JWERegistry.validate_compact_value_size#1`**
(`joserfc/_rfc7516/registry.py`, lines 113 to 122) rejects a compact JSON Web
Encryption (JWE) longer than the sum of the limits on its 5 segments,
1024 + 1024 + 64 + 65536 + 64 = 67712 characters by default (lines 55 to
64). It is called first in `extract_compact` (`joserfc/_rfc7516/compact.py`,
line 37). It fires in 2 cases: `TestJWECompact.test_ciphertext_exceeds_size#0`
(`tests/jwe/test_compact.py`, line 276) and
`TestJWECompact.test_header_exceeds_size#0` (line 256), whose ciphertext and
protected header exceed their own limits. After the deletion the value is
split into 5 segments (lines 39 to 43) and the segment checks run (lines 44
to 48): `validate_ciphertext_size#1` and `validate_protected_header_size#1`
reject the 2 inputs with the same class. By reading, the deleted check alone
rejects exactly the values of 5 segments that each fit their limits while the
whole value, which counts the 4 separators, exceeds the sum: the segments
together have at least the sum less 3. Under the default limits this needs an
initialization-vector segment of at least 61 characters. A segment of 61
characters cannot be decoded (`joserfc/util.py`, lines 28 to 30, reached
from line 69 of `compact.py`), and one of 62 to 64 characters gives 46 to 48
bytes, which `check_iv` rejects before any decryption
(`joserfc/_rfc7516/models.py`, lines 204 to 206, called at line 110 of
`joserfc/_rfc7516/message.py`), since the content-encryption algorithms use
12, 16 or 24 bytes (`joserfc/_rfc7518/jwe_encs.py`, lines 28 and 82;
`joserfc/drafts/jwe_chacha20.py`, lines 33 and 34). So under the default
limits no input was found that the library accepts without the check. The
limits are attributes of the registry that a subclass can set (registry,
lines 55 to 66). Under a registry whose limits on the initialization vector
and the tag are 16 and 22 characters, the lengths that A128GCM uses, the sum
is 67622. The witness gives, under that registry, a token with a header of
1024 characters, an RSA-OAEP encrypted key of 1024 characters from a 6144-bit
key, and a ciphertext of 65536 characters: 67626 characters in all. The
control, with a ciphertext of 65532 characters, gives 67622 and is accepted.
The library rejects the first; without the check it is accepted.

In both, the negative tests that reach the check give inputs that a segment
check rejects as well, and the deleted check alone rejects only values longer
than the sum of the segment limits by at most 4 characters (JWE) or 2 (JWS):
the separators that the sum does not count.

## What this library shows

The 2 deletions that the whole suite misses are both of deciding checks,
not of the 2 checks that fire and never decide. Each is detected by no
oracle (`deletions.csv`: "no" under O_V, O_Vfc, O_C, O_T, O_S and the suite),
because a later check of the same class decides each case instead. For the
JWS check, a test of a few lines separates the library under its default
limits from the copy without the check; for the JWE check, only a registry
with other limits does.
