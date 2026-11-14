# oauthlib 4.0.1: the deletions that the whole suite does not detect

A deletion replaces every raise statement of 1 check by `pass` in a copy of
the package. The checks deleted are those that fire in at least 1 case of the
study. The whole suite detects a deletion when a test that passes in both
unmodified whole-suite runs does not pass on the copy without the check.
For each deletion it misses, this file would give the cases in which the
check fires, what rejects their inputs after the deletion (from
`generated/oauthlib/undetected.csv`) and whether some input that the check
rejects is accepted without it, shown by a witness file that holds. Line
numbers refer to the commit of the subject (`subjects/oauthlib/subject.json`,
commit `6e3aa05a`).

| Deleted check | Cases in which it fires | After the deletion | Witness file | Does the deletion change what the library accepts? |
|---|---|---|---|---|
| none | | | | |

Counts: 0 deletions not detected by the whole suite.

## Reasons

47 checks fire in the negative tests of the study, and all 47 decide at least
1 case: 47 deciding checks, 0 checks that fire and never decide
(`generated/oauthlib/SUMMARY.md`, rows `checks_deciding`, `checks_firing` and
`checks_firing_and_never_deciding`). Each of the 47 was deleted (rows
`deletions` and `deletions_of_deciding_checks`). The whole suite, 717 tests
that pass in both unmodified runs, detects every one of the 47 deletions: the
row "whole suite" of the table of deletions not detected gives 0, and
`generated/oauthlib/undetected.csv` holds its header and no row. The O_S
oracle and the suite under the recorder detect all 47 as well (0 not
detected in both rows).

There is no deletion to describe, no case to read after a deletion and no
witness file.
