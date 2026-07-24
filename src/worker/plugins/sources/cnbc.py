from collections.abc import Mapping
from datetime import datetime, timezone

from src.core.logger import get_logger
from src.models.entities.news import NewsModel
from src.models.schemas.sources.cnbc import CnbcEntrySchema
from src.worker.plugins.rss_source import RssSource

logger = get_logger(__name__)


class CnbcSource(RssSource):
    """News source for CNBC RSS feed with source-specific boilerplate support."""

    @property
    def source(self) -> str:
        return "cnbc"

    @property
    def RSS_URL(self) -> str:
        return "https://search.cnbc.com/rs/search/combinedcms/view.xml" "?partnerId=wrss01&id=15839069"

    @property
    def RSS_ENTRY_STORAGE_FIELDS(self) -> set[str]:
        return {"link", "title", "published_parsed"}

    @property
    def RSS_ENTRY_METADATA_FIELDS(self) -> set[str]:
        return {"id", "metadata_type", "metadata_sponsored", "summary"}

    @property
    def RSS_ENTRY_IGNORED_FIELDS(self) -> set[str]:
        return {"links", "guidislink", "metadata_id", "title_detail", "summary_detail", "published"}

    @property
    def BOILERPLATE_CONTENTS(self) -> dict[str, str]:
        """Return known CNBC non-article boilerplates keyed by diagnostic name."""
        return {}

    async def run_fetch(self, executed_at: datetime) -> list[NewsModel]:
        """Fetch raw RSS feed and map to NewsModel entities without enrichment."""

        raw_feed = await self._fetch_feed()
        entries_data = raw_feed.get("entries") or []

        results: list[NewsModel] = []
        seen_unknowns: set[str] = set()

        for entry_data in entries_data:
            try:
                if isinstance(entry_data, Mapping):
                    self._warn_unknown_fields(entry_data=entry_data, seen_unknowns=seen_unknowns)

                entry = CnbcEntrySchema.model_validate(entry_data)
            except Exception:
                continue

            published_at = self._parse_published_at(entry=entry)
            if published_at is None:
                continue

            metadata_payload = entry.model_dump(exclude=self.RSS_ENTRY_STORAGE_FIELDS, mode="json")

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

        success_count = len(results)
        total_count = len(entries_data)

        logger.info(
            "RssSource fetch completed | source: %s, count: %d, total_count: %d, skipped_count: %d",
            self.source,
            success_count,
            total_count,
            total_count - success_count,
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
