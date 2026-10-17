"""Bounded planning, structured synthesis and deterministic evidence checks."""

from datetime import datetime, timezone
import json
from time import perf_counter, sleep
from typing import Literal, Protocol
from uuid import UUID

from google.genai import types
from pydantic import Field, ValidationError

from app.analytics.contracts import ComparisonEvidence, NdviEvidence, SoilGroupsEvidence, SoilSummaryEvidence
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
from app.harness.fallback import build_fallback_report
from app.harness.trace import InvestigationRecorder, ToolExecutionError
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
    request = InvestigationRequest.model_validate(request.model_dump())
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
        calls_used = len(recorder.snapshot().calls)
        remaining = budget.remaining

        def finish(reason, error=None) -> ToolLoopResult:
            return ToolLoopResult(
                investigation_id=recorder.investigation_id, stop_reason=reason,
                evidence=evidence, trace=recorder.snapshot(), warnings=warnings, error=error,
            )

        try:
            while calls_used < max_calls:
                mode = types.FunctionCallingConfig(mode="AUTO") if comparison_allowed else types.FunctionCallingConfig(
                    mode="ANY", allowed_function_names=["validate_comparison"],
                )
                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT + "\n\n" + TOOL_LOOP_INSTRUCTION,
                    tools=[build_gemini_tool()], candidate_count=1,
                    tool_config=types.ToolConfig(function_calling_config=mode),
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                )
                response = budget.generate(client, contents, config)

                content = _response_content(response)
                calls = [part.function_call for part in content.parts if part.function_call is not None]
                if not calls:
                    if not comparison_allowed:
                        raise _StopLoop("comparison_required", "Execute validate_comparison antes de finalizar ou analisar.")
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
                    if not comparison_allowed and call.name != "validate_comparison":
                        raise _StopLoop("comparison_required", "Execute validate_comparison antes de qualquer análise.")
                    calls_used += 1
                    try:
                        result = recorder.run_tool(call.name, call.args)
                    except (ToolCallValidationError, ToolExecutionError) as error:
                        # A calculation failure stops the loop; the model must not fill gaps.
                        raise _StopLoop(error.code, str(error)) from None
                    evidence.append(result)
                    remaining()
                    if call.name == "validate_comparison":
                        assert isinstance(result, ComparisonEvidence)
                        if not result.allowed:
                            return finish("invalid_comparison", ToolCallError(
                                code="invalid_comparison", message="O par selecionado não permite esta comparação.",
                            ))
                        comparison_allowed = True
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
    if (planning.stop_reason not in ("model_finished", "tool_limit") or planning.error is not None
            or not comparisons or not all(item.allowed for item in comparisons)):
        raise SynthesisError(ToolCallError(
            code="synthesis_not_ready", message="A fase de ferramentas não permite iniciar a síntese.",
        ))
    try:
        context = (build_repair_context(planning.evidence, planning.warnings, _repair_error.error, _repair_error.issues)
                   if _repair_error is not None else build_synthesis_context(planning.evidence, planning.warnings))
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


_FALLBACK_ERRORS = frozenset({
    "missing_api_key", "authentication_error", "permission_denied", "model_not_found", "rate_limit",
    "timeout", "unavailable", "network_error", "invalid_request", "configuration_error", "api_error",
    "client_error", "invalid_response", "invalid_report", "invalid_report_evidence", "invalid_report_language",
})


def _local_plan(comparison: ComparisonEvidence, request: InvestigationRequest) -> list[tuple[str, dict]]:
    """At most seven more calls after preflight, chosen from available analyses."""
    args = request.model_dump(mode="json", exclude={"question"})
    soil = {"dataset_id": str(request.dataset_id)}
    available = set(comparison.available_analyses)
    calls = []
    if "summarize_soil_analysis" in available:
        calls.append(("summarize_soil_analysis", {**soil, "measurement_group": "group_1"}))
        if "compare_soil_measurement_groups" in available:
            calls.append(("summarize_soil_analysis", {**soil, "measurement_group": "group_2"}))
    if "compare_soil_measurement_groups" in available:
        calls.append(("compare_soil_measurement_groups", soil))
    if "compare_ndvi" in available:
        calls.append(("compare_ndvi", args))
    # This tool safely returns available=false when pre-planting data is absent.
    calls.append(("check_initial_condition", args))
    if "application_compliance" in available and comparison.common_operations:
        operation = min(comparison.common_operations, key=lambda name: (name != "CALAGEM", name))
        calls.append(("application_compliance", {**args, "operation": operation}))
    if "compare_population" in available:
        calls.append(("compare_population", args))
    return calls


def _accumulated_warnings(planning: ToolLoopResult) -> list[ValidationIssue]:
    warnings = [item.model_copy(deep=True) for item in planning.warnings]
    for evidence in planning.evidence:
        for message in evidence.warnings:
            warning = ValidationIssue(code="analysis_warning", message=message)
            if warning not in warnings:
                warnings.append(warning)
    return warnings


def run_investigation(request: InvestigationRequest, *, client: PlanningClient | None = None,
                      settings: Settings | None = None, store: SessionStore = dataset_store) -> InvestigationResponse:
    """Synchronous public workflow: preflight, model/local analysis, valid report.

    Preflight counts against the same eight-call/time budget and seeds the model
    loop. Fallback reuses facts after provider failures, even after the deadline;
    only local template rendering/validation may run after timeout, never tools.
    """
    request = InvestigationRequest.model_validate(request.model_dump())
    settings = (settings or get_settings()).model_copy(deep=True)
    budget = _GenerationBudget(settings.gemini_timeout_seconds)
    recorder = InvestigationRecorder(request, model=client.model if client is not None else settings.gemini_model, store=store)
    _, warnings = build_investigation_context(request, store.get(request.dataset_id), max_tool_calls=min(8, settings.gemini_max_tool_calls))
    try:
        budget.remaining()
        comparison = recorder.run_tool("validate_comparison", request.model_dump(mode="json", exclude={"question"}))
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
                              evidence=[comparison], trace=recorder.snapshot(), warnings=warnings)
    report = None
    fallback_reason = "missing_api_key"
    if client is None and not settings.gemini_configured:
        try:
            for name, arguments in _local_plan(comparison, request):
                if len(recorder.snapshot().calls) >= min(8, settings.gemini_max_tool_calls):
                    planning.stop_reason = "tool_limit"
                    break
                budget.remaining()
                planning.evidence.append(recorder.run_tool(name, arguments))
                budget.remaining()
        except _StopLoop:
            planning.stop_reason = "timeout"
            fallback_reason = "timeout"
        except (ToolCallValidationError, ToolExecutionError) as error:
            # Calculation failures stop the investigation, not an invitation to
            # the model or templates to fill missing results.
            raise InvestigationError(error.code, str(error)) from None
        planning.trace = recorder.snapshot()
    else:
        draft = run_investigation_draft(request, client=client, settings=settings, store=store,
                                        _budget=budget, _recorder=recorder, _comparison=comparison)
        planning, report = draft.planning, draft.report
        if report is None:
            if draft.error is None or draft.error.code not in _FALLBACK_ERRORS:
                error = draft.error or ToolCallError(code="investigation_failed", message="Não foi possível concluir a investigação.")
                raise InvestigationError(error.code, error.message)
            fallback_reason = draft.error.code
    warnings = _accumulated_warnings(planning)
    if report is None:
        fallback = build_fallback_report(planning.evidence, warnings, reason=fallback_reason)
        report, warnings, origin = fallback.report, fallback.warnings, fallback.generated_by
    else:
        origin = ReportOrigin.GEMINI
    return InvestigationResponse(
        investigation_id=planning.investigation_id, status="completed", generated_by=origin, report=report,
        evidence=planning.evidence, trace=planning.trace, warnings=warnings,
        chart_data=InvestigationChartData(
            ndvi=next((item for item in planning.evidence if isinstance(item, NdviEvidence)), None),
            soil_summaries=[item for item in planning.evidence if isinstance(item, SoilSummaryEvidence)],
            soil_groups=[item for item in planning.evidence if isinstance(item, SoilGroupsEvidence)],
        ),
    ).model_copy(deep=True)
