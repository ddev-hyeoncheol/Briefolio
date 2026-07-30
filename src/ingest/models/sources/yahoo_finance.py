from pydantic import BaseModel, ConfigDict, Field


class YahooFinanceOriginalSourceSchema(BaseModel):
    """DTO for Yahoo Finance RSS entry original source information."""

    href: str | None = Field(default=None, description="RSS-provided original publisher link")
    title: str | None = Field(default=None, description="RSS-provided original publisher name")

    model_config = ConfigDict(
        extra="ignore",
    )


class YahooFinanceMediaContentSchema(BaseModel):
    """
    DTO for Yahoo Finance RSS media content tags.

    [Ignored RSS Fields]
    - height, width: Sizing metadata of the media content, low analytical value.
    """

    url: str | None = Field(default=None, description="RSS-provided thumbnail image URL")

    model_config = ConfigDict(
        extra="ignore",
    )


class YahooFinanceEntrySchema(BaseModel):
    """
    Pydantic schema for a validated Yahoo Finance RSS entry.

    [Ignored RSS Fields]
    - title_detail, links: Structural details of the fields, not needed for analysis.
    - published: Redundant raw string representation of the publication timestamp.
    - guidislink: Redundant indicator of whether the GUID is a link.
    - media_credit, credit: Low business value publishing credit metadata.
    """

    title: str = Field(description="RSS-provided news item title")
    link: str = Field(description="RSS-provided news item URL")
    published_parsed: list[int] | tuple[int, ...] = Field(description="RSS-provided publication timestamp structure")
    original_source: YahooFinanceOriginalSourceSchema | None = Field(
        default=None, alias="source", description="RSS-provided original source metadata"
    )
    id: str | None = Field(default=None, description="RSS-provided raw entry identifier")
    media_content: list[YahooFinanceMediaContentSchema] | None = Field(
        default=None, description="RSS-provided media content list"
    )

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )
