"""Shared evidence primitives, independent of analytical and report schemas."""

from typing import Annotated

from pydantic import ConfigDict, Field, StrictFloat, StrictInt, StringConstraints

from app.data.contracts import StrictModel


NonEmptyText = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]
EvidenceId = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^EV-[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-[0-9]{3,}$"),
]
FiniteValue = Annotated[StrictFloat, Field(allow_inf_nan=False)]


class Evidence(StrictModel):
    """Metadata shared by every tool, extended by inheritance or composition.

    Values are optional for unavailable analyses and multi-metric outputs such
    as soil summaries. Specialized results carry their own typed metrics and
    counts. Null means unknown/unavailable, never zero. No field association is
    imposed on dataset-wide soil evidence.
    """

    model_config = ConfigDict(allow_inf_nan=False)

    evidence_id: EvidenceId
    unit: NonEmptyText | None
    source_files: list[NonEmptyText] = Field(min_length=1)
    method: NonEmptyText
    observation_count: StrictInt | None = Field(ge=0)
    tool_version: NonEmptyText
    notes: list[NonEmptyText] = Field(default_factory=list)
    metric: NonEmptyText | None = None
    target_value: FiniteValue | None = None
    reference_value: FiniteValue | None = None
    difference: FiniteValue | None = None
