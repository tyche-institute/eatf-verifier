# google-auth 2.62.2: the deletions that the whole suite does not detect

A deletion replaces every raise statement of 1 check with `pass` in a copy of
the package; every other statement still runs. The checks deleted are those
that fire in at least 1 case of the study. The whole suite detects a deletion
when a test that passes in both unmodified whole-suite runs does not pass on
the copy without the check. The facts below come from
`generated/google-auth/SUMMARY.md`, `generated/google-auth/deletions.csv` and
`generated/google-auth/undetected.csv`. Line numbers refer to the commit of
the subject (`subjects/google-auth/subject.json`, commit
`50b1eb269f110a4b7ab09ffe5ae59c0151cd63c2`).

| Deleted check | Cases in which it fires | After the deletion | Witness file | Does the deletion change what the library accepts? |
|---|---|---|---|---|
| none | | | | |

Counts: 13 checks fire in the negative tests of the study, and 13 are
deleted. All 13 are deciding checks; 0 checks fire and never decide. The
whole suite (2349 tests that pass in both unmodified runs, suite runs `unit`
over `tests` and `tests_async`) detects the deletion of all 13 and misses 0.
`generated/google-auth/undetected.csv` holds its header line and no row.

## Reasons

There is nothing to describe: no deletion escapes the whole suite, so no
input was sought and no witness test was written. The recorder runs agree:
the tests that hold the cases (O_S) and the suite under the recorder detect
all 13 deletions as well (`generated/google-auth/SUMMARY.md`, table of
deletions not detected).

## What this library shows

Every check that fires in the negative tests of google-auth decides at least
1 case, and the whole suite detects the deletion of each of them.
