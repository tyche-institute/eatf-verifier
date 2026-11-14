# Labels by reading: summary over the libraries

Libraries: google-auth, oauthlib, authlib, joserfc. Every value is read from the outputs of `analyse_labels.py` in the folder of each library; nothing is run again.

## Blocks

Included blocks, the blocks labeled by both readings and the 4 agreement categories of section 4.1 of the protocol. The blocks with the same label are those of the first 2 categories.

| Blocks | google-auth | oauthlib | authlib | joserfc | together |
|---|---|---|---|---|---|
| included blocks | 17 | 73 | 43 | 138 | 271 |
| labeled by both readings | 17 | 73 | 43 | 138 | 271 |
| same check | 17 | 61 | 27 | 111 | 216 |
| both none | 0 | 5 | 14 | 22 | 41 |
| 1 check and 1 none | 0 | 7 | 2 | 4 | 13 |
| 2 different checks | 0 | 0 | 0 | 1 | 1 |
| same label in both readings | 17 | 66 | 41 | 133 | 257 |

## Agreement statistics

Observed agreement, agreement expected by chance and Cohen's kappa over the blocks labeled by both readings, as exact fractions and rounded to 4 places. Together, a label text is 1 category in every library, so `none` is 1 category.

| Categories | Library | Items | Categories used | Equal | Observed | Expected | Kappa |
|---|---|---|---|---|---|---|---|
| each label text | google-auth | 17 | 13 | 17 | 1/1 = 1.0 | 25/289 = 0.0865 | 1/1 = 1.0 |
| each label text | oauthlib | 73 | 45 | 66 | 66/73 = 0.9041 | 245/5329 = 0.046 | 4573/5084 = 0.8995 |
| each label text | authlib | 43 | 21 | 41 | 41/43 = 0.9535 | 271/1849 = 0.1466 | 746/789 = 0.9455 |
| each label text | joserfc | 138 | 46 | 133 | 133/138 = 0.9638 | 1333/19044 = 0.07 | 17021/17711 = 0.961 |
| each label text | together | 271 | 123 | 257 | 257/271 = 0.9483 | 3260/73441 = 0.0444 | 66387/70181 = 0.9459 |
| names a check, or none | google-auth | 17 | 1 | 17 | 1/1 = 1.0 | 1/1 = 1.0 | no value |
| names a check, or none | oauthlib | 73 | 2 | 66 | 66/73 = 0.9041 | 4232/5329 = 0.7941 | 586/1097 = 0.5342 |
| names a check, or none | authlib | 43 | 2 | 41 | 41/43 = 0.9535 | 1007/1849 = 0.5446 | 378/421 = 0.8979 |
| names a check, or none | joserfc | 138 | 2 | 134 | 67/69 = 0.971 | 3391/4761 = 0.7122 | 616/685 = 0.8993 |
| names a check, or none | together | 271 | 2 | 258 | 258/271 = 0.952 | 52204/73441 = 0.7108 | 17714/21237 = 0.8341 |
| variant: each label text qualified by its library | together | 271 | 125 | 257 | 257/271 = 0.9483 | 1874/73441 = 0.0255 | 67773/71567 = 0.947 |

The last row is a variant and not the result. No label text other than `none` occurs in 2 libraries, so the variant differs from the result only through the category `none`.

## Cases

Cases of the study by their agreed label, and the outcome of each case whose agreed label names a check. A shadowed case has the outcome "label does not fire and decides once the deciding check is deleted".

| Cases | google-auth | oauthlib | authlib | joserfc | together |
|---|---|---|---|---|---|
| cases | 22 | 142 | 48 | 190 | 402 |
| agreed label names a check | 22 | 124 | 27 | 137 | 310 |
| agreed label none | 0 | 9 | 19 | 48 | 76 |
| no agreed label | 0 | 9 | 2 | 5 | 16 |
| outcome: decided by its label | 22 | 124 | 27 | 129 | 302 |
| outcome: label fires and another check decides | 0 | 0 | 0 | 0 | 0 |
| outcome: label fires and no check decides | 0 | 0 | 0 | 0 | 0 |
| outcome: label does not fire and decides once the deciding check is deleted | 0 | 0 | 0 | 4 | 4 |
| outcome: label does not fire and does not decide then either | 0 | 0 | 0 | 4 | 4 |
| outcome: label does not fire; case not observed on the copy without the deciding check | 0 | 0 | 0 | 0 | 0 |
| outcome: label does not fire and no check decides | 0 | 0 | 0 | 0 | 0 |
| outcome: deciding check not deleted or record missing | 0 | 0 | 0 | 0 | 0 |
| outcome: fired checks not recorded | 0 | 0 | 0 | 0 | 0 |

## rule 2 against the agreed label

Cases per tier of the target and category. Of the cases with a target, those with an agreed label (a check or none) are split into target equals label and target is not the agreed label (the target differs, or the agreed label is none).

| Library | Tier | target equals label | target differs from label | target and label none | label none | no target | no agreed label | with target | with target and agreed label | target is not the agreed label |
|---|---|---|---|---|---|---|---|---|---|---|
| google-auth | assertion | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 0 |
| google-auth | name | 13 | 2 | 0 | 0 | 0 | 0 | 15 | 15 | 2 of 15 |
| google-auth | none | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 of 0 |
| google-auth | all | 13 | 2 | 0 | 0 | 7 | 0 | 15 | 15 | 2 of 15 |
| oauthlib | assertion | 25 | 0 | 0 | 0 | 0 | 0 | 25 | 25 | 0 of 25 |
| oauthlib | name | 18 | 10 | 0 | 0 | 0 | 0 | 28 | 28 | 10 of 28 |
| oauthlib | none | 0 | 0 | 9 | 0 | 71 | 9 | 0 | 0 | 0 of 0 |
| oauthlib | all | 43 | 10 | 9 | 0 | 71 | 9 | 53 | 53 | 10 of 53 |
| authlib | assertion | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 0 of 5 |
| authlib | name | 10 | 3 | 0 | 12 | 0 | 0 | 25 | 25 | 15 of 25 |
| authlib | none | 0 | 0 | 7 | 0 | 9 | 2 | 0 | 0 | 0 of 0 |
| authlib | all | 15 | 3 | 7 | 12 | 9 | 2 | 30 | 30 | 15 of 30 |
| joserfc | assertion | 40 | 37 | 0 | 20 | 0 | 2 | 99 | 97 | 57 of 97 |
| joserfc | name | 27 | 3 | 0 | 2 | 0 | 0 | 32 | 32 | 5 of 32 |
| joserfc | none | 0 | 0 | 26 | 0 | 30 | 3 | 0 | 0 | 0 of 0 |
| joserfc | all | 67 | 40 | 26 | 22 | 30 | 5 | 131 | 129 | 62 of 129 |
| together | assertion | 70 | 37 | 0 | 20 | 0 | 2 | 129 | 127 | 57 of 127 |
| together | name | 68 | 18 | 0 | 14 | 0 | 0 | 100 | 100 | 32 of 100 |
| together | none | 0 | 0 | 42 | 0 | 117 | 14 | 0 | 0 | 0 of 0 |
| together | all | 138 | 55 | 42 | 34 | 117 | 16 | 229 | 227 | 89 of 227 |

## rule 3 against the agreed label

Cases per tier of the target and category. Of the cases with a target, those with an agreed label (a check or none) are split into target equals label and target is not the agreed label (the target differs, or the agreed label is none).

| Library | Tier | target equals label | target differs from label | target and label none | label none | no target | no agreed label | with target | with target and agreed label | target is not the agreed label |
|---|---|---|---|---|---|---|---|---|---|---|
| google-auth | assertion | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 0 |
| google-auth | name | 13 | 2 | 0 | 0 | 0 | 0 | 15 | 15 | 2 of 15 |
| google-auth | none | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 of 0 |
| google-auth | all | 13 | 2 | 0 | 0 | 7 | 0 | 15 | 15 | 2 of 15 |
| oauthlib | assertion | 31 | 0 | 0 | 0 | 0 | 0 | 31 | 31 | 0 of 31 |
| oauthlib | name | 43 | 10 | 0 | 0 | 0 | 0 | 53 | 53 | 10 of 53 |
| oauthlib | none | 0 | 0 | 9 | 0 | 40 | 9 | 0 | 0 | 0 of 0 |
| oauthlib | all | 74 | 10 | 9 | 0 | 40 | 9 | 84 | 84 | 10 of 84 |
| authlib | assertion | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 0 of 5 |
| authlib | name | 10 | 3 | 0 | 12 | 0 | 0 | 25 | 25 | 15 of 25 |
| authlib | none | 0 | 0 | 7 | 0 | 9 | 2 | 0 | 0 | 0 of 0 |
| authlib | all | 15 | 3 | 7 | 12 | 9 | 2 | 30 | 30 | 15 of 30 |
| joserfc | assertion | 38 | 0 | 0 | 0 | 0 | 0 | 38 | 38 | 0 of 38 |
| joserfc | name | 57 | 7 | 0 | 2 | 0 | 2 | 68 | 66 | 9 of 66 |
| joserfc | none | 0 | 0 | 46 | 0 | 35 | 3 | 0 | 0 | 0 of 0 |
| joserfc | all | 95 | 7 | 46 | 2 | 35 | 5 | 106 | 104 | 9 of 104 |
| together | assertion | 74 | 0 | 0 | 0 | 0 | 0 | 74 | 74 | 0 of 74 |
| together | name | 123 | 22 | 0 | 14 | 0 | 2 | 161 | 159 | 36 of 159 |
| together | none | 0 | 0 | 62 | 0 | 91 | 14 | 0 | 0 | 0 of 0 |
| together | all | 197 | 22 | 62 | 14 | 91 | 16 | 235 | 233 | 36 of 233 |

## First reading of the flags

Each flag of the first study in 1 of 6 categories, by the agreed label and the described check of the first reading. A flag whose agreed label names a check while no check is described fits no category and fails a check.

| Library | Class | agreed label equals the described check | agreed label names another check than the described one | agreed label none, described check given | agreed label none, no described check given | no agreed label, described check given | no agreed label, no described check given | in no category | agreed label equals rule-2 target | agreed label is not the rule-2 target | no agreed label |
|---|---|---|---|---|---|---|---|---|---|---|---|
| google-auth | C | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| oauthlib | C | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| authlib | C | 3 | 0 | 3 | 6 | 0 | 0 | 0 | 0 | 12 | 0 |
| joserfc | A | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| joserfc | C | 37 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | 57 | 0 |
| together | A | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| together | C | 52 | 0 | 23 | 6 | 0 | 0 | 0 | 0 | 81 | 0 |

## Expectations L1 to L3

Units and status of the expectations of section 2 of the protocol. L3 with rule-3 targets is a supplement and not part of the expectations of the protocol.

| Expectation | Library | Units | Hold | Do not hold | Status | Units that do not hold |
|---|---|---|---|---|---|---|
| L1 | google-auth | 0 | 0 | 0 | not applicable | - |
| L1 | oauthlib | 0 | 0 | 0 | not applicable | - |
| L1 | authlib | 0 | 0 | 0 | not applicable | - |
| L1 | joserfc | 3 | 3 | 0 | held | - |
| L1 | together | 3 | 3 | 0 | held | - |
| L2 | google-auth | 2 | 2 | 0 | held | - |
| L2 | oauthlib | 10 | 10 | 0 | held | - |
| L2 | authlib | 3 | 3 | 0 | held | - |
| L2 | joserfc | 37 | 37 | 0 | held | - |
| L2 | together | 52 | 52 | 0 | held | - |
| L3 | google-auth | 13 | 13 | 0 | held | - |
| L3 | oauthlib | 43 | 43 | 0 | held | - |
| L3 | authlib | 15 | 15 | 0 | held | - |
| L3 | joserfc | 67 | 64 | 3 | not held | `tests/jwt/test_claims.py::TestJWTClaims::test_claim_jti\|tests/jwt/test_claims.py::TestJWTClaims.test_claim_jti#3\|0`; `tests/jwt/test_claims.py::TestJWTClaims::test_claim_jti\|tests/jwt/test_claims.py::TestJWTClaims.test_claim_jti#3\|1`; `tests/jwt/test_claims.py::TestJWTClaims::test_claim_jti\|tests/jwt/test_claims.py::TestJWTClaims.test_claim_jti#5\|0` |
| L3 | together | 138 | 135 | 3 | not held | `joserfc: tests/jwt/test_claims.py::TestJWTClaims::test_claim_jti\|tests/jwt/test_claims.py::TestJWTClaims.test_claim_jti#3\|0`; `joserfc: tests/jwt/test_claims.py::TestJWTClaims::test_claim_jti\|tests/jwt/test_claims.py::TestJWTClaims.test_claim_jti#3\|1`; `joserfc: tests/jwt/test_claims.py::TestJWTClaims::test_claim_jti\|tests/jwt/test_claims.py::TestJWTClaims.test_claim_jti#5\|0` |
| L3, rule 3 | google-auth | 13 | 13 | 0 | held | - |
| L3, rule 3 | oauthlib | 74 | 74 | 0 | held | - |
| L3, rule 3 | authlib | 15 | 15 | 0 | held | - |
| L3, rule 3 | joserfc | 89 | 89 | 0 | held | - |
| L3, rule 3 | together | 191 | 191 | 0 | held | - |

## Checks

Each check of the program and whether it holds.

| Check | Holds |
|---|---|
| agreement categories sum to the blocks labeled by both readings, and with label missing to the included blocks | yes |
| case kinds sum to the cases | yes |
| outcomes sum to the cases with an agreed label that names a check | yes |
| rule categories sum to the cases, in each tier and for all tiers | yes |
| first-reading categories sum to the flags | yes |
| agreement categories equal counts.json | yes |
| agreement statistics equal counts.json | yes |
| case counts, outcomes, rule categories and first-reading counts equal counts.json | yes |
| first-reading.csv and outcomes.csv agree with rule-vs-label.csv | yes |
| equal label texts of the statistics "labels" equal the blocks of "same check" and "both none", per library and together | yes |
