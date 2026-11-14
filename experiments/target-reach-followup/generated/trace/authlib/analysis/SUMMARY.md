# Target reach: authlib 1.9.5

Commit `42607cbc2135252a641a845e4ed7f94e3a922c47`. Rule `reach-target-rule/3`. Suite without the recorder: 159 passed, 1 warning.

| Count | Value |
|---|---|
| blocks | 91 |
| included_blocks | 43 |
| included_blocks_class_only | 41 |
| included_blocks_never_run | 0 |
| included_blocks_with_target | 30 |
| tests_run | 159 |
| tests_expected_to_fail_at_baseline | 0 |
| test_files_not_collected | 0 |
| tests_collected_again | 0 |
| tests_imported_and_kept | 0 |
| tests_with_cases | 28 |
| cases_of_included_blocks | 48 |
| cases_left_out | 0 |
| cases | 48 |
| cases_class_only | 46 |
| cases_nested | 0 |
| cases_fired_in_other_threads | 0 |
| cases_with_target | 30 |
| cases_reaching_target | 18 |
| cases_target_fires | 18 |
| flags | 12 |
| flags_target_fires | 0 |
| cases_another_check_fires_too | 0 |
| checks | 39 |
| checks_in_subject_files | 39 |
| checks_reachable | 36 |
| checks_deciding | 24 |
| checks_deciding_in_subject_files | 24 |
| checks_deciding_not_statically_reachable | 0 |
| checks_firing | 24 |
| checks_firing_and_never_deciding | 0 |
| deletions | 24 |
| deletions_of_deciding_checks | 24 |
| deletions_of_checks_that_fire_and_never_decide | 0 |
| deletions_in_handler | 3 |

Where the baseline cases raise:

- check: 42
- other raise: 6

Included blocks by basis of the target, or by the reason for none:

- class: 5
- name: 25
- none: no name token matches: 7
- none: tie: 6

Cases with a target, by tier (flags: the baseline raise site is not the target):

- assertion: 5 cases, 0 flags
- name: 25 cases, 12 flags

Cases with a target, by what decides them and by the case's own test on the copy without the target:

| Outcome | Cases |
|---|---|
| decided by the target | 18 |
| decided by the target; own test without the target: fails | 18 |
| the target does not fire | 12 |
| the target does not fire; own test without the target: fails | 4 |
| the target does not fire; own test without the target: passes | 1 |
| the target does not fire; own test without the target: target not deleted | 7 |

Deletions of the 24 reached checks, not detected:

| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing | Of them, deciding checks |
|---|---|---|---|---|
| O_V | 3 | 3 | 3 | 3 |
| O_Vfc | 8 | 8 | 8 | 8 |
| O_C | 3 | 3 | 3 | 3 |
| O_T | 10 | 10 | 10 | 10 |
| O_S | 3 | 3 |  |  |
| suite | 3 | 3 |  |  |
| whole suite | 3 | 3 |  |  |

Whole suite, without the recorder (core: pytest tests/core; jose: pytest tests/jose; clients: pytest tests/clients; flask: pytest tests/flask; django: pytest tests/django): 1211 tests pass in both unmodified runs, 0 differ between them.

Connection attempts to another machine, refused and counted in every run: suite run 0; recorder runs at baseline [0, 0]; recorder runs of the deletion copies and the control: 0 of 25 runs with an attempt; whole suite at baseline [0, 0]; whole suite on the deletion copies and the control: between 0 and 0 in 25 runs; witness runs 0.

Witness files (written after the run; a file holds when every test of it passes on the unmodified copy and at least 1 fails on the copy without the check):

| File | Deleted check | Holds | Tests | Passing on the unmodified copy | Failing without the check | Not passing without the check |
|---|---|---|---|---|---|---|
| `test_essential_claim_empty_value.py` | `jose.rfc7519.claims.BaseClaims._validate_essential_claims#2` | yes | 1 | 1 | 1 | 1 |
| `test_json_signature_empty.py` | `jose.rfc7515.jws.JsonWebSignature._validate_json_jws#2` | yes | 1 | 1 | 1 | 1 |

Recorded message of each failure on the copy without the check:

- `test_essential_claim_empty_value.py`, `test_essential_claim_with_empty_value`: `Failed: DID NOT RAISE InvalidClaimError`
- `test_json_signature_empty.py`, `test_json_serialization_with_empty_signature`: `Failed: DID NOT RAISE DecodeError`

Deletions that break an inclusion which holds by construction: O_Vfc within O_V: 0; O_V within O_C: 0; O_V within O_S: 0; O_S within suite: 0; suite within whole suite: 0.

Reached target checks whose deletion O_T does not detect: 0 of 14.

Pinning. For each case, the check that decides it is deleted and the case's own test is read. The unit counted is the case: a test with several cases is read 1 time per case, and it fails when it does not pass:

- cases decided by a deleted check: 42; the own test fails for 39 and still passes for 3
- cases of blocks that assert the class only: the own test still passes for 3 of 40
- cases of blocks that assert more than the class: the own test still passes for 0 of 2
- cases not counted: 6 whose exception no check raises; 0 whose deciding check was not deleted; 0 whose deletion run exceeded the time limit 2 times; 0 whose deletion run gave no record
- what the case does when its test still passes: same class, another check: 2; same class, other raise: 1

Sentinels:

- pass: 2 baseline runs and the control copy give identical records, message texts aside
- pass: in the baseline recorder run every test passes or is skipped, every test file is collected, and the tests deselected are the expected baseline failures
- pass: under the deletion of a check, that check fires in no case
- pass: every deletion run gave a record or exceeded the time limit 2 times
- pass: the check that decides a case is among the checks that fire in it
- pass: the whole suite ran on every deletion copy, and on the control copy it ends with its results and loses no test that passes in both unmodified runs
- pass: the deleted checks are the checks of the subject files that fire in at least 1 case of the study
