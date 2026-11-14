# Target labels by reading

Tooling for target labels assigned by reading: a reading pack per subject,
a validator for labels files, and the analysis that sets the labels beside
the runs of the toolkit (`../../target-reach`) and beside the rule. The
tooling uses the Python standard library only and reads the deposited
files of `../../target-reach` and `../../mutation-adequacy-pyjwt` without
changing them. All paths below are relative to the folder
`target-reach-followup`.

## Files

| file | purpose |
|---|---|
| `labels/labelslib.py` | shared code: TSV input and output, the label and basis grammar, validation of a labels file |
| `labels/prepare.py` | builds a reading pack for 1 subject |
| `labels/check_labels.py` | checks a pack against its manifest and validates a labels file against it |
| `labels/parts.py` | splits the blocks of a pack into parts by test file, and joins the labels files of the parts |
| `labels/analyse_labels.py` | compares 1 or 2 labels files with the runs and with the rule |
| `labels/convert_reference.py` | converts the labels of the PyJWT reference study into a labels file |
| `labels/INSTRUCTION.md` | the instruction of a reading; it goes into every pack |
| `labels/readings/<name>/` | the labels files of the readings (`A.tsv`, `B.tsv`) and the parts (`parts.tsv`) |
| `labels/first/` | transcription of the first reading of the flags, and `check_first.py` (see `first/README.md`) |
| `labels/tests/` | unit tests on synthetic inputs |

## Reading pack

    python3 -I -B labels/prepare.py --subject ../target-reach/subjects/<name>/subject.json \
        --clone <clone of the subject> --instruction <instruction file> --out <empty folder>

The pack holds `src/` (the paths that subject.json copies, read from the
object store of the clone at the commit of subject.json; the working tree
is not read), `checks.tsv` (every check: id, file, function, class, lines,
message template, guards; no reachable field), `classes.tsv` (declared bases
of the classes of the subject), `blocks.tsv` (every included block: key,
file, lines, test, expected classes, assertions as text), `labels.tsv` (an
empty template), the instruction file and `MANIFEST.txt` (SHA-256 of every
other file). Targets, generated outputs, readings and records are not in a
pack. `prepare.py` refuses an output folder inside the 3 experiment folders
(except their `work/` folders) or one that is not empty, a file whose name
is on its forbidden list, and a file other than the instruction whose bytes
equal a file of the experiment folders outside `work/`.

## Labels file

A TSV file (csv excel-tab dialect) with the columns `block`, `label`,
`basis`, `quote`, `note` and 1 row per included block of the pack.

- `label`: a check id of `checks.tsv`; `none` when no single check is
  described; or `by-param <name>: <value>=<id or none>; ...` (at least 2
  values) when the described check depends on a parameter of the test.
- `basis`: `none`, or `class`, `assert` and `name` joined by `+` (the class
  expected by the block; an assertion on message or attributes; the test
  name). Label `none` goes with basis `none` and a reason in `note`; a label
  that names a check goes with a basis other than `none`.
- `quote`: the text of the test that supports the basis; a basis without a
  quote is a warning, not an error.

A label whose check raises a class that is neither an expected class of the
block nor a subclass of one is valid and listed apart. Subclasses are
resolved through `classes.tsv`, and for built-in classes through the method
resolution order of the interpreter.

    python3 -I -B labels/check_labels.py --pack <pack> --labels <labels.tsv> [--json <report.json>]

The exit status is 1 when the pack does not match its manifest or the
labels file has an error.

## Parts

A pack with many blocks can be labeled in parts. A part is a set of test
files; every block of a test file is in the same part.

    python3 -I -B labels/parts.py split --pack <pack> --max-blocks 50 --out <parts.tsv>
    python3 -I -B labels/parts.py join --pack <pack> --parts <parts.tsv> \
        --labels <part 1.tsv> <part 2.tsv> ... --out <labels.tsv>

`split` takes k, the smallest number of parts with at most `--max-blocks`
blocks each on average (the number of blocks divided by the limit, rounded
up), sorts the test files by path and closes part i after the first file
with which the running number of blocks reaches i/k of all blocks; parts
without a file are left out and the parts are numbered from 1. A test file
with more blocks than the limit makes a part larger than the limit.
`parts.tsv` has the columns `file`, `part` and `blocks`. `join` takes 1
labels file per part, in the order of the parts, reads from each only the
rows of the blocks of its part, and writes the rows in the order of the
pack's `labels.tsv`. It fails when a block of a part has no row or 2 rows,
when a header is wrong or when the number of files is not the number of
parts; a row of another part is not read and is listed when it carries a
label.

## Analysis

    python3 -I -B labels/analyse_labels.py --subject ../target-reach/subjects/<name>/subject.json \
        --labels <reading 1.tsv> [<reading 2.tsv>] [--targets3 <targets.json of rule 3>]

Defaults: `--generated ../target-reach/generated/<name>`, `--first
labels/first/<name>.tsv`, `--toolkit ../target-reach`, `--out
generated/labels/<name>`. The analysis imports the definitions of case,
firing and raise site from the toolkit (`reach.study`, `reach.analyse`)
and reads the records from `records.tar.xz` without unpacking it.

Agreed label: with 2 files, the label of a block on which both agree
(the same check, or both `none`); with 1 file, its label. A by-param label
resolves to the value whose name is 1 of the `-`-separated parts of the
bracket id of the test node; a case with no or several matching values
fails sentinel 5.

Outputs:

- `agreement.csv`, per included block: same check; both none; 1 check and 1
  none; 2 different checks (with 1 file: single). With 2 files, `counts.json`
  and `COUNTS.md` also give Cohen's kappa over the blocks, computed 2 ways:
  with every label text as a category, and with the 2 categories "names a
  check" and "none". The values of a by-param label are sorted before the
  texts are compared. Kappa has no value when 1 category holds every label of
  both files.
- `outcomes.csv`, per case of the study whose agreed label names a check:
  decided by its label; label fires and another check decides; label fires
  and no check decides; label does not fire and decides once the deciding
  check is deleted; label does not fire and does not decide then either;
  label does not fire, case not observed on the copy without the deciding
  check; label does not fire and no check decides; deciding check not
  deleted or record missing; fired checks not recorded. "Fires" means: the
  label is among the fired checks of the case or is its raise site. The
  copy without the deciding check is the deletion run of the toolkit for
  that check.
- `rule-vs-label.csv`, per case and rule, with the tier of the rule
  (assertion, name, none): target equals label; target differs from label;
  target and label none; label none; no target; no agreed label. Rule 2 is
  the target of `cases.csv`; rule 3 the target of `--targets3`.
- `rule-vs-label-blocks.csv`, per included block, in the cells of
  `../target-reach/VALIDATION.md`: both, equal; both, different; rule only;
  label only; neither; no agreed label.
- `first-reading.csv`, per flag, when `first/<name>.tsv` exists.
- `counts.json` and `COUNTS.md`: every count and the 9 sentinels.

Sentinels (every output is written first; the exit status is 1 when 1
fails):

1. the deposited files of the generated folder match `SHA256SUMS`;
2. `cases.csv` holds exactly the cases of the study of the first baseline
   record, with the same raise site and fired checks;
3. the target of each row of `cases.csv` is the target of its block in
   `targets.json`;
4. every labels file is valid;
5. every by-param label resolves to exactly 1 value in every case of its
   block;
6. the agreement categories, the outcomes and the rule categories add up,
   for each rule and in each tier;
7. every case decided by its label has its label among its fired checks;
8. the deletion runs read are those of `deletions.csv`, and the status and
   raise site read from the records equal `pinning.csv`;
9. the transcription of the first reading matches `flags.csv` (not
   applicable without a transcription).

## Development runs

PyJWT, with the labels of the reference study (79 blocks, 1 labels file):

    python3 -I -B labels/convert_reference.py --out work/labels/dev/pyjwt-reference.tsv
    python3 -I -B labels/analyse_labels.py --subject ../target-reach/subjects/pyjwt/subject.json \
        --labels work/labels/dev/pyjwt-reference.tsv --out work/labels/dev/generated/pyjwt

79 blocks: 68 with a check, 1 by parameter, 10 none; all 9 sentinels hold
(sentinel 9 not applicable). 91 cases, 81 of them with an agreed label that
names a check: 80 decided by their label and 1 where the label does not fire
and does not decide once the deciding check is deleted
(`test_decode_deeply_nested_header_throws_decode_error`, label `_load#3`,
deciding check `_load#4`). Rule 2 per block: both, equal 47; both, different
0; rule only 1; label only 22; neither 9; per basis of the rule the same
counts as in `../target-reach/VALIDATION.md`.

jwcrypto, a pack and synthetic labels files (not readings): the pack holds
12 source files, 146 checks, 109 classes and 42 included blocks, and its
manifest checks; `check_labels.py` rejects a malformed file (exit status 1)
and accepts the 2 complete synthetic files (exit status 0); the analysis of
the 2 files with `targets.json` as rule 3 holds all sentinels.

## Tests

With an interpreter that has pytest (the tests run the toolkit on its
synthetic package `../target-reach/tests/fixture/toy` in a temporary
folder):

    PYTHONHASHSEED=0 <python with pytest> -B -m pytest -q -p no:cacheprovider labels/tests
