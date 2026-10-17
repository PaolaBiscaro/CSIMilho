"""Deterministic checks of cited facts and required limitations, not causal NLP.

Numbers must use digits and explicit units for dimensional quantities. Matching
is local to a sentence and its cited evidence, with role/metric qualifiers when
present. This is a conservative guard, not proof of arbitrary prose entailment.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import re
import unicodedata

from pydantic import TypeAdapter

from app.analytics.contracts import (
    ApplicationEvidence, ComparisonEvidence, InitialEvidence, NdviEvidence,
    PopulationEvidence, SoilGroupsEvidence, SoilSummaryEvidence,
)
from app.data.contracts import ValidationIssue
from app.harness.schemas import AnalyticalEvidence, InvestigationReport, ReportLimitation, ReportValidationIssue


class ReportValidationError(ValueError):
    def __init__(self, issues: list[ReportValidationIssue]) -> None:
        self.issues = issues
        super().__init__("O relatório contém referências, números ou limitações inválidos.")


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c)).replace("−", "-").replace("–", "-")


def required_limitations(evidence: list[AnalyticalEvidence], warnings: list[ValidationIssue] = ()) -> list[ReportLimitation]:
    """Stable rules copied verbatim into the report, without interpreting LLM prose."""
    rules = [
        ("observational_comparison", "Comparação observacional",
         "Os dados são observacionais e não permitem concluir causalidade sobre o manejo."),
        ("no_reliable_yield", "Produtividade não medida",
         "Não há produtividade confiável nas evidências; diferenças de NDVI não demonstram ganho de produtividade ou lucro."),
    ]
    initial = [item for item in evidence if isinstance(item, InitialEvidence)]
    if not initial:
        rules.append(("initial_condition_not_checked", "Condição inicial não verificada",
                      "A condição anterior ao plantio não foi verificada nesta investigação; diferenças prévias não podem ser descartadas."))
    elif any(not item.available for item in initial):
        rules.append(("initial_condition_unavailable", "Condição inicial indisponível",
                      "A condição anterior ao plantio está indisponível por insuficiência de dados; diferenças prévias não podem ser descartadas."))
    if any(item.available for item in initial):
        rules.append(("initial_gap_heuristic", "Heurística de condição inicial",
                      "A avaliação da condição inicial usa uma heurística operacional e não constitui teste de significância estatística."))
    if any(item.different is True for item in initial):
        rules.append(("initial_condition_different", "Diferença anterior ao plantio",
                      "Já havia diferença de NDVI antes do plantio; essa condição inicial é uma explicação alternativa e limita a interpretação do manejo."))
    if any(isinstance(item, (ComparisonEvidence, NdviEvidence)) and item.paired_dates < 5 for item in evidence):
        rules.append(("few_paired_dates", "Poucas datas pareadas",
                      "Há poucas datas de NDVI pareadas; a cobertura temporal limita a força da comparação."))
    soil = [item for item in evidence if isinstance(item, (SoilSummaryEvidence, SoilGroupsEvidence))]
    if soil:
        rules.extend([
            ("soil_dataset_scope", "Solo no escopo do dataset",
             "As amostras de solo pertencem ao dataset, sem vínculo documentado com talhão, coordenada, data ou profundidade."),
            ("soil_group_meaning", "Significado dos conjuntos",
             "O significado do sufixo _2 não está documentado; não há documentação de profundidade, época ou repetição para Conjunto 1 e Conjunto 2."),
            ("soil_agronomic_reference", "Referência agronômica ausente",
             "Não há referência agronômica documentada para classificar suficiência ou prescrever adubação e calagem a partir dessas amostras."),
        ])
        if any(metric.unit is None for item in soil for metric in item.metrics):
            rules.append(("soil_units_unknown", "Unidades não documentadas",
                          "Há métricas de solo com unidade não documentada; não se pode atribuir unidade ou classificação agronômica a esses valores."))
    # A provider/fallback notice is operational, not a data-quality defect.
    if any(item.code != "deterministic_fallback" for item in warnings) or any(item.warnings for item in evidence):
        rules.append(("data_quality_warnings", "Avisos de qualidade",
                      "Há avisos de qualidade nos dados ou nas análises; consulte os avisos acumulados e considere as lacunas na interpretação."))
    return [ReportLimitation(rule_id=key, title=title, explanation=text) for key, title, text in rules]


@dataclass(frozen=True)
class _Fact:
    value: Decimal
    unit: str | None
    role: str = ""
    metric: str = ""
    kind: str = ""
    integer: bool = False
    on_date: date | None = None
    sample: str | None = None


def _facts(item: AnalyticalEvidence) -> list[_Fact]:
    """Typed fields only: never mine IDs, versions, booleans or free-text notes."""
    facts = []

    def add(value, unit, role="", metric="", kind="", integer=False, on_date=None, sample=None):
        if value is not None and not isinstance(value, bool):
            facts.append(_Fact(Decimal(str(value)), unit, role, metric, kind, integer, on_date, sample))

    add(item.observation_count, "count", kind="observations", integer=True)
    if isinstance(item, ComparisonEvidence):
        add(item.score, "count", kind="score", integer=True)
        add(item.max_score, "count", kind="score", integer=True)
        add(item.paired_dates, "count", kind="dates", integer=True)
    elif isinstance(item, (NdviEvidence, InitialEvidence)):
        add(item.paired_dates, "count", kind="dates", integer=True)
        add(item.mean_gap, "ndvi", "difference", "ndvi", "mean")
        if isinstance(item, NdviEvidence):
            add(item.target_mean, "ndvi", "target", "ndvi", "mean")
            add(item.reference_mean, "ndvi", "reference", "ndvi", "mean")
            for key in ("negative_dates", "positive_dates", "equal_dates"):
                add(getattr(item, key), "count", kind=key, integer=True)
            for point in item.series:
                add(point.target_ndvi, "ndvi", "target", "ndvi", on_date=point.date)
                add(point.reference_ndvi, "ndvi", "reference", "ndvi", on_date=point.date)
                add(point.gap, "ndvi", "difference", "ndvi", on_date=point.date)
        else:
            add(item.threshold, "ndvi", metric="ndvi", kind="threshold")
    elif isinstance(item, PopulationEvidence):
        add(item.target_population_per_ha, "plants/ha", "target", "population")
        add(item.reference_population_per_ha, "plants/ha", "reference", "population")
        add(item.difference, "plants/ha", "difference", "population")
        add(item.difference_percent, "%", "difference", "population")
    elif isinstance(item, ApplicationEvidence):
        add(item.target_compliance_percent, "%", "target", "compliance")
        add(item.reference_compliance_percent, "%", "reference", "compliance")
        add(item.difference, "pp", "difference", "compliance")
        for role in ("target", "reference"):
            add(getattr(item, f"{role}_applied_dose"), "kg/ha", role, "dose", "applied")
            add(getattr(item, f"{role}_configured_dose"), "kg/ha", role, "dose", "configured")
    elif isinstance(item, (SoilSummaryEvidence, SoilGroupsEvidence)):
        add(item.sample_count, "count", kind="samples", integer=True)
        for metric in item.metrics:
            add(metric.valid_n, "count", metric=metric.name, kind="samples", integer=True)
            if isinstance(item, SoilSummaryEvidence):
                add(metric.missing_n, "count", metric=metric.name, kind="missing", integer=True)
                for key in ("mean", "median", "min", "max", "q1", "q3"):
                    add(getattr(metric, key), metric.unit, metric=metric.name, kind=key)
            else:
                add(metric.median_delta, metric.unit, "difference", metric.name, "median")
                for pair in metric.pairs:
                    add(pair.group_1, metric.unit, "group_1", metric.name, sample=pair.sample_id)
                    add(pair.group_2, metric.unit, "group_2", metric.name, sample=pair.sample_id)
                    add(pair.delta, metric.unit, "difference", metric.name, sample=pair.sample_id)
        if isinstance(item, SoilSummaryEvidence):
            add(item.completeness_percent, "%", metric="completeness")
            for value in (item.valid_values, item.expected_values):
                add(value, "count", kind="values", integer=True)
            for value in (item.texture.valid_n, item.texture.excluded_n):
                add(value, "count", kind="samples", integer=True)
            for sample in item.texture.samples:
                for name in ("sand", "silt", "clay"):
                    add(getattr(sample, name), "%", metric=name, sample=sample.sample_id)
                    add(getattr(sample, f"original_{name}"), None, metric=name, sample=sample.sample_id)
                add(sample.original_total, None, metric="texture_total", sample=sample.sample_id)
    if isinstance(item, (PopulationEvidence, ApplicationEvidence)):
        for role in ("target", "reference"):
            rows = getattr(item, f"{role}_rows")
            add(rows.valid, "count", role, kind="rows", integer=True)
            add(rows.discarded, "count", role, kind="rows", integer=True)
    return facts


_CITATION = re.compile(r"\bEV-[A-Za-z0-9_-]+")
_NUMBER = re.compile(r"(?<![\w])[-+−]?(?:\d+(?:[.,]\d+)*|[.,]\d+)(?:[eE][-+]?\d+)?(?!\d|[.,]\d)")
_DATE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b")
_UNIT = re.compile(r"^\s*(%|p\.?\s*p\.?\b|pontos? percentua(?:l|is)\b|por cento\b|"
                   r"(?:plantas?|plants)\s*(?:/|por\s+)ha\b|kg\s*/\s*ha\b|"
                   r"(?:mg|g|cmolc|cmol|mmolc)\s*/\s*(?:kg|dm[³3]|l)\b|"
                   r"[a-zµ]+[³²23]?\s*/\s*[a-zµ]+[³²23]?\b|ppm\b|ppb\b|"
                   r"t\s*/\s*ha\b|kg\b|g\b|ha\b|cm\b|mm\b|m\b)")
_COUNT = re.compile(r"^\s*(datas?|pares?|observacoes|registros?|linhas?|amostras?|valores?|criterios?|pontos?)\b")
_SPELLED = re.compile(r"\b(?:zero|um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|"
                      r"treze|catorze|quatorze|quinze|dezesseis|dezessete|dezoito|dezenove|vinte|trinta|"
                      r"quarenta|cinquenta|sessenta|setenta|oitenta|noventa|cem|cento|mil)\s+"
                      r"(?:e\s+\w+\s+)?(?:por cento|datas?|pares?|amostras?|plantas?|kg|pontos? percentuais?)\b")


def _number(raw: str) -> Decimal:
    raw = raw.replace("−", "-")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    elif re.fullmatch(r"[-+]?[1-9]\d{0,2}(?:\.\d{3})+", raw):
        raw = raw.replace(".", "")  # Portuguese grouping; 0.123 stays decimal.
    return Decimal(raw)


def _matches(value: Decimal, fact: _Fact) -> bool:
    if not value.is_finite() or (value == 0 and fact.value != 0):
        return False
    if value != 0 and value.is_signed() != fact.value.is_signed():
        return False
    if fact.integer:
        return value == fact.value
    with localcontext() as context:
        context.prec = max(50, len(fact.value.as_tuple().digits) + abs(value.as_tuple().exponent) + 5)
        return fact.value.quantize(Decimal(1).scaleb(value.as_tuple().exponent), rounding=ROUND_HALF_UP) == value


def _canonical_unit(text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    if compact in ("%", "porcento"):
        return "%"
    if "percentua" in compact or compact.replace(".", "") == "pp":
        return "pp"
    if compact.startswith(("planta", "plants")):
        return "plants/ha"
    return compact


def _qualify(facts: list[_Fact], prefix: str, suffix: str, number_unit: str | None) -> list[_Fact]:
    """Use nearby explicit roles/metrics, never accept a number from other metrics."""
    roles = [(m.start(), role) for role, pattern in (
        ("target", r"\balvo\b"), ("reference", r"\breferencia\b"),
        ("difference", r"\b(?:gap|delta|diferenca)\b"),
        ("group_1", r"\bconjunto 1\b"), ("group_2", r"\bconjunto 2\b"),
    ) for m in re.finditer(pattern, prefix)]
    if roles and number_unit != "count":
        role = "difference" if any(role == "difference" for _, role in roles) else max(roles)[1]
        facts = [fact for fact in facts if fact.role == role]
    combined = prefix + " " + suffix
    if number_unit == "count":
        count_kind = next((kind for kind, pattern in (
            ("negative_dates", r"^\s*datas?\s+negativas?"),
            ("positive_dates", r"^\s*datas?\s+positivas?"),
            ("equal_dates", r"^\s*datas?\s+iguais?"),
            ("dates", r"^\s*(?:datas?|pares?)\b"),
            ("samples", r"^\s*amostras?\b"),
            ("rows", r"^\s*(?:registros?|linhas?)\b"),
            ("values", r"^\s*valores?\b"),
            ("score", r"^\s*(?:criterios?|pontos?)\b"),
            ("observations", r"^\s*observacoes\b"),
        ) if re.search(pattern, suffix)), None)
        if count_kind:
            facts = [fact for fact in facts if fact.kind == count_kind or
                     (count_kind == "dates" and fact.kind == "samples" and "pares" in suffix)]
    selectors = [
        (r"\bndvi\b", {"ndvi"}), (r"\bpopulacao\b", {"population"}),
        (r"\bconformidade\b", {"compliance"}), (r"\bdose\b", {"dose"}),
        (r"\bcompletude\b", {"completeness"}),
    ]
    # A statement mentioning several different metrics is ambiguous: local
    # prefix wins; callers split clauses at semicolons/commas where possible.
    found = [(m.start(), names) for pattern, names in selectors for m in re.finditer(pattern, prefix)]
    if found and number_unit != "count":
        names = max(found, key=lambda item: item[0])[1]
        facts = [fact for fact in facts if fact.metric in names]
    soil_names = {fact.metric for fact in facts if fact.metric.isupper()}
    named = {name for name in soil_names if re.search(r"\b" + name.lower() + r"\b", combined)}
    if named:
        facts = [fact for fact in facts if fact.metric in named]
    texture_names = {name for name, label in (("sand", "areia"), ("silt", "silte"), ("clay", "argila"))
                     if re.search(r"\b" + label + r"\b", combined)}
    if texture_names and any(fact.sample for fact in facts):
        facts = [fact for fact in facts if fact.metric in texture_names or fact.metric.lower() in combined]
    kinds = [(m.start(), kind) for kind, pattern in (
        ("mean", r"\bmedia\b"), ("median", r"\bmediana\b"),
        ("min", r"\bminimo\b"), ("max", r"\bmaximo\b"),
        ("q1", r"\bq1\b"), ("q3", r"\bq3\b"),
        ("applied", r"\baplicada\b"), ("configured", r"\bconfigurada\b"),
        ("threshold", r"\blimiar\b"),
    ) for m in re.finditer(pattern, prefix)]
    if kinds and number_unit != "count":
        kind = max(kinds)[1]
        # mean/median describe ordinary field averages too, which have no kind.
        facts = [fact for fact in facts if fact.kind == kind or (not fact.kind and kind in ("mean", "median"))]
    return facts


def _direction_is_wrong(text: str, facts: list[_Fact]) -> bool:
    """Check explicit sign/comparison vocabulary; not arbitrary entailment."""
    claims = []
    sign = re.search(r"\b(?:gap|delta|diferenca)\b[^.;]{0,65}\b(positivo|positiva|negativo|negativa|nulo|nula)\b", text)
    comparison = re.search(r"\balvo\b[^.;]{0,65}\b(maior|superior|menor|inferior|igual)\b", text)
    if sign:
        word = sign[1]
        claims.append((1 if word.startswith("positiv") else -1 if word.startswith("negativ") else 0, sign[0]))
    if comparison:
        claims.append((1 if comparison[1] in ("maior", "superior") else -1 if comparison[1] in ("menor", "inferior") else 0, comparison[0]))
    change = re.search(r"\b(aumento|reducao|queda)\s+(?:de|do|da)\b", text)
    if change:
        claims.append((1 if change[1] == "aumento" else -1, change[0]))
    if not claims:
        return False
    selected = [fact for fact in facts if fact.role == "difference"]
    for keyword, metric in (("ndvi", "ndvi"), ("populacao", "population"), ("conformidade", "compliance")):
        if keyword in text:
            selected = [fact for fact in selected if fact.metric == metric]
            break
    named = {fact.metric for fact in selected if fact.metric.isupper() and
             re.search(r"\b" + fact.metric.lower() + r"\b", text)}
    if named:
        selected = [fact for fact in selected if fact.metric in named]
    signs = {(fact.value > 0) - (fact.value < 0) for fact in selected}
    for expected, phrase in claims:
        if "nao " in phrase:
            if not signs or all(value == expected for value in signs):
                return True
        elif expected not in signs:
            return True
    return False


def validate_report_evidence(report: InvestigationReport, evidence: list[AnalyticalEvidence],
                             warnings: list[ValidationIssue] = ()) -> InvestigationReport:
    """Return a revalidated copy or safe, located errors for the future repair step."""
    report = InvestigationReport.model_validate(report.model_dump())
    evidence = TypeAdapter(list[AnalyticalEvidence]).validate_python([item.model_dump() for item in evidence])
    issues = []

    def reject(code, location, message):
        issue = ReportValidationIssue(code=code, location=location, message=message)
        if issue not in issues:
            issues.append(issue)

    by_id = {item.evidence_id: item for item in evidence}
    if len(by_id) != len(evidence):
        reject("duplicate_evidence_id", "evidence", "Os IDs das evidências precisam ser únicos.")
    catalog = {key: _facts(item) for key, item in by_id.items()}
    required = {item.rule_id: item for item in required_limitations(evidence, warnings)}
    provided = {}
    for index, item in enumerate(report.limitations):
        if item.rule_id in provided:
            reject("duplicate_limitation", f"limitations[{index}]", "Cada rule_id deve ocorrer uma única vez.")
        provided[item.rule_id] = item
    for key, rule in required.items():
        if key not in provided:
            reject("missing_limitation", "limitations", f"Inclua a limitação obrigatória {key}.")
        elif " ".join(provided[key].explanation.split()) != " ".join(rule.explanation.split()):
            reject("invalid_limitation", "limitations", f"Preserve a explicação fornecida para {key}.")

    def check_text(text, location, declared=()):
        cited = set(declared) | set(_CITATION.findall(text))
        if cited - by_id.keys():
            reject("unknown_evidence_id", location, "Há referência a uma evidência inexistente.")
        # Each sentence uses its own inline references, or the structured IDs
        # of its finding/recommendation. Overview has no implicit global pool.
        for sentence in re.split(r"(?<=[.!?])\s+|;\s*|\n+", text):
            inline = set(_CITATION.findall(sentence))
            scope = (inline or set(declared)) & by_id.keys()
            facts = [fact for key in scope for fact in catalog[key]]
            clean = _CITATION.sub(lambda m: " " * len(m[0]), sentence)
            plain = _plain(clean)
            if _SPELLED.search(plain) or re.search(r"\d_\d", plain):
                reject("unsupported_number_format", location, "Escreva quantidades com algarismos e unidade explícita.")
            dates = set()
            for key in scope:
                item = by_id[key]
                if isinstance(item, NdviEvidence):
                    dates.update(point.date for point in item.series)
                if isinstance(item, InitialEvidence) and item.cutoff_date:
                    dates.add(item.cutoff_date)
                if hasattr(item, "period") and not isinstance(item.period, str):
                    dates.update((item.period.start, item.period.end))
            mentioned_dates = set()
            for match in _DATE.finditer(plain):
                try:
                    raw = match[0]
                    parsed = date.fromisoformat(raw if "-" in raw else "-".join(reversed(raw.split("/"))))
                except ValueError:
                    parsed = None
                if parsed not in dates:
                    reject("unsupported_date", location, "A data não consta das evidências citadas.")
                elif parsed:
                    mentioned_dates.add(parsed)
            plain = _DATE.sub(lambda m: " " * len(m[0]), plain)
            semantic_text = plain
            facts = [fact for fact in facts if (fact.on_date in mentioned_dates if fact.on_date else not mentioned_dates or fact.unit == "count")]
            sample_ids = {fact.sample for fact in facts if fact.sample and re.search(
                r"\bamostra\s+" + re.escape(_plain(fact.sample)) + r"\b", plain)}
            facts = [fact for fact in facts if fact.sample is None or fact.sample in sample_ids]
            if _direction_is_wrong(plain, facts):
                reject("direction_mismatch", location, "A direção declarada contradiz as evidências citadas ou está sem suporte.")
            for sample_id in sample_ids:
                plain = re.sub(r"(?<=amostra )" + re.escape(_plain(sample_id)) + r"\b", lambda m: " " * len(m[0]), plain)
            # Known labels are not measurements. Unknown group labels are checked.
            if any(isinstance(by_id[key], (SoilSummaryEvidence, SoilGroupsEvidence)) for key in scope):
                plain = re.sub(r"\bconjunto [12]\b|\b_[2]\b", lambda m: " " * len(m[0]), plain)
            # Canonical field IDs are labels only when explicitly introduced as such.
            for key in scope:
                item = by_id[key]
                for attr in ("target_field_id", "reference_field_id"):
                    field_id = getattr(item, attr, None)
                    if field_id:
                        plain = re.sub(r"(?<=talhao )" + re.escape(field_id) + r"\b", lambda m: " " * len(m[0]), plain)
            matches = list(_NUMBER.finditer(plain))
            for index, match in enumerate(matches):
                if not scope:
                    reject("uncited_number", location, "Números exigem evidências citadas no trecho.")
                    continue
                prefix = semantic_text[matches[index - 1].end() if index else 0:match.start()]
                suffix = semantic_text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(plain)]
                unit_match = _UNIT.match(suffix)
                count_match = _COUNT.match(suffix)
                unit = _canonical_unit(unit_match[1]) if unit_match else "count" if count_match else None
                candidates = _qualify(facts, prefix, suffix, unit)
                try:
                    value = _number(match[0])
                    # Bound precision/exponent before decimal rounding to avoid huge allocations.
                    if len(match[0]) > 64 or abs(value.as_tuple().exponent) > 20:
                        raise InvalidOperation
                    matching = [fact for fact in candidates if _matches(value, fact)]
                    compatible = [fact for fact in matching if fact.unit == unit or (unit is None and fact.unit == "ndvi")]
                    if not compatible:
                        opposite = any(_matches(-value, fact) for fact in candidates) if value else False
                        code = "unit_mismatch" if matching else "sign_mismatch" if opposite else "unsupported_number"
                        reject(code, location, "Confira valor, sinal, unidade e métrica nas evidências citadas.")
                except (InvalidOperation, ValueError):
                    reject("unsupported_number_format", location, "Use um número decimal finito em formato suportado.")

    check_text(report.overview.headline, "overview.headline")
    check_text(report.overview.summary, "overview.summary")
    for section in ("findings", "recommendations"):
        for index, item in enumerate(getattr(report, section)):
            fields = ("title", "explanation") if section == "findings" else ("action", "reason")
            for field in fields:
                check_text(getattr(item, field), f"{section}[{index}].{field}", item.evidence_ids)
    for index, item in enumerate(report.limitations):
        check_text(item.title, f"limitations[{index}].title")
        if set(_CITATION.findall(item.explanation)) - by_id.keys():
            reject("unknown_evidence_id", f"limitations[{index}].explanation", "Há referência a uma evidência inexistente.")
        if item.rule_id not in required:
            check_text(item.explanation, f"limitations[{index}].explanation")
    if issues:
        raise ReportValidationError(issues)
    return report
