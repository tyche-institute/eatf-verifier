# Target reach: oauthlib 4.0.1

Commit `6e3aa05af92978755939a18cb4dd655ced156c1e`. Rule `reach-target-rule/2`. Suite without the recorder: 314 passed.

| Count | Value |
|---|---|
| blocks | 98 |
| included_blocks | 73 |
| included_blocks_class_only | 71 |
| included_blocks_never_run | 0 |
| included_blocks_with_target | 26 |
| tests_run | 223 |
| tests_expected_to_fail_at_baseline | 0 |
| test_files_not_collected | 0 |
| tests_collected_again | 91 |
| tests_imported_and_kept | 3 |
| tests_with_cases | 96 |
| cases_of_included_blocks | 142 |
| cases_left_out | 0 |
| cases | 142 |
| cases_class_only | 140 |
| cases_nested | 0 |
| cases_fired_in_other_threads | 0 |
| cases_with_target | 53 |
| cases_reaching_target | 43 |
| cases_target_fires | 43 |
| flags | 10 |
| flags_target_fires | 0 |
| cases_another_check_fires_too | 0 |
| checks | 88 |
| checks_in_subject_files | 88 |
| checks_reachable | 54 |
| checks_deciding | 47 |
| checks_deciding_in_subject_files | 47 |
| checks_deciding_not_statically_reachable | 6 |
| checks_firing | 47 |
| checks_firing_and_never_deciding | 0 |
| deletions | 47 |
| deletions_of_deciding_checks | 47 |
| deletions_of_checks_that_fire_and_never_decide | 0 |
| deletions_in_handler | 2 |

Where the baseline cases raise:

- check: 142

Included blocks by basis of the target, or by the reason for none:

- class: 10
- name: 16
- none: no name token matches: 32
- none: no reachable check of the expected class: 6
- none: tie: 9

Cases with a target, by tier (flags: the baseline raise site is not the target):

- assertion: 25 cases, 0 flags
- name: 28 cases, 10 flags

Cases with a target, by what decides them and by the case's own test on the copy without the target:

| Outcome | Cases |
|---|---|
| decided by the target | 43 |
| decided by the target; own test without the target: fails | 43 |
| the target does not fire | 10 |
| the target does not fire; own test without the target: passes | 10 |

Deletions of the 47 reached checks, not detected:

| Oracle | Not detected | Of them, deciding checks | With withheld cases counted as failing | Of them, deciding checks |
|---|---|---|---|---|
| O_V | 7 | 7 | 7 | 7 |
| O_Vfc | 11 | 11 | 11 | 11 |
| O_C | 0 | 0 | 0 | 0 |
| O_T | 34 | 34 | 34 | 34 |
| O_S | 0 | 0 |  |  |
| suite | 0 | 0 |  |  |
| whole suite | 0 | 0 |  |  |

Whole suite, without the recorder (all: pytest tests): 717 tests pass in both unmodified runs, 0 differ between them.

Connection attempts to another machine, refused and counted in every run: suite run 0; recorder runs at baseline [0, 0]; recorder runs of the deletion copies and the control: 0 of 48 runs with an attempt; whole suite at baseline [0, 0]; whole suite on the deletion copies and the control: between 0 and 0 in 48 runs; witness runs 0.

Deletions that break an inclusion which holds by construction: O_Vfc within O_V: 0; O_V within O_C: 0; O_V within O_S: 0; O_S within suite: 0; suite within whole suite: 0.

Reached target checks whose deletion O_T does not detect: 0 of 13.

Pinning. For each case, the check that decides it is deleted and the case's own test is read. The unit counted is the case: a test with several cases is read 1 time per case, and it fails when it does not pass:

- cases decided by a deleted check: 142; the own test fails for 142 and still passes for 0
- cases of blocks that assert the class only: the own test still passes for 0 of 140
- cases of blocks that assert more than the class: the own test still passes for 0 of 2
- cases not counted: 0 whose exception no check raises; 0 whose deciding check was not deleted; 0 whose deletion run exceeded the time limit 2 times; 0 whose deletion run gave no record

Sentinels:

- pass: 2 baseline runs and the control copy give identical records, message texts aside
- pass: in the baseline recorder run every test passes or is skipped, every test file is collected, and the tests deselected are the expected baseline failures
- pass: under the deletion of a check, that check fires in no case
- pass: every deletion run gave a record or exceeded the time limit 2 times
- pass: the check that decides a case is among the checks that fire in it
- pass: the whole suite ran on every deletion copy, and on the control copy it ends with its results and loses no test that passes in both unmodified runs
- pass: the deleted checks are the checks of the subject files that fire in at least 1 case of the study

Tests that a test file imports from another test file and that pytest collects again (the copy is deselected in every recorder run):

- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_authenticate_client`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_authenticate_client_id`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_authentication_required`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_client_id_discrepancy`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_client_id_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_code_modifier_called`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_correct_code_challenge_method_plain`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_correct_code_challenge_method_s256`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_authorization_grant`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_authorization_grant_no_scopes`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_authorization_grant_state`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_authorization_response`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_cors_headers`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_cors_headers_insecure_origin`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_cors_headers_invalid_origin`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_cors_headers_no_origin`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_token_response`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_create_token_response_without_refresh_token`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_custom_auth_validators`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_custom_token_validators`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_hybrid_token_save`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_invalid_grant`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_invalid_grant_type`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_invalid_redirect_uri`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_invalid_request`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_invalid_request_duplicates`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_challenge_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_default_method`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_optional_verifier_missing_challenge_valid`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_optional_verifier_valid_challenge_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_invalid_challenge_valid_method_valid`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_missing_challenge_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_missing_challenge_valid`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_valid_challenge_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_valid_challenge_valid_method_valid`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_valid_challenge_valid_method_wrong`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_verifier_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_verifier_valid_challenge_valid_method_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_pkce_wrong_method`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_public_client_id_discrepancy`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_public_client_id_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_wrong_code_challenge_method_plain`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_authorization_code.py::AuthorizationCodeGrantTest::test_wrong_code_challenge_method_s256`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_authenticate_client`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_authenticate_client_id`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_authentication_required`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_client_id_discrepancy`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_client_id_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_code_modifier_called`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_correct_code_challenge_method_plain`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_correct_code_challenge_method_s256`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_authorization_grant`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_authorization_grant_no_scopes`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_authorization_grant_state`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_authorization_response`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_cors_headers`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_cors_headers_insecure_origin`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_cors_headers_invalid_origin`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_cors_headers_no_origin`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_token_response`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_create_token_response_without_refresh_token`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_custom_auth_validators`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_custom_token_validators`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_hybrid_token_save`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_invalid_grant`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_invalid_grant_type`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_invalid_redirect_uri`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_invalid_request`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_invalid_request_duplicates`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_challenge_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_default_method`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_optional_verifier_missing_challenge_valid`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_optional_verifier_valid_challenge_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_invalid_challenge_valid_method_valid`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_missing_challenge_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_missing_challenge_valid`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_valid_challenge_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_valid_challenge_valid_method_valid`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_required_verifier_valid_challenge_valid_method_wrong`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_verifier_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_verifier_valid_challenge_valid_method_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_pkce_wrong_method`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_public_client_id_discrepancy`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_public_client_id_missing`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_wrong_code_challenge_method_plain`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::AuthorizationCodeGrantTest::test_wrong_code_challenge_method_s256`, defined in `tests.oauth2.rfc6749.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::OpenIDAuthCodeTest::test_authorization`, defined in `tests.openid.connect.core.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::OpenIDAuthCodeTest::test_create_token_response`, defined in `tests.openid.connect.core.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::OpenIDAuthCodeTest::test_no_prompt_authorization`, defined in `tests.openid.connect.core.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::OpenIDAuthCodeTest::test_none_multi_prompt`, defined in `tests.openid.connect.core.grant_types.test_authorization_code`
- `tests/openid/connect/core/grant_types/test_hybrid.py::OpenIDAuthCodeTest::test_optional_nonce`, defined in `tests.openid.connect.core.grant_types.test_authorization_code`

Tests that a test file imports from another test file and that stay in the recorder runs, because the runs do not hold the test in the file that defines it:

- `tests/openid/connect/core/grant_types/test_implicit.py::ImplicitGrantTest::test_create_token_response`, defined in `tests.oauth2.rfc6749.grant_types.test_implicit`
- `tests/openid/connect/core/grant_types/test_implicit.py::ImplicitGrantTest::test_custom_validators`, defined in `tests.oauth2.rfc6749.grant_types.test_implicit`
- `tests/openid/connect/core/grant_types/test_implicit.py::ImplicitGrantTest::test_error_response`, defined in `tests.oauth2.rfc6749.grant_types.test_implicit`
