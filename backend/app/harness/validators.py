"""Public harness validators for tool calls and evidence-backed reports."""

import json

from pydantic import BaseModel, ValidationError

from app.analytics.common import canonical_operation
from app.analytics.contracts import ApplicationArgs, ComparisonArgs, SoilGroupsArgs, SoilSummaryArgs
from app.data.session_store import DatasetNotFoundError, SessionStore, dataset_store
from app.harness.registry import TOOLS
from app.harness.schemas import InvestigationRequest
from app.harness.report_validation import (
    ReportValidationError, ReportValidationIssue, required_limitations, validate_report_evidence,
)
from app.harness.language_validation import ReportLanguageError, validate_report_language


_MESSAGES = {
    "unknown_tool": "Ferramenta não permitida nesta investigação.",
    "invalid_arguments": "Argumentos inválidos ou campos não permitidos para a ferramenta.",
    "dataset_mismatch": "A chamada não pode trocar o dataset da investigação.",
    "dataset_not_found": "O dataset da investigação não está mais disponível na sessão.",
    "field_not_found": "Talhão inexistente no dataset da investigação.",
    "invalid_pair": "A investigação exige dois talhões distintos.",
    "pair_changed": "A chamada deve preservar o alvo e a referência selecionados.",
    "period_changed": "A chamada deve preservar o período selecionado.",
    "duplicate_call": "Esta ferramenta já foi solicitada com os mesmos argumentos.",
}


class ToolCallValidationError(ValueError):
    """Safe local error; no model input or Pydantic error details are exposed."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(_MESSAGES[code])


class ToolCallValidator:
    """Create once per investigation and use sequentially before tool execution.

    An accepted call is reserved immediately, even if execution later fails.
    Rejected calls do not reserve anything. Use the returned normalized arguments
    for execution/trace, not the original untrusted dictionary. Comparability,
    tool budgets, execution and trace collection belong to the orchestrator.
    """

    def __init__(self, request: InvestigationRequest, *, store: SessionStore = dataset_store) -> None:
        # Revalidate a copy: caller mutation must not change the selected scope.
        self._request = InvestigationRequest.model_validate(request.model_dump())
        self._store = store
        self._seen: set[tuple[str, str]] = set()
        self._field_ids()

    def _field_ids(self) -> set[str]:
        try:
            dataset = self._store.get(self._request.dataset_id)
        except DatasetNotFoundError:
            raise ToolCallValidationError("dataset_not_found") from None
        field_ids = {field.field_id for field in dataset.fields}
        if self._request.target_field_id not in field_ids or self._request.reference_field_id not in field_ids:
            raise ToolCallValidationError("field_not_found")
        if self._request.target_field_id == self._request.reference_field_id:
            raise ToolCallValidationError("invalid_pair")
        return field_ids

    def validate_call(self, name: str, arguments: dict) -> BaseModel:
        """Validate, normalize and reserve one call; return its typed arguments."""
        if not isinstance(name, str) or name not in TOOLS:
            raise ToolCallValidationError("unknown_tool")
        # Only accept the object shape returned by Function Calling. In particular,
        # do not accept prebuilt models that could bypass Pydantic revalidation.
        if not isinstance(arguments, dict):
            raise ToolCallValidationError("invalid_arguments")
        try:
            params = TOOLS[name].parameters.model_validate(arguments)
        except ValidationError:
            raise ToolCallValidationError("invalid_arguments") from None
        if params.dataset_id != self._request.dataset_id:
            raise ToolCallValidationError("dataset_mismatch")
        field_ids = self._field_ids()
        if isinstance(params, ComparisonArgs):
            if params.target_field_id not in field_ids or params.reference_field_id not in field_ids:
                raise ToolCallValidationError("field_not_found")
            if (params.target_field_id, params.reference_field_id) != (
                self._request.target_field_id, self._request.reference_field_id,
            ):
                raise ToolCallValidationError("pair_changed")
            if params.period != self._request.period:
                raise ToolCallValidationError("period_changed")
        if isinstance(params, ApplicationArgs):
            params.operation = canonical_operation(params.operation)
            if not params.operation:
                raise ToolCallValidationError("invalid_arguments")
        if isinstance(params, (SoilSummaryArgs, SoilGroupsArgs)) and params.metrics is not None:
            # The analytical functions already discard duplicate metric names.
            params.metrics = list(dict.fromkeys(params.metrics))
        normalized = params.model_dump(mode="json")
        if isinstance(params, (SoilSummaryArgs, SoilGroupsArgs)) and params.metrics is not None:
            # Changing only display order does not request a new analysis.
            normalized["metrics"] = sorted(params.metrics)
        fingerprint = (name, json.dumps(normalized, sort_keys=True, ensure_ascii=False, allow_nan=False))
        if fingerprint in self._seen:
            raise ToolCallValidationError("duplicate_call")
        self._seen.add(fingerprint)
        return params
