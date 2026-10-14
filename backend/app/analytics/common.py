"""Shared selection and validation; no CSV reads or external services."""
import unicodedata

import numpy as np
import pandas as pd

from app.analytics.contracts import DatePeriod, Period
from app.analytics.evidence import EvidenceIdGenerator
from app.data.session_store import NormalizedDataset

TOOL_VERSION = "1.0.0"
OPERATION_SOURCES = ["service_orders.csv", "service_orders_fields.csv", "fields.csv"]


class AnalysisUnavailableError(ValueError):
    """The selected data cannot support this calculation."""


def metadata(ids: EvidenceIdGenerator | None, prefix: str, sources: list[str], method: str,
             unit: str | None, count: int | None, **values) -> dict:
    return dict(evidence_id=(ids or EvidenceIdGenerator()).next_id(prefix), unit=unit,
                source_files=sources, method=method, observation_count=count,
                tool_version=TOOL_VERSION, **values)


def fields_for(dataset: NormalizedDataset, target: str, reference: str):
    fields = {field.field_id: field for field in dataset.fields}
    if target not in fields or reference not in fields:
        raise AnalysisUnavailableError("Talhão inexistente no dataset selecionado.")
    if target == reference:
        raise AnalysisUnavailableError("Escolha dois talhões distintos.")
    return fields[target], fields[reference]


def period_frame(frame: pd.DataFrame, period: Period, column: str) -> pd.DataFrame:
    result = frame.copy()
    if result.empty:
        return result
    dates = pd.to_datetime(result[column], utc=True, errors="coerce")
    valid = dates.notna()
    if isinstance(period, DatePeriod):
        valid &= (dates.dt.date >= period.start) & (dates.dt.date <= period.end)
    return result.loc[valid].copy()


def paired_ndvi(dataset, target, reference, period="full_season") -> pd.DataFrame:
    fields_for(dataset, target, reference)
    frame = period_frame(dataset.ndvi_observations, period, "date")
    sides = []
    for field, label in ((target, "target_ndvi"), (reference, "reference_ndvi")):
        rows = frame.loc[frame["field_id"] == field].copy()
        rows["date"] = pd.to_datetime(rows["date"], utc=True).dt.date
        valid = np.isfinite(rows["ndvi"]) & rows["ndvi"].between(-1, 1) & (rows["valid_pixels"] > 0)
        rows = rows.loc[valid]
        # Normalization already aggregates by date. Reject ambiguous internal data.
        if rows["date"].duplicated().any():
            raise AnalysisUnavailableError("NDVI normalizado contém datas duplicadas por talhão.")
        sides.append(rows[["date", "ndvi"]].rename(columns={"ndvi": label}))
    paired = sides[0].merge(sides[1], on="date", how="inner", validate="one_to_one").sort_values("date")
    paired["gap"] = paired["target_ndvi"] - paired["reference_ndvi"]
    return paired


def field_context(target, reference, period):
    return dict(target_field_id=target, reference_field_id=reference, period=period)


def operation_rows(dataset, frame, target, reference, period):
    fields_for(dataset, target, reference)
    frame = period_frame(frame, period, "operation_date")
    return [frame.loc[frame["field_id"] == identifier].copy() for identifier in (target, reference)]


def valid_weighted_rows(rows, columns, positive):
    mask = np.isfinite(rows["area_ha"]) & (rows["area_ha"] > 0)
    for column in columns:
        mask &= np.isfinite(rows[column]) & (rows[column] > 0 if column in positive else rows[column] >= 0)
    valid = rows.loc[mask]
    counts = dict(valid=len(valid), discarded=len(rows) - len(valid))
    if valid.empty:
        raise AnalysisUnavailableError("Não há linhas válidas para ambos os talhões no recorte.")
    return valid, counts


def weighted(rows, column):
    return float(np.average(rows[column], weights=rows["area_ha"]))


def canonical_operation(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().upper().split())
