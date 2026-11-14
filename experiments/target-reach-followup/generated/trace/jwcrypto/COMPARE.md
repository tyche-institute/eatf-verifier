# Targets under rule 2 and rule 3

Rule 2 is `reach-target-rule/2` of the toolkit. Rule 3 runs the same code with a check reachable when it is reachable by name or its function started under an entry point in the traced run of the whole suite on the unmodified copy (`reach.json`). The cases are those of the deposited records; nothing about a case is re-run. A case is decided by its target when the raise site of its exception is the target; a case with a target that its target does not decide is a flag.

## Reachability of the checks

| Subject | Checks | By name | By execution | Both | By name only | By execution only | Neither |
|---|---|---|---|---|---|---|---|
| jwcrypto | 146 | 93 | 103 | 89 | 4 | 14 | 39 |

## Transitions

| Subject | Unit | Same target | Changed target | Gained a target | Lost a target | No target under either |
|---|---|---|---|---|---|---|
| jwcrypto | cases | 14 | 0 | 0 | 0 | 28 |
| jwcrypto | included blocks | 14 | 0 | 0 | 0 | 28 |

## Cases with a target, per tier

| Subject | Rule | Tier | Cases with a target | Decided by the target | Not decided (flags) |
|---|---|---|---|---|---|
| jwcrypto | 2 | assertion | 6 | 6 | 0 |
| jwcrypto | 2 | name | 8 | 4 | 4 |
| jwcrypto | 2 | all | 14 | 10 | 4 |
| jwcrypto | 3 | assertion | 6 | 6 | 0 |
| jwcrypto | 3 | name | 8 | 4 | 4 |
| jwcrypto | 3 | all | 14 | 10 | 4 |

## Cases whose target differs

- jwcrypto: none

## Fired checks and the trace

Every check that fires in a case of an included block in either deposited baseline record, by where its function started in the trace (`fired-functions.csv`):

- jwcrypto: under an entry point: 33

## Where the field `reachable` is read

In the toolkit, the field `reachable` of a check is read by `reach/targets.py` (the candidates of the rule), by `reach/analyse.py` (column `reachable` of `checks.csv`, counts `checks_reachable` and `checks_deciding_not_statically_reachable`), by `reach/report.py` (the row "checks reachable"), by `recompute/second.py` and `recompute/compare.py` (the reachable checks counted), by `validate_pyjwt.py` and by `reach/run.py` (a count printed by `define`). The deletions (`reach/run.py`, `reached_checks`) take the checks that fire in a case of the study, from `reach/study.py`, and do not read it. The analysis under rule 3 keeps checks.json unchanged, so those columns and counts give the reachability by name; only the targets, and what derives from them, differ.

## Sentinels

- jwcrypto: pass: T2: every fired check lies in a function that started under an entry point, or is listed with the reason
- jwcrypto: pass: T4: the analysis under rule 3 passes the 7 sentinels of analyse.py
- jwcrypto: pass: R2: the analysis under rule 2 from the deposited records reproduces the deposited outputs
