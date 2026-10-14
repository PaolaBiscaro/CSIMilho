from app.analytics.common import OPERATION_SOURCES, field_context, metadata, operation_rows, valid_weighted_rows, weighted
from app.analytics.contracts import PopulationEvidence


def compare_population(dataset, target_field_id, reference_field_id, period="full_season", *, ids=None):
    sides = operation_rows(dataset, dataset.planting_operations, target_field_id, reference_field_id, period)
    checked = [valid_weighted_rows(rows, ["population_per_ha"], {"population_per_ha"}) for rows in sides]
    target, reference = (weighted(rows, "population_per_ha") for rows, _ in checked)
    counts = [count for _, count in checked]
    return PopulationEvidence(
        **metadata(ids, "POP", ["LAYER_MAP_PLANTING.csv", *OPERATION_SOURCES],
                   "Σ(população × área) / Σ(área), por talhão; diferença percentual = (alvo − referência) / referência × 100. Contagens referem-se ao recorte normalizado; descartes de importação permanecem nos avisos do pacote.",
                   "plants/ha", sum(count["valid"] for count in counts), metric="population_per_ha",
                   target_value=target, reference_value=reference, difference=target-reference),
        **field_context(target_field_id, reference_field_id, period),
        target_population_per_ha=target, reference_population_per_ha=reference,
        difference_percent=(target-reference)/reference*100, target_rows=counts[0], reference_rows=counts[1],
    )
