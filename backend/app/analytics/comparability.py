"""Five transparent criteria; a low score alone does not imply incompatibility."""
from app.analytics.common import canonical_operation, field_context, fields_for, metadata, operation_rows, paired_ndvi
from app.analytics.contracts import ComparisonEvidence, Criterion
from app.analytics.ndvi import check_initial_condition
from app.data.contracts import FieldManagement, FieldPurpose, ValidPair


def structural_pairs(fields):
    return [ValidPair(target_field_id=a.field_id, reference_field_id=b.field_id, purpose=a.purpose)
            for a in fields for b in fields
            if a.field_id != b.field_id and a.purpose != FieldPurpose.UNKNOWN and a.purpose == b.purpose
            and FieldManagement.UNKNOWN not in (a.management, b.management) and a.management != b.management]


def cultures(rows):
    # Only explicit crop names in planting operations are evidence of culture.
    known = {"MILHO", "SOJA", "SORGO", "TRIGO", "FEIJAO"}
    return {crop for operation in rows.operation for crop in known
            if crop in canonical_operation(operation).split()}


def validate_comparison(dataset, target_field_id, reference_field_id, period="full_season", *, ids=None):
    target, reference = fields_for(dataset, target_field_id, reference_field_id)
    planting = operation_rows(dataset, dataset.planting_operations, target_field_id, reference_field_id, period)
    fertilizer = operation_rows(dataset, dataset.fertilization_operations, target_field_id, reference_field_id, period)
    crop_a, crop_b = (cultures(rows) for rows in planting)
    same_crop = crop_a == crop_b if crop_a and crop_b else None
    same_purpose = target.purpose == reference.purpose and target.purpose != FieldPurpose.UNKNOWN
    distinct_management = target.management != reference.management and FieldManagement.UNKNOWN not in (target.management, reference.management)
    paired = paired_ndvi(dataset, target_field_id, reference_field_id, period)
    initial = check_initial_condition(dataset, target_field_id, reference_field_id, period)
    common = set(fertilizer[0].operation) & set(fertilizer[1].operation)
    common = sorted(common, key=lambda name: (name != "CALAGEM", name))
    complete = all(not rows.empty for rows in planting + fertilizer)
    criteria = [
        Criterion(id="same_crop", label="Mesma cultura", satisfied=same_crop, detail="Cultura explícita nas operações: " + ", ".join(sorted(crop_a | crop_b)) if crop_a or crop_b else "Cultura não identificada nas operações de plantio."),
        Criterion(id="same_purpose", label="Mesma finalidade", satisfied=same_purpose, detail=f"{target.purpose.value} × {reference.purpose.value}"),
        Criterion(id="paired_dates", label="Ao menos cinco datas pareadas", satisfied=len(paired) >= 5, detail=f"{len(paired)} datas pareadas."),
        Criterion(id="operations", label="Plantio e fertilização nos dois talhões", satisfied=complete, detail="Disponibilidade no período selecionado."),
        Criterion(id="initial_condition", label="Condição inicial sem gap relevante", satisfied=not initial.different if initial.available else None, detail=initial.method if initial.available else initial.warnings[0]),
    ]
    allowed = same_purpose and distinct_management and same_crop is not False
    warnings = [criterion.detail for criterion in criteria if criterion.satisfied is not True]
    if not distinct_management:
        warnings.append("Os manejos devem ser conhecidos e distintos.")
    analyses = []
    if allowed:
        if not paired.empty:
            analyses.append("compare_ndvi")
        if initial.available:
            analyses.append("check_initial_condition")
        if all(not rows.empty for rows in planting):
            analyses.append("compare_population")
        if common:
            analyses.append("application_compliance")
        if not dataset.soil_samples.empty:
            analyses.append("summarize_soil_analysis")
            if any(bool(group) for group in dataset.soil_samples.group_2):
                analyses.append("compare_soil_measurement_groups")
    return ComparisonEvidence(
        **metadata(ids, "COMP", ["fields.csv", "LAYER_MAP_PLANTING.csv", "LAYER_MAP_FERTILIZATION.csv", "ndvi_metadata.csv"],
                   "Um ponto por critério satisfeito; critério desconhecido não pontua. Cultura ou finalidade incompatível e manejo não distinto bloqueiam o par.", None, len(paired)),
        **field_context(target_field_id, reference_field_id, period), allowed=allowed,
        score=sum(item.satisfied is True for item in criteria), criteria=criteria, warnings=warnings,
        available_analyses=analyses, common_operations=common, paired_dates=len(paired),
    )
