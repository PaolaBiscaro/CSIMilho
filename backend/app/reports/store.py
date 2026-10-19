"""Bounded, process-local HTML snapshots; never persist credentials or raw CSVs."""
from collections import OrderedDict
from threading import RLock
from uuid import UUID

from app.harness.schemas import InvestigationResponse
from app.reports.html_report import render_html_report


class ReportStore:
    def __init__(self, max_entries: int = 32):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._reports: OrderedDict[UUID, str] = OrderedDict()
        self._lock = RLock()

    def save(self, result: InvestigationResponse) -> None:
        document = render_html_report(result)
        with self._lock:
            self._reports[result.investigation_id] = document
            self._reports.move_to_end(result.investigation_id)
            while len(self._reports) > self._max_entries:
                self._reports.popitem(last=False)

    def get(self, investigation_id: UUID) -> str:
        with self._lock:
            return self._reports[investigation_id]

    def clear(self) -> None:
        with self._lock:
            self._reports.clear()


report_store = ReportStore()
