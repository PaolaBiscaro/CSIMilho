"""Paired NDVI and the explicitly non-statistical initial-condition rule."""
import pandas as pd

from app.analytics.common import AnalysisUnavailableError, field_context, metadata, paired_ndvi
from app.analytics.contracts import InitialEvidence, NdviEvidence


def compare_ndvi(dataset, target_field_id, reference_field_id, period="full_season", *, ids=None):
    paired = paired_ndvi(dataset, target_field_id, reference_field_id, period)
    if paired.empty:
        raise AnalysisUnavailableError("NDVI indisponível: é necessária ao menos uma data pareada.")
    target, reference, gap = (float(paired[column].mean()) for column in ("target_ndvi", "reference_ndvi", "gap"))
    return NdviEvidence(
        **metadata(ids, "NDVI", ["ndvi_metadata.csv", "fields.csv"],
                   "Inner join por data, sem interpolação; médias e gap alvo menos referência. Mínimo de uma data; menos de cinco reduz comparabilidade.",
                   "ndvi", len(paired), metric="mean_gap", target_value=target, reference_value=reference, difference=gap),
        **field_context(target_field_id, reference_field_id, period),
        paired_dates=len(paired), target_mean=target, reference_mean=reference, mean_gap=gap,
        negative_dates=int((paired.gap < 0).sum()), positive_dates=int((paired.gap > 0).sum()),
        equal_dates=int((paired.gap == 0).sum()), series=paired.to_dict("records"),
        warnings=["Menos de cinco datas pareadas."] if len(paired) < 5 else [],
    )


def check_initial_condition(dataset, target_field_id, reference_field_id, period="full_season", *, ids=None):
    paired = paired_ndvi(dataset, target_field_id, reference_field_id, period)
    first_dates = []
    for identifier in (target_field_id, reference_field_id):
        rows = dataset.planting_operations.loc[dataset.planting_operations.field_id == identifier]
        dates = pd.to_datetime(rows.operation_date, utc=True, errors="coerce").dropna()
        if not dates.empty:
            first_dates.append(dates.min().date())
    cutoff = min(first_dates) if len(first_dates) == 2 else None
    before = paired.loc[paired.date < cutoff] if cutoff else paired.iloc[:0]
    available = cutoff is not None and len(before) >= 3
    gap = float(before.gap.mean()) if available else None
    return InitialEvidence(
        **metadata(ids, "INITIAL", ["ndvi_metadata.csv", "LAYER_MAP_PLANTING.csv", "fields.csv"],
                   "Pares estritamente anteriores à menor primeira data de plantio; mínimo de três pares; abs(gap) >= 0,02. Heurística operacional, não teste de significância.",
                   "ndvi", len(before), metric="initial_mean_gap", difference=gap),
        **field_context(target_field_id, reference_field_id, period), available=available,
        cutoff_date=cutoff, paired_dates=len(before), mean_gap=gap,
        different=bool(abs(gap) >= 0.02 - 1e-12) if gap is not None else None,
        warnings=[] if available else ["Condição inicial indisponível: faltam datas de plantio ou três pares anteriores ao corte."],
    )
