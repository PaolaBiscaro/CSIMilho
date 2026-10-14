from app.analytics.common import OPERATION_SOURCES, AnalysisUnavailableError, canonical_operation, field_context, metadata, operation_rows, valid_weighted_rows, weighted
from app.analytics.contracts import ApplicationEvidence


def application_compliance(dataset, target_field_id, reference_field_id, period="full_season", operation="CALAGEM", *, ids=None):
    operation = canonical_operation(operation)
    sides = operation_rows(dataset, dataset.fertilization_operations, target_field_id, reference_field_id, period)
    checked = []
    for rows in sides:
        selected = rows.loc[rows.operation.map(canonical_operation) == operation]
        if selected.empty:
            raise AnalysisUnavailableError(f"Operação {operation} indisponível para ambos os talhões.")
        checked.append(valid_weighted_rows(selected, ["applied_dose_kg_ha", "configured_dose_kg_ha"], {"configured_dose_kg_ha"}))
    applied = [weighted(rows, "applied_dose_kg_ha") for rows, _ in checked]
    configured = [weighted(rows, "configured_dose_kg_ha") for rows, _ in checked]
    compliance = [a/c*100 for a, c in zip(applied, configured)]
    counts = [count for _, count in checked]
    # Prefix is a readable category; the counter still guarantees uniqueness if labels collapse.
    import re
    label = re.sub(r"[^A-Z0-9]+", "-", operation).strip("-")
    label = "-".join(segment if segment[0].isalpha() else "N" + segment for segment in label.split("-") if segment) or "OP"
    return ApplicationEvidence(
        **metadata(ids, f"APP-{label}", ["LAYER_MAP_FERTILIZATION.csv", *OPERATION_SOURCES],
                   "Doses ponderadas por área; conformidade = aplicada / configurada × 100, sem teto de 100%. Diferença em pontos percentuais. Contagens referem-se ao recorte normalizado.",
                   "%", sum(count["valid"] for count in counts), metric="application_compliance",
                   target_value=compliance[0], reference_value=compliance[1], difference=compliance[0]-compliance[1]),
        **field_context(target_field_id, reference_field_id, period), operation=operation,
        target_compliance_percent=compliance[0], reference_compliance_percent=compliance[1],
        target_applied_dose=applied[0], reference_applied_dose=applied[1],
        target_configured_dose=configured[0], reference_configured_dose=configured[1],
        target_rows=counts[0], reference_rows=counts[1],
    )
