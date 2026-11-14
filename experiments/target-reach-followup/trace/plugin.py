"""pytest plugin that records, for every function of the subject that starts,
the entry-point names on the call stack of the same thread at that moment.

Loaded by `trace_run.py` (as the module `reach_trace`, from a folder that
holds no other module) in the whole-suite runs on an unmodified copy, together
with the offline module of the toolkit and without its recorder.

Environment:

    TRACE_ROOT     the source root of the copy (the directory that the "file"
                   fields of checks.json are relative to)
    TRACE_FILES    a JSON file: {"files": [the subject and observed files,
                   relative to TRACE_ROOT], "entry_points": [names]}
    TRACE_OUT      the JSON file written when pytest ends (pytest_unconfigure)

Definitions:

- A *function code* is a code object compiled from a function body: a `def`,
  an `async def`, a lambda or a generator expression. Module bodies and class
  bodies are not function codes.
- A code *belongs to the subject* when its file is 1 of TRACE_FILES.
- A frame is an *entry-point frame* when its code is a function code that
  belongs to the subject and whose name (`co_name`) is an entry-point name.
- A function *starts* at the interpreter's `PY_START` event of
  `sys.monitoring`: the first instruction of a call, or the first `next()` /
  `send()` of a generator or coroutine. Resuming a generator or coroutine
  after a `yield` or an `await` is not a start.
- At each start of a function code of the subject, the plugin walks the
  frame chain of the current thread from the new frame outward (`f_back`)
  and takes the names of the entry-point frames on it. The new frame is on
  the chain, so a function named like an entry point runs under its own name.

What is kept per function code (keyed by file, first line, name and
qualified name): the number of starts, the number of starts under no
entry-point frame, the union of the entry-point names seen, the number of
starts in a thread other than the main thread, up to 5 test ids of starts
under no entry-point frame, and for each entry-point name the test id of the
first start under it. The test id is the node id that pytest gives its
`pytest_runtest_logstart` hook, and the empty text outside a test.

The plugin claims its own `sys.monitoring` tool id, 5 or else 2 (the
recorder of the toolkit takes 4 or 3), and listens to `PY_START` only. For a
code that does not belong to the subject, or is no function code, the
callback returns `DISABLE`, so that the interpreter stops reporting that code.

The callback calls nothing that a test can replace. It reads no environment
variable and calls no function of `os`: the paths of the subject files are
spelled out when the plugin starts (as given, absolute and with links
resolved), and a file name is looked up among them as it stands. The names
that were not found are kept; when pytest ends, the document lists those that
resolve to a subject file (`subject_files_under_another_name`), since the
starts of their codes were not recorded. `threading.get_ident` and
`sys._getframe` are bound when the module is imported.
"""

from __future__ import annotations

import json
import os
import sys
import threading

CO_OPTIMIZED = 0x0001
CO_NEWLOCALS = 0x0002
TOOL_IDS = (5, 2)
KEEP_TESTS = 5

_get_ident = threading.get_ident
_getframe = sys._getframe


class Tracer:
    def __init__(self, root: str, files: list[str], entry_points: list[str]) -> None:
        self.root = os.path.realpath(root)
        self.real = {os.path.realpath(os.path.join(self.root, f)): f for f in files}
        self.files: dict[str, str] = {}              # every spelling of a subject path -> subject file
        for f in files:
            for base in (root, self.root):
                path = os.path.join(base, f)
                for spelling in (path, os.path.abspath(path), os.path.realpath(path)):
                    self.files[spelling] = f
        self.other_names: set[str] = set()           # file names that are no spelling above
        self.test = ""                               # node id of the running test (the hooks below)
        self.disable = sys.monitoring.DISABLE
        self.entry = frozenset(entry_points)
        self.rel_of: dict[str, str | None] = {}      # co_filename -> subject file or None
        self.frame_name: dict[object, str | None] = {}  # code -> entry-point name or None
        self.data: dict[tuple, dict] = {}            # code key -> counters
        self.key_of: dict[object, tuple] = {}        # code -> code key
        self.tool_id: int | None = None
        self.main_ident = threading.main_thread().ident
        self.events = 0

    # -- classification -----------------------------------------------------------
    def subject_file(self, filename: str) -> str | None:
        rel = self.rel_of.get(filename, False)
        if rel is False:
            rel = self.files.get(filename)
            if rel is None:
                self.other_names.add(filename)
            self.rel_of[filename] = rel
        return rel

    @staticmethod
    def is_function(code) -> bool:
        return (code.co_flags & CO_OPTIMIZED) and (code.co_flags & CO_NEWLOCALS)

    def entry_name(self, code) -> str | None:
        name = self.frame_name.get(code, False)
        if name is False:
            name = None
            if (code.co_name in self.entry and self.is_function(code)
                    and self.subject_file(code.co_filename) is not None):
                name = code.co_name
            self.frame_name[code] = name
        return name

    # -- the callback -------------------------------------------------------------
    def on_start(self, code, offset):
        key = self.key_of.get(code)
        if key is None:
            rel = self.subject_file(code.co_filename)
            if rel is None or not self.is_function(code):
                return self.disable
            key = (rel, code.co_firstlineno, code.co_name, code.co_qualname)
            self.key_of[code] = key
        self.events += 1
        names = set()
        frame = _getframe(1)  # the frame of the function that starts
        while frame is not None:
            name = self.entry_name(frame.f_code)
            if name is not None:
                names.add(name)
            frame = frame.f_back
        d = self.data.get(key)
        if d is None:
            d = self.data.setdefault(key, {"starts": 0, "starts_under_none": 0, "names": set(),
                                           "starts_other_threads": 0, "tests_under_none": [],
                                           "first_test": {}})
        d["starts"] += 1
        if names:
            new = names - d["names"]
            if new:
                test = self.test
                for n in new:
                    d["first_test"][n] = test
                d["names"] |= names
        else:
            d["starts_under_none"] += 1
            if len(d["tests_under_none"]) < KEEP_TESTS:
                test = self.test
                if test not in d["tests_under_none"]:
                    d["tests_under_none"].append(test)
        if _get_ident() != self.main_ident:
            d["starts_other_threads"] += 1
        return None

    # -- start and stop -----------------------------------------------------------
    def start(self) -> None:
        mon = sys.monitoring
        for tool_id in TOOL_IDS:
            try:
                mon.use_tool_id(tool_id, "reach-trace")
            except ValueError:
                continue
            self.tool_id = tool_id
            break
        if self.tool_id is None:
            raise RuntimeError("reach-trace: no free sys.monitoring tool id among %r" % (TOOL_IDS,))
        mon.register_callback(self.tool_id, mon.events.PY_START, self.on_start)
        mon.set_events(self.tool_id, mon.events.PY_START)

    def stop(self) -> None:
        if self.tool_id is None:
            return
        mon = sys.monitoring
        mon.set_events(self.tool_id, 0)
        mon.register_callback(self.tool_id, mon.events.PY_START, None)
        mon.free_tool_id(self.tool_id)

    def document(self) -> dict:
        codes = []
        for (rel, line, name, qual), d in sorted(self.data.items()):
            codes.append({"file": rel, "first_line": line, "name": name, "qualname": qual,
                          "starts": d["starts"], "starts_under_none": d["starts_under_none"],
                          "entry_points": sorted(d["names"]),
                          "starts_other_threads": d["starts_other_threads"],
                          "tests_under_none": d["tests_under_none"],
                          "first_test_per_entry_point": dict(sorted(d["first_test"].items()))})
        missed = sorted(n for n in self.other_names
                        if n and not n.startswith("<") and os.path.realpath(n) in self.real)
        return {"tool_id": self.tool_id, "events": self.events, "entry_points": sorted(self.entry),
                "codes": codes, "subject_files_under_another_name": missed}


TRACER: Tracer | None = None


def pytest_configure(config) -> None:
    global TRACER
    if os.environ.get("TRACE_OUT") is None:
        return
    with open(os.environ["TRACE_FILES"], encoding="utf-8") as handle:
        spec = json.load(handle)
    TRACER = Tracer(os.environ["TRACE_ROOT"], spec["files"], spec["entry_points"])
    TRACER.start()


def pytest_runtest_logstart(nodeid, location) -> None:
    if TRACER is not None:
        TRACER.test = nodeid


def pytest_runtest_logfinish(nodeid, location) -> None:
    if TRACER is not None:
        TRACER.test = ""


def pytest_unconfigure(config) -> None:
    global TRACER
    if TRACER is None:
        return
    TRACER.stop()
    with open(os.environ["TRACE_OUT"], "w", encoding="utf-8") as handle:
        json.dump(TRACER.document(), handle, indent=1, sort_keys=True)
        handle.write("\n")
    TRACER = None
