from __future__ import annotations

# ruff: noqa: S101 - assertions express expectations in test cases
import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final, cast

import pytest
from x_make_common_x.json_contracts import validate_payload, validate_schema

from x_make_markdown_x.json_contracts import (
    ERROR_SCHEMA,
    INPUT_SCHEMA,
    OUTPUT_SCHEMA,
)
from x_make_markdown_x.x_cls_make_markdown_x import main_json

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "json_contracts"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _load_fixture(name: str) -> dict[str, object]:
    with (FIXTURE_DIR / f"{name}.json").open("r", encoding="utf-8") as handle:
        raw_payload = cast("object", json.load(handle))
    if not isinstance(raw_payload, dict):
        message = f"Fixture payload must be an object: {name}"
        raise TypeError(message)
    typed_payload: dict[str, object] = {}
    for key, value in raw_payload.items():
        typed_payload[str(key)] = value
    return typed_payload


SAMPLE_INPUT: Final[dict[str, object]] = _load_fixture("input")
SAMPLE_OUTPUT: Final[dict[str, object]] = _load_fixture("output")
SAMPLE_ERROR: Final[dict[str, object]] = _load_fixture("error")


def test_schemas_are_valid() -> None:
    for schema in (INPUT_SCHEMA, OUTPUT_SCHEMA, ERROR_SCHEMA):
        validate_schema(schema)


def test_sample_payloads_match_schema() -> None:
    validate_payload(SAMPLE_INPUT, INPUT_SCHEMA)
    validate_payload(SAMPLE_OUTPUT, OUTPUT_SCHEMA)
    validate_payload(SAMPLE_ERROR, ERROR_SCHEMA)


def test_existing_reports_align_with_schema() -> None:
    if not REPORTS_DIR.exists():
        pytest.skip("no reports directory for markdown tool")
    report_files = sorted(REPORTS_DIR.glob("x_make_markdown_x_run_*.json"))
    if not report_files:
        pytest.skip("no markdown run reports to validate")
    for report_file in report_files:
        with report_file.open("r", encoding="utf-8") as handle:
            payload_obj: object = json.load(handle)
        if isinstance(payload_obj, Mapping):
            payload_map = cast("Mapping[str, object]", payload_obj)
            validate_payload(dict(payload_map), OUTPUT_SCHEMA)
        else:
            message = f"Report {report_file.name} must contain a JSON object"
            raise TypeError(message)


def test_main_json_executes_happy_path() -> None:
    result = main_json(SAMPLE_INPUT)
    validate_payload(result, OUTPUT_SCHEMA)
    status_value = result.get("status")
    assert isinstance(status_value, str)
    assert status_value == "success"


def test_main_json_returns_error_for_invalid_payload() -> None:
    invalid = copy.deepcopy(SAMPLE_INPUT)
    parameters_obj = invalid.get("parameters")
    if not isinstance(parameters_obj, dict):
        parameters_obj = {}
        invalid["parameters"] = parameters_obj
    parameters = cast("dict[str, object]", parameters_obj)
    parameters.pop("output_markdown", None)
    result = main_json(invalid)
    validate_payload(result, ERROR_SCHEMA)
    status_value = result.get("status")
    assert isinstance(status_value, str)
    assert status_value == "failure"
