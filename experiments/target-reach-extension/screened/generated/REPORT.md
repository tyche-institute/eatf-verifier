# Target reach: the subjects side by side

Every number is read from `generated/<name>/summary.json`.

| | ecdsa (held out) | python-jose (held out) | supabase-auth (held out) | service-identity (held out) |
|---|---|---|---|---|
| version | 0.19.2 | 3.5.0 | 2.34.1 | 26.1.0 |
| checks in subject files | 4 | 99 | 64 | 8 |
| checks reachable | 4 | 55 | 12 | 8 |
| checks that fire | 4 | 31 | 8 | 2 |
| deciding checks | 4 | 29 | 8 | 2 |
| checks that fire and never decide | 0 | 2 | 0 | 0 |
| blocks | 67 | 58 | 48 | 37 |
| included blocks | 9 | 44 | 16 | 12 |
| included blocks, class-only | 9 | 40 | 4 | 0 |
| included blocks with a target | 4 | 20 | 0 | 12 |
| cases | 57 | 56 | 20 | 15 |
| cases left out | 0 | 0 | 0 | 0 |
| cases with a target | 22 | 25 | 0 | 15 |
| cases with a target, assertion tier | 2 | 2 | 0 | 11 |
| cases with a target, name tier | 20 | 23 | 0 | 4 |
| cases with a target: decided by the target | 22 | 16 | 0 | 15 |
| cases with a target: the target fires and another check decides | 0 | 1 | 0 | 0 |
| cases with a target: the target fires and no check decides | 0 | 0 | 0 | 0 |
| cases with a target: the target does not fire | 0 | 8 | 0 | 0 |
| flags | 0 | 9 | 0 | 0 |
| flags, assertion tier | 0 | 0 | 0 | 0 |
| flags, name tier | 0 | 9 | 0 | 0 |
| deletions | 4 | 31 | 8 | 2 |
| deletions of deciding checks | 4 | 29 | 8 | 2 |
| deletions of checks that fire and never decide | 0 | 2 | 0 | 0 |
| not detected, deciding checks: O_V | 0 | 1 | 1 | 0 |
| not detected, deciding checks: O_Vfc | 3 | 12 | 5 | 0 |
| not detected, deciding checks: O_C | 0 | 0 | 1 | 0 |
| not detected, deciding checks: O_T | 0 | 20 | 8 | 0 |
| not detected, deciding checks: O_S | 0 | 1 | 0 | 0 |
| not detected, deciding checks: suite | 0 | 1 | 0 | 0 |
| not detected, deciding checks: whole suite | 0 | 1 | 0 | 0 |
| not detected, checks that fire and never decide: O_V | 0 | 1 | 0 | 0 |
| not detected, checks that fire and never decide: O_Vfc | 0 | 1 | 0 | 0 |
| not detected, checks that fire and never decide: O_C | 0 | 1 | 0 | 0 |
| not detected, checks that fire and never decide: O_T | 0 | 2 | 0 | 0 |
| not detected, checks that fire and never decide: O_S | 0 | 1 | 0 | 0 |
| not detected, checks that fire and never decide: suite | 0 | 1 | 0 | 0 |
| not detected, checks that fire and never decide: whole suite | 0 | 1 | 0 | 0 |
| not detected with withheld cases counted as failing, deciding checks: O_V | 0 | 1 | 1 | 0 |
| not detected with withheld cases counted as failing, deciding checks: O_Vfc | 3 | 12 | 5 | 0 |
| not detected with withheld cases counted as failing, deciding checks: O_C | 0 | 0 | 1 | 0 |
| not detected with withheld cases counted as failing, deciding checks: O_T | 0 | 20 | 8 | 0 |
| not detected with withheld cases counted as failing, checks that fire and never decide: O_V | 0 | 1 | 0 | 0 |
| not detected with withheld cases counted as failing, checks that fire and never decide: O_Vfc | 0 | 1 | 0 | 0 |
| not detected with withheld cases counted as failing, checks that fire and never decide: O_C | 0 | 1 | 0 | 0 |
| not detected with withheld cases counted as failing, checks that fire and never decide: O_T | 0 | 2 | 0 | 0 |
| deciding checks: O_C detects and O_V does not | 0 | 1 | 0 | 0 |
| deletions that exceeded the time limit | 0 | 0 | 0 | 0 |
| deletions without a record | 0 | 0 | 0 | 0 |
| pinning: cases | 57 | 56 | 20 | 15 |
| pinning: test passes | 6 | 2 | 0 | 0 |
| pinning: class-only cases | 57 | 52 | 8 | 0 |
| pinning: class-only, test passes | 6 | 2 | 0 | 0 |
| pinning: cases of blocks that assert more | 0 | 4 | 12 | 15 |
| pinning: blocks that assert more, test passes | 0 | 0 | 0 | 0 |
| tests expected to fail at baseline | 0 | 1 | 28 | 0 |
| test files not collected | 0 | 0 | 0 | 0 |
| tests collected again and deselected | 0 | 0 | 0 | 0 |
| imported tests that stay | 0 | 0 | 0 | 0 |
| cases of a block inside another block | 0 | 0 | 0 | 0 |
| cases in which a check fires in another thread | 0 | 0 | 0 | 0 |
| whole-suite tests passing in both unmodified runs | 2018 | 457 | 428 | 134 |
| connection attempts refused in the recorder runs at baseline | 0 | 0 | 0 | 0 |
| connection attempts refused in a whole-suite run at baseline | 0 | 0 | 0 | 0 |
| sentinels | 7 | 7 | 7 | 7 |
| sentinels that hold | 6 | 7 | 7 | 7 |
| deletions breaking an inclusion | 0 | 0 | 0 | 0 |
| witness tests | 0 | 0 | 0 | 0 |
| witness tests that hold | 0 | 0 | 0 | 0 |

## The 5 expectations (PROTOCOL.md, section 2)

Stated for the held-out libraries. The reference and the pilot are shown for comparison; the expectations were written with their counts in view. E5 is stated for a subject in which at least 9 of every 10 included blocks assert the class alone. An expectation with 0 units to decide on is not applicable. A subject in which a sentinel does not hold gets no verdict on any expectation.

| | Expectation | ecdsa | python-jose | supabase-auth | service-identity |
|---|---|---|---|---|---|
| E1 | At least 1 deletion of a deciding check is not detected by O_V. | no verdict (sentinel 1 does not hold) | held (1 of 29) | held (1 of 8) | not held (0 of 2) |
| E2 | O_C detects at least 1 deletion of a deciding check that O_V does not. | no verdict (sentinel 1 does not hold) | held (1 of 29) | not held (0 of 8) | not held (0 of 2) |
| E3 | The whole suite detects every deletion of a deciding check. | no verdict (sentinel 1 does not hold) | not held (28 of 29) | held (8 of 8) | held (2 of 2) |
| E4 | At least 1 case with a target is not decided by its target. | no verdict (sentinel 1 does not hold) | held (9 of 25) | not applicable (0 of 0) | not held (0 of 15) |
| E5 | At least 1 case of a block that asserts the class alone passes its own test after the deletion of its deciding check. | no verdict (sentinel 1 does not hold) | held (2 of 52) | not stated (4 of 16 included blocks assert the class alone) | not stated (0 of 12 included blocks assert the class alone) |

Verdicts per held-out library (no count is pooled across libraries):

- ecdsa: held 0, not held 0, not applicable 0, not stated 0, no verdict 5
- python-jose: held 4, not held 1, not applicable 0, not stated 0, no verdict 0
- supabase-auth: held 2, not held 1, not applicable 1, not stated 1, no verdict 0
- service-identity: held 1, not held 3, not applicable 0, not stated 1, no verdict 0

Sentinels that do not hold: ecdsa: 1: 2 baseline runs and the control copy give identical records, message texts aside.
