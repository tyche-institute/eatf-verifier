# Labels by reading: joserfc

Labels files: A.tsv, B.tsv; rule 3: targets.json

- A.tsv: 138 blocks labeled; check 116, none 22, by parameter 0; bases assert 3, class 28, class+name 63, name 22, none 22; 0 labels whose class is not an expected class or a subclass of one; 0 warnings
- B.tsv: 138 blocks labeled; check 112, none 26, by parameter 0; bases class 23, class+assert 3, class+assert+name 2, class+name 84, none 26; 0 labels whose class is not an expected class or a subclass of one; 0 warnings

## Agreement (included blocks)

| Category | Blocks |
|---|---|
| same check | 111 |
| both none | 22 |
| 1 check and 1 none | 4 |
| 2 different checks | 1 |

| Categories | Blocks | Categories used | Equal | Observed agreement | Expected by chance | Cohen's kappa |
|---|---|---|---|---|---|---|
| each label text | 138 | 46 | 133 | 0.9638 | 0.07 | 0.961 |
| a check is named, or none | 138 | 2 | 134 | 0.971 | 0.7122 | 0.8993 |

Cases of the study: 190; with an agreed label that names a check: 137; agreed label none: 48; no agreed label: 5.

## Outcome of the cases with an agreed label that names a check

| Outcome | Cases |
|---|---|
| decided by its label | 129 |
| label fires and another check decides | 0 |
| label fires and no check decides | 0 |
| label does not fire and decides once the deciding check is deleted | 4 |
| label does not fire and does not decide then either | 4 |
| label does not fire; case not observed on the copy without the deciding check | 0 |
| label does not fire and no check decides | 0 |
| deciding check not deleted or record missing | 0 |
| fired checks not recorded | 0 |

## rule 2 against the agreed label (cases)

| Tier of the target | target equals label | target differs from label | target and label none | label none | no target | no agreed label |
|---|---|---|---|---|---|---|
| assertion | 40 | 37 | 0 | 20 | 0 | 2 |
| name | 27 | 3 | 0 | 2 | 0 | 0 |
| none | 0 | 0 | 26 | 0 | 30 | 3 |
| all | 67 | 40 | 26 | 22 | 30 | 5 |

## rule 3 against the agreed label (cases)

| Tier of the target | target equals label | target differs from label | target and label none | label none | no target | no agreed label |
|---|---|---|---|---|---|---|
| assertion | 38 | 0 | 0 | 0 | 0 | 0 |
| name | 57 | 7 | 0 | 2 | 0 | 2 |
| none | 0 | 0 | 46 | 0 | 35 | 3 |
| all | 95 | 7 | 46 | 2 | 35 | 5 |

## rule 2 against the agreed label (included blocks)

| Basis of the target, or reason for none | both, equal | both, different | rule only | label only | neither | no agreed label |
|---|---|---|---|---|---|---|
| class | 32 | 22 | 6 | 0 | 0 | 2 |
| name | 24 | 3 | 2 | 0 | 0 | 0 |
| none: no name token matches | 0 | 0 | 0 | 15 | 10 | 3 |
| none: no reachable check of the expected class | 0 | 0 | 0 | 4 | 0 | 0 |
| none: tie | 0 | 0 | 0 | 11 | 4 | 0 |
| all | 56 | 25 | 8 | 30 | 14 | 5 |

## rule 3 against the agreed label (included blocks)

| Basis of the target, or reason for none | both, equal | both, different | rule only | label only | neither | no agreed label |
|---|---|---|---|---|---|---|
| assert-literal | 2 | 0 | 0 | 0 | 0 | 0 |
| class | 18 | 0 | 0 | 0 | 0 | 0 |
| name | 49 | 7 | 2 | 0 | 0 | 2 |
| none: no name token matches | 0 | 0 | 0 | 16 | 14 | 3 |
| none: tie | 0 | 0 | 0 | 19 | 6 | 0 |
| all | 69 | 7 | 2 | 35 | 20 | 5 |

## First reading of the flags

- flags: 60
- agreed_label_equals_described: 40
- agreed_label_differs_from_described: 20
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
