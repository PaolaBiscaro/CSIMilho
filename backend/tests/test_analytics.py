from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from app.analytics.application import application_compliance
from app.analytics.common import AnalysisUnavailableError
from app.analytics.comparability import structural_pairs, validate_comparison
from app.analytics.contracts import DatePeriod
from app.analytics.ndvi import check_initial_condition, compare_ndvi
from app.analytics.population import compare_population
from app.analytics.soil import compare_soil_measurement_groups, summarize_soil_analysis
from app.api.datasets import _process_package
from app.data.session_store import dataset_store


@pytest.fixture
def analytical_dataset(presentation_package):
    response = _process_package(presentation_package)
    dataset = dataset_store.get(response.dataset_id)
    dataset.ndvi_observations = pd.DataFrame([
        dict(field_id=field, date=date(2024, 12, day), ndvi=value, valid_pixels=10)
        for field, values in [("103144", [.2, .3, .4, .5, .6]), ("103145", [.3, .4, .5, .6, .7])]
        for day, value in enumerate(values, 1)
    ] + [dict(field_id="103144", date=date(2024, 12, 8), ndvi=.9, valid_pixels=10)])
    dataset.planting_operations = pd.DataFrame([
        dict(field_id=field, operation="MILHO", operation_date=date(2025, 1, 1), area_ha=area, population_per_ha=population)
        for field, rows in [("103144", [(1, 10), (3, 30)]), ("103145", [(2, 20)])]
        for area, population in rows
    ])
    dataset.fertilization_operations = pd.DataFrame([
        dict(field_id=field, operation="CALAGEM", operation_date=date(2025, 1, 2),
             area_ha=area, applied_dose_kg_ha=applied, configured_dose_kg_ha=configured)
        for field, rows in [("103144", [(1, 0, 100), (3, 100, 200)]), ("103145", [(1, 100, 100)])]
        for area, applied, configured in rows
    ])
    return dataset


PAIR = ("103144", "103145")


def test_comparability_has_five_criteria_and_allows_both_pair_directions(analytical_dataset):
    dataset = analytical_dataset
    pairs = structural_pairs(dataset.fields)
    assert {(p.target_field_id, p.reference_field_id) for p in pairs} == {
        ("103144", "103145"), ("103145", "103144"), ("103146", "103147"), ("103147", "103146")}
    result = validate_comparison(dataset, *PAIR)
    assert result.allowed and result.score == 4 and result.max_score == 5
    assert len(result.criteria) == 5
    assert not result.criteria[-1].satisfied
    assert result.common_operations == ["CALAGEM"]
    assert validate_comparison(dataset, *PAIR[::-1]).allowed
    assert not validate_comparison(dataset, "103144", "103147").allowed
    assert validate_comparison(dataset, "103146", "103147").allowed


def test_different_culture_blocks_pair_unknown_culture_only_warns(analytical_dataset):
    frame = analytical_dataset.planting_operations
    frame.loc[frame.field_id == PAIR[1], "operation"] = "PLANTIO SOJA"
    assert not validate_comparison(analytical_dataset, *PAIR).allowed
    frame.loc[frame.field_id == PAIR[1], "operation"] = "PLANTIO"
    result = validate_comparison(analytical_dataset, *PAIR)
    assert result.allowed and result.criteria[0].satisfied is None
    assert result.warnings


def test_unknown_and_same_ids_are_rejected(analytical_dataset):
    for target, reference in [(PAIR[0], PAIR[0]), (PAIR[0], "absent")]:
        with pytest.raises(AnalysisUnavailableError):
            compare_ndvi(analytical_dataset, target, reference)


def test_ndvi_pairs_dates_without_interpolation_and_preserves_sign(analytical_dataset):
    result = compare_ndvi(analytical_dataset, *PAIR)
    assert result.paired_dates == 5
    assert result.target_mean == pytest.approx(.4)
    assert result.reference_mean == pytest.approx(.5)
    assert result.mean_gap == pytest.approx(-.1)
    assert result.negative_dates == 5
    assert result.series[-1].date == date(2024, 12, 5)
    assert compare_ndvi(analytical_dataset, *PAIR[::-1]).mean_gap == pytest.approx(.1)
    period = DatePeriod(start=date(2024, 12, 2), end=date(2024, 12, 3))
    subset = compare_ndvi(analytical_dataset, *PAIR, period)
    assert subset.paired_dates == 2 and subset.warnings
    assert subset.target_mean == pytest.approx(.35)


def test_ndvi_unavailable_without_pairs(analytical_dataset):
    with pytest.raises(AnalysisUnavailableError, match="uma data"):
        compare_ndvi(analytical_dataset, *PAIR, DatePeriod(start=date(2030, 1, 1), end=date(2030, 1, 2)))


@pytest.mark.parametrize(("gap", "different"), [(0, False), (.019, False), (.02, True), (-.02, True), (.1, True)])
def test_initial_condition_heuristic_boundaries(analytical_dataset, gap, different):
    frame = analytical_dataset.ndvi_observations
    frame.loc[frame.field_id == PAIR[0], "ndvi"] = .5 + gap
    frame.loc[frame.field_id == PAIR[1], "ndvi"] = .5
    result = check_initial_condition(analytical_dataset, *PAIR)
    assert result.available and result.different is different
    assert result.cutoff_date == date(2025, 1, 1)
    assert result.mean_gap == pytest.approx(gap)
    assert "Heurística operacional" in result.method


def test_initial_condition_uses_earliest_planting_and_excludes_cutoff(analytical_dataset):
    planting = analytical_dataset.planting_operations
    planting.loc[planting.field_id == PAIR[0], "operation_date"] = date(2024, 12, 4)
    result = check_initial_condition(analytical_dataset, *PAIR)
    assert result.paired_dates == 3 and result.available
    planting.loc[planting.field_id == PAIR[0], "operation_date"] = date(2024, 12, 3)
    result = check_initial_condition(analytical_dataset, *PAIR)
    assert result.paired_dates == 2 and not result.available
    assert result.mean_gap is None and result.different is None
    empty = replace(analytical_dataset, planting_operations=planting.iloc[:0])
    assert check_initial_condition(empty, *PAIR).cutoff_date is None


def test_population_is_area_weighted_and_counts_invalid_rows(analytical_dataset):
    frame = analytical_dataset.planting_operations
    frame.loc[len(frame)] = [PAIR[0], "MILHO", date(2025, 1, 1), 0, 999]
    result = compare_population(analytical_dataset, *PAIR)
    assert result.target_population_per_ha == 25  # simple mean would be 20
    assert result.reference_population_per_ha == 20
    assert result.difference == 5 and result.difference_percent == 25
    assert result.target_rows.valid == 2 and result.target_rows.discarded == 1
    assert compare_population(analytical_dataset, *PAIR[::-1]).difference_percent == -20


def test_population_empty_period_is_unavailable(analytical_dataset):
    with pytest.raises(AnalysisUnavailableError):
        compare_population(analytical_dataset, *PAIR, DatePeriod(start=date(2030, 1, 1), end=date(2030, 1, 2)))


def test_application_uses_ratio_of_area_weighted_doses(analytical_dataset):
    result = application_compliance(analytical_dataset, *PAIR)
    assert result.target_applied_dose == 75
    assert result.target_configured_dose == 175
    assert result.target_compliance_percent == pytest.approx(75/175*100)
    assert result.reference_compliance_percent == 100


@pytest.mark.parametrize(("applied", "expected"), [(0, 0), (50, 50), (100, 100), (150, 150)])
def test_application_under_exact_and_over_application(analytical_dataset, applied, expected):
    frame = analytical_dataset.fertilization_operations
    frame["applied_dose_kg_ha"] = applied
    frame["configured_dose_kg_ha"] = 100
    assert application_compliance(analytical_dataset, *PAIR).target_compliance_percent == expected


def test_application_zero_configured_dose_and_missing_operation(analytical_dataset):
    frame = analytical_dataset.fertilization_operations
    frame.loc[frame.field_id == PAIR[0], "configured_dose_kg_ha"] = 0
    with pytest.raises(AnalysisUnavailableError):
        application_compliance(analytical_dataset, *PAIR)
    with pytest.raises(AnalysisUnavailableError):
        application_compliance(analytical_dataset, *PAIR, operation="GESSAGEM")


@pytest.fixture
def soil_dataset(analytical_dataset):
    analytical_dataset.soil_samples = pd.DataFrame([
        dict(sample_id=str(index), scope="dataset", group_1={"MO": one, "PHCACL2": None, "AREIA": sand, "SILTE": 30, "ARGILA": 20}, group_2=two)
        for index, (one, two, sand) in enumerate([
            (1, {"MO": 3}, 50), (3, {"MO": 2}, 49),
            (5, {"MO": None}, 10), (None, {"MO": 100}, None),
        ], 1)
    ])
    return analytical_dataset


def test_soil_summary_manual_quartiles_nulls_and_texture(soil_dataset):
    result = summarize_soil_analysis(soil_dataset)
    metric = next(item for item in result.metrics if item.name == "MO")
    assert metric.valid_n == 3 and metric.missing_n == 1
    assert (metric.min, metric.q1, metric.median, metric.q3, metric.max, metric.mean) == (1, 2, 3, 4, 5, 3)
    assert metric.unit is None
    ph = next(item for item in result.metrics if item.name == "PHCACL2")
    assert ph.valid_n == 0 and ph.mean is None
    assert result.texture.valid_n == 2 and result.texture.excluded_n == 2
    for sample in result.texture.samples:
        assert sample.sand + sample.silt + sample.clay == pytest.approx(100)
    assert result.texture.samples[1].original_total == 99
    assert result.scope == "dataset" and "field_id" not in result.model_dump_json()


def test_soil_comparison_pairs_by_sample_not_differences_of_means(soil_dataset):
    result = compare_soil_measurement_groups(soil_dataset, metrics=["MO"])
    metric = result.metrics[0]
    assert metric.valid_n == 2 and metric.median_delta == .5
    assert [pair.sample_id for pair in metric.pairs] == ["1", "2"]
    assert [pair.delta for pair in metric.pairs] == [2, -1]
    assert any("_2 não está documentado" in text for text in result.limitations)
    assert result.comparison == "group_2_minus_group_1"


def test_soil_missing_second_group_and_filters(soil_dataset):
    soil_dataset.soil_samples["group_2"] = [{} for _ in range(4)]
    result = compare_soil_measurement_groups(soil_dataset, metrics=["MO"])
    assert result.metrics == [] and result.warnings
    summary = summarize_soil_analysis(soil_dataset, "group_2", ["MO"])
    assert summary.metrics[0].mean is None and summary.metrics[0].valid_n == 0
    assert summary.completeness_percent == 0
    with pytest.raises(AnalysisUnavailableError):
        summarize_soil_analysis(soil_dataset, metrics=["invented"])


def test_analytics_leave_normalized_dataset_unchanged(analytical_dataset):
    before = analytical_dataset.ndvi_observations.copy(deep=True)
    for function in (validate_comparison, compare_ndvi, check_initial_condition, compare_population, application_compliance):
        result = function(analytical_dataset, *PAIR)
        assert result.model_validate_json(result.model_dump_json()) == result
    pd.testing.assert_frame_equal(analytical_dataset.ndvi_observations, before)


def test_frontend_local_fixture_matches_typed_backend_results(analytical_dataset):
    import json
    from pathlib import Path
    from app.analytics.contracts import (ComparisonEvidence, NdviEvidence, InitialEvidence,
        PopulationEvidence, ApplicationEvidence, SoilSummaryEvidence, SoilGroupsEvidence)
    fixture = json.loads((Path(__file__).parents[2] / 'frontend/src/mocks/analytics-preview.json').read_text())
    models = dict(validation=ComparisonEvidence, ndvi=NdviEvidence, initial=InitialEvidence,
                  population=PopulationEvidence, application=ApplicationEvidence)
    for results in fixture['comparisons'].values():
        for name, model in models.items():
            model.model_validate(results[name])
    SoilSummaryEvidence.model_validate(fixture['soil_summary'])
    SoilSummaryEvidence.model_validate(fixture['soil_summary_2'])
    SoilGroupsEvidence.model_validate(fixture['soil_groups'])
    for key, function in [('validation', validate_comparison), ('ndvi', compare_ndvi),
                          ('initial', check_initial_condition), ('population', compare_population),
                          ('application', application_compliance)]:
        assert fixture['comparisons']['103144:103145'][key] == function(analytical_dataset, *PAIR).model_dump(mode='json')
    assert fixture['soil_summary'] == summarize_soil_analysis(analytical_dataset).model_dump(mode='json')
    assert fixture['soil_groups'] == compare_soil_measurement_groups(analytical_dataset).model_dump(mode='json')
