import asyncio
import json
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends
from google.cloud import firestore, storage

from src.config.config import settings
from src.core.dependencies import get_firestore_client, get_source_semaphore, get_storage_client
from src.core.logger import get_logger
from src.models.entities.news import NewsModel
from src.models.schemas.ingest import IngestPhase, IngestResponse, IngestSourceResult
from src.worker.plugins.rss_source import RssSource
from src.worker.plugins.sources.yahoo_finance import YahooFinanceSource
from src.worker.providers.firestore import FirestoreProvider
from src.worker.providers.storage import CloudStorageProvider

logger = get_logger(__name__)

# Registry of enabled news source classes. Add a source class here to activate it.
ENABLED_SOURCE_CLASSES: tuple[type[RssSource], ...] = (YahooFinanceSource,)

# Firestore collection holding per-URL dedup state documents (TRANSITION.md 3.1).
NEWS_STATE_COLLECTION = "news_state"


class IngestService:
    """Ingest service that fetches news from sources and loads the raw bucket."""

    def __init__(
        self,
        source_plugins: Sequence[RssSource],
        firestore_provider: FirestoreProvider,
        storage_provider: CloudStorageProvider,
    ) -> None:
        """Initialize the ingest service with required source plugins and providers."""
        self.source_plugins = source_plugins
        self.firestore_provider = firestore_provider
        self.storage_provider = storage_provider

    async def run(self, executed_at: datetime) -> IngestResponse:
        """Fetch news from all sources and load to the raw bucket."""
        executed_at = self._resolve_executed_at(executed_at=executed_at)
        # Each invocation is an independent append-only capture, so duplicate or
        # replayed invocations never overwrite an earlier capture's files.
        run_id = str(uuid.uuid4())
        started_at = datetime.now(tz=timezone.utc)
        logger.info("IngestService ingest started | executed_at: %s, run_id: %s", executed_at.isoformat(), run_id)

        source_results = await asyncio.gather(
            *[
                self._run_source(source_plugin=plugin, executed_at=executed_at, run_id=run_id)
                for plugin in self.source_plugins
            ]
        )

        count = sum(r.count for r in source_results)

        if not source_results or all(r.status == "success" for r in source_results):
            overall_status = "success"
        elif all(r.status == "failed" for r in source_results):
            overall_status = "failed"
        else:
            overall_status = "partial"

        completed_at = datetime.now(tz=timezone.utc)
        elapsed_seconds = (completed_at - started_at).total_seconds()
        logger.info(
            "IngestService ingest completed | executed_at: %s, status: %s, count: %d, elapsed: %.2fs",
            executed_at.isoformat(),
            overall_status,
            count,
            elapsed_seconds,
        )

        return IngestResponse(
            executed_at=executed_at,
            run_id=run_id,
            status=overall_status,
            count=count,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_seconds=elapsed_seconds,
            details=source_results,
        )

    async def _run_source(self, source_plugin: RssSource, executed_at: datetime, run_id: str) -> IngestSourceResult:
        """Process a single source pipeline from RSS fetch to raw bucket load."""
        source = source_plugin.source
        started_at = datetime.now(tz=timezone.utc)
        current_phase: IngestPhase = "fetch"
        logger.info(
            "IngestService source started | executed_at: %s, source: %s",
            executed_at.isoformat(),
            source,
        )

        try:
            # 1. Fetch
            current_phase = "fetch"
            fetch_items = await source_plugin.run_fetch(executed_at=executed_at)

            # 2. Entry lookup (news_id equals entry_key before enrich)
            current_phase = "entry_lookup"
            lookup_items = await self._filter_retryable(items=fetch_items, key="entry_key")

            # 3. Enrich
            current_phase = "enrich"
            enriched_items = await source_plugin.run_enrich(items=lookup_items)

            # 4. News lookup: only items whose canonical URL moved the key need a fresh check.
            current_phase = "news_lookup"
            changed_items = [item for item in enriched_items if item.news_id != item.entry_key]
            retryable_items = await self._filter_retryable(items=changed_items, key="news_id")

            # Items dropped here are duplicates of an already-successful article, so their
            # entry URL is resolved immediately, without waiting for a load attempt.
            duplicate_keys = {item.news_id for item in changed_items} - {item.news_id for item in retryable_items}
            duplicate_items = [item for item in enriched_items if item.news_id in duplicate_keys]
            final_items = [item for item in enriched_items if item.news_id not in duplicate_keys]

            # Detect item-level enrich failures among the items this run will load.
            has_enrich_failure = any(item.status != "success" for item in final_items)
            if duplicate_items:
                await self.firestore_provider.set_states(
                    collection=NEWS_STATE_COLLECTION,
                    states={
                        item.entry_key: self._create_state_doc(
                            item=item, url=item.entry_url, executed_at=executed_at, status="success"
                        )
                        for item in duplicate_items
                    },
                )

            # 5. Load
            current_phase = "load"
            await self._load_news(source=source, executed_at=executed_at, run_id=run_id, items=final_items)

            # 6. State write: runs only after a successful load, so absent state records
            # always mean the next invocation retries these items.
            current_phase = "state_write"
            if final_items:
                states: dict[str, dict] = {}
                for item in final_items:
                    if not item.status:
                        continue
                    states[item.news_id] = self._create_state_doc(
                        item=item, url=item.canonical_url or item.entry_url, executed_at=executed_at, status=item.status
                    )
                    if item.entry_key != item.news_id:
                        states[item.entry_key] = self._create_state_doc(
                            item=item, url=item.entry_url, executed_at=executed_at, status=item.status
                        )
                await self.firestore_provider.set_states(collection=NEWS_STATE_COLLECTION, states=states)

            status = "partial" if has_enrich_failure else "success"
            completed_at = datetime.now(tz=timezone.utc)
            elapsed_seconds = (completed_at - started_at).total_seconds()
            logger.info(
                "IngestService source completed | executed_at: %s, source: %s, status: %s, count: %d, elapsed: %.2fs",
                executed_at.isoformat(),
                source,
                status,
                len(final_items),
                elapsed_seconds,
            )

            return IngestSourceResult(
                source=source,
                executed_at=executed_at,
                status=status,
                count=len(final_items),
                started_at=started_at,
                completed_at=completed_at,
                elapsed_seconds=elapsed_seconds,
            )
        except Exception as e:
            completed_at = datetime.now(tz=timezone.utc)
            elapsed_seconds = (completed_at - started_at).total_seconds()
            logger.exception(
                "IngestService source failed | executed_at: %s, source: %s, failed_phase: %s, elapsed: %.2fs, error: %s",
                executed_at.isoformat(),
                source,
                current_phase,
                elapsed_seconds,
                str(e),
            )
            return IngestSourceResult(
                source=source,
                executed_at=executed_at,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                elapsed_seconds=elapsed_seconds,
                failed_phase=current_phase,
                error_message=f"{type(e).__name__}::{e}",
            )

    async def _load_news(
        self,
        source: str,
        executed_at: datetime,
        run_id: str,
        items: Sequence[NewsModel],
    ) -> None:
        """Upload a JSONL capture and its manifest to the raw bucket (TRANSITION.md 3.2)."""
        # Segments follow containment: a slot holds invocations, an invocation holds
        # per-source captures. Date/hour scans use executed_at value prefixes.
        partition = f"executed_at={executed_at.strftime('%Y%m%dT%H%M%SZ')}/run_id={run_id}"

        manifest_content = json.dumps(
            {
                "source": source,
                "run_id": run_id,
                "executed_at": executed_at.isoformat(),
                "count": len(items),
            }
        )

        # The manifest is written last so its presence signals a complete capture.
        # An empty capture skips the data file but still records the manifest as its execution trace.
        if items:
            jsonl_content = "\n".join(item.model_dump_json() for item in items)
            await self.storage_provider.upload_text(
                path=f"news/data/{partition}/source={source}.jsonl",
                content=jsonl_content,
                content_type="application/jsonl",
            )
        await self.storage_provider.upload_text(
            path=f"news/manifests/{partition}/source={source}.json",
            content=manifest_content,
            content_type="application/json",
        )

    async def _filter_retryable(
        self,
        items: Sequence[NewsModel],
        key: Literal["entry_key", "news_id"],
    ) -> list[NewsModel]:
        """Return items whose dedup status is not yet 'success' (missing or failed)."""
        if not items:
            return []

        doc_ids = [getattr(item, key) for item in items]
        statuses = await self.firestore_provider.get_statuses(collection=NEWS_STATE_COLLECTION, doc_ids=doc_ids)
        retryable_items = [item for item in items if statuses.get(getattr(item, key)) != "success"]

        logger.info(
            "IngestService filter_retryable completed | lookup_key: %s, count: %d, retryable_count: %d",
            key,
            len(items),
            len(retryable_items),
        )
        return retryable_items

    def _create_state_doc(self, item: NewsModel, url: str, executed_at: datetime, status: str) -> dict:
        """Return a news_state document payload for the given URL key."""
        doc: dict = {
            "status": status,
            "url": url,
            "source": item.source,
            "executed_at": executed_at,
        }
        if status == "failed" and item.error_message:
            doc["error_message"] = item.error_message
        return doc

    def _resolve_executed_at(self, executed_at: datetime) -> datetime:
        """Return the normalized execution time floored to the nearest 10-minute UTC."""
        utc_dt = executed_at.astimezone(timezone.utc)
        return utc_dt.replace(second=0, microsecond=0, minute=(utc_dt.minute // 10) * 10)


def get_ingest_service(
    source_semaphore: asyncio.Semaphore = Depends(get_source_semaphore),
    firestore_client: firestore.AsyncClient = Depends(get_firestore_client),
    storage_client: storage.Client = Depends(get_storage_client),
) -> IngestService:
    """Provide FastAPI dependency for IngestService."""
    source_plugins = [source_cls(semaphore=source_semaphore) for source_cls in ENABLED_SOURCE_CLASSES]
    firestore_provider = FirestoreProvider(client=firestore_client)
    storage_provider = CloudStorageProvider(client=storage_client, bucket_name=settings.raw_bucket_name)

    return IngestService(
        source_plugins=source_plugins,
        firestore_provider=firestore_provider,
        storage_provider=storage_provider,
    )
