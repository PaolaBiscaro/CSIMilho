"""Bounded planning, structured synthesis and deterministic evidence checks."""

from datetime import datetime, timezone
import json
from time import perf_counter, sleep
from typing import Literal, Protocol
from uuid import UUID

from google.genai import types
from pydantic import Field, ValidationError

from app.analytics.contracts import (
    ComparisonEvidence, FieldApplicationEvidence, FieldNdviEvidence, FieldPopulationEvidence,
    NdviChangeEvidence, NdviEvidence, OperationNdviEvidence, PairedNdviTestEvidence,
    SoilGroupsEvidence, SoilStatisticalEvidence, SoilSummaryEvidence,
)
from app.analytics.capabilities import missing_data_gap_for_tool
from app.config import Settings, get_settings
from app.data.contracts import StrictModel, ValidationIssue
from app.data.session_store import SessionStore, dataset_store
from app.harness import gemini_client
from app.harness.prompts import (
    SYSTEM_PROMPT, SYNTHESIS_INSTRUCTION, TOOL_LOOP_INSTRUCTION, REPAIR_INSTRUCTION,
    build_investigation_context, build_synthesis_context, build_repair_context,
)
from app.harness.registry import TOOLS, build_gemini_tool
from app.harness.schemas import (
    AnalyticalEvidence, InvestigationChartData, InvestigationReport, InvestigationRequest,
    InvestigationResponse, InvestigationTrace, ReportOrigin, ReportRepairTrace, ToolCallError,
)
from app.harness.trace import InvestigationRecorder, ProgressSink, ToolExecutionError
from app.harness.validators import ToolCallValidationError, ReportValidationError, validate_report_evidence
from app.harness.report_validation import ReportValidationIssue
from app.harness.language_validation import ReportLanguageError, validate_report_language


class PlanningClient(Protocol):
    @property
    def model(self) -> str: ...

    def generate_content(self, contents: list[types.Content], *, config: types.GenerateContentConfig,
                         timeout_seconds: float | None = None) -> types.GenerateContentResponse: ...


class ToolLoopResult(StrictModel):
    """Internal handoff to synthesis/fallback; never a completed report."""

    investigation_id: UUID
    stop_reason: Literal["model_finished", "tool_limit", "invalid_comparison", "error", "timeout"]
    evidence: list[AnalyticalEvidence]
    trace: InvestigationTrace
    warnings: list[ValidationIssue]
    question: str | None = None
    analysis_mode: Literal["comparison", "single_field"] = "comparison"
    error: ToolCallError | None = None


class _StopLoop(Exception):
    def __init__(self, code: str, message: str, reason: str = "error") -> None:
        self.error = ToolCallError(code=code, message=message)
        self.reason = reason


class InvestigationDraft(StrictModel):
    """Internal validated draft consumed by the complete investigation workflow."""

    planning: ToolLoopResult
    report: InvestigationReport | None = None
    error: ToolCallError | None = None
    validation_issues: list[ReportValidationIssue] = Field(default_factory=list)


class SynthesisError(RuntimeError):
    """Safe failure without raw model output or Pydantic input values."""

    def __init__(self, error: ToolCallError, issues: list[ReportValidationIssue] = ()) -> None:
        self.code = error.code
        self.error = error
        self.issues = list(issues)
        super().__init__(error.message)


class _GenerationBudget:
    """One deadline and one 429 retry shared across planning, synthesis and repair."""

    def __init__(self, seconds: float) -> None:
        self.deadline = perf_counter() + seconds
        self.retried_rate_limit = False

    def remaining(self) -> float:
        seconds = self.deadline - perf_counter()
        if seconds <= 0:
            raise _StopLoop("timeout", "O prazo total da investigação foi excedido.", "timeout")
        return seconds

    def generate(self, client: PlanningClient, contents: list[types.Content],
                 config: types.GenerateContentConfig) -> types.GenerateContentResponse:
        while True:
            seconds = self.remaining()
            try:
                response = client.generate_content(
                    [item.model_copy(deep=True) for item in contents],
                    config=config.model_copy(deep=True), timeout_seconds=seconds,
                )
            except gemini_client.GeminiError as error:
                self.remaining()
                if error.code == "rate_limit" and not self.retried_rate_limit:
                    self.retried_rate_limit = True
                    sleep(min(1.0, self.remaining()))
                    continue
                raise _StopLoop(error.code, str(error), "timeout" if error.code == "timeout" else "error") from None
            except Exception:
                self.remaining()
                raise _StopLoop("client_error", "Não foi possível obter a resposta do Gemini.") from None
            self.remaining()
            return response


def _response_content(response: types.GenerateContentResponse) -> types.Content:
    """Reject blocked, truncated, partial or ambiguous responses before executing."""
    invalid = _StopLoop("invalid_response", "O Gemini retornou uma resposta inválida.")
    if not isinstance(response, types.GenerateContentResponse):
        raise invalid
    if response.prompt_feedback and response.prompt_feedback.block_reason not in (
        None, types.BlockedReason.BLOCKED_REASON_UNSPECIFIED,
    ):
        raise invalid
    if not response.candidates or len(response.candidates) != 1:
        raise invalid
    candidate = response.candidates[0]
    if candidate.finish_reason not in (None, types.FinishReason.STOP):
        raise invalid
    content = candidate.content
    if not content or content.role != "model" or not content.parts:
        raise invalid
    call_ids = set()
    has_calls = False
    for part in content.parts:
        # Preserve supported text/thought/signature parts exactly in history.
        if set(part.model_dump(exclude_none=True)) - {"text", "thought", "thought_signature", "function_call"}:
            raise invalid
        call = part.function_call
        if call is not None:
            has_calls = True
            if part.thought or call.partial_args or call.will_continue:
                raise invalid
            if call.id is not None:
                if call.id in call_ids:
                    raise invalid
                call_ids.add(call.id)
    if not has_calls and not any(part.text and part.text.strip() and not part.thought for part in content.parts):
        raise invalid
    return content.model_copy(deep=True)


def run_investigation_tools(request: InvestigationRequest, *, client: PlanningClient | None = None,
                            settings: Settings | None = None,
                            store: SessionStore = dataset_store,
                            _budget: _GenerationBudget | None = None,
                            _recorder: InvestigationRecorder | None = None,
                            _comparison: ComparisonEvidence | None = None) -> ToolLoopResult:
    """Run one investigation's planning phase using local, sequential tools.

    Own/close the real client when none is supplied; injected clients belong to
    the caller. Invalid initial selections raise before contacting Gemini.
    Subsequent controlled failures return partial evidence and trace. Deadlines
    are checked between synchronous steps; local Python calls are not preempted.
    """
    settings = (settings or get_settings()).model_copy(deep=True)
    request = InvestigationRequest.model_validate({**request.model_dump(), "analysis_mode": request.analysis_mode})
    budget = _budget if _budget is not None else _GenerationBudget(settings.gemini_timeout_seconds)
    max_calls = min(8, settings.gemini_max_tool_calls)
    owned_client = client is None
    client = client if client is not None else gemini_client.GeminiClient(settings)
    try:
        recorder = _recorder if _recorder is not None else InvestigationRecorder(request, model=client.model, store=store)
        context, warnings = build_investigation_context(request, store.get(request.dataset_id), max_tool_calls=max_calls)
        evidence = [_comparison.model_copy(deep=True)] if _comparison is not None else []
        if _comparison is not None:
            # Backend preflight has already executed/recorded this tool. Supply
            # facts as data, not a fabricated model function call/history.
            payload = json.loads(context)
            payload["precomputed_evidence"] = [item.model_dump(mode="json") for item in evidence]
            context = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=context)])]
        comparison_allowed = _comparison is not None and _comparison.allowed
        single_mode = request.analysis_mode == "single_field"
        scope_ready = single_mode or comparison_allowed
        single_only_tools = {
            "analyze_field_ndvi",
            "detect_field_ndvi_changes",
            "associate_field_operations_ndvi",
            "summarize_field_population",
            "summarize_field_application",
        }
        allowed_tools = (
            [
                "analyze_field_ndvi",
                "detect_field_ndvi_changes",
                "associate_field_operations_ndvi",
                "summarize_field_population",
                "summarize_field_application",
                "summarize_soil_analysis",
                "compare_soil_measurement_groups",
                "test_soil_measurement_groups",
            ]
            if single_mode
            else [name for name in TOOLS if name not in single_only_tools]
        )
        calls_used = len(recorder.snapshot().calls)
        remaining = budget.remaining

        def finish(reason, error=None) -> ToolLoopResult:
            return ToolLoopResult(
                investigation_id=recorder.investigation_id, stop_reason=reason,
                evidence=evidence, trace=recorder.snapshot(), warnings=warnings,
                question=request.question, analysis_mode=request.analysis_mode, error=error,
            )

        try:
            while calls_used < max_calls:
                mode = (types.FunctionCallingConfig(mode="AUTO")
                        if scope_ready else types.FunctionCallingConfig(
                            mode="ANY", allowed_function_names=["validate_comparison"],
                        ))
                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT + "\n\n" + TOOL_LOOP_INSTRUCTION,
                    tools=[build_gemini_tool(allowed_tools if scope_ready else ["validate_comparison"])], candidate_count=1,
                    tool_config=types.ToolConfig(function_calling_config=mode),
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                )
                response = budget.generate(client, contents, config)

                content = _response_content(response)
                calls = [part.function_call for part in content.parts if part.function_call is not None]
                if not calls:
                    if not scope_ready:
                        raise _StopLoop("comparison_required", "Execute validate_comparison antes de finalizar ou analisar.")
                    if single_mode and not any(isinstance(item, (
                        FieldNdviEvidence, NdviChangeEvidence, OperationNdviEvidence,
                        FieldPopulationEvidence, FieldApplicationEvidence,
                    )) for item in evidence):
                        raise _StopLoop("analysis_required", "Execute ao menos uma análise individual antes de finalizar.")
                    # Free-form model text is only a completion signal, never a report.
                    return finish("model_finished")
                contents.append(content)  # Keep call IDs and thought signatures intact.
                responses = []
                for call in calls:
                    remaining()
                    if calls_used >= max_calls:
                        return finish("tool_limit")
                    if not isinstance(call.name, str) or call.name not in TOOLS:
                        raise _StopLoop("unknown_tool", "Ferramenta não permitida nesta investigação.")
                    if call.name not in allowed_tools and not (not scope_ready and call.name == "validate_comparison"):
                        raise _StopLoop("scope_mismatch", "A ferramenta não corresponde ao modo da investigação.")
                    if not scope_ready and call.name != "validate_comparison":
                        raise _StopLoop("comparison_required", "Execute validate_comparison antes de qualquer análise.")
                    calls_used += 1
                    try:
                        result = recorder.run_tool(call.name, call.args)
                    except ToolCallValidationError as error:
                        raise _StopLoop(error.code, str(error)) from None
                    except ToolExecutionError as error:
                        gap = missing_data_gap_for_tool(call.name) if error.code == "analysis_unavailable" else None
                        if gap is None or call.name == "validate_comparison":
                            # Infrastructure, invalid results and preflight failures
                            # remain fatal. Only unavailable optional analyses are partial.
                            raise _StopLoop(error.code, str(error)) from None
                        warning = gap.as_warning()
                        if warning not in warnings:
                            warnings.append(warning)
                        responses.append(types.Part(function_response=types.FunctionResponse(
                            id=call.id, name=call.name,
                            response={"error": {"code": gap.code, "message": gap.explanation}},
                        )))
                        continue
                    evidence.append(result)
                    remaining()
                    if call.name == "validate_comparison":
                        assert isinstance(result, ComparisonEvidence)
                        if not result.allowed:
                            return finish("invalid_comparison", ToolCallError(
                                code="invalid_comparison", message="O par selecionado não permite esta comparação.",
                            ))
                        comparison_allowed = True
                        scope_ready = True
                    responses.append(types.Part(function_response=types.FunctionResponse(
                        id=call.id, name=call.name, response={"output": result.model_dump(mode="json")},
                    )))
                contents.append(types.Content(role="user", parts=responses))
            # The synthesis phase will receive all evidence, including the last call.
            return finish("tool_limit")
        except _StopLoop as stopped:
            return finish(stopped.reason, stopped.error)
    finally:
        if owned_client:
            client.close()


def _schema_issues(error: ValidationError) -> list[ReportValidationIssue]:
    """Project trusted schema paths/types only; extra keys and inputs may be secrets."""
    allowed_fields = {
        "overview", "headline", "summary", "evidence_strength", "findings", "title", "explanation",
        "evidence_ids", "limitations", "rule_id", "recommendations", "action", "reason",
    }
    messages = {
        "missing": "Inclua o campo obrigatório conforme o schema.",
        "extra_forbidden": "Remova campos adicionais não previstos no schema.",
        "enum": "Use somente os valores enumerados no schema.",
        "too_short": "Respeite o tamanho mínimo exigido no schema.",
        "string_too_short": "Preencha o texto obrigatório.",
        "string_type": "Use texto no campo indicado.",
        "list_type": "Use uma lista no campo indicado.",
        "model_type": "Use um objeto conforme o schema.",
        "json_invalid": "Responda com um objeto JSON válido, sem texto externo.",
    }
    issues = []
    for detail in error.errors(include_url=False, include_context=False, include_input=False)[:50]:
        location = "report"
        for segment in detail["loc"]:
            if isinstance(segment, int):
                location += f"[{segment}]"
            elif segment in allowed_fields:
                location += "." + segment
            else:
                break
        kind = detail["type"] if detail["type"] in messages else "invalid_schema"
        issue = ReportValidationIssue(code="schema_" + kind, location=location,
                                      message=messages.get(kind, "Corrija o valor ou a estrutura conforme o schema."))
        if issue not in issues:
            issues.append(issue)
    return issues


def synthesize_report(planning: ToolLoopResult, *, client: PlanningClient,
                      settings: Settings | None = None,
                      _budget: _GenerationBudget | None = None,
                      _repair_error: SynthesisError | None = None) -> InvestigationReport:
    """Generate and fully validate one report; this function never loops on validation.

    The supplied client belongs to the caller. Standalone use starts a fresh
    budget; run_investigation_draft shares the investigation's original budget.
    """
    settings = settings or get_settings()
    budget = _budget if _budget is not None else _GenerationBudget(settings.gemini_timeout_seconds)
    failure = None
    validation_issues = []
    try:
        # Do not trust model_copy/model_construct to have validated nested facts.
        planning = ToolLoopResult.model_validate(planning.model_dump())
    except (ValidationError, ValueError, TypeError):
        failure = ToolCallError(code="invalid_synthesis_input", message="As evidências para a síntese são inválidas.")
    if failure is not None:
        raise SynthesisError(failure)
    comparisons = [item for item in planning.evidence if isinstance(item, ComparisonEvidence)]
    individual = [item for item in planning.evidence if isinstance(item, (
        FieldNdviEvidence, NdviChangeEvidence, OperationNdviEvidence,
        FieldPopulationEvidence, FieldApplicationEvidence,
    ))]
    if (planning.stop_reason not in ("model_finished", "tool_limit") or planning.error is not None
            or (not individual and (not comparisons or not all(item.allowed for item in comparisons)))):
        raise SynthesisError(ToolCallError(
            code="synthesis_not_ready", message="A fase de ferramentas não permite iniciar a síntese.",
        ))
    try:
        context = (build_repair_context(planning.evidence, planning.warnings, _repair_error.error,
                                        _repair_error.issues, planning.question, planning.analysis_mode)
                   if _repair_error is not None else build_synthesis_context(
                       planning.evidence, planning.warnings, planning.question, planning.analysis_mode))
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=context)])]
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT + "\n\n" + SYNTHESIS_INSTRUCTION +
                               ("\n\n" + REPAIR_INSTRUCTION if _repair_error is not None else ""),
            response_mime_type="application/json",
            response_json_schema=InvestigationReport.model_json_schema(),
            candidate_count=1,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = budget.generate(client, contents, config)
        content = _response_content(response)
        if any(part.function_call is not None for part in content.parts):
            raise _StopLoop("invalid_response", "A síntese não permite chamadas de ferramentas.")
        text = "".join(part.text for part in content.parts if part.text is not None and not part.thought)
        # Parse the actual output, never response.parsed (SDK parsing is not a trust boundary).
        report = InvestigationReport.model_validate_json(text)
        report = validate_report_evidence(report, planning.evidence, planning.warnings)
        report = validate_report_language(report)
        budget.remaining()
        return report
    except _StopLoop as stopped:
        failure = stopped.error
    except ValidationError as error:
        validation_issues = _schema_issues(error)
        failure = ToolCallError(
            code="invalid_report", message="A síntese não corresponde ao JSON de InvestigationReport.",
        )
    except ReportValidationError as error:
        validation_issues = error.issues
        failure = ToolCallError(code="invalid_report_evidence", message=str(error))
    except ReportLanguageError as error:
        validation_issues = error.issues
        failure = ToolCallError(code="invalid_report_language", message=str(error))
    # Raise outside handlers: neither provider bodies nor raw validation errors
    # are retained as the context of this public failure.
    raise SynthesisError(failure, validation_issues)


def run_investigation_draft(request: InvestigationRequest, *, client: PlanningClient | None = None,
                            settings: Settings | None = None,
                            store: SessionStore = dataset_store,
                            _budget: _GenerationBudget | None = None,
                            _recorder: InvestigationRecorder | None = None,
                            _comparison: ComparisonEvidence | None = None) -> InvestigationDraft:
    """Plan then synthesize with one client/budget, retaining evidence on failure.

    A rejected report gets at most one repair using the original facts/budget.
    run_investigation wraps this draft with fallback and the public response.
    """
    settings = (settings or get_settings()).model_copy(deep=True)
    budget = _budget if _budget is not None else _GenerationBudget(settings.gemini_timeout_seconds)
    owned_client = client is None
    client = client if client is not None else gemini_client.GeminiClient(settings)
    try:
        planning = run_investigation_tools(request, client=client, settings=settings, store=store, _budget=budget,
                                           _recorder=_recorder, _comparison=_comparison)
        if planning.stop_reason not in ("model_finished", "tool_limit") or planning.error is not None:
            return InvestigationDraft(planning=planning, error=planning.error)
        if _recorder is not None:
            _recorder.emit_progress("report_started", "Organizando os resultados em um relatório")
        try:
            report = synthesize_report(planning, client=client, settings=settings, _budget=budget)
        except SynthesisError as error:
            if error.code not in {"invalid_report", "invalid_report_evidence", "invalid_report_language"}:
                return InvestigationDraft(planning=planning, error=error.error, validation_issues=error.issues)
            # One branch, not a loop: validation failure of the replacement is final.
            started_at, start = datetime.now(timezone.utc), perf_counter()
            final_error = None
            report = None
            try:
                report = synthesize_report(planning, client=client, settings=settings, _budget=budget,
                                           _repair_error=error)
            except SynthesisError as repair_error:
                final_error = repair_error
            repair = ReportRepairTrace(
                started_at=started_at, duration_ms=max(0.0, (perf_counter() - start) * 1000),
                status="error" if final_error else "success", trigger=error.error,
                trigger_issues=error.issues, error=final_error.error if final_error else None,
                validation_issues=final_error.issues if final_error else [],
            )
            planning = planning.model_copy(deep=True)
            planning.trace.repair = repair
            if final_error:
                return InvestigationDraft(planning=planning, error=final_error.error,
                                          validation_issues=final_error.issues)
        return InvestigationDraft(planning=planning, report=report)
    finally:
        if owned_client:
            client.close()


class InvestigationError(RuntimeError):
    """Safe failure when a valid completed report cannot be produced."""

    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        self.error = ToolCallError(code=code, message=message)
        self.status_code = status_code
        super().__init__(message)


def _accumulated_warnings(planning: ToolLoopResult) -> list[ValidationIssue]:
    warnings = [item.model_copy(deep=True) for item in planning.warnings]
    for evidence in planning.evidence:
        for message in evidence.warnings:
            warning = ValidationIssue(code="analysis_warning", message=message)
            if warning not in warnings:
                warnings.append(warning)
    return warnings


def run_investigation(request: InvestigationRequest, *, client: PlanningClient | None = None,
                      settings: Settings | None = None, store: SessionStore = dataset_store,
                      progress_sink: ProgressSink | None = None) -> InvestigationResponse:
    """Synchronous legacy workflow that delivers only a Gemini-validated report.

    The dataset remains in the session after a provider failure, but deterministic
    fallback is never published as if it were the requested final report.
    """
    request = InvestigationRequest.model_validate({**request.model_dump(), "analysis_mode": request.analysis_mode})
    settings = (settings or get_settings()).model_copy(deep=True)
    budget = _GenerationBudget(settings.gemini_timeout_seconds)
    recorder = InvestigationRecorder(
        request, model=client.model if client is not None else settings.gemini_model,
        store=store, progress_sink=progress_sink,
    )
    _, warnings = build_investigation_context(request, store.get(request.dataset_id), max_tool_calls=min(8, settings.gemini_max_tool_calls))
    comparison = None
    if request.analysis_mode == "comparison":
        comparison_args = {
            "dataset_id": str(request.dataset_id), "target_field_id": request.target_field_id,
            "reference_field_id": request.reference_field_id, "period": request.model_dump(mode="json")["period"],
        }
        try:
            budget.remaining()
            comparison = recorder.run_tool("validate_comparison", comparison_args)
        except (ToolCallValidationError, ToolExecutionError) as error:
            raise InvestigationError(error.code, str(error)) from None
        except _StopLoop:
            raise InvestigationError("timeout", "O prazo terminou antes de obter evidências para o relatório.") from None
        assert isinstance(comparison, ComparisonEvidence)
        if not comparison.allowed:
            labels = {"same_crop": "culturas incompatíveis", "same_purpose": "finalidades incompatíveis"}
            reasons = [labels[item.id] for item in comparison.criteria if item.id in labels and item.satisfied is False]
            raise InvestigationError("invalid_comparison", "Par incompatível: " + "; ".join(reasons or ["os manejos precisam ser conhecidos e distintos"]) + ".", 422)
    planning = ToolLoopResult(investigation_id=recorder.investigation_id, stop_reason="model_finished",
                              evidence=[comparison] if comparison is not None else [], trace=recorder.snapshot(), warnings=warnings,
                              question=request.question, analysis_mode=request.analysis_mode)
    report = None
    recorder.emit_progress("planning", "Escolhendo as análises compatíveis com a pergunta e os dados")
    if client is None and not settings.gemini_configured:
        raise InvestigationError(
            "missing_api_key",
            "O relatório precisa do Gemini. Configure ao menos uma chave e tente novamente; o dataset foi preservado.",
            503,
        )
    else:
        draft = run_investigation_draft(request, client=client, settings=settings, store=store,
                                        _budget=budget, _recorder=recorder, _comparison=comparison)
        planning, report = draft.planning, draft.report
        if report is None:
            error = draft.error or ToolCallError(
                code="investigation_failed", message="Não foi possível concluir a investigação."
            )
            status = {
                "authentication_error": 401,
                "permission_denied": 403,
                "rate_limit": 429,
                "timeout": 504,
                "invalid_report": 502,
                "invalid_report_evidence": 502,
                "invalid_report_language": 502,
                "invalid_response": 502,
            }.get(error.code, 503)
            raise InvestigationError(
                error.code,
                error.message + " O dataset foi preservado para uma nova tentativa.",
                status,
            )
    warnings = _accumulated_warnings(planning)
    if report is None:
        raise InvestigationError(
            "investigation_failed",
            "Não foi possível produzir um relatório validado. O dataset foi preservado para uma nova tentativa.",
        )
    origin = ReportOrigin.GEMINI
    recorder.emit_progress("completed", "Investigação concluída")
    return InvestigationResponse(
        investigation_id=planning.investigation_id, question=request.question,
        status="completed", generated_by=origin, report=report,
        evidence=planning.evidence, trace=planning.trace, warnings=warnings,
        chart_data=InvestigationChartData(
            ndvi=next((item for item in planning.evidence if isinstance(item, NdviEvidence)), None),
            field_ndvi=next((item for item in planning.evidence if isinstance(item, FieldNdviEvidence)), None),
            ndvi_tests=[item for item in planning.evidence if isinstance(item, PairedNdviTestEvidence)],
            ndvi_changes=[item for item in planning.evidence if isinstance(item, NdviChangeEvidence)],
            operation_ndvi=[item for item in planning.evidence if isinstance(item, OperationNdviEvidence)],
            soil_summaries=[item for item in planning.evidence if isinstance(item, SoilSummaryEvidence)],
            soil_groups=[item for item in planning.evidence if isinstance(item, SoilGroupsEvidence)],
            soil_tests=[item for item in planning.evidence if isinstance(item, SoilStatisticalEvidence)],
        ),
    ).model_copy(deep=True)
