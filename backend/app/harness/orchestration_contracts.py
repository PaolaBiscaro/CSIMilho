"""Closed internal contracts for analytical chat orchestration."""

from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictInt, model_validator

from app.data.contracts import StrictModel
from app.harness.chat_contracts import AnswerGap, IntentDecision
from app.harness.evidence_schema import EvidenceId, NonEmptyText
from app.harness.schemas import AnalyticalEvidence


class OrchestrationStage(str, Enum):
    QUESTION_RECEIVED = "question_received"
    INTENT_CLASSIFIED = "intent_classified"
    CONTEXT_LOADED = "context_loaded"
    HYPOTHESES_PLANNED = "hypotheses_planned"
    DATA_CHECKED = "data_checked"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_BLOCKED = "tool_blocked"
    EVIDENCE_INTEGRATED = "evidence_integrated"
    CONCLUSION_READY = "conclusion_ready"


class OrchestrationEvent(StrictModel):
    sequence: StrictInt = Field(ge=1)
    stage: OrchestrationStage
    message: NonEmptyText
    tool: NonEmptyText | None = None
    evidence_ids: list[EvidenceId] = Field(default_factory=list)
    gap: AnswerGap | None = None

    @model_validator(mode="after")
    def stage_fields_are_safe_and_consistent(self):
        tool_stage = self.stage in {
            OrchestrationStage.TOOL_STARTED,
            OrchestrationStage.TOOL_COMPLETED,
            OrchestrationStage.TOOL_BLOCKED,
        }
        if tool_stage != (self.tool is not None):
            raise ValueError("Eventos de ferramenta exigem tool; outros eventos não aceitam tool.")
        if self.stage == OrchestrationStage.TOOL_COMPLETED and not self.evidence_ids:
            raise ValueError("Ferramenta concluída exige ao menos uma evidência.")
        if self.stage == OrchestrationStage.TOOL_BLOCKED and self.gap is None:
            raise ValueError("Ferramenta bloqueada exige a lacuna classificada.")
        return self


class AnalyticalHypothesisPlan(StrictModel):
    hypothesis_id: NonEmptyText
    question: NonEmptyText
    scope: Literal["single_field", "comparison", "dataset"]
    tools: list[NonEmptyText] = Field(min_length=1)
    status: Literal["planned", "executed", "partially_executed", "blocked"]
    evidence_ids: list[EvidenceId] = Field(default_factory=list)
    gaps: list[AnswerGap] = Field(default_factory=list)

    @model_validator(mode="after")
    def status_matches_results(self):
        if self.status == "executed" and (not self.evidence_ids or self.gaps):
            raise ValueError("Hipótese executada exige evidências e não aceita lacunas.")
        if self.status == "partially_executed" and (not self.evidence_ids or not self.gaps):
            raise ValueError("Hipótese parcial exige evidências e lacunas.")
        if self.status == "blocked" and (self.evidence_ids or not self.gaps):
            raise ValueError("Hipótese bloqueada exige lacunas e não pode declarar evidências.")
        return self


class ToolExecutionSummary(StrictModel):
    tool: NonEmptyText
    status: Literal["completed", "blocked"]
    evidence_ids: list[EvidenceId] = Field(default_factory=list)
    source_files: list[NonEmptyText] = Field(default_factory=list)
    gap: AnswerGap | None = None

    @model_validator(mode="after")
    def result_is_consistent(self):
        completed = self.status == "completed"
        if completed and (not self.evidence_ids or not self.source_files or self.gap is not None):
            raise ValueError("Execução concluída exige evidência e fontes, sem lacuna.")
        if not completed and (self.evidence_ids or self.source_files or self.gap is None):
            raise ValueError("Execução bloqueada exige lacuna e não produz evidência.")
        return self


class IntegratedConclusion(StrictModel):
    status: Literal["answered", "partially_answered", "not_answered"]
    answer: NonEmptyText
    evidence_ids: list[EvidenceId] = Field(default_factory=list)
    gaps: list[AnswerGap] = Field(default_factory=list)

    @model_validator(mode="after")
    def answer_matches_support(self):
        if self.status == "answered" and (not self.evidence_ids or self.gaps):
            raise ValueError("Conclusão respondida exige evidências e não aceita lacunas.")
        if self.status == "partially_answered" and (not self.evidence_ids or not self.gaps):
            raise ValueError("Conclusão parcial exige evidências e lacunas.")
        if self.status == "not_answered" and (self.evidence_ids or not self.gaps):
            raise ValueError("Conclusão não respondida exige lacunas e não declara evidências.")
        return self


class ChatOrchestrationRun(StrictModel):
    turn_id: UUID
    dataset_id: UUID
    intent: IntentDecision
    target_field_id: NonEmptyText | None = None
    reference_field_id: NonEmptyText | None = None
    hypotheses: list[AnalyticalHypothesisPlan]
    executions: list[ToolExecutionSummary]
    evidence: list[AnalyticalEvidence]
    conclusion: IntegratedConclusion | None = None
    events: list[OrchestrationEvent] = Field(min_length=2)

    @model_validator(mode="after")
    def trace_is_ordered_and_complete(self):
        if [event.sequence for event in self.events] != list(range(1, len(self.events) + 1)):
            raise ValueError("A sequência do trace deve ser contínua e ordenada.")
        if self.events[0].stage != OrchestrationStage.QUESTION_RECEIVED:
            raise ValueError("O trace deve começar pelo recebimento da pergunta.")
        if self.conclusion is not None and self.events[-1].stage != OrchestrationStage.CONCLUSION_READY:
            raise ValueError("Uma conclusão exige o evento final conclusion_ready.")
        ranks = {
            OrchestrationStage.QUESTION_RECEIVED: 0,
            OrchestrationStage.INTENT_CLASSIFIED: 1,
            OrchestrationStage.CONTEXT_LOADED: 2,
            OrchestrationStage.HYPOTHESES_PLANNED: 3,
            OrchestrationStage.DATA_CHECKED: 4,
            OrchestrationStage.TOOL_STARTED: 5,
            OrchestrationStage.TOOL_COMPLETED: 5,
            OrchestrationStage.TOOL_BLOCKED: 5,
            OrchestrationStage.EVIDENCE_INTEGRATED: 6,
            OrchestrationStage.CONCLUSION_READY: 7,
        }
        event_ranks = [ranks[event.stage] for event in self.events]
        if event_ranks != sorted(event_ranks):
            raise ValueError("As etapas do trace estão fora de ordem.")
        evidence_ids = {item.evidence_id for item in self.evidence}
        declared_ids = {
            evidence_id
            for execution in self.executions
            for evidence_id in execution.evidence_ids
        }
        if declared_ids != evidence_ids:
            raise ValueError("As execuções devem corresponder exatamente às evidências preservadas.")
        if self.conclusion is not None and set(self.conclusion.evidence_ids) != evidence_ids:
            raise ValueError("A conclusão deve declarar exatamente as evidências integradas.")
        return self


class ConversationTurnMemory(StrictModel):
    turn_id: UUID
    dataset_id: UUID
    intent: IntentDecision
    target_field_id: NonEmptyText | None = None
    reference_field_id: NonEmptyText | None = None
    hypothesis_ids: list[NonEmptyText]
    evidence_ids: list[EvidenceId]
    conclusion_status: Literal["answered", "partially_answered", "not_answered"] | None
    conclusion_summary: NonEmptyText | None
    gap_types: list[Literal["missing_data", "missing_tooling", "scientific_limit", "out_of_scope"]]
