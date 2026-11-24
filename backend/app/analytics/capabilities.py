"""Trusted classification of analytical blockers for investigation reports.

The catalog distinguishes a method the backend cannot run from an analysis
that a registered tool cannot run with the available data. Messages are local
and deterministic: exception text, CSV contents and model prose are never used
as report limitations.
"""

from dataclasses import dataclass
import re
from typing import Literal
import unicodedata

from app.data.contracts import ValidationIssue


BlockerType = Literal["missing_tooling", "missing_data"]


@dataclass(frozen=True)
class CapabilityGap:
    code: str
    blocker_type: BlockerType
    title: str
    explanation: str
    pattern: re.Pattern[str] | None = None

    def as_context(self) -> dict[str, str]:
        return {
            "code": self.code,
            "status": "blocked",
            "blocker_type": self.blocker_type,
            "title": self.title,
            "required": self.explanation,
        }

    def as_warning(self) -> ValidationIssue:
        return ValidationIssue(code=self.code, message=self.explanation)


def _plain(text: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    )


_QUESTION_GAPS = (
    CapabilityGap(
        code="analysis_missing_tooling_requested_hypothesis_method",
        blocker_type="missing_tooling",
        title="Ferramenta ausente — método estatístico solicitado",
        explanation=(
            "O backend possui teste exato pareado para desenhos compatíveis, mas ainda não implementa "
            "o método nominal solicitado. O sistema deve escolher o teste pelo desenho dos dados; ANOVA, "
            "teste t, Mann–Whitney e qui-quadrado exigem módulos e pressupostos próprios."
        ),
        pattern=re.compile(
            r"\b(?:anova|teste\s+t|wilcoxon|mann[ -]?whitney|qui[ -]?quadrado)\b"
        ),
    ),
    CapabilityGap(
        code="analysis_missing_tooling_correlation",
        blocker_type="missing_tooling",
        title="Ferramenta ausente — correlação ou regressão",
        explanation=(
            "O backend ainda não possui um módulo validado de correlação ou regressão. Para implementá-lo, "
            "também serão necessárias observações das variáveis ligadas à mesma unidade, talhão e período."
        ),
        pattern=re.compile(r"\b(?:correlac\w*|regress\w*|coeficiente\s+de\s+pearson|spearman)\b"),
    ),
    CapabilityGap(
        code="analysis_missing_data_yield",
        blocker_type="missing_data",
        title="Dados ausentes — produtividade",
        explanation=(
            "Não há dados confiáveis de produtividade ou colheita vinculados a cada talhão e período. "
            "Seriam necessários rendimento medido, unidade, área colhida, data ou safra e o vínculo com "
            "o talhão para comparar produtividade."
        ),
        pattern=re.compile(r"\b(?:produtiv\w*|rendimento|sacas?|colheit\w*)\b"),
    ),
    CapabilityGap(
        code="analysis_missing_data_causal_design",
        blocker_type="missing_data",
        title="Dados ausentes — inferência causal",
        explanation=(
            "Os dados observacionais atuais não permitem atribuir o resultado ao manejo. Seriam necessários "
            "um desenho experimental ou quase experimental, grupos comparáveis, condição inicial, variáveis "
            "de controle e medições repetidas com vínculo temporal."
        ),
        pattern=re.compile(
            r"\b(?:caus\w*|efeito\s+(?:do|da|de)\s+manejo|impacto\s+(?:do|da|de)\s+manejo|"
            r"responsavel\s+(?:por|pela|pelo))\b"
        ),
    ),
    CapabilityGap(
        code="analysis_missing_tooling_forecast",
        blocker_type="missing_tooling",
        title="Ferramenta ausente — previsão",
        explanation=(
            "O backend ainda não possui um modelo de previsão validado. A implementação também exigirá "
            "histórico temporal suficiente, separação temporal entre treino e validação e métricas de erro."
        ),
        pattern=re.compile(r"\b(?:previs\w*|projec\w*|forecast\w*|estimar\s+o\s+futuro)\b"),
    ),
    CapabilityGap(
        code="analysis_missing_tooling_spatial",
        blocker_type="missing_tooling",
        title="Ferramenta ausente — análise espacial",
        explanation=(
            "O backend ainda não possui um módulo geoespacial para mapas, zonas ou autocorrelação. A "
            "implementação também exigirá coordenadas ou polígonos ligados às observações na granularidade necessária."
        ),
        pattern=re.compile(
            r"\b(?:mapa\w*|geo(?:graf\w*|espacial\w*)|espacial\w*|zonas?\s+de\s+manejo|"
            r"hotspots?|autocorrelac\w*)\b"
        ),
    ),
    CapabilityGap(
        code="analysis_missing_tooling_multivariate",
        blocker_type="missing_tooling",
        title="Ferramenta ausente — análise multivariada",
        explanation=(
            "O backend ainda não possui um módulo multivariado validado, como agrupamento ou componentes "
            "principais, com seleção de variáveis, tratamento de escala e validação do método."
        ),
        pattern=re.compile(
            r"\b(?:cluster\w*|agrupamento\w*|componentes?\s+principais|pca|multivariad\w*)\b"
        ),
    ),
)


_TOOL_DATA_GAPS = {
    "analyze_field_ndvi": CapabilityGap(
        code="analysis_missing_data_field_ndvi", blocker_type="missing_data",
        title="Dados ausentes — série temporal de NDVI do talhão",
        explanation=(
            "A série temporal individual não pôde ser analisada. É necessária ao menos uma observação "
            "válida de NDVI vinculada ao talhão dentro do período selecionado."
        ),
    ),
    "detect_field_ndvi_changes": CapabilityGap(
        code="analysis_missing_data_ndvi_changes", blocker_type="missing_data",
        title="Dados ausentes — detecção robusta de mudanças",
        explanation="São necessárias ao menos cinco observações válidas de NDVI do talhão no período.",
    ),
    "associate_field_operations_ndvi": CapabilityGap(
        code="analysis_missing_data_operation_ndvi", blocker_type="missing_data",
        title="Dados ausentes — associação temporal entre operação e NDVI",
        explanation=(
            "São necessárias operações datadas e observações válidas de NDVI antes e depois de cada "
            "operação, vinculadas ao mesmo talhão e dentro da janela temporal configurada."
        ),
    ),
    "summarize_field_population": CapabilityGap(
        code="analysis_missing_data_field_population", blocker_type="missing_data",
        title="Dados ausentes — população do talhão",
        explanation="São necessários registros válidos de plantio, população informada e área positiva vinculados ao talhão.",
    ),
    "summarize_field_application": CapabilityGap(
        code="analysis_missing_data_field_application", blocker_type="missing_data",
        title="Dados ausentes — aplicação do talhão",
        explanation="São necessários registros da operação com dose configurada, dose aplicada e área válidas vinculados ao talhão.",
    ),
    "compare_ndvi": CapabilityGap(
        code="analysis_missing_data_compare_ndvi", blocker_type="missing_data",
        title="Dados ausentes — comparação de NDVI",
        explanation=(
            "A comparação de NDVI não pôde ser executada. É necessária ao menos uma observação válida "
            "de NDVI para cada talhão em uma mesma data dentro do período selecionado."
        ),
    ),
    "test_paired_ndvi_difference": CapabilityGap(
        code="analysis_missing_data_paired_ndvi_test", blocker_type="missing_data",
        title="Dados ausentes — teste pareado de NDVI",
        explanation=(
            "O teste exige ao menos cinco diferenças não empatadas de NDVI em datas válidas comuns "
            "aos dois talhões."
        ),
    ),
    "check_initial_condition": CapabilityGap(
        code="analysis_missing_data_initial_condition", blocker_type="missing_data",
        title="Dados ausentes — condição inicial",
        explanation=(
            "A condição inicial não pôde ser avaliada. São necessárias observações válidas de NDVI dos "
            "dois talhões em datas pareadas anteriores ao plantio."
        ),
    ),
    "compare_population": CapabilityGap(
        code="analysis_missing_data_compare_population", blocker_type="missing_data",
        title="Dados ausentes — população de plantas",
        explanation=(
            "A comparação de população não pôde ser executada. São necessários registros válidos de "
            "plantio dos dois talhões, população informada e área positiva vinculada a cada talhão."
        ),
    ),
    "application_compliance": CapabilityGap(
        code="analysis_missing_data_application_compliance", blocker_type="missing_data",
        title="Dados ausentes — conformidade de aplicação",
        explanation=(
            "A conformidade de aplicação não pôde ser calculada. São necessários registros da mesma "
            "operação para os dois talhões, com dose configurada, dose aplicada e área válidas."
        ),
    ),
    "summarize_soil_analysis": CapabilityGap(
        code="analysis_missing_data_soil_summary", blocker_type="missing_data",
        title="Dados ausentes — resumo de solo",
        explanation=(
            "O resumo de solo não pôde ser calculado. São necessárias amostras de solo e valores numéricos "
            "válidos para o conjunto de medição solicitado."
        ),
    ),
    "compare_soil_measurement_groups": CapabilityGap(
        code="analysis_missing_data_soil_groups", blocker_type="missing_data",
        title="Dados ausentes — contraste entre conjuntos de solo",
        explanation=(
            "O contraste entre conjuntos de solo não pôde ser calculado. São necessárias amostras pareadas "
            "pelo identificador AMOSTRA e variáveis numéricas válidas presentes nos dois conjuntos."
        ),
    ),
    "test_soil_measurement_groups": CapabilityGap(
        code="analysis_missing_data_soil_test", blocker_type="missing_data",
        title="Dados ausentes — teste pareado de solo",
        explanation=(
            "É necessária ao menos uma variável com cinco pares não empatados entre Conjunto 1 e "
            "Conjunto 2, vinculados pela mesma AMOSTRA."
        ),
    ),
}


_BY_CODE = {gap.code: gap for gap in (*_QUESTION_GAPS, *_TOOL_DATA_GAPS.values())}


def assess_question_capabilities(question: str) -> list[CapabilityGap]:
    """Return stable, deduplicated blockers explicitly requested in the question."""
    normalized = _plain(question)
    return [gap for gap in _QUESTION_GAPS if gap.pattern is not None and gap.pattern.search(normalized)]


def missing_data_gap_for_tool(tool_name: str) -> CapabilityGap | None:
    """Return a trusted missing-data explanation for one registered analysis."""
    return _TOOL_DATA_GAPS.get(tool_name)


def capability_gap_for_code(code: str) -> CapabilityGap | None:
    """Resolve only trusted catalog entries; warning messages are never reused."""
    return _BY_CODE.get(code)
