import math

import pandas as pd
import pytest

from app.data.contracts import Centroid, FieldManagement, FieldPurpose, FieldRecord
from app.data.linker import (
    EARTH_RADIUS_METERS,
    build_service_order_catalog,
    build_service_order_mapping,
    haversine_distance_m,
    link_ndvi_seasons,
    web_mercator_to_wgs84,
)
from tests.test_normalizer import demonstration_fields_frame
from app.data.normalizer import normalize_fields


def normalized_fields():
    return normalize_fields(demonstration_fields_frame()).fields


def test_service_orders_are_resolved_to_known_fields() -> None:
    frame = pd.DataFrame(
        {
            "idField": ["103144", "103145", "103144"],
            "idServiceOrder": ["SO-1", "SO-2", "SO-1"],
            "fieldName": ["Grão 4.0", "Grão Convencional", "Grão 4.0"],
        }
    )

    result = build_service_order_mapping(frame, normalized_fields())

    assert result.errors == []
    assert result.mapping == {"SO-1": {"103144"}, "SO-2": {"103145"}}


def test_service_order_linked_to_two_fields_is_valid_candidate_set() -> None:
    frame = pd.DataFrame(
        {
            "idField": ["103144", "103145"],
            "idServiceOrder": ["SO-1", "SO-1"],
            "fieldName": ["Grão 4.0", "Grão Convencional"],
        }
    )

    result = build_service_order_mapping(frame, normalized_fields())

    assert result.mapping == {"SO-1": {"103144", "103145"}}
    assert result.errors == []


def test_service_order_catalog_canonicalizes_numbers() -> None:
    frame = pd.DataFrame({
        "idServiceOrder": ["SO-1", "SO-2"],
        "serviceOrderNumber": [" 1.0 ", "2"],
        "idAgriculturalOperation_agriculturalOperationName": ["PLANTIO", "CALAGEM"],
    })

    result = build_service_order_catalog(frame)

    assert result.errors == []
    assert result.number_to_id == {"1": "SO-1", "2": "SO-2"}
    assert result.operation_by_id == {"SO-1": "PLANTIO", "SO-2": "CALAGEM"}


def test_service_order_catalog_rejects_number_for_different_ids() -> None:
    frame = pd.DataFrame({
        "idServiceOrder": ["SO-1", "SO-2"],
        "serviceOrderNumber": ["1", "1.0"],
        "idAgriculturalOperation_agriculturalOperationName": ["PLANTIO", "PLANTIO"],
    })

    result = build_service_order_catalog(frame)

    assert "1" not in result.number_to_id
    assert result.errors[0].code == "ambiguous_service_order_number"


def test_service_order_rejects_unknown_field() -> None:
    frame = pd.DataFrame(
        {
            "idField": ["999999"],
            "idServiceOrder": ["SO-X"],
            "fieldName": ["Desconhecido"],
        }
    )

    result = build_service_order_mapping(frame, normalized_fields())

    assert result.mapping == {}
    assert result.errors[0].code == "unknown_field"


def test_service_orders_report_missing_columns() -> None:
    result = build_service_order_mapping(pd.DataFrame({"idField": ["103144"]}), normalized_fields())

    assert {issue.code for issue in result.errors} == {"missing_column"}


def field(field_id: str, longitude: float, latitude: float) -> FieldRecord:
    return FieldRecord(
        field_id=field_id,
        farm_id="F-1",
        name=f"Grão 4.0 {field_id}",
        label=f"Grão 4.0 {field_id}",
        purpose=FieldPurpose.GRAIN,
        management=FieldManagement.DIGITAL,
        centroid=Centroid(longitude=longitude, latitude=latitude),
        geometry_available=True,
    )


def mercator(longitude: float, latitude: float) -> tuple[float, float]:
    x = EARTH_RADIUS_METERS * math.radians(longitude)
    y = EARTH_RADIUS_METERS * math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2))
    return x, y


def ndvi_rows(points: list[tuple[str, float, float]]) -> pd.DataFrame:
    records = []
    for season_id, longitude, latitude in points:
        x, y = mercator(longitude, latitude)
        records.append(
            {
                "season_id": season_id,
                "date": pd.Timestamp("2025-01-01").date(),
                "crs": "EPSG:3857",
                "bounds_left": x - 50,
                "bounds_bottom": y - 50,
                "bounds_right": x + 50,
                "bounds_top": y + 50,
                "valid_pixels": 100,
                "ndvi": 0.5,
            }
        )
    return pd.DataFrame(records)


def test_projection_and_haversine_have_expected_regression_values() -> None:
    x, y = mercator(-49.98, -22.24)
    longitude, latitude = web_mercator_to_wgs84(x, y)

    assert longitude == pytest.approx(-49.98, abs=1e-9)
    assert latitude == pytest.approx(-22.24, abs=1e-9)
    assert haversine_distance_m(-49.98, -22.24, -49.98, -22.24) == pytest.approx(0.0)


def test_all_demo_series_link_to_correct_nearest_field() -> None:
    fields = [
        field("F-1", -49.98, -22.24),
        field("F-2", -49.96, -22.24),
        field("F-3", -49.94, -22.24),
        field("F-4", -49.92, -22.24),
    ]
    frame = ndvi_rows(
        [
            ("S-1", -49.98, -22.24),
            ("S-2", -49.96, -22.24),
            ("S-3", -49.94, -22.24),
            ("S-4", -49.92, -22.24),
        ]
    )

    result = link_ndvi_seasons(frame, fields)

    assert result.errors == []
    assert result.mapping == {"S-1": "F-1", "S-2": "F-2", "S-3": "F-3", "S-4": "F-4"}
    assert all(link.rule == "nearest_centroid_within_1000m" for link in result.links)


def test_duplicate_dates_are_aggregated_by_valid_pixels() -> None:
    fields = [field("F-1", -49.98, -22.24)]
    frame = pd.concat(
        [
            ndvi_rows([("S-1", -49.98, -22.24)]),
            ndvi_rows([("S-1", -49.98, -22.24)]),
        ],
        ignore_index=True,
    )
    frame.loc[0, ["valid_pixels", "ndvi"]] = [100, 0.4]
    frame.loc[1, ["valid_pixels", "ndvi"]] = [300, 0.8]

    result = link_ndvi_seasons(frame, fields)

    assert len(result.frame) == 1
    assert result.frame.loc[0, "valid_pixels"] == 400
    assert result.frame.loc[0, "ndvi"] == pytest.approx(0.7)


def test_linking_rejects_distance_and_duplicate_field_assignment() -> None:
    fields = [field("F-1", -49.98, -22.24)]
    far = link_ndvi_seasons(ndvi_rows([("S-FAR", -49.90, -22.24)]), fields)
    duplicate = link_ndvi_seasons(
        ndvi_rows([("S-1", -49.98, -22.24), ("S-2", -49.979, -22.24)]),
        fields,
    )

    assert {issue.code for issue in far.errors} == {"unsafe_season_link", "no_linked_ndvi_series"}
    assert {issue.code for issue in duplicate.errors} == {
        "duplicate_season_link",
        "no_linked_ndvi_series",
    }
