import asyncio

from google.cloud import storage

from src.core.logger import get_logger

logger = get_logger(__name__)


class CloudStorageProvider:
    """Thin wrapper around the Cloud Storage client for raw bucket writes."""

    def __init__(self, client: storage.Client, bucket_name: str) -> None:
        """Initialize the provider with a Storage client and target bucket."""
        self.bucket = client.bucket(bucket_name)

    async def upload_text(self, path: str, content: str, content_type: str) -> None:
        """Upload text content to the given object path in the bucket."""
        await asyncio.to_thread(self._upload_text_sync, path, content, content_type)

        logger.info(
            "CloudStorageProvider upload_text completed | bucket: %s, path: %s, size: %d",
            self.bucket.name,
            path,
            len(content),
        )

    def _upload_text_sync(self, path: str, content: str, content_type: str) -> None:
        """Upload text content synchronously (runs in a worker thread)."""
        blob = self.bucket.blob(path)
        blob.upload_from_string(content, content_type=content_type)
