import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.analytics.common import AnalysisUnavailableError
from app.analytics.evidence import EvidenceIdGenerator
from app.api.datasets import _process_package
from app.config import get_settings
from app.data.session_store import dataset_store
from app.harness.registry import TOOLS, execute_tool, get_tool
from app.main import app
from tests.test_analytics import analytical_dataset


@pytest.fixture
def arguments(analytical_dataset):
    identifier = dataset_store.save(analytical_dataset)
    return dict(dataset_id=str(identifier), target_field_id="103144", reference_field_id="103145")


def test_registry_is_closed_typed_and_versioned():
    assert set(TOOLS) == {"validate_comparison", "compare_ndvi", "check_initial_condition", "compare_population", "application_compliance", "summarize_soil_analysis", "compare_soil_measurement_groups"}
    for tool in TOOLS.values():
        assert tool.version == "1.0.0" and tool.description
        schema = tool.parameters.model_json_schema()
        assert schema["additionalProperties"] is False
        assert "DataFrame" not in json.dumps(schema) and "path" not in schema["properties"]
    with pytest.raises(AnalysisUnavailableError):
        get_tool("execute_python")
    with pytest.raises(TypeError):
        TOOLS["extra"] = None


@pytest.mark.parametrize("name", list(TOOLS))
def test_each_tool_runs_locally_through_diagnostics(arguments, name):
    if "soil" in name:
        arguments = dict(dataset_id=arguments["dataset_id"])
    response = TestClient(app).post("/api/diagnostics/tools", json=dict(tool=name, arguments=arguments))
    assert response.status_code == 200, response.text
    assert response.json()["evidence_id"].startswith("EV-")
    assert response.json()["source_files"]
    assert response.json()["tool_version"] == "1.0.0"


@pytest.mark.parametrize(("tool", "override", "status"), [
    ("compare_ndvi", {"path": "/tmp/data.csv"}, 422),
    ("compare_ndvi", {"frame": []}, 422),
    ("compare_ndvi", {"target_field_id": "unknown"}, 422),
    ("compare_ndvi", {"reference_field_id": "103147"}, 422),
    ("compare_ndvi", {"period": {"start": "2025-02-01", "end": "2025-01-01"}}, 422),
    ("compare_ndvi", {"dataset_id": str(uuid4())}, 404),
    ("compare_ndvi", {"dataset_id": "not-a-uuid"}, 422),
    ("execute_python", {}, 422),
    ("summarize_soil_analysis", {"metrics": ["INVENTED"]}, 422),
])
def test_diagnostics_reject_invalid_calls(arguments, tool, override, status):
    response = TestClient(app).post("/api/diagnostics/tools", json=dict(tool=tool, arguments={**arguments, **override}))
    assert response.status_code == status


@pytest.mark.parametrize("environment", ["presentation", "production", "test"])
def test_diagnostics_disabled_outside_development(monkeypatch, arguments, environment):
    monkeypatch.setenv("APP_ENV", environment)
    get_settings.cache_clear()
    try:
        response = TestClient(app).post("/api/diagnostics/tools", json=dict(tool="compare_ndvi", arguments=arguments))
        assert response.status_code == 404
    finally:
        get_settings.cache_clear()


def test_registry_can_share_investigation_local_ids(arguments):
    ids = EvidenceIdGenerator()
    assert execute_tool("compare_ndvi", arguments, ids=ids).evidence_id == "EV-NDVI-001"
    assert execute_tool("compare_ndvi", arguments, ids=ids).evidence_id == "EV-NDVI-002"


def test_uploaded_pairs_support_reverse_order_and_reject_crop_mismatch(presentation_package):
    result = _process_package(presentation_package)
    assert len(result.valid_pairs) == 4
    planting = presentation_package["LAYER_MAP_PLANTING.csv"].decode("utf-8-sig")
    lines = planting.splitlines()
    lines[2] = lines[2].replace("MILHO", "SOJA")
    presentation_package["LAYER_MAP_PLANTING.csv"] = "\n".join(lines).encode()
    result = _process_package(presentation_package)
    assert len(result.valid_pairs) == 2
    assert all(pair.purpose.value == "silage" for pair in result.valid_pairs)
