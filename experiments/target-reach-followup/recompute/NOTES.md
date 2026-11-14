# Second computation: report of step 8

## 1. Purpose and scope

Step 8 of section 6 of `PROTOCOL.md` reads: "A second script, written from
this protocol without sight of the first programs' analysis code, recomputes
the counts of steps 3, 4 and 6 from their records, and every difference is
resolved or reported". This file is the report of that step.

The counts recomputed are:

- rule 3 and its analysis (step 3: `trace/rule3.py`, `trace/analyse3.py`);
- the labels, their agreement, the outcomes, the shadowed cases, program
  against label, the first reading and the expectations L1 to L3 (step 4:
  `labels/analyse_labels.py`);
- the mutants and the expectations M1 to M3 (step 6: `mutants/analyse_mutants.py`,
  `mutants/at_check.py`);
- the totals over the 4 held-out libraries (`labels/summary.py` and
  `generated/trace/compare.json`).

"Second" means: the same records and the same label files, read by separate
code. The second scripts do not import or call the analysis programs of the
first computation (`trace/rule3.py`, `trace/analyse3.py`,
`labels/analyse_labels.py`, `labels/summary.py`, `mutants/analyse_mutants.py`,
`mutants/at_check.py`). They do depend on the following programs and files,
which the first computation also uses or which a program of this experiment
wrote:

- `recompute/second_rule3.py` reads `generated/trace/<name>/reach.json`,
  written by the trace step (`trace/trace_run.py`). It gives, per function,
  the entry points under which the function started in the traced run of the
  whole suite. Both computations start from it, so the comparison cannot
  detect an error in the trace.
- `recompute/second_rule3.py` imports the rule code `reach/targets.py` of the
  toolkit and calls `compute_targets`, the function that `trace/rule3.py` also
  calls. The rule is therefore not computed a second time. The block
  transitions and the blocks that target each check are tallies of the rule
  output. The script computes the following separately:
  - which checks are reachable by execution and under rule 3 (the widening of
    the field `reachable`);
  - the cases of the study and the deciding check of each case, from the
    records;
  - whether the target decides each case, and the outcomes;
  - the case transitions between the rules;
  - the fired checks and where their functions started;
  - the quantities of T1 to T3.
- `recompute/second_rule3.py` imports `recompute/second.py` of the toolkit,
  the second computation of the toolkit, which imports nothing from the
  toolkit. It runs that computation on a copy of the definitions that holds
  the rule-3 targets, for the group `toolkit_second_under_rule3`: the
  outcomes of the cases with a target, the O_T detections and the own test on
  the copy without the target. The first side takes these values from
  `reach/analyse.py`, which `trace/analyse3.py` runs. The comparison of these
  values sets the 2 computations of the toolkit against each other, not code
  of the second script (section 4.5).
- `recompute/second_labels.py` imports `recompute/second.py` of the toolkit
  for the unpacking of the records, the key of a case and the status of a
  case in a deletion run. The first program takes the key and the status of
  a case from `reach/study.py` and `reach/analyse.py` of the toolkit.
- `recompute/second_labels.py` takes the rule-3 targets as an input
  (`--targets3`). The deposited outputs were first written with
  `generated/trace/<name>/targets.json`, the rule output of the first program
  `trace/rule3.py`. Written again with `recompute/out/<name>/second_targets3.json`,
  the rule output of the second script, each of the 4 outputs is
  byte-identical (`cmp`) to the deposited file. The commands of section 3.2
  use the second rule output. Either rule output comes from `compute_targets`.
- `recompute/second_mutants.py` imports `recompute/second.py` of the toolkit
  for the unpacking of the records, the key of a case, whether a test passes,
  the status of a case, the removal of message texts, and the counts of the
  toolkit. It uses these counts only to set its deletions against the
  deposited deletion records of the toolkit (an input check).
- `recompute/second_mutants.py` reads `mutants.csv`, written by
  `mutants/materialize.py`. The script checks its list of mutants against
  `manifest.json`, its changed lines against its own line comparison of each
  modified file with the clone, and its digests against the modified files.
  It takes the columns `function`, `operator` and, for a deletion, `check` as
  given. The first outputs take them from the same file, so the comparison
  cannot detect an error in these 3 columns.
- `recompute/second_mutants.py` reads the cases file
  `generated/mutants/<name>/cases.tsv`, written by `mutants/cases_file.py` from
  `generated/labels/<name>/outcomes.csv` (an output of
  `labels/analyse_labels.py`), `labels/first/<name>.tsv` and the deposited
  outputs of the toolkit. The script takes the shadowed rows (case, described
  check, kind, variant) as given. It derives the comparison cases itself and
  checks them against the rows of kind "comparison". The shadowed cases are
  checked apart: `recompute/compare_labels.py` sets the shadowed cases of
  `recompute/second_labels.py` against `shadowed.csv`, which
  `mutants/cases_file.py` writes with the cases file.
- `recompute/second_mutants.py` reads the raw records in `work/mutants/<name>/`
  (not deposited, section 3.2).
  `mutants/materialize.py` wrote `manifest.json` and the modified files, and
  `mutants/run_mutants.py` wrote the run records, the recorder records, the
  baseline records and the records of the extra runs. The script checks the
  digests of the modified files, the baseline records against the deposited
  records of the toolkit, and the deletions against the deposited deletion
  records of the toolkit. It takes the kills of a mutant from the field
  `lost` of the run records, as the first program does (section 7).
- `recompute/second_totals.py` reads only outputs of the second scripts.

The comparison scripts then set each second output against the first
outputs, value by value.

The held-out libraries are google-auth, oauthlib, authlib and joserfc. The
development subjects are pyjwt, pyjwt-package and jwcrypto.

## 2. The second scripts

Each second script was written from `PROTOCOL.md`, the documents that
describe the formats of the records, and the records themselves. While each
was written, the analysis code of the first programs and any text that
states their results were withheld. The outputs of the first programs were
withheld too, except the files named in section 1, which were available as
inputs. The rule code `reach/targets.py` and `recompute/second.py` of the
toolkit were not withheld from the writing of the scripts that import them.
`recompute/second_totals.py` was written from `PROTOCOL.md` and the outputs
of `recompute/second_labels.py` and `recompute/second_rule3.py`.

The command logs kept while the 4 second scripts were written were searched
for every file that was opened. No analysis program of the first
computation was opened, no output of one other than the inputs named in
section 1, and no document that states their results. While
`recompute/second_totals.py` was written, 2 listing commands printed the
names of files outside its list, and 1 search for cache folders ran over the
experiment directory and printed nothing.

The statements about what was withheld, about the search of the command
logs and about the freeze before any comparison rest on working records:
the command logs, and kept copies of the scripts with their digests. These
records are not part of the deposit. In the deposit the digests stand in
this file. The commit that first holds this file is time-stamped (step 9 of
section 6 of `PROTOCOL.md`, `timestamps/README.md`). That time stamp fixes
the digests after the comparisons, not before them.

The comparison scripts (`recompute/compare_*.py`) were written afterwards,
with sight of both sides.

The 4 second scripts were frozen before any comparison. The deposited files
have these SHA-256 digests, checked with `sha256sum recompute/second_*.py`:

| Script | SHA-256 |
|---|---|
| `recompute/second_labels.py` | `34dcf5a6603c2ca37f1f3d883ea6f735e53316145007ffbe8189aa52cddc0fc6` |
| `recompute/second_rule3.py` | `457fcad3c59d12391ebc5af6dd198258cbb60aae7f0222e7127eb667f6b5a0de` |
| `recompute/second_mutants.py` | `f05c76f6146eb116c52a2094172877bf620128a89bdd38f995d2eca2c9c867c2` |
| `recompute/second_totals.py` | `1f7883a5c6671625a888113b4b3878c460af7e380244d542f56ed43ed1a7ad81` |

No second script was changed after it was frozen.

### 2.1 recompute/second_labels.py

Reads, for 1 subject:

- `subject.json` of the toolkit, with `checks.json`, `blocks.json` and the
  rule-2 `targets.json` beside it;
- the deposited `records.tar.xz` of the toolkit;
- the label files, 1 or 2 (readings A and B);
- optionally the rule-3 targets (`--targets3`) and the transcription of the
  first reading of the flags (`--first`, `labels/first/<name>.tsv`).

It imports only `recompute/second.py` of the toolkit, for the unpacking of
the records, the key of a case and the status of a case in a deletion run. It writes
`recompute/out/<name>/second_labels.json`: readings, agreement and Cohen's
kappa in 2 forms with their marginal counts, outcomes, shadowed cases,
program against label for rule 2 and rule 3, the first reading and L1 to L3.

### 2.2 recompute/second_rule3.py

Reads the subject folder of the toolkit (`subject.json`, `checks.json`,
`blocks.json`, the rule-2 `targets.json`), the deposited `records.tar.xz` and
the trace output `generated/trace/<name>/reach.json`. It imports 2 parts of
the toolkit and uses them as they are:

- `reach/targets.py`, the rule code: rule 2 on the unchanged `checks.json`,
  and rule 3 on a copy whose field `reachable` is widened by the checks whose
  function started under an entry point;
- `recompute/second.py`, the second computation of the toolkit, run on a
  copy of the definitions that holds the rule-3 targets; its result is kept
  in the group `toolkit_second_under_rule3`.

Everything else is computed from the records and `reach.json`. It writes
`recompute/out/<name>/second_rule3.json` and, with `--targets-out`, the rule
output `recompute/out/<name>/second_targets3.json`.

### 2.3 recompute/second_mutants.py

Reads, for 1 subject:

- the subject definition of the toolkit and its deposited `records.tar.xz`
  (the cases of the study, their deciding checks, their classes, the tests
  that pass at baseline);
- the raw records of the mutant runs in `work/mutants/<name>/` (manifest,
  modified files, run records, recorder records, baseline records, records
  of the extra runs);
- `mutants.csv`, the sources of the mutated files in the clone of the
  library, the cases file, the folder of the extra tests, and the given
  removals and replacements of tests.

It imports `recompute/second.py` of the toolkit (section 1). It writes
`recompute/out/joserfc/second_mutants.json`, which records every argument
except the output path as given on the command line.

### 2.4 recompute/second_totals.py

Reads `recompute/out/<name>/second_labels.json` and
`recompute/out/<name>/second_rule3.json` of the 4 held-out libraries and
nothing else. It writes `recompute/out/second_totals.json`: the agreement
pooled over the 4 libraries, cases, outcomes, program against label, the
first reading, L1 to L3 overall, rule counts and transitions, T1 to T3, and
338 consistency checks.

## 3. Commands

Every command runs from the experiment directory, with the standard library
of Python 3.12 or later. The toolkit is found at `../target-reach`. `OUT`
stands for a folder outside the experiment directory.

### 3.1 Integrity of the second scripts

    sha256sum recompute/second_*.py

The 4 digests equal the table of section 2.

### 3.2 Second outputs of the held-out libraries

    CA=$(awk -F'\t' 'NR>1 && $4=="A"{print $3"|"$1"|"$2}' labels/first/joserfc.tsv | tr '\n' ' ')
    for n in google-auth oauthlib authlib joserfc; do
      EX=""; [ $n = joserfc ] && EX="--class-a $CA"
      python3 -I -B recompute/second_rule3.py --subject ../target-reach/subjects/$n/subject.json \
        --records ../target-reach/generated/$n/records.tar.xz --reach generated/trace/$n/reach.json \
        --out recompute/out/$n/second_rule3.json --targets-out recompute/out/$n/second_targets3.json $EX
    done
    for n in google-auth oauthlib authlib joserfc; do
      python3 -I -B recompute/second_labels.py --subject ../target-reach/subjects/$n/subject.json \
        --records ../target-reach/generated/$n/records.tar.xz \
        --labels labels/readings/$n/A.tsv labels/readings/$n/B.tsv \
        --targets3 recompute/out/$n/second_targets3.json --first labels/first/$n.tsv \
        --out recompute/out/$n/second_labels.json
    done
    python3 -I -B recompute/second_totals.py --out recompute/out/second_totals.json
    python3 -I -B recompute/second_mutants.py --subject ../target-reach/subjects/joserfc/subject.json \
        --work work/mutants/joserfc --mutants generated/mutants/joserfc/mutants.csv \
        --clone ../target-reach/work/src/joserfc --cases generated/mutants/joserfc/cases.tsv \
        --extra-tests repaired/joserfc/tests_repaired \
        --records ../target-reach/generated/joserfc/records.tar.xz \
        --without-tests "all|tests.jwe.test_compact.TestJWECompact::test_ciphertext_exceeds_size" \
                        "all|tests.jwe.test_compact.TestJWECompact::test_header_exceeds_size" \
                        "all|tests.jws.test_compact.TestCompact::test_payload_exceeded_size_error" \
                        "all|tests.jws.test_json.TestJSON::test_b64_must_be_protected" \
        --replace "all|tests.jwe.test_compact.TestJWECompact::test_ciphertext_exceeds_size=test_repaired_ciphertext_exceeds_size" \
                  "all|tests.jwe.test_compact.TestJWECompact::test_header_exceeds_size=test_repaired_header_exceeds_size" \
                  "all|tests.jws.test_compact.TestCompact::test_payload_exceeded_size_error=test_repaired_payload_exceeded_size_error" \
                  "all|tests.jws.test_json.TestJSON::test_b64_must_be_protected=test_repaired_b64_must_be_protected" \
        --out recompute/out/joserfc/second_mutants.json

Each script exits with 0. Run with `--out` and `--targets-out` under `OUT`,
and with `--targets3` naming the rule output under `OUT`, each gives a file
byte-identical (`cmp`) to the deposited one. `recompute/second_totals.py`
records the paths of its inputs. Run with `--out` under `OUT` on the
deposited inputs, it gives a file byte-identical to the deposited one. Run
with `--out-dir OUT` on the outputs under `OUT`, its file differs only in
those recorded paths. `recompute/second_totals.py`
prints a line that ends in "checks 338, failed 0". The joserfc line of
`recompute/second_mutants.py` ends in "M1 not held, M2 not held, M3 not held".

`recompute/second_mutants.py` needs the raw records in `work/mutants/joserfc/`
and the clone `../target-reach/work/src/joserfc`, which are not deposited.
`generated/mutants/joserfc/records.tar.xz` holds the recorder record and the
run summary of every mutant and the baseline records, but not the manifest,
the modified files or the records of the extra runs. The comparison in
section 3.3 needs only deposited files.

### 3.3 Comparisons on the deposited data

    for n in google-auth oauthlib authlib joserfc; do
      python3 -I -B recompute/compare_labels.py --second recompute/out/$n/second_labels.json \
        --first-dir generated/labels/$n --subject ../target-reach/subjects/$n/subject.json \
        --shadowed generated/mutants/$n/shadowed.csv --summary generated/labels/summary.json
    done
    python3 -I -B recompute/compare_totals.py
    for n in google-auth oauthlib authlib joserfc; do
      EX=""; [ $n = joserfc ] && EX="--class-a-tsv labels/first/joserfc.tsv"
      python3 -I -B recompute/compare_rule3.py --second recompute/out/$n/second_rule3.json \
        --second-targets recompute/out/$n/second_targets3.json --first generated/trace/$n $EX
    done
    python3 -I -B recompute/compare_mutants.py --second recompute/out/joserfc/second_mutants.json \
        --first generated/mutants/joserfc

`recompute/compare_totals.py` reads `second_labels.json` from `recompute/out`,
the default of `--second-dir`. `recompute/compare_labels.py` and
`recompute/compare_totals.py` accept `--json FILE` for a JSON record of the
result. `recompute/compare_mutants.py` accepts `--summary FILE` for the counts
per comparison name. Expected first lines, each with exit status 0:

    google-auth: compared 339, agree 339, differ 0
    oauthlib: compared 1165, agree 1165, differ 0
    authlib: compared 501, agree 501, differ 0
    joserfc: compared 1559, agree 1559, differ 0
    compared 1830, agree 1830, differ 0
    google-auth: compared 320, agree 320, differ 0
    oauthlib: compared 701, agree 701, differ 0
    authlib: compared 380, agree 380, differ 0
    joserfc: compared 964, agree 964, differ 0
    compared 15488, agree 15488, differ 0

`recompute/compare_mutants.py` also prints "internal checks of the second
output (list length equals its count): checked 2216, failed 0". Each
comparison exits with 0 when no compared value differs, 1 when a compared
value differs, and 2 on a missing or malformed input. `recompute/compare_rule3.py`
also exits with 2 when `--class-a-tsv` is absent for a second output that
carries class-A cases (joserfc).

### 3.4 Development comparisons

The development comparisons ran on the development subjects before the
held-out data were compared. Their inputs under `work/` are not deposited
(`work/` is excluded from the deposit); "kept" below means kept in `work/`:

- labels: `work/labels/dev/pyjwt-reference.tsv`, the synthetic label files
  `work/labels/dev/jwcrypto-synthetic-1.tsv` and
  `work/labels/dev/jwcrypto-synthetic-2.tsv`, and the first outputs in
  `work/labels/dev/generated/`;
- mutants: the raw records in `work/mutants/pyjwt-package/`, the cases file
  and the extra tests in `work/mutants/dev-extra/`, and the first outputs in
  `work/mutants/dev-extra-out/`.

`labels/README.md`, section "Development runs", gives the commands that
regenerate `work/labels/dev/pyjwt-reference.tsv` and
`work/labels/dev/generated/pyjwt`. It describes the synthetic jwcrypto files
but gives no command that regenerates them. `mutants/README.md`, section
"Commands", regenerates the records in `work/mutants/pyjwt-package/`. No
README describes the cases file and the extra tests of `work/mutants/dev-extra/`
or the first outputs of `work/mutants/dev-extra-out/`.

The rule-3 development comparisons need only deposited inputs. The second
outputs go to `OUT`:

    for n in pyjwt pyjwt-package jwcrypto; do
      python3 -I -B recompute/second_rule3.py --subject ../target-reach/subjects/$n/subject.json \
        --records ../target-reach/generated/$n/records.tar.xz --reach generated/trace/$n/reach.json \
        --out $OUT/$n.json --targets-out $OUT/$n.targets3.json
      python3 -I -B recompute/compare_rule3.py --second $OUT/$n.json \
        --second-targets $OUT/$n.targets3.json --first generated/trace/$n
    done

The labels development comparisons run `recompute/second_labels.py` with the
label files above. Each development run passes as `--targets3` the rule
output of the first program, `generated/trace/<name>/targets.json`. That is
the file with which the first output of jwcrypto was written. The kept
first output of pyjwt holds no rule 3, so rule 3 is not compared against it.
Each second output is compared with the kept development output and
with a rerun of `labels/analyse_labels.py` on the same inputs with `--out`
under `OUT` (section 5.1):

    python3 -I -B recompute/second_labels.py --subject ../target-reach/subjects/jwcrypto/subject.json \
      --records ../target-reach/generated/jwcrypto/records.tar.xz \
      --labels work/labels/dev/jwcrypto-synthetic-1.tsv work/labels/dev/jwcrypto-synthetic-2.tsv \
      --targets3 generated/trace/jwcrypto/targets.json --first labels/first/jwcrypto.tsv \
      --out $OUT/jwcrypto.json
    python3 -I -B recompute/second_labels.py --subject ../target-reach/subjects/pyjwt/subject.json \
      --records ../target-reach/generated/pyjwt/records.tar.xz \
      --labels work/labels/dev/pyjwt-reference.tsv \
      --targets3 generated/trace/pyjwt/targets.json --out $OUT/pyjwt.json
    python3 -I -B labels/analyse_labels.py --subject ../target-reach/subjects/jwcrypto/subject.json \
      --labels work/labels/dev/jwcrypto-synthetic-1.tsv work/labels/dev/jwcrypto-synthetic-2.tsv \
      --targets3 generated/trace/jwcrypto/targets.json --first labels/first/jwcrypto.tsv \
      --out $OUT/first-jwcrypto
    python3 -I -B labels/analyse_labels.py --subject ../target-reach/subjects/pyjwt/subject.json \
      --labels work/labels/dev/pyjwt-reference.tsv \
      --targets3 generated/trace/pyjwt/targets.json --out $OUT/first-pyjwt
    for n in jwcrypto pyjwt; do
      python3 -I -B recompute/compare_labels.py --second $OUT/$n.json \
        --first-dir work/labels/dev/generated/$n --subject ../target-reach/subjects/$n/subject.json
      python3 -I -B recompute/compare_labels.py --second $OUT/$n.json \
        --first-dir $OUT/first-$n --subject ../target-reach/subjects/$n/subject.json
    done

First lines, in this order:

    jwcrypto: compared 376, agree 364, differ 12
    jwcrypto: compared 382, agree 382, differ 0
    pyjwt: compared 630, agree 630, differ 0
    pyjwt: compared 825, agree 825, differ 0

The first comparison exits with 1 (section 5.1), the other 3 with 0.

The rerun of `mutants/at_check.py` for joserfc (sections 5.6 and 5.7) reads
`runs.jsonl.xz`, `cases.csv.xz`, `mutants.csv` and `materialize.json` from
its output folder. These 4 files are first copied into `OUT`:

    for f in runs.jsonl.xz cases.csv.xz mutants.csv materialize.json; do
      cp generated/mutants/joserfc/$f $OUT/
    done
    python3 -I -B mutants/at_check.py --subject joserfc --cases generated/mutants/joserfc/cases.tsv \
      --extra-tests repaired/joserfc/tests_repaired --out $OUT

It exits with 0. Its `at-check.csv`, `check-spans.csv`, `described-cases.csv`
and `described-cases.json` are byte-identical (`cmp`) to those in
`generated/mutants/joserfc/`. It also reads the baseline records in
`work/mutants/joserfc/` and the clone of the library, which are not
deposited.

The mutants development comparison streams the second output into the
comparison:

    python3 -I -B recompute/second_mutants.py --subject ../target-reach/subjects/pyjwt-package/subject.json \
        --work work/mutants/pyjwt-package --mutants work/mutants/dev-extra-out/mutants.csv \
        --clone ../mutation-adequacy-pyjwt/work/pyjwt --cases work/mutants/dev-extra/dev-cases-pyjwt-package.tsv \
        --extra-tests work/mutants/dev-extra \
        --without-tests "all|tests.test_api_jws.TestJWS::test_decode_deeply_nested_header_throws_decode_error" \
                        "all|tests.test_api_jws.TestJWS::test_decode_with_non_mapping_header_throws_exception" \
        --replace "all|tests.test_api_jws.TestJWS::test_decode_deeply_nested_header_throws_decode_error=test_dev_extra_not_enough_segments" \
                  "all|tests.test_api_jws.TestJWS::test_decode_with_non_mapping_header_throws_exception=test_dev_extra_algorithm_not_allowed" \
        --out /dev/fd/3 3>&1 1>/dev/null \
      | python3 -I -B recompute/compare_mutants.py --second /dev/stdin --first work/mutants/dev-extra-out

The results are in section 4.

## 4. Results

### 4.1 First comparison

The first comparison set the frozen second outputs against the first
outputs, before any difference was resolved. The labels and rule-3 parts
were first compared on the development subjects only. The held-out data
were compared with the second scripts unchanged.

The table below is assembled afterwards, not printed as it stands. Its
labels, totals and mutants counts are those printed by the earliest kept
copies of the comparison scripts. Its rule-3 counts are those printed by
the comparison script as it stood after the development comparison, on the
development and on the held-out data. Differences that were traced to
defects of the comparison scripts themselves, and that went away when the
comparison script was corrected, are not in the table:

- labels: 6, on authlib, in the deciding check of the 6 flags of
  `tests/jose/test_jws.py::test_invalid_input`. The first output holds the
  text of a raise site that is no check, and the second output holds no
  deciding check. The comparison now compares such a value as "raise site
  is not a check" (section 6.1).
- totals: 0.
- rule 3: 1, on pyjwt, in the cases with a target per outcome with the own
  test without the target. The name map of the comparison did not translate
  the reason for the own test that `recompute/second.py` of the toolkit
  gives into the words of `reach/analyse.py`. The map was corrected.
- mutants: 1, on the development data, in a derived value: whether library
  values from the shadowed rows are present. The second output holds them
  with no shadowed row, as the values of the whole suite. The comparison
  expected them only when the first side has such rows, and was corrected.

The first run of the mutants comparison on the development data printed
compared 23823, agree 23821, differ 2, before the overall status of M1 to
M3 was compared. The 2 differences are 2 of the 3 of section 5.3. The
records of these runs, of the differences above and of the kept copies are
working records that are not part of the deposit.

| Part | Subject | Data | Compared | Agree | Differ |
|---|---|---|---|---|---|
| labels | pyjwt | development | 625 | 625 | 0 |
| labels | jwcrypto | development | 364 | 352 | 12 |
| labels | google-auth | held-out | 284 | 284 | 0 |
| labels | oauthlib | held-out | 1110 | 1110 | 0 |
| labels | authlib | held-out | 446 | 446 | 0 |
| labels | joserfc | held-out | 1504 | 1504 | 0 |
| totals | 4 libraries | held-out | 1083 | 1083 | 0 |
| rule 3 | pyjwt | development | 606 | 606 | 0 |
| rule 3 | pyjwt-package | development | 625 | 625 | 0 |
| rule 3 | jwcrypto | development | 465 | 465 | 0 |
| rule 3 | google-auth | held-out | 312 | 312 | 0 |
| rule 3 | oauthlib | held-out | 693 | 693 | 0 |
| rule 3 | authlib | held-out | 372 | 372 | 0 |
| rule 3 | joserfc | held-out | 956 | 956 | 0 |
| mutants | pyjwt-package | development | 23826 | 23823 | 3 |
| mutants | joserfc | held-out | 13226 | 13222 | 4 |

The 12 labels differences are explained in section 5.1, the 3 mutants
differences on the development data in section 5.3 and the 4 on joserfc in
section 5.2.

### 4.2 Final comparison

The final comparison uses the deposited second outputs and the comparison
scripts as deposited. The comparison scripts compare more values than in
the first comparison. Section 5 and the sections below name what was added.

| Part | Subject | Data | Compared | Agree | Differ |
|---|---|---|---|---|---|
| labels | google-auth | held-out | 339 | 339 | 0 |
| labels | oauthlib | held-out | 1165 | 1165 | 0 |
| labels | authlib | held-out | 501 | 501 | 0 |
| labels | joserfc | held-out | 1559 | 1559 | 0 |
| totals | 4 libraries | held-out | 1830 | 1830 | 0 |
| rule 3 | google-auth | held-out | 320 | 320 | 0 |
| rule 3 | oauthlib | held-out | 701 | 701 | 0 |
| rule 3 | authlib | held-out | 380 | 380 | 0 |
| rule 3 | joserfc | held-out | 964 | 964 | 0 |
| mutants | joserfc | held-out | 15488 | 15488 | 0 |
| labels | pyjwt | development, kept first output | 630 | 630 | 0 |
| labels | pyjwt | development, rerun of the first program with rule 3 | 825 | 825 | 0 |
| labels | jwcrypto | development, kept first output | 376 | 364 | 12 |
| labels | jwcrypto | development, rerun of the first program | 382 | 382 | 0 |
| rule 3 | pyjwt | development | 614 | 614 | 0 |
| rule 3 | pyjwt-package | development | 633 | 633 | 0 |
| rule 3 | jwcrypto | development | 473 | 473 | 0 |
| mutants | pyjwt-package | development | 27122 | 27122 | 0 |

On the held-out data no compared value differs. The 12 differences of
jwcrypto against its kept development output stand (section 5.1).

### 4.3 Labels: what is compared

`recompute/compare_labels.py` compares 1 library. It reads the second output,
the first outputs in `generated/labels/<name>/` (`counts.json`,
`agreement.csv`, `outcomes.csv`, `rule-vs-label.csv`,
`rule-vs-label-blocks.csv`, `first-reading.csv`) and `checks.json` beside
`--subject`. With `--shadowed` it reads `generated/mutants/<name>/shadowed.csv`.
With `--summary` it reads the entry of the library in
`generated/labels/summary.json`.

Compared, among others:

- per included block, the agreement category and the agreed label;
- per case, the outcome of the agreed label and program against label for
  rule 2 and rule 3, per tier and per basis;
- the first reading per flag;
- each float of the 2 agreement forms against its own fraction rounded to 9
  places, and rounded to 4 places against `counts.json`; each fraction
  exactly against `summary.json`;
- the shadowed cases against `shadowed.csv`, with the case sets;
- L1, L2, L3 and the supplement "L3, rule 3": units, units that hold,
  status, the set of unit cases and the set of cases that do not hold,
  against `summary.json`.

Against the first comparison, each held-out library has 55 more compared
values: 18 for the float and fraction fields, 9 for the shadowed counts and
28 for the 4 expectations.

### 4.4 Totals: what is compared

`recompute/compare_totals.py` reads `recompute/out/second_totals.json`,
`generated/labels/summary.json`, `generated/trace/compare.json` (the entries
of the 4 held-out libraries, summed and 1 by 1),
`generated/trace/joserfc/compare.csv` for T2, and
`recompute/out/<name>/second_labels.json` of each held-out library. A table
`NAME_MAP` maps every category name of the second output to the name or
names of the first outputs. A name that the table does not map is a
difference.

| Part | From `second_totals.json` and `compare.json` | From `second_labels.json` | Compared | Agree | Differ |
|---|---|---|---|---|---|
| pooled (with L1 to L3 overall) | 224 | 12 | 236 | 236 | 0 |
| google-auth | 206 | 33 | 239 | 239 | 0 |
| oauthlib | 206 | 105 | 311 | 311 | 0 |
| authlib | 206 | 96 | 302 | 302 | 0 |
| joserfc | 213 | 501 | 714 | 714 | 0 |
| T1 to T3 | 28 | 0 | 28 | 28 | 0 |
| total | 1083 | 747 | 1830 | 1830 | 0 |

The column "From `second_totals.json` and `compare.json`" is the first
comparison of the totals. joserfc has 7 more values there: the flags of
class A and its 6 categories.

The values from `second_labels.json` were added later:

- per library and pooled, for L1, L2, L3 and "L3, rule 3", the set of unit
  cases and the set of cases that do not hold, against `unit_rows` and
  `not_holding` of `summary.json`;
- for "L3, rule 3", units, units that hold and status;
- per unit of L1, whether it holds, the rule-2 target and the 2 labels as an
  unordered pair;
- per unit of L2, whether it holds, the rule-2 target and the agreed label;
- per unit of L3 and "L3, rule 3" that does not hold, the target and the
  agreed label;
- the set of flags of the first reading, and per flag its class, category,
  rule-2 target, agreed label, described check and whether the agreed label
  equals the rule-2 target;
- from these, the counts per class against
  `first_reading.agreed_label_equals_target_by_class` of `summary.json`.

### 4.5 Rule 3: what is compared

`recompute/compare_rule3.py` compares the second output and the rule output
with the outputs of `trace/rule3.py` and `trace/analyse3.py`
(`generated/trace/<name>/` and `generated/trace/compare.json`). Its function
`mappings` is the table of compared values. Each number, each set and each
item of a table counts as 1 compared value.

Some compared values take their second side from the group
`toolkit_second_under_rule3`, that is, from `recompute/second.py` of the
toolkit run on the rule-3 targets. These set the second computation of the
toolkit against `trace/analyse3.py`, not an independent computation of
`recompute/second_rule3.py`. The comparison prints 2 numbers for them:

| Subject | Compared values that involve these names | Fields that rest on that computation |
|---|---|---|
| pyjwt | 97 | 55 |
| pyjwt-package | 97 | 55 |
| jwcrypto | 48 | 20 |
| google-auth | 28 | 21 |
| oauthlib | 148 | 90 |
| authlib | 54 | 36 |
| joserfc | 196 | 112 |

The fields are the field `own_test_without_target` of each per-case item
with a rule-3 target, and each of 6 other names as 1 whole value.

Other compared values are, on the second side, outputs of the rule code
`reach/targets.py` (`compute_targets`), tallies of them or constants of the
rule module. The comparison table `RULE_CODE_VALUES` names them, and the
comparison prints their number:

| Subject | Compared values from the rule code | Names |
|---|---|---|
| pyjwt | 200 | 15 |
| pyjwt-package | 200 | 15 |
| jwcrypto | 102 | 15 |
| google-auth | 55 | 15 |
| oauthlib | 174 | 15 |
| authlib | 113 | 15 |
| joserfc | 318 | 15 |

Both sides call the same rule code, so these values are equal by
construction once the 2 widened inputs are equal. They do not check the rule
code. The comparison of the rule-3 part therefore checks the widening and
the analysis of the targets against the records.

Each final count is 8 higher than in the first comparison. The 2 equalities
of the second output about rule 2 were 1 compared value there and are 2
compared values now (section 7). Later, 7 mapping rows were added:

- the count `checks` of the second output against `variant.reachability.checks`
  of `targets.json`, in every run;
- with `--second-targets`, 6 fields of `variant` of the rule output: its 3
  counts of reachable checks against `variant.reachability` of `targets.json`,
  its fields `reach_json_sha256` and `rule_code` against the fields of the
  same name, and the field `rule_version` of the rule output against
  `variant.name`.

### 4.6 Mutants: what is compared

`recompute/compare_mutants.py` holds a table (`MAP`) that names, for each
compared value, its place in the second output and in the first outputs.
Where no first output states a value directly, the first value is derived
from the raw first outputs (`oracles.csv`, `runs.jsonl.xz`, `cases.csv.xz`,
`per-case.csv`, `at-check.csv`, `check-spans.csv`, `mutants.csv`,
`score.json`).

| Comparison | joserfc: compared | development: compared |
|---|---|---|
| per mutant (`oracles.csv`, `runs.jsonl.xz`) | 10356 | 21661 |
| at a check (sets) | 2 | 2 |
| checks: spans, members at the check and in its function, function | 233 | 369 |
| tests: kills, unique kills, deletions killed | 1531 | 1076 |
| `score.json` | 141 | 130 |
| totals of tool mutants and deletions, by operator and by file (`score.json`, `mutants.csv`) | 5 | 5 |
| extra tests: kills and deletions killed (sets) | 8 | 4 |
| per case of a row (`cases.csv.xz`, `per-case.csv`) | 227 | 585 |
| rows of `described-cases.json`: counts, deletions, facts, mutated files | 913 | 145 |
| cells of `described-cases.csv` against `described-cases.json` | 761 | 121 |
| member lists of the 8 groups of each row (sets) | 1159 | 2989 |
| library values | 32 | 35 |
| expectations M1 to M3 under both readings, and the key `expectations` | 118 | 0 |
| cases file: comparison cases and shadowed rows (sets) | 2 | 0 |
| total | 15488 | 27122 |

A table of counts (for example the tool mutants by operator) is compared as a
whole and counts as 1 compared value. The deletions per file are derived from
the rows of `mutants.csv` whose operator is `check_deletion`.

No value differs in either column. The internal checks of the second output
(each list that has a count beside it has that length) number 2216 on
joserfc and 3897 on the development data, with 0 failed.

Also, 2 pairs of first outputs are compared with each other:

- `described-cases.csv` against `described-cases.json`, through the table
  `CSV_COLUMNS` of the 41 columns;
- the key `expectations` of `described-cases.json` against the member
  `tool_mutants_and_deletions` of `expectations_by_reading`.

In a printed difference of these 2 comparisons, the slot "second" holds the
JSON value or the value of the member. The slot "first" holds the CSV cell or
the value of the key.

## 5. Differences and their resolution

### 5.1 Labels: kappa absent from the kept jwcrypto development output

The 12 differences of jwcrypto are the 6 values (units, categories, agreeing
units, observed agreement, expected agreement, kappa) of each of the 2
agreement forms. The kept `work/labels/dev/generated/jwcrypto/counts.json`
has no key `agreement_statistics`, so every first value is null.

Cause: the kept development output comes from an earlier state of the
first program. Its modification time is earlier than that of
`labels/analyse_labels.py`, which now computes the statistics.

Resolution: `labels/analyse_labels.py` was run again on the same inputs with
`--out` outside the deposit. Its `agreement.csv`, `outcomes.csv`,
`rule-vs-label.csv`, `rule-vs-label-blocks.csv` and `first-reading.csv` are
byte-identical to the kept ones. Its `counts.json` differs only by the
added `agreement_statistics`:

- every label text as a category: 42 items, 8 categories, 41 equal,
  observed 41/42, expected 275/588, kappa 299/313;
- names a check or none: 42 items, 2 categories, 42 equal, observed 1,
  expected 5/9, kappa 1.

These equal the second values. Against the rerun, 0 values differ. Against
the kept development output, the 12 differences stand, and neither
program is at fault for them. The deposited held-out outputs in
`generated/labels/` hold the statistics and are compared in full.

### 5.2 Mutants: 2 readings of "mutant" in M1 to M3

The first comparison of joserfc gave 4 differences: whether M3 holds on 3
shadowed rows, and the status of M3. The rows are
`TestJWECompact::test_ciphertext_exceeds_size#0`,
`TestJWECompact::test_header_exceeds_size#0` and
`TestCompact::test_payload_exceeded_size_error#0`.

Cause: the protocol leaves it open. Section 4.3 says that counts of mutants
are of tool mutants and that the deletions are counted apart. It also says
that the deletion of a check is at that check. M1 to M3 can therefore be
decided on tool mutants only, or on tool mutants and deletions.
`recompute/second_mutants.py` decides on tool mutants only and reports the
deletion of the relevant check beside each row. The first program reported
only the reading with deletions.

Resolution: `mutants/at_check.py` now reports both readings in
`described-cases.json`, key `expectations_by_reading`, members `tool_mutants`
and `tool_mutants_and_deletions`. The older key `expectations` holds the
second reading. The comparison takes M1 to M3 of the second output against
`tool_mutants`. It takes the deletion values of the second output against
`tool_mutants_and_deletions`: the difference of the 2 members per row must
equal the deletion flag. All values agree.

Statuses on joserfc, equal on both sides:

| Expectation | Tool mutants only | Tool mutants and deletions |
|---|---|---|
| M1 | not held | not held |
| M2 | not held | not held |
| M3 | not held | held |

Under the first reading, the variants of the 3 size tests kill 0 of the 3
tool mutants at their described check, and the variant of the b64 test
kills 4 of 8. Under the second reading, each of the 4 variants also kills
the deletion of its described check, so the per-row counts are 1, 1, 1 and
5. No deletion of a deciding check is a unique kill of its test, and no
deletion of a described check is detected under O_C by its case. M1 and M2
therefore have the same values under both readings.

### 5.3 Mutants: M1 on the development rows

The first comparison of the development data gave 3 differences, all on M1:
its rows, the tests with a unique kill at the deciding check, and its
status.

Cause: the protocol leaves it open. Section 2 defines M1 to M3 over shadowed
cases, and the 3 development rows have the kind "development row".
`mutants/at_check.py` selects rows whose described check differs from their
deciding check, whatever the kind. `recompute/second_mutants.py` selects
shadowed rows by kind, finds none, and reports M1 to M3 over the rows of
other kinds apart.

Resolution: on rows whose kind is neither a shadowed kind nor "comparison",
M1 to M3 are listed as not compared, because the protocol defines no
expectation over these rows. On joserfc both selections give the same 4
shadowed rows.

### 5.4 Mutants: absolute path in the second output

`recompute/second_mutants.py` resolves its default records path to an
absolute path and records it among its arguments. After the first
comparison, the script was run once more for joserfc with `--records` given
as a relative path. Only that argument string changed in the output. No
file under `recompute/` holds an absolute path.

### 5.5 Totals: pooled agreement

At first neither computation gave the agreement pooled over the 4
libraries: `labels/analyse_labels.py` and `recompute/second_labels.py` work
on 1 library each. `labels/summary.py` (part `together` of
`generated/labels/summary.json`) and `recompute/second_totals.py` now both
compute it, and `recompute/compare_totals.py` compares the 2. Both give, over
271 blocks:

| Form | Categories | Observed agreement | Expected agreement | Kappa |
|---|---|---|---|---|
| every label text as a category | 123 | 257/271 = 0.9483 | 3260/73441 = 0.0444 | 66387/70181 = 0.9459 |
| names a check or none | 2 | 258/271 = 0.952 | 52204/73441 = 0.7108 | 17714/21237 = 0.8341 |
| variant, label qualified by its library | 125 | 257/271 = 0.9483 | 1874/73441 = 0.0255 | 67773/71567 = 0.947 |

The variant is not the result: it splits the text `none` by library. No
label text other than `none` occurs in 2 or more libraries, so the variant
has 2 categories more than the form by label text.

### 5.6 Readings that differ without a difference in these data

- Rows of M3. `mutants/at_check.py` computed M3 for every row with a
  variant, while section 2 defines M3 over the shadowed cases that have a
  variant. The program now limits M3 to shadowed rows, as it does for M1 and
  M2. `mutants/at_check.py` takes a row as shadowed when its described check
  is not its deciding check, whatever the kind of the row.
  `recompute/second_mutants.py` selects shadowed rows by their kind (section
  5.3). The 2 selections give the same rows on joserfc and differ on the
  development rows. In joserfc only the 4 shadowed rows have a variant, so
  the rerun of `mutants/at_check.py` leaves every output file unchanged.
- Extra runs that are not completed. The first program counts a mutant whose
  extra run is a timeout or an error as killed with the extra tests and in
  each replacement. Section 4.3 counts a variant kill only in a completed
  run of the extra tests, and `recompute/second_mutants.py` follows that. No
  mutant in either data set has a completed whole-suite run and an extra run
  that is not completed.
- "With each such test replaced by its variant". The first program scores
  each replacement alone in `score.json`, and the second script scores all
  replacements together. Both forms are compared: the single replacements
  from the per-mutant values of the second output, and the joint value from
  `runs.jsonl.xz` of the first side. Cause: the protocol leaves it open.
- Equal label texts. Section 4.1 calls 2 labels the same after the values of
  a by-parameter label are sorted, while the statistics of
  `labels/analyse_labels.py` compare raw texts. `labels/summary.py` now checks
  that the equal label texts equal the blocks of "same check" and "both
  none", per library and together. The check holds, and no by-parameter
  label occurs in the data.
- T1. The combined verdict of `recompute/second_rule3.py` needs both the
  fall of the count and the bound of 10. For google-auth, oauthlib and
  authlib the count does not fall, so the second script gives "does not
  hold", although google-auth (2) and oauthlib (10) have 10 or fewer. The
  protocol states T1 for joserfc only (60 under rule 2, 16 under rule 3: not
  held on both sides).

### 5.7 Changes to first programs made during the comparison

- `mutants/at_check.py`: both readings of "mutant" (section 5.2) and the
  rows of M3 (section 5.6). For joserfc, the first change added the key
  `expectations_by_reading` to `described-cases.json` and changed no other
  value and no other output file. The second change left every output file
  unchanged.
- `labels/summary.py`: the character | in a table cell of `SUMMARY.md` is
  written as \|, so each row has the cells of its header. The check on equal
  label texts was added. The parts `libraries` and `together` of
  `summary.json` are unchanged by the rerun.

No second script was changed.

## 6. Not compared

### 6.1 Labels

- Marginals of the agreement forms: `summary.json` holds none, and the first
  outputs per library hold none.
- `counts.json` fields `by_basis`, `warnings` and `class_outside` of each
  label file: the second script does not compute the distribution of bases
  or the class check of a label.
- `counts.json` sentinels 1 to 9 and `pinning_rows_compared`: checks of the
  deposited outputs that the second script does not repeat.
- `outcomes.csv` columns of the status on the deletion copy: they enter
  through the outcomes 6, 7 and 8, which are compared per case.
- The text of a raise site that is no check: compared only as "raise site is
  not a check".
- Labels per reading of blocks without a case of the study: the second
  output holds per-reading labels per case only.
- Rows of program against label per block split by the reason for no
  target: compared summed.
- `by_rule_2_target_in_place_of_the_label` and `by_reading` of the shadowed
  part: no first counterpart; compared with the size of their sets.
- Values of the second output with no first counterpart: outcomes per
  reading, class-A rows of the first reading, blocks that keep, change, gain
  or lose a target, the form remarks.
- `COUNTS.md`, `SUMMARY.md`: renderings of compared values.

### 6.2 Totals

- `agreed_label_missing_by_param_unresolved`, `shadowed_or_class_a`,
  `class_a_cases_of_the_first_reading` and the shadowed case ids of
  `second_totals.json`: no counterpart in `summary.json`. The shadowed cases
  are compared per library by `recompute/compare_labels.py`.
- "L3, rule 3" of `summary.json` against `second_totals.json`, which does not
  total it: it is compared per library and pooled from `second_labels.json`.
- The target and the agreed label of the units of L3 and "L3, rule 3" that
  hold: `second_labels.json` holds only their case keys.
- The per-flag fields `deciding_check` and `agreed_label_outcome`, and the
  fields `class_c_flags`, `class_c_flags_without_an_agreed_label_naming_a_check`
  and `readings_compared` of `second_labels.json`: no counterpart in
  `summary.json`.
- The list `checks` of `summary.json` and the lists `checks` and
  `checks_failed` of `second_totals.json`: each holds the checks of its own
  program on its own inputs.
- The statuses of T1, T2 and T3: no first output holds them as data.
  `trace/README.md` states them in prose (T1 not met, T2 met, T3 not met),
  and the second output gives the same statuses.
- The per-library statistics of the variant by library: defined only for
  pooled data.
- The trace counts that the second scripts do not compute (reachability,
  fired checks, block transitions, times, sentinels of `compare.json`):
  compared per library by `recompute/compare_rule3.py` where the second
  output holds them.

### 6.3 Rule 3

- `reach.json` itself, the trace counts of `compare.json` other than the 4
  compared ones, and `seconds`: outputs of the trace step, an input to both
  programs.
- Sentinels T4 and R2 of `compare.json`: they concern `reach/analyse.py` on
  the rule-3 targets and the reproduction of the rule-2 analysis, which the
  second script does not compute.
- The text `variant.reachable` of the rule output, which `recompute/second_rule3.py`
  and `trace/rule3.py` word differently. The other fields of `variant` of the
  rule output are compared with `targets.json` (section 4.5). Of the fields
  of `variant` that only `targets.json` holds, `name` is compared with
  `rule_version` of the rule output, and the 8 counts of `reachability` with
  the reachability counts of the second output. Its sentinel T1 is compared
  with each of the 2 rule-2 equalities.
- The sentinel of `targets.json` that every function of `reach.json` is a
  function of `checks.json`. The second script writes no value for it and
  refuses such a `reach.json` with exit status 2.
- The columns of `fired-functions.csv` that count executions and starts, and
  the full text of `reason` (its category is compared).
- Columns of `analysis/` that do not depend on the targets or read the
  unchanged field `reachable`; `analysis/pinning.csv`,
  `analysis/undetected.csv`; the `lists` and `sentinels` of
  `analysis/summary.json`; the O_T withheld-as-failing count of checks that
  fire and never decide.
- T1: the fall of the count, the combined verdict and
  `stated_values_for_joserfc` (the first outputs hold no T1 verdict in a
  file). T2: the verdict and the outcome-7 set (the first outputs do not
  hold them).
- `SUMMARY.md`, `COMPARE.md` and `SHA256SUMS`: renderings and digests of
  compared values.
- Without `--second-targets`: the per-block table of the rule output, its
  fields `constants`, `counts` and `rule_version`, and the 6 compared fields
  of its `variant` (section 4.5). The comparison prints 1 "not compared" line
  and then these values, 1 per line. Every comparison in section 4 gives
  `--second-targets`.
- Values of the second output with no first counterpart:
  - the outcomes of section 4.1 with the target in place of the label;
  - the outcome-7 set;
  - rule-2 counts per basis and per outcome, and rule-2 block counts;
  - the reachability counts over the subject files only;
  - function lists;
  - E4 and other values of `recompute/second.py` of the toolkit beyond those
    named in section 4.5.

### 6.4 Mutants

- Values of the second output with no first counterpart, each printed as
  "NOT COMPARED" by the comparison:
  - per check: fires in a recorded case of the baseline, fires in a case of
    the study, decides a case, reachable, span, function lines, guard texts;
  - per row: fires in a case of the study, test passes in the baseline
    recorder run, the variant as written;
  - per mutant: the changed lines (an input, checked by the second script),
    the checks in whose function the mutant lies and `killed_by_suite_as`
    (no first column per mutant; the members in the function of each check
    are compared per check);
  - the counts `recorded_executions_of_included_blocks`,
    `mutants_without_a_recorder_value` and `tool_mutants_at_least_1_check`,
    the note of the removal check, the rules of the expectations;
  - the provenance fields `arguments`, `input_sha256`, `input_checks`,
    `readings`, `protocol` and `version`.
- `score.json` provenance and run checks: `reference_study`, `sentinels`,
  `subject`, `files`, `mutmut_version`, `targets`,
  `sha256_before_compression` and `tests_passing_in_both_unmodified_runs`.
- `per-case.csv` and `cases.csv.xz` outside the cases of the rows, and the
  columns of O_V, O_Vfc and O_T per case: the second script computes
  per-case detection only for the cases of the rows, as section 4.3
  "Reported" asks.
- On the development data: M1 to M3 of either side over the development
  rows, because the protocol defines no expectation over these rows. The
  second output gives M1 and M2 over 3 rows and M3 over 2 rows. The
  development first output was written before the key
  `expectations_by_reading` existed, so neither reading is compared there.
  The first output folder holds no cases file, so the comparison cases and
  the shadowed rows of a cases file are not compared.
- `described-cases.csv`: every column is compared, so none is listed.

## 7. Limits

- Both computations read the same records and the same label files.
  Agreement shows that the arithmetic and the definitions match. It does not
  show that the inputs are right.
- Both sides take the kills of a mutant from the same field `lost` of the
  run records: the tests that pass in both unmodified runs and do not pass
  on the mutant copy. The comparison cannot detect an error in that field.
- `recompute/second_rule3.py` imports the rule code `reach/targets.py` of the
  toolkit, so the rule itself is computed by the same code on both sides.
  It also imports `recompute/second.py` of the toolkit. Values that rest on
  either are not independent of the toolkit. Section 4.5 gives both counts
  per subject: the compared values that come from `recompute/second.py`, and
  the compared values that are outputs of the rule code or tallies of them.
- Both sides read the same `reach.json` of the trace step (section 1). The
  comparison cannot detect an error in the trace.
- The second equality about rule 2, `rule_code_with_an_empty_execution_set_equals_rule2`,
  calls the rule code on an unwidened copy of `checks.json`, the same input
  as the first equality. It shows only that the computation is repeatable.
  It does not pass an empty execution set through a widening step, as
  `trace/rule3.py` does for its sentinel T1. The value stays compared.
- No copy of the first version of `recompute/compare_rule3.py` was kept. The
  statement that no earlier comparison was dropped rests on the counts: each
  count rose by 1 when 1 value was split into 2. The later change, which
  added the 7 mapping rows of section 4.5, started from a kept copy, and
  each count rose by 7.
- Definitions that the protocol leaves open, and how each side chose:
  - L1 units: both sides take the class-A flags of joserfc from the first
    reading (`labels/first/joserfc.tsv`). A unit holds when both readings
    give the rule-2 target, compared per reading and not through the agreed
    label.
  - L2 for a flag without a rule-2 target: both sides count it as a unit
    that holds, since a label that names a check differs from no target. No
    such unit occurs in the data.
  - Kappa over the blocks labeled by both readings: both sides use these
    blocks. In the 4 libraries every included block is labeled by both
    readings (271 of 271).
  - M3 over the shadowed rows that have a variant: `mutants/at_check.py`
    takes a row as shadowed when its described check is not its deciding
    check, whatever its kind, and `recompute/second_mutants.py` selects
    shadowed rows by their kind. The 2 selections give the same rows on
    joserfc and differ on the development rows (sections 5.3 and 5.6).
  - The reading of "mutant" in M1 to M3: both readings are reported and
    compared (section 5.2).
  - Pooled kappa: `recompute/second_totals.py` computes it from the marginal
    counts and agreeing blocks of each library, which is exact for Cohen's
    kappa. Equal label texts form 1 category across libraries.
- The development first outputs under `work/` are not deposited, and some
  of them come from earlier states of the first programs (section 5.1).
- Unit tests of the comparison scripts are in `recompute/tests`. They run
  with an interpreter that has pytest installed:

      PYTHONHASHSEED=0 python -I -B -m pytest -q -p no:cacheprovider recompute/tests
