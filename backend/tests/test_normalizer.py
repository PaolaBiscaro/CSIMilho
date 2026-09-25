import json

import pandas as pd
from shapely import wkt

from app.data.contracts import FieldManagement, FieldPurpose
from app.data.normalizer import normalize_fertilization, normalize_fields, normalize_ndvi, normalize_planting


def demonstration_fields_frame() -> pd.DataFrame:
    names = [
        "Grão 4.0 - 19,3 ha",
        "Grão Convencional - 20 ha",
        "Silagem 4.0 - 14,7 ha",
        "Silagem Convencional - 15 ha",
    ]
    return pd.DataFrame(
        {
            "idField": [103144, 103145, 103146, 103147],
            "idFarm": [25213] * 4,
            "fieldName": names,
            "fieldAreaCentroid": [
                json.dumps({"longitude": -49.980 + index * 0.002, "latitude": -22.240})
                for index in range(4)
            ],
            "fieldGeom": [
                f"POLYGON (({-49.985 + index * 0.002} -22.245, "
                f"{-49.975 + index * 0.002} -22.245, "
                f"{-49.975 + index * 0.002} -22.235, "
                f"{-49.985 + index * 0.002} -22.235, "
                f"{-49.985 + index * 0.002} -22.245))"
                for index in range(4)
            ],
        }
    )


def test_normalize_fields_recognizes_four_demonstration_fields() -> None:
    result = normalize_fields(demonstration_fields_frame())

    assert result.errors == []
    assert [field.field_id for field in result.fields] == ["103144", "103145", "103146", "103147"]
    assert [field.label for field in result.fields] == [
        "Grão 4.0",
        "Grão Convencional",
        "Silagem 4.0",
        "Silagem Convencional",
    ]
    assert [field.purpose for field in result.fields] == [
        FieldPurpose.GRAIN,
        FieldPurpose.GRAIN,
        FieldPurpose.SILAGE,
        FieldPurpose.SILAGE,
    ]
    assert [field.management for field in result.fields] == [
        FieldManagement.DIGITAL,
        FieldManagement.CONVENTIONAL,
        FieldManagement.DIGITAL,
        FieldManagement.CONVENTIONAL,
    ]
    assert all(field.geometry_available for field in result.fields)


def test_normalize_fields_corrects_known_alias_for_classification() -> None:
    frame = demonstration_fields_frame().iloc[:2].copy()
    frame.loc[1, "fieldName"] = "  Grão Convecional - 20 ha  "

    result = normalize_fields(frame)

    field = result.fields[1]
    assert field.name == "Grão Convecional - 20 ha"
    assert field.label == "Grão Convencional"
    assert field.management is FieldManagement.CONVENTIONAL
    assert [warning.code for warning in result.warnings] == ["field_name_normalized"]


def test_normalize_fields_reports_missing_columns() -> None:
    result = normalize_fields(demonstration_fields_frame().drop(columns=["fieldAreaCentroid"]))

    assert result.fields == []
    assert result.errors[0].code == "missing_column"
    assert "fieldAreaCentroid" in result.errors[0].message


def test_normalize_fields_reports_duplicate_id_and_invalid_centroid() -> None:
    frame = demonstration_fields_frame().iloc[:2].copy()
    frame.loc[1, "idField"] = frame.loc[0, "idField"]
    frame.loc[0, "fieldAreaCentroid"] = "not-json"

    result = normalize_fields(frame)

    assert result.fields == []
    assert len(result.errors) == 3
    assert all(issue.code in {"invalid_field", "no_fields"} for issue in result.errors)


def test_normalize_fields_uses_unknown_without_guessing() -> None:
    frame = demonstration_fields_frame().iloc[:1].copy()
    frame.loc[0, "fieldName"] = "Área experimental"

    result = normalize_fields(frame)

    assert result.fields[0].purpose is FieldPurpose.UNKNOWN
    assert result.fields[0].management is FieldManagement.UNKNOWN


def test_normalize_planting_links_rows_and_discards_invalid_values() -> None:
    frame = pd.DataFrame(
        {
            "Timestamp": [1735689600, 1735776000, 1735862400],
            "geometry": ["POINT (-49.98 -22.24)"] * 3,
            "Date Time": ["2025-01-01T10:00:00Z", "invalid", "2025-01-03T10:00:00Z"],
            "Service Order": ["1", "1.0", "999"],
            "Operation": ["Plantio", "Plantio", "Plantio"],
            "Area - ha": [2.0, -1.0, 1.0],
            "Population - ha": [60000, 62000, 61000],
        }
    )

    fields = normalize_fields(demonstration_fields_frame())
    result = normalize_planting(
        frame, {"1": "SO-1"}, {"SO-1": {"103144"}}, fields.geometries,
    )

    assert len(result.frame) == 1
    assert result.frame.loc[0, "field_id"] == "103144"
    assert result.frame.loc[0, "operation"] == "PLANTIO"
    assert result.discarded_rows == 2
    assert {warning.code for warning in result.warnings} == {"unmatched_service_order", "discarded_rows"}
    assert result.linkage.assigned_rows == 2
    assert result.linkage.unassigned_rows == 1


def test_normalize_planting_uses_timestamp_as_date_fallback() -> None:
    frame = pd.DataFrame(
        {
            "Timestamp": [1735689600],
            "geometry": ["POINT (-49.98 -22.24)"],
            "Date Time": ["invalid"],
            "Service Order": ["1.0"],
            "Operation": ["Plantio"],
            "Area - ha": [1.0],
            "Population - ha": [60000],
        }
    )

    fields = normalize_fields(demonstration_fields_frame())
    result = normalize_planting(
        frame, {"1": "SO-1"}, {"SO-1": {"103144"}}, fields.geometries,
    )

    assert str(result.frame.loc[0, "operation_date"].date()) == "2025-01-01"


def test_normalize_fertilization_normalizes_operation_and_rules() -> None:
    frame = pd.DataFrame(
        {
            "Timestamp": [1735689600, 1735776000, 1735862400, 1735948800],
            "geometry": ["POINT (-49.98 -22.24)"] * 4,
            "Date Time": ["2025-01-01"] * 4,
            "Service Order": ["1"] * 4,
            "operation": [" calagem ", "CALAGEM", "CALAGEM", "CALAGEM"],
            "Area - ha": [2.0, 0.0, 1.0, 1.0],
            "AppliedDos - kg/ha": [100.0, 100.0, -1.0, 100.0],
            "Configured - kg/ha": [200.0, 200.0, 200.0, 0.0],
        }
    )

    fields = normalize_fields(demonstration_fields_frame())
    result = normalize_fertilization(
        frame, {"1": "SO-1"}, {"SO-1": {"103144"}}, fields.geometries,
    )

    assert len(result.frame) == 1
    assert result.frame.loc[0, "operation"] == "CALAGEM"
    assert result.discarded_rows == 3


def test_operation_normalizers_report_missing_columns() -> None:
    planting = normalize_planting(pd.DataFrame({"Timestamp": [1]}), {}, {}, {})
    fertilization = normalize_fertilization(pd.DataFrame({"Timestamp": [1]}), {}, {}, {})

    assert planting.frame.empty and planting.errors
    assert fertilization.frame.empty and fertilization.errors
    assert all(issue.code == "missing_column" for issue in planting.errors + fertilization.errors)


def planting_row(geometry: str) -> pd.DataFrame:
    return pd.DataFrame({
        "geometry": [geometry],
        "Timestamp": [1735689600],
        "Date Time": ["2025-01-01T10:00:00Z"],
        "Service Order": ["1"],
        "Operation": ["MILHO"],
        "Area - ha": [1.0],
        "Population - ha": [60000],
    })


def test_operation_uses_representative_point_with_shared_order() -> None:
    geometries = {
        "A": wkt.loads("POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0))"),
        "B": wkt.loads("POLYGON ((5 0, 9 0, 9 4, 5 4, 5 0))"),
    }
    result = normalize_planting(
        planting_row("POLYGON ((5.5 1, 6.5 1, 6.5 2, 5.5 2, 5.5 1))"),
        {"1": "SO-1"}, {"SO-1": {"A", "B"}}, geometries,
    )

    assert result.frame.loc[0, "field_id"] == "B"
    assert result.linkage.assigned_rows == 1


def test_operation_uses_intersection_fallback_at_half_or_more() -> None:
    geometry = (
        "MULTIPOLYGON (((20 0, 24 0, 24 1, 20 1, 20 0)), "
        "((0 0, 3 0, 3 1, 0 1, 0 0)), ((4 0, 7 0, 7 1, 4 1, 4 0)))"
    )
    result = normalize_planting(
        planting_row(geometry), {"1": "SO-1"}, {"SO-1": {"A"}},
        {"A": wkt.loads("POLYGON ((-1 -1, 10 -1, 10 2, -1 2, -1 -1))")},
    )

    assert result.frame.loc[0, "field_id"] == "A"
    assert result.linkage.assigned_rows == 1


def test_operation_outside_candidates_is_discarded_with_warning() -> None:
    result = normalize_planting(
        planting_row("POINT (20 20)"), {"1": "SO-1"}, {"SO-1": {"A"}},
        {"A": wkt.loads("POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0))")},
    )

    assert result.frame.empty
    assert result.linkage.unassigned_rows == 1
    assert "operation_outside_candidates" in {warning.code for warning in result.warnings}


def test_operation_spatial_tie_is_blocking() -> None:
    shared = wkt.loads("POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0))")
    result = normalize_planting(
        planting_row("POINT (2 2)"), {"1": "SO-1"}, {"SO-1": {"A", "B"}},
        {"A": shared, "B": shared},
    )

    assert result.frame.empty
    assert result.linkage.ambiguous_rows == 1
    assert result.errors[0].code == "ambiguous_operation_geometry"


def ndvi_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "filename": ["ndvi_2025-01-01.tif", "ndvi_2025-01-08.tif", "ndvi_2025-01-15.tif"],
            "season_id": ["S-1", "S-1", "S-1"],
            "crs": ["EPSG:3857"] * 3,
            "bounds_left": [-5_563_100.0] * 3,
            "bounds_bottom": [-2_539_100.0] * 3,
            "bounds_right": [-5_562_900.0] * 3,
            "bounds_top": [-2_538_900.0] * 3,
            "b1_valid_pixels": [100, 0, 100],
            "b1_mean": [0.52, 0.48, None],
        }
    )


def test_normalize_ndvi_preserves_valid_observations_without_interpolation() -> None:
    result = normalize_ndvi(ndvi_frame())

    assert result.errors == []
    assert len(result.frame) == 1
    assert str(result.frame.loc[0, "date"]) == "2025-01-01"
    assert result.frame.loc[0, "ndvi"] == 0.52
    assert result.discarded_rows == 2
    assert {warning.code for warning in result.warnings} == {
        "ndvi_without_valid_pixels",
        "discarded_rows",
    }


def test_normalize_ndvi_rejects_out_of_range_value_and_invalid_date() -> None:
    frame = ndvi_frame().iloc[:2].copy()
    frame.loc[0, "b1_mean"] = 1.2
    frame.loc[1, "b1_valid_pixels"] = 100
    frame.loc[1, "filename"] = "ndvi_without_date.tif"

    result = normalize_ndvi(frame)

    assert result.frame.empty
    assert result.discarded_rows == 2


def test_normalize_ndvi_reports_unsupported_crs_and_missing_columns() -> None:
    frame = ndvi_frame().iloc[:1].copy()
    frame.loc[0, "crs"] = "EPSG:4326"
    unsupported = normalize_ndvi(frame)
    missing = normalize_ndvi(frame.drop(columns=["b1_mean"]))

    assert unsupported.errors[0].code == "unsupported_crs"
    assert unsupported.frame.empty
    assert missing.errors[0].code == "missing_column"
