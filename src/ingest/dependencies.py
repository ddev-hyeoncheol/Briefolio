from fastapi import Request

from src.config.config import settings
from src.ingest.plugins.rss import RssPlugin
from src.ingest.plugins.sources.yahoo_finance import YahooFinanceSource
from src.ingest.providers.firestore import FirestoreProvider
from src.ingest.providers.storage import CloudStorageProvider
from src.ingest.service import IngestService

# Registry of enabled news source classes. Add a source class here to activate it.
ENABLED_SOURCE_CLASSES: tuple[type[RssPlugin], ...] = (YahooFinanceSource,)


def get_ingest_service(request: Request) -> IngestService:
    """Provide the IngestService assembled from shared application resources."""
    source_plugins = [
        source_cls(enrich_semaphore=request.app.state.enrich_semaphore) for source_cls in ENABLED_SOURCE_CLASSES
    ]
    firestore_provider = FirestoreProvider(client=request.app.state.firestore_client)
    storage_provider = CloudStorageProvider(
        client=request.app.state.storage_client,
        bucket_name=settings.raw_bucket_name,
    )

    return IngestService(
        source_plugins=source_plugins,
        firestore_provider=firestore_provider,
        storage_provider=storage_provider,
    )
