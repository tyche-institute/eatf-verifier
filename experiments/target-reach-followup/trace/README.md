# Reachability from execution, and target rule 3

The target rule of the toolkit in `../target-reach/` (`reach/targets.py`,
`reach-target-rule/2`) takes as candidates the checks that are *reachable*:
`reach/checks.py` marks a check reachable when its function lies in the
closure by name from the functions named like an entry point. That closure
does not follow a call through `getattr` with a computed name, a function
imported under another name, or a call of a class to its `__init__`.

This folder keeps the code of the rule unchanged and widens only its input.
Under `reach-target-rule/3` a check is reachable when it is reachable by name
**or** its function started, in a run of the whole suite on the unmodified
copy, while a function named like an entry point of the subject was on the
call stack of the same thread. The rule uses the runs of the whole suite and
never the outcome of the block that is being assigned a target.

Paths below are relative to the experiment directory
(`target-reach-followup/`); `../target-reach/` is the toolkit, which is only
read.

## Files

| File | What it does |
|---|---|
| `trace/plugin.py` | pytest plugin: for every function of the subject that starts, the entry-point names on the stack of the same thread |
| `trace/trace_run.py` | runs every suite run of `subject.json` on fresh unmodified copies with the plugin and the offline module; writes `generated/trace/<name>/reach.json` |
| `trace/rule3.py` | widens `reachable`, calls `compute_targets` of the toolkit unchanged; writes `targets.json` and `checks-reachability.csv` |
| `trace/analyse3.py` | runs `reach/analyse.py` of the toolkit, unchanged, on the deposited records under both rules; writes `analysis/`, `compare.csv`, `fired-functions.csv`, `COMPARE.md` per subject, and `generated/trace/COMPARE.md` and `compare.json` |
| `trace/tests/` | unit and end-to-end tests on the synthetic package `tests/fixture/toytrace` |

## Definitions

**Subject code.** The files of the subject are the subject files and the
observed files of `checks.json` (its field `sha256`), the same files whose
functions `reach/checks.py` puts in the closure by name. A code object
belongs to the subject when its file is 1 of them. Test files inside the
package directory (as in `jwcrypto`) are not subject files and do not count.

**Function code.** A code object compiled from a function body (`def`,
`async def`, lambda, generator expression): one with the flags `CO_OPTIMIZED`
and `CO_NEWLOCALS`. A module body and a class body are not function codes.

**Entry-point frame.** A frame whose code is a function code of the subject
and whose name (`co_name`) is an entry-point name of `subject.json`. A method
counts by its bare name, as in the closure by name. A call of a class named
like an entry point (`JWT(...)` in `jwcrypto`) runs `__init__` and is no
entry-point frame; the body of that class, run at import, is no function
code.

**Start.** The `PY_START` event of `sys.monitoring`: the first instruction of
a call, or the first `next()` or `send()` of a generator or coroutine.
Resuming a generator or coroutine after `yield` or `await` is not a start.

**Started under an entry point.** At the start of a function code of the
subject, the plugin walks the frame chain of the current thread from the new
frame outward (`f_back`) and takes the names of the entry-point frames on it.
The new frame is on the chain, so a function named like an entry point runs
under its own name. A function *started under an entry point* when at least
1 of its starts had a non-empty set. What follows from walking the real frame
chain at each start:

- **Recursion**: every recursive call is a start and sees the same chain.
- **Exceptions**: no shadow stack is kept, so a frame that an exception
  unwinds leaves no trace; a later call sees only the frames that exist.
- **Generators**: the chain at the first `next()` counts, not the chain where
  the generator object was created. A generator created inside an entry point
  and first advanced after the entry point returned starts under no entry
  point. A check that a generator raises after a `yield`, when the generator
  was first advanced under an entry point and resumed under none (or under
  another one), is credited to the names of the first advance only.
- **Coroutines**: an awaited coroutine is chained to the frame that awaits it.
  `asyncio.run` and an event loop run in the calling thread, so a coroutine
  run by them from inside an entry point sees the entry point on its chain. A
  task run by an event loop in another thread does not.
- **Threads**: only the thread of the start counts. A function run in a thread
  that an entry point started has the thread's own chain (bootstrap frames and
  the thread target) and starts under no entry point, unless that chain holds
  an entry-point frame itself.

**Keys.** A started code is keyed by its file, `co_firstlineno` and `co_name`.
`trace_run.py` maps the key to the function of `checks.json` with
`functions()` of `reach/checks.py` on the copy, whose files are the files of
`checks.json` byte for byte (`make_copy` checks the digests): a definition
matches when its name is `co_name` and its first line is `co_firstlineno`,
which is the line of the first decorator of a decorated definition and the
`def` line otherwise. So the keys are the "file" and "function" of
`checks.json` exactly: a method is `Class.method`, a function nested in a
function is `outer.inner` (Python's `outer.<locals>.inner`), and the k-th
definition of a name in 1 scope, k >= 2, is `<name>~k` (a property setter,
for example).

**Lambdas, generator expressions and comprehensions.** A lambda and a
generator expression have their own code object; they are recorded under
`unmapped` with their qualified name and entry points and are not mapped to
the enclosing function. They hold no raise statement (a raise is a
statement), so no check lies in them, and the enclosing function has already
started when they run; crediting their starts to it could add names under
which the enclosing function never ran. List, set and dictionary
comprehensions have no code object of their own in CPython 3.12 (PEP 709):
their instructions are part of the enclosing function. A definition that
`checks.json` does not list (in a loop, an exception handler, an `async
with` or a `match` statement, as `reach/checks.py` reads them) is recorded
under `unmapped` too, with that reason; `trace_run.py` checks the reason
against the source of every unmapped code (sentinel T-map).

**Reachable under rule 3.** `rule3.py` replaces, in a copy of `checks.json`,
the field `reachable` of each check by `reachable by name or (file, function)
started under an entry point`, and calls `compute_targets` of
`reach/targets.py` on that copy and the unchanged `blocks.json`. Nothing else
of `checks.json` changes.

## How to run

The toolkit and this part need the standard library of Python 3.12 or later;
the subject runs use the interpreter and the clone named in
`../target-reach/work/<name>/local.json` (or `--python` and `--clone`).

    export PYTHONHASHSEED=0
    python3 -I -B trace/trace_run.py --subject ../target-reach/subjects/<name>/subject.json --repeats 3
    python3 -I -B trace/rule3.py --subject ../target-reach/subjects/<name>/subject.json
    python3 -I -B trace/analyse3.py --subjects pyjwt pyjwt-package jwcrypto

`trace_run.py` runs, `--repeats` times, the suite without the plugin and with
it, each on its own fresh copy in `work/trace/<name>/copies/`, alternating; the
first traced run gives `reach.json`. The pytest call of each suite run is that
of the step `whole-baseline` of `reach/run.py` (`pytest_args`, the arguments
of the suite run, `-p reach_offline`, `--rootdir=.`, `--tb=no`,
`--continue-on-collection-errors`, `--junitxml`, the paths), with the same
environment variables (`PATH`, `HOME`, `LANG` and `LC_ALL` `C.UTF-8`,
`PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`) and `-p reach_trace` added.
The plugin is copied as `reach_trace.py` into `work/trace/<name>/plugin/`, a
folder with no other module, and its digest is written in `reach.json`.
`analyse3.py` unpacks `../target-reach/generated/<name>/records.tar.xz` into
`work/trace/<name>/deposited/` and builds the derived definition folders
`work/trace/<name>/defs-rule2/` and `defs-rule3/`.

The tests:

    PYTHONHASHSEED=0 <env with pytest>/bin/python -I -B -m pytest -q -p no:cacheprovider trace/tests

## Outputs

`generated/trace/<name>/`:

| File | What it holds |
|---|---|
| `reach.json` | per function of `checks.json` that started: the entry points (sorted), the starts, the starts under no entry point, the starts in another thread, up to 5 tests of starts under no entry point and the first test per entry point; the functions that started only under no entry point; the unmapped codes; the test outcomes and the deposited whole-baseline counts; the interpreter, the installed packages, the `sys.monitoring` tool id, the time of each run; the sentinels |
| `targets.json` | the output of `compute_targets`, as `reach/run.py` writes `targets.json`, with `rule_version` `reach-target-rule/3` and a field `variant` (rule code `reach-target-rule/2`, the reachability counts, the digest of `reach.json`, sentinel T1) |
| `checks-reachability.csv` | check, file, function, role, reachable by name, by execution, under rule 3, entry points |
| `analysis/` | the outputs of `reach/analyse.py` for the rule-3 targets, from the deposited records |
| `compare.csv` | per case of the study: target, basis, tier and whether the target decides the case, under rule 2 and rule 3; the baseline raise site; the transition |
| `fired-functions.csv` | per check that fires in a case of an included block in either deposited baseline record: where its function started in the trace, and the reason when not under an entry point |
| `COMPARE.md` | the counts of the subject |

`generated/trace/COMPARE.md` and `compare.json` put the subjects named to
`analyse3.py` side by side.

## Sentinels

Every program writes its outputs and then exits with an error when 1 of its
sentinels does not hold.

| Sentinel | Program | Holds when |
|---|---|---|
| T1 | `rule3.py` | with an empty execution set, the same code gives `targets.json` of the toolkit byte for byte after the same serialization |
| T2 | `analyse3.py` | every check that fires in a case of an included block in `base-1.json` or `base-2.json` lies in a function that started under an entry point, or is listed in `fired-functions.csv` with the reason; a fired check whose function did not start at all in the traced run does not hold |
| T3 | `trace_run.py` | the tests that pass in the traced run are the tests that pass in both deposited whole-baseline runs (`whole/base.json` of the deposited records), and every traced pytest call left its result file and its trace |
| T3-repeat | `trace_run.py` | with 2 or more repeats, every traced run gives the same entry-point sets and the same passing tests; the differences are listed |
| T3-repeat-reach | `trace_run.py` | with 2 or more repeats, every traced run gives the same set of codes that started under at least 1 entry point, which is all that rule 3 reads |
| T-map | `trace_run.py` | every started code of a subject file is a function of `checks.json`, or a lambda, a generator expression or an unlisted definition found at that line of the source |
| T4 | `analyse3.py` | `reach/analyse.py` on the rule-3 targets passes its 7 sentinels |
| R2 | `analyse3.py` | `reach/analyse.py` on the rule-2 targets, from the deposited records, writes files equal byte for byte to `../target-reach/generated/<name>/` (SHA256SUMS aside) |
| (unnamed) | `rule3.py` | every function of `reach.json` is a function of `checks.json` |

## Where the field `reachable` is read

In the toolkit the field `reachable` of a check is read by `reach/targets.py`
(the candidates of the rule); by `reach/analyse.py` (column `reachable` of
`checks.csv`, and the counts `checks_reachable` and
`checks_deciding_not_statically_reachable`); by `reach/report.py` (the row
"checks reachable"); by `recompute/second.py` and `recompute/compare.py`; by
`validate_pyjwt.py`; and by `reach/run.py` in a count that `define` prints.
The deletions (`reach/run.py`, `reached_checks`) take the checks that fire in
a case of the study (`reach/study.py`) and do not read it. `analyse3.py`
keeps `checks.json` unchanged in both derived folders, so those columns and
counts give the reachability by name under both rules; only the targets, and
what derives from them, differ.

## Results on the development subjects

Run of 14 November 2026, CPython 3.12.3, 3 repeats per subject. All sentinels
above hold for the 3 subjects in the runs whose outputs are in
`generated/trace/`.

| | pyjwt | pyjwt-package | jwcrypto |
|---|---|---|---|
| Checks | 80 | 99 | 146 |
| Reachable by name | 54 | 57 | 93 |
| Reachable by execution | 52 | 52 | 103 |
| Both | 52 | 52 | 89 |
| By name only | 2 | 5 | 4 |
| By execution only | 0 | 0 | 14 |
| Neither | 26 | 42 | 39 |
| Cases of the study | 91 | 91 | 42 |
| Cases with a target, rule 2 / rule 3 | 49 / 49 | 49 / 49 | 14 / 14 |
| Same target | 49 | 49 | 14 |
| Changed, gained, lost a target | 0, 0, 0 | 0, 0, 0 | 0, 0, 0 |
| Flags, rule 2 / rule 3 | 1 / 1 | 1 / 1 | 4 / 4 |
| Fired checks under an entry point | 44 of 44 | 44 of 44 | 33 of 33 |
| Suite, without / with the plugin (mean of 3, s) | 5.749 / 6.047 | 5.730 / 6.175 | 5.978 / 6.516 |

The times are those of the run whose outputs are written; on the same
machine, an earlier run of `jwcrypto` gave 5.722 / 6.980 s, so the overhead
of the plugin varied between 5 % and 22 % across these runs.

In `jwcrypto` the 14 checks reachable by execution only are 11 checks of
`JWK.import_key`, 1 of `JWA.signing_alg`, 1 of `JWSCore._jwa` and 1 of
`JWSEHeaderRegistry.__init__`; none of them changes a target. On the 3
subjects the analysis under rule 3 gives the outputs of the toolkit byte for
byte, except the rule name in `summary.json` and `SUMMARY.md`.

**Repeats.** In 2 earlier runs of `jwcrypto` (3 and 5 repeats), T3-repeat did
not hold: the code `InvalidJWSSignature.__init__` (`jwcrypto/jws.py`) started
under `deserialize` and `verify` in some runs and under `deserialize`,
`validate` and `verify` in others (run 3 of 3 in the first, runs 2 to 5 of 5
in the second, against run 1); the first start under `validate` was in
`jwcrypto/tests.py::TestJWT::test_Issue_209`, which validates a token with a
key set holding a newly generated key, so the order in which the keys are
tried varies between runs. That function holds no check, and it started
under at least 1 entry point in every run, so the input of rule 3 was the
same; T3-repeat-reach was added after these runs and was not evaluated on
them. In the run whose outputs are written, all 3 repeats agree.

## Limits

- The trace is 1 run of the suite (the first of the repeats); a path that a
  test takes only in some runs can add or remove an entry-point name.
- Only `PY_START` is a start: resumptions of generators and coroutines are
  not read.
- Only the thread of the start counts; work handed to another thread, a
  process or an event loop in another thread is not credited to the entry
  point that handed it over.
- The counters of the plugin are updated without a lock; with several
  threads, a count of starts can be low. The sets of entry-point names are
  updated by a single set operation.
- Entry-point frames are recognized by name, like the closure by name: any
  function of the subject named like an entry point counts, whatever its
  class.
- Rule 3 can only add candidates to rule 2; a check reachable by name stays
  a candidate even when it never starts under an entry point.
- Reachability by execution depends on the suite: a function that no test
  reaches through an entry point is not reachable by execution.
