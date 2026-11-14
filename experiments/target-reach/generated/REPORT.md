# Target reach: the subjects side by side

Every number is read from `generated/<name>/summary.json`.

| | pyjwt-package (reference) | jwcrypto (pilot) | google-auth (held out) | oauthlib (held out) | authlib (held out) | joserfc (held out) |
|---|---|---|---|---|---|---|
| version | 2.15.1 | 1.6.1 | 2.62.2 | 4.0.1 | 1.9.5 | 1.8.0 |
| checks in subject files | 99 | 146 | 100 | 88 | 39 | 97 |
| checks reachable | 57 | 93 | 52 | 54 | 36 | 81 |
| checks that fire | 44 | 33 | 13 | 47 | 24 | 55 |
| deciding checks | 44 | 16 | 13 | 47 | 24 | 53 |
| checks that fire and never decide | 0 | 17 | 0 | 0 | 0 | 2 |
| blocks | 179 | 94 | 21 | 98 | 91 | 193 |
| included blocks | 79 | 42 | 17 | 73 | 43 | 138 |
| included blocks, class-only | 29 | 42 | 0 | 71 | 41 | 133 |
| included blocks with a target | 48 | 14 | 10 | 26 | 30 | 91 |
| cases | 91 | 42 | 22 | 142 | 48 | 190 |
| cases left out | 0 | 0 | 0 | 0 | 0 | 0 |
| cases with a target | 49 | 14 | 15 | 53 | 30 | 131 |
| cases with a target, assertion tier | 42 | 6 | 0 | 25 | 5 | 99 |
| cases with a target, name tier | 7 | 8 | 15 | 28 | 25 | 32 |
| cases with a target: decided by the target | 48 | 10 | 13 | 43 | 18 | 71 |
| cases with a target: the target fires and another check decides | 0 | 3 | 0 | 0 | 0 | 0 |
| cases with a target: the target fires and no check decides | 0 | 0 | 0 | 0 | 0 | 0 |
| cases with a target: the target does not fire | 1 | 1 | 2 | 10 | 12 | 60 |
| flags | 1 | 4 | 2 | 10 | 12 | 60 |
| flags, assertion tier | 0 | 0 | 0 | 0 | 0 | 53 |
| flags, name tier | 1 | 4 | 2 | 10 | 12 | 7 |
| deletions | 44 | 33 | 13 | 47 | 24 | 55 |
| deletions of deciding checks | 44 | 16 | 13 | 47 | 24 | 53 |
| deletions of checks that fire and never decide | 0 | 17 | 0 | 0 | 0 | 2 |
| not detected, deciding checks: O_V | 7 | 4 | 2 | 7 | 3 | 12 |
| not detected, deciding checks: O_Vfc | 23 | 6 | 9 | 11 | 8 | 29 |
| not detected, deciding checks: O_C | 3 | 0 | 1 | 0 | 3 | 2 |
| not detected, deciding checks: O_T | 14 | 11 | 6 | 34 | 10 | 32 |
| not detected, deciding checks: O_S | 0 | 0 | 0 | 0 | 3 | 2 |
| not detected, deciding checks: suite | 0 | 0 | 0 | 0 | 3 | 2 |
| not detected, deciding checks: whole suite | 0 | 0 | 0 | 0 | 3 | 2 |
| not detected, checks that fire and never decide: O_V | 0 | 8 | 0 | 0 | 0 | 0 |
| not detected, checks that fire and never decide: O_Vfc | 0 | 8 | 0 | 0 | 0 | 2 |
| not detected, checks that fire and never decide: O_C | 0 | 7 | 0 | 0 | 0 | 0 |
| not detected, checks that fire and never decide: O_T | 0 | 16 | 0 | 0 | 0 | 2 |
| not detected, checks that fire and never decide: O_S | 0 | 7 | 0 | 0 | 0 | 0 |
| not detected, checks that fire and never decide: suite | 0 | 7 | 0 | 0 | 0 | 0 |
| not detected, checks that fire and never decide: whole suite | 0 | 7 | 0 | 0 | 0 | 0 |
| not detected with withheld cases counted as failing, deciding checks: O_V | 7 | 4 | 2 | 7 | 3 | 12 |
| not detected with withheld cases counted as failing, deciding checks: O_Vfc | 23 | 6 | 9 | 11 | 8 | 29 |
| not detected with withheld cases counted as failing, deciding checks: O_C | 3 | 0 | 1 | 0 | 3 | 2 |
| not detected with withheld cases counted as failing, deciding checks: O_T | 14 | 11 | 6 | 34 | 10 | 32 |
| not detected with withheld cases counted as failing, checks that fire and never decide: O_V | 0 | 8 | 0 | 0 | 0 | 0 |
| not detected with withheld cases counted as failing, checks that fire and never decide: O_Vfc | 0 | 8 | 0 | 0 | 0 | 2 |
| not detected with withheld cases counted as failing, checks that fire and never decide: O_C | 0 | 7 | 0 | 0 | 0 | 0 |
| not detected with withheld cases counted as failing, checks that fire and never decide: O_T | 0 | 16 | 0 | 0 | 0 | 2 |
| deciding checks: O_C detects and O_V does not | 4 | 4 | 1 | 7 | 0 | 10 |
| deletions that exceeded the time limit | 0 | 0 | 0 | 0 | 0 | 0 |
| deletions without a record | 0 | 0 | 0 | 0 | 0 | 0 |
| pinning: cases | 91 | 42 | 22 | 142 | 42 | 190 |
| pinning: test passes | 1 | 0 | 0 | 0 | 3 | 4 |
| pinning: class-only cases | 30 | 42 | 0 | 140 | 40 | 168 |
| pinning: class-only, test passes | 1 | 0 | 0 | 0 | 3 | 4 |
| pinning: cases of blocks that assert more | 61 | 0 | 22 | 2 | 2 | 22 |
| pinning: blocks that assert more, test passes | 0 | 0 | 0 | 0 | 0 | 0 |
| tests expected to fail at baseline | 0 | 0 | 0 | 0 | 0 | 0 |
| test files not collected | 0 | 0 | 0 | 0 | 0 | 0 |
| tests collected again and deselected | 0 | 0 | 0 | 91 | 0 | 0 |
| imported tests that stay | 0 | 0 | 0 | 3 | 0 | 0 |
| cases of a block inside another block | 0 | 0 | 0 | 0 | 0 | 0 |
| cases in which a check fires in another thread | 0 | 0 | 0 | 0 | 0 | 0 |
| whole-suite tests passing in both unmodified runs | 471 | 163 | 2349 | 717 | 1211 | 310 |
| connection attempts refused in the recorder runs at baseline | 0 | 0 | 0 | 0 | 0 | 0 |
| connection attempts refused in a whole-suite run at baseline | 0 | 0 | 9 | 0 | 0 | 0 |
| sentinels | 7 | 7 | 7 | 7 | 7 | 7 |
| sentinels that hold | 7 | 7 | 7 | 7 | 7 | 7 |
| deletions breaking an inclusion | 0 | 0 | 0 | 0 | 0 | 0 |
| witness tests | 0 | 5 | 0 | 0 | 2 | 2 |
| witness tests that hold | 0 | 4 | 0 | 0 | 2 | 2 |

## The 5 expectations (PROTOCOL.md, section 2)

Stated for the held-out libraries. The reference and the pilot are shown for comparison; the expectations were written with their counts in view. E5 is stated for a subject in which at least 9 of every 10 included blocks assert the class alone. An expectation with 0 units to decide on is not applicable. A subject in which a sentinel does not hold gets no verdict on any expectation.

| | Expectation | pyjwt-package | jwcrypto | google-auth | oauthlib | authlib | joserfc |
|---|---|---|---|---|---|---|---|
| E1 | At least 1 deletion of a deciding check is not detected by O_V. | held (7 of 44) | held (4 of 16) | held (2 of 13) | held (7 of 47) | held (3 of 24) | held (12 of 53) |
| E2 | O_C detects at least 1 deletion of a deciding check that O_V does not. | held (4 of 44) | held (4 of 16) | held (1 of 13) | held (7 of 47) | not held (0 of 24) | held (10 of 53) |
| E3 | The whole suite detects every deletion of a deciding check. | held (44 of 44) | held (16 of 16) | held (13 of 13) | held (47 of 47) | not held (21 of 24) | not held (51 of 53) |
| E4 | At least 1 case with a target is not decided by its target. | held (1 of 49) | held (4 of 14) | held (2 of 15) | held (10 of 53) | held (12 of 30) | held (60 of 131) |
| E5 | At least 1 case of a block that asserts the class alone passes its own test after the deletion of its deciding check. | not stated (29 of 79 included blocks assert the class alone) | not held (0 of 42) | not stated (0 of 17 included blocks assert the class alone) | not held (0 of 140) | held (3 of 40) | held (4 of 168) |

Verdicts per held-out library (no count is pooled across libraries):

- google-auth: held 4, not held 0, not applicable 0, not stated 1, no verdict 0
- oauthlib: held 4, not held 1, not applicable 0, not stated 0, no verdict 0
- authlib: held 3, not held 2, not applicable 0, not stated 0, no verdict 0
- joserfc: held 4, not held 1, not applicable 0, not stated 0, no verdict 0

Sentinels that do not hold: none.
