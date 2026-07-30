from pydantic import BaseModel, ConfigDict, Field


class CnbcEntrySchema(BaseModel):
    """
    Pydantic schema for a validated CNBC RSS entry.

    [Ignored RSS Fields]
    - links, title_detail: Structural details of the fields, not needed for analysis.
    - guidislink: Redundant indicator of whether the GUID is a link.
    - metadata_id: Redundant CNBC content identifier, duplicated by id.
    - summary_detail: Structural detail of the summary field.
    - published: Redundant raw string representation of the publication timestamp.
    """

    link: str = Field(description="RSS-provided news item URL")
    id: str | None = Field(default=None, description="RSS-provided raw entry identifier")
    metadata_type: str | None = Field(default=None, description="RSS-provided CNBC content type")
    metadata_sponsored: str | None = Field(default=None, description="RSS-provided CNBC sponsored flag")
    title: str = Field(description="RSS-provided news item title")
    summary: str | None = Field(default=None, description="RSS-provided news item summary")
    published_parsed: list[int] | tuple[int, ...] = Field(description="RSS-provided publication timestamp structure")

    model_config = ConfigDict(
        extra="ignore",
    )
