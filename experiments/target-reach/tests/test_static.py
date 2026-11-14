"""Static analysis on synthetic packages: classes known by module, the
resolution of class expressions, labels, every definition of a function, and
the method-resolution order of a message argument."""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from reach.blocks import enumerate_blocks
from reach.checks import enumerate_checks, functions, line_index, message_argument, mro
from reach.delete import delete_check
from reach.scope import scope
from reach.targets import descriptor, target_for

E = Path(__file__).resolve().parents[1]


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def subject_of(package: str, files: list[str], entry: list[str], bases: list[str],
               tests: list[str]) -> dict:
    return {"name": package, "package": package, "source_root": ".", "subject_files": files,
            "observed_files": [], "entry_points": entry, "rejection_bases": bases, "tests": tests}


def by_id(doc: dict) -> dict:
    return {c["id"]: c for c in doc["checks"]}


def blocks_by_test(doc: dict) -> dict:
    return {b["test"] + "#" + str(b["k"]): b for b in doc["blocks"]}


# -- 1 package with most resolution paths ------------------------------------------

SP = {
    "sp/__init__.py": """
        from . import errors
        from .errors import BadToken, Rejected
        """,
    "sp/errors.py": """
        class Rejected(Exception):
            pass


        class BadToken(Rejected):
            pass


        class Expired(Rejected):
            pass


        class Revoked(Rejected):
            pass
        """,
    "sp/other.py": """
        class BadToken(Exception):
            pass
        """,
    "sp/sub/__init__.py": """
        from .deep import Deep
        """,
    "sp/sub/deep.py": """
        from .. import errors


        class Deep(errors.Rejected):
            pass
        """,
    "sp/starred.py": """
        from .errors import *


        def decode(token):
            raise Expired("starred")
        """,
    "sp/core.py": """
        import sp.sub
        from sp import errors
        from . import other
        from .errors import Expired as Gone
        from extlib.errors import Expired as ExtExpired
        import extlib

        Alias = errors.Revoked


        def decode(token):
            if token == 1:
                raise errors.BadToken("chain")
            if token == 2:
                raise other.BadToken("not a rejection")
            if token == 3:
                raise sp.sub.Deep("deep")
            if token == 4:
                raise Gone("gone")
            if token == 5:
                raise ExtExpired("external")
            if token == 6:
                raise Alias("alias")
            if token == 7:
                from .errors import Rejected as Local
                raise Local("local import")
            if token == 8:
                raise token.Expired("fallback")
            if token == 9:
                raise extlib.errors.BadToken("external chain")
            return token
        """,
    "tests/test_sp.py": """
        import pytest

        import sp
        from sp import errors
        from sp.core import decode
        from sp.other import BadToken as OtherBad
        from extlib.errors import Expired as ExtExpired


        def test_chain():
            with pytest.raises(sp.errors.BadToken):
                decode(1)


        def test_other():
            with pytest.raises(OtherBad):
                decode(2)


        def test_external():
            with pytest.raises(ExtExpired):
                decode(5)


        def test_mixed():
            with pytest.raises((errors.Expired, ExtExpired)):
                decode(4)


        def test_relative():
            from .helpers import Revoked
            with pytest.raises(Revoked):
                decode(6)


        def test_reexport():
            with pytest.raises(sp.Rejected):
                decode(7)


        def test_local_name():
            expected = errors.Expired if True else errors.Revoked
            with pytest.raises(expected):
                decode(4)
        """,
}


@pytest.fixture(scope="module")
def sp_defs(tmp_path_factory):
    root = tmp_path_factory.mktemp("sp")
    write(root, SP)
    subject = subject_of("sp", ["sp/core.py", "sp/starred.py"], ["decode"], ["Rejected"], ["tests"])
    checks = enumerate_checks(subject, root)
    blocks = enumerate_blocks(subject, root, checks)
    return root, subject, checks, blocks


def test_two_classes_of_one_name_in_two_modules(sp_defs):
    _, _, checks, _ = sp_defs
    classes = checks["classes"]
    # 1 entry per class statement; the bare name is ambiguous, so the label is qualified
    assert classes["sp.errors.BadToken"]["module"] == "sp.errors"
    assert classes["sp.other.BadToken"]["module"] == "sp.other"
    assert "BadToken" not in classes
    assert classes["sp.errors.BadToken"]["bases"] == ["Rejected"]
    assert classes["sp.other.BadToken"]["bases"] == ["Exception"]
    assert "sp.errors.BadToken" in checks["rejection_classes"]
    assert "sp.other.BadToken" not in checks["rejection_classes"]
    c = by_id(checks)
    assert c["core.decode#1"]["class"] == "sp.errors.BadToken"
    assert c["core.decode#1"]["class_name"] == "BadToken"
    other = [o for o in checks["other_raises"] if o["line"] == 15]
    assert [(o["class"], o["class_resolved"], o["reason"]) for o in other] == [
        ("BadToken", "sp.other.BadToken", "not a rejection class")]


def test_external_class_with_a_package_name(sp_defs):
    _, _, checks, blocks = sp_defs
    ext = {o["line"]: o for o in checks["other_raises"]}
    # raise ExtExpired(...): imported from outside the package, not the package's Expired
    assert (ext[21]["class"], ext[21]["class_resolved"]) == ("ExtExpired", "extlib.errors.Expired")
    assert (ext[30]["class"], ext[30]["class_resolved"]) == ("BadToken", "extlib.errors.BadToken")
    b = blocks_by_test(blocks)
    assert b["test_external#0"]["expected"] == ["extlib.errors.Expired"]
    assert b["test_external#0"]["expected_kinds"] == ["external"]
    assert b["test_external#0"]["included"] is False
    assert b["test_external#0"]["exclusion"] == ["expects extlib.errors.Expired"]


def test_attribute_chains_reexport_alias_and_relative_imports(sp_defs):
    _, _, checks, _ = sp_defs
    c = by_id(checks)
    got = {k: (v["class"], v["class_resolution"]) for k, v in c.items() if k.startswith("core.")}
    assert got == {
        "core.decode#1": ("sp.errors.BadToken", ["import"]),   # errors.BadToken
        "core.decode#2": ("Deep", ["import"]),                 # sp.sub.Deep, re-exported by sp/sub/__init__.py
        "core.decode#3": ("Expired", ["import"]),              # from .errors import Expired as Gone
        "core.decode#4": ("Revoked", ["import"]),              # Alias = errors.Revoked
        "core.decode#5": ("Rejected", ["import"]),             # import inside the function
        "core.decode#6": ("Expired", ["unique name"]),         # token.Expired: the fallback
    }
    # the base of Deep is resolved through `from .. import errors` in a submodule
    assert checks["classes"]["Deep"]["bases"] == ["Rejected"]
    assert checks["rejection_bases"] == [{"name": "Rejected", "kind": "package",
                                          "module": "sp.errors", "qualname": "Rejected"}]


def test_star_import(sp_defs):
    _, _, checks, _ = sp_defs
    c = by_id(checks)
    assert (c["starred.decode#1"]["class"], c["starred.decode#1"]["class_resolution"]) == (
        "Expired", ["import"])


def test_blocks_resolution(sp_defs):
    _, _, _, blocks = sp_defs
    b = blocks_by_test(blocks)
    assert (b["test_chain#0"]["expected"], b["test_chain#0"]["expected_kinds"]) == (
        ["sp.errors.BadToken"], ["import"])
    assert b["test_chain#0"]["included"] is True
    assert b["test_other#0"]["expected"] == ["sp.other.BadToken"]
    assert b["test_other#0"]["exclusion"] == ["expects sp.other.BadToken"]
    # a tuple that mixes a package class and an external class of the same bare name
    assert b["test_mixed#0"]["expected"] == ["Expired", "extlib.errors.Expired"]
    assert b["test_mixed#0"]["expected_kinds"] == ["import", "external"]
    assert b["test_mixed#0"]["exclusion"] == ["expects extlib.errors.Expired"]
    # a relative import in a test module outside the package is not followed: the fallback
    assert (b["test_relative#0"]["expected"], b["test_relative#0"]["expected_kinds"]) == (
        ["Revoked"], ["unique name"])
    assert b["test_reexport#0"]["expected"] == ["Rejected"]
    assert b["test_reexport#0"]["expected_kinds"] == ["import"]
    # the path through local assignments stays for a name the module does not bind
    local = b["test_local_name#0"]
    assert (local["expected"], local["expected_kinds"], local["expected_resolution"]) == (
        ["Expired", "Revoked"], ["import", "import"], "local assignment")


# -- 2 rejection classes of 1 bare name --------------------------------------------

DUP = {
    "dup/__init__.py": "",
    "dup/a.py": """
        class Base(Exception):
            pass


        class Invalid(Base):
            pass
        """,
    "dup/b.py": """
        from .a import Base


        class Invalid(Base):
            pass
        """,
    "dup/core.py": """
        from . import a, b


        def decode(x):
            if x == 1:
                raise a.Invalid("first problem")
            if x == 2:
                raise b.Invalid("second problem")
            return x
        """,
    "tests/test_dup.py": """
        import pytest

        from dup import b
        from dup.core import decode


        def test_second_problem():
            with pytest.raises(b.Invalid):
                decode(2)
        """,
}


def test_two_rejection_classes_of_one_bare_name(tmp_path):
    write(tmp_path, DUP)
    subject = subject_of("dup", ["dup/core.py"], ["decode"], ["Base"], ["tests"])
    checks = enumerate_checks(subject, tmp_path)
    c = by_id(checks)
    assert checks["rejection_classes"] == ["Base", "dup.a.Invalid", "dup.b.Invalid"]
    assert (c["core.decode#1"]["class"], c["core.decode#2"]["class"]) == ("dup.a.Invalid", "dup.b.Invalid")
    # the rule reads the bare class name: no token of the module path
    assert descriptor(c["core.decode#1"]) == {"first", "problem", "invalid", "decode"}
    blocks = enumerate_blocks(subject, tmp_path, checks)
    (block,) = blocks["blocks"]
    assert block["expected"] == ["dup.b.Invalid"] and block["included"]
    t = target_for(block, checks["checks"], checks["classes"])
    # only the checks of the expected class are candidates
    assert t["C_class"] == ["core.decode#2"]
    assert (t["target"], t["basis"]) == ("core.decode#2", "class")


def test_ambiguous_rejection_base(tmp_path):
    write(tmp_path, DUP)
    subject = subject_of("dup", ["dup/core.py"], ["decode"], ["Invalid"], ["tests"])
    with pytest.raises(SystemExit, match="dup.a.Invalid, dup.b.Invalid"):
        enumerate_checks(subject, tmp_path)
    subject["rejection_bases"] = ["NoSuchClass"]
    with pytest.raises(SystemExit, match="NoSuchClass"):
        enumerate_checks(subject, tmp_path)
    # the label of 1 package class is accepted
    subject["rejection_bases"] = ["dup.b.Invalid"]
    checks = enumerate_checks(subject, tmp_path)
    assert checks["rejection_classes"] == ["dup.b.Invalid"]
    assert [(c["id"], c["class"]) for c in checks["checks"]] == [("core.decode#1", "dup.b.Invalid")]


def test_package_class_named_like_a_builtin(tmp_path):
    write(tmp_path, {
        "own/__init__.py": "",
        "own/errors.py": """
            class Base(Exception):
                pass


            class TimeoutError(Base):
                pass
            """,
        "own/core.py": """
            from . import errors


            def decode(x):
                if x == 1:
                    raise TimeoutError("the built-in")
                if x == 2:
                    raise errors.TimeoutError("of the package")
                raise ValueError("own")
            """,
        "tests/test_own.py": """
            import pytest
            from own import errors
            from own.core import decode


            def test_builtin():
                with pytest.raises(TimeoutError):
                    decode(1)


            def test_package():
                with pytest.raises(errors.TimeoutError):
                    decode(2)


            def test_attribute_of_an_object(obj):
                with pytest.raises(obj.TimeoutError):
                    decode(2)
            """,
    })
    subject = subject_of("own", ["own/core.py"], ["decode"], ["Base"], ["tests"])
    checks = enumerate_checks(subject, tmp_path)
    # the package class never takes the label of the built-in
    assert "TimeoutError" not in checks["classes"]
    assert checks["rejection_classes"] == ["Base", "own.errors.TimeoutError"]
    assert [(c["class"], c["class_name"], c["lines"]) for c in checks["checks"]] == [
        ("own.errors.TimeoutError", "TimeoutError", [[8, 8]])]
    assert {o["line"]: (o["class_resolved"], o["reason"]) for o in checks["other_raises"]} == {
        6: ("TimeoutError", "not a rejection class"), 9: ("ValueError", "not a rejection class")}
    b = blocks_by_test(enumerate_blocks(subject, tmp_path, checks))
    assert (b["test_builtin#0"]["expected"], b["test_builtin#0"]["expected_kinds"],
            b["test_builtin#0"]["included"]) == (["TimeoutError"], ["builtin"], False)
    assert (b["test_package#0"]["expected"], b["test_package#0"]["included"]) == (
        ["own.errors.TimeoutError"], True)
    # a name that a built-in has is never resolved by the unique-name fallback
    obj = b["test_attribute_of_an_object#0"]
    assert (obj["expected"], obj["expected_kinds"], obj["included"]) == (["?TimeoutError"], ["unknown"], False)
    # a built-in rejection base is the built-in; the package class is named by its label
    subject["rejection_bases"] = ["TimeoutError"]
    checks = enumerate_checks(subject, tmp_path)
    assert checks["rejection_bases"] == [{"name": "TimeoutError", "kind": "builtin",
                                          "module": "builtins", "qualname": "TimeoutError"}]
    assert checks["rejection_classes"] == []
    assert [c["lines"] for c in checks["checks"]] == [[[6, 6]]]
    b = blocks_by_test(enumerate_blocks(subject, tmp_path, checks))
    assert [k for k, v in sorted(b.items()) if v["included"]] == ["test_builtin#0"]
    subject["rejection_bases"] = ["own.errors.TimeoutError"]
    checks = enumerate_checks(subject, tmp_path)
    assert checks["rejection_bases"] == [{"name": "own.errors.TimeoutError", "kind": "package",
                                          "module": "own.errors", "qualname": "TimeoutError"}]
    assert [c["lines"] for c in checks["checks"]] == [[[8, 8]]]


def test_builtin_class_that_inherits_from_a_builtin_base(tmp_path):
    write(tmp_path, {
        "hier/__init__.py": "",
        "hier/core.py": """
            class Local(UnicodeError):
                pass


            class Odd(registry.ValueError):
                pass


            class Made(make_base()):
                pass


            def decode(x):
                if x == 1:
                    raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")
                if x == 2:
                    raise Local("local")
                if x == 3:
                    raise KeyError("no")
                if x == 4:
                    raise Odd("odd")
                raise ValueError("value")
            """,
        "tests/test_hier.py": """
            import json

            import pytest
            from hier.core import decode


            def test_builtin_subclass():
                with pytest.raises(UnicodeError):
                    decode(1)


            def test_external_subclass():
                with pytest.raises(json.JSONDecodeError):
                    decode(1)
            """,
    })
    subject = subject_of("hier", ["hier/core.py"], ["decode"], ["ValueError"], ["tests"])
    checks = enumerate_checks(subject, tmp_path)
    # a base that cannot be followed is no class, even when its name is a built-in name
    assert checks["classes"]["Odd"]["bases"] == ["?ValueError"]
    assert checks["classes"]["Made"]["bases"] == ["?make_base"]
    assert checks["rejection_classes"] == ["Local"]
    assert [(c["class"], c["lines"]) for c in checks["checks"]] == [
        ("UnicodeDecodeError", [[15, 15]]), ("Local", [[17, 17]]), ("ValueError", [[22, 22]])]
    assert [(o["class"], o["reason"]) for o in checks["other_raises"]] == [
        ("KeyError", "not a rejection class"), ("Odd", "not a rejection class")]
    b = blocks_by_test(enumerate_blocks(subject, tmp_path, checks))
    assert b["test_builtin_subclass#0"]["included"] is True
    # a class from outside the package is not a rejection class, whatever it inherits from
    ext = b["test_external_subclass#0"]
    assert (ext["expected"], ext["expected_kinds"], ext["included"]) == (
        ["json.JSONDecodeError"], ["external"], False)


def test_import_with_a_fallback_keeps_the_binding_of_the_try_body(tmp_path):
    write(tmp_path, {
        "tr/__init__.py": "",
        "tr/errors.py": """
            class Rejected(Exception):
                pass


            class Other(Exception):
                pass
            """,
        "tr/core.py": """
            try:
                from .errors import Rejected as Err
            except ImportError:
                from .errors import Other as Err


            def decode(x):
                raise Err("no")
            """,
    })
    subject = subject_of("tr", ["tr/core.py"], ["decode"], ["Rejected"], [])
    checks = enumerate_checks(subject, tmp_path)
    assert [(c["class"], c["class_resolution"]) for c in checks["checks"]] == [("Rejected", ["import"])]


def test_class_of_a_test_module_is_not_a_package_class(tmp_path):
    write(tmp_path, {
        "fo/__init__.py": "",
        "fo/core.py": """
            class Rejected(Exception):
                pass


            def decode(x):
                raise Rejected("no")
            """,
        "tests/test_fo.py": """
            import pytest
            from fo.core import decode


            class Rejected(Exception):
                pass


            class Holder:
                class Rejected(Exception):
                    pass


            def test_module_class():
                with pytest.raises(Rejected):
                    decode(1)


            def test_local_class():
                class Rejected(Exception):
                    pass
                with pytest.raises(Rejected):
                    decode(1)


            def test_nested_class():
                with pytest.raises(Holder.Rejected):
                    decode(1)


            def test_attribute_of_an_object(obj):
                with pytest.raises(obj.Rejected):
                    decode(1)
            """,
    })
    subject = subject_of("fo", ["fo/core.py"], ["decode"], ["Rejected"], ["tests"])
    checks = enumerate_checks(subject, tmp_path)
    b = blocks_by_test(enumerate_blocks(subject, tmp_path, checks))
    for test in ("test_module_class#0", "test_local_class#0", "test_nested_class#0"):
        assert (b[test]["expected"], b[test]["expected_kinds"], b[test]["included"]) == (
            ["?Rejected"], ["unknown"], False)
        assert b[test]["exclusion"] == ["expects ?Rejected"]
    # an expression that cannot be followed still falls back to the 1 package class of the name
    obj = b["test_attribute_of_an_object#0"]
    assert (obj["expected"], obj["expected_kinds"], obj["included"]) == (["Rejected"], ["unique name"], True)


def test_star_import_through_two_modules(tmp_path):
    write(tmp_path, {
        "st/__init__.py": """
            from .api import *
            """,
        "st/api.py": """
            from .errors import *
            """,
        "st/errors.py": """
            class Rejected(Exception):
                pass


            class _Hidden(Rejected):
                pass
            """,
        "st/core.py": """
            from st import *


            def decode(x):
                if x:
                    raise Rejected("no")
                raise _Hidden("hidden")
            """,
        "tests/test_st.py": """
            import pytest
            import st
            from st.core import decode


            def test_star():
                with pytest.raises(st.Rejected):
                    decode(1)
            """,
    })
    subject = subject_of("st", ["st/core.py"], ["decode"], ["Rejected"], ["tests"])
    checks = enumerate_checks(subject, tmp_path)
    # Rejected comes through 2 star imports; _Hidden is not exported, so only its unique name finds it
    assert [(c["class"], c["class_resolution"]) for c in checks["checks"]] == [
        ("Rejected", ["import"]), ("_Hidden", ["unique name"])]
    b = blocks_by_test(enumerate_blocks(subject, tmp_path, checks))
    assert (b["test_star#0"]["expected"], b["test_star#0"]["expected_kinds"]) == (["Rejected"], ["import"])


def test_survey_reports_an_ambiguous_base(tmp_path):
    write(tmp_path, DUP)
    out = subprocess.run([sys.executable, "-I", "-B", str(E / "selection" / "survey.py"), str(E),
                          str(tmp_path), "dup", "decode", "Invalid", "tests"],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0
    assert "stopped: rejection base 'Invalid'" in out.stdout


# -- every definition of a function ----------------------------------------------------

OV = '''
from typing import overload


class Err(Exception):
    pass


class Box:
    @property
    def value(self):
        raise Err("getter")

    @value.setter
    def value(self, v):
        if v is None:
            raise Err("setter")
        self._v = v


@overload
def load(x: int) -> int: ...
@overload
def load(x: str) -> str: ...
def load(x):
    if not x:
        raise Err("empty")
    return x


def decode(box):
    box.value = 1
    return box


def unused():
    raise Err("never")
'''


def test_getter_setter_and_overloads(tmp_path):
    write(tmp_path, {"ov/__init__.py": "", "ov/core.py": OV})
    subject = subject_of("ov", ["ov/core.py"], ["decode"], ["Err"], [])
    checks = enumerate_checks(subject, tmp_path)
    c = by_id(checks)
    assert sorted(c) == ["core.Box.value#1", "core.Box.value~2#1", "core.load~3#1", "core.unused#1"]
    assert c["core.Box.value#1"]["template"] == "getter"
    assert c["core.Box.value~2#1"]["template"] == "setter"
    assert c["core.Box.value~2#1"]["function"] == "Box.value~2"
    assert c["core.Box.value~2#1"]["function_name"] == "value"
    assert c["core.load~3#1"]["function_name"] == "load"
    # reachability reads a ~k definition as its name: box.value reaches getter and setter
    assert c["core.Box.value#1"]["reachable"] and c["core.Box.value~2#1"]["reachable"]
    assert not c["core.load~3#1"]["reachable"] and not c["core.unused#1"]["reachable"]
    subject["entry_points"] = ["load"]
    assert by_id(enumerate_checks(subject, tmp_path))["core.load~3#1"]["reachable"]
    assert [f["function"] for f in checks["functions"]] == [
        "Box.value", "Box.value~2", "decode", "load", "load~2", "load~3", "unused"]
    index = line_index(checks)["ov/core.py"]
    assert index[c["core.Box.value~2#1"]["lines"][0][0]]["check"] == "core.Box.value~2#1"
    # the deletion of the setter's check leaves the getter as it was
    source = (tmp_path / "ov" / "core.py").read_text(encoding="utf-8")
    out, changed = delete_check(source, c["core.Box.value~2#1"])
    assert 'raise Err("setter")' not in out and 'raise Err("getter")' in out
    assert changed[0]["lines"] == c["core.Box.value~2#1"]["lines"][0]
    out, _ = delete_check(source, c["core.load~3#1"])
    assert "empty" not in out and len(out.splitlines()) == len(source.splitlines())


def test_nested_function_in_a_later_definition():
    tree = ast.parse("def f():\n    pass\n\n\ndef f():\n    def inner():\n        pass\n")
    assert list(functions(tree)) == ["f", "f~2", "f~2.inner"]


# -- the message argument ---------------------------------------------------------------

def test_message_argument_in_method_resolution_order(tmp_path):
    write(tmp_path, {
        "mr/__init__.py": "",
        "mr/core.py": """
            class Root(Exception):
                pass


            class A(Root):
                def __init__(self, detail=None):
                    super().__init__(detail)


            class B(Root):
                def __init__(self, message=None):
                    super().__init__(message)


            class Mixed(B, A):
                pass


            def decode(x):
                raise Mixed(detail="from a", message="from b")
            """,
    })
    subject = subject_of("mr", ["mr/core.py"], ["decode"], ["Root"], [])
    checks = enumerate_checks(subject, tmp_path)
    assert checks["classes"]["Mixed"]["bases"] == ["A", "B"]
    assert checks["classes"]["Mixed"]["bases_declared"] == ["B", "A"]
    # B comes first in the method-resolution order, though A sorts first
    assert checks["checks"][0]["template"] == "from b"
    assert mro("Mixed", checks["classes"]) == ["Mixed", "B", "A", "Root", "Exception"]


def test_mro_falls_back_to_depth_first():
    classes = {"A": {"bases_declared": ["Exception"]}, "B": {"bases_declared": ["Exception"]},
               "X": {"bases_declared": ["A", "B"]}, "Y": {"bases_declared": ["B", "A"]},
               "Z": {"bases_declared": ["X", "Y"], "init_params": None}}
    assert mro("Z", classes) == ["Z", "X", "A", "Exception", "B", "Y"]
    call = ast.parse("E(text='t')", mode="eval").body
    assert message_argument(call, "Z", {**classes, "B": {"bases_declared": [], "init_params": ["text"]}}) \
        is call.keywords[0].value


# -- a test module inside the package directory --------------------------------------------

def test_test_module_inside_the_package(tmp_path):
    write(tmp_path, {
        "inpkg/__init__.py": "",
        "inpkg/errors.py": """
            class Bad(Exception):
                pass
            """,
        "inpkg/core.py": """
            from .errors import Bad


            def decode(x):
                raise Bad("bad")
            """,
        "inpkg/test_core.py": """
            import unittest

            from . import errors
            from .core import decode


            class Local(errors.Bad):
                pass


            class T(unittest.TestCase):
                def test_bad(self):
                    with self.assertRaises(errors.Bad):
                        decode(1)

                def test_local(self):
                    with self.assertRaises(Local):
                        decode(1)
            """,
    })
    subject = subject_of("inpkg", ["inpkg/core.py"], ["decode"], ["Bad"], ["inpkg/test_core.py"])
    checks = enumerate_checks(subject, tmp_path)
    assert checks["classes"]["Local"]["module"] == "inpkg.test_core"
    blocks = enumerate_blocks(subject, tmp_path, checks)
    b = blocks_by_test(blocks)
    assert (b["test_bad#0"]["expected"], b["test_bad#0"]["expected_kinds"]) == (["Bad"], ["import"])
    assert (b["test_local#0"]["expected"], b["test_local#0"]["expected_kinds"]) == (
        ["Local"], ["definition"])
    assert b["test_bad#0"]["included"] and b["test_local#0"]["included"]


# -- scope counts ------------------------------------------------------------------------------

def test_scope_counts(tmp_path):
    write(tmp_path, DUP)
    write(tmp_path, {"tests/test_none.py": """
        import pytest


        def test_nothing():
            with pytest.raises(KeyError):
                {}["x"]
        """})
    draft = {"name": "dup", "package": "dup", "source_root": ".", "entry_points": ["decode"],
             "rejection_bases": ["Base"], "test_directories": ["tests"]}
    subject = scope(draft, tmp_path)
    assert subject["tests"] == ["tests/test_dup.py"]
    assert subject["scope_counts"] == {"test_files_in_test_directories": 2,
                                       "blocks_in_test_directories": 2,
                                       "test_files_with_an_included_block": 1}
