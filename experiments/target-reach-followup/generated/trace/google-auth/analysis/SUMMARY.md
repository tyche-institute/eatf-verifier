# Target reach: google-auth 2.62.2

Commit `50b1eb269f110a4b7ab09ffe5ae59c0151cd63c2`. Rule `reach-target-rule/3`. Suite without the recorder: 76 passed.

| Count | Value |
|---|---|
| blocks | 21 |
| included_blocks | 17 |
| included_blocks_class_only | 0 |
| included_blocks_never_run | 0 |
| included_blocks_with_target | 10 |
| tests_run | 76 |
| tests_expected_to_fail_at_baseline | 0 |
| test_files_not_collected | 0 |
| tests_collected_again | 0 |
| tests_imported_and_kept | 0 |
| tests_with_cases | 22 |
| cases_of_included_blocks | 22 |
| cases_left_out | 0 |
| cases | 22 |
| cases_class_only | 0 |
| cases_nested | 0 |
| cases_fired_in_other_threads | 0 |
| cases_with_target | 15 |
| cases_reaching_target | 13 |
| cases_target_fires | 13 |
| flags | 2 |
| flags_target_fires | 0 |
| cases_another_check_fires_too | 0 |
| checks | 100 |
| checks_in_subject_files | 100 |
| checks_reachable | 52 |
| checks_deciding | 13 |
| checks_deciding_in_subject_files | 13 |
| checks_deciding_not_statically_reachable | 0 |
| checks_firing | 13 |
| checks_firing_and_never_deciding | 0 |
| deletions | 13 |
| deletions_of_deciding_checks | 13 |
| deletions_of_checks_that_fire_and_never_decide | 0 |
| deletions_in_handler | 3 |

Where the baseline cases raise:

- check: 22

Included blocks by basis of the target, or by the reason for none:

- assert+name: 7
- name: 3
- none: tie: 7

Cases with a target, by tier (flags: the baseline raise site is not the target):

- name: 15 cases, 2 flags

Cases with a target, by what decides them and by the case's own test on the copy without the target:

| Outcome | Cases |
|---|---|
| decided by the target | 13 |
| decided by the target; own test without the target: fails | 13 |
| the target does not fire | 2 |
| the target does not fire; own test without the target: passes | 1 |
| the target does not fire; own test without the target: target not deleted | 1 |

Deletions of the 13 reached checks, not detected:

| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing | Of them, deciding checks |
|---|---|---|---|---|
| O_V | 2 | 2 | 2 | 2 |
| O_Vfc | 9 | 9 | 9 | 9 |
| O_C | 1 | 1 | 1 | 1 |
| O_T | 6 | 6 | 6 | 6 |
| O_S | 0 | 0 |  |  |
| suite | 0 | 0 |  |  |
| whole suite | 0 | 0 |  |  |

Whole suite, without the recorder (unit: pytest tests tests_async): 2349 tests pass in both unmodified runs, 0 differ between them.

Connection attempts to another machine, refused and counted in every run: suite run 0; recorder runs at baseline [0, 0]; recorder runs of the deletion copies and the control: 0 of 14 runs with an attempt; whole suite at baseline [9, 9]; whole suite on the deletion copies and the control: between 8 and 9 in 14 runs; witness runs 0.

Tests during which an attempt was refused (the name of a suite run comes before `|` for a whole-suite run):

- `unit|`
- `unit|tests/compute_engine/test_credentials.py::TestIDTokenCredentials::test_refresh_success`
- `unit|tests/compute_engine/test_credentials.py::TestIDTokenCredentials::test_refresh_with_agent_identity[None]`
- `unit|tests/compute_engine/test_credentials.py::TestIDTokenCredentials::test_with_target_audience_integration`
- `unit|tests/transport/test__http_client.py::TestRequestResponse::test_connection_error`
- `unit|tests/transport/test_requests.py::TestRequestResponse::test_connection_error`
- `unit|tests/transport/test_urllib3.py::TestRequestResponse::test_connection_error`
- `unit|tests_async/transport/test_aiohttp_requests.py::TestRequestResponse::test_connection_error`

Deletions that break an inclusion which holds by construction: O_Vfc within O_V: 0; O_V within O_C: 0; O_V within O_S: 0; O_S within suite: 0; suite within whole suite: 0.

Reached target checks whose deletion O_T does not detect: 0 of 7.

Pinning. For each case, the check that decides it is deleted and the case's own test is read. The unit counted is the case: a test with several cases is read 1 time per case, and it fails when it does not pass:

- cases decided by a deleted check: 22; the own test fails for 22 and still passes for 0
- cases of blocks that assert the class only: the own test still passes for 0 of 0
- cases of blocks that assert more than the class: the own test still passes for 0 of 22
- cases not counted: 0 whose exception no check raises; 0 whose deciding check was not deleted; 0 whose deletion run exceeded the time limit 2 times; 0 whose deletion run gave no record

Sentinels:

- pass: 2 baseline runs and the control copy give identical records, message texts aside
- pass: in the baseline recorder run every test passes or is skipped, every test file is collected, and the tests deselected are the expected baseline failures
- pass: under the deletion of a check, that check fires in no case
- pass: every deletion run gave a record or exceeded the time limit 2 times
- pass: the check that decides a case is among the checks that fire in it
- pass: the whole suite ran on every deletion copy, and on the control copy it ends with its results and loses no test that passes in both unmodified runs
- pass: the deleted checks are the checks of the subject files that fire in at least 1 case of the study
