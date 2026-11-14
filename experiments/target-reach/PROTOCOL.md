# Protocol: declared targets and check deletions on 4 more verification libraries

Fixed on 14 November 2026, before any target was computed, any test was run
under the recorder and any check was deleted on the 4 libraries of section 3.
Section 5 says exactly what had been done before. Right after the commit that
holds this file, a text that names the commit is time-stamped by 2
authorities; a later commit adds the tokens in `timestamps/`.

## 1. Purpose

The experiment in `../mutation-adequacy-pyjwt/` measured 2 things on PyJWT
2.15.1 without a mutation tool. First, for each negative-test block, whether
the check that rejects the input is the check the test describes. Second, for
each check that rejects an input in those tests, which test oracles notice
when the check is deleted. Its targets were labels written by hand.

This experiment repeats both measurements on 4 more libraries, with the
targets assigned by a fixed rule instead of by hand. It is a replication of
an exploratory study: it reports counts per library and tests no hypothesis.
PyJWT is the development subject, on which the toolkit and the rule were
built. `jwcrypto` is the pilot. The 4 libraries of section 3 are held out.

## 2. Questions

- **Q1.** In how many cases with a target is the input rejected by the
  target, and what happens in the others?
- **Q2.** For each check that fires in the negative tests, which oracles
  detect its deletion? Where the whole suite does not detect it, is there an
  input that the library accepts only without the check?
- **Q3.** When the check that decides a case is deleted, does the case's own
  test fail, and does that depend on whether the block asserts more than the
  exception class?

### Expectations stated in advance

The PyJWT study leads to 5 expectations. They are not hypothesis tests. Each
is decided per library and reported with its counts as *held* or *not held*,
unless 1 of the 4 rules below gives it another status. Section 4 defines the
terms.

| | Expectation, for 1 library | Decided on | PyJWT, package scope | Pilot |
|---|---|---|---|---|
| E1 | At least 1 deletion of a deciding check is not detected by O_V. | deletions of deciding checks | held (7 of 44) | held (4 of 16) |
| E2 | O_C detects at least 1 deletion of a deciding check that O_V does not. | deletions of deciding checks | held (4 of 44) | held (4 of 16) |
| E3 | The whole suite detects every deletion of a deciding check. | deletions of deciding checks | held (44 of 44) | held (16 of 16) |
| E4 | At least 1 case with a target is not decided by its target. | cases with a target | held (1 of 49) | held (4 of 14) |
| E5 | At least 1 case of a class-only block passes its own test after the deletion of its deciding check. | cases of class-only blocks whose deciding check is deleted and whose deletion run gives a record | not stated (29 of 79 included blocks are class-only; the count is 1 of 30 cases) | not held (0 of 42) |

4 rules, applied by `reach/report.py` and nowhere else:

- E5 is stated for a library in which at least 9 of every 10 included blocks
  are class-only; elsewhere it is reported as *not stated*. By the counts of
  this commit, which come from the sources alone, E5 is stated for `oauthlib`
  (71 of 73 included blocks), `authlib` (41 of 43) and `joserfc` (133 of
  138), and not for `google-auth` (0 of 17). The threshold was set after the
  pilot, with these 4 shares known.
- An expectation with 0 units to be decided on in a library is reported as
  *not applicable*.
- A library in which a sentinel of section 4 does not hold gets no verdict:
  each of its 5 expectations is reported as *no verdict*, with the numbers
  of the sentinels that do not hold.
- The report is not written while a library named to it lacks the records of
  the whole suite.

The expectations were written with the counts of PyJWT and of the pilot in
view, so their 2 columns are a comparison and no test. The pilot did not show
E5. No expectation is stated for the checks that fire and never decide: the
pilot introduced them (section 5), and PyJWT has none.

## 3. Subjects

`SELECTION.md` records the selection: the frame, the criteria, the screening
of the 50 candidates, the recount and the releases.

| Subject | Version | Commit | Package | Entry points | Rejection base |
|---|---|---|---|---|---|
| google-auth | 2.62.2 | `50b1eb269f110a4b7ab09ffe5ae59c0151cd63c2` | `google` | `decode` | the built-in `ValueError` |
| oauthlib | 4.0.1 | `6e3aa05af92978755939a18cb4dd655ced156c1e` | `oauthlib` | `validate_authorization_request`, `validate_token_request` | `OAuth2Error` |
| authlib | 1.9.5 | `42607cbc2135252a641a845e4ed7f94e3a922c47` | `authlib` | `decode`, `deserialize`, `deserialize_compact`, `deserialize_json`, `validate` | `JoseError` |
| joserfc | 1.8.0 | `f345ff71cd6c36452a4e11e47b805ad450a95dd8` | `joserfc` | `decode`, `decrypt_compact`, `decrypt_json`, `deserialize_compact`, `deserialize_json`, `validate`, `validate_compact` | `JoseError` |

A subject is defined by 6 decisions, each written with its source in
`subjects/<name>/draft.json`:

1. the release: the latest release at the Python Package Index (PyPI) on 14
   November 2026 that is not a pre-release, at the commit of its tag;
2. the package directory;
3. the entry points: the names of the public functions or methods through
   which a received artifact is submitted for verification;
4. the rejection base: the base class of the exceptions the documentation of
   the entry points names as rejections;
5. the test directories: those of the project's own test configuration;
6. the suite runs: the pytest calls of the project's own test configuration.

An entry point is a name. It can name a class whose constructor takes the
artifact: the pilot names `JWT`, and none of the 4 libraries names a class.
Such a name counts for the blocks that call it; it starts no reachability,
which starts from function definitions (section 4).

`draft.json` also holds settings that are no decisions of the study. They
were set by hand from the layout of each repository: the paths that a copy
of the release takes (`copy`), the options that every pytest call gets
(`pytest_args`), the Python version, the name of the distribution, the
source root and, for `google-auth`, the directory of the project inside its
repository.

Everything else is derived by `reach/scope.py` and `reach/run.py define`: the
subject files are every Python file of the package that is not a test file,
and the test files of the recorder runs are those that hold at least 1
included block. The definitions of the 4 subjects are in `subjects/` and are
part of the protocol commit. They change after it only as a deviation
(section 6).

**The rejection base of google-auth, and why there are 4 libraries.**
Decision 4 has 2 readings for `google-auth`, and the choice between them was
made with the tests in view. The docstring of `decode` names 2 exceptions,
`google.auth.exceptions.InvalidValue` and `MalformedError`. Both inherit from
the package's own base, `GoogleAuthError`, and from the built-in
`ValueError`. Of the 20 blocks that call `decode`, 14 expect `ValueError`, 2
`InvalidValue` and 1 `MalformedError`; the other 3 name `TypeError`, 1 of
them beside `ValueError`. With `GoogleAuthError` as the base, 3 blocks are
included and the library fails criterion I4 of the selection, which asks for
10; with `ValueError`, 17 are included and it passes. `ValueError` was
chosen. `selection/recounts.txt` gives the counts under both readings and
under their union.

The selection takes the first 3 candidates in rank order that pass the
criteria. Under the reading that was made, they are `google-auth`, `oauthlib`
and `authlib`. Under the other reading, `google-auth` is no subject and they
are `oauthlib`, `authlib` and `joserfc`. The experiment therefore runs all 4
and reports each library on its own; a reader who rejects the reading that
was made drops the row of `google-auth` and loses nothing else.

**No replacement.** A library whose tests cannot be run under the recorder
without changing 1 of the 6 decisions is reported as failed, with the reason.
No other library takes its place. A defect of the toolkit is not a reason to
fail a library (section 6).

**PyJWT in 2 scopes.** `subjects/pyjwt` keeps the scope of the reference
study: 2 subject files and 1 observed file, whose checks are recorded and
never deleted. It serves only to compare the toolkit with that study
(`generated/pyjwt/VALIDATION.md`). `subjects/pyjwt-package` defines
PyJWT by the 6 decisions above, like the 4 libraries; its row is the one
shown beside theirs.

## 4. Definitions

The first 5 definitions, down to the target, are read from the sources:
nothing is run. The others are about runs.

**Class labels.** A class is known by the module that defines it. A class
expression (a name or an attribute chain) is resolved through the bindings of
the module it stands in: class statements, imports, relative ones too, star
imports from modules of the package, and aliases, which are assignments of a
name or an attribute chain. Where a module binds a name 2 or more times, the
binding read last wins. The bindings under an `if`, `try`, `with` or `async
with` statement are read; those in a loop or a `match` statement are not
(section 8). The parts of a compound statement are read in this order: for a
`try` statement the handlers, then the body, the `else` part and the
`finally` part, so that an import in the body wins over its fallback in a
handler; for an `if` statement the body, then the `else` part.
Inside a function, the imports of that function, in the order of their lines
wherever they stand in its body, and then its class statements come first;
then those of the functions that enclose it, the innermost first; then the
bindings of the module, its star imports, the last first, and the built-ins.
A class of the package is labelled by its
bare name when no other class statement of the package has that name and no
built-in has it, and by `<module>.<qualified name>` otherwise. A built-in
class is labelled by its name, and a class imported from outside the package
by its dotted path. An expression that cannot be followed (a parameter, a
variable, the result of a call) stands for the package class of the same bare
name when exactly 1 class statement of the package has that name and no
built-in has it; otherwise it names no class and is labelled `?name`. A class
statement of a test module outside the package directory names no class of
the package.

**Rejection class.** A rejection base is a class of the package or a built-in
class. A rejection class is a rejection base, a class of the package that
inherits from one, or a built-in class that inherits from a built-in
rejection base. Inheritance follows the declared bases, resolved as above,
and for a built-in class the bases the interpreter gives. A class from
outside the package and an expression that names no class are not rejection
classes, whatever they inherit from.

**Check.** The raise statements of 1 function definition that construct the
same rejection class with the same message template. The function
definitions read are those at the top level of a module, in a class body and
in another function, and those under an `if`, `try` or `with` statement at
any of these places. The handlers of a `try` statement, loops, `async with`
and `match` statements are not searched for definitions (section 8). A raise
statement belongs to the innermost definition that holds it. It constructs a
class when it raises a call of the class, the class itself, or a local name
that the function binds exactly 1 time, by a plain assignment from a call of
the class. Every other statement that binds the name, or that assigns to 1
of its attributes or items, counts as a further binding. A name that is the
bare name of a class of the package is always read as that class. A `from`
clause changes nothing. The message is the first positional
argument of the call or, when the call has none, the keyword argument named
as the first parameter of the nearest `__init__` in the method-resolution
order of the class. The template is the message with every computed part
replaced by a placeholder. Not checks, and listed apart: a bare `raise`; a
raise of the name bound by an `except` clause; a raise of a class held in a
variable or a parameter; a raise of a class that is not a rejection class.
Every function definition is kept: when 1 scope defines a name 2 or more
times (a property and its setter, `@overload` stubs and the implementation),
the definition number k, from the second on, is named `<name>~k`.

A check is *reachable* when its function is in the closure of the entry
points under reference by name: a function refers to every name it calls and
to every attribute name it mentions, and a name stands for every function
definition of that name in the files of the subject. The closure starts from
the function definitions that have the name of an entry point.

**Block.** A use of `pytest.raises`, `assertRaises`, `assertRaisesRegex` or
`assertRaisesRegexp` in a test function, as an item of a `with` statement
(not of an `async with`) or with a callable among its arguments. The test
directories of a subject (decision 5) can name a file as well as a
directory. The test files are the files named so, whatever their name, and
the files named `test_*.py` or `*_test.py` under the directories. The pilot
names 3 files, `jwcrypto/tests.py`, `jwcrypto/tests-cookbook.py` and
`jwcrypto/tests_mldsa.py`; the 4 libraries name directories only. A test
function is any function definition at the top level of
a test file or in a class of it, whatever its name; a block in a function
nested in a test function belongs to that test function. When 1 scope
defines a test name 2 or more times, the last definition counts, as in
Python.

A block is *included* when it calls an entry point and every class it
expects is a rejection class. It calls an entry point when the body of the
`with` statement holds a call whose function has, as its last name, the name
of an entry point; in the form with a callable, when an argument holds such
a call or mentions such a name. The expected classes are those of the first
argument or of the keyword `expected_exception`: a class expression or a
tuple of them, resolved in the test module as above. A name that neither the
module nor an enclosing function binds stands for the classes that the test
function assigns to it before the block. A block *asserts more than the
class* when it gives a pattern or the test asserts on the caught exception
afterwards; otherwise it is *class-only*.

The block counts of a subject cover the test files of its recorder runs,
which are the files with at least 1 included block; `scope_counts` in
`subject.json` gives the number of test files and of blocks over the test
directories. `subjects/pyjwt` names its test directory by hand, as the
reference study did, and has no `scope_counts`.

**Target.** The check the block describes, assigned by rule
`reach-target-rule/2` (`reach/targets.py`, whose header states the rule in
full). The rule reads the block's expected classes, its pattern, the
assertions on the caught exception and the name of the test. It never reads a
run. In short: the candidates are the reachable checks whose class is an
expected class or inherits from one. The block's assertions exclude the
candidates that cannot satisfy them: an assertion on the message excludes a
check whose message cannot satisfy it, and an assertion that an attribute of
the exception equals a constant excludes a check whose raise calls all give
that attribute a literal value and none of them that constant. A single
remaining candidate is the target. Otherwise, when exactly 1 remaining
candidate has a literal part of its message, or a literal argument, that
satisfies an assertion, that candidate is the target. Otherwise the name of
the test breaks the tie, among the candidates with such a literal when there
are 2 or more of them and among all the remaining candidates when there is
none: each is scored by
inverse-document-frequency weighting of the tokens it shares with the name,
and the single highest score above 0 gives the target. No candidate, no
remaining candidate or no single highest score means no target. Targets
assigned from classes and assertions alone form the *assertion tier*, those
that needed the name of the test the *name tier*. Counts are reported per
tier.

**Runs.** Every run uses a fresh copy of the release, made from a clone at
the commit of section 3, and the environment pinned in
`subjects/<name>/requirements.txt`, on CPython 3.12.3. Before the runs of a
library, `reach/run.py verify` checks that the clone is at that commit; that
the paths copied from it hold no changed, untracked or ignored file; that
the subject files and the test files have the digests recorded with the
definitions; that the interpreter is CPython 3.12.3; that its installed
packages are exactly those of `requirements.txt`, `pip` aside; and that the
library itself is not installed in the environment, so that the tests import
it from the copy. Every pytest call gets the same environment variables
(`PATH`, `HOME`, `LANG` and `LC_ALL` set to `C.UTF-8`, `PYTHONHASHSEED=0`,
`PYTHONDONTWRITEBYTECODE=1`) and the options of `pytest_args`.

A *recorder run* runs the test files of the subject under the pytest plugin
`reach/recorder.py`. A *whole-suite run* runs every suite run of decision 6,
without the recorder, each as 1 pytest call that writes a result file. Under
the recorder a test goes on after a block whose own check fails; the failure
is recorded and the test counts as failed. The runs of the deletion copies
go 10 at a time.

**Outside connections.** Every pytest call of the study loads
`guard/reach_offline.py`. An attempt to connect to an address that is neither
a loopback address nor a Unix socket, and a lookup of a host name other than
`localhost`, is refused with an error and counted; a lookup of an address
literal passes. The refusal sits in the `connect` and `connect_ex` methods of
a socket and in `socket.getaddrinfo`, and nowhere else (section 8). The
counts are in the records and in the summaries; for a run that was repeated,
the count is that of the repeated run.

**Baseline.** First the test files are run 1 time without the recorder, in a
run that goes on past a file it cannot collect. A test of which a report
fails in this run (its setup, its body, its teardown or a subtest) is an
*expected baseline failure*: every recorder run deselects it, by its exact
identifier as this run reports it, and it is listed. A test file that pytest
cannot collect in this run is ignored in every recorder run and listed. Then
come 2 recorder runs, on 2 unmodified copies. Each of these 3 runs may take
3600 s; a run that takes longer stops the step.

**Tests collected through an import.** A test that a test file imports from
another test file is collected a second time, under the importing file. The
copy is deselected when the run holds the same test in the file that defines
it, and listed (`collected_again`). A copy stays whenever the run does not
hold the test in its defining file, as when that file is not among the test
files of the subject, and is listed (`imported_kept`).

**Case.** 1 execution of an included block in 1 test, in the first of the 2
baseline recorder runs; the executions of a block in a test are numbered in
order. An execution that ends with an exception that is no subclass of
`Exception`, such as a keyboard interrupt or an outcome that pytest raises
to skip or fail a test, is not recorded and takes no number. The *cases of
the study* are the cases in which the block raises an exception of a
rejection class and the block's own check accepts it. The other cases are
left out and counted by reason.

At run time, an exception is of a rejection class when the method-resolution
order of its class holds a class with the module and the qualified name of a
rejection base. For a built-in base this covers every subclass from any
module, the standard library included. So a case of the study can raise a
class that is no rejection class in the sources; the statement that raises it
is then not a check.

**Deciding check.** The raise site of a case is the innermost frame of the
exception's traceback inside the package directory. When its line is a line
of a raise statement of a check, that check *decides* the case. Otherwise no
check decides it: the raise site is a raise statement that is no check, a
line that is no raise statement, or the traceback has no frame inside the
package. A check that decides at least 1 case of the study is a *deciding
check*.

**Fired checks.** A check *fires* in a case when, while the block is open, 1
of its raise statements raises an exception whose class has the bare name of
the check's class, whether or not a handler catches it later. The recorder
takes this from the interpreter's `RAISE` events (`sys.monitoring`) and
counts an event only when its instruction is the raise instruction itself,
`RAISE_VARARGS`: an exception that merely passes through a raise statement is
no firing. The events are those of the whole process, so a firing in another
thread counts; the record names the checks that fired only in other threads
(`fired_other_threads`). The check that decides a case counts as firing in
it, and sentinel 5 checks that the events say the same. A block opened while
the same thread holds another block open is a case of its own, of depth 2 or
more, and what fires inside it counts in every open block. The inner block
keeps its exception, whatever its own check decides, so the outer block sees
none: the outer case raises nothing, its own check fails and the test counts
as failed.

**Outcome of a case with a target.** 1 of 4: the target decides the case; the
target fires and another check decides; the target fires and no check
decides; the target does not fire. A case of the last 3 kinds is a *flag*.
Where a record holds no fired checks, because the interpreter gives no such
events, a case that its target does not decide gets a fifth value, "not
decided by the target", and sentinel 5 does not hold.

**Deletion.** Every raise statement of the check is replaced by `pass` in a
copy of the package; every line keeps its number. The checks deleted are the
checks of the subject files that fire in at least 1 case of the study in the
first of the 2 baseline recorder runs: the deciding checks and the checks
that fire and never decide, reported apart. Each deletion copy gets 1
recorder run and 1 whole-suite run. An unmodified *control copy* gets the
same 2 runs.

**A test passes** in a recorder run when its setup, its body and its teardown
pass, none of its blocks fails its own check and none of its subtests fails.
A test that ends as an expected failure counts as skipped: it does not pass,
and it is no failure either. No test file of the 6 libraries carries such a
mark. In a whole-suite run a test passes when the result file of its pytest
call gives it no failure, no error and no skip; a test that the file names 2
times with 2 outcomes counts as failed, and a file that pytest cannot
collect counts as 1 failed test.

**Status of a case in a deletion run.** *Observed*: the run holds the case.
Otherwise the test of the case decides, by the first of 5 rules that applies:

1. the run holds no record of the test: *crashed*;
2. the test went on after a block that failed its own check: *withheld* when
   the test then stopped, a skip included, or had a failed subtest, and
   *missing* otherwise;
3. the test stopped, in its setup or in its body, and was not skipped:
   *withheld* when it stopped on a failed assertion (an `AssertionError`, or
   pytest's failure outcome `Failed`, which `pytest.fail` raises, as does a
   `pytest.raises` or `pytest.warns` that sees no exception or warning),
   *crashed* otherwise;
4. subtests of the test failed: *crashed* when the record names what stopped
   each failed subtest and none of them stopped on a failed assertion in the
   sense of rule 3, *withheld* otherwise;
5. otherwise *missing*: the test was skipped, or it ended without running the
   block.

A crash of any case counts as a detection under O_V, O_Vfc, O_C, O_T and
O_S. Withheld cases are not counted in the main columns; a second set of
columns, for the 4 case oracles O_V, O_Vfc, O_C and O_T, counts them as
failing. Missing cases are not counted.

**Oracles.** Each holds or not for a case at baseline and in a deletion run.

| Oracle | Holds for a case when |
|---|---|
| O_V | an exception of a rejection class is raised |
| O_Vfc | any exception is raised |
| O_C | an exception is raised and its class, by module and qualified name, is the class the case raises at baseline |
| O_T | the raise site is the target (cases with a target only) |

A deletion is *detected* under a case oracle when the oracle holds for a case
of the study at baseline and does not hold for that case, observed, in the
recorder run of the deletion copy. 3 more detections are decided on tests.
**O_S**: a test that holds a case of the study passes at baseline and does
not pass in that recorder run. **Suite**: the same, for any test of the
recorder run. **Whole suite**: a test that passes in both unmodified
whole-suite runs does not pass in the whole-suite run of the deletion copy.

By construction, a deletion detected under O_Vfc is detected under O_V, and
one detected under O_V is detected under O_C. A deletion detected under O_V
is also detected under O_S when the test of the case passes at baseline; one
detected under O_S is detected under the suite; and one detected under the
suite is expected to be detected under the whole suite, which runs the same
tests without the recorder. O_T is not nested in these. The analysis counts
the deletions that break each of these 5 inclusions, the third without its
condition; the expected count is 0, and any other count is listed and
explained.

**Pinning.** For each case of the study, on the copy without its deciding
check: the case's own test passes or does not pass, by class-only blocks and
blocks that assert more, and what the case does when the test still passes.
The unit counted is the case, and what is read is its test: a test with
several blocks does not pass when any of them fails. Here "the test fails"
stands for "the test does not pass". A case is not counted when no check
decides it, when its deciding check is not deleted because it lies outside
the subject files, or when the deletion run exceeded the time limit or gave
no record; these cases are counted by reason. For each case with a target,
the own test is read in the same way on the copy without the target. Where
it cannot be read, the reason is the time limit, no record, or that the
target was not deleted, because it lies outside the subject files or because
it fires in no case of the study.

**Time limit.** The recorder run of a deletion copy or of the control copy
may take 10 times the slower of the 2 baseline recorder runs, and at least 60
s. A run that gives no record, because it exceeded the limit or because the
interpreter ended before the record was written, is repeated 1 time, alone,
on a fresh copy. When both runs exceed the limit, the deletion counts as
detected under O_V, O_Vfc, O_C, O_T, O_S and the suite, and its cases are
counted apart. When a run gives no record 2 times without both exceeding the
limit, sentinel 4 does not hold; that is a deviation (section 6).

A whole-suite run follows the same limit on the slower of the 2 unmodified
whole-suite runs, and the limit holds for all the suite runs of a copy
together. A whole-suite run that exceeds it, or of which a pytest call
leaves no result file that can be read, is repeated 1 time, alone, on a
fresh copy. When the repeated run ends in 1 of these 2 ways too, the
deletion counts as detected by the whole suite. Each of the 2 unmodified
whole-suite runs may take 7200 s and must end with its result files, and
each run of a witness test may take 600 s. The summary lists every run that
was repeated and every run that ended without a record or a result.

**Sentinels.** `reach/analyse.py` stops without writing any output when
`checks.json`, `blocks.json`, `targets.json`, the record of the suite run
without the recorder (`suite.json`) or either of the 2 baseline recorder
records is absent. Otherwise it writes its outputs and then exits with an
error unless all 7 hold, and a sentinel whose other records are absent (the
deletion runs, the control copy, the whole-suite runs) does not hold. A
library in which a sentinel does not hold gets no verdict on the
expectations (section 2).

1. The 2 baseline runs and the control copy give identical records, message
   texts aside (a message can hold the time of the run; no count reads it).
2. In the baseline recorder run every test passes or is skipped, every test
   file is collected, and the tests deselected are the expected baseline
   failures.
3. Under the deletion of a check, that check fires in no case.
4. Every deletion run gave a record or exceeded the time limit 2 times.
5. The check that decides a case is among the checks that fire in it.
6. The whole suite ran on every deletion copy, and on the control copy it
   ends with its results and loses no test that passes in both unmodified
   runs.
7. The deleted checks are the checks of the subject files that fire in at
   least 1 case of the study.

## 5. What had been done before this protocol

**On PyJWT.** The toolkit and the target rule were developed on PyJWT, with
the hand labels of the reference study in view. Version 1 of the rule was
written without them; version 2 after the comparison. The agreement of the
rule with those labels (`generated/pyjwt/VALIDATION.md`) is therefore not an
independent validation of the rule.

**On the candidates.** The screening of `SELECTION.md`: reading, and counts
on the syntax tree. Nothing was run. The recount of 11 projects with the
toolkit's own enumerators reads sources only.

**On the 4 subjects.** Their sources and tests were read to write the 6
decisions. `reach/scope.py`, `reach/run.py define` and `reach/run.py verify`
derived and checked `subject.json`, `checks.json` and `blocks.json`, so the
checks and the blocks of the 4 libraries were known, with the blocks that are
class-only. Their sources were also scanned, without running anything, for
what the enumerations of section 4 do not read (section 8). The following
runs were made, all on unmodified copies and without the recorder:

- `google-auth`, `oauthlib`, `authlib`: the test files that hold included
  blocks, 1 time, and the whole suite, 2 times, with an earlier state of the
  toolkit; their records were removed before this commit;
- `joserfc`: its test directory, 1 time;
- all 4: the offline check of criterion I5, which runs every suite run 1 time
  plainly and 1 time with outside connections refused
  (`selection/offline-check.txt`).

The tests of the toolkit itself run the recorder on small synthetic packages.
They were also run with the interpreters of the `google-auth` and `oauthlib`
environments, because those hold the pytest plugins that some of these tests
need; that runs no test of a library.

Not done on any of the 4: no target was computed, no test of a library was
run under the recorder, and no check was deleted.

**On the pilot.** The whole procedure was run on `jwcrypto` 1.6.1, the
lowest-ranked candidate that passes the criteria, to exercise the toolkit on
`unittest`-style tests. Its outputs are in `generated/jwcrypto/`, the reading
of its flags and of its undetected deletions in `readings/jwcrypto/`, and its
witness tests in `witnesses/jwcrypto/`. It is reported as a pilot.

**Changes of the toolkit that came from the held-out libraries, the screened
candidates or the pilot.** All were made before this protocol, and none
touched the rule, `reach/targets.py`, which has stayed as fixed on PyJWT.
After every change, PyJWT and the pilot were run again; the outputs in
`generated/` are those of the last run. Before the commit, the toolkit and
this text were reviewed 3 times against the sources of the 6 libraries; the
third review also read this text against the code. A fourth reading compared
the texts of this folder with the code and with the outputs for PyJWT and
the pilot. The rows marked "review" come from those readings.

| Change | What showed the need |
|---|---|
| A message given by keyword is read as the message | `oauthlib` |
| Check identifiers start with the module path | module names that repeat within 1 package |
| The last definition of a duplicated test name is the one that counts | a general safeguard; no subject defines a test name 2 times |
| A case of an included block that raises no rejection class is left out and counted | an exception class of the same name in 2 packages (`authlib`, `joserfc`) |
| Literal keyword arguments are stored as values | `checks.json` differed between 2 runs on `oauthlib` and `authlib` |
| A byte-order mark at the start of a file is accepted | `msal`, in the recount |
| `verify` imports a namespace package | `google` |
| The summary line of pytest is parsed with warnings and skips | suite runs of the libraries |
| The whole-suite runs, and the time limit with 1 repeat | design, before any deletion |
| The records are packed into 1 archive that the analysis can read | design |
| Test files inside the package are not subject files | pilot |
| The determinism sentinel ignores message texts | pilot: a message holds the time of the run |
| Fired checks are recorded, and checks that fire and never decide are deleted too | pilot: a handler replaces the exception of the check a test describes |
| For each case with a target, the case's own test on the copy without the target | pilot: 3 of its 4 flags are tests whose target fires |
| For each deletion, what fires in place of the deleted check, and a table of the deletions that the whole suite does not detect (`undetected.csv`) | pilot: the whole suite misses 7 deletions |
| The `witness` step: a new test is run on the unmodified copy and on the copy without 1 check | pilot: 4 of those 7 deletions change what the library accepts |
| The deletions that break an inclusion between oracles are counted | design |
| `reach/report.py`: the subjects side by side, and the 5 expectations | design |
| Class expressions are resolved through the imports of their module, and a label carries the module where the bare name is not unique or is the name of a built-in | review: classes of 1 name in 2 modules of `oauthlib` and of `authlib`, and in the 2 packages `authlib` and `joserfc`; package classes named like built-ins in `google-auth` and, in the recount, in `pynacl` |
| A built-in class that inherits from a built-in rejection base is a rejection class; a class from outside the package is not | review: the base of `google-auth` is a built-in |
| Every definition of a function name is kept (`~k`) | review: PyJWT defines `to_jwk` with `@overload` stubs |
| At run time, a rejection class is known by the module and the qualified name of its base | review: an exception class of the same name in 2 packages |
| A firing needs the raise instruction itself; firings in other threads are named; the depth of a block is counted per thread | review of the recorder |
| Failed subtests are counted, with what stopped each of them | review: `oauthlib` and `joserfc` use `subTest` |
| A test collected through an import is deselected, test by test, and a copy that stays is listed | review: test files of `oauthlib` import test classes from other test files |
| The deleted checks are those that fire in the cases of the study, with sentinel 7 | review |
| The fourth outcome: the target fires and no check decides | review |
| The status of a case: a skip is missing, a failed assertion in the setup is withheld, missing cases are not counted | review |
| The time limit of a whole-suite run holds for all the suite runs of a copy together | review: `authlib` has 5 suite runs |
| The `deletions` step removes the records of an earlier run, and `pack` takes only the records the steps name | review |
| Every pytest call refuses and counts outside connections | the offline check: tests of `google-auth` look up host names |
| E5 by the share of class-only blocks, and "not applicable" | review of this text |
| The expected baseline failures are read from the reports of the run and deselected by their exact identifiers; the run goes on past a file it cannot collect | review: a deselection by prefix also drops a test whose identifier starts with that of a failing test |
| Every repeated run, and the second unmodified whole-suite run, gets a fresh copy | review |
| A whole-suite run of which a pytest call leaves no result file is repeated 1 time, and then counts as detected | review |
| `verify` refuses a clone with untracked or ignored files in the copied paths, and an environment that differs from `requirements.txt` | review |
| A witness file holds only when a test fails on the copy without the check, and the message of the failure is recorded | review: a test that is skipped does not pass either |
| A library in which a sentinel does not hold gets no verdict; sentinel 2 also asks that the tests deselected are the expected baseline failures, and sentinel 3 needs the records of the deletion runs | review |
| The cases not counted in pinning are counted by reason, and the summary lists the runs repeated and the runs without a record | review |
| `verify` asks for CPython, not for the version number alone; `pack` packs the other records when the control copy gave no record 2 times, and sentinel 1 names that reason | review of this text |
| 4 libraries, and no replacement | the 2 readings of the rejection base of `google-auth` |

## 6. Order of execution

1. This file, the toolkit, its tests, the definitions of the subjects, the
   selection record and the outputs for PyJWT and the pilot are committed in
   1 commit. A text that names the commit is time-stamped by 2 authorities,
   and the tokens are committed.
2. `reach/run.py targets` is run for the 4 libraries. The 4 `targets.json`
   files are committed, and that commit is time-stamped the same way, before
   the next step.
3. For each library, in rank order: `verify`, `baseline`, `deletions`,
   `whole-baseline`, `whole-deletions`, `pack`, then `reach/analyse.py`. The
   outputs go to `generated/<name>/`.
4. Every flag is read against the source of the test and of the 2 checks, and
   put in 1 class with a reason, in `readings/<name>/FLAGS.md`:
   **A** the test does not reach its target;
   **B** the target fires and a handler replaces its exception;
   **C** the target the rule assigned is not the check the test describes;
   **D** cannot be decided from the sources.
   The classes are tried in the order C, A, B, D, and a flag gets the first
   that fits. The counts of section 4 stay mechanical; the classes are a
   reading and are reported as one.
5. Every deletion that the whole suite does not detect is described in
   `readings/<name>/UNDETECTED.md`: the cases in which the check fires, what
   rejects their inputs after the deletion (from
   `generated/<name>/undetected.csv`), and whether some input that the check
   rejects is accepted without it. Where such an input is found, a witness
   test is written in `witnesses/<name>/` and the `witness` step runs it on
   the unmodified copy and on the copy without the check; `pack` and
   `reach/analyse.py` are then run again, which changes no other count. A
   witness file *holds* when every test of it passes on the unmodified copy
   and at least 1 of them fails on the copy without the check. A witness
   test is written to fail only when the library accepts the input, and the
   recorded message of the failure is read to confirm that it did. A witness
   file that holds then shows that the deletion changes what the library
   accepts. An attempt that does not hold, or the absence of a witness test,
   shows nothing: it is reported as "no input found".
6. `reach/report.py` puts the subjects side by side and states each of the 5
   expectations for each library (`generated/REPORT.md`).
7. Every reported count is recomputed from the deposited records by a second
   script, written from this protocol without sight of `reach/analyse.py`,
   `reach/report.py` and `reach/study.py`. Disagreements are listed. Where
   the 2 scripts disagree, the count that follows section 4 stands and the
   other script is corrected; a correction of `reach/analyse.py` is a
   deviation. Where section 4 does not decide, both counts are reported.

**Deviations.** A *defect* of the toolkit is a crash, or a contradiction
between the code and a definition of section 4. A defect found during the run
is fixed and listed in `DEVIATIONS.md` with its date, the reason and the
files changed. The outputs and the verdicts obtained before the fix are
deposited beside the new ones, marked as superseded; the outputs after the
last fix are the result. PyJWT and the pilot are then run again, and
any change of their outputs is listed. The library in hand is run again from
`baseline`, and so is every library already run whose records the fix can
change. `targets.json` is not computed again unless the defect is in the
inputs of the rule; then both versions are deposited. The rule itself does
not change. A change of `reach/analyse.py` or of `reach/report.py` after the
protocol commit is a deviation of the same kind. Any other departure from
this file is listed in `DEVIATIONS.md` too.

## 7. What is reported

Per library, with PyJWT in package scope and the pilot beside them, and with
the note of section 3 on the row of `google-auth`:

- checks, reachable checks, deciding checks, checks that fire and never
  decide; blocks, included blocks, class-only blocks; cases, cases left out;
- Q1: cases with a target by tier, their 4 outcomes, and flags by class;
- Q2: deletions not detected under each oracle, for deciding checks and for
  checks that fire and never decide, with the withheld-as-failing columns,
  the deletions that exceeded the time limit, the runs that were repeated
  and the runs that ended without a record or a result; for the deletions
  that the whole suite does not detect, the witness files, each as holds or
  does not hold;
- Q3: pinning by kind of block, with the cases not counted, by reason;
- the 5 expectations, each as held, not held, not applicable, not stated or
  no verdict;
- the expected baseline failures, the test files not collected, the tests
  deselected as copies and the copies that stay, the cases of nested blocks,
  the cases with a firing in another thread, and the refused connection
  attempts;
- the 7 sentinels, the deviations, and the result of the second computation.

No statistical test is applied, no count is pooled across libraries, and no
rate is reported as an estimate for verifiers in general. The verdicts on the
expectations are tallied per library, never across libraries.

## 8. Limits known in advance

- Matching is by name: entry points and calls are resolved by name, without
  types. A check can be marked reachable that no entry point runs, and the
  reverse. Classes are resolved through imports, without running the code: a
  class reached through a variable or a call is known only by a name that is
  unique in the package.
- Only raise statements that construct a rejection class are checks. A
  rejection made by returning a value, by a bare `raise`, by re-raising a
  variable or inside compiled code is not a check and is not deleted.
- A raise statement outside the function definitions that section 4 reads is
  not listed at all: at the top level of a module, directly in the body of a
  class outside its methods, or in a function or a class defined in a handler
  of a `try` statement, in a loop, in an `async with` or in a `match`
  statement. The subject files of the 6 libraries hold 7 such statements, 1
  in `jwcrypto`, 5 in `google-auth` and 1 in `oauthlib`: 6 at the top level
  of a module and 1 in a method of a class defined in a handler. Each
  raises `ImportError` or `RuntimeError`, which is no rejection class of its
  library.
- Module bindings in a loop or a `match` statement are not read (section 4).
  No subject file of the 6 libraries binds a class, an import or an alias at
  the top level of a module under a `with` statement, a loop or a `match`
  statement.
- A block in an `async with`, and a `pytest.raises` object that is made in 1
  place and entered in another, are not blocks. The test directories of the
  6 libraries hold no block of the first kind and 1 object of the second
  kind, in a test of PyJWT that calls no entry point.
- A firing is matched by the line of the raise statement and the bare name of
  the class. At run time a rejection class is known by the module and the
  qualified name of its base; a class whose 2 names were reassigned after its
  definition would not be recognised. No file of the 6 libraries makes such
  an assignment.
- The recorder wraps `pytest.raises` and the `assertRaises` family. It does
  not wrap `pytest.RaisesGroup` or `pytest.RaisesExc`; no file of the 6
  libraries uses them.
- 1 deletion variant: the raise statements become `pass`. Code after the
  deleted statement runs, which no other variant was tried against here.
- The rule can assign a wrong target. A wrong target that differs from the
  deciding check shows as a flag and is read. A wrong target that equals the
  deciding check is not seen at all.
- A flag is a statement about the raise site. The pilot showed flags whose
  target fires and is needed by the test; the 4 outcomes of section 4
  separate them.
- The reading of flags and of undetected deletions is done by reading
  sources. It is reported apart from the counts.
- With outside connections refused, a test that needs another machine would
  fail at baseline and be deselected. The offline check found no such test:
  every test of the 4 libraries has the same outcome with and without the
  refusal. The refusal covers connections and lookups through
  `socket.getaddrinfo`. A lookup through `socket.gethostbyname` and its
  variants, and a datagram sent without a connection, are neither refused
  nor counted.
- 4 libraries, 1 language, 1 family of protocols, chosen by download rank and
  a keyword filter (`SELECTION.md`, section 8). 1 of the 4, `google-auth`, is
  a subject only under 1 of the 2 readings of its rejection base (section 3).
- 2 of the 4 are not independent. `authlib` 1.9.5 requires `joserfc`, and its
  environment holds `joserfc` 1.8.0, the release that is the fourth subject.
  The included blocks of `authlib` are all in the tests of `authlib.jose`, a
  module that the release marks as deprecated in favour of `joserfc`. The
  subject `authlib` counts the checks of the package `authlib` alone.
- The time stamps show that a text naming the protocol commit existed at
  their time. They cannot show that nothing was run before; the statement of
  section 5 rests on this record.
