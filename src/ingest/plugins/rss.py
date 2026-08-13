import asyncio
import random
from abc import ABC, abstractmethod
from datetime import datetime

import feedparser
import httpx
import newspaper
from tenacity import retry, retry_if_result, stop_after_attempt, wait_fixed

from src.config.config import settings
from src.core.transient import is_transient_http_status_code
from src.ingest.models.news import NewsModel
from src.ingest.models.sources.common import ArticleEnrichmentSchema

_retry = retry(
    retry=retry_if_result(lambda res: is_transient_http_status_code(res[0])),
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry_error_callback=lambda retry_state: retry_state.outcome.result() if retry_state.outcome else None,
)


class RssPlugin(ABC):
    """Abstract plugin for RSS fetching and article enrichment."""

    @property
    @abstractmethod
    def source(self) -> str:
        """Return the news source identifier."""
        pass

    @property
    @abstractmethod
    def rss_url(self) -> str:
        """Return the base RSS feed URL."""
        pass

    @property
    def rss_entry_storage_fields(self) -> set[str]:
        """Return DTO fields mapped to first-class storage columns and excluded from metadata dumps."""
        return set()

    @property
    def rss_entry_metadata_fields(self) -> set[str]:
        """Return known source RSS fields intended for metadata after DTO mapping."""
        return set()

    @property
    def rss_entry_ignored_fields(self) -> set[str]:
        """Return RSS fields intentionally ignored by this source."""
        return set()

    @property
    def rss_entry_known_fields(self) -> set[str]:
        """Return all known top-level RSS entry fields."""
        return self.rss_entry_storage_fields | self.rss_entry_metadata_fields | self.rss_entry_ignored_fields

    @property
    def boilerplate_contents(self) -> dict[str, str]:
        """Return exact non-article boilerplate content keyed by diagnostic name."""
        return {}

    def __init__(self, enrich_semaphore: asyncio.Semaphore) -> None:
        self._enrich_semaphore = enrich_semaphore
        self._user_agent = settings.user_agent
        self._newspaper_config = newspaper.Config()

    @abstractmethod
    async def run_fetch(self, executed_at: datetime) -> list[NewsModel]:
        """Fetch raw RSS feed and map to NewsModel entities without enrichment."""
        pass

    async def run_enrich(self, items: list[NewsModel]) -> list[NewsModel]:
        """
        Enrich targeted items with full article content in parallel.

        HTTP and parsing errors are isolated into top-level diagnostics,
        known source boilerplates are marked as failed item diagnostics,
        and other successful items continue.
        """
        if not items:
            return []

        tasks = [self._enrich_article(item.entry_url) for item in items]
        enrichments = await asyncio.gather(*tasks)

        enriched_items: list[NewsModel] = []

        for item, enriched in zip(items, enrichments):
            content = enriched.content
            status_code = enriched.status_code
            error_message = enriched.error_message

            if content is not None:
                content = content.strip() or None

            if (bp_name := self._find_matching_boilerplate(content)) is not None:
                content = None
                if error_message is None:
                    error_message = f"Content unavailable::boilerplate content::{bp_name}"

            if status_code == 200 and content:
                status = "success"
            else:
                status = "failed"
                if error_message is None:
                    error_message = (
                        f"HTTP status not OK::status_code={status_code}"
                        if status_code != 200
                        else "Content unavailable::empty content"
                    )

            update_fields = enriched.model_dump(exclude={"status_code", "error_message"})
            update_fields.update(
                {
                    "content": content,
                    "status": status,
                    "status_code": status_code,
                    "error_message": error_message,
                }
            )

            new_item = item.model_copy(update=update_fields)
            enriched_items.append(new_item)

        return enriched_items

    def _find_matching_boilerplate(self, content: str | None) -> str | None:
        """Return the diagnostic name for exact boilerplate content matches."""
        if content is None:
            return None
        for name, boilerplate in self.boilerplate_contents.items():
            if content == boilerplate:
                return name
        return None

    async def _fetch_feed(self) -> feedparser.FeedParserDict:
        """Fetch raw RSS feed using feedparser and validate HTTP status."""
        feed = await asyncio.to_thread(feedparser.parse, self.rss_url, agent=self._user_agent)

        status = feed.get("status")
        if status is None:
            raise RuntimeError("RSS fetch failed::missing status_code")

        if status != 200:
            raise RuntimeError(f"RSS fetch failed::status_code={status}")

        return feed

    async def _enrich_article(self, url: str) -> ArticleEnrichmentSchema:
        """Fetch and parse one article while preserving item-level diagnostics."""
        status_code, html, error_message = await self._fetch_html(url)

        if status_code == 200 and html:
            try:
                parsed = await asyncio.to_thread(self._parse_article_html, url, html)
                return parsed.model_copy(update={"status_code": status_code, "error_message": error_message})
            except Exception as e:
                error_message = f"Parsing failed::{type(e).__name__}::{e}"

        return ArticleEnrichmentSchema(
            status_code=status_code,
            error_message=error_message,
        )

    @_retry
    async def _fetch_html(self, url: str) -> tuple[int | None, str | None, str | None]:
        """Fetch HTML content asynchronously with transient failure retries."""
        try:
            # Jitter each attempt to reduce bursty requests against article hosts.
            await asyncio.sleep(random.uniform(0.1, 0.5))
            async with self._enrich_semaphore:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url, headers={"User-Agent": self._user_agent}, timeout=10.0)
                    return response.status_code, response.text, None
        except Exception as e:
            return None, None, f"Network error::{type(e).__name__}::{e}"

    def _parse_article_html(self, url: str, html: str) -> ArticleEnrichmentSchema:
        """Extract text and metadata from raw HTML synchronously using newspaper4k."""
        article = newspaper.Article(url, config=self._newspaper_config)
        article.html = html
        article.parse()

        authors = getattr(article, "authors", None)
        canonical_url = getattr(article, "canonical_link", None) or None
        image_url = getattr(article, "top_image", None) or None
        language = getattr(article, "meta_lang", None) or None
        content = getattr(article, "text", None) or None

        return ArticleEnrichmentSchema(
            authors="|".join(authors) if authors else None,
            canonical_url=canonical_url,
            image_url=image_url,
            language=language,
            content=content,
        )
