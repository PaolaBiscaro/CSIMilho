"""Untrusted calls are checked against an investigation's fixed selection."""

from copy import deepcopy
from dataclasses import replace
import traceback
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.analytics.contracts import ComparisonArgs
from app.data.session_store import SessionStore
from app.harness import validators
from app.harness.registry import TOOLS, execute_tool
from app.harness.schemas import InvestigationRequest
from app.harness.validators import ToolCallValidationError, ToolCallValidator
from tests.test_analytics import analytical_dataset


@pytest.fixture
def context(analytical_dataset):
    store = SessionStore()
    request = InvestigationRequest(
        dataset_id=store.save(analytical_dataset), target_field_id="103144",
        reference_field_id="103145", period="full_season", question="Como os talhões se comparam?",
    )
    return request, store


def comparison_args(request):
    return request.model_dump(mode="json", exclude={"question"})


def assert_rejected(validator, name, arguments, code):
    with pytest.raises(ToolCallValidationError) as caught:
        validator.validate_call(name, arguments)
    assert caught.value.code == code
    return caught.value


@pytest.mark.parametrize("name", list(TOOLS))
def test_all_seven_tools_accept_correct_scope_and_return_executable_arguments(context, name):
    request, store = context
    args = {"dataset_id": str(request.dataset_id)} if "soil" in name else comparison_args(request)
    original = deepcopy(args)
    params = ToolCallValidator(request, store=store).validate_call(name, args)
    assert type(params) is TOOLS[name].parameters
    assert params.dataset_id == request.dataset_id
    assert args == original
    result = execute_tool(name, params.model_dump(mode="json"), store=store)
    assert result.evidence_id and result.source_files
    if "soil" in name:
        assert result.scope == "dataset"
        assert "target_field_id" not in params.model_dump()
    else:
        assert result.target_field_id == request.target_field_id


@pytest.mark.parametrize("name", ["execute_python", "COMPARE_NDVI", " compare_ndvi", "", None, [], {}])
def test_unknown_and_malformed_tool_names_are_controlled_errors(context, name):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    assert_rejected(validator, name, comparison_args(request), "unknown_tool")
    assert validator.validate_call("compare_ndvi", comparison_args(request))


@pytest.mark.parametrize("payload", [None, [], "{}", 1, True])
def test_arguments_must_be_an_object(context, payload):
    request, store = context
    assert_rejected(ToolCallValidator(request, store=store), "compare_ndvi", payload, "invalid_arguments")


@pytest.mark.parametrize("change", [
    {"path": "private.csv"}, {"frame": []}, {"store": {}}, {"ids": {}},
    {"dataset_id": "not-a-uuid"}, {"target_field_id": 103144}, {"reference_field_id": " "},
    {"period": {"start": "2026-02-01", "end": "2026-01-01"}},
    {"period": {"start": "2026-01-01", "end": "2026-02-01", "path": "private.csv"}},
])
def test_schema_rejects_invalid_types_extras_and_bad_periods_without_reserving(context, change):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    assert_rejected(validator, "compare_ndvi", {**comparison_args(request), **change}, "invalid_arguments")
    assert validator.validate_call("compare_ndvi", comparison_args(request))


def test_missing_fields_and_prebuilt_models_cannot_bypass_validation(context):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    assert_rejected(validator, "compare_ndvi", {"dataset_id": str(request.dataset_id)}, "invalid_arguments")
    forged = ComparisonArgs.model_construct(**comparison_args(request), path="private.csv")
    assert_rejected(validator, "compare_ndvi", forged, "invalid_arguments")


@pytest.mark.parametrize("name", ["compare_ndvi", "summarize_soil_analysis", "compare_soil_measurement_groups"])
def test_cannot_switch_to_another_existing_dataset(context, analytical_dataset, name):
    request, store = context
    other_id = store.save(analytical_dataset)
    args = {"dataset_id": str(other_id)}
    if "soil" not in name:
        args = {**comparison_args(request), **args}
    assert_rejected(ToolCallValidator(request, store=store), name, args, "dataset_mismatch")


@pytest.mark.parametrize("field", ["target_field_id", "reference_field_id"])
def test_field_from_another_dataset_is_not_accepted(context, analytical_dataset, field):
    request, store = context
    other = deepcopy(analytical_dataset)
    other.fields[0].field_id = "other-dataset-field"
    store.save(other)
    args = {**comparison_args(request), field: "other-dataset-field"}
    assert_rejected(ToolCallValidator(request, store=store), "compare_ndvi", args, "field_not_found")


@pytest.mark.parametrize("change", [
    {"target_field_id": "103145", "reference_field_id": "103144"},
    {"target_field_id": "103146"}, {"reference_field_id": "103147"},
    {"target_field_id": "103145"},
])
def test_existing_fields_cannot_replace_or_reverse_selected_pair(context, change):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    assert_rejected(validator, "validate_comparison", {**comparison_args(request), **change}, "pair_changed")
    assert validator.validate_call("validate_comparison", comparison_args(request))


@pytest.mark.parametrize(("change", "code"), [
    ({"dataset_id": uuid4()}, "dataset_not_found"),
    ({"target_field_id": "missing"}, "field_not_found"),
    ({"reference_field_id": "103144"}, "invalid_pair"),
])
def test_invalid_initial_selection_is_rejected(context, change, code):
    request, store = context
    request = InvestigationRequest.model_validate({**request.model_dump(), **change})
    with pytest.raises(ToolCallValidationError) as caught:
        ToolCallValidator(request, store=store)
    assert caught.value.code == code


def test_removed_dataset_is_checked_again_on_each_call(context):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    validator.validate_call("validate_comparison", comparison_args(request))
    store.clear()
    assert_rejected(validator, "compare_ndvi", comparison_args(request), "dataset_not_found")


def test_removed_field_is_checked_again_even_for_soil(context):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    dataset = store.get(request.dataset_id)
    dataset.fields = [item for item in dataset.fields if item.field_id != request.target_field_id]
    store.save(dataset, dataset_id=request.dataset_id)
    assert_rejected(validator, "summarize_soil_analysis", {"dataset_id": str(request.dataset_id)}, "field_not_found")


def test_period_is_fixed_and_equivalent_date_objects_are_normalized(context):
    request, store = context
    period = {"start": "2024-12-01", "end": "2024-12-05"}
    request = InvestigationRequest.model_validate({**request.model_dump(), "period": period})
    validator = ToolCallValidator(request, store=store)
    args = comparison_args(request)
    assert_rejected(validator, "compare_ndvi", {**args, "period": "full_season"}, "period_changed")
    assert_rejected(validator, "compare_ndvi", {k: v for k, v in args.items() if k != "period"}, "period_changed")
    assert_rejected(validator, "compare_ndvi", {**args, "period": {**period, "end": "2024-12-04"}}, "period_changed")
    params = validator.validate_call("compare_ndvi", args)
    assert params.period == request.period
    assert_rejected(validator, "compare_ndvi", params.model_dump(), "duplicate_call")


@pytest.mark.parametrize("change", [{"target_field_id": "103144"}, {"period": "full_season"},
                                    {"metrics": []}, {"metrics": ["INVENTED"]}])
def test_soil_rejects_field_scope_and_unsupported_filters(context, change):
    request, store = context
    assert_rejected(ToolCallValidator(request, store=store), "summarize_soil_analysis",
                    {"dataset_id": str(request.dataset_id), **change}, "invalid_arguments")


def test_duplicates_include_defaults_whitespace_and_uuid_normalization(context):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    args = comparison_args(request)
    args.pop("period")
    validator.validate_call("compare_ndvi", args)
    repeated = dict(reversed(list(comparison_args(request).items())))
    repeated.update(dataset_id=request.dataset_id.hex.upper(), target_field_id=" 103144 ")
    assert_rejected(validator, "compare_ndvi", repeated, "duplicate_call")
    assert validator.validate_call("compare_population", comparison_args(request))


def test_operations_use_same_canonicalization_as_analytics(context):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    args = comparison_args(request)
    first = validator.validate_call("application_compliance", args)
    assert first.operation == "CALAGEM"
    assert_rejected(validator, "application_compliance", {**args, "operation": " calágem "}, "duplicate_call")
    assert_rejected(validator, "application_compliance", {**args, "operation": "🌱"}, "invalid_arguments")
    assert validator.validate_call("application_compliance", {**args, "operation": " outra operação "}).operation == "OUTRA OPERACAO"


def test_soil_defaults_and_same_metric_set_are_duplicates_but_new_groups_are_allowed(context):
    request, store = context
    validator = ToolCallValidator(request, store=store)
    args = {"dataset_id": str(request.dataset_id)}
    validator.validate_call("summarize_soil_analysis", args)
    assert_rejected(validator, "summarize_soil_analysis", {**args, "metrics": None, "measurement_group": "group_1"}, "duplicate_call")
    assert validator.validate_call("summarize_soil_analysis", {**args, "measurement_group": "group_2"})
    selected = validator.validate_call("summarize_soil_analysis", {**args, "metrics": ["MO", "PHCACL2", "MO"]})
    assert selected.metrics == ["MO", "PHCACL2"]
    assert_rejected(validator, "summarize_soil_analysis", {**args, "metrics": ["PHCACL2", "MO"]}, "duplicate_call")
    assert validator.validate_call("summarize_soil_analysis", {**args, "metrics": ["MO"]})
    assert validator.validate_call("compare_soil_measurement_groups", {**args, "metrics": ["MO"]})


def test_validation_reserves_call_without_executing_and_state_is_local(context, monkeypatch):
    request, store = context
    function = Mock(side_effect=AssertionError("validator must not execute tools"))
    monkeypatch.setattr(validators, "TOOLS", {name: replace(tool, function=function) for name, tool in TOOLS.items()})
    first = ToolCallValidator(request, store=store)
    second = ToolCallValidator(request, store=store)
    args = comparison_args(request)
    first.validate_call("compare_ndvi", args)
    assert_rejected(first, "compare_ndvi", args, "duplicate_call")
    assert second.validate_call("compare_ndvi", args)
    function.assert_not_called()


def test_caller_mutation_does_not_change_selection_or_reserved_fingerprint(context):
    request, store = context
    args = comparison_args(request)
    validator = ToolCallValidator(request, store=store)
    request.target_field_id = "103146"
    result = validator.validate_call("compare_ndvi", args)
    result.target_field_id = "103147"
    assert_rejected(validator, "compare_ndvi", args, "duplicate_call")
    assert_rejected(validator, "compare_population", comparison_args(request), "pair_changed")
    assert validator.validate_call("compare_population", args)


def test_error_text_does_not_echo_untrusted_values_or_validation_details(context, caplog):
    request, store = context
    sentinel = "private-key-or-prompt-sentinel"
    validator = ToolCallValidator(request, store=store)
    for name, args, code in [
        (sentinel, {}, "unknown_tool"),
        ("compare_ndvi", {**comparison_args(request), "period": {"start": sentinel}}, "invalid_arguments"),
        ("compare_ndvi", {**comparison_args(request), "target_field_id": sentinel}, "field_not_found"),
    ]:
        error = assert_rejected(validator, name, args, code)
        public = str(error) + repr(error) + str(vars(error)) + "".join(traceback.format_exception(error)) + caplog.text
        assert sentinel not in public
