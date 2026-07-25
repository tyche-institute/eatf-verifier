"""Validate the shipped schemas and every positive conformance package."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = REPO_ROOT / "schemas"
VALID_PACKAGES = sorted((REPO_ROOT / "test-vectors" / "valid").glob("*/package.aep"))

CASES = (
    ("aep-v1.schema.json", "metadata.json"),
    ("overt-receipt-v1.schema.json", "overt_receipt.json"),
)


@pytest.mark.parametrize(("schema_name", "entry_name"), CASES)
def test_schema_is_valid_draft_2020_12(schema_name: str, entry_name: str) -> None:
    del entry_name
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("package", VALID_PACKAGES, ids=lambda path: path.parent.name)
@pytest.mark.parametrize(("schema_name", "entry_name"), CASES)
def test_positive_vectors_match_shipped_schemas(
    package: Path,
    schema_name: str,
    entry_name: str,
) -> None:
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    with zipfile.ZipFile(package) as archive:
        instance = json.loads(archive.read(entry_name))

    validator.validate(instance)
