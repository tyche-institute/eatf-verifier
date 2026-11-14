# Follow-up analyses on the replication of target reach

The experiment in `../target-reach/` assigned, by a fixed rule, the check that
each negative-test block of 4 held-out Python verification libraries
describes, and compared it with the check that rejects the input. This folder
holds 4 follow-up analyses of that replication. They were chosen after its
results had been read, and they are reported as follow-up analyses.

1. **Labels.** The target of every included block of the 4 libraries is
   assigned by reading the test, 2 times, from 1 written instruction and
   without sight of any run (`labels/`).
2. **Rule 3.** The rule of `../target-reach/` with 1 input widened: a check
   is also a candidate when its function runs under an entry point in the
   library's own suite (`trace/`).
3. **Mutants.** The mutants of mutmut 3.8.1 and the deletion of each check,
   in the files of the tests that an earlier check stops, scored per case and
   per test (`mutants/`, `repaired/`).
4. **Recounts and interpreter versions.** Counts recomputed from the deposited
   outputs of `../target-reach/` (`recount/`), and tests run on later versions
   of CPython (`versions/`).

## Status

The commit that adds this folder fixes `PROTOCOL.md` and
`labels/INSTRUCTION.md`. Right after it, a text that names the commit is
time-stamped by 2 authorities, and a later commit adds the tokens in
`timestamps/`. Section 5 of the protocol says what had been done before the
commit on each subject. On the 4 held-out libraries, at the commit: no
reading pack had been built and no label made by the instruction; no suite
had been traced and rule 3 had not been computed; no mutant of the tool had
been made. The programs had been written and tried on PyJWT 2.15.1 and
jwcrypto 1.6.1, the 2 development subjects of `../target-reach/`.

The steps of section 6 of the protocol have been carried out. A second
commit holds the labels of the 2 readings as they were returned, and a third
commit holds the results, the readings of the flags, the second computation
and `DEVIATIONS.md`. Each of the 3 commits is time-stamped in the same way,
and `timestamps/README.md` names them with their times.

## Results

The protocol's expectations are reported as held or not held, and no
definition was changed after the protocol commit. `DEVIATIONS.md` lists the
defects of programs that were corrected, the runs that were repeated, and
what was added to the outputs that the protocol lists.

| Step | Result | Stated in |
|---|---|---|
| Labels | The 2 readings give the same label for 257 of the 271 included blocks (Cohen's kappa 0.946 with every label text as a category). The agreed label names a check for 310 of the 402 cases, and that check decides 302 of them. The other 8 are in joserfc, and 4 of them are shadowed. | `generated/labels/SUMMARY.md`, `readings/joserfc/LABEL-OUTCOMES.md` |
| Rule 3 | Over the 4 libraries, the cases with a target go from 229 under rule 2 to 235, the cases that their target decides from 145 to 195, and the flags from 84 to 40. | `trace/README.md`, `generated/trace/COMPARE.md`, `readings/joserfc/FLAGS-RULE3.md` |
| Mutants | Only joserfc has shadowed cases. Its suite kills 376 of 516 tool mutants, 374 without the 4 tests that hold a shadowed case, and 376 with each of the 4 replaced by its repaired variant. The suite detects the deletion of 21 of 29 checks, and of 23 with the variants. | `mutants/README.md` ("Run on joserfc"), `generated/mutants/joserfc/` |
| Recounts | Counts recomputed from the deposited outputs of `../target-reach/`. | `generated/recount/RECOUNT.md` |
| Interpreter versions | The nested-header test of PyJWT on CPython 3.12 to 3.14, and the 4 tests of joserfc with their variants on CPython 3.13. | `versions/README.md` |
| Second computation | On the 4 libraries, no compared value differs between the second scripts and the first programs. The report states what the 2 sides share. | `recompute/NOTES.md` |

Expectations of section 2 of the protocol:

| Expectation | Outcome |
|---|---|
| L1 | held: 3 of 3 units |
| L2 | held: 52 of 52 units |
| L3 | not held: 135 of 138 units |
| T1 | not held: 16 flags of joserfc under rule 3, against 10 or fewer |
| T2 | held |
| T3 | not held: the target decides 90 of 106 cases of joserfc (84.9%), against at least 85% |
| M1 | not held |
| M2 | not held |
| M3 | not held when only tool mutants count; held when the deletion of a check counts as a mutant at that check (`recompute/NOTES.md`, section 5.2) |

## Contents

| Path | What it holds |
|---|---|
| `PROTOCOL.md` | Questions, expectations, definitions, what had been done before the commit, the order of execution, limits |
| `labels/` | The instruction of a reading, the programs for packs, parts, validation and analysis, the transcribed first readings of the flags (`labels/README.md`) |
| `trace/` | The trace plugin, rule 3 and its analysis (`trace/README.md`) |
| `mutants/` | The programs that make, run and score the mutants and the deletions (`mutants/README.md`) |
| `labels/readings/<name>/` | The 2 readings of each held-out library (`A.tsv`, `B.tsv`) and the parts |
| `repaired/joserfc/` | Repaired variants of 4 tests of joserfc and their verification (`repaired/joserfc/README.md`) |
| `recount/` | The recounts (`recount/README.md`) |
| `versions/` | The nested-header test of PyJWT on CPython 3.12, 3.13 and 3.14, and the 4 tests of joserfc with their variants on CPython 3.13 (`versions/README.md`) |
| `readings/joserfc/` | The reading of the 16 flags of joserfc under rule 3 (`FLAGS-RULE3.md`) and of the 8 cases that their agreed label does not decide (`LABEL-OUTCOMES.md`) |
| `recompute/` | The second computation: 4 second scripts, 4 comparison scripts, their outputs in `recompute/out/`, unit tests, and the report `recompute/NOTES.md` |
| `generated/labels/` | Per held-out library: agreement, outcomes of the cases, program against label. `SUMMARY.md` and `summary.json` hold the 4 libraries together and L1 to L3. |
| `generated/trace/` | Per subject: functions started under an entry point, targets of rule 3, the analysis. `COMPARE.md` and `compare.json` compare rule 2 and rule 3. |
| `generated/mutants/` | Per held-out library: the shadowed cases. For joserfc also the mutants, runs, kills per case and per test, mutants at each check, scores. `pyjwt-package/` holds the development run. |
| `generated/recount/` | The recounts |
| `generated/SHA256SUMS`, `recompute/out/SHA256SUMS` | The SHA-256 digest of every file under `generated/` and of every second output |
| `timestamps/` | The tokens of the 3 commits and how to verify them (`timestamps/README.md`) |
| `DEVIATIONS.md` | Deviations from the protocol |

`work/` (copies, environments, logs, raw records, reading packs) is not
deposited.

## Requirements

Python 3.12 or later. The programs use the standard library and import the
toolkit of `../target-reach/` (`reach/`, `guard/`), which they do not change.
pytest runs only inside the environment of a subject, as
`../target-reach/subjects/<name>/` defines it; mutmut 3.8.1 runs only inside
an environment that has it. Every interpreter is started with `-I -B`.

## Order of the steps

From this folder, for each held-out library `<name>` (section 6 of the
protocol gives the order and what is committed between the steps):

    # labels: pack, parts, 2 readings, form check
    python3 -I -B labels/prepare.py --subject ../target-reach/subjects/<name>/subject.json \
        --clone <clone> --instruction labels/INSTRUCTION.md --out <pack>
    python3 -I -B labels/parts.py split --pack <pack> --max-blocks 50 --out <parts.tsv>
    python3 -I -B labels/parts.py join --pack <pack> --parts <parts.tsv> --labels <part files> --out <labels.tsv>
    python3 -I -B labels/check_labels.py --pack <pack> --labels <labels.tsv>

    # rule 3
    export PYTHONHASHSEED=0
    python3 -I -B trace/trace_run.py --subject ../target-reach/subjects/<name>/subject.json --repeats 3
    python3 -I -B trace/rule3.py --subject ../target-reach/subjects/<name>/subject.json
    python3 -I -B trace/analyse3.py --subjects <names>

    # labels against the records and the 2 rules
    python3 -I -B labels/analyse_labels.py --subject ../target-reach/subjects/<name>/subject.json \
        --labels labels/readings/<name>/A.tsv labels/readings/<name>/B.tsv \
        --targets3 generated/trace/<name>/targets.json

    # shadowed cases, mutants, deletions
    python3 -I -B mutants/cases_file.py --subject <name>
    python3 -I -B mutants/materialize.py --subject <name> --files <lines of mutated-files.txt> \
        --mutmut-python <python of an environment with mutmut 3.8.1>
    python3 -I -B mutants/run_mutants.py --subject <name> --extra-tests repaired/<name>/tests_repaired
    python3 -I -B mutants/analyse_mutants.py --subject <name> --extra-tests repaired/<name>/tests_repaired
    python3 -I -B mutants/at_check.py --subject <name> --cases generated/mutants/<name>/cases.tsv \
        --extra-tests repaired/<name>/tests_repaired

    # recounts
    python3 -I -B recount/recount.py

After the 4 libraries, `labels/summary.py` writes `generated/labels/SUMMARY.md`
and `summary.json`:

    python3 -I -B labels/summary.py

`recompute/NOTES.md`, section 3, gives the commands of the second computation
and of its comparisons.

## Tests of the programs

Each folder has unit tests on synthetic inputs; its README gives the command.
They need an interpreter with pytest; the end-to-end test of `mutants/` also
needs mutmut 3.8.1.
