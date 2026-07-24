from pydantic import BaseModel, ConfigDict, Field


class SourceEnrichedArticleSchema(BaseModel):
    """
    Unified schema for raw article content enrichment results.

    [Ignored Enrichment Fields]
    - url, title: Redundant with RSS entry fields.
    - images, movies: High storage cost, low analytical value.
    - publish_date: Redundant with RSS `published_at` timestamp.
    - meta_description, meta_keywords, meta_data: Redundant or noisy parser metadata.
    - keywords, summary: Redundant parser metadata.
    """

    authors: str | None = Field(default=None, description="HTML-extracted pipe-delimited author names")
    canonical_url: str | None = Field(default=None, description="HTML-declared canonical URL")
    image_url: str | None = Field(default=None, description="HTML-extracted representative image URL")
    language: str | None = Field(default=None, description="HTML-declared language code")
    content: str | None = Field(default=None, description="HTML-extracted article body text")
    status_code: int | None = Field(default=None, description="Item HTTP status code")
    error_message: str | None = Field(default=None, description="Item error message")

    model_config = ConfigDict(
        extra="ignore",
    )
