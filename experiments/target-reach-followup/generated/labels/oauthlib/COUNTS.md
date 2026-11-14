# Labels by reading: oauthlib

Labels files: A.tsv, B.tsv; rule 3: targets.json

- A.tsv: 73 blocks labeled; check 65, none 8, by parameter 0; bases class 22, class+assert 2, class+name 14, name 27, none 8; 0 labels whose class is not an expected class or a subclass of one; 0 warnings
- B.tsv: 73 blocks labeled; check 64, none 9, by parameter 0; bases class 24, class+assert 2, class+name 38, none 9; 0 labels whose class is not an expected class or a subclass of one; 0 warnings

## Agreement (included blocks)

| Category | Blocks |
|---|---|
| same check | 61 |
| both none | 5 |
| 1 check and 1 none | 7 |
| 2 different checks | 0 |

| Categories | Blocks | Categories used | Equal | Observed agreement | Expected by chance | Cohen's kappa |
|---|---|---|---|---|---|---|
| each label text | 73 | 45 | 66 | 0.9041 | 0.046 | 0.8995 |
| a check is named, or none | 73 | 2 | 66 | 0.9041 | 0.7941 | 0.5342 |

Cases of the study: 142; with an agreed label that names a check: 124; agreed label none: 9; no agreed label: 9.

## Outcome of the cases with an agreed label that names a check

| Outcome | Cases |
|---|---|
| decided by its label | 124 |
| label fires and another check decides | 0 |
| label fires and no check decides | 0 |
| label does not fire and decides once the deciding check is deleted | 0 |
| label does not fire and does not decide then either | 0 |
| label does not fire; case not observed on the copy without the deciding check | 0 |
| label does not fire and no check decides | 0 |
| deciding check not deleted or record missing | 0 |
| fired checks not recorded | 0 |

## rule 2 against the agreed label (cases)

| Tier of the target | target equals label | target differs from label | target and label none | label none | no target | no agreed label |
|---|---|---|---|---|---|---|
| assertion | 25 | 0 | 0 | 0 | 0 | 0 |
| name | 18 | 10 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 9 | 0 | 71 | 9 |
| all | 43 | 10 | 9 | 0 | 71 | 9 |

## rule 3 against the agreed label (cases)

| Tier of the target | target equals label | target differs from label | target and label none | label none | no target | no agreed label |
|---|---|---|---|---|---|---|
| assertion | 31 | 0 | 0 | 0 | 0 | 0 |
| name | 43 | 10 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 9 | 0 | 40 | 9 |
| all | 74 | 10 | 9 | 0 | 40 | 9 |

## rule 2 against the agreed label (included blocks)

| Basis of the target, or reason for none | both, equal | both, different | rule only | label only | neither | no agreed label |
|---|---|---|---|---|---|---|
| class | 10 | 0 | 0 | 0 | 0 | 0 |
| name | 10 | 6 | 0 | 0 | 0 | 0 |
| none: no name token matches | 0 | 0 | 0 | 23 | 4 | 5 |
| none: no reachable check of the expected class | 0 | 0 | 0 | 6 | 0 | 0 |
| none: tie | 0 | 0 | 0 | 6 | 1 | 2 |
| all | 20 | 6 | 0 | 35 | 5 | 7 |

## rule 3 against the agreed label (included blocks)

| Basis of the target, or reason for none | both, equal | both, different | rule only | label only | neither | no agreed label |
|---|---|---|---|---|---|---|
| class | 12 | 0 | 0 | 0 | 0 | 0 |
| name | 19 | 6 | 0 | 0 | 0 | 0 |
| none: no name token matches | 0 | 0 | 0 | 18 | 4 | 5 |
| none: tie | 0 | 0 | 0 | 6 | 1 | 2 |
| all | 31 | 6 | 0 | 24 | 5 | 7 |

## First reading of the flags

- flags: 10
- agreed_label_equals_described: 10
- agreed_label_differs_from_described: 0
- not_compared: 0

## Sentinels

1. the deposited files of generated/<name>/ match SHA256SUMS: holds
2. cases.csv holds exactly the cases of the study of the first baseline record, with the same raise site and fired checks: holds
3. the target of each row of cases.csv is the target of its block in targets.json: holds
4. every labels file is valid: each included block exactly once, labels are check ids or none, bases are valid: holds
5. every by-param label resolves to exactly 1 value in every case of its block: holds
6. the agreement categories add up to the included blocks, the outcomes to the cases with an agreed label that names a check, and the rule categories to the cases of the study, for each rule and in each tier: holds
7. every case decided by its label has its label among its fired checks: holds
8. the deletion runs read here are those of deletions.csv, and for every case whose deciding check was deleted and gave a record, the status and raise site read from the records equal those of pinning.csv: holds
9. the transcription of the first reading matches flags.csv: the same cases, targets and deciding checks, in the same order: holds
