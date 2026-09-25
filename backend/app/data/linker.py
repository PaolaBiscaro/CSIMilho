from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from app.data.contracts import FieldRecord, ValidationIssue
from app.data.normalizer import _canonical_service_order_number, _required_text

SERVICE_ORDER_CATALOG_FILE = "service_orders.csv"
SERVICE_ORDER_CATALOG_REQUIRED_COLUMNS = {
    "idServiceOrder",
    "serviceOrderNumber",
    "idAgriculturalOperation_agriculturalOperationName",
}
SERVICE_ORDER_FIELDS_FILE = "service_orders_fields.csv"
SERVICE_ORDER_FIELDS_REQUIRED_COLUMNS = {"idField", "idServiceOrder", "fieldName"}
EARTH_RADIUS_METERS = 6_378_137.0


@dataclass
class ServiceOrderCatalogResult:
    number_to_id: dict[str, str] = field(default_factory=dict)
    operation_by_id: dict[str, str] = field(default_factory=dict)
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)


@dataclass
class ServiceOrderMappingResult:
    mapping: dict[str, set[str]] = field(default_factory=dict)
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)


@dataclass(frozen=True)
class SeasonFieldLink:
    season_id: str
    field_id: str
    distance_m: float
    rule: str = "nearest_centroid_within_1000m"


@dataclass
class SeasonLinkResult:
    frame: pd.DataFrame = field(
        default_factory=lambda: pd.DataFrame(
            columns=["field_id", "season_id", "date", "ndvi", "valid_pixels", "link_distance_m"]
        )
    )
    mapping: dict[str, str] = field(default_factory=dict)
    links: list[SeasonFieldLink] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)


def build_service_order_catalog(frame: pd.DataFrame) -> ServiceOrderCatalogResult:
    result = ServiceOrderCatalogResult()
    missing = sorted(SERVICE_ORDER_CATALOG_REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        result.errors.extend(
            ValidationIssue(
                code="missing_column",
                message=f"Coluna obrigatória ausente em {SERVICE_ORDER_CATALOG_FILE}: {column}.",
                file=SERVICE_ORDER_CATALOG_FILE,
            )
            for column in missing
        )
        return result

    seen_ids: set[str] = set()
    conflicted_numbers: set[str] = set()
    for index, row in frame.iterrows():
        row_number = int(index) + 2 if isinstance(index, int) else 2
        try:
            service_order_id = _required_text(row["idServiceOrder"], "idServiceOrder")
            service_order_number = _canonical_service_order_number(row["serviceOrderNumber"])
            operation = _required_text(
                row["idAgriculturalOperation_agriculturalOperationName"],
                "idAgriculturalOperation_agriculturalOperationName",
            )
        except ValueError as exc:
            result.errors.append(
                ValidationIssue(
                    code="invalid_service_order",
                    message=f"Ordem de serviço inválida na linha {row_number}: {exc}",
                    file=SERVICE_ORDER_CATALOG_FILE,
                    row=row_number,
                )
            )
            continue

        if service_order_id in seen_ids:
            result.errors.append(
                ValidationIssue(
                    code="duplicate_service_order_id",
                    message=f"idServiceOrder duplicado: {service_order_id}.",
                    file=SERVICE_ORDER_CATALOG_FILE,
                    row=row_number,
                )
            )
            continue
        seen_ids.add(service_order_id)
        result.operation_by_id[service_order_id] = operation

        previous = result.number_to_id.get(service_order_number)
        if previous is not None and previous != service_order_id:
            result.errors.append(
                ValidationIssue(
                    code="ambiguous_service_order_number",
                    message=(
                        f"O número de ordem {service_order_number} aponta para IDs diferentes "
                        f"({previous} e {service_order_id})."
                    ),
                    file=SERVICE_ORDER_CATALOG_FILE,
                    row=row_number,
                )
            )
            conflicted_numbers.add(service_order_number)
            result.number_to_id.pop(service_order_number, None)
            continue

        if service_order_number not in conflicted_numbers:
            result.number_to_id[service_order_number] = service_order_id

    return result


def build_service_order_mapping(
    frame: pd.DataFrame,
    fields: list[FieldRecord],
) -> ServiceOrderMappingResult:
    result = ServiceOrderMappingResult()
    missing = sorted(SERVICE_ORDER_FIELDS_REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        result.errors.extend(
            ValidationIssue(
                code="missing_column",
                message=f"Coluna obrigatória ausente em {SERVICE_ORDER_FIELDS_FILE}: {column}.",
                file=SERVICE_ORDER_FIELDS_FILE,
            )
            for column in missing
        )
        return result

    valid_field_ids = {item.field_id for item in fields}
    for index, row in frame.iterrows():
        row_number = int(index) + 2 if isinstance(index, int) else 2
        try:
            field_id = _required_text(row["idField"], "idField")
            service_order_id = _required_text(row["idServiceOrder"], "idServiceOrder")
            _required_text(row["fieldName"], "fieldName")
        except ValueError as exc:
            result.errors.append(
                ValidationIssue(
                    code="invalid_service_order",
                    message=f"Vínculo de ordem inválido na linha {row_number}: {exc}",
                    file=SERVICE_ORDER_FIELDS_FILE,
                    row=row_number,
                )
            )
            continue

        if field_id not in valid_field_ids:
            result.errors.append(
                ValidationIssue(
                    code="unknown_field",
                    message=f"A ordem {service_order_id} referencia o talhão inexistente {field_id}.",
                    file=SERVICE_ORDER_FIELDS_FILE,
                    row=row_number,
                )
            )
            continue

        result.mapping.setdefault(service_order_id, set()).add(field_id)

    return result


def web_mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    longitude = (x / EARTH_RADIUS_METERS) * 180 / math.pi
    latitude = (2 * math.atan(math.exp(y / EARTH_RADIUS_METERS)) - math.pi / 2) * 180 / math.pi
    return longitude, latitude


def haversine_distance_m(
    longitude_a: float,
    latitude_a: float,
    longitude_b: float,
    latitude_b: float,
) -> float:
    lon_a, lat_a, lon_b, lat_b = map(
        math.radians,
        (longitude_a, latitude_a, longitude_b, latitude_b),
    )
    delta_lon = lon_b - lon_a
    delta_lat = lat_b - lat_a
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(value))


def link_ndvi_seasons(
    frame: pd.DataFrame,
    fields: list[FieldRecord],
    max_distance_m: float = 1_000.0,
    warning_distance_m: float = 500.0,
) -> SeasonLinkResult:
    result = SeasonLinkResult()
    candidates: list[SeasonFieldLink] = []

    for season_id, group in frame.groupby("season_id", sort=True):
        center_x = ((group["bounds_left"] + group["bounds_right"]) / 2).mean()
        center_y = ((group["bounds_bottom"] + group["bounds_top"]) / 2).mean()
        longitude, latitude = web_mercator_to_wgs84(float(center_x), float(center_y))
        distances = sorted(
            (
                haversine_distance_m(
                    longitude,
                    latitude,
                    item.centroid.longitude,
                    item.centroid.latitude,
                ),
                item.field_id,
            )
            for item in fields
        )
        if not distances or distances[0][0] > max_distance_m:
            result.errors.append(
                ValidationIssue(
                    code="unsafe_season_link",
                    message=f"A série {season_id} não possui talhão a até {max_distance_m:.0f} m.",
                    file="ndvi_metadata.csv",
                )
            )
            continue
        if len(distances) > 1 and abs(distances[1][0] - distances[0][0]) <= 1.0:
            result.errors.append(
                ValidationIssue(
                    code="ambiguous_season_link",
                    message=f"A série {season_id} está equidistante de mais de um talhão.",
                    file="ndvi_metadata.csv",
                )
            )
            continue

        distance, field_id = distances[0]
        candidates.append(
            SeasonFieldLink(
                season_id=str(season_id),
                field_id=field_id,
                distance_m=round(distance, 3),
            )
        )

    by_field: dict[str, list[SeasonFieldLink]] = {}
    for link in candidates:
        by_field.setdefault(link.field_id, []).append(link)

    for field_id, links in by_field.items():
        if len(links) > 1:
            seasons = ", ".join(link.season_id for link in links)
            result.errors.append(
                ValidationIssue(
                    code="duplicate_season_link",
                    message=f"As séries {seasons} foram ligadas ao mesmo talhão {field_id}.",
                    file="ndvi_metadata.csv",
                )
            )
            continue
        link = links[0]
        result.links.append(link)
        result.mapping[link.season_id] = link.field_id
        if link.distance_m > warning_distance_m:
            result.warnings.append(
                ValidationIssue(
                    code="distant_season_link",
                    message=(
                        f"A série {link.season_id} foi ligada ao talhão {link.field_id} "
                        f"a {link.distance_m:.1f} m."
                    ),
                    file="ndvi_metadata.csv",
                )
            )

    if not result.mapping:
        result.errors.append(
            ValidationIssue(
                code="no_linked_ndvi_series",
                message="Nenhuma série de NDVI pôde ser ligada com segurança a um talhão.",
                file="ndvi_metadata.csv",
            )
        )
        return result

    linked = frame[frame["season_id"].isin(result.mapping)].copy()
    linked["field_id"] = linked["season_id"].map(result.mapping)
    distance_by_season = {link.season_id: link.distance_m for link in result.links}
    linked["link_distance_m"] = linked["season_id"].map(distance_by_season)
    linked["weighted_ndvi"] = linked["ndvi"] * linked["valid_pixels"]

    records: list[dict] = []
    for (field_id, date), group in linked.groupby(["field_id", "date"], sort=True):
        valid_pixels = int(group["valid_pixels"].sum())
        records.append(
            {
                "field_id": field_id,
                "season_id": str(group.iloc[0]["season_id"]),
                "date": date,
                "ndvi": float(group["weighted_ndvi"].sum() / valid_pixels),
                "valid_pixels": valid_pixels,
                "link_distance_m": float(group.iloc[0]["link_distance_m"]),
            }
        )
    result.frame = pd.DataFrame.from_records(
        records,
        columns=["field_id", "season_id", "date", "ndvi", "valid_pixels", "link_distance_m"],
    )
    return result
