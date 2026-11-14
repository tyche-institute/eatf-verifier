# Labels by reading: authlib

Labels files: A.tsv, B.tsv; rule 3: targets.json

- A.tsv: 43 blocks labeled; check 27, none 16, by parameter 0; bases class 5, class+assert 2, class+name 20, none 16; 0 labels whose class is not an expected class or a subclass of one; 0 warnings
- B.tsv: 43 blocks labeled; check 29, none 14, by parameter 0; bases class 5, class+assert 2, class+name 22, none 14; 0 labels whose class is not an expected class or a subclass of one; 0 warnings

## Agreement (included blocks)

| Category | Blocks |
|---|---|
| same check | 27 |
| both none | 14 |
| 1 check and 1 none | 2 |
| 2 different checks | 0 |

| Categories | Blocks | Categories used | Equal | Observed agreement | Expected by chance | Cohen's kappa |
|---|---|---|---|---|---|---|
| each label text | 43 | 21 | 41 | 0.9535 | 0.1466 | 0.9455 |
| a check is named, or none | 43 | 2 | 41 | 0.9535 | 0.5446 | 0.8979 |

Cases of the study: 48; with an agreed label that names a check: 27; agreed label none: 19; no agreed label: 2.

## Outcome of the cases with an agreed label that names a check

| Outcome | Cases |
|---|---|
| decided by its label | 27 |
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
| assertion | 5 | 0 | 0 | 0 | 0 | 0 |
| name | 10 | 3 | 0 | 12 | 0 | 0 |
| none | 0 | 0 | 7 | 0 | 9 | 2 |
| all | 15 | 3 | 7 | 12 | 9 | 2 |

## rule 3 against the agreed label (cases)

| Tier of the target | target equals label | target differs from label | target and label none | label none | no target | no agreed label |
|---|---|---|---|---|---|---|
| assertion | 5 | 0 | 0 | 0 | 0 | 0 |
| name | 10 | 3 | 0 | 12 | 0 | 0 |
| none | 0 | 0 | 7 | 0 | 9 | 2 |
| all | 15 | 3 | 7 | 12 | 9 | 2 |

## rule 2 against the agreed label (included blocks)

| Basis of the target, or reason for none | both, equal | both, different | rule only | label only | neither | no agreed label |
|---|---|---|---|---|---|---|
| class | 5 | 0 | 0 | 0 | 0 | 0 |
| name | 10 | 3 | 12 | 0 | 0 | 0 |
| none: no name token matches | 0 | 0 | 0 | 6 | 1 | 0 |
| none: tie | 0 | 0 | 0 | 3 | 1 | 2 |
| all | 15 | 3 | 12 | 9 | 2 | 2 |

## rule 3 against the agreed label (included blocks)

| Basis of the target, or reason for none | both, equal | both, different | rule only | label only | neither | no agreed label |
|---|---|---|---|---|---|---|
| class | 5 | 0 | 0 | 0 | 0 | 0 |
| name | 10 | 3 | 12 | 0 | 0 | 0 |
| none: no name token matches | 0 | 0 | 0 | 6 | 1 | 0 |
| none: tie | 0 | 0 | 0 | 3 | 1 | 2 |
| all | 15 | 3 | 12 | 9 | 2 | 2 |

## First reading of the flags

- flags: 12
- agreed_label_equals_described: 3
- agreed_label_differs_from_described: 3
- not_compared: 6

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
