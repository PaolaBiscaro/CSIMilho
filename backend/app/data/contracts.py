from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileStatus(str, Enum):
    MISSING = "missing"
    RECEIVED = "received"
    VALID = "valid"
    INVALID = "invalid"


class DatasetStatus(str, Enum):
    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    ERROR = "error"


class FieldPurpose(str, Enum):
    GRAIN = "grain"
    SILAGE = "silage"
    UNKNOWN = "unknown"


class FieldManagement(str, Enum):
    DIGITAL = "digital"
    CONVENTIONAL = "conventional"
    UNKNOWN = "unknown"


class FileValidation(StrictModel):
    name: StrictStr
    status: FileStatus
    size_bytes: StrictInt = Field(ge=0)
    rows: StrictInt | None = Field(default=None, ge=0)
    encoding: StrictStr | None = None
    delimiter: StrictStr | None = Field(default=None, pattern=r"^[,;]$")


class Centroid(StrictModel):
    longitude: StrictFloat = Field(ge=-180, le=180)
    latitude: StrictFloat = Field(ge=-90, le=90)


class FieldRecord(StrictModel):
    field_id: StrictStr
    farm_id: StrictStr
    name: StrictStr
    label: StrictStr
    purpose: FieldPurpose
    management: FieldManagement
    centroid: Centroid
    geometry_available: bool


class ValidationIssue(StrictModel):
    code: StrictStr
    message: StrictStr
    file: StrictStr | None = None
    row: StrictInt | None = Field(default=None, ge=1)


class ValidPair(StrictModel):
    target_field_id: StrictStr
    reference_field_id: StrictStr
    purpose: FieldPurpose


class OperationLinkage(StrictModel):
    assigned_rows: StrictInt = Field(default=0, ge=0)
    unassigned_rows: StrictInt = Field(default=0, ge=0)
    invalid_geometry_rows: StrictInt = Field(default=0, ge=0)
    ambiguous_rows: StrictInt = Field(default=0, ge=0)


class SoilAvailability(StrictModel):
    sample_count: StrictInt = Field(default=0, ge=0)
    scope: Literal["dataset"] = "dataset"
    measurement_groups: list[StrictStr] = Field(default_factory=list)


class DatasetValidationResponse(StrictModel):
    dataset_id: UUID | None
    status: DatasetStatus
    quality_score: StrictInt = Field(ge=0, le=100)
    files: list[FileValidation]
    fields: list[FieldRecord]
    valid_pairs: list[ValidPair]
    available_operations: list[StrictStr]
    soil: SoilAvailability
    operation_linkage: OperationLinkage
    warnings: list[ValidationIssue]
    errors: list[ValidationIssue]
