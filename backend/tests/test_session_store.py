import pandas as pd
import pytest

from app.data.normalizer import normalize_fields
from app.data.session_store import DatasetNotFoundError, NormalizedDataset, SessionStore
from tests.test_normalizer import demonstration_fields_frame


def dataset(label: str = "original") -> NormalizedDataset:
    return NormalizedDataset(
        fields=normalize_fields(demonstration_fields_frame()).fields,
        ndvi_observations=pd.DataFrame({"field_id": ["103144"], "ndvi": [0.5]}),
        planting_operations=pd.DataFrame({"field_id": ["103144"]}),
        fertilization_operations=pd.DataFrame({"field_id": ["103144"]}),
        service_order_number_mapping={"1": "SO-1"},
        service_order_operations={"SO-1": "PLANTIO"},
        service_order_mapping={"SO-1": {"103144"}},
        season_links=[],
        dataset_metadata={"label": label, "source_files": ["fields.csv"]},
    )


def test_store_recovers_normalized_objects_by_uuid() -> None:
    store = SessionStore()
    dataset_id = store.save(dataset())

    recovered = store.get(dataset_id)

    assert recovered.fields[0].field_id == "103144"
    assert recovered.ndvi_observations.loc[0, "ndvi"] == 0.5
    assert recovered.service_order_mapping == {"SO-1": {"103144"}}
    assert recovered.dataset_metadata["source_files"] == ["fields.csv"]


def test_store_can_replace_package_under_same_id() -> None:
    store = SessionStore()
    dataset_id = store.save(dataset())

    returned_id = store.save(dataset("replacement"), dataset_id=dataset_id)

    assert returned_id == dataset_id
    assert store.get(dataset_id).dataset_metadata["label"] == "replacement"


def test_store_returns_controlled_error_for_unknown_id() -> None:
    store = SessionStore()

    with pytest.raises(DatasetNotFoundError, match="Dataset não encontrado"):
        store.get("00000000-0000-0000-0000-000000000000")


def test_store_returns_copies_instead_of_mutable_internal_state() -> None:
    store = SessionStore()
    dataset_id = store.save(dataset())
    recovered = store.get(dataset_id)
    recovered.ndvi_observations.loc[0, "ndvi"] = 0.9

    assert store.get(dataset_id).ndvi_observations.loc[0, "ndvi"] == 0.5
