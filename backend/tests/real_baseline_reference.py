"""Reference calculations for the fixed real package, independent of app code.

Uses csv/math/statistics for parsing and arithmetic; Shapely only for geometry.
This is a test oracle for W2.14, not a second application pipeline.
"""
import csv
import io
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from statistics import mean

from shapely import wkt


def read_rows(package, name):
    return list(csv.DictReader(io.StringIO(package[name].decode("utf-8-sig")),
                               delimiter="," if name == "ndvi_metadata.csv" else ";"))


def number(value):
    result = float(value.replace(",", "."))
    assert math.isfinite(result)
    return result


def weighted(rows, column):
    return math.fsum(number(row[column]) * number(row["Area - ha"]) for row in rows) / math.fsum(
        number(row["Area - ha"]) for row in rows
    )


def audit_operations(package, name):
    fields = {row["idField"]: wkt.loads(row["fieldGeom"]) for row in read_rows(package, "fields.csv")}
    orders = {Decimal(row["serviceOrderNumber"]): row["idServiceOrder"]
              for row in read_rows(package, "service_orders.csv")}
    candidates = defaultdict(set)
    for row in read_rows(package, "service_orders_fields.csv"):
        candidates[row["idServiceOrder"]].add(row["idField"])
    result, counts = defaultdict(list), Counter()
    for row in read_rows(package, name):
        order = orders.get(Decimal(row["Service Order"]))
        if order is None:
            counts["unknown_order"] += 1
            continue
        choices = candidates[order] & fields.keys()
        if not choices:
            counts["no_candidates"] += 1
            continue
        geometry = wkt.loads(row["geometry"])
        if not geometry.is_valid or geometry.is_empty:
            counts["invalid_geometry"] += 1
            continue
        found = [fid for fid in choices if fields[fid].covers(geometry.representative_point())]
        if not found and geometry.area:
            overlap = sorted((geometry.intersection(fields[fid]).area / geometry.area, fid)
                             for fid in choices)
            if overlap[-1][0] >= .5:
                assert len(overlap) == 1 or not math.isclose(
                    overlap[-1][0], overlap[-2][0], rel_tol=1e-9, abs_tol=1e-12)
                found = [overlap[-1][1]]
        if not found:
            counts["outside"] += 1
            continue
        assert len(found) == 1
        counts["assigned"] += 1
        columns = (["Population - ha"] if "PLANTING" in name
                   else ["AppliedDos - kg/ha", "Configured - kg/ha"])
        try:
            area, values = number(row["Area - ha"]), [number(row[col]) for col in columns]
            assert area > 0 and values[-1] > 0 and values[0] >= 0
            date = datetime.strptime(row["Date Time"], "%d/%m/%Y %H:%M:%S").date()
        except (ValueError, AssertionError):
            counts["invalid_values"] += 1
            continue
        result[found[0]].append(dict(row, date=date))
    return dict(result), dict(counts)


def audit_ndvi(package):
    centers = {row["idField"]: json.loads(row["fieldAreaCentroid"])
               for row in read_rows(package, "fields.csv")}
    seasons = defaultdict(list)
    for row in read_rows(package, "ndvi_metadata.csv"):
        if number(row["b1_valid_pixels"]) > 0:
            seasons[row["season_id"]].append(row)
    series = {}
    for rows in seasons.values():
        assert all(row["crs"] == "EPSG:3857" for row in rows)
        x = mean((number(r["bounds_left"]) + number(r["bounds_right"])) / 2 for r in rows)
        y = mean((number(r["bounds_bottom"]) + number(r["bounds_top"])) / 2 for r in rows)
        lon, lat = x / 6378137, 2 * math.atan(math.exp(y / 6378137)) - math.pi / 2
        distances = []
        for fid, center in centers.items():
            a, b = math.radians(center["longitude"]), math.radians(center["latitude"])
            distance = 2 * 6378137 * math.asin(math.sqrt(
                math.sin((b - lat) / 2) ** 2 + math.cos(b) * math.cos(lat) * math.sin((a - lon) / 2) ** 2))
            distances.append((distance, fid))
        distances.sort()
        assert distances[0][0] < 1000 and distances[1][0] - distances[0][0] > 1
        fid = distances[0][1]
        assert fid not in series
        series[fid] = {}
        for row in rows:
            date = datetime.strptime(row["filename"][-15:-5], "%Y-%m-%d").date()
            assert date not in series[fid]  # The audited package has no duplicate field/date.
            value = number(row["b1_mean"])
            assert -1 <= value <= 1
            series[fid][date] = value
    return series
