"""Closed structural contracts for investigation input, trace and output.

Dataset membership, evidence references, numbers in prose and causal language
are checked by the harness validators, not these structural schemas.
"""

from enum import Enum
from types import MappingProxyType
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime, BaseModel, Field, StrictInt, StringConstraints,
    ValidationInfo, field_validator, model_validator,
)

from app.analytics.contracts import (
    ApplicationArgs, ApplicationEvidence, ComparisonArgs, ComparisonEvidence,
    FieldApplicationEvidence, FieldNdviEvidence, FieldPopulationEvidence, InitialEvidence,
    NdviChangeEvidence, NdviEvidence, OperationNdviArgs, OperationNdviEvidence,
    PairedNdviTestEvidence, Period, PopulationEvidence, SingleApplicationArgs,
    SingleFieldArgs, SoilGroupsArgs, SoilGroupsEvidence, SoilStatisticalEvidence,
    SoilSummaryArgs, SoilSummaryEvidence,
)
from app.data.contracts import StrictModel, ValidationIssue
# Preserve the public imports used by W2 callers.
from app.harness.evidence_schema import Evidence, EvidenceId, FiniteValue, NonEmptyText


class EvidenceStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class ReportOrigin(str, Enum):
    GEMINI = "gemini"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class InvestigationRequest(StrictModel):
    dataset_id: UUID
    # Runtime routing metadata, not part of any analytical tool argument.
    analysis_mode: Literal["comparison", "single_field"] = Field(default="comparison", exclude=True)
    target_field_id: NonEmptyText
    reference_field_id: NonEmptyText | None = None
    period: Period
    question: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=10, max_length=500)
    ]

    @model_validator(mode="after")
    def scope_is_consistent(self):
        if self.analysis_mode == "comparison":
            if self.reference_field_id is None:
                raise ValueError("A comparação exige um talhão de referência.")
            if self.reference_field_id == self.target_field_id:
                raise ValueError("A comparação exige dois talhões distintos.")
        elif self.reference_field_id is not None:
            raise ValueError("A análise individual não aceita talhão de referência.")
        return self


class ToolName(str, Enum):
    VALIDATE_COMPARISON = "validate_comparison"
    COMPARE_NDVI = "compare_ndvi"
    TEST_PAIRED_NDVI_DIFFERENCE = "test_paired_ndvi_difference"
    ANALYZE_FIELD_NDVI = "analyze_field_ndvi"
    DETECT_FIELD_NDVI_CHANGES = "detect_field_ndvi_changes"
    ASSOCIATE_FIELD_OPERATIONS_NDVI = "associate_field_operations_ndvi"
    SUMMARIZE_FIELD_POPULATION = "summarize_field_population"
    SUMMARIZE_FIELD_APPLICATION = "summarize_field_application"
    CHECK_INITIAL_CONDITION = "check_initial_condition"
    COMPARE_POPULATION = "compare_population"
    APPLICATION_COMPLIANCE = "application_compliance"
    SUMMARIZE_SOIL_ANALYSIS = "summarize_soil_analysis"
    COMPARE_SOIL_MEASUREMENT_GROUPS = "compare_soil_measurement_groups"
    TEST_SOIL_MEASUREMENT_GROUPS = "test_soil_measurement_groups"


ToolArguments = (
    ApplicationArgs | ComparisonArgs | OperationNdviArgs | SingleApplicationArgs
    | SingleFieldArgs | SoilSummaryArgs | SoilGroupsArgs
)
# No registry import here: the executable registry itself imports Evidence.
_ARGUMENT_MODELS = MappingProxyType({
    ToolName.VALIDATE_COMPARISON: ComparisonArgs,
    ToolName.COMPARE_NDVI: ComparisonArgs,
    ToolName.TEST_PAIRED_NDVI_DIFFERENCE: ComparisonArgs,
    ToolName.ANALYZE_FIELD_NDVI: SingleFieldArgs,
    ToolName.DETECT_FIELD_NDVI_CHANGES: SingleFieldArgs,
    ToolName.ASSOCIATE_FIELD_OPERATIONS_NDVI: OperationNdviArgs,
    ToolName.SUMMARIZE_FIELD_POPULATION: SingleFieldArgs,
    ToolName.SUMMARIZE_FIELD_APPLICATION: SingleApplicationArgs,
    ToolName.CHECK_INITIAL_CONDITION: ComparisonArgs,
    ToolName.COMPARE_POPULATION: ComparisonArgs,
    ToolName.APPLICATION_COMPLIANCE: ApplicationArgs,
    ToolName.SUMMARIZE_SOIL_ANALYSIS: SoilSummaryArgs,
    ToolName.COMPARE_SOIL_MEASUREMENT_GROUPS: SoilGroupsArgs,
    ToolName.TEST_SOIL_MEASUREMENT_GROUPS: SoilGroupsArgs,
})


class ToolCallStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class ToolCallError(StrictModel):
    """Local error code and safe message; never a raw provider exception."""

    code: NonEmptyText
    message: NonEmptyText


class ToolCallTrace(StrictModel):
    """One known tool execution with normalized arguments and its outcome."""

    trace_id: UUID
    sequence: StrictInt = Field(ge=1)
    tool: ToolName
    arguments: ToolArguments
    result_evidence_ids: list[EvidenceId]
    source_files: list[NonEmptyText]
    tool_version: NonEmptyText
    started_at: AwareDatetime
    duration_ms: FiniteValue = Field(ge=0)
    status: ToolCallStatus
    error: ToolCallError | None = None

    @field_validator("arguments", mode="before")
    @classmethod
    def arguments_match_tool(cls, value, info: ValidationInfo):
        tool = info.data.get("tool")
        if tool is None:
            return value  # The tool field already reports the validation error.
        if isinstance(value, BaseModel):
            value = value.model_dump()
        return _ARGUMENT_MODELS[tool].model_validate(value)

    @model_validator(mode="after")
    def outcome_is_consistent(self):
        if self.status == ToolCallStatus.SUCCESS:
            if self.error is not None or not self.result_evidence_ids or not self.source_files:
                raise ValueError("Uma chamada bem-sucedida exige evidências, fontes e ausência de erro.")
        elif self.error is None or self.result_evidence_ids:
            raise ValueError("Uma chamada com falha exige erro controlado e não produz evidências.")
        return self


class ReportOverview(StrictModel):
    headline: NonEmptyText
    summary: NonEmptyText
    evidence_strength: EvidenceStrength


class ReportFinding(StrictModel):
    title: NonEmptyText
    explanation: NonEmptyText
    evidence_ids: list[EvidenceId] = Field(min_length=1)


class ReportLimitation(StrictModel):
    title: NonEmptyText
    explanation: NonEmptyText
    rule_id: NonEmptyText


class ReportRecommendation(StrictModel):
    action: NonEmptyText
    reason: NonEmptyText
    evidence_ids: list[EvidenceId] = Field(min_length=1)
    availability: Literal["continue_now", "needs_data", "needs_tooling"] = "continue_now"
    suggested_question: NonEmptyText | None = None


class InvestigationReport(StrictModel):
    """Narrative generated by Gemini or fallback; provenance is backend-owned."""

    overview: ReportOverview
    findings: list[ReportFinding]
    limitations: list[ReportLimitation] = Field(min_length=1)
    recommendations: list[ReportRecommendation]


AnalyticalEvidence = (
    ComparisonEvidence | NdviEvidence | InitialEvidence | PopulationEvidence
    | ApplicationEvidence | FieldNdviEvidence | FieldPopulationEvidence | FieldApplicationEvidence
    | NdviChangeEvidence | PairedNdviTestEvidence | OperationNdviEvidence
    | SoilSummaryEvidence | SoilGroupsEvidence | SoilStatisticalEvidence
)


class InvestigationChartData(StrictModel):
    """Selected tool outputs, preserving W2 series, quartiles, pairs and texture.

    Null/empty collections mean that no chart evidence is available. Soil lists
    support both measurement groups and calls with different metric filters.
    """

    ndvi: NdviEvidence | None = None
    field_ndvi: FieldNdviEvidence | None = None
    ndvi_tests: list[PairedNdviTestEvidence] = Field(default_factory=list)
    ndvi_changes: list[NdviChangeEvidence] = Field(default_factory=list)
    operation_ndvi: list[OperationNdviEvidence] = Field(default_factory=list)
    soil_summaries: list[SoilSummaryEvidence] = Field(default_factory=list)
    soil_groups: list[SoilGroupsEvidence] = Field(default_factory=list)
    soil_tests: list[SoilStatisticalEvidence] = Field(default_factory=list)


class InvestigationTrace(StrictModel):
    trace_id: UUID
    dataset_id: UUID
    model: NonEmptyText
    created_at: AwareDatetime
    calls: list[ToolCallTrace]
    repair: "ReportRepairTrace | None" = None


class ReportValidationIssue(StrictModel):
    code: str
    location: str
    message: str


class ReportRepairTrace(StrictModel):
    """One report-repair attempt; no prompt, raw response or report text."""

    attempt: Literal[1] = 1
    started_at: AwareDatetime
    duration_ms: FiniteValue = Field(ge=0)
    status: Literal["success", "error"]
    trigger: ToolCallError
    trigger_issues: list[ReportValidationIssue] = Field(default_factory=list)
    error: ToolCallError | None = None
    validation_issues: list[ReportValidationIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_outcome(self):
        if self.status == "success" and (self.error is not None or self.validation_issues):
            raise ValueError("Reparo bem-sucedido não pode conter erro final.")
        if self.status == "error" and self.error is None:
            raise ValueError("Reparo com falha exige erro final.")
        return self


InvestigationTrace.model_rebuild()


class InvestigationResponse(StrictModel):
    investigation_id: UUID
    question: NonEmptyText | None = None
    status: Literal["completed"]
    generated_by: ReportOrigin
    report: InvestigationReport
    evidence: list[AnalyticalEvidence]
    chart_data: InvestigationChartData
    trace: InvestigationTrace
    warnings: list[ValidationIssue]
