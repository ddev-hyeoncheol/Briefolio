from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from google.cloud import firestore

# Populate the expiration field used when Firestore TTL enforcement is enabled.
STATE_TTL = timedelta(days=7)


class FirestoreProvider:
    """Provider for reading and writing ingestion deduplication state in Firestore."""

    def __init__(self, client: firestore.AsyncClient) -> None:
        self.client = client

    async def get_statuses(self, collection: str, doc_ids: Sequence[str]) -> dict[str, str | None]:
        """Return each document's stored status, or None when the document does not exist."""
        if not doc_ids:
            return {}

        refs = [self.client.collection(collection).document(doc_id) for doc_id in doc_ids]
        statuses: dict[str, str | None] = {}
        async for snapshot in self.client.get_all(refs):
            statuses[snapshot.id] = (snapshot.to_dict() or {}).get("status")

        return statuses

    async def set_states(self, collection: str, states: Mapping[str, Mapping[str, Any]]) -> None:
        """Overwrite state documents after adding a shared TTL expiration timestamp."""
        if not states:
            return

        batch = self.client.batch()
        expires_at = datetime.now(tz=timezone.utc) + STATE_TTL
        for doc_id, state in states.items():
            ref = self.client.collection(collection).document(doc_id)
            batch.set(ref, {**state, "expires_at": expires_at})
        await batch.commit()
