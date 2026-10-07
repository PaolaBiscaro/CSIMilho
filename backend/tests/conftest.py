import csv
import io
import json
import math

import pytest

from app.data.linker import EARTH_RADIUS_METERS


def csv_bytes(fieldnames: list[str], rows: list[dict], delimiter: str = ",") -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def mercator(longitude: float, latitude: float) -> tuple[float, float]:
    x = EARTH_RADIUS_METERS * math.radians(longitude)
    y = EARTH_RADIUS_METERS * math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2))
    return x, y


@pytest.fixture
def presentation_package() -> dict[str, bytes]:
    field_specs = [
        ("103144", "Grão 4.0 - 19,3 ha", -49.98, -22.24, "SO-1", "1", "S-1"),
        ("103145", "Grão Convecional - 20 ha", -49.96, -22.24, "SO-1", "1", "S-2"),
        ("103146", "Silagem 4.0 - 14,7 ha", -49.94, -22.24, "SO-2", "2", "S-3"),
        ("103147", "Silagem Convencional - 15 ha", -49.92, -22.24, "SO-2", "2", "S-4"),
    ]
    fields = csv_bytes(
        ["idField", "idFarm", "fieldName", "fieldAreaCentroid", "fieldGeom"],
        [
            {
                "idField": field_id,
                "idFarm": "25213",
                "fieldName": name,
                "fieldAreaCentroid": json.dumps({"longitude": longitude, "latitude": latitude}),
                "fieldGeom": (
                    f"POLYGON (({longitude - 0.005} {latitude - 0.005}, "
                    f"{longitude + 0.005} {latitude - 0.005}, "
                    f"{longitude + 0.005} {latitude + 0.005}, "
                    f"{longitude - 0.005} {latitude + 0.005}, "
                    f"{longitude - 0.005} {latitude - 0.005}))"
                ),
            }
            for field_id, name, longitude, latitude, _, _, _ in field_specs
        ],
    )
    service_order_catalog = csv_bytes(
        ["idServiceOrder", "serviceOrderNumber", "idAgriculturalOperation_agriculturalOperationName"],
        [
            {"idServiceOrder": "SO-1", "serviceOrderNumber": "1.0", "idAgriculturalOperation_agriculturalOperationName": "PLANTIO"},
            {"idServiceOrder": "SO-2", "serviceOrderNumber": "2", "idAgriculturalOperation_agriculturalOperationName": "PLANTIO"},
        ],
    )
    service_order_fields = csv_bytes(
        ["idField", "idServiceOrder", "fieldName"],
        [
            {"idField": field_id, "idServiceOrder": order, "fieldName": name}
            for field_id, name, _, _, order, _, _ in field_specs
        ],
    )
    planting = csv_bytes(
        ["geometry", "Timestamp", "Date Time", "Service Order", "Operation", "Area - ha", "Population - ha"],
        [
            {
                "geometry": f"POINT ({longitude} {latitude})",
                "Timestamp": "1735689600",
                "Date Time": "2025-01-01T10:00:00Z",
                "Service Order": order_number,
                "Operation": "MILHO",
                "Area - ha": "1.0",
                "Population - ha": "60000",
            }
            for _, _, longitude, latitude, _, order_number, _ in field_specs
        ],
    )
    fertilization = csv_bytes(
        [
            "Timestamp",
            "geometry",
            "Date Time",
            "Service Order",
            "operation",
            "Area - ha",
            "AppliedDos - kg/ha",
            "Configured - kg/ha",
        ],
        [
            {
                "geometry": f"POINT ({longitude} {latitude})",
                "Timestamp": "1735689600",
                "Date Time": "2025-01-01T10:00:00Z",
                "Service Order": order_number,
                "operation": "CALAGEM",
                "Area - ha": "1.0",
                "AppliedDos - kg/ha": "100",
                "Configured - kg/ha": "120",
            }
            for _, _, longitude, latitude, _, order_number, _ in field_specs
        ],
    )
    ndvi_rows = []
    for _, _, longitude, latitude, _, _, season_id in field_specs:
        x, y = mercator(longitude, latitude)
        ndvi_rows.append(
            {
                "filename": f"{season_id}_2025-01-08.tif",
                "season_id": season_id,
                "crs": "EPSG:3857",
                "bounds_left": x - 50,
                "bounds_bottom": y - 50,
                "bounds_right": x + 50,
                "bounds_top": y + 50,
                "b1_valid_pixels": "100",
                "b1_mean": "0.5",
            }
        )
    ndvi = csv_bytes(
        [
            "filename",
            "season_id",
            "crs",
            "bounds_left",
            "bounds_bottom",
            "bounds_right",
            "bounds_top",
            "b1_valid_pixels",
            "b1_mean",
        ],
        ndvi_rows,
    )
    soil_columns = [
        "AMOSTRA", "ARGILA", "SILTE", "AREIA", "MO", "CTC", "CTCE", "PHCACL2",
        "CA", "SATCA", "MG", "SATMG", "K", "SATK", "P", "SATB", "AL", "SATAL",
        "S", "HAL", "SB", "B", "ZN", "MN", "CU", "FE", "MO_2", "CTC_2",
        "PHCACL2_2", "AL_2", "SATB_2",
    ]
    soil = csv_bytes(
        soil_columns,
        [
            {
                "AMOSTRA": "1", "ARGILA": "20,0", "SILTE": "30,0", "AREIA": "50,0",
                "MO": "4,5", "CTC": "25,0", "CTCE": "20,0", "PHCACL2": "5,2",
                "CA": "12,0", "SATCA": "48,0", "MG": "3,0", "SATMG": "12,0",
                "K": "1,0", "SATK": "4,0", "P": "10,0", "SATB": "64,0",
                "AL": "0,5", "SATAL": "2,0", "S": "6,0", "HAL": "9,0", "SB": "16,0",
                "B": "0,2", "ZN": "1,0", "MN": "5,0", "CU": "0,5", "FE": "30,0",
                "MO_2": "4,8", "CTC_2": "26,0", "PHCACL2_2": "5,4", "AL_2": "0,3",
                "SATB_2": "66,0",
            },
            {
                "AMOSTRA": "2", "ARGILA": "25,0", "SILTE": "25,0", "AREIA": "50,0",
                "MO": "5,0", "CTC": "27,0", "CTCE": "21,0", "PHCACL2": "5,5",
                "CA": "13,0", "SATCA": "48,1", "MG": "3,2", "SATMG": "11,9",
                "K": "1,1", "SATK": "4,1", "P": "11,0", "SATB": "64,1",
                "AL": "0,4", "SATAL": "1,9", "S": "6,3", "HAL": "9,5", "SB": "17,3",
                "B": "0,3", "ZN": "1,2", "MN": "5,5", "CU": "0,6", "FE": "32,0",
                "MO_2": "5,1", "CTC_2": "27,5", "PHCACL2_2": "5,6", "AL_2": "0,2",
                "SATB_2": "67,0",
            },
        ],
        delimiter=";",
    )
    return {
        "fields.csv": fields,
        "service_orders.csv": service_order_catalog,
        "ndvi_metadata.csv": ndvi,
        "LAYER_MAP_PLANTING.csv": planting,
        "LAYER_MAP_FERTILIZATION.csv": fertilization,
        "service_orders_fields.csv": service_order_fields,
        "soil_analysis.csv": soil,
    }
