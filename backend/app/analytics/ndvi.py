"""Single-field and paired NDVI analyses with explicit inference limits."""
import numpy as np
import pandas as pd

from app.analytics.common import AnalysisUnavailableError, field_context, metadata, paired_ndvi, period_frame
from app.analytics.contracts import (
    AbruptNdviChange, FieldNdviEvidence, InitialEvidence, NdviChangeEvidence,
    NdviEvidence, PairedNdviTestEvidence,
)
from app.analytics.statistics import paired_sign_statistics, select_paired_continuous_test


def _field_ndvi_rows(dataset, field_id, period):
    if field_id not in {field.field_id for field in dataset.fields}:
        raise AnalysisUnavailableError("Talhão inexistente no dataset selecionado.")
    rows = period_frame(dataset.ndvi_observations, period, "date")
    rows = rows.loc[rows["field_id"] == field_id].copy()
    rows["date"] = pd.to_datetime(rows["date"], utc=True, errors="coerce").dt.date
    valid = rows["ndvi"].map(pd.notna) & rows["ndvi"].between(-1, 1) & (rows["valid_pixels"] > 0)
    rows = rows.loc[valid, ["date", "ndvi"]].sort_values("date")
    if rows.empty:
        raise AnalysisUnavailableError("NDVI indisponível para o talhão no período selecionado.")
    if rows["date"].duplicated().any():
        raise AnalysisUnavailableError("NDVI normalizado contém datas duplicadas para o talhão.")
    return rows


def analyze_field_ndvi(dataset, field_id, period="full_season", *, ids=None):
    """Describe one field's NDVI trajectory and flag unusually large adjacent changes.

    This is an operational rule over observed differences, not an anomaly test.
    The threshold is the larger of 0.05 NDVI or twice the median absolute
    adjacent change, which keeps the calculation deterministic and explainable.
    """
    rows = _field_ndvi_rows(dataset, field_id, period)
    rows["change_from_previous"] = rows["ndvi"].diff()
    changes = rows["change_from_previous"].dropna().abs()
    median_change = float(changes.median()) if not changes.empty else 0.0
    threshold = max(0.05, 2 * median_change)
    abrupt = []
    for index in range(1, len(rows)):
        change = float(rows.iloc[index]["change_from_previous"])
        if abs(change) + 1e-12 >= threshold:
            abrupt.append(AbruptNdviChange(
                previous_date=rows.iloc[index - 1]["date"], date=rows.iloc[index]["date"],
                change=change, direction="increase" if change > 0 else "decrease",
            ))
    values = rows["ndvi"].astype(float)
    total_change = float(values.iloc[-1] - values.iloc[0])
    return FieldNdviEvidence(
        **metadata(
            ids, "FIELD-NDVI", ["ndvi_metadata.csv", "fields.csv"],
            "Série temporal de um talhão, sem interpolação. Variações bruscas usam regra operacional: abs(variação adjacente) >= max(0,05; 2 × mediana das variações absolutas). Não é teste estatístico de anomalia.",
            "ndvi", len(rows), metric="field_ndvi", target_value=float(values.mean()), difference=total_change,
        ),
        field_id=field_id, period=period, observations=len(rows), mean_ndvi=float(values.mean()),
        min_ndvi=float(values.min()), max_ndvi=float(values.max()), first_ndvi=float(values.iloc[0]),
        last_ndvi=float(values.iloc[-1]), total_change=total_change, abrupt_change_threshold=float(threshold),
        abrupt_changes=abrupt,
        series=[{
            "date": row.date, "ndvi": float(row.ndvi),
            "change_from_previous": None if pd.isna(row.change_from_previous) else float(row.change_from_previous),
        } for row in rows.itertuples(index=False)],
        warnings=["Há menos de três observações; a trajetória temporal é limitada."] if len(rows) < 3 else [],
    )


def detect_field_ndvi_changes(dataset, field_id, period="full_season", *, ids=None):
    """Detect isolated adjacent changes with a robust median/MAD rule."""
    rows = _field_ndvi_rows(dataset, field_id, period)
    if len(rows) < 5:
        raise AnalysisUnavailableError(
            "Detecção robusta de mudanças exige ao menos cinco observações válidas de NDVI."
        )
    rows["change"] = rows["ndvi"].astype(float).diff()
    changes = rows["change"].dropna().to_numpy(dtype=float)
    typical = float(np.median(changes))
    deviations = np.abs(changes - typical)
    mad = float(np.median(deviations))
    practical_threshold = 0.05
    robust_threshold = 3.5
    detected = []
    for index, change in enumerate(changes, start=1):
        deviation = float(abs(change - typical))
        score = None if mad <= 1e-12 else float(0.67448975 * (change - typical) / mad)
        unusual = (
            deviation >= practical_threshold
            if score is None
            else abs(score) >= robust_threshold and abs(change) >= practical_threshold
        )
        if unusual:
            detected.append({
                "previous_date": rows.iloc[index - 1]["date"],
                "date": rows.iloc[index]["date"],
                "change": float(change),
                "deviation_from_typical_change": deviation,
                "robust_score": score,
                "direction": "increase" if change > 0 else "decrease",
            })
    warnings = [
        "Mudanças detectadas são sinais temporais; a série isolada não identifica a causa."
    ]
    if not detected:
        warnings.append("Nenhuma mudança adjacente ultrapassou simultaneamente os critérios robusto e prático.")
    return NdviChangeEvidence(
        **metadata(
            ids,
            "NDVI-CHANGE",
            ["ndvi_metadata.csv", "fields.csv"],
            "Mudanças adjacentes avaliadas pela mediana e MAD das diferenças; escore robusto >= 3,5 e variação absoluta >= 0,05. Quando MAD=0, usa desvio do padrão típico >= 0,05.",
            "ndvi",
            len(rows),
            metric="robust_adjacent_change",
        ),
        field_id=field_id,
        period=period,
        observations=len(rows),
        adjacent_changes=len(changes),
        typical_change=typical,
        change_mad=mad,
        practical_threshold=practical_threshold,
        robust_score_threshold=robust_threshold,
        changes=detected,
        warnings=warnings,
    )


def test_paired_ndvi_difference(
    dataset, target_field_id, reference_field_id, period="full_season", *, ids=None
):
    """Run an exact paired sign test on same-date NDVI differences."""
    paired = paired_ndvi(dataset, target_field_id, reference_field_id, period)
    nonzero_count = int((paired["gap"].abs() > 1e-12).sum())
    selection = select_paired_continuous_test(nonzero_count, repeated_time=True)
    if selection.method == "descriptive_only":
        raise AnalysisUnavailableError(selection.reason)
    try:
        result = paired_sign_statistics(paired["gap"].astype(float).tolist())
    except ValueError as error:
        raise AnalysisUnavailableError(str(error)) from None
    warnings = [
        "O teste é exploratório porque observações sucessivas da série podem ser autocorrelacionadas.",
        "Associação ou diferença temporal não demonstra efeito causal do manejo.",
    ]
    if result["median_ci_low"] is None:
        warnings.append("A amostra não permite um intervalo exato finito de 95% para a mediana.")
    return PairedNdviTestEvidence(
        **metadata(
            ids,
            "NDVI-PAIRED-TEST",
            ["ndvi_metadata.csv", "fields.csv"],
            selection.reason + " Tamanho de efeito: correlação bisserial por postos pareados.",
            "ndvi",
            result["pair_count"],
            metric="paired_ndvi_difference",
            target_value=float(paired["target_ndvi"].median()),
            reference_value=float(paired["reference_ndvi"].median()),
            difference=result["median_difference"],
        ),
        **field_context(target_field_id, reference_field_id, period),
        target_median=float(paired["target_ndvi"].median()),
        reference_median=float(paired["reference_ndvi"].median()),
        alpha=0.05,
        warnings=warnings,
        **result,
    )


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
