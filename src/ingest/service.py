import asyncio
import json
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal

from src.ingest.models.ingest import IngestPhase, IngestResponse, IngestSourceResult
from src.ingest.models.news import NewsModel
from src.ingest.plugins.rss import RssPlugin
from src.ingest.providers.firestore import FirestoreProvider
from src.ingest.providers.storage import CloudStorageProvider

# Shared collection for entry and canonical URL deduplication state.
NEWS_STATE_COLLECTION = "news_state"


class IngestService:
    """Service that orchestrates source ingestion, deduplication, raw loading, and state recording."""

    def __init__(
        self,
        source_plugins: Sequence[RssPlugin],
        firestore_provider: FirestoreProvider,
        storage_provider: CloudStorageProvider,
    ) -> None:
        self.source_plugins = source_plugins
        self.firestore_provider = firestore_provider
        self.storage_provider = storage_provider

    async def run(self, executed_at: datetime) -> IngestResponse:
        """Run all source pipelines and aggregate their results."""
        executed_at = self._resolve_executed_at(executed_at=executed_at)
        # Each invocation is an independent append-only capture, so duplicate or
        # replayed invocations never overwrite an earlier capture's files.
        run_id = str(uuid.uuid4())
        started_at = datetime.now(tz=timezone.utc)

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

    async def _run_source(self, source_plugin: RssPlugin, executed_at: datetime, run_id: str) -> IngestSourceResult:
        """Run the complete Ingest pipeline for one source."""
        source = source_plugin.source
        started_at = datetime.now(tz=timezone.utc)
        current_phase: IngestPhase = "fetch"

        try:
            current_phase = "fetch"
            fetch_items = await source_plugin.run_fetch(executed_at=executed_at)

            # Before enrichment, news_id and entry_key identify the same RSS URL.
            current_phase = "entry_lookup"
            entry_retryable_items = await self._filter_retryable(items=fetch_items, key="entry_key")

            current_phase = "enrich"
            enriched_items = await source_plugin.run_enrich(items=entry_retryable_items)
            deduplicated_items, grouped_items = self._deduplicate_enriched_items(items=enriched_items)

            # Only canonical URLs that changed the key need a second lookup.
            current_phase = "news_lookup"
            rekeyed_items = [item for item in deduplicated_items if item.news_id != item.entry_key]
            news_retryable_items = await self._filter_retryable(items=rekeyed_items, key="news_id")

            # Items dropped here are duplicates of an already-successful article, so their
            # entry URLs are resolved immediately, without waiting for a load attempt.
            duplicate_keys = {item.news_id for item in rekeyed_items} - {
                item.news_id for item in news_retryable_items
            }
            duplicate_items = [item for item in deduplicated_items if item.news_id in duplicate_keys]
            final_items = [item for item in deduplicated_items if item.news_id not in duplicate_keys]

            has_enrich_failure = any(item.status != "success" for item in final_items)
            if duplicate_items:
                duplicate_states: dict[str, dict] = {}
                for item in duplicate_items:
                    for grouped_item in grouped_items[item.news_id]:
                        duplicate_states[grouped_item.entry_key] = self._create_state_doc(
                            item=grouped_item,
                            url=grouped_item.entry_url,
                            executed_at=executed_at,
                            status="success",
                        )
                await self.firestore_provider.set_states(
                    collection=NEWS_STATE_COLLECTION,
                    states=duplicate_states,
                )

            current_phase = "load"
            await self._load_news(source=source, executed_at=executed_at, run_id=run_id, items=final_items)

            # Write state only after a successful load so failed captures remain retryable.
            current_phase = "state_write"
            if final_items:
                states: dict[str, dict] = {}
                for item in final_items:
                    if not item.status:
                        continue
                    states[item.news_id] = self._create_state_doc(
                        item=item, url=item.canonical_url or item.entry_url, executed_at=executed_at, status=item.status
                    )
                    for grouped_item in grouped_items[item.news_id]:
                        if grouped_item.entry_key != item.news_id:
                            states[grouped_item.entry_key] = self._create_state_doc(
                                item=grouped_item,
                                url=grouped_item.entry_url,
                                executed_at=executed_at,
                                status=item.status,
                            )
                await self.firestore_provider.set_states(collection=NEWS_STATE_COLLECTION, states=states)

            status = "partial" if has_enrich_failure else "success"
            completed_at = datetime.now(tz=timezone.utc)
            elapsed_seconds = (completed_at - started_at).total_seconds()

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
        """Upload a JSONL capture and its manifest to the raw bucket."""
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

        return retryable_items

    def _deduplicate_enriched_items(
        self,
        items: Sequence[NewsModel],
    ) -> tuple[list[NewsModel], dict[str, list[NewsModel]]]:
        """Select one item per news_id while retaining every grouped entry URL."""
        selected_items: dict[str, NewsModel] = {}
        grouped_items: dict[str, list[NewsModel]] = {}

        for item in items:
            grouped_items.setdefault(item.news_id, []).append(item)
            selected_item = selected_items.get(item.news_id)
            if selected_item is None or (selected_item.status != "success" and item.status == "success"):
                selected_items[item.news_id] = item

        return list(selected_items.values()), grouped_items

    def _create_state_doc(self, item: NewsModel, url: str, executed_at: datetime, status: str) -> dict:
        """Return a news_state document payload for the given URL."""
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
