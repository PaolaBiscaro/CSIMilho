"""Deterministic registry and declarative Gemini adapter; no orchestration."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Callable

from pydantic import BaseModel

from app.analytics.application import application_compliance, summarize_field_application
from app.analytics.common import AnalysisUnavailableError, TOOL_VERSION
from app.analytics.comparability import validate_comparison
from app.analytics.contracts import (
    ApplicationArgs, ApplicationEvidence, ComparisonArgs, ComparisonEvidence,
    FieldApplicationEvidence, FieldNdviEvidence, FieldPopulationEvidence, InitialEvidence,
    NdviChangeEvidence, NdviEvidence, OperationNdviArgs, OperationNdviEvidence,
    PairedNdviTestEvidence, PopulationEvidence, SingleApplicationArgs, SingleFieldArgs,
    SoilGroupsArgs, SoilGroupsEvidence, SoilStatisticalEvidence, SoilSummaryArgs,
    SoilSummaryEvidence,
)
from app.analytics.evidence import EvidenceIdGenerator
from app.analytics.ndvi import (
    analyze_field_ndvi, check_initial_condition, compare_ndvi,
    detect_field_ndvi_changes, test_paired_ndvi_difference,
)
from app.analytics.population import compare_population, summarize_field_population
from app.analytics.soil import (
    compare_soil_measurement_groups, summarize_soil_analysis, test_soil_measurement_groups,
)
from app.analytics.temporal import associate_field_operations_ndvi
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
    ToolDefinition("test_paired_ndvi_difference", "Testa exploratoriamente diferenças de NDVI nas mesmas datas, com p-valor exato, intervalo para a mediana e tamanho de efeito.", ComparisonArgs, test_paired_ndvi_difference, PairedNdviTestEvidence),
    ToolDefinition("analyze_field_ndvi", "Analisa a série temporal de NDVI de um único talhão e identifica variações adjacentes bruscas por regra operacional.", SingleFieldArgs, analyze_field_ndvi, FieldNdviEvidence),
    ToolDefinition("detect_field_ndvi_changes", "Detecta mudanças adjacentes atípicas na série de um talhão por mediana e MAD, sem atribuir causa.", SingleFieldArgs, detect_field_ndvi_changes, NdviChangeEvidence),
    ToolDefinition("associate_field_operations_ndvi", "Relaciona temporalmente operações documentadas às observações de NDVI imediatamente anterior e posterior, sem inferência causal.", OperationNdviArgs, associate_field_operations_ndvi, OperationNdviEvidence),
    ToolDefinition("summarize_field_population", "Resume a população de plantas registrada para um único talhão.", SingleFieldArgs, summarize_field_population, FieldPopulationEvidence),
    ToolDefinition("summarize_field_application", "Resume doses e conformidade de uma operação em um único talhão.", SingleApplicationArgs, summarize_field_application, FieldApplicationEvidence),
    ToolDefinition("check_initial_condition", "Verifica gap pré-plantio com mínimo de três pares e heurística de 0,02.", ComparisonArgs, check_initial_condition, InitialEvidence),
    ToolDefinition("compare_population", "Compara população de plantas ponderada por área.", ComparisonArgs, compare_population, PopulationEvidence),
    ToolDefinition("application_compliance", "Compara conformidade das doses ponderadas por área, priorizando CALAGEM.", ApplicationArgs, application_compliance, ApplicationEvidence),
    ToolDefinition("summarize_soil_analysis", "Resume métricas e textura do solo no escopo do dataset.", SoilSummaryArgs, summarize_soil_analysis, SoilSummaryEvidence),
    ToolDefinition("compare_soil_measurement_groups", "Compara Conjunto 2 menos Conjunto 1 por AMOSTRA e variável.", SoilGroupsArgs, compare_soil_measurement_groups, SoilGroupsEvidence),
    ToolDefinition("test_soil_measurement_groups", "Aplica teste pareado exato por variável entre os conjuntos de solo, com tamanho de efeito, incerteza e ajuste de Holm; não atribui amostras a talhões.", SoilGroupsArgs, test_soil_measurement_groups, SoilStatisticalEvidence),
)})


def get_tool(name: str) -> ToolDefinition:
    try:
        return TOOLS[name]
    except KeyError as exc:
        raise AnalysisUnavailableError("Ferramenta desconhecida.") from exc


def build_gemini_tool(allowed_names: list[str] | None = None) -> "types.Tool":
    """Declare the registry's public inputs without exposing Python callables.

    Use in GenerateContentConfig(tools=[build_gemini_tool()]). JSON Schema
    preserves closed objects, references, unions, defaults and nullable filters.
    Build fresh objects so SDK/caller mutations cannot change later requests.
    The harness remains responsible for validating and executing model calls.
    """
    from google.genai import types

    selected = TOOLS.values() if allowed_names is None else (TOOLS[name] for name in allowed_names)
    return types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters_json_schema=tool.parameters.model_json_schema(),
        )
        for tool in selected
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
