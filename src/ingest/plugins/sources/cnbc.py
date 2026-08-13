from datetime import datetime, timezone

from src.ingest.models.news import NewsModel
from src.ingest.models.sources.cnbc import CnbcEntrySchema
from src.ingest.plugins.rss import RssPlugin


class CnbcSource(RssPlugin):
    """RSS source for fetching and mapping CNBC news."""

    @property
    def source(self) -> str:
        return "cnbc"

    @property
    def rss_url(self) -> str:
        return "https://search.cnbc.com/rs/search/combinedcms/view.xml" "?partnerId=wrss01&id=15839069"

    @property
    def rss_entry_storage_fields(self) -> set[str]:
        return {"link", "title", "published_parsed"}

    @property
    def rss_entry_metadata_fields(self) -> set[str]:
        return {"id", "metadata_type", "metadata_sponsored", "summary"}

    @property
    def rss_entry_ignored_fields(self) -> set[str]:
        return {"links", "guidislink", "metadata_id", "title_detail", "summary_detail", "published"}

    @property
    def boilerplate_contents(self) -> dict[str, str]:
        return {}

    async def run_fetch(self, executed_at: datetime) -> list[NewsModel]:
        """Fetch raw RSS feed and map to NewsModel entities without enrichment."""

        raw_feed = await self._fetch_feed()
        entries_data = raw_feed.get("entries") or []

        results: list[NewsModel] = []

        for entry_data in entries_data:
            try:
                entry = CnbcEntrySchema.model_validate(entry_data)
            except Exception:
                continue

            published_at = self._parse_published_at(entry=entry)
            if published_at is None:
                continue

            metadata_payload = entry.model_dump(exclude=self.rss_entry_storage_fields, mode="json")

            results.append(
                NewsModel(
                    executed_at=executed_at,
                    source=self.source,
                    title=entry.title,
                    entry_url=entry.link,
                    published_at=published_at,
                    metadata=metadata_payload,
                )
            )

        return results

    def _parse_published_at(self, entry: CnbcEntrySchema) -> datetime | None:
        """Return the RSS publication timestamp as a UTC datetime."""
        published_parsed = entry.published_parsed
        if not isinstance(published_parsed, (list, tuple)):
            return None
        try:
            return datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            return None
