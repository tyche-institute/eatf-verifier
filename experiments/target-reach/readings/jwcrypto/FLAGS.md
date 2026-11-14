# jwcrypto 1.6.1 (pilot): reading of the flags

A flag is a case with a target that the target does not decide. The columns
"target fires" and "own test without the target" are mechanical and come from
`generated/jwcrypto/flags.csv`. The class is a reading of the sources, with its
reason, and is reported as a reading. Line numbers refer to the commit of the
subject (`subjects/jwcrypto/subject.json`).

Classes: **A** the test does not reach its target; **B** the target fires and a
handler replaces its exception; **C** the target the rule assigned is not the
check the test describes; **D** cannot be decided from the sources. The
classes are tried in the order C, A, B, D, and a flag gets the first that
fits.

| Case | Target | Decided by | Target fires | Own test without the target | Class |
|---|---|---|---|---|---|
| `ConformanceTests.test_jwe_decompression_max#0` (`jwcrypto/tests.py:2392`) | `jwe.JWE._decrypt#4` | `jwe.JWE.decrypt#3` | yes | fails | B |
| `ConformanceTests.test_jwe_decompression_max#1` (`jwcrypto/tests.py:2403`) | `jwe.JWE._decrypt#4` | `jwe.JWE.decrypt#3` | no | fails | C |
| `ConformanceTests.test_jwe_decompression_max#2` (`jwcrypto/tests.py:2415`) | `jwe.JWE._decrypt#4` | `jwe.JWE.decrypt#3` | yes | fails | B |
| `TestJWE.test_bare_ecdh_with_ek_fails#0` (`jwcrypto/tests.py:1618`) | `jwa._EcdhEs.unwrap#1` | `jwe.JWE.decrypt#3` | yes | fails | B |

Counts: A 0, B 3, C 1, D 0.

## Reasons

**The handler.** `JWE.decrypt` calls `JWE._decrypt` inside `try` and catches
every exception (`jwcrypto/jwe.py`, lines 463 to 477). It appends the caught
exception to a log and, when no plaintext was produced, raises its own
`InvalidJWEData`: "No recipient matched the provided key" followed by the log
(line 482, check `jwe.JWE.decrypt#3`). Every rejection made inside `_decrypt`
other than a `JWKeyNotFound` therefore reaches the caller as an exception
raised by `decrypt#3`. A caught `JWKeyNotFound` only sets a flag, and the
caller then receives the `JWKeyNotFound` "Key Not found in JWKSet" raised at
line 481 (check `jwe.JWE.decrypt#2`).

**`test_jwe_decompression_max#0`: B.** The token holds compressed data above
the default limit on compressed size. `_decrypt#4` raises "Compressed data
exceeds maximum allowedsize (262144)" (lines 420 to 423), and the handler
replaces it. The baseline message of the case quotes the message of the
target. Without the target the test fails.

**`test_jwe_decompression_max#1`: C.** Line 2397 of the test raises the limit
on compressed size, so `_decrypt#4` no longer applies. The comment at line 2402
says that the decryption "will still fail because the max plaintext length
clamps this": the check the block describes is `_decrypt#5`, the limit on the
output size (lines 426 to 430), and the baseline message quotes its text. The
rule read the name of the test, which the 3 blocks share, and gave all 3 the
same target. The test fails without the target only because block `#0` of the
same test needs it.

**`test_jwe_decompression_max#2`: B.** Line 2412 restores the limit on
compressed size, and `_decrypt#4` fires again, as in block `#0`.

**`test_bare_ecdh_with_ek_fails#0`: B.** The test puts a non-empty encrypted
key into a token of direct key agreement. `_EcdhEs.unwrap#1` raises 'Non empty
"ek" parameter' (`jwcrypto/jwa.py`, lines 849 to 850), and the same handler
replaces it. Without the target the test fails.

## What the pilot shows about flags

3 of the 4 flags are not weak tests: the target fires, the test needs it, and
only the raise site belongs to a wrapper. The raise site alone would have
counted them as tests that miss their target. The other flag is a wrong
target of the name tier; all 4 targets were assigned in that tier.
