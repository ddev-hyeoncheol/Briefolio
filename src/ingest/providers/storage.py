import asyncio

from google.cloud import storage


class CloudStorageProvider:
    """Provider for uploading raw ingestion objects to Cloud Storage."""

    def __init__(self, client: storage.Client, bucket_name: str) -> None:
        self.bucket = client.bucket(bucket_name)

    async def upload_text(self, path: str, content: str, content_type: str) -> None:
        """Upload text content to a Cloud Storage object."""
        await asyncio.to_thread(self._upload_text_sync, path, content, content_type)

    def _upload_text_sync(self, path: str, content: str, content_type: str) -> None:
        blob = self.bucket.blob(path)
        blob.upload_from_string(content, content_type=content_type)
