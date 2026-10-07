from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import numpy as np
import pandas as pd
from pydantic import ValidationError
from shapely import wkt
from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from app.data.contracts import (
    Centroid,
    FieldManagement,
    FieldPurpose,
    FieldRecord,
    OperationLinkage,
    ValidationIssue,
)

FIELDS_FILE = "fields.csv"
FIELDS_REQUIRED_COLUMNS = {"idField", "idFarm", "fieldName", "fieldAreaCentroid", "fieldGeom"}
PLANTING_FILE = "LAYER_MAP_PLANTING.csv"
PLANTING_REQUIRED_COLUMNS = {
    "geometry", "Timestamp", "Date Time", "Service Order", "Operation",
    "Area - ha", "Population - ha",
}
FERTILIZATION_FILE = "LAYER_MAP_FERTILIZATION.csv"
FERTILIZATION_REQUIRED_COLUMNS = {
    "geometry", "Timestamp", "Date Time", "Service Order", "operation",
    "Area - ha", "AppliedDos - kg/ha", "Configured - kg/ha",
}
NDVI_FILE = "ndvi_metadata.csv"
NDVI_REQUIRED_COLUMNS = {
    "filename", "season_id", "crs", "bounds_left", "bounds_bottom",
    "bounds_right", "bounds_top", "b1_valid_pixels", "b1_mean",
}
SOIL_FILE = "soil_analysis.csv"
SOIL_TEXTURE_METRICS = ("ARGILA", "SILTE", "AREIA")
SOIL_FERTILITY_METRICS = (
    "MO", "CTC", "CTCE", "PHCACL2", "CA", "SATCA", "MG", "SATMG", "K",
    "SATK", "P", "SATB", "AL", "SATAL", "S", "HAL", "SB",
)
SOIL_MICRONUTRIENT_METRICS = ("B", "ZN", "MN", "CU", "FE")
SOIL_REQUIRED_COLUMNS = {
    "AMOSTRA", *SOIL_TEXTURE_METRICS, *SOIL_FERTILITY_METRICS,
}


@dataclass
class FieldNormalizationResult:
    fields: list[FieldRecord] = field(default_factory=list)
    geometries: dict[str, BaseGeometry] = field(default_factory=dict)
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)


@dataclass
class OperationNormalizationResult:
    frame: pd.DataFrame
    discarded_rows: int = 0
    linkage: OperationLinkage = field(default_factory=OperationLinkage)
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)


@dataclass
class NdviNormalizationResult:
    frame: pd.DataFrame
    discarded_rows: int = 0
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)


@dataclass
class SoilNormalizationResult:
    frame: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(
        columns=["sample_id", "scope", "group_1", "group_2"]
    ))
    measurement_groups: list[str] = field(default_factory=list)
    discarded_rows: int = 0
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)


def normalize_fields(frame: pd.DataFrame) -> FieldNormalizationResult:
    result = FieldNormalizationResult()
    missing = sorted(FIELDS_REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        result.errors.extend(
            ValidationIssue(
                code="missing_column",
                message=f"Coluna obrigatória ausente em {FIELDS_FILE}: {column}.",
                file=FIELDS_FILE,
            )
            for column in missing
        )
        return result

    seen_ids: set[str] = set()
    for index, row in frame.iterrows():
        row_number = int(index) + 2 if isinstance(index, int) else 2
        try:
            field_id = _required_text(row["idField"], "idField")
            if field_id in seen_ids:
                raise ValueError(f"idField duplicado: {field_id}")
            seen_ids.add(field_id)
            farm_id = _required_text(row["idFarm"], "idFarm")
            name = _required_text(row["fieldName"], "fieldName")
            classification_name = _normalize_field_name(name)
            centroid = _parse_centroid(row["fieldAreaCentroid"])
            geometry = _parse_field_geometry(row["fieldGeom"])
            record = FieldRecord(
                field_id=field_id,
                farm_id=farm_id,
                name=name,
                label=_derive_label(classification_name),
                purpose=_derive_purpose(classification_name),
                management=_derive_management(classification_name),
                centroid=centroid,
                geometry_available=True,
            )
        except (TypeError, ValueError, json.JSONDecodeError, ValidationError, GEOSException) as exc:
            result.errors.append(
                ValidationIssue(
                    code="invalid_field",
                    message=f"Talhão inválido na linha {row_number}: {exc}",
                    file=FIELDS_FILE,
                    row=row_number,
                )
            )
            continue

        if classification_name != unicodedata.normalize("NFC", name).strip():
            result.warnings.append(
                ValidationIssue(
                    code="field_name_normalized",
                    message=(f"O nome do talhão {field_id} foi normalizado de "
                             f"'{name}' para '{classification_name}' para classificação."),
                    file=FIELDS_FILE,
                    row=row_number,
                )
            )
        result.fields.append(record)
        result.geometries[field_id] = geometry

    if not result.fields:
        result.errors.append(
            ValidationIssue(code="no_fields", message="Nenhum talhão válido foi reconhecido.", file=FIELDS_FILE)
        )
    return result


def normalize_planting(
    frame: pd.DataFrame,
    service_order_numbers: dict[str, str],
    service_order_candidates: dict[str, set[str]],
    field_geometries: dict[str, BaseGeometry],
) -> OperationNormalizationResult:
    columns = ["field_id", "service_order_id", "service_order_number", "operation",
               "operation_date", "area_ha", "population_per_ha"]
    result = OperationNormalizationResult(frame=pd.DataFrame(columns=columns))
    if _report_missing_columns(frame, PLANTING_REQUIRED_COLUMNS, PLANTING_FILE, result.errors):
        return result

    records: list[dict[str, Any]] = []
    warning_counts: Counter[str] = Counter()
    for index, row in frame.iterrows():
        row_number = int(index) + 2 if isinstance(index, int) else 2
        link = _resolve_operation_field(
            row, row_number, PLANTING_FILE, service_order_numbers,
            service_order_candidates, field_geometries, result, warning_counts,
        )
        if link is None:
            result.discarded_rows += 1
            continue
        field_id, service_order_id, service_order_number = link
        try:
            operation = _required_text(row["Operation"], "Operation").upper()
            operation_date = _operation_date(row["Date Time"], row["Timestamp"])
            area = _finite_number(row["Area - ha"], "Area - ha")
            population = _finite_number(row["Population - ha"], "Population - ha")
            if area <= 0 or population <= 0:
                raise ValueError("área e população devem ser positivas")
        except (TypeError, ValueError):
            result.discarded_rows += 1
            continue
        records.append({
            "field_id": field_id, "service_order_id": service_order_id,
            "service_order_number": service_order_number, "operation": operation,
            "operation_date": operation_date, "area_ha": area,
            "population_per_ha": population,
        })

    result.frame = pd.DataFrame.from_records(records, columns=columns)
    _append_linkage_warnings(result, PLANTING_FILE, warning_counts)
    _append_discard_warning(result, PLANTING_FILE)
    return result


def normalize_fertilization(
    frame: pd.DataFrame,
    service_order_numbers: dict[str, str],
    service_order_candidates: dict[str, set[str]],
    field_geometries: dict[str, BaseGeometry],
) -> OperationNormalizationResult:
    columns = ["field_id", "service_order_id", "service_order_number", "operation",
               "operation_date", "area_ha", "applied_dose_kg_ha", "configured_dose_kg_ha"]
    result = OperationNormalizationResult(frame=pd.DataFrame(columns=columns))
    if _report_missing_columns(frame, FERTILIZATION_REQUIRED_COLUMNS, FERTILIZATION_FILE, result.errors):
        return result

    records: list[dict[str, Any]] = []
    warning_counts: Counter[str] = Counter()
    for index, row in frame.iterrows():
        row_number = int(index) + 2 if isinstance(index, int) else 2
        link = _resolve_operation_field(
            row, row_number, FERTILIZATION_FILE, service_order_numbers,
            service_order_candidates, field_geometries, result, warning_counts,
        )
        if link is None:
            result.discarded_rows += 1
            continue
        field_id, service_order_id, service_order_number = link
        try:
            operation = _required_text(row["operation"], "operation").upper()
            operation_date = _operation_date(row["Date Time"], row["Timestamp"])
            area = _finite_number(row["Area - ha"], "Area - ha")
            applied = _finite_number(row["AppliedDos - kg/ha"], "AppliedDos - kg/ha")
            configured = _finite_number(row["Configured - kg/ha"], "Configured - kg/ha")
            if area <= 0 or applied < 0 or configured <= 0:
                raise ValueError("área e dose configurada devem ser positivas; dose aplicada não pode ser negativa")
        except (TypeError, ValueError):
            result.discarded_rows += 1
            continue
        records.append({
            "field_id": field_id, "service_order_id": service_order_id,
            "service_order_number": service_order_number, "operation": operation,
            "operation_date": operation_date, "area_ha": area,
            "applied_dose_kg_ha": applied, "configured_dose_kg_ha": configured,
        })

    result.frame = pd.DataFrame.from_records(records, columns=columns)
    _append_linkage_warnings(result, FERTILIZATION_FILE, warning_counts)
    _append_discard_warning(result, FERTILIZATION_FILE)
    return result


def _resolve_operation_field(
    row: pd.Series,
    row_number: int,
    file_name: str,
    service_order_numbers: dict[str, str],
    service_order_candidates: dict[str, set[str]],
    field_geometries: dict[str, BaseGeometry],
    result: OperationNormalizationResult,
    warning_counts: Counter[str],
) -> tuple[str, str, str] | None:
    try:
        service_order_number = _canonical_service_order_number(row["Service Order"])
    except ValueError:
        result.linkage.unassigned_rows += 1
        warning_counts["unmatched_service_order"] += 1
        return None

    service_order_id = service_order_numbers.get(service_order_number)
    if service_order_id is None:
        result.linkage.unassigned_rows += 1
        warning_counts["unmatched_service_order"] += 1
        return None
    candidate_ids = sorted(service_order_candidates.get(service_order_id, set()))
    candidates = [(field_id, field_geometries[field_id]) for field_id in candidate_ids
                  if field_id in field_geometries]
    if not candidates:
        result.linkage.unassigned_rows += 1
        warning_counts["service_order_without_fields"] += 1
        return None

    try:
        operation_geometry = _parse_operation_geometry(row["geometry"])
    except (TypeError, ValueError, GEOSException):
        result.linkage.invalid_geometry_rows += 1
        warning_counts["invalid_operation_geometry"] += 1
        return None

    representative_point = operation_geometry.representative_point()
    covering = [field_id for field_id, geometry in candidates if geometry.covers(representative_point)]
    if len(covering) == 1:
        result.linkage.assigned_rows += 1
        return covering[0], service_order_id, service_order_number
    if len(covering) > 1:
        _append_spatial_ambiguity(result, file_name, row_number, service_order_number)
        return None

    if operation_geometry.area > 0:
        ratios = [(operation_geometry.intersection(geometry).area / operation_geometry.area, field_id)
                  for field_id, geometry in candidates]
        max_ratio = max((ratio for ratio, _ in ratios), default=0.0)
        winners = [field_id for ratio, field_id in ratios
                   if math.isclose(ratio, max_ratio, rel_tol=1e-9, abs_tol=1e-12)]
        if max_ratio >= 0.50 and len(winners) == 1:
            result.linkage.assigned_rows += 1
            return winners[0], service_order_id, service_order_number
        if max_ratio >= 0.50 and len(winners) > 1:
            _append_spatial_ambiguity(result, file_name, row_number, service_order_number)
            return None

    result.linkage.unassigned_rows += 1
    warning_counts["operation_outside_candidates"] += 1
    return None


def _append_spatial_ambiguity(
    result: OperationNormalizationResult, file_name: str, row_number: int,
    service_order_number: str,
) -> None:
    result.linkage.ambiguous_rows += 1
    result.errors.append(
        ValidationIssue(
            code="ambiguous_operation_geometry",
            message=(f"A ordem {service_order_number}, linha {row_number}, intersecta mais de um "
                     "talhão candidato sem desempate espacial seguro."),
            file=file_name,
            row=row_number,
        )
    )


def normalize_ndvi(frame: pd.DataFrame) -> NdviNormalizationResult:
    columns = ["season_id", "date", "crs", "bounds_left", "bounds_bottom",
               "bounds_right", "bounds_top", "valid_pixels", "ndvi"]
    result = NdviNormalizationResult(frame=pd.DataFrame(columns=columns))
    if _report_missing_columns(frame, NDVI_REQUIRED_COLUMNS, NDVI_FILE, result.errors):
        return result

    records: list[dict[str, Any]] = []
    invalid_pixels = 0
    unsupported_crs: set[str] = set()
    for _, row in frame.iterrows():
        try:
            filename = _required_text(row["filename"], "filename")
            season_id = _required_text(row["season_id"], "season_id")
            crs = _required_text(row["crs"], "crs").upper()
            if crs != "EPSG:3857":
                unsupported_crs.add(crs)
                raise ValueError("CRS diferente de EPSG:3857")
            date = _date_from_filename(filename)
            left = _finite_number(row["bounds_left"], "bounds_left")
            bottom = _finite_number(row["bounds_bottom"], "bounds_bottom")
            right = _finite_number(row["bounds_right"], "bounds_right")
            top = _finite_number(row["bounds_top"], "bounds_top")
            if left >= right or bottom >= top:
                raise ValueError("bounds inválidos")
            valid_pixels = _positive_integer(row["b1_valid_pixels"], "b1_valid_pixels")
            ndvi = _finite_number(row["b1_mean"], "b1_mean")
            if not -1 <= ndvi <= 1:
                raise ValueError("b1_mean fora do intervalo [-1, 1]")
        except (TypeError, ValueError):
            try:
                raw_pixels = float(row["b1_valid_pixels"])
                if not np.isfinite(raw_pixels) or raw_pixels <= 0:
                    invalid_pixels += 1
            except (TypeError, ValueError):
                invalid_pixels += 1
            result.discarded_rows += 1
            continue
        records.append({
            "season_id": season_id, "date": date, "crs": crs,
            "bounds_left": left, "bounds_bottom": bottom, "bounds_right": right,
            "bounds_top": top, "valid_pixels": valid_pixels, "ndvi": ndvi,
        })

    result.frame = pd.DataFrame.from_records(records, columns=columns)
    if invalid_pixels:
        result.warnings.append(ValidationIssue(
            code="ndvi_without_valid_pixels",
            message=f"{invalid_pixels} observação(ões) de NDVI não possuíam pixels válidos.",
            file=NDVI_FILE,
        ))
    if result.discarded_rows:
        result.warnings.append(ValidationIssue(
            code="discarded_rows",
            message=f"{result.discarded_rows} observação(ões) inválida(s) de NDVI foram descartadas.",
            file=NDVI_FILE,
        ))
    for crs in sorted(unsupported_crs):
        result.errors.append(ValidationIssue(
            code="unsupported_crs",
            message=f"CRS não suportado em {NDVI_FILE}: {crs}; esperado EPSG:3857.",
            file=NDVI_FILE,
        ))
    return result


def normalize_soil(frame: pd.DataFrame) -> SoilNormalizationResult:
    """Normalize soil samples without inventing a relationship to individual fields."""
    result = SoilNormalizationResult()
    if _report_missing_columns(frame, SOIL_REQUIRED_COLUMNS, SOIL_FILE, result.errors):
        return result

    metric_columns = [column for column in frame.columns if column != "AMOSTRA"]
    group_1_columns = [column for column in metric_columns if not column.endswith("_2")]
    group_2_columns = [column for column in metric_columns if column.endswith("_2")]
    result.measurement_groups = ["group_1"] + (["group_2"] if group_2_columns else [])

    missing_micronutrients = sorted(set(SOIL_MICRONUTRIENT_METRICS) - set(frame.columns))
    if missing_micronutrients:
        result.warnings.append(ValidationIssue(
            code="missing_soil_micronutrients",
            message=("Micronutrientes opcionais ausentes em soil_analysis.csv: "
                     f"{', '.join(missing_micronutrients)}."),
            file=SOIL_FILE,
        ))
    if not group_2_columns:
        result.warnings.append(ValidationIssue(
            code="missing_soil_group_2",
            message="O Conjunto 2 não está disponível em soil_analysis.csv.",
            file=SOIL_FILE,
        ))

    records: list[dict[str, Any]] = []
    seen_samples: set[str] = set()
    invalid_value_count = 0
    for index, row in frame.iterrows():
        row_number = int(index) + 2 if isinstance(index, int) else 2
        try:
            sample_id = _required_text(row["AMOSTRA"], "AMOSTRA")
        except ValueError as exc:
            result.errors.append(ValidationIssue(
                code="invalid_soil_sample",
                message=f"Amostra de solo inválida na linha {row_number}: {exc}.",
                file=SOIL_FILE,
                row=row_number,
            ))
            result.discarded_rows += 1
            continue
        if sample_id in seen_samples:
            result.errors.append(ValidationIssue(
                code="duplicate_soil_sample",
                message=f"AMOSTRA duplicada em soil_analysis.csv: {sample_id}.",
                file=SOIL_FILE,
                row=row_number,
            ))
            result.discarded_rows += 1
            continue
        seen_samples.add(sample_id)

        group_1, invalid_group_1 = _normalize_soil_metrics(row, group_1_columns)
        group_2, invalid_group_2 = _normalize_soil_metrics(row, group_2_columns)
        invalid_value_count += invalid_group_1 + invalid_group_2
        if not any(value is not None for value in group_1.values()):
            result.discarded_rows += 1
            continue

        texture_values = [group_1.get(metric) for metric in SOIL_TEXTURE_METRICS]
        if all(value is not None for value in texture_values):
            texture_sum = sum(texture_values)
            if not 95 <= texture_sum <= 105:
                result.warnings.append(ValidationIssue(
                    code="soil_texture_sum_out_of_range",
                    message=(f"A soma de ARGILA, SILTE e AREIA da amostra {sample_id} "
                             f"é {texture_sum:.2f}; esperado entre 95 e 105."),
                    file=SOIL_FILE,
                    row=row_number,
                ))

        records.append({
            "sample_id": sample_id,
            "scope": "dataset",
            "group_1": group_1,
            "group_2": group_2,
        })

    result.frame = pd.DataFrame.from_records(
        records, columns=["sample_id", "scope", "group_1", "group_2"]
    )
    if invalid_value_count:
        result.warnings.append(ValidationIssue(
            code="invalid_soil_values",
            message=(f"{invalid_value_count} valor(es) ausente(s) ou inválido(s) em "
                     "soil_analysis.csv foram descartados, sem substituição por zero."),
            file=SOIL_FILE,
        ))
    if not result.frame.empty:
        result.warnings.append(ValidationIssue(
            code="soil_units_undocumented",
            message=("As unidades e faixas agronômicas de soil_analysis.csv não estão "
                     "documentadas; os valores serão apresentados sem classificação."),
            file=SOIL_FILE,
        ))
    else:
        result.errors.append(ValidationIssue(
            code="no_valid_soil_samples",
            message="Nenhuma amostra de solo válida foi reconhecida.",
            file=SOIL_FILE,
        ))
    return result


def _normalize_soil_metrics(
    row: pd.Series, columns: list[str],
) -> tuple[dict[str, float | None], int]:
    values: dict[str, float | None] = {}
    invalid_count = 0
    for column in columns:
        metric = column[:-2] if column.endswith("_2") else column
        raw_value = row[column]
        try:
            if pd.isna(raw_value) or not str(raw_value).strip():
                raise ValueError(f"{column} está vazio")
            normalized = str(raw_value).strip().replace(",", ".")
            value = _finite_number(normalized, column)
            if metric in SOIL_TEXTURE_METRICS and not 0 <= value <= 100:
                raise ValueError(f"{column} deve estar entre 0 e 100")
            if metric == "PHCACL2" and not 0 <= value <= 14:
                raise ValueError(f"{column} deve estar entre 0 e 14")
            if metric not in SOIL_TEXTURE_METRICS and metric != "PHCACL2" and value < 0:
                raise ValueError(f"{column} não pode ser negativo")
        except (TypeError, ValueError):
            value = None
            invalid_count += 1
        values[metric] = value
    return values, invalid_count


def _required_text(value: Any, column: str) -> str:
    if pd.isna(value):
        raise ValueError(f"{column} está vazio")
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{column} está vazio")
    return normalized


def _canonical_service_order_number(value: Any) -> str:
    text = _required_text(value, "Service Order")
    try:
        number = Decimal(text)
    except InvalidOperation:
        return text
    if not number.is_finite():
        raise ValueError("Service Order não é finita")
    if number == 0:
        return "0"
    return format(number.normalize(), "f")


def _finite_number(value: Any, column: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{column} não é numérico") from exc
    if not np.isfinite(number):
        raise ValueError(f"{column} não é finito")
    return number


def _positive_integer(value: Any, column: str) -> int:
    number = _finite_number(value, column)
    if number <= 0 or not number.is_integer():
        raise ValueError(f"{column} deve ser inteiro positivo")
    return int(number)


def _date_from_filename(filename: str):
    match = re.search(r"(\d{4}-\d{2}-\d{2})(?:\.[^.]+)?$", filename)
    if not match:
        raise ValueError("filename não termina com data YYYY-MM-DD")
    parsed = pd.to_datetime(match.group(1), format="%Y-%m-%d", errors="coerce")
    if pd.isna(parsed):
        raise ValueError("data inválida no filename")
    return parsed.date()


def _operation_date(date_time: Any, timestamp: Any) -> pd.Timestamp:
    parsed = pd.to_datetime(date_time, errors="coerce", utc=True, format="mixed", dayfirst=True)
    if not pd.isna(parsed):
        return parsed
    unix_value = _finite_number(timestamp, "Timestamp")
    unit = "ms" if abs(unix_value) >= 100_000_000_000 else "s"
    parsed = pd.to_datetime(unix_value, unit=unit, errors="coerce", utc=True)
    if pd.isna(parsed):
        raise ValueError("data operacional inválida")
    return parsed


def _report_missing_columns(
    frame: pd.DataFrame, required: set[str], file_name: str,
    errors: list[ValidationIssue],
) -> bool:
    missing = sorted(required - set(frame.columns))
    errors.extend(ValidationIssue(
        code="missing_column",
        message=f"Coluna obrigatória ausente em {file_name}: {column}.",
        file=file_name,
    ) for column in missing)
    return bool(missing)


def _append_linkage_warnings(
    result: OperationNormalizationResult, file_name: str, counts: Counter[str],
) -> None:
    messages = {
        "unmatched_service_order": "linha(s) não encontraram uma ordem de serviço cadastrada",
        "service_order_without_fields": "linha(s) pertencem a ordens sem talhões candidatos",
        "operation_outside_candidates": "linha(s) ficaram fora dos talhões candidatos",
        "invalid_operation_geometry": "linha(s) possuíam geometria inválida",
    }
    for code, message in messages.items():
        if counts[code]:
            result.warnings.append(ValidationIssue(
                code=code, message=f"{counts[code]} {message} e foram descartadas.", file=file_name,
            ))


def _append_discard_warning(result: OperationNormalizationResult, file_name: str) -> None:
    if result.discarded_rows:
        result.warnings.append(ValidationIssue(
            code="discarded_rows",
            message=f"{result.discarded_rows} linha(s) inválida(s) foram descartadas.",
            file=file_name,
        ))


def _parse_centroid(value: Any) -> Centroid:
    if isinstance(value, str):
        parsed = json.loads(value)
    elif isinstance(value, dict):
        parsed = value
    else:
        raise ValueError("fieldAreaCentroid deve ser um objeto JSON")
    if not isinstance(parsed, dict):
        raise ValueError("fieldAreaCentroid deve ser um objeto JSON")
    try:
        longitude = float(parsed["longitude"])
        latitude = float(parsed["latitude"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("centroide exige longitude e latitude numéricas") from exc
    return Centroid(longitude=longitude, latitude=latitude)


def _parse_field_geometry(value: Any) -> BaseGeometry:
    geometry = _load_geometry(value, "fieldGeom")
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise ValueError("fieldGeom deve ser POLYGON ou MULTIPOLYGON")
    return geometry


def _parse_operation_geometry(value: Any) -> BaseGeometry:
    return _load_geometry(value, "geometry")


def _load_geometry(value: Any, column: str) -> BaseGeometry:
    text = _required_text(value, column)
    try:
        geometry = wkt.loads(text)
    except (GEOSException, TypeError, ValueError) as exc:
        raise ValueError(f"{column} não contém WKT válido") from exc
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError(f"{column} contém geometria vazia ou inválida")
    return geometry


def _normalize_field_name(name: str) -> str:
    normalized = unicodedata.normalize("NFC", name).strip()
    return re.sub(r"\bconvecional\b", "Convencional", normalized, flags=re.IGNORECASE)


def _derive_label(name: str) -> str:
    label = re.sub(r"\s+-\s+\d+(?:[.,]\d+)?\s*ha\s*$", "", name, flags=re.IGNORECASE).strip()
    return label or name.strip()


def _derive_purpose(name: str) -> FieldPurpose:
    normalized = name.casefold()
    if "grão" in normalized:
        return FieldPurpose.GRAIN
    if "silagem" in normalized:
        return FieldPurpose.SILAGE
    return FieldPurpose.UNKNOWN


def _derive_management(name: str) -> FieldManagement:
    normalized = name.casefold()
    if "4.0" in normalized:
        return FieldManagement.DIGITAL
    if "convencional" in normalized:
        return FieldManagement.CONVENTIONAL
    return FieldManagement.UNKNOWN
