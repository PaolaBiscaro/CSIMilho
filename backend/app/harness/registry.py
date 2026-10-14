"""Local deterministic registry only; no Gemini declarations or orchestration."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable

from pydantic import BaseModel

from app.analytics.application import application_compliance
from app.analytics.common import AnalysisUnavailableError, TOOL_VERSION
from app.analytics.comparability import validate_comparison
from app.analytics.contracts import ApplicationArgs, ComparisonArgs, SoilGroupsArgs, SoilSummaryArgs
from app.analytics.evidence import EvidenceIdGenerator
from app.analytics.ndvi import check_initial_condition, compare_ndvi
from app.analytics.population import compare_population
from app.analytics.soil import compare_soil_measurement_groups, summarize_soil_analysis
from app.data.session_store import SessionStore, dataset_store
from app.harness.schemas import Evidence


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: type[BaseModel]
    function: Callable[..., Evidence]
    version: str = TOOL_VERSION


TOOLS = MappingProxyType({item.name: item for item in (
    ToolDefinition("validate_comparison", "Verifica finalidade, cultura e cinco critérios de comparabilidade.", ComparisonArgs, validate_comparison),
    ToolDefinition("compare_ndvi", "Compara NDVI nas datas válidas comuns ao par e período.", ComparisonArgs, compare_ndvi),
    ToolDefinition("check_initial_condition", "Verifica gap pré-plantio com mínimo de três pares e heurística de 0,02.", ComparisonArgs, check_initial_condition),
    ToolDefinition("compare_population", "Compara população de plantas ponderada por área.", ComparisonArgs, compare_population),
    ToolDefinition("application_compliance", "Compara conformidade das doses ponderadas por área, priorizando CALAGEM.", ApplicationArgs, application_compliance),
    ToolDefinition("summarize_soil_analysis", "Resume métricas e textura do solo no escopo do dataset.", SoilSummaryArgs, summarize_soil_analysis),
    ToolDefinition("compare_soil_measurement_groups", "Compara Conjunto 2 menos Conjunto 1 por AMOSTRA e variável.", SoilGroupsArgs, compare_soil_measurement_groups),
)})


def get_tool(name: str) -> ToolDefinition:
    try:
        return TOOLS[name]
    except KeyError as exc:
        raise AnalysisUnavailableError("Ferramenta desconhecida.") from exc


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
