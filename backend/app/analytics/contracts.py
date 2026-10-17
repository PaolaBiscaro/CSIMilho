"""Typed inputs and outputs of the deterministic analytical tools."""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.data.contracts import StrictModel
from app.harness.evidence_schema import Evidence, FiniteValue, NonEmptyText


class DatePeriod(StrictModel):
    start: date = Field(description="Data inicial inclusiva no formato ISO YYYY-MM-DD.")
    end: date = Field(description="Data final inclusiva no formato ISO YYYY-MM-DD, igual ou posterior ao início.")

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
    dataset_id: UUID = Field(description="UUID do dataset validado da sessão, fornecido pelo harness.")
    target_field_id: NonEmptyText = Field(description="ID textual normalizado do talhão alvo selecionado; preservar na investigação.")
    reference_field_id: NonEmptyText = Field(description="ID textual normalizado do talhão de referência selecionado; não inverter com o alvo.")
    period: Period = Field(default="full_season", description="Período selecionado: full_season usa todos os dados disponíveis; start/end limita às datas inclusivas. Preservar a seleção do harness.")


class ApplicationArgs(ComparisonArgs):
    operation: NonEmptyText = Field(default="CALAGEM", description="Nome da operação disponível no dataset; CALAGEM é a operação padrão prioritária.")


class SoilSummaryArgs(StrictModel):
    dataset_id: UUID = Field(description="UUID do dataset validado da sessão; solo tem escopo geral, sem vínculo com talhão.")
    measurement_group: Literal["group_1", "group_2"] = Field(default="group_1", description="group_1 é Conjunto 1 e group_2 é Conjunto 2; não representam profundidade ou data documentada.")
    metrics: list[SoilMetricName] | None = Field(default=None, min_length=1, description="Variáveis permitidas a resumir. Omitir ou usar null para todas as disponíveis; lista vazia não é válida.")


class SoilGroupsArgs(StrictModel):
    dataset_id: UUID = Field(description="UUID do dataset validado da sessão; solo tem escopo geral, sem vínculo com talhão.")
    metrics: list[SoilMetricName] | None = Field(default=None, min_length=1, description="Variáveis permitidas para parear por amostra; delta é Conjunto 2 menos Conjunto 1. Omitir ou usar null para todas as disponíveis; lista vazia não é válida.")


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
