"""Deterministic, investigation-local evidence identifiers."""

import re


class EvidenceIdGenerator:
    """Create one instance per investigation and share it among its tools.

    Each prefix has its own counter, starting at 001 (e.g. NDVI or
    APP-CALAGEM). The same ordered prefix requests reproduce the same IDs.
    IDs are unique within this instance, not across investigations; use the
    investigation_id together with evidence_id for cross-report references.
    No global counter, clock, randomness or analytical tool registry is used.
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def next_id(self, prefix: str) -> str:
        """Return EV-<prefix>-<sequence>; reject noncanonical prefixes."""
        if not isinstance(prefix, str) or not re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*", prefix):
            raise ValueError("Evidence prefix must contain uppercase alphanumeric segments starting with a letter.")
        sequence = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = sequence
        return f"EV-{prefix}-{sequence:03d}"
