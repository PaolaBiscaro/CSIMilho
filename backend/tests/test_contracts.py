from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.data.contracts import (
    Centroid,
    DatasetStatus,
    DatasetValidationResponse,
    FieldManagement,
    FieldPurpose,
    FieldRecord,
    FileStatus,
    FileValidation,
    OperationLinkage,
    SoilAvailability,
    ValidPair,
)


def valid_field() -> FieldRecord:
    return FieldRecord(
        field_id="103144",
        farm_id="25213",
        name="Grão 4.0 - 19,3 ha",
        label="Grão 4.0",
        purpose=FieldPurpose.GRAIN,
        management=FieldManagement.DIGITAL,
        centroid=Centroid(longitude=-49.98, latitude=-22.24),
        geometry_available=True,
    )


def test_validation_response_accepts_normalized_objects() -> None:
    field = valid_field()
    response = DatasetValidationResponse(
        dataset_id=uuid4(),
        status=DatasetStatus.READY,
        quality_score=100,
        files=[FileValidation(name="fields.csv", status=FileStatus.VALID, size_bytes=120, rows=1)],
        fields=[field],
        valid_pairs=[
            ValidPair(target_field_id=field.field_id, reference_field_id="103145", purpose=FieldPurpose.GRAIN)
        ],
        available_operations=["CALAGEM"],
        soil=SoilAvailability(sample_count=2, measurement_groups=["group_1", "group_2"]),
        operation_linkage=OperationLinkage(assigned_rows=1),
        warnings=[],
        errors=[],
    )

    assert response.fields[0].centroid.longitude == -49.98
    assert response.status is DatasetStatus.READY
    assert response.soil.scope == "dataset"


def test_critical_contracts_reject_extra_fields() -> None:
    payload = valid_field().model_dump()
    payload["unexpected"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FieldRecord.model_validate(payload)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"longitude": "-49.98", "latitude": -22.24}, "valid number"),
        ({"longitude": -49.98, "latitude": -122.24}, "greater than or equal to -90"),
    ],
)
def test_centroid_rejects_wrong_types_and_ranges(payload: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Centroid.model_validate(payload)
