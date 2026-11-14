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

## Contents

| Path | What it holds |
|---|---|
| `PROTOCOL.md` | Questions, expectations, definitions, what had been done before the commit, the order of execution, limits |
| `labels/` | The instruction of a reading, the programs for packs, parts, validation and analysis, the transcribed first readings of the flags (`labels/README.md`) |
| `trace/` | The trace plugin, rule 3 and its analysis (`trace/README.md`) |
| `mutants/` | The programs that make, run and score the mutants and the deletions (`mutants/README.md`) |
| `repaired/joserfc/` | Repaired variants of 3 tests of joserfc and their verification |
| `recount/` | The recounts (`recount/README.md`) |
| `versions/` | The nested-header test of PyJWT on CPython 3.12, 3.13 and 3.14 (`versions/README.md`) |
| `generated/` | Outputs: `recount/`, and the development runs in `trace/` and `mutants/pyjwt-package/` |

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

## Tests of the programs

Each folder has unit tests on synthetic inputs; its README gives the command.
They need an interpreter with pytest; the end-to-end test of `mutants/` also
needs mutmut 3.8.1.
