"""Write subject.json from draft.json: the 2 lists that follow from a rule.

    python -I reach/scope.py --draft subjects/<name>/draft.json --clone DIR

A draft gives what a person decides for a subject: the release, the package,
the entry points, the rejection bases, the test directories and the pytest
calls that make up the project's whole test suite ("suite_runs"). This step
adds what follows mechanically:

    subject_files  every Python file of the package that is not a test file
                   of the test directories, sorted
    tests          every test file of the test directories that holds at
                   least 1 included block (a negative-test block that calls
                   an entry point by name and expects a rejection class)
    scope_counts   the counts before and after that narrowing:
                   test_files_in_test_directories, blocks_in_test_directories
                   and test_files_with_an_included_block. The block counts of
                   `run.py define` read only the files of `tests`, so they
                   count the blocks of the files with an included block.

It reads source files only (AST); it runs nothing and computes no target.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_ROOT = HERE.parent
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from reach.blocks import enumerate_blocks, test_files  # noqa: E402
from reach.checks import enumerate_checks, load_json, package_dir  # noqa: E402

DERIVED = ("subject_files", "observed_files", "tests", "scope_counts")


def scope(draft: dict, clone: Path) -> dict:
    subject = {k: v for k, v in draft.items() if k != "test_directories"}
    root = clone / draft.get("source_root", ".")
    tests = {p.resolve() for p in test_files({"tests": draft["test_directories"]}, clone)}
    subject["subject_files"] = sorted(p.relative_to(root).as_posix()
                                      for p in package_dir(draft, clone).rglob("*.py")
                                      if p.resolve() not in tests)
    subject["observed_files"] = []
    subject["tests"] = list(draft["test_directories"])
    checks = enumerate_checks(subject, clone)
    blocks = enumerate_blocks(subject, clone, checks)
    subject["tests"] = sorted({b["file"] for b in blocks["blocks"] if b["included"]})
    subject["scope_counts"] = {"test_files_in_test_directories": len(blocks["test_files"]),
                               "blocks_in_test_directories": blocks["counts"]["blocks"],
                               "test_files_with_an_included_block": len(subject["tests"])}
    return subject


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="write subject.json from draft.json")
    parser.add_argument("--draft", required=True)
    parser.add_argument("--clone", required=True)
    args = parser.parse_args(argv)
    draft_path = Path(args.draft).resolve()
    draft = load_json(draft_path)
    for key in DERIVED:
        if key in draft:
            raise SystemExit(f"draft.json must not give {key}")
    subject = scope(draft, Path(args.clone).resolve())
    out = draft_path.with_name("subject.json")
    out.write_text(json.dumps(subject, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"scope: {len(subject['subject_files'])} subject files, {len(subject['tests'])} test files -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
