# Deviations from the protocol

`PROTOCOL.md`, section 6, asks that a defect of a program found after the
protocol commit be corrected and described here with the change, and that
every run that used the program be repeated; a correction of form of a labels
file is listed here too. Times are in Coordinated Universal Time (UTC), on
14 November 2026.

## 1. Defects of the programs

### 1.1 The wording of 1 kind of assertion in the reading pack

`labels/prepare.py` writes the assertions of a block as text into the column
`assertions` of `blocks.tsv`. For the statement `excinfo.match(pattern)` made
after a block, the text was "after the block: re.match <pattern> on the
exception". pytest searches the pattern in the text of the exception; it does
not match from the start of the text. The first experiment computes a search
as well (`reach/targets.py`), so no target and no count of the first
experiment is affected. The wording of the pack could be read as a match from
the start of the text, which removes more checks than the assertion does.

The defect was found from a remark returned with reading A of google-auth, at
14:17, before a labels file was compared with a record, a target or another
reading, and before reading B started.

Change: 1 line of `labels/prepare.py`; the text is now "after the block:
re.search <pattern> in str(exception)". A unit test fixes the texts of the 5
kinds of assertion (`labels/tests/test_labels.py`).

Runs repeated:

- The 4 packs and their parts were built again at 14:20:08. The packs of
  oauthlib, authlib and joserfc, and their parts, are byte for byte equal to
  the first build: no block of the 3 libraries carries an assertion of this
  kind. The pack of google-auth differs in the column `assertions` of 14 of
  the 17 rows of `blocks.tsv` and in the line of that file in `MANIFEST.txt`,
  and in nothing else.
- Reading A of google-auth was repeated on the corrected pack. The labels of
  the first run are kept in `labels/readings/google-auth/A-first-pack.tsv`;
  no analysis reads that file.
- Reading B used the corrected pack of google-auth from its start.

### 1.2 The trace plugin read an environment variable inside its callback

`trace/plugin.py` took the test id of a start from the environment variable
`PYTEST_CURRENT_TEST`, with a call of `os.environ.get` inside the callback of
`sys.monitoring`. 3 tests of google-auth replace `os.environ.get` for their
duration (`tests/oauth2/test_webauthn_handler.py`, 2 tests, and
`tests/oauth2/test_webauthn_handler_factory.py`, 1 test). Under the plugin the
call of the callback reached the replaced function, and the 3 tests failed in
each of the 3 traced runs, while all 2349 tests passed in the 3 runs without
the plugin. Sentinel T3 did not hold for google-auth (2346 passing tests
against 2349 deposited), and the step stopped for that library, as section
4.2 of the protocol asks. The traced runs of joserfc, authlib and oauthlib
had ended with every sentinel holding.

Change: the callback calls nothing that a test can replace. The test id is
the node id that pytest passes to its `pytest_runtest_logstart` hook; the
paths of the subject files are spelled out when the plugin starts, and a file
name is looked up among them without a call of `os`; `threading.get_ident`
and `sys._getframe` are bound when the module is imported. A new sentinel,
T-files, does not hold when a code of a subject file ran under a file name
that is none of the spellings. The synthetic package of the unit tests holds
a test that replaces `os.environ.get` and counts its calls; it fails under
the plugin as it was and passes under the corrected one.

Runs repeated: the traced and plain runs of the 4 libraries and of the 3
development subjects, 3 repeats each, with the corrected plugin. No output of
the first runs is used. Rule 3 had not been computed for any of the 4
libraries when the defect was found, and no labels file had been compared.

### 1.3 The rows of M3 in the program that counts mutants at a check

`mutants/at_check.py`, run with a cases file, computed M3 over every row that
has a variant. Section 2 of the protocol defines M3 over the shadowed cases
that have a variant. The difference was found in the second computation
(step 8 of section 6), on the development rows (`recompute/NOTES.md`,
sections 5.3 and 5.6), after the mutant runs of joserfc.

Change: the program limits M3 to the rows whose described check is not their
deciding check, as it does for M1 and M2.

Runs repeated: `mutants/at_check.py` for joserfc and for the development
subject pyjwt-package. In joserfc only the 4 shadowed rows have a variant.
Every output file of the 2 runs is byte for byte equal to the file before
the change.

## 2. Additions to what the protocol lists

None of these changes a definition, a program of the analysis or a label.

### 2.1 A 4th repaired variant of joserfc

Section 4.3 of the protocol states that the variants of the 3 class-A cases
of joserfc were written before its commit, and step 5 of section 6 asks for a
variant of each shadowed case that has none. The labels show 1 more shadowed
case, `TestJWECompact.test_header_exceeds_size#0`, which the program's target
under rule 2 did not flag. Its variant
(`repaired/joserfc/tests_repaired/test_repaired_jwe_compact_header.py`) was
written at 14:49 and verified at 14:50 (`repaired/joserfc/verify.json`, all 7
sentinels), after the analysis of the labels (14:43) and before any mutant of
joserfc was made (14:52). The 3 earlier variant files are unchanged, byte for
byte. `repaired/joserfc/verify.py` now lists 4 cases.

### 2.2 Files beside the outputs of section 7

- `readings/joserfc/FLAGS-RULE3.md`: the reading of the 16 flags of joserfc
  under rule 3, which step 9 of section 6 names; the folder `readings/` is
  not in the table of section 7.
- `generated/mutants/joserfc/records.tar.xz`: the raw records of the mutant
  runs, which section 7 leaves in `work/`. They are deposited so that the
  second computation can be repeated from the deposit. The 2 junit result
  files of the unmodified whole-suite runs are left out, because they name
  the machine; `records/whole/base.json` in the archive lists the tests that
  pass in both of those runs.
- `versions/joserfc-313.json`: the output of the run that section 4.5 asks
  for.
- `readings/joserfc/LABEL-OUTCOMES.md`: the reading of the 8 cases of joserfc
  that the check of their agreed label does not decide.
- `labels/summary.py`, with `generated/labels/SUMMARY.md` and
  `generated/labels/summary.json`: the 4 libraries together, the agreement
  pooled over them and L1 to L3 overall. The definitions are those of
  section 4.1; the protocol lists the outputs per library only.
- `recompute/second_totals.py` and `recompute/compare_totals.py`: the totals
  over the 4 libraries on the second side, and their comparison.
  `recompute/out/<name>/second_targets3.json`: the rule output as the second
  script writes it. `recompute/tests/`: unit tests of the comparison scripts.
- `generated/SHA256SUMS` and `recompute/out/SHA256SUMS`: the SHA-256 digest of
  every file under `generated/` and of every second output. From either
  folder, `sha256sum -c --quiet SHA256SUMS` checks them.

### 2.3 What the second computation shares with the first programs

Step 8 of section 6 asks for a second script written without sight of the
analysis code of the first programs. The second scripts do not import or
call the analysis programs of this experiment. They do share the following
with the first computation (`recompute/NOTES.md`, sections 1 and 7):

- the rule code `reach/targets.py` of the toolkit, which both sides call, so
  rule 3 itself is not computed a second time;
- the trace output `generated/trace/<name>/reach.json`, which both sides
  read;
- `recompute/second.py` of the toolkit, the second computation of
  `../target-reach/`, which 3 of the 4 second scripts import;
- `mutants.csv`, the cases file and the raw records of the mutant runs,
  which programs of the first computation wrote.

The comparison scripts were written afterwards, with sight of both sides.
Agreement of the 2 sides therefore shows that the arithmetic and the
definitions match on the same records. It does not check the rule code, the
trace, the labels or the mutant runs.

## 3. Events of the runs

### 3.1 The 2 runs of reading A of google-auth

Reading A of google-auth was made 2 times (deviation 1.1). The 2 files give
the same label for 17 of the 17 blocks. The column `basis` differs in 14
rows, and the columns `quote` and `note` differ in 17 and 16 rows. The
analysis reads the column `label` only, of `A.tsv`.

### 3.2 Repeats of the traced runs

The suites of joserfc, authlib and oauthlib were traced 2 times, before and
after the correction of deviation 1.2; `trace/README.md` ("Repeats") states
what the 2 runs give. For jwcrypto, a development subject, the repeat
sentinel on started functions does not hold in the deposited run, for 1
function; the same paragraph gives the detail. No run was repeated until its
repeats agreed.

### 3.3 Expectations that are not held

T1, T3, L3, M1 and M2 are not held. M3 is not held when only tool mutants
count, and held when the deletion of a check counts as a mutant at that
check. The protocol leaves that reading open, and both are reported
(`recompute/NOTES.md`, section 5.2). The outcomes are stated in `README.md`,
`trace/README.md`, `generated/labels/SUMMARY.md` and `mutants/README.md` ("Run
on joserfc"). No definition was changed because of them.

### 3.4 Differences found by the second computation

The first comparison of the second outputs with the first outputs gave 19
differing values (`recompute/NOTES.md`, sections 4.1 and 5): 12 for the
labels of jwcrypto and 3 for the mutants of pyjwt-package, both on
development data, and 4 for the mutants of joserfc.

- The 12 values are agreement statistics. The development output of jwcrypto
  that was kept comes from an earlier state of `labels/analyse_labels.py` and
  does not hold them. A rerun of the program on the same inputs gives the
  values of the second script.
- The 3 values concern M1 on development rows. The protocol defines no
  expectation over these rows, and they are listed as not compared.
- The 4 values are M3 on 3 rows of joserfc and the status of M3. The 2 sides
  had read "mutant" differently (section 3.3). `mutants/at_check.py` now
  writes both readings in `described-cases.json`, under the key
  `expectations_by_reading`. Its rerun for joserfc added that key and changed
  no other value and no other file.

Differences that came from defects of the comparison scripts themselves are
listed in section 4.1 of that file. Neither side computed the agreement
pooled over the 4 libraries at first; `labels/summary.py` and
`recompute/second_totals.py` now both compute it. In the final comparison no
compared value differs on the 4 held-out libraries. The 12 values of
jwcrypto still differ against the kept development output. No second script
was changed after it was frozen.
