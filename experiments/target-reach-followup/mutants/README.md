# Mutants of mutmut 3.8.1 and deletions of checks, scored like deletions

This folder holds 5 programs that score 2 kinds of mutant per case and per
test, with the rules that `../../target-reach/` applies to a deletion copy:
the mutants of mutmut 3.8.1 ("tool mutants") and the deletion of each check
of the mutated files ("deletions"). The toolkit of `../../target-reach/` is
imported, not copied (`common.py` puts its folder on `sys.path`). The programs
use the standard library only; pytest runs only inside a subject environment,
and mutmut runs only inside an environment that has mutmut 3.8.1
(`mutmut_generate.py`).

| File | Purpose |
|---|---|
| `materialize.py` | creates every mutant of the given files, 1 modified file each; sentinels S1 and S2 |
| `mutmut_generate.py` | runs in the mutmut environment; re-creates the tool mutants with mutmut's own generator |
| `run_mutants.py` | 1 recorder run and 1 whole-suite run per mutant (and, on request, a run of extra tests); resumable |
| `analyse_mutants.py` | the tables and the score; sentinels S1 to S6 |
| `at_check.py` | the span of each check, the mutants at each check, and the report on the cases that describe a check |
| `cases_file.py` | the shadowed cases of a subject, the files to mutate and the cases file of `at_check.py` |
| `common.py` | what the programs share |
| `tests/` | unit tests and an end-to-end test on the synthetic package of the toolkit |

## Commands

Paths are relative to `../` (the folder `target-reach-followup/`). Every
interpreter runs with `-I -B`.

```
python3 -I -B mutants/materialize.py --subject pyjwt-package \
    --files jwt/api_jws.py jwt/api_jwt.py \
    --mutmut-python ../mutation-adequacy-pyjwt/work/venv/bin/python
python3 -I -B mutants/run_mutants.py --subject pyjwt-package --workers 10
python3 -I -B mutants/analyse_mutants.py --subject pyjwt-package
python3 -I -B mutants/at_check.py --subject pyjwt-package
```

The clone and the interpreter of a subject default to those that
`../target-reach/work/<name>/local.json` names (`--clone`, `--python` to
give others). Records go to `work/mutants/<name>/`, outputs to
`generated/mutants/<name>/`. `run_mutants.py` skips every mutant whose runs
exist for the same modified file, so it can be stopped and started again.

Recomputations:

```
python3 -I -B mutants/analyse_mutants.py --subject NAME --without-tests ID [ID ...]   # or @FILE, 1 id per line
python3 -I -B mutants/run_mutants.py --subject NAME --extra-tests DIR
python3 -I -B mutants/analyse_mutants.py --subject NAME --extra-tests DIR [--replace OLD=NEW ...]
python3 -I -B mutants/analyse_mutants.py --subject NAME --targets-file FILE.tsv
python3 -I -B mutants/cases_file.py --subject NAME
python3 -I -B mutants/at_check.py --subject NAME --cases CASES.tsv [--extra-tests DIR]
```

Test ids are the keys of the whole-suite runs (`<run>|<module>.<class>::<name>`,
as `reach.run.junit_outcomes` gives them). `--without-tests` is a pure
recomputation: it removes the given tests from the kills of every completed
whole-suite run. `--extra-tests DIR` copies the files `test_*.py` of DIR into
each copy as `_extra/` and runs them as 1 more pytest call: 2 times on 2
unmodified copies and 1 time on each mutant copy, with the time limit and the
repeat rule of the whole suite; the runs are kept per digest of the files.
`--replace OLD=NEW` scores the whole suite with the test OLD removed and the
extra test NEW (a key, or the end of a key) added. A targets file holds 1 line
per case: the case key (`<test node>|<block>|<index>`, as in `cases.csv`), a
tab, and a check id or nothing (no target); it replaces `targets.json` in the
columns that depend on the target (O_T, and the kills inside the target's
function). A cases file (`at_check.py --cases`) is tab-separated with the
header `case`, `described`, `kind`, `variant`: the case key, the id of the
check that the case is said to describe, free text for the kind of row, and
nothing or the end of the id of 1 extra test (the repaired variant of the
case's test).

`cases_file.py` writes that file for a subject, with `shadowed.csv` and
`mutated-files.txt` (the `--files` of `materialize.py`). It reads
`generated/labels/<name>/outcomes.csv`, `labels/first/<name>.tsv` where it
exists, `cases.csv` and `pinning.csv` of the toolkit's deposited outputs (checked
against their `SHA256SUMS`), `checks.json`, and `repaired/<name>/variants.tsv`
where it exists (tab-separated; header `case`, `described`, `variant`). A case
is shadowed by the labels when its outcome in `outcomes.csv` is "label does not
fire and decides once the deciding check is deleted"; the described check is
then the agreed label. A case is shadowed by the first reading when that
reading puts its flag in class A; the described check is then the target of
the rule, and the program stops unless the deposit shows for the target what
the outcome requires of a label: the target is not the deciding check and not
among the fired checks of the case, and on the copy without the deciding check
the case is observed and the target decides it. A case that both sources show
with the same described check gives 1 row, with 2 described checks 2 rows. The
files to mutate are the files of the described and the deciding check of every
shadowed row. The comparison cases are the cases with a target that is their
deciding check, whose target lies in a file to mutate and that are not
shadowed. The kind of a row is `shadowed (labels)`, `shadowed (first reading)`,
`shadowed (labels and first reading)` or `comparison`.

Unit tests (with an interpreter that has pytest; the end-to-end test also needs
mutmut 3.8.1, by default in `../mutation-adequacy-pyjwt/work/venv`, or in the
environment that `MUTMUT_PYTHON` names):

```
cd mutants/tests && ../../../mutation-adequacy-pyjwt/work/venv/bin/python -I -B -m pytest -q .
```

## How a mutant is made

1. `mutmut_generate.py` parses each file with mutmut's own functions
   (`create_mutations`, `group_by_top_level_node`) and enumerates the mutants
   as mutmut does when it writes a mutated file: the mutations of each
   module-level function and of each method of a module-level class with an
   indented body, numbered from 1 per function in the order of mutmut's
   visitor. Each mutation operator is wrapped so that it tags what it yields
   with its name; the operator label in `mutants.csv` is that name without
   the prefix `operator_`. The mutant name is mutmut's
   (`<module>.x_<function>__mutmut_<n>`, `<module>.xǁ<Class>ǁ<method>__mutmut_<n>`).
   A file of the subject that holds `[tool.mutmut]` options is not read: the
   generator runs in a folder whose `pyproject.toml` names only the package
   as `source_paths`, so mutmut's defaults apply.
2. For each mutant, mutmut's parsed module with this 1 mutation applied is
   rendered by libcst. `materialize.py` takes the lines of the mutated
   function from it and puts them in place of the function's lines in the
   unmodified file; every other byte is the file's own. Where the mutation
   takes k lines fewer than the text it replaces, k padding lines follow the
   new text: empty lines, or, where the last new line ends in a backslash
   that continues the statement, lines that hold 1 backslash each. A mutation
   that takes more lines than the text it replaces fails S1.
3. The ids `M00001`, `M00002`, ... follow the files in sorted order and, in
   each file, mutmut's order.

A deletion is the unmodified file in which every raise statement of 1 check is
replaced by `pass`, with every line number kept. The toolkit's own function
makes it (`reach.delete.delete_check`): it is the copy that the toolkit's step
`deletions` runs for the check. Every check that `checks.json` lists in a
mutated file gets 1, whether or not a test reaches it. The ids `D00001`,
`D00002`, ... follow the files in sorted order and, in each file, the first
raise line of the check and then its id. In `mutants.csv` a deletion has the
operator `check_deletion` and the id of its check in the column `check`.
`materialize.py` stops when a file of the clone is not the file that
`checks.json` was made from (by digest).

A mutant copy is a fresh copy of the subject (as `reach.run.make_copy_check`
makes it: every other subject file is checked against the digest that the
toolkit's `define` recorded) in which the 1 modified file replaces the file.
The recorder run and the whole-suite run use 2 separate fresh copies, as the
toolkit's steps `deletions` and `whole-deletions` do.

The modified file is active as soon as it is imported. mutmut instead
installs trampolines and activates 1 mutant only when a mutated function is
called under its test runner. A mutation of a function that the package
calls while it is imported (for example a constructor called at module level)
therefore stops the import of the package in a mutant copy, and pytest
collects no test.

## Runs and their status

`run_mutants.py` first runs the toolkit's `verify`, `baseline` and
`whole-baseline` with `work/mutants/<name>/` as the work directory: 1 run
without the recorder, 2 recorder runs on 2 unmodified copies, the time limit
of the recorder (`max(60, 10 × the slower baseline run)` seconds), and 2
whole-suite runs on 2 unmodified copies with their time limit. Then, for each
mutant, with `--workers` copies at a time (default 10):

- the recorder run (`reach.run.recorder_run`, with the offline guard of the
  toolkit and `PYTHONHASHSEED=0`) on 1 fresh copy;
- the whole-suite run (`reach.run.whole_run`, all suite runs of the subject
  under 1 time limit) on another fresh copy.

A recorder run that gives no record is repeated 1 time, alone, on a fresh
copy. Its status is `completed` (a record), `timeout` (both runs exceeded the
time limit) or `error` (no record otherwise). A whole-suite run that exceeds
its time limit, or of which a pytest call leaves no result file, is repeated
1 time, alone, on a fresh copy; the repeated run counts. Its status is
`completed`, `timeout` or `error` (no result file).

## Definitions

- A test **kills** a mutant when the test passes in both whole-suite runs on
  unmodified copies and does not pass in the whole-suite run on the mutant
  copy (failed, error, skipped or absent).
- A mutant is **killed by the whole suite** when a test kills it, or when its
  whole-suite run is `timeout` or `error` after the repeat. A `timeout` and an
  `error` give no kill to any test. `score.json` gives the 3 kinds apart, and
  the score with and without the `error` mutants.
- A **unique kill** of a test: the tests that kill the mutant are that 1
  test. A test that runs in several suite runs is 1 test (in `per-test.csv`
  its unique kill is counted in the row of each of its runs). The unique
  kills of a case are those of its own test (the whole-suite key of the
  case's test node).
- Every count of mutants is of **tool mutants**, unless a deletion is named:
  the score, the per-case counts and the first 5 columns of `per-test.csv`
  hold no deletion. The deletions have their own section in `score.json`
  (`check_deletions`) and 2 columns of `per-test.csv`; `runs.jsonl`,
  `cases.csv` and `oracles.csv` hold both kinds.
- The **span of a check**: the lines of each of its raise statements, and the
  lines of the innermost guard of each: the test of the enclosing `if`
  statement (the raise may stand in its body or in its `else` part), or the
  header of the enclosing `except` clause, from `except` to the end of the
  exception type. The guard is found as the toolkit finds it
  (`reach.checks.guard_of`). A raise statement under no `if` and no `except`
  has its own lines only. Conditions further out, and the statements that
  compute what a guard reads, are not part of the span.
- A mutant is **at a check** when at least 1 line that it changes lies in the
  span of the check. A deletion is at its check. A mutant can be at several
  checks. The attribution is by line: where a guard and a statement that is
  not part of it share a line, a change of either counts.
- A mutant is **killed by a variant** when the variant does not pass on the
  mutant copy, in a completed run of the extra tests.
- **Detection of a case** under O_V, O_Vfc, O_C, O_T and O_S follows the
  toolkit's rules for a deletion copy (`reach.analyse`): for an observed case
  an oracle detects when it holds on the unmodified copy and does not hold
  on the mutant copy (`reach.analyse.oracles`); a crashed case is detected
  under every oracle (O_T only for a case with a target); a withheld case is
  not detected and is counted in the withheld-as-failing columns; a missing
  case is not detected; O_S detects when the case's own test passes on the
  unmodified copy and not on the mutant copy. A recorder run that is
  `timeout` is detected under every oracle in every case; a recorder run that
  is `error` gives no value (empty cells), and the mutant is not counted in
  the per-case kills.
- **Detection of a mutant** (`oracles.csv`) is the toolkit's detection of a
  deletion: an oracle detects when it detects in an observed case; a crashed
  case anywhere is a detection under every oracle.
- The **function of a check** is the function that `checks.json` names
  (`function`, in `file`). A mutant lies **inside** that function when every
  changed line of the modified file lies within the lines of the function
  (`reach.checks.functions`, decorators and nested definitions included). The
  function listed for a mutant is the function that mutmut mutated
  (`Class.method` or `function`).

## Outputs (`generated/mutants/<name>/`)

| File | Content |
|---|---|
| `mutants.csv` | id, file, function (and mutmut's form of it), function lines, changed lines, operator, mutmut name, sha256 of the modified file, original and mutated text of the node, and for a deletion the id of its check |
| `materialize.json` | counts per file and operator, padding, the number of deletions, S1 and S2 |
| `runs.jsonl.xz` | per mutant: the status and number of the recorder runs and whole-suite runs, and the tests that kill it (and the runs of extra tests) |
| `cases.csv.xz` | per mutant and case: the status of the case and its detection under each oracle, and the withheld-as-failing values |
| `oracles.csv` | per mutant: the detection over all cases, as the toolkit decides it for a deletion, and the whole-suite status |
| `per-case.csv` | per case: target and deciding check with their functions; per oracle the detecting tool mutants inside the target's function, inside the deciding check's function and in all mutated files; the unique kills of the case's own test, with their functions |
| `per-test.csv` | per test with at least 1 kill: kills, unique kills, the functions of the unique kills, the number of cases of the test, the deletions it kills, and the checks whose deletion it alone kills |
| `score.json` | counts, by file and operator, the mutant-level oracle counts, the deletions, the recomputations asked for, the comparison with the reference study (PyJWT) and with the toolkit's deletions, and the sentinels |
| `check-spans.csv` | per check of the mutated files: the lines of its raise statements, the kind and the lines of its guards, the number of tool mutants at it, and the id of its deletion |
| `at-check.csv` | per mutant and check at which it is: the operator and the part of the span that it changes (`raise`, `guard`, `raise and guard`) |
| `described-cases.csv`, `described-cases.json` | with `--cases`: per row, the tool mutants at the described check, at the deciding check and at the described check only, with the numbers of section "Definitions", the same for the 2 deletions, and what the rows give for the expectations M1 to M3 of `../PROTOCOL.md` |
| `shadowed.csv`, `mutated-files.txt`, `cases.tsv` | written by `cases_file.py`: the shadowed rows with the files of their 2 checks, their source and their variant; the files to mutate; the cases file |
| `SHA256SUMS` | digests of every file of the folder |

`runs.jsonl` and `cases.csv` are kept compressed (xz); `score.json` gives the
digest of each text before compression (`sha256_before_compression`). All
files are sorted and hold no time; the run times are in
`work/mutants/<name>/runs/` only.

## Sentinels

Each program writes its outputs, then exits with status 1 when a sentinel does
not hold.

- **S1** Each modified file differs from the unmodified file, only inside the
  lines of 1 function; it has the same number of lines and compiles; the runs
  used the modified file of `mutants.csv`. A deletion changes the lines of
  the raise statements of its check and no other line.
- **S2** The mutated function of each modified file of a tool mutant has the
  syntax tree of the function that mutmut writes for this mutant in its own
  mutated file (with the function names set equal); and each file has as many
  tool mutants as mutmut's own file generator (`mutate_file_contents`) yields,
  with the same names in the same order.
- **S3** The unmodified copies give the deposited baseline: the same cases
  with the same deciding check as `../target-reach/generated/<name>/cases.csv`,
  the same tests passing in both whole-suite runs as the deposited whole-suite
  baseline (`records/whole/base.json` in `records.tar.xz`), and 2 identical
  recorder records, message texts aside.
- **S4** Every mutant has its recorder run and its whole-suite run (and the
  run of the extra tests, when given), each `completed`, or a stated
  `timeout` or `error` after 1 repeat.
- **S5** (PyJWT) The tool mutants are those of the reference study
  (`../mutation-adequacy-pyjwt/generated/mutants.csv`), by mutmut name. The
  agreement of the whole-suite status with the study's mutmut status
  (`tool_class`) is reported in `score.json`, with each difference; the
  agreement itself is not a sentinel.
- **S6** (where `../target-reach/generated/<name>/deletions.csv` has rows)
  The deletion of each check that the toolkit's `deletions.csv` lists gives
  here what the toolkit recorded for its own deletion copy: the same
  detection under O_V, O_Vfc, O_C, O_T and O_S and by the suite of the
  recorder run, the same withheld-as-failing columns, the same whole-suite
  status and the same number of tests not passing. With `--targets-file` the
  O_T columns are left out. `at_check.py` exits with status 1 when a deletion
  is not at its check.

## Development run on PyJWT

`generated/mutants/pyjwt-package/` holds the run on the 2 modules of the
reference study (`jwt/api_jws.py`, `jwt/api_jwt.py`) of PyJWT 2.15.1: 1094
tool mutants and 46 deletions. All 6 sentinels hold: the whole-suite status
agrees with the mutmut status of the reference study for 1094 of 1094 tool
mutants, and 41 of the 46 deletions are of checks that the toolkit's
`deletions.csv` lists, with no difference in any of the 12 compared columns.
