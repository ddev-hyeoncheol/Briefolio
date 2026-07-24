from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

IngestStatus = Literal["success", "partial", "failed"]
IngestPhase = Literal["fetch", "entry_lookup", "enrich", "news_lookup", "load", "state_write"]


class IngestRequest(BaseModel):
    """Request payload to trigger an ingest execution."""

    executed_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="Requested ingest execution time. Defaults to current UTC time if not provided.",
    )


class IngestSourceResult(BaseModel):
    """Response payload for a single news source execution."""

    source: str = Field(
        description="News source name.",
    )
    executed_at: AwareDatetime = Field(
        description="Normalized ingest execution time (UTC).",
    )
    status: IngestStatus = Field(
        description="Status of this source execution.",
    )
    count: int = Field(
        default=0,
        description="Number of news items loaded by this source execution.",
    )
    started_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this source execution started (UTC).",
    )
    completed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this source execution finished (UTC).",
    )
    elapsed_seconds: float | None = Field(
        default=None,
        description="Duration of this source execution in seconds.",
    )
    failed_phase: IngestPhase | None = Field(
        default=None,
        description="Source execution phase where a phase-level failure occurred.",
    )
    error_message: str | None = Field(
        default=None,
        description="Phase-level error message for this source execution.",
    )


class IngestResponse(BaseModel):
    """Response payload for an ingest execution."""

    executed_at: AwareDatetime = Field(
        description="Normalized ingest execution time (UTC).",
    )
    run_id: str = Field(
        description="Unique identifier of this invocation, used as the capture path segment.",
    )
    status: IngestStatus = Field(
        description="Overall status of this ingest execution.",
    )
    count: int = Field(
        default=0,
        description="Total number of news items loaded across all sources.",
    )
    started_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this ingest execution started (UTC).",
    )
    completed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp when this ingest execution finished (UTC).",
    )
    elapsed_seconds: float | None = Field(
        default=None,
        description="Duration of this ingest execution in seconds.",
    )
    details: list[IngestSourceResult] = Field(
        default_factory=list,
        description="Per-source execution results for this ingest execution.",
    )
