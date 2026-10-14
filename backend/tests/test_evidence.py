import json
from typing import Literal

import pytest
from pydantic import StrictBool, StrictInt, ValidationError

from app.analytics.evidence import EvidenceIdGenerator
from app.data.contracts import StrictModel
from app.harness.schemas import Evidence, FiniteValue


def evidence_payload(**overrides) -> dict:
    return {
        "evidence_id": "EV-NDVI-001",
        "unit": "ndvi",
        "source_files": ["ndvi_metadata.csv"],
        "method": "inner join por data e média do gap",
        "observation_count": 3,
        "tool_version": "1.0.0",
        "metric": "mean_gap",
        "target_value": 0.4,
        "reference_value": 0.5,
        "difference": -0.1,
        **overrides,
    }


def test_evidence_preserves_values_and_provenance_in_json() -> None:
    evidence = Evidence(**evidence_payload(notes=["Sem interpolação."]))
    restored = Evidence.model_validate_json(evidence.model_dump_json())

    assert restored == evidence
    assert restored.difference == -0.1
    assert restored.source_files == ["ndvi_metadata.csv"]
    assert restored.notes == ["Sem interpolação."]
    assert restored.tool_version == "1.0.0"


def test_unavailable_values_and_unknown_unit_remain_null() -> None:
    evidence = Evidence(**evidence_payload(
        unit=None, observation_count=None, metric=None,
        target_value=None, reference_value=None, difference=None,
    ))
    payload = json.loads(evidence.model_dump_json())
    for field in ("unit", "observation_count", "metric", "target_value", "reference_value", "difference"):
        assert payload[field] is None


@pytest.mark.parametrize("field", ["evidence_id", "unit", "source_files", "method", "observation_count", "tool_version"])
def test_common_metadata_must_be_explicit(field: str) -> None:
    payload = evidence_payload()
    del payload[field]
    with pytest.raises(ValidationError):
        Evidence(**payload)


@pytest.mark.parametrize("overrides", [
    {"evidence_id": "EV-NDVI-1"},
    {"evidence_id": ""},
    {"source_files": []},
    {"source_files": [" "]},
    {"method": " "},
    {"tool_version": ""},
    {"unit": ""},
    {"unit": 1},
    {"notes": [False]},
    {"observation_count": -1},
    {"observation_count": "3"},
    {"observation_count": True},
    {"observation_count": 1.5},
    {"target_value": "0.4"},
    {"reference_value": True},
    {"unexpected": "extra"},
])
def test_evidence_rejects_invalid_metadata_and_types(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        Evidence(**evidence_payload(**overrides))


@pytest.mark.parametrize("field", ["target_value", "reference_value", "difference"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_evidence_rejects_nonfinite_values(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        Evidence(**evidence_payload(**{field: value}))


@pytest.mark.parametrize(("prefix", "unit", "source"), [
    pytest.param("COMP", None, "fields.csv", id="validate_comparison"),
    pytest.param("NDVI", "ndvi", "ndvi_metadata.csv", id="compare_ndvi"),
    pytest.param("INITIAL", "ndvi", "ndvi_metadata.csv", id="check_initial_condition"),
    pytest.param("POP", "plants/ha", "LAYER_MAP_PLANTING.csv", id="compare_population"),
    pytest.param("APP-CALAGEM", "%", "LAYER_MAP_FERTILIZATION.csv", id="application_compliance"),
    pytest.param("SOIL-SUMMARY", None, "soil_analysis.csv", id="summarize_soil_analysis"),
    pytest.param("SOIL-GROUPS", None, "soil_analysis.csv", id="compare_soil_measurement_groups"),
])
def test_future_tools_can_inherit_or_compose_evidence(prefix: str, unit: str | None, source: str) -> None:
    # Test-only extensions verify the protocol without implementing any tool.
    class ExtendedEvidence(Evidence):
        available: StrictBool

    class ComposedResult(StrictModel):
        evidence: Evidence
        available: StrictBool

    payload = evidence_payload(
        evidence_id=EvidenceIdGenerator().next_id(prefix), unit=unit,
        source_files=[source], metric=None, target_value=None,
        reference_value=None, difference=None,
    )
    inherited = ExtendedEvidence(**payload, available=True)
    composed = ComposedResult(evidence=Evidence(**payload), available=True)
    assert ExtendedEvidence.model_validate_json(inherited.model_dump_json()) == inherited
    assert ComposedResult.model_validate_json(composed.model_dump_json()) == composed
    assert inherited.model_dump(exclude={"available"}) == composed.evidence.model_dump()
    assert ExtendedEvidence.model_json_schema()["additionalProperties"] is False


def test_dataset_soil_extension_supports_multiple_metrics_without_field_ids() -> None:
    class Metric(StrictModel):
        name: str
        unit: str | None
        valid_n: StrictInt
        mean: FiniteValue | None

    class SoilEvidence(Evidence):
        scope: Literal["dataset"] = "dataset"
        metrics: list[Metric]

    payload = evidence_payload(
        evidence_id="EV-SOIL-SUMMARY-001", unit=None, metric=None,
        source_files=["soil_analysis.csv"], target_value=None,
        reference_value=None, difference=None,
    )
    soil = SoilEvidence(**payload, metrics=[Metric(name="PHCACL2", unit=None, valid_n=0, mean=None)])
    assert soil.scope == "dataset"
    assert soil.metrics[0].mean is None
    for field in ("target_field_id", "reference_field_id"):
        with pytest.raises(ValidationError):
            SoilEvidence(**soil.model_dump(), **{field: "field-1"})


def test_generator_is_repeatable_unique_and_scoped_to_each_investigation() -> None:
    prefixes = ["NDVI", "COMP", "NDVI", "APP-CALAGEM", "APP-GESSAGEM", "APP-CALAGEM"]
    expected = ["EV-NDVI-001", "EV-COMP-001", "EV-NDVI-002", "EV-APP-CALAGEM-001", "EV-APP-GESSAGEM-001", "EV-APP-CALAGEM-002"]
    first, second = EvidenceIdGenerator(), EvidenceIdGenerator()
    assert [first.next_id(prefix) for prefix in prefixes] == expected
    assert [second.next_id(prefix) for prefix in prefixes] == expected
    assert len(set(expected)) == len(expected)
    assert first.next_id("NDVI") == "EV-NDVI-003"
    assert EvidenceIdGenerator().next_id("NDVI") == "EV-NDVI-001"


@pytest.mark.parametrize("prefix", ["", "ndvi", "NDVI ", "NDVI\n", "APP--CALAGEM", "../NDVI", "NDVI-001", None, 1])
def test_generator_rejects_invalid_prefix_without_consuming_ids(prefix) -> None:
    generator = EvidenceIdGenerator()
    with pytest.raises(ValueError):
        generator.next_id(prefix)
    assert generator.next_id("NDVI") == "EV-NDVI-001"


def test_counter_does_not_wrap_after_three_digits() -> None:
    generator = EvidenceIdGenerator()
    ids = [generator.next_id("NDVI") for _ in range(1000)]
    assert len(set(ids)) == 1000
    assert ids[-1] == "EV-NDVI-1000"
    assert Evidence(**evidence_payload(evidence_id=ids[-1])).evidence_id == ids[-1]
