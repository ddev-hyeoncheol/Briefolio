from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from google.cloud import firestore

from src.core.logger import get_logger

logger = get_logger(__name__)

# State documents expire after this window, mirroring the legacy BigQuery
# 7-day retry lookup window (TRANSITION.md 3.1).
STATE_TTL = timedelta(days=7)


class FirestoreProvider:
    """Thin wrapper around the Firestore async client for dedup state storage."""

    def __init__(self, client: firestore.AsyncClient) -> None:
        """Initialize the provider with a Firestore async client."""
        self.client = client

    async def get_statuses(self, collection: str, doc_ids: Sequence[str]) -> dict[str, str | None]:
        """Return the latest status for each doc_id in the collection, or None if the document doesn't exist."""
        if not doc_ids:
            return {}

        refs = [self.client.collection(collection).document(doc_id) for doc_id in doc_ids]
        statuses: dict[str, str | None] = {}
        async for snapshot in self.client.get_all(refs):
            statuses[snapshot.id] = (snapshot.to_dict() or {}).get("status")

        logger.info(
            "FirestoreProvider get_statuses completed | collection: %s, count: %d",
            collection,
            len(doc_ids),
        )
        return statuses

    async def set_states(self, collection: str, states: Mapping[str, Mapping[str, Any]]) -> None:
        """Overwrite each doc_id's state document with an appended TTL expiration timestamp."""
        if not states:
            return

        batch = self.client.batch()
        expires_at = datetime.now(tz=timezone.utc) + STATE_TTL
        for doc_id, state in states.items():
            ref = self.client.collection(collection).document(doc_id)
            batch.set(ref, {**state, "expires_at": expires_at})
        await batch.commit()

        logger.info(
            "FirestoreProvider set_states completed | collection: %s, count: %d",
            collection,
            len(states),
        )
