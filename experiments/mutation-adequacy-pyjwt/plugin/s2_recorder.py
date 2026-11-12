"""pytest plugin that records what each `pytest.raises` block does.

See ../PROTOCOL.md, "Observation". Loaded with `-p s2_recorder`, with this
folder on PYTHONPATH. Settings come from the environment:

    S2_CASES    cases.json            (required)
    S2_CHECKS   checks.json           (required)
    S2_OUT      JSON file to write    (required)
    S2_PACKAGE  package under test    (default: jwt)
    S2_SELECT   "cases" runs only the tests that contain an included block
                (default); "all" runs every test
    S2_MUTANT   mutmut mutant to activate (for example
                jwt.api_jws.xǁPyJWSǁ_load__mutmut_7); "" activates none

A mutant is activated when collection has finished and every module of the
package has been imported, as mutmut 3.8.1 does: its forked children inherit
the package and the test modules that its in-process runs imported with no
mutant active. Code that runs at import time therefore runs unmutated.
`MUTANT_UNDER_TEST` must not be set when the run starts.

The plugin replaces `pytest.raises` with a wrapper around pytest's own context
manager. The wrapper records the block's exception, its raise site and the
result of pytest's own check, then lets the test continue whatever the block
did. It never suppresses an exception outside `Exception`.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import time
from pathlib import Path

import pytest
from _pytest.outcomes import Failed

_REAL_RAISES = pytest.raises
MANGLED_METHOD = re.compile(r"^xǁ(?P<cls>[^ǁ]+)ǁ(?P<name>.+)__mutmut_(?P<variant>orig|\d+)$")
MANGLED_FUNCTION = re.compile(r"^x_(?P<name>.+)__mutmut_(?P<variant>orig|\d+)$")


def demangle(code) -> tuple[str, str | None]:
    """(function as named in the original source, mutmut variant or None)."""
    m = MANGLED_METHOD.match(code.co_name)
    if m:
        return f"{m['cls']}.{m['name']}", m["variant"]
    m = MANGLED_FUNCTION.match(code.co_name)
    if m:
        return m["name"], m["variant"]
    return code.co_qualname.replace(".<locals>", ""), None


def qualname(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


class SourceIndex:
    """Parses each executed file once and answers: which raise statement or
    call of a function contains an instruction."""

    def __init__(self) -> None:
        self._trees: dict[str, list[ast.AST]] = {}

    def _defs(self, filename: str) -> list[ast.AST]:
        if filename not in self._trees:
            try:
                tree = ast.parse(Path(filename).read_text(encoding="utf-8"))
            except (OSError, SyntaxError, ValueError):
                tree = ast.Module(body=[], type_ignores=[])
            self._trees[filename] = [n for n in ast.walk(tree)
                                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        return self._trees[filename]

    def function(self, code) -> ast.AST | None:
        for node in self._defs(code.co_filename):
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            if node.name == code.co_name and code.co_firstlineno in (first, node.lineno):
                return node
        return None

    @staticmethod
    def own_nodes(fn: ast.AST, kind) -> list[ast.AST]:
        out = []

        def visit(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    continue
                if isinstance(child, kind):
                    out.append(child)
                visit(child)

        visit(fn)
        return sorted(out, key=lambda n: (n.lineno, n.col_offset))


def position(code, lasti: int, lineno: int) -> tuple[int, int | None]:
    try:
        pos = list(code.co_positions())[lasti // 2]
        if pos[0] is not None:
            return pos[0], pos[2]
    except (IndexError, ValueError):
        pass
    return lineno, None


def contains(node: ast.AST, line: int, col: int | None) -> bool:
    if not (node.lineno <= line <= node.end_lineno):
        return False
    if col is None:
        return True
    if line == node.lineno and col < node.col_offset:
        return False
    if line == node.end_lineno and col >= node.end_col_offset:
        return False
    return True


class Recorder:
    def __init__(self, config) -> None:
        self.config = config
        self.package = os.environ.get("S2_PACKAGE", "jwt")
        self.out = Path(os.environ["S2_OUT"])
        self.select = os.environ.get("S2_SELECT", "cases")
        cases = json.loads(Path(os.environ["S2_CASES"]).read_text(encoding="utf-8"))
        checks = json.loads(Path(os.environ["S2_CHECKS"]).read_text(encoding="utf-8"))
        self.blocks: dict[tuple[str, int], dict] = {}
        self.case_tests: set[tuple[str, str]] = set()
        for b in cases["blocks"]:
            for line in range(b["with_line"], b["call_lines"][1] + 1):
                self.blocks[(b["file"], line)] = b
            if b["included"]:
                self.case_tests.add((b["file"], b["test"]))
        self.check_of = {(c["file"], c["function"], k): c["id"]
                         for c in checks["checks"] for k in c["raises"]}
        self.segment_of = {v: k for k, v in checks["segment_calls"].items()}
        self.index = SourceIndex()
        self.records: list[dict] = []
        self.tests: dict[str, dict] = {}
        self.collect_errors: list[dict] = []
        self.current: str | None = None
        self.occurrence: dict[tuple[str, str], int] = {}
        self.started = time.time()
        self._pkg_dir: str | None = None
        self.mutant = os.environ.get("S2_MUTANT")
        self.mutant_env_at_start = os.environ.get("MUTANT_UNDER_TEST")
        if self.mutant is not None and self.mutant_env_at_start is not None:
            raise pytest.UsageError("MUTANT_UNDER_TEST is set before collection")
        self.preimported: list[str] = []
        self.preimport_errors: list[dict] = []
        self.activated_at: float | None = None

    # -- the raise site -----------------------------------------------------

    def package_dir(self) -> str | None:
        if self._pkg_dir is None:
            mod = sys.modules.get(self.package)
            if mod is not None and getattr(mod, "__file__", None):
                self._pkg_dir = os.path.dirname(os.path.realpath(mod.__file__))
        return self._pkg_dir

    def frame_info(self, frame, lineno: int, lasti: int) -> dict | None:
        pkg = self.package_dir()
        code = frame.f_code
        path = os.path.realpath(code.co_filename)
        if pkg is None or not path.startswith(pkg + os.sep):
            return None
        rel = f"{self.package}/{os.path.relpath(path, pkg)}"
        function, variant = demangle(code)
        line, col = position(code, lasti, lineno)
        info = {"file": rel, "function": function, "variant": variant, "line": line,
                "kind": "line", "ordinal": None, "callee": None}
        fn = self.index.function(code)
        if fn is None:
            info["kind"] = "unparsed"
            return info
        for k, node in enumerate(self.index.own_nodes(fn, ast.Raise)):
            if contains(node, line, col):
                info.update(kind="raise", ordinal=k)
                return info
        calls = [n for n in self.index.own_nodes(fn, ast.Call) if contains(n, line, col)]
        if calls:
            call = max(calls, key=lambda n: (n.lineno, n.col_offset))  # the innermost
            callee = call.func.attr if isinstance(call.func, ast.Attribute) else (
                call.func.id if isinstance(call.func, ast.Name) else None)
            same = [n for n in self.index.own_nodes(fn, ast.Call)
                    if isinstance(n.func, (ast.Attribute, ast.Name))
                    and (n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id) == callee]
            info.update(kind="call", callee=callee,
                        ordinal=next((i for i, n in enumerate(same) if n is call), None))
        return info

    def site(self, tb) -> dict:
        frames = []
        while tb is not None:
            info = self.frame_info(tb.tb_frame, tb.tb_lineno, tb.tb_lasti)
            if info is not None:
                frames.append(info)
            tb = tb.tb_next
        site = {"frames": frames, "check": None, "segment": None}
        if not frames:
            return site
        inner = frames[-1]
        if inner["kind"] == "raise":
            site["check"] = self.check_of.get((inner["file"], inner["function"], inner["ordinal"]))
        if site["check"] == "jws.segment-encoding" and len(frames) > 1:
            outer = frames[-2]
            if (outer["function"] == "PyJWS._load" and outer["kind"] == "call"
                    and outer["callee"] == "_decode_base64url_segment"):
                site["segment"] = self.segment_of.get(outer["ordinal"])
        return site

    # -- records ------------------------------------------------------------

    def record(self, filename: str, lineno: int, et, ev, tb, real: str, real_detail: str) -> None:
        block = self.blocks.get((os.path.basename(filename), lineno))
        rec: dict = {
            "test": self.current,
            "key": block["key"] if block else None,
            "included": bool(block and block["included"]),
            "where": f"{os.path.basename(filename)}:{lineno}",
            "real": real,
            "real_detail": real_detail[:300],
        }
        if block is not None and self.current is not None:
            n = self.occurrence.get((self.current, block["key"]), 0)
            self.occurrence[(self.current, block["key"])] = n + 1
            rec["occurrence"] = n
        if et is None:
            rec["outcome"] = "returned"
        else:
            rec["outcome"] = "raised"
            mro = [qualname(c) for c in et.__mro__]
            rec["class"] = qualname(et)
            rec["mro"] = mro
            rec["pyjwt_error"] = f"{self.package}.exceptions.PyJWTError" in mro
            try:
                rec["message"] = str(ev)
            except Exception as e:  # a broken __str__ is an observation too
                rec["message"] = None
                rec["message_error"] = qualname(type(e))
            claim = getattr(ev, "claim", None)
            rec["claim"] = claim if isinstance(claim, (str, int, float, bool, type(None))) else repr(claim)
            cause = ev.__cause__ if ev is not None else None
            rec["cause_mro"] = [qualname(c) for c in type(cause).__mro__] if cause is not None else None
            if block is not None and block["included"]:
                rec["site"] = self.site(tb)
        self.records.append(rec)

    def write(self, exitstatus) -> None:
        data = {
            "env": {"mutant": self.mutant, "mutant_env_at_start": self.mutant_env_at_start,
                    "mutant_env_at_end": os.environ.get("MUTANT_UNDER_TEST"),
                    "activated_at": self.activated_at, "preimported": self.preimported,
                    "preimport_errors": self.preimport_errors, "cwd": os.getcwd(),
                    "package_dir": self.package_dir(), "select": self.select,
                    "seconds": round(time.time() - self.started, 3),
                    "exitstatus": int(exitstatus)},
            "collect_errors": self.collect_errors,
            "tests": self.tests,
            "blocks": self.records,
        }
        self.out.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.out.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, default=repr), encoding="utf-8")
        tmp.replace(self.out)


RECORDER: Recorder | None = None


class Block:
    """Wraps pytest's own context manager for one block."""

    def __init__(self, cm, filename: str, lineno: int) -> None:
        self.cm, self.filename, self.lineno = cm, filename, lineno
        self.excinfo = None

    def __enter__(self):
        self.excinfo = self.cm.__enter__()
        return self.excinfo

    def __exit__(self, et, ev, tb):
        if et is not None and not issubclass(et, Exception):
            return self.cm.__exit__(et, ev, tb)  # never swallowed
        try:
            real, detail = ("ok", "") if self.cm.__exit__(et, ev, tb) else ("propagate", "")
        except AssertionError as e:
            real, detail = "assertion", str(e)
        except Failed as e:
            real, detail = "failed", str(e)
        except Exception as e:  # pytest's check itself broke
            real, detail = f"error:{qualname(type(e))}", str(e)
        if RECORDER is not None:
            RECORDER.record(self.filename, self.lineno, et, ev, tb, real, detail)
        if et is None:
            return False
        if self.excinfo is not None and getattr(self.excinfo, "_excinfo", None) is None:
            self.excinfo.fill_unfilled((et, ev, tb))
        return True


def recording_raises(*args, **kwargs):
    if len(args) > 1 or "func" in kwargs:  # the function form is passed through
        return _REAL_RAISES(*args, **kwargs)
    caller = sys._getframe(1)
    return Block(_REAL_RAISES(*args, **kwargs), caller.f_code.co_filename, caller.f_lineno)


def pytest_configure(config) -> None:
    global RECORDER
    RECORDER = Recorder(config)
    pytest.raises = recording_raises


def pytest_collectreport(report) -> None:
    if report.failed and RECORDER is not None:
        RECORDER.collect_errors.append({"nodeid": report.nodeid,
                                        "detail": str(report.longrepr)[-500:]})


def pytest_collection_finish(session) -> None:
    """Import the whole package, then activate the mutant (see the docstring)."""
    if RECORDER is None:
        return
    import importlib
    import pkgutil
    try:
        pkg = importlib.import_module(RECORDER.package)
        names = [RECORDER.package] + [m.name for m in pkgutil.walk_packages(
            pkg.__path__, prefix=f"{RECORDER.package}.")]
    except Exception as e:
        RECORDER.preimport_errors.append({"module": RECORDER.package, "class": qualname(type(e))})
        names = []
    for name in names:
        try:
            importlib.import_module(name)
            RECORDER.preimported.append(name)
        except Exception as e:
            RECORDER.preimport_errors.append({"module": name, "class": qualname(type(e))})
    if RECORDER.mutant is not None:
        from mutmut.mutation.trampoline import set_mutant_under_test
        set_mutant_under_test(RECORDER.mutant)
        RECORDER.activated_at = round(time.time() - RECORDER.started, 3)


def pytest_collection_modifyitems(session, config, items) -> None:
    if RECORDER is None or RECORDER.select == "all":
        return
    keep, drop = [], []
    for item in items:
        name = getattr(item, "originalname", item.name)
        (keep if (item.path.name, name) in RECORDER.case_tests else drop).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if RECORDER is not None:
        RECORDER.current = item.nodeid
        entry = RECORDER.tests.setdefault(item.nodeid, {})
        entry["file"] = item.path.name
        entry["function"] = getattr(item, "originalname", item.name)
        callspec = getattr(item, "callspec", None)
        if callspec is not None:
            entry["params"] = {k: v if isinstance(v, (str, int, float, bool, type(None))) else repr(v)
                               for k, v in callspec.params.items()}
    try:
        return (yield)
    finally:
        if RECORDER is not None:
            RECORDER.current = None


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    if RECORDER is None:
        return rep
    stop = None
    if call.excinfo is not None:
        et = call.excinfo.type
        stop = {"class": qualname(et),
                "assertion": issubclass(et, (AssertionError, Failed))}
    RECORDER.tests.setdefault(item.nodeid, {})[call.when] = {"outcome": rep.outcome, "stop": stop}
    return rep


def pytest_sessionfinish(session, exitstatus) -> None:
    if RECORDER is not None:
        RECORDER.write(exitstatus)
