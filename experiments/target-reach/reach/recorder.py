"""pytest plugin that records every negative-test block of a run.

Loaded with `-p reach.recorder` (the runner puts the toolkit on PYTHONPATH).
Settings come from the environment:

    REACH_SUBJECT  subject.json
    REACH_CHECKS   checks.json written by `run.py define`
    REACH_BLOCKS   blocks.json written by `run.py define`
    REACH_OUT      the JSON record to write
    REACH_ROOT     the directory that holds the copied subject
    REACH_SUITE    optional: suite.json of the run without the recorder

It wraps `pytest.raises` and `unittest.TestCase.assertRaises`,
`assertRaisesRegex` and `assertRaisesRegexp` (context-manager and callable
forms). At a block's exit it records the exception, for included blocks the
raise site, and what the block's own check decides (`check_result`). While a
block is open it also records every check that fires: a raise statement of the
check raises an exception of the check's class, whether or not a handler
catches it later (`fired`, in the order of the first firing; `sys.monitoring`,
Python 3.12 or later; `null` when that is not available). Then the
test goes on in every case: an exception that the real check would let
through is swallowed, and a failure of the real check is recorded and not
raised. The later blocks of the test are therefore observed even when an
earlier block fails, which is what an oracle weaker than the test's own needs.
The test's real outcome is not lost: a test with a failed block is recorded
in `failed_blocks` and counts as failed in the analysis.

Exceptions that are not `Exception` subclasses (KeyboardInterrupt, pytest's
own outcomes such as skip and fail) are never swallowed, and outside a test
(collection, import) every block behaves as it does without the plugin.

A firing is a RAISE event whose instruction is `RAISE_VARARGS`: an exception
that only passes through a raise statement of a check (raised by a call in the
statement's arguments, on any of its lines) is not a firing of that check. The
class of the exception is compared with the class of the check by bare name
(`class_name` in checks.json).
`sys.monitoring` events are process-wide, so a check that fires in another
thread while a block is open counts too; `fired_other_threads` lists the checks
of `fired` whose every firing during the block happened in a thread other than
the thread that entered the block.

Nested blocks: a block opened while another block is open records its own
case, and the firings inside it count in every open block. The inner block
swallows its exception, so the outer block sees none (`raised` false; pytest's
own check of the outer block fails, and the test counts as failed). `depth` is
the number of blocks that the entering thread holds open when the case's block
is entered, itself included (1 for a block that is not nested).

Subtests (`unittest.TestCase.subTest` and the `subtests` fixture) report under
the test's node id with `when == "call"`; their reports are counted in
`subtests_failed` (the failed ones) and never replace the `setup`, `call` or
`teardown` entry of the test, which come from the test's own reports: the
objects that `pytest_runtest_makereport` returned for the test's phases. A
block inside a subtest is recorded as a case of the test. For every failed
subtest report, `subtest_stops` holds what stopped the subtest ({"stop",
"stop_is_assertion"}): pytest passes the subtest's exception to
`pytest_runtest_makereport` and then logs the subtest report, in the same
thread, so the entry comes from the last call of that hook in the thread; both
values are `null` when that call did not fail.

The tests named in the list `failures` of the file REACH_SUITE (the tests
that failed in the run without the recorder) are deselected first, by their
exact node id. The record lists, in `deselected`, those that were found among
the collected tests.

A test that a test module imports from another test module is collected again
under the importing module. Such a copy is deselected when the session then
holds the same test in the module that defines it: the same method name,
parameters included, of the same class object, or the same parameters of the
same function object. The record lists the deselected copies in
`collected_again` and the copies that stay, because the session does not hold
the test in the defining module, in `imported_kept`. A subclass defined in the
importing module is another class, and its tests stay.

When checks.json has the top-level key `rejection_bases` (a list of
{"name", "kind", "module", "qualname"}), a class is a rejection class when its
MRO holds a class with the same `__module__` and `__qualname__` as 1 of them;
without the key, a class of the package or a built-in class whose bare name is
a rejection base of subject.json. The comparison is by these 2 names: a class
whose `__module__` or `__qualname__` was assigned after its definition is not
recognised.
"""

from __future__ import annotations

import dis
import json
import os
import re
import sys
import threading
import unittest
from pathlib import Path

import pytest
from _pytest.outcomes import Failed

MESSAGE_LIMIT = 500
ADDRESS = re.compile(r" at 0x[0-9a-fA-F]+")  # object addresses differ between runs
_REAL_RAISES = pytest.raises
_REAL_UNITTEST = {name: getattr(unittest.TestCase, name)
                  for name in ("assertRaises", "assertRaisesRegex", "assertRaisesRegexp")
                  if hasattr(unittest.TestCase, name)}
RAISE_VARARGS = dis.opmap["RAISE_VARARGS"]
PHASES = ("setup", "call", "teardown")


def qualname(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


class OpenBlock:
    """The checks fired while 1 block is open, and the thread that entered it."""

    def __init__(self, depth: int) -> None:
        self.fired: list[str] = []          # in the order of the first firing
        self.same_thread: set[str] = set()  # checks fired at least 1 time in the entering thread
        self.thread = threading.get_ident()
        self.depth = depth

    def other_threads(self) -> list[str]:
        return [c for c in self.fired if c not in self.same_thread]


class Recorder:
    def __init__(self) -> None:
        env = os.environ
        self.subject = json.loads(Path(env["REACH_SUBJECT"]).read_text(encoding="utf-8"))
        checks = json.loads(Path(env["REACH_CHECKS"]).read_text(encoding="utf-8"))
        blocks = json.loads(Path(env["REACH_BLOCKS"]).read_text(encoding="utf-8"))
        self.out = Path(env["REACH_OUT"])
        self.root = os.path.realpath(env["REACH_ROOT"])
        src = self.subject.get("source_root", ".")
        self.src_root = os.path.realpath(os.path.join(self.root, src))
        self.pkg_dir = os.path.realpath(os.path.join(self.src_root, *self.subject["package"].split(".")))
        self.bases = set(self.subject["rejection_bases"])
        named = checks.get("rejection_bases")
        self.base_ids: set[tuple[str, str]] | None = (
            None if named is None else {(b["module"], b["qualname"]) for b in named})
        self.blocks: dict[tuple[str, int], dict] = {}
        for b in blocks["blocks"]:
            for line in range(b["header_span"][0], b["header_span"][1] + 1):
                self.blocks.setdefault((b["file"], line), b)
        self.lines: dict[str, dict[int, dict]] = {}
        self.check_class: dict[str, str] = {}
        for c in checks["checks"]:
            self.check_class[c["id"]] = c.get("class_name", c["class"])
            for (a, z) in c["lines"]:
                for line in range(a, z + 1):
                    self.lines.setdefault(c["file"], {})[line] = c["id"]
        self.open_blocks: list[OpenBlock] = []
        self.monitored: dict[str, str | None] = {}  # code file name -> path relative to the source root
        self.tool_id: int | None = None
        self.fired_recorded = False
        self.other_lines: dict[str, set[int]] = {}
        for o in checks["other_raises"]:
            for line in range(o["line"], o["end_line"] + 1):
                self.other_lines.setdefault(o["file"], set()).add(line)
        self.cases: list[dict] = []
        self.unmatched: list[dict] = []
        self.tests: dict[str, dict] = {}
        self.collect_errors: list[dict] = []
        self.current: str | None = None
        self.counter: dict[tuple[str, str], int] = {}
        self.sources: dict[str, list[str]] = {}
        # the report objects that pytest_runtest_makereport returned for the current
        # test, by id, with the phase entry they give; a reference is kept so that an
        # id is not reused while the test runs
        self.made: dict[int, tuple[object, dict]] = {}
        # thread -> the phase entry of the last pytest_runtest_makereport call in it
        self.last_made: dict[int, dict] = {}
        self.collected_again: list[dict] = []
        self.imported_kept: list[dict] = []
        # the tests that failed in the run without the recorder, and those of them deselected here
        self.expected_failures: set[str] = set()
        suite = env.get("REACH_SUITE")
        if suite and os.path.exists(suite):
            self.expected_failures = set(json.loads(Path(suite).read_text(encoding="utf-8"))["failures"])
        self.deselected: list[str] = []

    def rel(self, filename: str) -> str:
        path = os.path.realpath(filename)
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def source_line(self, path: str, line: int) -> str:
        if path not in self.sources:
            try:
                self.sources[path] = Path(path).read_text(encoding="utf-8-sig").splitlines()
            except OSError:
                self.sources[path] = []
        lines = self.sources[path]
        return lines[line - 1].strip() if 0 < line <= len(lines) else ""

    def site(self, tb) -> dict | None:
        inner = None
        while tb is not None:
            path = os.path.realpath(tb.tb_frame.f_code.co_filename)
            if path.startswith(self.pkg_dir + os.sep):
                inner = (path, tb.tb_frame.f_code, tb.tb_lineno)
            tb = tb.tb_next
        if inner is None:
            return None
        path, code, line = inner
        rel = os.path.relpath(path, self.src_root).replace(os.sep, "/")
        check = self.lines.get(rel, {}).get(line)
        return {"file": rel, "function": code.co_qualname.replace(".<locals>", ""),
                "line": line, "check": check,
                "kind": "check" if check else ("other raise" if line in self.other_lines.get(rel, set())
                                               else "outside checks"),
                "source": None if check else self.source_line(path, line)}

    # -- the checks that fire while a block is open ------------------------------------

    def start_monitoring(self) -> None:
        mon = getattr(sys, "monitoring", None)
        if mon is None:
            return
        for tool_id in (4, 3):  # ids that no standard tool claims
            try:
                mon.use_tool_id(tool_id, "reach")
            except ValueError:
                continue
            self.tool_id = tool_id
            self.fired_recorded = True
            mon.register_callback(tool_id, mon.events.RAISE, self.on_raise)
            mon.set_events(tool_id, mon.events.RAISE)
            return

    def stop_monitoring(self) -> None:
        if self.tool_id is not None:
            mon = sys.monitoring
            mon.set_events(self.tool_id, 0)
            mon.register_callback(self.tool_id, mon.events.RAISE, None)
            mon.free_tool_id(self.tool_id)
            self.tool_id = None

    def on_raise(self, code, offset, exception) -> None:
        """An exception is raised in, or passes through, a frame of `code`. It counts
        as a firing when the instruction at `offset` is `RAISE_VARARGS`, its line is a
        line of a raise statement of a check and the exception has the check's class.
        An exception that only passes through a frame has the offset of the call it
        came from, so it is left out even on a line of the check."""
        if not self.open_blocks:
            return
        name = code.co_filename
        if name not in self.monitored:
            path = os.path.realpath(name)
            self.monitored[name] = (os.path.relpath(path, self.src_root).replace(os.sep, "/")
                                    if path.startswith(self.pkg_dir + os.sep) else None)
        rel = self.monitored[name]
        if rel is None:
            return
        by_line = self.lines.get(rel)
        if not by_line:
            return
        frame = sys._getframe(1)
        if frame.f_code is not code:
            return
        check = by_line.get(frame.f_lineno)
        if check is None or type(exception).__name__ != self.check_class[check]:
            return
        # co_code is the bytecode without instrumentation; `offset` is in bytes
        if code.co_code[offset] != RAISE_VARARGS:
            return
        thread = threading.get_ident()
        for opened in list(self.open_blocks):
            if check not in opened.fired:
                opened.fired.append(check)
            if thread == opened.thread:
                opened.same_thread.add(check)

    def is_rejection(self, et) -> bool:
        """With `rejection_bases` in checks.json: a class of that list, by module and
        qualified name, is in the MRO. Without it: a class of the package, or a
        built-in class, whose name is a rejection base is in the MRO."""
        if self.base_ids is not None:
            return any((c.__module__, c.__qualname__) in self.base_ids for c in et.__mro__)
        pkg = self.subject["package"]
        return any(c.__name__ in self.bases
                   and (c.__module__ == pkg or c.__module__.startswith(pkg + ".") or c.__module__ == "builtins")
                   for c in et.__mro__)

    def observe(self, filename: str, lineno: int, api: str, form: str, et, ev, tb,
                opened: OpenBlock | None) -> dict:
        rel = self.rel(filename)
        block = self.blocks.get((rel, lineno))
        rec: dict = {"test": self.current, "block": block["key"] if block else None,
                     "where": f"{rel}:{lineno}", "api": api, "form": form,
                     "included": bool(block and block["included"]),
                     "depth": opened.depth if opened is not None else None}
        if rec["included"]:
            known = self.fired_recorded and opened is not None
            rec["fired"] = list(opened.fired) if known else None
            rec["fired_other_threads"] = opened.other_threads() if known else None
        if block is not None and self.current is not None:
            k = (self.current, block["key"])
            rec["index"] = self.counter.get(k, 0)
            self.counter[k] = rec["index"] + 1
        if et is None:
            rec["raised"] = False
        else:
            rec["raised"] = True
            rec["class"] = qualname(et)
            rec["mro"] = [qualname(c) for c in et.__mro__]
            rec["rejection"] = self.is_rejection(et)
            try:
                msg = str(ev)
            except Exception as e:  # a broken __str__ is an observation too
                msg = f"<str() raised {qualname(type(e))}>"
            rec["message"] = ADDRESS.sub(" at 0x*", msg)[:MESSAGE_LIMIT]
            cause = getattr(ev, "__cause__", None)
            rec["cause"] = qualname(type(cause)) if cause is not None else None
            if rec["included"]:
                rec["site"] = self.site(tb)
        if block is None or self.current is None:
            self.unmatched.append(rec)
        else:
            self.cases.append(rec)
        return rec

    def block_failed(self, rec: dict | None, result: str, filename: str, lineno: int) -> None:
        """A block of the current test failed its own check; the test counts as failed."""
        entry = self.tests.setdefault(self.current, {})
        entry.setdefault("failed_blocks", []).append({
            "block": rec.get("block") if rec else None,
            "index": rec.get("index") if rec else None,
            "where": f"{self.rel(filename)}:{lineno}", "result": result})

    def write(self) -> None:
        cases = sorted(self.cases, key=lambda r: (r["test"], r["block"], r["index"]))
        unmatched = sorted(self.unmatched, key=lambda r: (str(r["test"]), r["where"],
                                                          json.dumps(r, sort_keys=True)))
        tests = [dict(nodeid=k, **v) for k, v in sorted(self.tests.items())]
        data = {"cases": cases, "tests": tests, "unmatched": unmatched,
                "collect_errors": sorted(self.collect_errors, key=lambda r: r["nodeid"]),
                "fired_recorded": self.fired_recorded,
                "collected_again": sorted(self.collected_again, key=lambda r: r["nodeid"]),
                "imported_kept": sorted(self.imported_kept, key=lambda r: r["nodeid"]),
                "deselected": sorted(set(self.deselected))}
        self.out.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.out.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False, default=repr) + "\n",
                       encoding="utf-8")
        tmp.replace(self.out)


RECORDER: Recorder | None = None


class Block:
    """Wraps a real context manager; records at exit, then lets the test go on."""

    def __init__(self, cm, filename: str, lineno: int, api: str, form: str) -> None:
        self.cm, self.filename, self.lineno, self.api, self.form = cm, filename, lineno, api, form
        self.bound = None

    def __enter__(self):
        self.bound = self.cm.__enter__()
        if RECORDER is not None:
            me = threading.get_ident()
            self.opened = OpenBlock(1 + sum(o.thread == me for o in RECORDER.open_blocks))
            RECORDER.open_blocks.append(self.opened)
        return self.bound

    def __exit__(self, et, ev, tb):
        __tracebackhide__ = True
        opened = getattr(self, "opened", None)
        if RECORDER is not None and opened is not None:
            RECORDER.open_blocks[:] = [o for o in RECORDER.open_blocks if o is not opened]
        if RECORDER is None or RECORDER.current is None:
            return self.cm.__exit__(et, ev, tb)  # outside a test: as without the plugin
        if et is not None and not issubclass(et, Exception):
            return self.cm.__exit__(et, ev, tb)  # never swallowed
        rec = None
        try:
            rec = RECORDER.observe(self.filename, self.lineno, self.api, self.form, et, ev, tb, opened)
        except Exception as e:  # a recorder fault is an observation, not a test failure
            RECORDER.unmatched.append({"recorder_error": qualname(type(e)), "where": self.lineno})
        try:
            result, detail = ("accepted", "") if self.cm.__exit__(et, ev, tb) else ("propagated", "")
        except AssertionError as e:
            result, detail = "assertion", str(e)
        except Failed as e:
            result, detail = "failed", str(e)
        except Exception as e:  # the real check itself broke
            result, detail = f"error:{qualname(type(e))}", str(e)
        if rec is not None:
            rec["check_result"] = result
            if detail:
                rec["check_detail"] = ADDRESS.sub(" at 0x*", detail)[:MESSAGE_LIMIT]
        if result != "accepted":
            RECORDER.block_failed(rec, result, self.filename, self.lineno)
        if et is None:
            return False
        # the test goes on: give the bound object what an accepting check gives
        try:
            if self.api == "pytest":
                if self.bound is not None and getattr(self.bound, "_excinfo", None) is None:
                    self.bound.fill_unfilled((et, ev, tb))
            elif not hasattr(self.cm, "exception"):
                self.cm.exception = ev.with_traceback(None)
        except Exception as e:
            RECORDER.unmatched.append({"recorder_error": qualname(type(e)), "where": self.lineno})
        return True


def recording_raises(expected_exception=None, func=None, *args, **kwargs):
    __tracebackhide__ = True
    caller = sys._getframe(1)
    filename, lineno = caller.f_code.co_filename, caller.f_lineno
    if func is None and not args:
        if expected_exception is None:
            return Block(_REAL_RAISES(**kwargs), filename, lineno, "pytest", "with")
        return Block(_REAL_RAISES(expected_exception, **kwargs), filename, lineno, "pytest", "with")
    if not callable(func):  # let pytest produce its own error
        return _REAL_RAISES(expected_exception, func, *args, **kwargs)
    with Block(_REAL_RAISES(expected_exception), filename, lineno, "pytest", "call") as excinfo:
        func(*args, **kwargs)
    return excinfo


def unittest_wrapper(name: str):
    real = _REAL_UNITTEST[name]
    lead = 1 if name.startswith("assertRaisesRegex") else 0

    def wrapper(self, expected_exception, *args, **kwargs):
        __tracebackhide__ = True
        caller = sys._getframe(1)
        filename, lineno = caller.f_code.co_filename, caller.f_lineno
        head, rest = args[:lead], args[lead:]
        if not rest:
            ctx = real(self, expected_exception, *head, **kwargs)
            return Block(ctx, filename, lineno, "unittest", "with")
        ctx = real(self, expected_exception, *head)
        func, fargs = rest[0], rest[1:]
        with Block(ctx, filename, lineno, "unittest", "call"):
            func(*fargs, **kwargs)
        return None

    wrapper.__name__ = name
    return wrapper


def pytest_configure(config) -> None:
    global RECORDER
    RECORDER = Recorder()
    RECORDER.start_monitoring()
    pytest.raises = recording_raises
    for name in _REAL_UNITTEST:
        setattr(unittest.TestCase, name, unittest_wrapper(name))


def pytest_unconfigure(config) -> None:
    if RECORDER is not None:
        RECORDER.stop_monitoring()
    pytest.raises = _REAL_RAISES
    for name, real in _REAL_UNITTEST.items():
        setattr(unittest.TestCase, name, real)


def pytest_collectreport(report) -> None:
    if report.failed and RECORDER is not None:
        RECORDER.collect_errors.append({"nodeid": report.nodeid})


def _module_name(item) -> str | None:
    module = getattr(item, "module", None)
    return getattr(module, "__name__", None)


def _owner(item):
    """The class that owns a test method, or the function of a module-level test."""
    cls = getattr(item, "cls", None)
    if cls is not None:
        return cls
    return getattr(item, "function", None)


def _test_key(item, owner) -> tuple:
    """1 test of its owner: the method name (with its parameters) for a method of
    a class, the parameters for a module-level function."""
    if getattr(item, "cls", None) is not None:
        return (id(owner), item.name)
    spec = getattr(item, "callspec", None)
    return (id(owner), spec.id if spec is not None else "")


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items) -> None:
    """Deselects, by their exact node id, the tests that failed in the run
    without the recorder. Then deselects a test collected again through an
    import: its owner (class or function) is defined in another module, and the
    session holds the same test of the same owner object in the module that
    defines it. The hook runs after pytest's own deselection and the copies are
    looked at last, so a copy stays when its test in the defining module was
    deselected or not collected."""
    if RECORDER is None:
        return
    expected = RECORDER.expected_failures
    failing = [item for item in items if item.nodeid in expected]
    if failing:
        RECORDER.deselected += [item.nodeid for item in failing]
        config.hook.pytest_deselected(items=failing)
        items[:] = [item for item in items if item.nodeid not in expected]
    at_home: set[tuple] = set()
    owners = []
    for item in items:
        owner = _owner(item)
        home = getattr(owner, "__module__", None)
        owners.append((owner, home))
        if owner is not None and home is not None and home == _module_name(item):
            at_home.add(_test_key(item, owner))
    keep, again = [], []
    for item, (owner, home) in zip(items, owners):
        if owner is not None and home is not None and home != _module_name(item):
            if _test_key(item, owner) in at_home:
                again.append(item)
                RECORDER.collected_again.append({"nodeid": item.nodeid, "defined_in": home})
                continue
            RECORDER.imported_kept.append({"nodeid": item.nodeid, "defined_in": home})
        keep.append(item)
    if again:
        config.hook.pytest_deselected(items=again)
        items[:] = keep


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if RECORDER is not None:
        RECORDER.current = item.nodeid
        entry = RECORDER.tests.setdefault(item.nodeid, {})
        entry["file"] = item.path.relative_to(RECORDER.root).as_posix() \
            if str(item.path).startswith(RECORDER.root) else item.path.name
        entry["function"] = getattr(item, "originalname", item.name)
        entry.setdefault("subtests_failed", 0)
    try:
        return (yield)
    finally:
        if RECORDER is not None:
            RECORDER.current = None
            RECORDER.made.clear()
            RECORDER.last_made.clear()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """Notes what stopped the phase. A subtest calls this hook too (when "call"),
    then logs a new report built from the result, so the note is kept by the
    identity of the report and used only when that same object is logged."""
    rep = yield
    if RECORDER is not None:
        stop, assertion = None, None
        if call.excinfo is not None:
            stop = qualname(call.excinfo.type)
            assertion = issubclass(call.excinfo.type, (AssertionError, Failed))
        phase = {"outcome": rep.outcome, "stop": stop, "stop_is_assertion": assertion}
        if hasattr(rep, "wasxfail"):
            phase["xfail"] = True
        RECORDER.made[id(rep)] = (rep, phase)
        RECORDER.last_made[threading.get_ident()] = phase
    return rep


@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report) -> None:
    """Runs after the terminal reporter, which may turn the outcome of a test with
    failed subtests into "failed"; the entry keeps the outcome pytest reports."""
    if RECORDER is None or report.when not in PHASES:
        return
    entry = RECORDER.tests.setdefault(report.nodeid, {})
    made = RECORDER.made.get(id(report))
    if made is not None and made[0] is report:
        phase = dict(made[1])
    elif getattr(report, "context", None) is not None:
        # a subtest report: a new object with the subtest's context (pytest's
        # SubtestReport, or SubTestReport of the pytest-subtests plugin)
        entry.setdefault("subtests_failed", 0)
        if report.failed:
            entry["subtests_failed"] += 1
            last = RECORDER.last_made.get(threading.get_ident())
            known = last is not None and last["outcome"] == "failed"
            entry.setdefault("subtest_stops", []).append(
                {"stop": last["stop"] if known else None,
                 "stop_is_assertion": last["stop_is_assertion"] if known else None})
        return
    else:
        phase = {"outcome": None, "stop": None, "stop_is_assertion": None}
    phase["outcome"] = report.outcome
    entry[report.when] = phase
    entry.setdefault("subtests_failed", 0)


def pytest_sessionfinish(session, exitstatus) -> None:
    if RECORDER is not None:
        RECORDER.write()
