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

**What the plugin leaves alone.** A suite may replace a function of the
standard library during a test and count its calls. The callback of the
plugin therefore calls nothing that a test can replace: it reads no
environment variable and calls no function of `os`. The test id of a start is
the node id that pytest passes to `pytest_runtest_logstart`. The paths of the
subject files are spelled out when the plugin starts (as given, absolute and
with links resolved), and a file name is looked up among them as it stands;
a name that is no such spelling and resolves to a subject file is reported
when pytest ends, and sentinel T-files then does not hold, since the starts
of that file's codes were not recorded.

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
| T-files | `trace_run.py` | no code of a subject file ran under a file name that the plugin did not hold when it started |
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

## Results

Runs of 14 November 2026, CPython 3.12.3, 3 repeats per subject, with the
plugin whose SHA-256 is
`0a29e451a3b1fa5bc9cbbbf42bffe9c464a68aa865ded5270d8a5228be5d10d7`
(`plugin_sha256` in every `reach.json`). The outputs are in
`generated/trace/`. All sentinels above hold for the 7 subjects, except
T3-repeat for `jwcrypto` (see "Repeats").

### Development subjects

| | pyjwt | pyjwt-package | jwcrypto |
|---|---|---|---|
| Checks | 80 | 99 | 146 |
| Reachable by name | 54 | 57 | 93 |
| Reachable by execution | 52 | 52 | 103 |
| Both | 52 | 52 | 89 |
| By name only | 2 | 5 | 4 |
| By execution only | 0 | 0 | 14 |
| Neither | 26 | 42 | 39 |
| Functions started / under an entry point | 73 / 39 | 115 / 47 | 261 / 148 |
| Cases of the study | 91 | 91 | 42 |
| Cases with a target, rule 2 / rule 3 | 49 / 49 | 49 / 49 | 14 / 14 |
| Same target | 49 | 49 | 14 |
| Changed, gained, lost a target | 0, 0, 0 | 0, 0, 0 | 0, 0, 0 |
| Decided by the target, rule 2 / rule 3 | 48 / 48 | 48 / 48 | 10 / 10 |
| Flags, rule 2 / rule 3 | 1 / 1 | 1 / 1 | 4 / 4 |
| Assertion tier, rule 3: with a target / decided | 42 / 42 | 42 / 42 | 6 / 6 |
| Name tier, rule 3: with a target / decided | 7 / 6 | 7 / 6 | 8 / 4 |
| Fired checks under an entry point | 44 of 44 | 44 of 44 | 33 of 33 |
| Suite, without / with the plugin (mean of 3, s) | 5.747 / 6.009 | 5.765 / 6.276 | 6.077 / 6.698 |

In `jwcrypto` the 14 checks reachable by execution only are 11 checks of
`JWK.import_key`, 1 of `JWA.signing_alg`, 1 of `JWSCore._jwa` and 1 of
`JWSEHeaderRegistry.__init__`; none of them changes a target. On the 3
subjects the analysis under rule 3 gives the outputs of the toolkit byte for
byte, except the rule name in `summary.json` and `SUMMARY.md`.

### The 4 held-out libraries

| | google-auth | oauthlib | authlib | joserfc |
|---|---|---|---|---|
| Checks | 100 | 88 | 39 | 97 |
| Reachable by name | 52 | 54 | 36 | 81 |
| Reachable by execution | 14 | 61 | 35 | 84 |
| Both | 14 | 54 | 33 | 71 |
| By name only | 38 | 0 | 3 | 10 |
| By execution only | 0 | 7 | 2 | 13 |
| Neither | 48 | 27 | 1 | 3 |
| Functions started / under an entry point | 848 / 21 | 373 / 53 | 1081 / 266 | 342 / 197 |
| Cases of the study | 22 | 142 | 48 | 190 |
| Cases with a target, rule 2 / rule 3 | 15 / 15 | 53 / 84 | 30 / 30 | 131 / 106 |
| Same target | 15 | 53 | 30 | 59 |
| Changed, gained, lost a target | 0, 0, 0 | 0, 31, 0 | 0, 0, 0 | 43, 4, 29 |
| Decided by the target, rule 2 / rule 3 | 13 / 13 | 43 / 74 | 18 / 18 | 71 / 90 |
| Flags, rule 2 / rule 3 | 2 / 2 | 10 / 10 | 12 / 12 | 60 / 16 |
| Assertion tier, rule 3: with a target / decided | 0 / 0 | 31 / 31 | 5 / 5 | 38 / 38 |
| Name tier, rule 3: with a target / decided | 15 / 13 | 53 / 43 | 25 / 13 | 68 / 52 |
| Fired checks under an entry point | 13 of 13 | 47 of 47 | 24 of 24 | 55 of 55 |
| Suite, without / with the plugin (mean of 3, s) | 81.623 / 81.987 | 1.690 / 3.373 | 26.586 / 30.649 | 6.766 / 8.593 |

Over the 4 libraries, 229 cases have a target under rule 2 and its target
decides 145 of them (84 flags); 235 have a target under rule 3 and its target
decides 195 (40 flags). In the assertion tier the counts are 129, 76 and 53
under rule 2 and 74, 74 and 0 under rule 3; in the name tier 100, 69 and 31
under rule 2 and 161, 121 and 40 under rule 3.

The checks reachable by execution only are, in `joserfc`, 9 checks of the 7
methods `JWTClaimsRegistry.validate_aud`, `validate_exp`, `validate_iat`,
`validate_iss`, `validate_jti`, `validate_nbf` and `validate_sub`
(`joserfc/_rfc7519/claims.py`, started under `validate`), 2 of
`decode_header` (`joserfc/_rfc7515/compact.py`), 2 of
`extract_rfc7515_compact` (`joserfc/_rfc7797/compact.py`) and 1 of
`extract_rfc7797_json` (`joserfc/_rfc7797/json.py`); in `oauthlib`, 7 checks
of `GrantTypeBase._inflate_claims` and of the 3 methods
`openid_authorization_validator` of `GrantTypeBase`, `HybridGrant` and
`ImplicitGrant` (`oauthlib/openid/connect/core/grant_types/`); in `authlib`,
2 checks of `decode_payload` (`authlib/jose/rfc7519/jwt.py`). In
`google-auth` the 14 checks reachable by execution are all reachable by name
too, and the entry point is `decode`: of the 848 functions that started, 21
started under it.

The targets of `google-auth` and `authlib` are the same under both rules. In
`oauthlib` 31 cases gain a target and each is decided by it; no case changes
or loses one. In `joserfc`, of the 60 cases that are flags under rule 2, 32
are decided by their target under rule 3, 23 have no target under rule 3 and
5 stay flags; of the 71 cases decided by their target under rule 2, 54 stay
decided, 11 are flags under rule 3 and 6 have no target; 4 cases without a
target under rule 2 gain one that decides them (`compare.csv`).

The expectations of section 4.2 of `PROTOCOL.md`: T1 is not met (16 flags of
`joserfc` under rule 3; the expectation was at most 10). T2 is met: the 3
cases keep their target under rule 3 (`compare.csv`, transition "same
target"). T3 is not met: the target decides 90 of the 106 cases of `joserfc`
with a target under rule 3, 84.9 %, and the expectation was at least 85 %.

The mean time of the suite with the plugin, against the mean without it, is
higher by 0.4 % (`google-auth`), 4.6 % (`pyjwt`), 8.9 % (`pyjwt-package`),
10.2 % (`jwcrypto`), 15.3 % (`authlib`), 27.0 % (`joserfc`) and 99.6 %
(`oauthlib`, 1.690 s against 3.373 s).

**Repeats.** For `jwcrypto`, T3-repeat does not hold in the run whose outputs
are written: the code `InvalidJWSSignature.__init__` (`jwcrypto/jws.py`)
started under `deserialize`, `validate` and `verify` in run 1 and under
`deserialize` and `verify` in runs 2 and 3. The same difference appeared in 2
earlier runs of `jwcrypto` (3 and 5 repeats): the first start under
`validate` is in `jwcrypto/tests.py::TestJWT::test_Issue_209`, which
validates a token with a key set holding a newly generated key, so the order
in which the keys are tried varies between runs. That function holds no
check, and it started under at least 1 entry point in every run, so the input
of rule 3 is the same: T3 and T3-repeat-reach hold, which is the condition of
section 4.2 of the protocol. The run was not repeated until the 3 traces
agreed. For the other 6 subjects all 3 repeats agree.

The traces were made 2 times: the first runs used the plugin as committed
with the protocol, the runs whose outputs are written use the corrected
plugin (`DEVIATIONS.md`, section 1.2). For `joserfc`, `oauthlib` and
`authlib`, where both runs completed, the 2 runs give the same functions and
the same entry-point sets.

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
