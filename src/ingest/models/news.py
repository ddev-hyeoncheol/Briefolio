import uuid
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, computed_field

_NAMESPACE_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "gemini-news-brief")


def make_url_id(url: str) -> str:
    """Return a deterministic UUID v5 for the normalized form of a URL."""
    parts = urlsplit(url.strip())
    normalized_url = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
    return str(uuid.uuid5(_NAMESPACE_UUID, normalized_url))


class NewsModel(BaseModel):
    """Entity model representing a raw news item collected directly from external sources."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        str_strip_whitespace=True,
    )

    executed_at: AwareDatetime = Field(description="Normalized 10-minute UTC ingest execution slot")
    source: str = Field(description="RSS news source identifier")
    title: str = Field(description="RSS-provided news item title")
    entry_url: str = Field(description="RSS-provided news item URL")
    published_at: AwareDatetime = Field(description="RSS-provided publication timestamp")
    updated_at: AwareDatetime | None = Field(default=None, description="RSS-provided update timestamp")
    thumbnail_url: str | None = Field(default=None, description="RSS-provided thumbnail image URL")
    authors: str | None = Field(default=None, description="HTML-extracted pipe-delimited author names")
    canonical_url: str | None = Field(default=None, description="HTML-declared canonical URL")
    image_url: str | None = Field(default=None, description="HTML-extracted representative image URL")
    language: str | None = Field(default=None, description="HTML-declared language code")
    content: str | None = Field(default=None, description="HTML-extracted article body text")
    status: Literal["success", "failed"] | None = Field(default=None, description="HTML enrichment status")
    status_code: int | None = Field(default=None, description="Article fetch HTTP status code")
    error_message: str | None = Field(default=None, description="HTML enrichment error message")
    metadata: dict[str, Any] | None = Field(default=None, description="Source-specific RSS metadata")

    # news_id is the pipeline-wide unique key, so it is serialized into the raw JSONL.
    # entry_key is internal dedup bookkeeping: a plain property never lands in model_dump.
    @computed_field(
        description=(
            "Deterministic identifier derived from the canonical URL when available, "
            "otherwise the RSS entry URL"
        )
    )
    @property
    def news_id(self) -> str:
        """Return the URL-derived unique news identifier (canonical URL preferred)."""
        return make_url_id(self.canonical_url or self.entry_url)

    @property
    def entry_key(self) -> str:
        """Return the URL-derived dedup key for the RSS entry URL."""
        return make_url_id(self.entry_url)
