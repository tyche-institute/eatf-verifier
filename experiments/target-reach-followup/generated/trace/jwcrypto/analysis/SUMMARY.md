# Target reach: jwcrypto 1.6.1

Commit `c10aa4343f9ce2e68caaf20aef9d2c5f6d0c4d71`. Rule `reach-target-rule/3`. Suite without the recorder: 144 passed.

| Count | Value |
|---|---|
| blocks | 94 |
| included_blocks | 42 |
| included_blocks_class_only | 42 |
| included_blocks_never_run | 2 |
| included_blocks_with_target | 14 |
| tests_run | 144 |
| tests_expected_to_fail_at_baseline | 0 |
| test_files_not_collected | 0 |
| tests_collected_again | 0 |
| tests_imported_and_kept | 0 |
| tests_with_cases | 22 |
| cases_of_included_blocks | 42 |
| cases_left_out | 0 |
| cases | 42 |
| cases_class_only | 42 |
| cases_nested | 0 |
| cases_fired_in_other_threads | 0 |
| cases_with_target | 14 |
| cases_reaching_target | 10 |
| cases_target_fires | 13 |
| flags | 4 |
| flags_target_fires | 3 |
| cases_another_check_fires_too | 24 |
| checks | 146 |
| checks_in_subject_files | 146 |
| checks_reachable | 93 |
| checks_deciding | 16 |
| checks_deciding_in_subject_files | 16 |
| checks_deciding_not_statically_reachable | 0 |
| checks_firing | 33 |
| checks_firing_and_never_deciding | 17 |
| deletions | 33 |
| deletions_of_deciding_checks | 16 |
| deletions_of_checks_that_fire_and_never_decide | 17 |
| deletions_in_handler | 3 |

Where the baseline cases raise:

- check: 42

Included blocks by basis of the target, or by the reason for none:

- class: 6
- name: 8
- none: no name token matches: 21
- none: tie: 7

Cases with a target, by tier (flags: the baseline raise site is not the target):

- assertion: 6 cases, 0 flags
- name: 8 cases, 4 flags

Cases with a target, by what decides them and by the case's own test on the copy without the target:

| Outcome | Cases |
|---|---|
| decided by the target | 10 |
| decided by the target; own test without the target: fails | 10 |
| the target does not fire | 1 |
| the target does not fire; own test without the target: fails | 1 |
| the target fires and another check decides | 3 |
| the target fires and another check decides; own test without the target: fails | 3 |

Deletions of the 33 reached checks, not detected:

| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing | Of them, deciding checks |
|---|---|---|---|---|
| O_V | 12 | 4 | 12 | 4 |
| O_Vfc | 14 | 6 | 14 | 6 |
| O_C | 7 | 0 | 7 | 0 |
| O_T | 27 | 11 | 27 | 11 |
| O_S | 7 | 0 |  |  |
| suite | 7 | 0 |  |  |
| whole suite | 7 | 0 |  |  |

Whole suite, without the recorder (all: pytest jwcrypto): 163 tests pass in both unmodified runs, 0 differ between them.

Connection attempts to another machine, refused and counted in every run: suite run 0; recorder runs at baseline [0, 0]; recorder runs of the deletion copies and the control: 0 of 34 runs with an attempt; whole suite at baseline [0, 0]; whole suite on the deletion copies and the control: between 0 and 0 in 34 runs; witness runs 0.

Witness files (written after the run; a file holds when every test of it passes on the unmodified copy and at least 1 fails on the copy without the check):

| File | Deleted check | Holds | Tests | Passing on the unmodified copy | Failing without the check | Not passing without the check |
|---|---|---|---|---|---|---|
| `test_content_key_length.py` | `jwa._RSA.unwrap#1` | yes | 1 | 1 | 1 | 1 |
| `test_key_management_algorithm.py` | `jwe.JWE._jwa_keymgmt#1` | yes | 1 | 1 | 1 | 1 |
| `test_key_wrap_key_length.py` | `jwa._AesKw._get_key#2` | yes | 1 | 1 | 1 | 1 |
| `test_rsa_token_with_another_key_type.py` | `jwa._RSA._check_key#1` | no | 4 | 4 | 0 | 0 |
| `test_unknown_critical_header.py` | `jws.JWS._merge_check_headers#1` | yes | 1 | 1 | 1 | 1 |

Recorded message of each failure on the copy without the check:

- `test_content_key_length.py`, `test_content_key_longer_than_the_algorithm_names`: `Failed: DID NOT RAISE InvalidJWEData`
- `test_key_management_algorithm.py`, `test_key_management_algorithm_not_allowed`: `Failed: DID NOT RAISE InvalidJWEData`
- `test_key_wrap_key_length.py`, `test_key_shorter_than_the_algorithm_names`: `Failed: DID NOT RAISE InvalidJWEData`
- `test_unknown_critical_header.py`, `test_unknown_critical_header_with_valid_signature`: `Failed: DID NOT RAISE InvalidJWSSignature`

Deletions that break an inclusion which holds by construction: O_Vfc within O_V: 0; O_V within O_C: 0; O_V within O_S: 0; O_S within suite: 0; suite within whole suite: 0.

Reached target checks whose deletion O_T does not detect: 0 of 4.

Pinning. For each case, the check that decides it is deleted and the case's own test is read. The unit counted is the case: a test with several cases is read 1 time per case, and it fails when it does not pass:

- cases decided by a deleted check: 42; the own test fails for 42 and still passes for 0
- cases of blocks that assert the class only: the own test still passes for 0 of 42
- cases of blocks that assert more than the class: the own test still passes for 0 of 0
- cases not counted: 0 whose exception no check raises; 0 whose deciding check was not deleted; 0 whose deletion run exceeded the time limit 2 times; 0 whose deletion run gave no record

Sentinels:

- pass: 2 baseline runs and the control copy give identical records, message texts aside
- pass: in the baseline recorder run every test passes or is skipped, every test file is collected, and the tests deselected are the expected baseline failures
- pass: under the deletion of a check, that check fires in no case
- pass: every deletion run gave a record or exceeded the time limit 2 times
- pass: the check that decides a case is among the checks that fire in it
- pass: the whole suite ran on every deletion copy, and on the control copy it ends with its results and loses no test that passes in both unmodified runs
- pass: the deleted checks are the checks of the subject files that fire in at least 1 case of the study
