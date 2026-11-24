"""End-to-end contract for the individual-field investigation mode."""

import pytest

from app.api.datasets import _process_package
from app.config import Settings
from app.data.session_store import dataset_store
from app.data.session_store import SessionStore
from app.harness.orchestrator import InvestigationError, run_investigation, run_investigation_tools
from app.harness.schemas import InvestigationRequest
from tests.test_gemini_client import settings
from tests.test_orchestrator import FakeClient, call, done, response


def test_single_field_without_gemini_blocks_report_and_preserves_dataset(presentation_package):
    dataset = _process_package(presentation_package)
    request = InvestigationRequest(
        dataset_id=dataset.dataset_id,
        analysis_mode="single_field",
        target_field_id="103144",
        reference_field_id=None,
        period="full_season",
        question="Analise a trajetória do NDVI e os registros deste talhão.",
    )

    with pytest.raises(InvestigationError) as raised:
        run_investigation(request, settings=Settings(
            GEMINI_API_KEY=None, GEMINI_API_KEY_2=None, GEMINI_API_KEY_3=None,
        ))

    assert raised.value.error.code == "missing_api_key"
    assert dataset_store.get(dataset.dataset_id) is not None


def test_single_field_rejects_reference():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        InvestigationRequest(
            dataset_id="2b4a0ad8-6771-4728-84f0-17e6702086de",
            analysis_mode="single_field",
            target_field_id="103144",
            reference_field_id="103145",
            period="full_season",
            question="Analise somente este talhão e sua trajetória.",
        )


def test_comparison_mode_without_gemini_also_blocks_final_report(presentation_package):
    dataset = _process_package(presentation_package)
    request = InvestigationRequest(
        dataset_id=dataset.dataset_id,
        target_field_id="103144",
        reference_field_id="103145",
        period="full_season",
        question="Compare os sinais disponíveis nos dois talhões selecionados.",
    )

    with pytest.raises(InvestigationError) as raised:
        run_investigation(request, settings=Settings(
            GEMINI_API_KEY=None, GEMINI_API_KEY_2=None, GEMINI_API_KEY_3=None,
        ))

    assert raised.value.error.code == "missing_api_key"
    assert dataset_store.get(dataset.dataset_id) is not None


def test_gemini_planner_is_restricted_to_individual_tools(presentation_package):
    uploaded = _process_package(presentation_package)
    store = SessionStore()
    dataset_id = store.save(dataset_store.get(uploaded.dataset_id))
    request = InvestigationRequest(
        dataset_id=dataset_id,
        analysis_mode="single_field",
        target_field_id="103144",
        period="full_season",
        question="Investigue a trajetória temporal do NDVI deste talhão.",
    )
    arguments = {"dataset_id": str(dataset_id), "field_id": "103144", "period": "full_season"}
    client = FakeClient(response(call("analyze_field_ndvi", arguments)), done())

    result = run_investigation_tools(request, client=client, settings=settings(), store=store)

    assert result.error is None
    assert [item.tool.value for item in result.trace.calls] == ["analyze_field_ndvi"]
    declared = {item.name for item in client.calls[0][1].tools[0].function_declarations}
    assert "analyze_field_ndvi" in declared
    assert "compare_ndvi" not in declared
    assert result.question == request.question
    assert result.analysis_mode == "single_field"
