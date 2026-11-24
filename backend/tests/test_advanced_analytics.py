from datetime import date

import pandas as pd
import pytest

from app.analytics.common import AnalysisUnavailableError
from app.analytics.ndvi import (
    detect_field_ndvi_changes,
    test_paired_ndvi_difference as run_paired_ndvi_test,
)
from app.analytics.soil import test_soil_measurement_groups as run_soil_group_test
from app.analytics.statistics import (
    holm_adjust,
    paired_sign_statistics,
    select_paired_continuous_test,
)
from app.analytics.temporal import associate_field_operations_ndvi
from app.api.datasets import _process_package
from app.data.session_store import dataset_store


@pytest.fixture
def advanced_dataset(presentation_package):
    response = _process_package(presentation_package)
    dataset = dataset_store.get(response.dataset_id)
    dataset.ndvi_observations = pd.DataFrame(
        [
            {
                "field_id": field_id,
                "date": date(2025, 1, day),
                "ndvi": value,
                "valid_pixels": 10,
            }
            for field_id, values in (
                ("103144", [0.20, 0.22, 0.24, 0.05, 0.07, 0.09]),
                ("103145", [0.10, 0.12, 0.14, -0.05, -0.03, -0.01]),
            )
            for day, value in enumerate(values, 1)
        ]
    )
    dataset.planting_operations = pd.DataFrame(
        [
            {
                "field_id": "103144",
                "operation": "MILHO",
                "operation_date": date(2025, 1, 3),
                "area_ha": 10.0,
                "population_per_ha": 60000.0,
            }
        ]
    )
    dataset.fertilization_operations = pd.DataFrame(
        [
            {
                "field_id": "103144",
                "operation": "CALAGEM",
                "operation_date": date(2025, 1, 4),
                "area_ha": 10.0,
                "applied_dose_kg_ha": 100.0,
                "configured_dose_kg_ha": 100.0,
            }
        ]
    )
    return dataset


def test_test_selection_uses_sample_design_not_question_wording():
    small = select_paired_continuous_test(4, repeated_time=True)
    assert small.method == "descriptive_only"
    assert small.minimum_pairs == 5

    temporal = select_paired_continuous_test(8, repeated_time=True)
    assert temporal.method == "paired_sign_test"
    assert temporal.inference_scope == "exploratory"
    assert "autocorrelacionadas" in temporal.reason

    soil = select_paired_continuous_test(8, multiple_metrics=True)
    assert soil.inference_scope == "confirmatory"
    assert soil.multiplicity_correction == "holm"


def test_exact_sign_test_effect_size_interval_and_holm_are_deterministic():
    result = paired_sign_statistics([1.0] * 6)
    assert result["p_value"] == pytest.approx(0.03125)
    assert result["rank_biserial"] == 1.0
    assert result["median_ci_low"] == result["median_ci_high"] == 1.0
    assert result["significant"] is True
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_robust_change_detection_finds_break_not_regular_growth(advanced_dataset):
    result = detect_field_ndvi_changes(advanced_dataset, "103144")
    assert result.observations == 6
    assert len(result.changes) == 1
    assert result.changes[0].date == date(2025, 1, 4)
    assert result.changes[0].direction == "decrease"
    assert result.changes[0].change == pytest.approx(-0.19)
    assert "causa" in result.warnings[0]


def test_change_detection_blocks_when_series_is_too_short(advanced_dataset):
    advanced_dataset.ndvi_observations = advanced_dataset.ndvi_observations.iloc[:4]
    with pytest.raises(AnalysisUnavailableError, match="cinco observações"):
        detect_field_ndvi_changes(advanced_dataset, "103144")


def test_paired_ndvi_test_reports_effect_uncertainty_and_temporal_limit(advanced_dataset):
    result = run_paired_ndvi_test(advanced_dataset, "103144", "103145")
    assert result.pair_count == result.nonzero_pairs == 6
    assert result.median_difference == pytest.approx(0.10)
    assert result.p_value == pytest.approx(0.03125)
    assert result.rank_biserial == 1.0
    assert result.significant is True
    assert result.inference_scope == "exploratory"
    assert any("autocorrelacionadas" in warning for warning in result.warnings)


def test_paired_ndvi_test_blocks_below_minimum_nonzero_pairs(advanced_dataset):
    frame = advanced_dataset.ndvi_observations
    advanced_dataset.ndvi_observations = frame.loc[frame["date"] <= date(2025, 1, 4)]
    with pytest.raises(AnalysisUnavailableError, match="cinco pares"):
        run_paired_ndvi_test(advanced_dataset, "103144", "103145")


def test_operation_ndvi_link_is_temporal_and_never_causal(advanced_dataset):
    result = associate_field_operations_ndvi(
        advanced_dataset,
        "103144",
        operation="CALAGEM",
        max_window_days=10,
    )
    assert result.eligible_operations == 1
    link = result.links[0]
    assert link.operation_date == date(2025, 1, 4)
    assert link.before_date == date(2025, 1, 4)
    assert link.after_date == date(2025, 1, 5)
    assert link.ndvi_change == pytest.approx(0.02)
    assert any("não demonstra" in warning for warning in result.warnings)


def test_operation_ndvi_link_reports_missing_temporal_coverage(advanced_dataset):
    advanced_dataset.fertilization_operations.loc[:, "operation_date"] = date(2030, 1, 1)
    with pytest.raises(AnalysisUnavailableError, match="observações válidas"):
        associate_field_operations_ndvi(advanced_dataset, "103144", operation="CALAGEM")


def test_soil_paired_test_uses_holm_and_preserves_dataset_scope(advanced_dataset):
    advanced_dataset.soil_samples = pd.DataFrame(
        [
            {
                "sample_id": str(index),
                "scope": "dataset",
                "group_1": {"MO": float(index)},
                "group_2": {"MO": float(index + 1)},
            }
            for index in range(1, 7)
        ]
    )
    result = run_soil_group_test(advanced_dataset, metrics=["MO"])
    test = result.tests[0]
    assert result.scope == "dataset"
    assert result.executed_tests == 1
    assert test.status == "executed"
    assert test.median_delta == 1.0
    assert test.raw_p_value == test.adjusted_p_value == pytest.approx(0.03125)
    assert test.significant_after_holm is True
    assert "field_id" not in result.model_dump_json()
    assert any("sem vínculo" in limitation for limitation in result.limitations)


def test_soil_paired_test_distinguishes_insufficient_data(advanced_dataset):
    advanced_dataset.soil_samples = pd.DataFrame(
        [
            {
                "sample_id": str(index),
                "scope": "dataset",
                "group_1": {"MO": float(index)},
                "group_2": {"MO": float(index + 1)},
            }
            for index in range(1, 5)
        ]
    )
    with pytest.raises(AnalysisUnavailableError, match="cinco pares"):
        run_soil_group_test(advanced_dataset, metrics=["MO"])
