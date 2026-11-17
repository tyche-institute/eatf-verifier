# Target reach: python-jose 3.5.0

Commit `018b310ddb8b50dcfd09a0c152117835a21dd656`. Rule `reach-target-rule/2`. Suite without the recorder: 1 failed, 249 passed, 6 skipped, 5 warnings.

| Count | Value |
|---|---|
| blocks | 58 |
| included_blocks | 44 |
| included_blocks_class_only | 40 |
| included_blocks_never_run | 1 |
| included_blocks_with_target | 20 |
| tests_run | 255 |
| tests_expected_to_fail_at_baseline | 1 |
| test_files_not_collected | 0 |
| tests_collected_again | 0 |
| tests_imported_and_kept | 0 |
| tests_with_cases | 56 |
| cases_of_included_blocks | 56 |
| cases_left_out | 0 |
| cases | 56 |
| cases_class_only | 52 |
| cases_nested | 0 |
| cases_fired_in_other_threads | 0 |
| cases_with_target | 25 |
| cases_reaching_target | 16 |
| cases_target_fires | 17 |
| flags | 9 |
| flags_target_fires | 1 |
| cases_another_check_fires_too | 5 |
| checks | 99 |
| checks_in_subject_files | 99 |
| checks_reachable | 55 |
| checks_deciding | 29 |
| checks_deciding_in_subject_files | 29 |
| checks_deciding_not_statically_reachable | 0 |
| checks_firing | 31 |
| checks_firing_and_never_deciding | 2 |
| deletions | 31 |
| deletions_of_deciding_checks | 29 |
| deletions_of_checks_that_fire_and_never_decide | 2 |
| deletions_in_handler | 13 |

Where the baseline cases raise:

- check: 56

Included blocks by basis of the target, or by the reason for none:

- assert+name: 1
- assert-literal: 2
- name: 17
- none: no name token matches: 5
- none: tie: 19

Cases with a target, by tier (flags: the baseline raise site is not the target):

- assertion: 2 cases, 0 flags
- name: 23 cases, 9 flags

Cases with a target, by what decides them and by the case's own test on the copy without the target:

| Outcome | Cases |
|---|---|
| decided by the target | 16 |
| decided by the target; own test without the target: fails | 16 |
| the target does not fire | 8 |
| the target does not fire; own test without the target: passes | 4 |
| the target does not fire; own test without the target: target not deleted | 4 |
| the target fires and another check decides | 1 |
| the target fires and another check decides; own test without the target: fails | 1 |

Deletions of the 31 reached checks, not detected:

| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing | Of them, deciding checks |
|---|---|---|---|---|
| O_V | 2 | 1 | 2 | 1 |
| O_Vfc | 13 | 12 | 13 | 12 |
| O_C | 1 | 0 | 1 | 0 |
| O_T | 22 | 20 | 22 | 20 |
| O_S | 2 | 1 |  |  |
| suite | 2 | 1 |  |  |
| whole suite | 2 | 1 |  |  |

Whole suite, without the recorder (compatibility: pytest tests): 457 tests pass in both unmodified runs, 0 differ between them.

Connection attempts to another machine, refused and counted in every run: suite run 0; recorder runs at baseline [0, 0]; recorder runs of the deletion copies and the control: 0 of 32 runs with an attempt; whole suite at baseline [0, 0]; whole suite on the deletion copies and the control: between 0 and 0 in 32 runs; witness runs 0.

Deletions that break an inclusion which holds by construction: O_Vfc within O_V: 0; O_V within O_C: 0; O_V within O_S: 0; O_S within suite: 0; suite within whole suite: 0.

Reached target checks whose deletion O_T does not detect: 0 of 9.

Pinning. For each case, the check that decides it is deleted and the case's own test is read. The unit counted is the case: a test with several cases is read 1 time per case, and it fails when it does not pass:

- cases decided by a deleted check: 56; the own test fails for 54 and still passes for 2
- cases of blocks that assert the class only: the own test still passes for 2 of 52
- cases of blocks that assert more than the class: the own test still passes for 0 of 4
- cases not counted: 0 whose exception no check raises; 0 whose deciding check was not deleted; 0 whose deletion run exceeded the time limit 2 times; 0 whose deletion run gave no record
- what the case does when its test still passes: other class, another check: 1; same class, another check: 1

Sentinels:

- pass: 2 baseline runs and the control copy give identical records, message texts aside
- pass: in the baseline recorder run every test passes or is skipped, every test file is collected, and the tests deselected are the expected baseline failures
- pass: under the deletion of a check, that check fires in no case
- pass: every deletion run gave a record or exceeded the time limit 2 times
- pass: the check that decides a case is among the checks that fire in it
- pass: the whole suite ran on every deletion copy, and on the control copy it ends with its results and loses no test that passes in both unmodified runs
- pass: the deleted checks are the checks of the subject files that fire in at least 1 case of the study

Tests that fail without the recorder (deselected in every recorder run):

- `tests/algorithms/test_EC.py::test_incorrect_public_key_hmac_signing`
