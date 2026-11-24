"""Temporal linkage between documented field operations and NDVI observations."""

import pandas as pd

from app.analytics.common import AnalysisUnavailableError, canonical_operation, metadata, period_frame
from app.analytics.contracts import OperationNdviEvidence
from app.analytics.ndvi import _field_ndvi_rows


def associate_field_operations_ndvi(
    dataset,
    field_id,
    period="full_season",
    operation=None,
    max_window_days=45,
    *,
    ids=None,
):
    """Link operations to nearest valid observations before/on and after them.

    The result is temporal co-occurrence only. It must never be phrased as the
    operation causing the subsequent NDVI change.
    """
    ndvi = _field_ndvi_rows(dataset, field_id, period)
    event_frames = []
    sources = ["ndvi_metadata.csv", "fields.csv"]
    for frame, kind, source in (
        (dataset.planting_operations, "PLANTIO", "LAYER_MAP_PLANTING.csv"),
        (dataset.fertilization_operations, "APLICAÇÃO", "LAYER_MAP_FERTILIZATION.csv"),
    ):
        rows = period_frame(frame, period, "operation_date")
        rows = rows.loc[rows["field_id"] == field_id].copy()
        if rows.empty:
            continue
        rows["operation_date"] = pd.to_datetime(
            rows["operation_date"], utc=True, errors="coerce"
        ).dt.date
        rows = rows.loc[rows["operation_date"].notna()]
        rows["normalized_operation"] = rows["operation"].map(canonical_operation)
        rows["event_label"] = kind + ": " + rows["normalized_operation"]
        event_frames.append(rows[["operation_date", "normalized_operation", "event_label"]])
        sources.append(source)
    if not event_frames:
        raise AnalysisUnavailableError("Não há operações documentadas para o talhão no período selecionado.")
    events = pd.concat(event_frames, ignore_index=True).drop_duplicates(
        subset=["operation_date", "event_label"]
    )
    if operation is not None:
        selected = canonical_operation(operation)
        events = events.loc[
            (events["normalized_operation"] == selected)
            | events["event_label"].str.contains(selected, regex=False)
        ]
    if events.empty:
        raise AnalysisUnavailableError("A operação solicitada não está documentada para o talhão no período.")

    links = []
    for event in events.sort_values("operation_date").itertuples(index=False):
        before = ndvi.loc[ndvi["date"] <= event.operation_date]
        after = ndvi.loc[ndvi["date"] > event.operation_date]
        if before.empty or after.empty:
            continue
        before_row = before.iloc[-1]
        after_row = after.iloc[0]
        days_before = (event.operation_date - before_row["date"]).days
        days_after = (after_row["date"] - event.operation_date).days
        if days_before > max_window_days or days_after > max_window_days:
            continue
        links.append(
            {
                "operation": event.event_label,
                "operation_date": event.operation_date,
                "before_date": before_row["date"],
                "after_date": after_row["date"],
                "days_before": days_before,
                "days_after": days_after,
                "before_ndvi": float(before_row["ndvi"]),
                "after_ndvi": float(after_row["ndvi"]),
                "ndvi_change": float(after_row["ndvi"] - before_row["ndvi"]),
            }
        )
    if not links:
        raise AnalysisUnavailableError(
            "Não há observações válidas de NDVI antes e depois das operações dentro da janela selecionada."
        )
    return OperationNdviEvidence(
        **metadata(
            ids,
            "OPERATION-NDVI",
            list(dict.fromkeys(sources)),
            "Associação temporal observacional: observação válida de NDVI mais próxima em ou antes da operação e primeira observação posterior, ambas dentro da janela configurada; não estima causalidade.",
            "ndvi",
            len(links),
            metric="ndvi_change_around_operation",
        ),
        field_id=field_id,
        period=period,
        requested_operation=operation,
        max_window_days=max_window_days,
        eligible_operations=len(links),
        links=links,
        warnings=[
            "Coincidência temporal não demonstra que a operação causou a mudança de NDVI.",
            "Outros fatores não medidos podem explicar o comportamento observado.",
        ],
    )
