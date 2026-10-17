"""Deterministic registry and declarative Gemini adapter; no orchestration."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Callable

from pydantic import BaseModel

from app.analytics.application import application_compliance
from app.analytics.common import AnalysisUnavailableError, TOOL_VERSION
from app.analytics.comparability import validate_comparison
from app.analytics.contracts import (
    ApplicationArgs, ApplicationEvidence, ComparisonArgs, ComparisonEvidence,
    InitialEvidence, NdviEvidence, PopulationEvidence, SoilGroupsArgs,
    SoilGroupsEvidence, SoilSummaryArgs, SoilSummaryEvidence,
)
from app.analytics.evidence import EvidenceIdGenerator
from app.analytics.ndvi import check_initial_condition, compare_ndvi
from app.analytics.population import compare_population
from app.analytics.soil import compare_soil_measurement_groups, summarize_soil_analysis
from app.data.session_store import SessionStore, dataset_store
from app.harness.schemas import Evidence

if TYPE_CHECKING:
    from google.genai import types


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: type[BaseModel]
    function: Callable[..., Evidence]
    result: type[Evidence]
    version: str = TOOL_VERSION


TOOLS = MappingProxyType({item.name: item for item in (
    ToolDefinition("validate_comparison", "Verifica finalidade, cultura e cinco critérios de comparabilidade.", ComparisonArgs, validate_comparison, ComparisonEvidence),
    ToolDefinition("compare_ndvi", "Compara NDVI nas datas válidas comuns ao par e período.", ComparisonArgs, compare_ndvi, NdviEvidence),
    ToolDefinition("check_initial_condition", "Verifica gap pré-plantio com mínimo de três pares e heurística de 0,02.", ComparisonArgs, check_initial_condition, InitialEvidence),
    ToolDefinition("compare_population", "Compara população de plantas ponderada por área.", ComparisonArgs, compare_population, PopulationEvidence),
    ToolDefinition("application_compliance", "Compara conformidade das doses ponderadas por área, priorizando CALAGEM.", ApplicationArgs, application_compliance, ApplicationEvidence),
    ToolDefinition("summarize_soil_analysis", "Resume métricas e textura do solo no escopo do dataset.", SoilSummaryArgs, summarize_soil_analysis, SoilSummaryEvidence),
    ToolDefinition("compare_soil_measurement_groups", "Compara Conjunto 2 menos Conjunto 1 por AMOSTRA e variável.", SoilGroupsArgs, compare_soil_measurement_groups, SoilGroupsEvidence),
)})


def get_tool(name: str) -> ToolDefinition:
    try:
        return TOOLS[name]
    except KeyError as exc:
        raise AnalysisUnavailableError("Ferramenta desconhecida.") from exc


def build_gemini_tool() -> "types.Tool":
    """Declare the registry's public inputs without exposing Python callables.

    Use in GenerateContentConfig(tools=[build_gemini_tool()]). JSON Schema
    preserves closed objects, references, unions, defaults and nullable filters.
    Build fresh objects so SDK/caller mutations cannot change later requests.
    The harness remains responsible for validating and executing model calls.
    """
    from google.genai import types

    return types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters_json_schema=tool.parameters.model_json_schema(),
        )
        for tool in TOOLS.values()
    ])


def execute_tool(name: str, arguments: dict, *, store: SessionStore = dataset_store,
                 ids: EvidenceIdGenerator | None = None) -> Evidence:
    tool = get_tool(name)
    params = tool.parameters.model_validate(arguments)
    dataset = store.get(params.dataset_id)
    kwargs = {key: getattr(params, key) for key in type(params).model_fields if key != "dataset_id"}
    if isinstance(params, ComparisonArgs) and name != "validate_comparison":
        comparison = validate_comparison(dataset, params.target_field_id, params.reference_field_id, params.period)
        if not comparison.allowed:
            raise AnalysisUnavailableError("Par incompatível: confira cultura, finalidade e manejos.")
    return tool.function(dataset, **kwargs, ids=ids)
