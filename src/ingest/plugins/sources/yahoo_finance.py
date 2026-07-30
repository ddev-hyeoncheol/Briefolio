from datetime import datetime, timezone

from src.ingest.models.news import NewsModel
from src.ingest.models.sources.yahoo_finance import YahooFinanceEntrySchema
from src.ingest.plugins.rss import RssPlugin


class YahooFinanceSource(RssPlugin):
    """News source for Yahoo Finance RSS feed with source-specific boilerplate support."""

    @property
    def source(self) -> str:
        return "yahoo_finance"

    @property
    def rss_url(self) -> str:
        return "https://finance.yahoo.com/rss/"

    @property
    def rss_entry_storage_fields(self) -> set[str]:
        return {"title", "link", "published_parsed", "media_content"}

    @property
    def rss_entry_metadata_fields(self) -> set[str]:
        return {"source", "id"}

    @property
    def rss_entry_ignored_fields(self) -> set[str]:
        return {"title_detail", "links", "published", "guidislink", "media_credit", "credit"}

    @property
    def boilerplate_contents(self) -> dict[str, str]:
        """Return known Yahoo Finance non-article boilerplates keyed by diagnostic name."""
        return {
            "yahoo_login": "Sign in to access your portfolio\n\nSign in",
            "coinbase_ad": (
                "Trading disclosure\n\n"
                "The above button links to Coinbase. Yahoo Finance is not a broker-dealer or "
                "investment adviser and does not offer securities or cryptocurrencies for sale "
                "or facilitate trading. Coinbase pays us for certain activity generated through "
                "this link. Prices displayed are informational."
            ),
        }

    async def run_fetch(self, executed_at: datetime) -> list[NewsModel]:
        """Fetch raw RSS feed and map to NewsModel entities without enrichment."""

        raw_feed = await self._fetch_feed()
        entries_data = raw_feed.get("entries") or []

        results: list[NewsModel] = []

        for entry_data in entries_data:
            try:
                entry = YahooFinanceEntrySchema.model_validate(entry_data)
            except Exception:
                continue

            published_at = self._parse_published_at(entry=entry)
            if published_at is None:
                continue

            thumbnail_url = None
            if entry.media_content:
                first_media = entry.media_content[0]
                if first_media.url:
                    thumbnail_url = first_media.url

            metadata_payload = entry.model_dump(exclude=self.rss_entry_storage_fields, mode="json")

            results.append(
                NewsModel(
                    executed_at=executed_at,
                    source=self.source,
                    title=entry.title,
                    entry_url=entry.link,
                    published_at=published_at,
                    thumbnail_url=thumbnail_url,
                    metadata=metadata_payload,
                )
            )

        return results

    def _parse_published_at(self, entry: YahooFinanceEntrySchema) -> datetime | None:
        """Return the RSS publication timestamp as a UTC datetime."""
        published_parsed = entry.published_parsed
        if not isinstance(published_parsed, (list, tuple)):
            return None
        try:
            return datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            return None
