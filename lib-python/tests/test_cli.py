"""Command-line conformance runner — counts, path handling, empty trees.

A conformance run that finds no vectors used to print "0 verified,
0 rejected, 0 contract mismatches." and exit 0. On native Windows that
happened for the shipped tree itself, because vectors were classified
by a "valid/" string prefix on paths joined with backslashes.
"""

from __future__ import annotations

import pathlib

import pytest

from eatf_verifier.cli import _expected_verdict, main

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VECTORS_ROOT = REPO_ROOT / "test-vectors"

VALID_COUNT = len(list((VECTORS_ROOT / "valid").rglob("*.aep")))
INVALID_COUNT = len(list((VECTORS_ROOT / "invalid").rglob("*.aep")))


def test_corpus_is_not_empty() -> None:
    assert VALID_COUNT > 0
    assert INVALID_COUNT > 0


@pytest.mark.parametrize(
    "spelling",
    ["absolute", "absolute-trailing-separator", "relative", "relative-trailing-slash"],
)
def test_conformance_runs_every_vector(
    spelling: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    root = {
        "absolute": str(VECTORS_ROOT),
        "absolute-trailing-separator": str(VECTORS_ROOT) + "/",
        "relative": "test-vectors",
        "relative-trailing-slash": "test-vectors/",
    }[spelling]

    code = main(["--conformance", root])

    out = capsys.readouterr().out
    assert code == 0, out
    assert (
        f"Conformance: {VALID_COUNT} verified, {INVALID_COUNT} rejected, "
        "0 contract mismatches."
    ) in out
    assert out.count("PASS  package.aep") == VALID_COUNT + INVALID_COUNT


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        (r"valid\minimal-roundtrip\package.aep", "true"),
        (r"invalid\bad-timestamp\package.aep", "false"),
        ("valid/minimal-roundtrip/package.aep", "true"),
        ("invalid/bad-timestamp/package.aep", "false"),
        (r"keys\stray.aep", None),
        (r"validation\x\package.aep", None),
    ],
)
def test_expected_verdict_with_windows_separators(relative: str, expected: str | None) -> None:
    root = pathlib.PureWindowsPath(r"C:\e\eatf-verifier\test-vectors")
    assert _expected_verdict(root / relative, root) == expected


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("valid/minimal-roundtrip/package.aep", "true"),
        ("invalid/bad-timestamp/package.aep", "false"),
        ("keys/stray.aep", None),
    ],
)
def test_expected_verdict_with_posix_separators(relative: str, expected: str | None) -> None:
    root = pathlib.PurePosixPath("/srv/eatf-verifier/test-vectors")
    assert _expected_verdict(root / relative, root) == expected


def test_conformance_with_no_vectors_fails(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "keys").mkdir()
    (tmp_path / "keys" / "stray.aep").write_bytes(b"not under valid/ or invalid/")

    code = main(["--conformance", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 2
    assert "Conformance:" not in captured.out
    assert "no .aep vectors under valid/ or invalid/" in captured.err


def test_conformance_on_a_category_directory_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["--conformance", str(VECTORS_ROOT / "valid")])

    assert code == 2
    assert "no .aep vectors under valid/ or invalid/" in capsys.readouterr().err


def test_conformance_on_a_missing_directory_fails(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["--conformance", str(tmp_path / "no-such-dir")])

    assert code == 2
    assert "--conformance directory missing" in capsys.readouterr().err
