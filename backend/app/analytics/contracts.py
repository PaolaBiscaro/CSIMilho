"""Typed inputs and outputs of the deterministic analytical tools."""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.data.contracts import StrictModel
from app.harness.schemas import Evidence, FiniteValue, NonEmptyText


class DatePeriod(StrictModel):
    start: date
    end: date

    @model_validator(mode="after")
    def ordered(self):
        if self.start > self.end:
            raise ValueError("O início do período deve anteceder o fim.")
        return self


Period = Literal["full_season"] | DatePeriod
SoilMetricName = Literal[
    "ARGILA", "SILTE", "AREIA", "MO", "CTC", "CTCE", "PHCACL2", "CA", "SATCA",
    "MG", "SATMG", "K", "SATK", "P", "SATB", "AL", "SATAL", "S", "HAL", "SB",
    "B", "ZN", "MN", "CU", "FE",
]


class ComparisonArgs(StrictModel):
    dataset_id: UUID
    target_field_id: NonEmptyText
    reference_field_id: NonEmptyText
    period: Period = "full_season"


class ApplicationArgs(ComparisonArgs):
    operation: NonEmptyText = "CALAGEM"


class SoilSummaryArgs(StrictModel):
    dataset_id: UUID
    measurement_group: Literal["group_1", "group_2"] = "group_1"
    metrics: list[SoilMetricName] | None = Field(default=None, min_length=1)


class SoilGroupsArgs(StrictModel):
    dataset_id: UUID
    metrics: list[SoilMetricName] | None = Field(default=None, min_length=1)


class FieldEvidence(Evidence):
    target_field_id: NonEmptyText
    reference_field_id: NonEmptyText
    period: Period
    warnings: list[str] = Field(default_factory=list)


class NdviPoint(StrictModel):
    date: date
    target_ndvi: FiniteValue
    reference_ndvi: FiniteValue
    gap: FiniteValue


class NdviEvidence(FieldEvidence):
    paired_dates: int
    target_mean: FiniteValue
    reference_mean: FiniteValue
    mean_gap: FiniteValue
    negative_dates: int
    positive_dates: int
    equal_dates: int
    series: list[NdviPoint]


class InitialEvidence(FieldEvidence):
    available: bool
    cutoff_date: date | None
    paired_dates: int
    mean_gap: FiniteValue | None
    threshold: FiniteValue = 0.02
    different: bool | None
    rule_id: Literal["initial_gap_heuristic"] = "initial_gap_heuristic"


class Criterion(StrictModel):
    id: str
    label: str
    satisfied: bool | None
    detail: str


class ComparisonEvidence(FieldEvidence):
    allowed: bool
    score: int = Field(ge=0, le=5)
    max_score: Literal[5] = 5
    criteria: list[Criterion]
    available_analyses: list[str]
    common_operations: list[str]
    paired_dates: int


class RowCounts(StrictModel):
    valid: int
    discarded: int


class PopulationEvidence(FieldEvidence):
    target_population_per_ha: FiniteValue
    reference_population_per_ha: FiniteValue
    difference_percent: FiniteValue
    target_rows: RowCounts
    reference_rows: RowCounts


class ApplicationEvidence(FieldEvidence):
    operation: str
    target_compliance_percent: FiniteValue
    reference_compliance_percent: FiniteValue
    target_applied_dose: FiniteValue
    reference_applied_dose: FiniteValue
    target_configured_dose: FiniteValue
    reference_configured_dose: FiniteValue
    target_rows: RowCounts
    reference_rows: RowCounts
    dose_unit: Literal["kg/ha"] = "kg/ha"


class SoilMetric(StrictModel):
    name: SoilMetricName
    family: str
    unit: str | None = None
    valid_n: int
    missing_n: int
    mean: FiniteValue | None
    median: FiniteValue | None
    min: FiniteValue | None
    max: FiniteValue | None
    q1: FiniteValue | None
    q3: FiniteValue | None
    source_files: list[str]


class TextureSample(StrictModel):
    sample_id: str
    sand: FiniteValue
    silt: FiniteValue
    clay: FiniteValue
    original_total: FiniteValue
    original_sand: FiniteValue
    original_silt: FiniteValue
    original_clay: FiniteValue


class TextureComposition(StrictModel):
    unit: Literal["%"] = "%"
    method: str = "Normalização de AREIA, SILTE e ARGILA para soma de 100%, apenas quando a soma original está entre 95 e 105."
    valid_n: int
    excluded_n: int
    samples: list[TextureSample]
    source_files: list[str]


class SoilEvidence(Evidence):
    scope: Literal["dataset"] = "dataset"
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str]


class SoilSummaryEvidence(SoilEvidence):
    measurement_group: Literal["group_1", "group_2"]
    sample_count: int
    valid_values: int
    expected_values: int
    completeness_percent: FiniteValue | None
    metrics: list[SoilMetric]
    texture: TextureComposition


class SoilPair(StrictModel):
    sample_id: str
    group_1: FiniteValue
    group_2: FiniteValue
    delta: FiniteValue


class SoilPairedMetric(StrictModel):
    name: SoilMetricName
    family: str
    unit: str | None = None
    valid_n: int
    median_delta: FiniteValue | None
    pairs: list[SoilPair]
    source_files: list[str]


class SoilGroupsEvidence(SoilEvidence):
    comparison: Literal["group_2_minus_group_1"] = "group_2_minus_group_1"
    sample_count: int
    metrics: list[SoilPairedMetric]
