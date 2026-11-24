"""Closed contracts for the analytical chat and executive report v2.

These models define the target product without changing the current API yet.
The orchestrator will adopt them incrementally in later phases.
"""

from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictInt, StringConstraints, TypeAdapter, model_validator

from app.data.contracts import StrictModel
from app.harness.evidence_schema import EvidenceId, FiniteValue, NonEmptyText
from app.harness.schemas import AnalyticalEvidence, InvestigationChartData


ChatMessage = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=2, max_length=1000)
]


class QuestionIntent(str, Enum):
    DATA_CATALOG = "data_catalog"
    CAPABILITY_CATALOG = "capability_catalog"
    DESCRIPTIVE_QUERY = "descriptive_query"
    INVESTIGATIVE_QUERY = "investigative_query"
    CONTEXTUAL_FOLLOWUP = "contextual_followup"
    UNSUPPORTED_QUERY = "unsupported_query"


class RequestedMode(str, Enum):
    AUTO = "auto"
    DESCRIPTIVE = "descriptive"
    INVESTIGATIVE = "investigative"


class ChatResponseKind(str, Enum):
    DATA_CATALOG = "data_catalog"
    CAPABILITY_CATALOG = "capability_catalog"
    DESCRIPTIVE = "descriptive"
    INVESTIGATION_REPORT = "investigation_report"
    UNSUPPORTED = "unsupported"


class IntentReason(str, Enum):
    DATA_INVENTORY_REQUEST = "data_inventory_request"
    CAPABILITY_INVENTORY_REQUEST = "capability_inventory_request"
    DESCRIPTIVE_SUMMARY_REQUEST = "descriptive_summary_request"
    HYPOTHESIS_OR_RELATIONSHIP_REQUEST = "hypothesis_or_relationship_request"
    FOLLOWUP_REFERENCE = "followup_reference"
    OUTSIDE_SUPPORTED_SCOPE = "outside_supported_scope"


class GapType(str, Enum):
    MISSING_DATA = "missing_data"
    MISSING_TOOLING = "missing_tooling"
    SCIENTIFIC_LIMIT = "scientific_limit"
    OUT_OF_SCOPE = "out_of_scope"


class AnswerStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ExecutiveConclusionStatus(str, Enum):
    CONCLUSIVE = "conclusive"
    INDICATIVE = "indicative"
    INCONCLUSIVE = "inconclusive"
    NOT_ANALYZABLE = "not_analyzable"


class CapabilityAvailability(str, Enum):
    AVAILABLE_NOW = "available_now"
    NEEDS_DATA = "needs_data"
    NEEDS_TOOLING = "needs_tooling"


class ChatRequestV2(StrictModel):
    dataset_id: UUID
    message: ChatMessage
    requested_mode: RequestedMode = RequestedMode.AUTO
    prior_turn_id: UUID | None = None
    target_field_id: NonEmptyText | None = None
    reference_field_id: NonEmptyText | None = None


class IntentDecision(StrictModel):
    intent: QuestionIntent
    response_kind: ChatResponseKind
    reason: IntentReason
    requires_tools: bool
    requires_report: bool
    uses_conversation_context: bool

    @model_validator(mode="after")
    def decision_is_consistent(self):
        if self.requires_report != (self.response_kind == ChatResponseKind.INVESTIGATION_REPORT):
            raise ValueError("requires_report deve corresponder ao tipo investigation_report.")
        if self.uses_conversation_context != (self.intent == QuestionIntent.CONTEXTUAL_FOLLOWUP):
            raise ValueError("Somente contextual_followup pode reutilizar contexto da conversa.")
        expected = {
            QuestionIntent.DATA_CATALOG: ChatResponseKind.DATA_CATALOG,
            QuestionIntent.CAPABILITY_CATALOG: ChatResponseKind.CAPABILITY_CATALOG,
            QuestionIntent.DESCRIPTIVE_QUERY: ChatResponseKind.DESCRIPTIVE,
            QuestionIntent.INVESTIGATIVE_QUERY: ChatResponseKind.INVESTIGATION_REPORT,
            QuestionIntent.UNSUPPORTED_QUERY: ChatResponseKind.UNSUPPORTED,
        }.get(self.intent)
        if expected is not None and self.response_kind != expected:
            raise ValueError("A intenção não corresponde ao tipo de resposta.")
        return self


class AnswerGap(StrictModel):
    gap_type: GapType
    question_part: NonEmptyText
    explanation: NonEmptyText
    requirement: NonEmptyText


class DatasetAsset(StrictModel):
    name: NonEmptyText
    description: NonEmptyText
    available: bool
    record_count: StrictInt | None = Field(default=None, ge=0)
    supported_uses: list[NonEmptyText] = Field(default_factory=list)
    limitations: list[NonEmptyText] = Field(default_factory=list)


class CapabilityItem(StrictModel):
    capability_id: NonEmptyText
    title: NonEmptyText
    description: NonEmptyText
    category: Literal["catalog", "descriptive", "statistical", "temporal", "operational", "soil"]
    availability: CapabilityAvailability
    required_data: list[NonEmptyText]
    methods: list[NonEmptyText] = Field(default_factory=list)
    limitation: NonEmptyText | None = None


class DescriptiveInsight(StrictModel):
    title: NonEmptyText
    explanation: NonEmptyText
    evidence_ids: list[EvidenceId] = Field(min_length=1)
    chart_ids: list[NonEmptyText] = Field(default_factory=list)


class DataCatalogChatResponse(StrictModel):
    kind: Literal[ChatResponseKind.DATA_CATALOG] = ChatResponseKind.DATA_CATALOG
    status: Literal[AnswerStatus.COMPLETE] = AnswerStatus.COMPLETE
    answer: NonEmptyText
    assets: list[DatasetAsset] = Field(min_length=1)


class CapabilityCatalogChatResponse(StrictModel):
    kind: Literal[ChatResponseKind.CAPABILITY_CATALOG] = ChatResponseKind.CAPABILITY_CATALOG
    status: Literal[AnswerStatus.COMPLETE, AnswerStatus.PARTIAL]
    answer: NonEmptyText
    capabilities: list[CapabilityItem] = Field(min_length=1)
    gaps: list[AnswerGap] = Field(default_factory=list)

    @model_validator(mode="after")
    def partial_response_names_its_gaps(self):
        if (self.status == AnswerStatus.PARTIAL) != bool(self.gaps):
            raise ValueError("Catálogo parcial exige gaps; catálogo completo não aceita gaps.")
        return self


class DescriptiveChatResponse(StrictModel):
    kind: Literal[ChatResponseKind.DESCRIPTIVE] = ChatResponseKind.DESCRIPTIVE
    status: Literal[AnswerStatus.COMPLETE, AnswerStatus.PARTIAL]
    answer: NonEmptyText
    insights: list[DescriptiveInsight]
    gaps: list[AnswerGap] = Field(default_factory=list)

    @model_validator(mode="after")
    def partial_response_names_its_gaps(self):
        if (self.status == AnswerStatus.PARTIAL) != bool(self.gaps):
            raise ValueError("Resposta descritiva parcial exige gaps; resposta completa não aceita gaps.")
        return self


class ExecutiveAnswer(StrictModel):
    status: ExecutiveConclusionStatus
    headline: NonEmptyText = Field(max_length=180)
    answer: NonEmptyText = Field(max_length=1500)
    confidence: ConfidenceLevel
    main_caveat: NonEmptyText = Field(max_length=500)
    evidence_ids: list[EvidenceId] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_matches_status(self):
        is_not_analyzable = self.status == ExecutiveConclusionStatus.NOT_ANALYZABLE
        if is_not_analyzable == bool(self.evidence_ids):
            raise ValueError(
                "Resposta analisável exige evidências; resposta não analisável não pode declará-las."
            )
        return self


class ExecutiveInsight(StrictModel):
    claim: NonEmptyText = Field(max_length=240)
    analytical_method: NonEmptyText = Field(max_length=180)
    evidence_summary: NonEmptyText = Field(max_length=700)
    interpretation: NonEmptyText = Field(max_length=900)
    uncertainty: NonEmptyText = Field(max_length=600)
    evidence_ids: list[EvidenceId] = Field(min_length=1)
    chart_ids: list[NonEmptyText] = Field(default_factory=list)


class ExecutiveChartNarrative(StrictModel):
    chart_id: NonEmptyText
    title: NonEmptyText = Field(max_length=180)
    takeaway: NonEmptyText = Field(max_length=500)
    evidence_ids: list[EvidenceId] = Field(min_length=1)


class ExecutiveLimitation(StrictModel):
    limitation_type: GapType
    title: NonEmptyText
    explanation: NonEmptyText
    impact: NonEmptyText
    requirement: NonEmptyText


class HypothesisResult(StrictModel):
    hypothesis_id: NonEmptyText
    question: NonEmptyText
    null_hypothesis: NonEmptyText
    alternative_hypothesis: NonEmptyText
    method: NonEmptyText
    status: Literal["executed", "blocked"]
    sample_size: StrictInt | None = Field(default=None, ge=0)
    statistic_name: NonEmptyText | None = None
    statistic_value: FiniteValue | None = None
    p_value: FiniteValue | None = Field(default=None, ge=0, le=1)
    effect_size_name: NonEmptyText | None = None
    effect_size_value: FiniteValue | None = None
    evidence_ids: list[EvidenceId] = Field(default_factory=list)
    source_files: list[NonEmptyText] = Field(default_factory=list)
    blocker: AnswerGap | None = None

    @model_validator(mode="after")
    def result_is_consistent(self):
        if self.status == "blocked":
            if self.blocker is None or self.evidence_ids:
                raise ValueError("Hipótese bloqueada exige blocker e não pode declarar evidência produzida.")
        elif self.blocker is not None or not self.evidence_ids or not self.source_files:
            raise ValueError("Hipótese executada exige evidências e fontes, sem blocker.")
        return self


class TechnicalAppendix(StrictModel):
    hypotheses: list[HypothesisResult] = Field(min_length=1)
    methods_summary: list[NonEmptyText] = Field(min_length=1)
    source_files: list[NonEmptyText] = Field(min_length=1)


class ExecutiveInvestigationReportV2(StrictModel):
    question: ChatMessage
    scope_summary: NonEmptyText
    executive_answer: ExecutiveAnswer
    insights: list[ExecutiveInsight] = Field(max_length=5)
    charts: list[ExecutiveChartNarrative] = Field(max_length=8)
    unanswered_parts: list[AnswerGap] = Field(default_factory=list, max_length=8)
    limitations: list[ExecutiveLimitation] = Field(max_length=8)
    field_recommendations: list[NonEmptyText] = Field(default_factory=list, max_length=5)
    technical_appendix: TechnicalAppendix

    @model_validator(mode="after")
    def report_is_consistent(self):
        if self.executive_answer.status == ExecutiveConclusionStatus.NOT_ANALYZABLE and self.insights:
            raise ValueError("Relatório não analisável não pode declarar insights conclusivos.")
        if self.executive_answer.status != ExecutiveConclusionStatus.NOT_ANALYZABLE and not self.insights:
            raise ValueError("Relatório analisável exige ao menos um insight.")
        return self


class InvestigativeChatResponse(StrictModel):
    kind: Literal[ChatResponseKind.INVESTIGATION_REPORT] = ChatResponseKind.INVESTIGATION_REPORT
    status: Literal[AnswerStatus.COMPLETE, AnswerStatus.PARTIAL]
    report: ExecutiveInvestigationReportV2
    evidence: list[AnalyticalEvidence] = Field(default_factory=list)
    chart_data: InvestigationChartData = Field(default_factory=InvestigationChartData)

    @model_validator(mode="after")
    def partial_response_names_its_gaps(self):
        has_gaps = bool(self.report.unanswered_parts)
        if (self.status == AnswerStatus.PARTIAL) != has_gaps:
            raise ValueError("Relatório parcial exige unanswered_parts; relatório completo não aceita partes sem resposta.")
        return self


class UnsupportedChatResponse(StrictModel):
    kind: Literal[ChatResponseKind.UNSUPPORTED] = ChatResponseKind.UNSUPPORTED
    status: Literal[AnswerStatus.UNSUPPORTED, AnswerStatus.BLOCKED]
    answer: NonEmptyText
    gaps: list[AnswerGap] = Field(min_length=1)


ChatResponse = Annotated[
    DataCatalogChatResponse
    | CapabilityCatalogChatResponse
    | DescriptiveChatResponse
    | InvestigativeChatResponse
    | UnsupportedChatResponse,
    Field(discriminator="kind"),
]
CHAT_RESPONSE_ADAPTER = TypeAdapter(ChatResponse)


class ChatEnvelopeV2(StrictModel):
    turn_id: UUID
    intent: IntentDecision
    response: ChatResponse

    @model_validator(mode="after")
    def intent_matches_response(self):
        if self.intent.response_kind.value != self.response.kind.value:
            raise ValueError("A decisão de intenção não corresponde à resposta entregue.")
        return self
