"""Record individual local tool executions; no Gemini loop or report generation."""

from datetime import datetime, timezone
from time import perf_counter_ns
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.analytics.common import AnalysisUnavailableError
from app.analytics.evidence import EvidenceIdGenerator
from app.data.loader import EXPECTED_FILE_NAMES
from app.data.session_store import DatasetNotFoundError, SessionStore, dataset_store
from app.harness import registry
from app.harness.schemas import Evidence, InvestigationRequest, InvestigationTrace, ToolCallError, ToolCallTrace
from app.harness.validators import ToolCallValidator


_ERROR_MESSAGES = {
    "analysis_unavailable": "Os dados disponíveis não permitem executar esta análise.",
    "dataset_not_found": "O dataset não está mais disponível para executar a ferramenta.",
    "invalid_tool_result": "A ferramenta retornou uma evidência inválida para esta análise.",
    "tool_execution_failed": "Não foi possível concluir a execução da ferramenta.",
}


class ToolExecutionError(RuntimeError):
    """Safe execution error, also available in the recorded failed call."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(_ERROR_MESSAGES[code])


class InvestigationRecorder:
    """One recorder per sequential investigation, kept only in memory.

    run_tool validates/reserves through W3.06 before executing. Rejected calls
    propagate ToolCallValidationError and create no execution entry. Accepted
    calls create exactly one success/error entry; failures raise a safe error.
    The orchestrator owns call budgets, comparison order and Gemini.
    """

    def __init__(self, request: InvestigationRequest, *, model: str,
                 store: SessionStore = dataset_store) -> None:
        self._validator = ToolCallValidator(request, store=store)
        self._store = store
        self._investigation_id = uuid4()
        self._trace = InvestigationTrace(
            trace_id=uuid4(), dataset_id=request.dataset_id, model=model,
            created_at=datetime.now(timezone.utc), calls=[],
        )
        self._ids = EvidenceIdGenerator()
        self._result_ids: set[str] = set()

    @property
    def investigation_id(self) -> UUID:
        return self._investigation_id

    @property
    def trace_id(self) -> UUID:
        return self._trace.trace_id

    def snapshot(self) -> InvestigationTrace:
        """Return a defensive copy with no question, raw data or provider config."""
        return self._trace.model_copy(deep=True)

    def run_tool(self, name: str, arguments: dict) -> Evidence:
        params = self._validator.validate_call(name, arguments)
        tool = registry.get_tool(name)
        # Keep trace arguments separate from the dictionary passed to execution.
        normalized = params.model_dump(mode="json")
        started_at = datetime.now(timezone.utc)
        start_ns = perf_counter_ns()
        error_code = None
        try:
            result = registry.execute_tool(
                name, params.model_dump(mode="json"), store=self._store, ids=self._ids,
            )
        except AnalysisUnavailableError:
            error_code = "analysis_unavailable"
        except DatasetNotFoundError:
            error_code = "dataset_not_found"
        except Exception:
            # Exception messages can contain rows, paths or other private input.
            # Do not log them, retain them or chain them to the public error.
            error_code = "tool_execution_failed"

        base = dict(
            trace_id=self.trace_id, sequence=len(self._trace.calls) + 1,
            tool=name, arguments=normalized, tool_version=tool.version,
            started_at=started_at, duration_ms=(perf_counter_ns() - start_ns) / 1_000_000,
        )
        if error_code is None:
            try:
                if not isinstance(result, Evidence):
                    raise ValueError("Expected an evidence model.")
                # Revalidate the full concrete result, including model_copy/construct
                # instances, before recording success or returning facts to Gemini.
                result = tool.result.model_validate(result.model_dump())
                # Project only audit metadata, never the full result/notes/series.
                entry = ToolCallTrace(
                    **base, result_evidence_ids=[result.evidence_id],
                    source_files=result.source_files, status="success",
                )
                if (result.tool_version != tool.version
                        or entry.result_evidence_ids[0] in self._result_ids
                        or any(source not in EXPECTED_FILE_NAMES for source in entry.source_files)):
                    raise ValueError("Inconsistent audit metadata.")
            except (ValidationError, ValueError, AttributeError, TypeError):
                error_code = "invalid_tool_result"

        if error_code is not None:
            self._trace.calls.append(ToolCallTrace(
                **base, result_evidence_ids=[], source_files=[], status="error",
                error=ToolCallError(code=error_code, message=_ERROR_MESSAGES[error_code]),
            ))
            # Raise outside the except blocks so no raw exception is retained.
            raise ToolExecutionError(error_code)

        self._trace.calls.append(entry)
        self._result_ids.add(entry.result_evidence_ids[0])
        return result
