from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

import pandas as pd

from app.data.contracts import FieldRecord
from app.data.linker import SeasonFieldLink


@dataclass
class NormalizedDataset:
    fields: list[FieldRecord]
    ndvi_observations: pd.DataFrame
    planting_operations: pd.DataFrame
    fertilization_operations: pd.DataFrame
    service_order_number_mapping: dict[str, str]
    service_order_operations: dict[str, str]
    service_order_mapping: dict[str, set[str]]
    season_links: list[SeasonFieldLink]
    soil_samples: pd.DataFrame
    soil_metadata: dict[str, Any]
    dataset_metadata: dict[str, Any] = field(default_factory=dict)


class DatasetNotFoundError(LookupError):
    def __init__(self, dataset_id: UUID | str) -> None:
        super().__init__(f"Dataset não encontrado: {dataset_id}.")
        self.dataset_id = dataset_id


class SessionStore:
    def __init__(self) -> None:
        self._datasets: dict[UUID, NormalizedDataset] = {}
        self._lock = RLock()

    def save(self, dataset: NormalizedDataset, dataset_id: UUID | None = None) -> UUID:
        identifier = dataset_id or uuid4()
        with self._lock:
            self._datasets[identifier] = _copy_dataset(dataset)
        return identifier

    def get(self, dataset_id: UUID | str) -> NormalizedDataset:
        try:
            identifier = dataset_id if isinstance(dataset_id, UUID) else UUID(str(dataset_id))
        except ValueError as exc:
            raise DatasetNotFoundError(dataset_id) from exc

        with self._lock:
            dataset = self._datasets.get(identifier)
            if dataset is None:
                raise DatasetNotFoundError(identifier)
            return _copy_dataset(dataset)

    def clear(self) -> None:
        with self._lock:
            self._datasets.clear()


dataset_store = SessionStore()


def _copy_dataset(dataset: NormalizedDataset) -> NormalizedDataset:
    copied = deepcopy(dataset)
    # pandas preserves references stored inside object cells even in a deep DataFrame copy.
    copied.soil_samples = copied.soil_samples.map(deepcopy)
    return copied
