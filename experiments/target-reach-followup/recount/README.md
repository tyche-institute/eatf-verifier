# Recount from the deposited outputs of target reach

`recount.py` recomputes and extends counts of the toolkit in `../target-reach`
from its deposited files alone. It runs no library and no test. It reads, for
each of the 7 subjects (`pyjwt`, `pyjwt-package`, `jwcrypto`, `google-auth`,
`oauthlib`, `authlib`, `joserfc`):

- `../target-reach/generated/<name>/cases.csv`, `checks.csv`,
  `deletions.csv`, `flags.csv`, `pinning.csv` and `summary.json`;
- `../target-reach/generated/<name>/records.tar.xz`, extracted into
  `work/recount/records/<name>/`, of which only `records/base-1.json` (the
  first baseline recorder run) is read;
- `../target-reach/subjects/<name>/targets.json`, `blocks.json` and
  `checks.json` (only its list `other_raises`);
- the table and the line "Counts:" of `../target-reach/readings/<name>/FLAGS.md`,
  where the file exists (`jwcrypto` and the 4 held-out libraries).

It does not import or read `../target-reach/reach/analyse.py` or
`../target-reach/recompute/second.py`. The terms are those of
`../target-reach/PROTOCOL.md`, section 4.

## How to run

From the experiment directory, with Python 3.12 or later and the standard
library only:

    python3 -I -B recount/recount.py

It writes `generated/recount/recount.json` and `generated/recount/RECOUNT.md`,
prints the number of sentinels and of those that do not hold, and exits with
status 1 when any sentinel does not hold. The outputs are written in either
case. Options: `--source` (default `../target-reach`), `--work` (default
`work/recount/records`), `--out` (default `generated/recount`), `--subjects`,
`--held-out`, and `--held-out-totals`, a JSON file that replaces the fixed
totals of sentinel group S2 (used by the tests).

The tests build a synthetic deposit of 1 toy subject and run the recount on
it, in an environment that has pytest:

    cd recount && <python with pytest> -B -m pytest -q -p no:cacheprovider -c tests/pytest.ini tests

## Columns read and their meaning

- A *case* is 1 row of `cases.csv`, identified by (`block`, `index`,
  `test_node`). The 3 fields together are the key; `block` alone is not
  unique, since a block of a base class can run under several test files.
- The *raise site* of a case is `cases.csv:baseline_site`. A case is *decided
  by a check* when its raise site is an identifier listed in `checks.csv`;
  that check is its *deciding check*. Any other value (in the deposit, the
  form `other raise (<file>:<line> <statement>)`) means that no check decides
  the case.
- The *target* of a case is `cases.csv:target`; empty means no target. Its
  *tier* is `cases.csv:tier` (`assertion` or `name`).
- A deletion is 1 row of `deletions.csv`. A deletion is *not detected* by an
  oracle when its column holds `no`: `O_V`, `O_Vfc`, `O_C`, `O_T`, `O_S`,
  `suite`, and `whole_suite` for the whole suite. These are the main columns
  of the toolkit, in which withheld cases are not counted as failing; the
  withheld-as-failing columns are not read.
- *In a handler* is the column `in_handler` of `checks.csv`, taken as
  deposited. The recount does not recompute it from the sources.

## Definitions of the counts

**Reproduced counts** (per subject, and summed over the 4 held-out
libraries): cases = rows of `cases.csv`; cases with a target = cases with a
non-empty target; decided by the target = cases with a target whose raise site
equals the target; flags = cases with a target whose raise site differs from
the target; deciding checks = distinct raise sites that are checks; deletions
of deciding checks not detected by an oracle = rows of `deletions.csv` whose
check is a deciding check and whose column for the oracle is `no`.

**1. O_T against its own denominator.** The deciding checks are split into 3
disjoint groups:

- *targeted deciding checks*: deciding checks that are the target of at least
  1 case that they decide (equivalently, the targets of the cases decided by
  their target);
- *deciding checks that are the target of no case*: no row of `cases.csv` has
  the check as its target;
- *deciding checks that are a target only of cases they do not decide*: the
  remaining deciding checks; each is the target of at least 1 case and decides
  none of the cases whose target it is.

For each group: the number of checks, the number that have a row in
`deletions.csv` ("deleted"; a deciding check of an observed file of
`subjects/pyjwt` is not deleted), and, over those deletions, the number not
detected by each of the 7 oracles. O_T holds at baseline only for a case
decided by its target, so a deletion can be detected by O_T only through such
a case. The row "cases decided by their target" gives the number of cases for
which O_T holds at baseline.

**2. Checks that fire and never decide.** Checks that fire in at least 1 case
(the union of the field `fired` of the cases of the study in
`records/base-1.json`) and decide no case. "Deleted" counts the rows of
`deletions.csv` whose check decides no case; for each oracle, the number of
those deletions whose column is `no`.

**3. Cases decided by a statement that is not a check.** Cases whose raise
site is no check. For each: the case key, and, from the matching case of
`records/base-1.json`, the kind, file, line and source text of the raise
site; and, from `checks.json:other_raises`, the entry with the same file and
line: its class label, its reason and its guard. The pinning denominators:
the cases of the study; those not counted in pinning because no check decides
them; those whose deciding check was not deleted; the rows of `pinning.csv`.

**4. Flags per tier and per class.** Per tier (assertion, name): cases with a
target, cases decided by the target, flags, and the flags in each of the
classes A, B, C, D read from `FLAGS.md`. A row of the table of `FLAGS.md` is
matched to a flag by the test node it names (the file after "run under" when
present, else the file of the cited line, joined by `::` to the case label
with `.` replaced by `::`), the block number `#k`, the execution index (the
number in `[i]`, 0 when absent) and the file of the block. A subject without
`FLAGS.md` gets "not read". Then every flag whose row in `pinning.csv` has
`test_passes` = `yes`: the own test of the case passes on the copy without
its deciding check. For each, the class of the reading, and the class and
the site that `pinning.csv` gives for the case on that copy (the columns
`class` and `site`), with `what_the_case_does`.

**5. PyJWT, both scopes.** Every flag (test node, target, deciding check, the
columns `target_fired` and `own_test_without_target`) and every row of
`pinning.csv` with `test_passes` = `yes`, each with the assertions of its
block from `blocks.json`: the pattern (`match`), the assertions after the
block (`post`) and the parts that could not be parsed (`match_unparsed`,
`post_unparsed`), and the column `asserts` (`class only` or `message`).

**6. Checks inside an except handler.** Checks with `in_handler` = `yes`; of
them, the deciding checks; the number of cases these deciding checks decide;
and the number of these checks that were deleted.

## Sentinels

The recount writes its outputs and then exits with status 1 when any sentinel
does not hold. The groups:

- **S1.** Per subject, the reproduced counts equal `summary.json`: `cases`,
  `cases_with_target`, `cases_with_target_by_outcome["decided by the target"]`,
  `flags`, `checks_deciding`, `deletions_of_deciding_checks`, and
  `deletions_not_detected_of_deciding_checks` for O_V, O_Vfc, O_C, O_T and the
  whole suite.
- **S2.** The sums over the 4 held-out libraries equal 402 cases, 229 with a
  target, 145 decided by the target, 84 flags, 137 deciding checks, and 24,
  57, 6, 82 and 5 deletions of deciding checks not detected by O_V, O_Vfc,
  O_C, O_T and the whole suite.
- **S3.** The files agree with each other: the rows of `cases.csv` are the
  cases of the study in `records/base-1.json` (included block, an exception
  raised, of a rejection class, accepted by the block's own check), with no
  repeated key; the raise site of every case agrees with the record; the
  target and tier of every case agree with `targets.json`; the rows of
  `flags.csv` are the flags; `checks.csv` columns `decides` and
  `cases_decided` agree with `cases.csv`; the rows of `deletions.csv` are the
  checks of the subject files that fire in at least 1 case of the record; the
  rows of `pinning.csv` are the cases whose deciding check was deleted; every
  oracle column holds `yes` or `no`; `in_handler` agrees between
  `deletions.csv` and `checks.csv`.
- **S4.** Further counts of `summary.json`: `reached_targets`,
  `reached_targets_deletion_not_detected_O_T`,
  `checks_firing_and_never_deciding`,
  `deletions_of_checks_that_fire_and_never_decide`, `deletions_not_detected`
  for each of the 7 oracles as the sum of the 2 kinds of deletion,
  `cases_by_site_kind`, `cases_with_target_by_tier`, `flags_by_tier`,
  `deletions_in_handler`, and in `pinning`: `cases`, `test_passes`,
  `cases_not_counted_no_deciding_check`,
  `cases_not_counted_deciding_check_not_deleted`.
- **S5.** The reading: every row of the table of `FLAGS.md` names exactly 1
  flag, every flag has exactly 1 row, the classes of the rows agree with the
  line "Counts:", and the columns "Target fires" and "Own test without the
  target" agree with `cases.csv` and `flags.csv`.
- **S6.** The 3 groups of count 1 partition the deciding checks.

`recount.json` lists every sentinel with what was expected and found; for a
sentinel that holds, a list or mapping longer than 300 characters is shown by
its size only.
