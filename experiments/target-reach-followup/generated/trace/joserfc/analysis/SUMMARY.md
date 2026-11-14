# Target reach: joserfc 1.8.0

Commit `f345ff71cd6c36452a4e11e47b805ad450a95dd8`. Rule `reach-target-rule/3`. Suite without the recorder: 147 passed, 49 subtests passed.

| Count | Value |
|---|---|
| blocks | 193 |
| included_blocks | 138 |
| included_blocks_class_only | 133 |
| included_blocks_never_run | 0 |
| included_blocks_with_target | 80 |
| tests_run | 147 |
| tests_expected_to_fail_at_baseline | 0 |
| test_files_not_collected | 0 |
| tests_collected_again | 0 |
| tests_imported_and_kept | 0 |
| tests_with_cases | 80 |
| cases_of_included_blocks | 190 |
| cases_left_out | 0 |
| cases | 190 |
| cases_class_only | 168 |
| cases_nested | 0 |
| cases_fired_in_other_threads | 0 |
| cases_with_target | 106 |
| cases_reaching_target | 90 |
| cases_target_fires | 90 |
| flags | 16 |
| flags_target_fires | 0 |
| cases_another_check_fires_too | 13 |
| checks | 97 |
| checks_in_subject_files | 97 |
| checks_reachable | 81 |
| checks_deciding | 53 |
| checks_deciding_in_subject_files | 53 |
| checks_deciding_not_statically_reachable | 13 |
| checks_firing | 55 |
| checks_firing_and_never_deciding | 2 |
| deletions | 55 |
| deletions_of_deciding_checks | 53 |
| deletions_of_checks_that_fire_and_never_decide | 2 |
| deletions_in_handler | 12 |

Where the baseline cases raise:

- check: 190

Included blocks by basis of the target, or by the reason for none:

- assert-literal: 2
- class: 18
- name: 60
- none: no name token matches: 33
- none: tie: 25

Cases with a target, by tier (flags: the baseline raise site is not the target):

- assertion: 38 cases, 0 flags
- name: 68 cases, 16 flags

Cases with a target, by what decides them and by the case's own test on the copy without the target:

| Outcome | Cases |
|---|---|
| decided by the target | 90 |
| decided by the target; own test without the target: fails | 90 |
| the target does not fire | 16 |
| the target does not fire; own test without the target: fails | 4 |
| the target does not fire; own test without the target: passes | 10 |
| the target does not fire; own test without the target: target not deleted | 2 |

Deletions of the 55 reached checks, not detected:

| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing | Of them, deciding checks |
|---|---|---|---|---|
| O_V | 12 | 12 | 12 | 12 |
| O_Vfc | 31 | 29 | 31 | 29 |
| O_C | 2 | 2 | 2 | 2 |
| O_T | 27 | 25 | 27 | 25 |
| O_S | 2 | 2 |  |  |
| suite | 2 | 2 |  |  |
| whole suite | 2 | 2 |  |  |

Whole suite, without the recorder (all: pytest tests): 310 tests pass in both unmodified runs, 0 differ between them.

Connection attempts to another machine, refused and counted in every run: suite run 0; recorder runs at baseline [0, 0]; recorder runs of the deletion copies and the control: 0 of 56 runs with an attempt; whole suite at baseline [0, 0]; whole suite on the deletion copies and the control: between 0 and 0 in 56 runs; witness runs 0.

Witness files (written after the run; a file holds when every test of it passes on the unmodified copy and at least 1 fails on the copy without the check):

| File | Deleted check | Holds | Tests | Passing on the unmodified copy | Failing without the check | Not passing without the check |
|---|---|---|---|---|---|---|
| `test_jwe_compact_length_with_separators.py` | `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | yes | 1 | 1 | 1 | 1 |
| `test_jws_compact_length_with_separators.py` | `_rfc7515.registry.JWSRegistry.validate_compact_value_size#1` | yes | 1 | 1 | 1 | 1 |

Recorded message of each failure on the copy without the check:

- `test_jwe_compact_length_with_separators.py`, `test_segments_within_their_limits_whole_value_beyond_the_total`: `Failed: DID NOT RAISE ExceededSizeError`
- `test_jws_compact_length_with_separators.py`, `test_segments_within_their_limits_whole_value_beyond_the_total`: `Failed: DID NOT RAISE ExceededSizeError`

Deletions that break an inclusion which holds by construction: O_Vfc within O_V: 0; O_V within O_C: 0; O_V within O_S: 0; O_S within suite: 0; suite within whole suite: 0.

Reached target checks whose deletion O_T does not detect: 0 of 28.

Pinning. For each case, the check that decides it is deleted and the case's own test is read. The unit counted is the case: a test with several cases is read 1 time per case, and it fails when it does not pass:

- cases decided by a deleted check: 190; the own test fails for 186 and still passes for 4
- cases of blocks that assert the class only: the own test still passes for 4 of 168
- cases of blocks that assert more than the class: the own test still passes for 0 of 22
- cases not counted: 0 whose exception no check raises; 0 whose deciding check was not deleted; 0 whose deletion run exceeded the time limit 2 times; 0 whose deletion run gave no record
- what the case does when its test still passes: same class, another check: 4

Sentinels:

- pass: 2 baseline runs and the control copy give identical records, message texts aside
- pass: in the baseline recorder run every test passes or is skipped, every test file is collected, and the tests deselected are the expected baseline failures
- pass: under the deletion of a check, that check fires in no case
- pass: every deletion run gave a record or exceeded the time limit 2 times
- pass: the check that decides a case is among the checks that fire in it
- pass: the whole suite ran on every deletion copy, and on the control copy it ends with its results and loses no test that passes in both unmodified runs
- pass: the deleted checks are the checks of the subject files that fire in at least 1 case of the study
