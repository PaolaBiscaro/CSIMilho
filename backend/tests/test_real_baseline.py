"""Opt-in integration regression; private CSVs stay outside the repository.

FARMLAB_REAL_DATA_DIR=/path/to/FarmLab .venv/bin/python -m pytest tests/test_real_baseline.py
"""
import hashlib
import json
import os
from pathlib import Path
from statistics import mean, median, quantiles

from fastapi.testclient import TestClient
import pytest

from app.config import get_settings
from app.data.loader import EXPECTED_FILE_NAMES
from app.harness.registry import TOOLS
from app.main import app
from tests.real_baseline_reference import audit_ndvi, audit_operations, number, read_rows, weighted

BASELINE = json.loads((Path(__file__).parent / "fixtures/real_baseline.json").read_text(encoding="utf-8"))
TARGET, REFERENCE = "103144", "103145"


def close(value, expected):
    # Numerical reproducibility, not a tolerance around the historical prototype.
    assert value == pytest.approx(expected, rel=0, abs=1e-8)


@pytest.fixture(scope="module")
def real_package():
    directory = os.environ.get("FARMLAB_REAL_DATA_DIR")
    if directory is None:
        pytest.skip("Set FARMLAB_REAL_DATA_DIR to validate the private real package.")
    root = Path(directory).expanduser()
    assert root.is_dir(), "FARMLAB_REAL_DATA_DIR must be an existing directory"
    package = {}
    for name in EXPECTED_FILE_NAMES:
        matches = [path for path in root.rglob(name) if path.is_file()]
        assert len(matches) == 1, f"Expected exactly one {name}, found {len(matches)}"
        package[name] = matches[0].read_bytes()
    assert {name: hashlib.sha256(data).hexdigest() for name, data in package.items()} == BASELINE["sha256"], (
        "Package changed: audit the new files before updating the baseline."
    )
    return package


@pytest.fixture(scope="module")
def real_results(real_package):
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("APP_ENV", "development")
        get_settings.cache_clear()
        try:
            with TestClient(app) as client:
                response = client.post("/api/datasets", files=[
                    ("files", (name, data, "text/csv")) for name, data in real_package.items()])
                assert response.status_code == 201, response.text
                validation = response.json()
                results = {}
                for name in TOOLS:
                    arguments = {"dataset_id": validation["dataset_id"]}
                    if "soil" not in name:
                        arguments.update(target_field_id=TARGET, reference_field_id=REFERENCE)
                    response = client.post("/api/diagnostics/tools", json={"tool": name, "arguments": arguments})
                    assert response.status_code == 200, response.text
                    results[name] = response.json()
                response = client.post("/api/diagnostics/tools", json={
                    "tool": "summarize_soil_analysis", "arguments": {
                        "dataset_id": validation["dataset_id"], "measurement_group": "group_2"}})
                assert response.status_code == 200, response.text
                results["soil_group_2"] = response.json()
                return validation, results
        finally:
            get_settings.cache_clear()


@pytest.fixture(scope="module")
def raw_reference(real_package):
    planting, plant_counts = audit_operations(real_package, "LAYER_MAP_PLANTING.csv")
    fertilization, fert_counts = audit_operations(real_package, "LAYER_MAP_FERTILIZATION.csv")
    return planting, fertilization, plant_counts, fert_counts, audit_ndvi(real_package)


def test_real_import_and_linkage(real_results, raw_reference):
    validation, _ = real_results
    assert validation["status"] == "ready_with_warnings"
    assert validation["quality_score"] == 60 and len(validation["warnings"]) == 15
    assert validation["errors"] == []
    assert len(validation["fields"]) == 4 and len(validation["valid_pairs"]) == 4
    assert all(file["status"] == "valid" for file in validation["files"])
    assert validation["soil"] == {"sample_count": 8, "scope": "dataset", "measurement_groups": ["group_1", "group_2"]}
    assert validation["operation_linkage"] == BASELINE["operation_linkage"]
    planting, fertilization, pc, fc, _ = raw_reference
    assert pc == BASELINE["planting_audit"] and fc == BASELINE["fertilization_audit"]
    assert sum(map(len, planting.values())) == 5850
    assert sum(map(len, fertilization.values())) == 17699


def test_real_comparability(real_results):
    result = real_results[1]["validate_comparison"]
    assert result["allowed"] is True and result["score"] == 4
    assert [criterion["satisfied"] for criterion in result["criteria"]] == [True, True, True, True, False]
    assert set(result["available_analyses"]) == set(TOOLS) - {"validate_comparison"}


def test_real_ndvi_paired_dates_and_gap(real_results, raw_reference):
    series = raw_reference[4]
    assert [len(series[fid]) for fid in (TARGET, REFERENCE)] == [31, 29]
    dates = sorted(series[TARGET].keys() & series[REFERENCE].keys())
    result = real_results[1]["compare_ndvi"]
    assert result["paired_dates"] == len(dates) == 29
    assert (result["negative_dates"], result["positive_dates"], result["equal_dates"]) == (26, 3, 0)
    assert [row["date"] for row in result["series"]] == [date.isoformat() for date in dates]
    for row, date in zip(result["series"], dates, strict=True):
        close(row["target_ndvi"], series[TARGET][date])
        close(row["reference_ndvi"], series[REFERENCE][date])
        close(row["gap"], series[TARGET][date] - series[REFERENCE][date])
    close(result["target_mean"], mean(series[TARGET][date] for date in dates))
    close(result["reference_mean"], mean(series[REFERENCE][date] for date in dates))
    close(result["mean_gap"], mean(series[TARGET][date] - series[REFERENCE][date] for date in dates))
    close(result["mean_gap"], BASELINE["ndvi_mean_gap"])


def test_real_initial_condition(real_results, raw_reference):
    planting, _, _, _, series = raw_reference
    cutoff = min(min(row["date"] for row in planting[fid]) for fid in (TARGET, REFERENCE))
    dates = [date for date in series[TARGET].keys() & series[REFERENCE].keys() if date < cutoff]
    result = real_results[1]["check_initial_condition"]
    assert result["cutoff_date"] == cutoff.isoformat() == "2025-11-11"
    assert result["paired_dates"] == len(dates) == 15
    assert result["available"] is True and result["different"] is True
    close(result["mean_gap"], mean(series[TARGET][date] - series[REFERENCE][date] for date in dates))
    close(result["mean_gap"], BASELINE["initial_mean_gap"])


def test_real_population_area_weighted(real_results, raw_reference):
    result = real_results[1]["compare_population"]
    for side, fid, count in (("target", TARGET, 2197), ("reference", REFERENCE, 1465)):
        rows = raw_reference[0][fid]
        assert result[f"{side}_rows"] == {"valid": len(rows), "discarded": 0}
        assert len(rows) == count
        close(result[f"{side}_population_per_ha"], weighted(rows, "Population - ha"))
        close(result[f"{side}_population_per_ha"], BASELINE["population"][side])
    close(result["difference_percent"], -3.650471462011807)


def test_real_calagem_area_weighted(real_results, raw_reference):
    result = real_results[1]["application_compliance"]
    for side, fid, count in (("target", TARGET, 5333), ("reference", REFERENCE, 1088)):
        rows = [row for row in raw_reference[1][fid] if row["operation"] == "CALAGEM"]
        assert result[f"{side}_rows"] == {"valid": len(rows), "discarded": 0}
        assert len(rows) == count
        applied, configured = weighted(rows, "AppliedDos - kg/ha"), weighted(rows, "Configured - kg/ha")
        close(result[f"{side}_applied_dose"], applied)
        close(result[f"{side}_configured_dose"], configured)
        close(result[f"{side}_compliance_percent"], applied / configured * 100)
        close(result[f"{side}_compliance_percent"], BASELINE["calagem_percent"][side])


@pytest.mark.parametrize(("key", "suffix", "count"), [
    ("summarize_soil_analysis", "", 25), ("soil_group_2", "_2", 17),
])
def test_real_soil_statistics_and_texture(real_package, real_results, key, suffix, count):
    rows = read_rows(real_package, "soil_analysis.csv")
    assert len(rows) == len({row["AMOSTRA"] for row in rows}) == 8
    result = real_results[1][key]
    assert result["scope"] == "dataset" and result["sample_count"] == 8
    assert result["expected_values"] == result["valid_values"] == count * 8
    assert result["completeness_percent"] == 100
    assert len(result["metrics"]) == count
    for metric in result["metrics"]:
        values = [number(row[metric["name"] + suffix]) for row in rows]
        q1, _, q3 = quantiles(values, n=4, method="inclusive")
        assert metric["valid_n"] == 8 and metric["missing_n"] == 0 and metric["unit"] is None
        for name, expected in dict(mean=mean(values), median=median(values), min=min(values),
                                   max=max(values), q1=q1, q3=q3).items():
            close(metric[name], expected)
    texture = result["texture"]
    assert (texture["valid_n"], texture["excluded_n"]) == ((0, 8) if suffix else (8, 0))
    if not suffix:
        samples = {str(row["AMOSTRA"]): row for row in rows}
        for sample in texture["samples"]:
            row = samples[sample["sample_id"]]
            total = sum(number(row[key]) for key in ("AREIA", "SILTE", "ARGILA"))
            close(sample["original_total"], total)
            assert 95 <= total <= 105
            for label, column in (("sand", "AREIA"), ("silt", "SILTE"), ("clay", "ARGILA")):
                close(sample[label], number(row[column]) / total * 100)
                close(sample[f"original_{label}"], number(row[column]))


def test_real_soil_groups_paired_by_sample(real_package, real_results):
    rows = {row["AMOSTRA"]: row for row in read_rows(real_package, "soil_analysis.csv")}
    result = real_results[1]["compare_soil_measurement_groups"]
    assert result["scope"] == "dataset" and result["sample_count"] == 8
    assert len(result["metrics"]) == 17
    for metric in result["metrics"]:
        assert metric["valid_n"] == 8 and metric["unit"] is None
        assert {pair["sample_id"] for pair in metric["pairs"]} == rows.keys()
        deltas = []
        for pair in metric["pairs"]:
            row = rows[pair["sample_id"]]
            one, two = number(row[metric["name"]]), number(row[metric["name"] + "_2"])
            close(pair["group_1"], one)
            close(pair["group_2"], two)
            close(pair["delta"], two - one)
            deltas.append(two - one)
        close(metric["median_delta"], median(deltas))
    mo = next(metric for metric in result["metrics"] if metric["name"] == "MO")
    close(mo["median_delta"], -0.965)
