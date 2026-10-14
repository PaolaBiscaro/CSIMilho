"""Dataset-wide soil summaries. No field, time or depth association is inferred."""
import math
from typing import get_args

import numpy as np

from app.analytics.common import AnalysisUnavailableError, metadata
from app.analytics.contracts import SoilGroupsEvidence, SoilMetricName, SoilSummaryEvidence

SOURCES = ["soil_analysis.csv"]
LIMITATIONS = [
    "As amostras pertencem ao dataset, sem vínculo documentado com talhão, coordenada, data ou profundidade.",
    "O significado do sufixo _2 não está documentado; os grupos são somente Conjunto 1 e Conjunto 2.",
    "Unidades e referências agronômicas não documentadas; não há classificação de suficiência.",
]
FAMILIES = {
    "textura": ("ARGILA", "SILTE", "AREIA"),
    "acidez_fertilidade": ("MO", "CTC", "CTCE", "PHCACL2", "P", "AL", "SATAL", "S", "HAL"),
    "bases": ("CA", "SATCA", "MG", "SATMG", "K", "SATK", "SATB", "SB"),
    "micronutrientes": ("B", "ZN", "MN", "CU", "FE"),
}


def family(metric):
    return next(name for name, metrics in FAMILIES.items() if metric in metrics)


def valid_value(value):
    return value is not None and not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def selected_metrics(samples, groups, requested):
    available = set().union(*(set(sample[group]) for sample in samples for group in groups))
    allowed = get_args(SoilMetricName)
    if requested is not None and (not requested or set(requested) - set(allowed)):
        raise AnalysisUnavailableError("Filtro de métricas de solo inválido.")
    return list(dict.fromkeys(requested)) if requested is not None else [name for name in allowed if name in available]


def texture_composition(samples, group):
    records = []
    for sample in samples:
        values = [sample[group].get(key) for key in ("AREIA", "SILTE", "ARGILA")]
        if not all(valid_value(value) and 0 <= value <= 100 for value in values):
            continue
        total = sum(values)
        if not 95 <= total <= 105:
            continue
        sand, silt, clay = values
        records.append(dict(sample_id=sample["sample_id"], sand=sand/total*100,
                            silt=silt/total*100, clay=clay/total*100, original_total=total,
                            original_sand=sand, original_silt=silt, original_clay=clay))
    return dict(valid_n=len(records), excluded_n=len(samples)-len(records), samples=records, source_files=SOURCES)


def summarize_soil_analysis(dataset, measurement_group="group_1", metrics=None, *, ids=None):
    if measurement_group not in ("group_1", "group_2"):
        raise AnalysisUnavailableError("Conjunto de medição inválido.")
    samples = dataset.soil_samples.to_dict("records")
    names = selected_metrics(samples, [measurement_group], metrics)
    output = []
    for name in names:
        values = [sample[measurement_group].get(name) for sample in samples]
        values = [value for value in values if valid_value(value)]
        stats = {key: None for key in ("mean", "median", "min", "max", "q1", "q3")}
        if values:
            minimum, q1, median, q3, maximum = np.quantile(values, [0, .25, .5, .75, 1], method="linear")
            stats = dict(mean=float(np.mean(values)), median=float(median), min=float(minimum),
                         max=float(maximum), q1=float(q1), q3=float(q3))
        output.append(dict(name=name, family=family(name), valid_n=len(values), missing_n=len(samples)-len(values),
                           source_files=SOURCES, **stats))
    valid = sum(metric["valid_n"] for metric in output)
    expected = len(names) * len(samples)
    warnings = []
    if not valid:
        warnings.append("Nenhum valor válido disponível no conjunto/filtro selecionado.")
    if valid < expected:
        warnings.append("Valores ausentes foram excluídos das estatísticas, sem substituição por zero.")
    return SoilSummaryEvidence(
        **metadata(ids, "SOIL-SUMMARY", SOURCES,
                   "Estatísticas descritivas por variável sobre valores válidos; quartis por interpolação linear (NumPy); sem classificação agronômica.",
                   None, len(samples)), measurement_group=measurement_group, sample_count=len(samples),
        valid_values=valid, expected_values=expected, completeness_percent=valid/expected*100 if expected else None,
        metrics=output, texture=texture_composition(samples, measurement_group), warnings=warnings, limitations=LIMITATIONS,
    )


def compare_soil_measurement_groups(dataset, metrics=None, *, ids=None):
    samples = dataset.soil_samples.to_dict("records")
    names = selected_metrics(samples, ["group_1", "group_2"], metrics)
    present_1 = set().union(*(set(sample["group_1"]) for sample in samples))
    present_2 = set().union(*(set(sample["group_2"]) for sample in samples))
    output, warnings = [], []
    for name in names:
        if name not in present_1 & present_2:
            if metrics is not None:
                warnings.append(f"{name} não está presente nos dois conjuntos.")
            continue
        pairs = []
        for sample in samples:
            one, two = sample["group_1"].get(name), sample["group_2"].get(name)
            if valid_value(one) and valid_value(two):
                pairs.append(dict(sample_id=sample["sample_id"], group_1=one, group_2=two, delta=two-one))
        output.append(dict(name=name, family=family(name), valid_n=len(pairs), pairs=pairs,
                           median_delta=float(np.median([pair["delta"] for pair in pairs])) if pairs else None,
                           source_files=SOURCES))
    if not any(metric["valid_n"] for metric in output):
        warnings.append("Não há pares válidos entre Conjunto 1 e Conjunto 2.")
    return SoilGroupsEvidence(
        **metadata(ids, "SOIL-GROUPS", SOURCES, "Comparação pareada por AMOSTRA e variável; delta = Conjunto 2 − Conjunto 1; mediana dos deltas válidos.", None, len(samples)),
        sample_count=len(samples), metrics=output, warnings=warnings, limitations=LIMITATIONS,
    )
