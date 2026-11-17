"""Shared fixtures of the unit tests of the scripts of this folder.

They run on the synthetic package of ../../target-reach/tests/fixture/toy and on
synthetic files in temporary folders, never on a library of the study. Run them
with the interpreter of an environment on CPython 3.12.3 that holds pytest:

    ../work/tests-venv/bin/python -B -m pytest -q -p no:cacheprovider tests

-B keeps bytecode out of ../../target-reach, whose modules the scripts import.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

X = Path(__file__).resolve().parents[1]                     # target-reach-extension
T = X.parent / "target-reach"
TOY = T / "tests" / "fixture" / "toy"
TOY_SUBJECT = T / "tests" / "fixture" / "subject.json"


def load(name: str, rel: str):
    """A script of this folder, imported as the module `name`."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, X / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def toy_subjects(tmp_path_factory) -> Path:
    """A subjects folder that holds toy/: the toolkit's subject.json of the toy and the
    checks.json and blocks.json that the toolkit's `define` writes for it."""
    root = tmp_path_factory.mktemp("subjects")
    (root / "toy").mkdir()
    shutil.copy(TOY_SUBJECT, root / "toy" / "subject.json")
    subprocess.run([sys.executable, "-I", "-B", str(T / "reach" / "run.py"), "define",
                    "--subject", str(root / "toy" / "subject.json"), "--clone", str(TOY),
                    "--python", sys.executable, "--work", str(tmp_path_factory.mktemp("define"))],
                   check=True, capture_output=True)
    return root


@pytest.fixture
def subjects_copy(toy_subjects, tmp_path) -> Path:
    """A copy of toy_subjects that a test may change."""
    dest = tmp_path / "subjects"
    shutil.copytree(toy_subjects, dest)
    return dest
