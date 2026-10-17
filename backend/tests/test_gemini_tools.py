"""Verify public declarations and their actual SDK HTTP payload, without network."""

import json
from typing import get_args
from unittest.mock import Mock

from google import genai
from google.genai import types
import httpx
import pytest

from app.analytics.contracts import SoilMetricName
from app.harness import registry
from tests.test_gemini_client import make_client


COMPARISON_FIELDS = {"dataset_id", "target_field_id", "reference_field_id", "period"}
PUBLIC_FIELDS = {
    "validate_comparison": COMPARISON_FIELDS,
    "compare_ndvi": COMPARISON_FIELDS,
    "check_initial_condition": COMPARISON_FIELDS,
    "compare_population": COMPARISON_FIELDS,
    "application_compliance": COMPARISON_FIELDS | {"operation"},
    "summarize_soil_analysis": {"dataset_id", "measurement_group", "metrics"},
    "compare_soil_measurement_groups": {"dataset_id", "metrics"},
}


@pytest.mark.parametrize("name", PUBLIC_FIELDS)
def test_declarations_expose_only_public_inputs_and_preserve_contracts(name):
    declarations = registry.build_gemini_tool().function_declarations
    assert {item.name for item in declarations} == set(PUBLIC_FIELDS) == set(registry.TOOLS)
    assert len(declarations) == len(PUBLIC_FIELDS)
    declaration = next(item for item in declarations if item.name == name)
    schema = declaration.parameters_json_schema
    assert declaration.description == registry.TOOLS[name].description
    assert schema == registry.TOOLS[name].parameters.model_json_schema()
    assert declaration.parameters is None  # Mutually exclusive SDK schema fields.
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == PUBLIC_FIELDS[name]
    assert all(item["description"] for item in schema["properties"].values())
    required = {"dataset_id"} if "soil" in name else COMPARISON_FIELDS - {"period"}
    assert set(schema["required"]) == required
    wire = json.loads(declaration.model_dump_json(exclude_none=True, by_alias=True))
    assert set(wire) == {"name", "description", "parametersJsonSchema"}
    assert types.FunctionDeclaration.model_validate(wire) == declaration


def test_nested_period_and_soil_filters_keep_constraints_and_defaults():
    schemas = {item.name: item.parameters_json_schema
               for item in registry.build_gemini_tool().function_declarations}
    comparison = schemas["compare_ndvi"]
    period = comparison["properties"]["period"]
    assert period["default"] == "full_season"
    assert period["anyOf"] == [
        {"const": "full_season", "type": "string"}, {"$ref": "#/$defs/DatePeriod"},
    ]
    dates = comparison["$defs"]["DatePeriod"]
    assert dates["additionalProperties"] is False
    assert dates["required"] == ["start", "end"]
    assert all(prop["format"] == "date" for prop in dates["properties"].values())
    assert comparison["properties"]["dataset_id"]["format"] == "uuid"
    assert schemas["application_compliance"]["properties"]["operation"]["default"] == "CALAGEM"
    for name in ("summarize_soil_analysis", "compare_soil_measurement_groups"):
        metrics = schemas[name]["properties"]["metrics"]
        assert metrics["default"] is None
        choices, nullable = metrics["anyOf"]
        assert choices["minItems"] == 1
        assert choices["items"]["enum"] == list(get_args(SoilMetricName))
        assert nullable == {"type": "null"}
    group = schemas["summarize_soil_analysis"]["properties"]["measurement_group"]
    assert group["enum"] == ["group_1", "group_2"] and group["default"] == "group_1"


def test_declarations_need_no_key_client_or_local_execution(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = Mock(side_effect=AssertionError("must not create a client"))
    executor = Mock(side_effect=AssertionError("must not run a tool"))
    monkeypatch.setattr(genai, "Client", client)
    monkeypatch.setattr(registry, "execute_tool", executor)
    assert len(registry.build_gemini_tool().function_declarations) == 7
    client.assert_not_called()
    executor.assert_not_called()


def test_caller_mutation_cannot_affect_registry_or_next_declarations():
    original = registry.TOOLS["compare_ndvi"].parameters.model_json_schema()
    first = registry.build_gemini_tool()
    ndvi = next(item for item in first.function_declarations if item.name == "compare_ndvi")
    ndvi.parameters_json_schema["$defs"]["DatePeriod"]["properties"]["start"]["type"] = "number"
    ndvi.parameters_json_schema["properties"]["path"] = {"type": "string"}
    first.function_declarations.clear()
    second = registry.build_gemini_tool()
    assert len(second.function_declarations) == 7
    assert next(item for item in second.function_declarations if item.name == "compare_ndvi").parameters_json_schema == original
    assert registry.TOOLS["compare_ndvi"].parameters.model_json_schema() == original


@pytest.mark.parametrize("name", PUBLIC_FIELDS)
def test_official_sdk_sends_all_declarations_and_returns_calls_without_execution(make_client, monkeypatch, name):
    arguments = {"dataset_id": "00000000-0000-4000-8000-000000000001"}
    if "soil" not in name:
        arguments.update(target_field_id="artificial-target", reference_field_id="artificial-reference",
                         period={"start": "2026-01-01", "end": "2026-02-01"})
    else:
        arguments["metrics"] = ["PHCACL2"]
    if name == "summarize_soil_analysis":
        arguments["measurement_group"] = "group_2"

    def respond(request):
        return httpx.Response(200, json={"candidates": [{"content": {
            "role": "model", "parts": [{"functionCall": {"name": name, "args": arguments}}],
        }}]})

    executor = Mock(side_effect=AssertionError("execution belongs to the future orchestrator"))
    monkeypatch.setattr(registry, "execute_tool", executor)
    client, _, requests, transport = make_client(respond)
    config = types.GenerateContentConfig(tools=[registry.build_gemini_tool()])
    with client:
        result = client.generate_content("Contexto artificial para testar declarações.", config=config)
    assert len(requests) == 1 and transport.is_closed
    assert result.function_calls[0].name == name
    assert result.function_calls[0].args == arguments
    executor.assert_not_called()
    payload = json.loads(requests[0].content)
    declared = payload["tools"][0]["functionDeclarations"]
    assert len(declared) == 7
    assert {item["name"] for item in declared} == set(PUBLIC_FIELDS)
    for item in declared:
        # The SDK HTTP converter uses snake_case for this JSON Schema field.
        assert set(item) == {"name", "description", "parameters_json_schema"}
        assert item["parameters_json_schema"] == registry.TOOLS[item["name"]].parameters.model_json_schema()
    assert config.automatic_function_calling is None  # Client must not mutate caller config.
