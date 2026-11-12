# Mutation adequacy of PyJWT's negative tests: protocol

Fixed on 2026-11-12, before any mutant of the subject was generated and before
any case was observed. This text is not edited after execution. Anything that
changes once runs begin is recorded, dated, under "Deviations" at the end.

This is the second subject of the study in `../mutation-adequacy/`. It keeps
that study's oracles where they carry over and says where they differ.

## Done before fixing

- The subject was cloned into `work/pyjwt` and a virtual environment built.
- The subject's whole test suite was run without any recorder, to check the
  environment: 471 passed, 4 skipped. The 4 skipped tests run only when the
  cryptography library is absent, and none contains a case.
- The source and the tests were read, and `define_s2.py` was written and run.
  It writes `checks.json` and `cases.json`.

No mutant of the subject was generated, no check was deleted, and no case was
observed under a recorder.

## Question

The first subject, eatf-verifier, and its negative cases come from the same
author. This subject asks whether the findings depend on that: PyJWT and its
tests were written by others, and its decoder rejects a token by raising an
exception whose class is shared by several checks.

- **RQ-E1.** How many mutants of PyJWT's decoding path do its own negative
  tests kill under a rejection-only oracle, an exact-class oracle, a
  target-check oracle and the tests' own assertions?
- **RQ-E2.** Which checks can be removed completely without each oracle
  noticing?
- **RQ-E3.** Does the class of the exception identify the check that rejected
  the token?

## Subject

PyJWT 2.15.1, <https://github.com/jpadilla/pyjwt>, commit
`7d5ef55e42ce42221f58dc49943e92ccad1fa66a` (2026-09-28), MIT licence.

It was chosen on 2026-11-12 from two screened candidates, PyJWT 2.15.1 and
python-tuf v7.0.1, for four properties:

1. it is written and maintained by others;
2. its decoder is fail-closed and applies its checks in a fixed order;
3. it rejects through typed exceptions, and several checks share a class;
4. its negative tests assert in different ways: the class only, a `match=`
   pattern, the message, or an attribute of the exception.

| File mutated | What it holds |
|---|---|
| `jwt/api_jws.py` | JSON Web Signature (JWS) decoding: segments, header, critical header parameters, algorithm and signature checks |
| `jwt/api_jwt.py` | JSON Web Token (JWT) payload decoding and claim validation |

`checks.json` records the SHA-256 of these two files, of `jwt/algorithms.py`
and of `jwt/exceptions.py`, and the runner refuses to start if any differs.

The subject is the set of functions of the two files that a decode can run,
listed in `checks.json` under `subject_functions`: 11 methods of `PyJWS` and
16 of `PyJWT`. The 7 other methods encode tokens, register or list algorithms,
or read a header without verifying it. Their mutants are generated, counted
and reported as outside the subject, as the signer was in the first study.

The other modules are not mutated. `jwt/algorithms.py` wraps the cryptography
library and prepares keys; `api_jwk.py`, `jwks_client.py` and `jwk_set_cache.py`
handle key sets; the rest define the exceptions, types and warnings, or are
helpers.

## Tools

mutmut 3.8.1, run with Python 3.12.3, pytest 9.1.1 and cryptography 49.0.0 in
a virtual environment without system site packages. The full freeze is in
`work/pip-freeze.txt` and is copied to `generated/`. PyJWT is not installed
into the environment: the tests import the copy under test.

mutmut runs with its default mutation operators. No operator is disabled and
no mutant is removed by hand. The configuration is appended to a copy of
PyJWT's own `pyproject.toml` and sets only what the setup needs:
`source_paths = ["jwt"]`, the two files in `only_mutate`, `tests/` as the test
selection, and `use_git_change_detection = false`. mutmut runs with
`--max-children 10`.

The suite's own pytest configuration is used unchanged. It turns warnings into
errors, so a warning raised during a case is an exception like any other.

## Checks

A check is the set of raise statements in one subject function that construct
the same PyJWTError subclass with the same message template. `define_s2.py`
assigns every raise of a PyJWTError in a subject function to a check, and stops
if one is left over.

- **44 checks in the two mutated files**, 21 in `PyJWS` and 23 in `PyJWT`.
  `checks.json` names each one and gives its raise statements, numbered in
  source order within their function.
- **The checks share 13 classes.** `DecodeError` is raised by 13 checks,
  `InvalidTokenError` and `InvalidAudienceError` by 6 each,
  `InvalidAlgorithmError` by 4, `MissingRequiredClaimError` and
  `InvalidIssuerError` by 3 each, `ImmatureSignatureError` and
  `InvalidSubjectError` by 2 each. 5 classes belong to one check each.
- **Not checks.** 3 raise statements of subject functions raise something
  other than a PyJWTError: 2 `NotImplementedError` in `get_algorithm_by_name`
  and 1 `TypeError` in `_validate_claims`.
- **External checks.** 5 checks in `jwt/algorithms.py` that a case can reach,
  all raising `InvalidKeyError`: the key of the `none` algorithm, an empty
  hash-based message authentication code (HMAC) key, an asymmetric key or a
  JSON Web Key (JWK) given as an HMAC secret, and an elliptic-curve key of the
  wrong curve. They are observed like the others but neither mutated nor
  deleted.

`checks.json` also records the order in which `PyJWT.decode` evaluates the
checks. It is used only to say whether a check that rejects a case in place of
another comes earlier or later.

## Cases

A case is one execution of a `with pytest.raises(...)` block of the subject's
own `tests/` whose statements call `decode` or `decode_complete` and whose
expected exception is a PyJWTError subclass.

- Of the 212 `pytest.raises` blocks in `tests/`, 82 call a decode function.
  3 of these expect `TypeError` or `ValueError` and are excluded. The other 79
  are the included blocks, listed in `cases.json`. They stand in 76 tests.
- A block runs once per parametrization of its test, and once per iteration
  when it stands in a loop. Each run is a case. The number of cases is fixed by
  the first baseline run and reported.
- No test is added or changed.

## Targets

Each included block gets one target check, or none, by intersecting three sets:

- **C_class:** the checks that raise the asserted class or a subclass;
- **C_assert:** the checks whose message or attributes satisfy the test's
  assertions on the exception (`match=` and assertions after the block), if it
  makes any;
- **C_name:** the checks whose message or condition the test's name names, if
  it names any.

If exactly one check is left, it is the target; otherwise the block has none.
For a target in `PyJWS._decode_base64url_segment`, the segment (header,
payload or crypto) is part of the target.

C_name takes judgement. One author applied the rule from the test text alone,
before any observation, and `cases.json` records the basis of every label and
the reason for every block without one. The result is 69 labelled blocks and
10 without a target. One block, in
`test_decode_raises_clean_error_if_claim_is_non_numeric_type`, has one target
per value of its `claim` parameter.

## Observation

A pytest plugin, the recorder, wraps pytest's own `pytest.raises` for the
session. For each block it records:

- whether the block's statements raised and, if so: the exception's class with
  its ancestors, whether it is a PyJWTError, its message, its `claim`
  attribute if it has one, and the class of its `__cause__`;
- the raise site: the innermost frame of the exception's traceback that runs
  code of the `jwt` package. If that line is a raise statement of a check, the
  site is that check. For `jws.segment-encoding`, the segment is read from the
  call in `PyJWS._load` that reached it. Otherwise the site is recorded without
  a check;
- the result of pytest's own check of the block, class and `match=`.

The wrapper then lets the test continue, whatever the block did. It never
suppresses an exception outside `Exception`, such as `KeyboardInterrupt`.
Functions that mutmut has mutated are recognised by its name mangling. A raise
site in a mutated function is mapped to the check of the raise statement with
the same number, in source order, in the original function.

For each test, the recorder also records the outcome of its setup and its
call, and the class of the exception that stopped it. Only the tests that
contain an included block are run.

A case that a mutant prevents from running is classified by why its test
stopped before it:

- **crashed:** the test could not be collected or set up, or it stopped with
  an exception that is not an assertion failure;
- **withheld:** the test stopped at an assertion failure, `AssertionError` or
  pytest's own failure, after an earlier block.

## Oracles

For case *c*, B(*c*) is the class that the unmutated library raises on *c*, and
t(*c*) is its target check.

| Oracle | Holds on *c* when |
|---|---|
| O_V, rejection | the block raised a PyJWTError |
| O_V^fc, fail-closed rejection | the block raised an exception of any class |
| O_C, exact class | the block raised an exception of class B(*c*), not a subclass |
| O_T, target check | the raise site lies in t(*c*), and in its segment if it has one |
| O_S, the tests' own assertions | pytest's own check of the block passed, and every assertion that the test makes on the block's exception after the block holds |

O_V is what a differential test sees when it compares only whether a token
is rejected; O_C adds the exception class. O_S is evaluated on the record: the assertions listed under `post` in
`cases.json` (the message equals or contains a text, the `claim` attribute
equals a name, the cause is of a class) are evaluated on the recorded message,
attribute and cause.

- **Applicable cases.** S_O is the set of cases on which oracle O holds for the
  unmutated library. A case outside S_O is never counted as killing a mutant
  under O. O_T applies only to cases with a target.
- **Kill.** A mutant is killed under O in either of two situations:
  - it crashes any case, times out, or fails to load;
  - O fails on some case in S_O.

  A crashed case is credited with the kill only if it is in S_O.
- **Withheld cases** are excluded from every oracle. A sensitivity analysis
  reports the kills when they count as failing every oracle.
- **Load failures.** A mutant under which no case is observed at all is killed
  under every oracle, and that kill is attributed to no case.
- **Timeouts.** A recorder run is stopped after the larger of 60 seconds and
  10 times the baseline run. A stopped run kills under every oracle, attributed
  to no case.
- **Equivalent mutants.** These are not identified by hand. Every oracle is
  scored over the same denominator, so equivalent mutants lower all scores
  alike.

## Mutant sets

1. **Tool mutants.** Everything mutmut generates for the two files. Each
   mutant belongs to the function mutmut mutated. Every mutant in a subject
   function is run once more under the recorder, one recorder run per mutant.
   The others are counted as outside the subject.
2. **Check deletions.** 44, one per check in the two files. Every raise
   statement of the check is replaced by `pass`, keeping the line count. The
   rest of the program is intact, so a case that reached the check continues
   to whatever comes next. Each deletion runs under the recorder on its own
   copy of the package, and an unmodified copy goes through the same steps as
   a control.

A check is **reached** when it is the raise site of at least one case on the
unmutated library. Deleting a check that no case reaches changes no case, so
those deletions are reported but are not part of the predictions.

## Measures

- **Per oracle:** subject mutants, killed, survived, and the mutation score
  (killed / subject mutants). For context, mutmut's own status for every
  mutant, mapped as in the first study.
- **Per subject function:** the same counts.
- **Per case:** kills under each oracle, and unique kills.
- **Per deletion:** reached or not; detected or not under O_V, O_V^fc, O_C, O_T
  and O_S; and for every case, whether its class, raise site or message
  changed.
- **Gaps:** kills(O_C) minus kills(O_V), as a share of kills(O_C); kills(O_T)
  minus kills(O_C), and kills(O_C) minus kills(O_T); kills(O_S) against
  kills(O_C) and kills(O_V). Every comparison that involves O_S is reported
  twice: for all mutants, and without the mutants that change only the
  arguments of an exception in a raise statement (its message, or the claim
  name). O_V, O_C and O_T cannot see those arguments by construction.
- **Moves.** For every mutant killed under O_C but not under O_V, every mutant
  killed under O_T but not under O_C, and every deletion: which check now
  rejects each case whose raise site changed, placed by the order in
  `checks.json`: a later check, an earlier check, or none (no check raised, or
  the token was accepted).

## Sentinels

Each sentinel stops the analysis until its failure is explained.

1. Two baseline runs on the unmutated library, the deletion stage's control
   copy, and a run through mutmut's mutated package with no mutant active give
   the same records, apart from timing.
2. On the unmutated library under the recorder, every test that contains a
   case passes, pytest's own check passes on every block, and every included
   block runs at least once. Without the recorder, the whole suite passes.
3. kills(O_V^fc) ⊆ kills(O_V) ⊆ kills(O_C), and kills(O_V) ⊆ kills(O_S).
   Given P1, these hold by construction, so they check the recorder and the
   analysis, not the library.
4. Every mutant killed under O_S is killed by mutmut too.
5. Every deletion of a check that is t(*c*) for a case *c* in S_O_T is detected
   under O_T.

## Predictions

Fixed before execution.

- **P1. Unmutated library.** Every case raises a PyJWTError, and O_S holds on
  every case. O_T holds on every case with a target.
- **P2. Check deletions.** Among the deletions of reached checks:
  - (a) at least one goes undetected under O_V;
  - (b) at least one goes undetected under O_C, because every case that
    reached the deleted check is rejected instead by another check with the
    same class;
  - (c) at least one is detected under O_V only through an exception that is
    not a PyJWTError, and so goes undetected under O_V^fc.
- **P3. The class does not identify the check.** At least one tool mutant is
  killed under O_T and not under O_C.
- **P4. The rejection-only gap.** kills(O_V) is a strict subset of kills(O_C),
  and the difference is at least 10% of kills(O_C).
- **P5. Kills by target function.** Each case with a target in the two mutated
  files, on which O_T holds, kills under O_T at least one tool mutant of its
  target check's function.

Exploratory analyses carry no prediction:

- O_S against O_C and O_V, and an oracle that compares class and message with
  the unmutated library;
- kills by subject function and by mutation operator;
- which check rejects each case of the 10 blocks without a target;
- mutmut's own score over the whole suite;
- the sensitivity to withheld cases.

## Order of execution

1. Commit this protocol, `define_s2.py`, `checks.json` and `cases.json`.
2. Write the recorder and test it on a small project that is not the subject.
   Run it on the unmutated library, to check P1 and sentinel 2.
3. Run the check deletions and their control.
4. Run mutmut, then the recorder on every subject mutant, and on mutmut's
   mutated package with no mutant active (sentinel 1).
5. Run the analysis, which writes `generated/` with `SHA256SUMS` and
   `SUMMARY.md`.

A refuted prediction is reported as refuted. It is not repaired by changing a
definition above.

## Deviations

None recorded at the time of fixing.
