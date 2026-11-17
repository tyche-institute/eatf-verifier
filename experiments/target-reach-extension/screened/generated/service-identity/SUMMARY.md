# Target reach: service-identity 26.1.0

Commit `5025f92e3856e814bb5012ba4ed03b71320131d8`. Rule `reach-target-rule/2`. Suite without the recorder: 133 passed.

| Count | Value |
|---|---|
| blocks | 37 |
| included_blocks | 12 |
| included_blocks_class_only | 0 |
| included_blocks_never_run | 0 |
| included_blocks_with_target | 12 |
| tests_run | 133 |
| tests_expected_to_fail_at_baseline | 0 |
| test_files_not_collected | 0 |
| tests_collected_again | 0 |
| tests_imported_and_kept | 0 |
| tests_with_cases | 15 |
| cases_of_included_blocks | 15 |
| cases_left_out | 0 |
| cases | 15 |
| cases_class_only | 0 |
| cases_nested | 0 |
| cases_fired_in_other_threads | 0 |
| cases_with_target | 15 |
| cases_reaching_target | 15 |
| cases_target_fires | 15 |
| flags | 0 |
| flags_target_fires | 0 |
| cases_another_check_fires_too | 0 |
| checks | 8 |
| checks_in_subject_files | 8 |
| checks_reachable | 8 |
| checks_deciding | 2 |
| checks_deciding_in_subject_files | 2 |
| checks_deciding_not_statically_reachable | 0 |
| checks_firing | 2 |
| checks_firing_and_never_deciding | 0 |
| deletions | 2 |
| deletions_of_deciding_checks | 2 |
| deletions_of_checks_that_fire_and_never_decide | 0 |
| deletions_in_handler | 0 |

Where the baseline cases raise:

- check: 15

Included blocks by basis of the target, or by the reason for none:

- class: 9
- name: 3

Cases with a target, by tier (flags: the baseline raise site is not the target):

- assertion: 11 cases, 0 flags
- name: 4 cases, 0 flags

Cases with a target, by what decides them and by the case's own test on the copy without the target:

| Outcome | Cases |
|---|---|
| decided by the target | 15 |
| decided by the target; own test without the target: fails | 15 |

Deletions of the 2 reached checks, not detected:

| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing | Of them, deciding checks |
|---|---|---|---|---|
| O_V | 0 | 0 | 0 | 0 |
| O_Vfc | 0 | 0 | 0 | 0 |
| O_C | 0 | 0 | 0 | 0 |
| O_T | 0 | 0 | 0 | 0 |
| O_S | 0 | 0 |  |  |
| suite | 0 | 0 |  |  |
| whole suite | 0 | 0 |  |  |

Whole suite, without the recorder (all: pytest tests): 134 tests pass in both unmodified runs, 0 differ between them.

Connection attempts to another machine, refused and counted in every run: suite run 0; recorder runs at baseline [0, 0]; recorder runs of the deletion copies and the control: 0 of 3 runs with an attempt; whole suite at baseline [0, 0]; whole suite on the deletion copies and the control: between 0 and 0 in 3 runs; witness runs 0.

Deletions that break an inclusion which holds by construction: O_Vfc within O_V: 0; O_V within O_C: 0; O_V within O_S: 0; O_S within suite: 0; suite within whole suite: 0.

Reached target checks whose deletion O_T does not detect: 0 of 2.

Pinning. For each case, the check that decides it is deleted and the case's own test is read. The unit counted is the case: a test with several cases is read 1 time per case, and it fails when it does not pass:

- cases decided by a deleted check: 15; the own test fails for 15 and still passes for 0
- cases of blocks that assert the class only: the own test still passes for 0 of 0
- cases of blocks that assert more than the class: the own test still passes for 0 of 15
- cases not counted: 0 whose exception no check raises; 0 whose deciding check was not deleted; 0 whose deletion run exceeded the time limit 2 times; 0 whose deletion run gave no record

Sentinels:

- pass: 2 baseline runs and the control copy give identical records, message texts aside
- pass: in the baseline recorder run every test passes or is skipped, every test file is collected, and the tests deselected are the expected baseline failures
- pass: under the deletion of a check, that check fires in no case
- pass: every deletion run gave a record or exceeded the time limit 2 times
- pass: the check that decides a case is among the checks that fire in it
- pass: the whole suite ran on every deletion copy, and on the control copy it ends with its results and loses no test that passes in both unmodified runs
- pass: the deleted checks are the checks of the subject files that fire in at least 1 case of the study
