# Target reach: pyjwt 2.15.1

Commit `7d5ef55e42ce42221f58dc49943e92ccad1fa66a`. Rule `reach-target-rule/3`. Suite without the recorder: 471 passed, 4 skipped.

| Count | Value |
|---|---|
| blocks | 215 |
| included_blocks | 79 |
| included_blocks_class_only | 29 |
| included_blocks_never_run | 0 |
| included_blocks_with_target | 48 |
| tests_run | 475 |
| tests_expected_to_fail_at_baseline | 0 |
| test_files_not_collected | 0 |
| tests_collected_again | 0 |
| tests_imported_and_kept | 0 |
| tests_with_cases | 87 |
| cases_of_included_blocks | 91 |
| cases_left_out | 0 |
| cases | 91 |
| cases_class_only | 30 |
| cases_nested | 0 |
| cases_fired_in_other_threads | 0 |
| cases_with_target | 49 |
| cases_reaching_target | 48 |
| cases_target_fires | 48 |
| flags | 1 |
| flags_target_fires | 0 |
| cases_another_check_fires_too | 0 |
| checks | 80 |
| checks_in_subject_files | 46 |
| checks_reachable | 54 |
| checks_deciding | 44 |
| checks_deciding_in_subject_files | 41 |
| checks_deciding_not_statically_reachable | 0 |
| checks_firing | 44 |
| checks_firing_and_never_deciding | 0 |
| deletions | 41 |
| deletions_of_deciding_checks | 41 |
| deletions_of_checks_that_fire_and_never_decide | 0 |
| deletions_in_handler | 9 |

Where the baseline cases raise:

- check: 91

Included blocks by basis of the target, or by the reason for none:

- assert: 14
- assert+name: 4
- assert-literal: 19
- class: 8
- name: 3
- none: no name token matches: 22
- none: tie: 9

Cases with a target, by tier (flags: the baseline raise site is not the target):

- assertion: 42 cases, 0 flags
- name: 7 cases, 1 flags

Cases with a target, by what decides them and by the case's own test on the copy without the target:

| Outcome | Cases |
|---|---|
| decided by the target | 48 |
| decided by the target; own test without the target: fails | 46 |
| decided by the target; own test without the target: target not deleted | 2 |
| the target does not fire | 1 |
| the target does not fire; own test without the target: passes | 1 |

Deletions of the 41 reached checks, not detected:

| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing | Of them, deciding checks |
|---|---|---|---|---|
| O_V | 5 | 5 | 5 | 5 |
| O_Vfc | 21 | 21 | 21 | 21 |
| O_C | 3 | 3 | 3 | 3 |
| O_T | 12 | 12 | 12 | 12 |
| O_S | 0 | 0 |  |  |
| suite | 0 | 0 |  |  |
| whole suite | 0 | 0 |  |  |

Whole suite, without the recorder (all: pytest tests): 471 tests pass in both unmodified runs, 0 differ between them.

Connection attempts to another machine, refused and counted in every run: suite run 0; recorder runs at baseline [0, 0]; recorder runs of the deletion copies and the control: 0 of 42 runs with an attempt; whole suite at baseline [0, 0]; whole suite on the deletion copies and the control: between 0 and 0 in 42 runs; witness runs 0.

Deletions that break an inclusion which holds by construction: O_Vfc within O_V: 0; O_V within O_C: 0; O_V within O_S: 0; O_S within suite: 0; suite within whole suite: 0.

Reached target checks whose deletion O_T does not detect: 0 of 30.

Pinning. For each case, the check that decides it is deleted and the case's own test is read. The unit counted is the case: a test with several cases is read 1 time per case, and it fails when it does not pass:

- cases decided by a deleted check: 86; the own test fails for 85 and still passes for 1
- cases of blocks that assert the class only: the own test still passes for 1 of 27
- cases of blocks that assert more than the class: the own test still passes for 0 of 59
- cases not counted: 0 whose exception no check raises; 5 whose deciding check was not deleted; 0 whose deletion run exceeded the time limit 2 times; 0 whose deletion run gave no record
- what the case does when its test still passes: same class, another check: 1

Sentinels:

- pass: 2 baseline runs and the control copy give identical records, message texts aside
- pass: in the baseline recorder run every test passes or is skipped, every test file is collected, and the tests deselected are the expected baseline failures
- pass: under the deletion of a check, that check fires in no case
- pass: every deletion run gave a record or exceeded the time limit 2 times
- pass: the check that decides a case is among the checks that fire in it
- pass: the whole suite ran on every deletion copy, and on the control copy it ends with its results and loses no test that passes in both unmodified runs
- pass: the deleted checks are the checks of the subject files that fire in at least 1 case of the study
