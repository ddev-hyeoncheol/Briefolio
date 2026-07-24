import asyncio

from fastapi import Request
from google.cloud import firestore, storage


def get_source_semaphore(request: Request) -> asyncio.Semaphore:
    """
    Return the shared source collection semaphore from FastAPI app state.
    Limit concurrent outgoing web requests across source plugins.
    """
    return request.app.state.source_semaphore


def get_firestore_client(request: Request) -> firestore.AsyncClient:
    """Return the shared Firestore async client from FastAPI app state."""
    return request.app.state.firestore_client


def get_storage_client(request: Request) -> storage.Client:
    """Return the shared Cloud Storage client from FastAPI app state."""
    return request.app.state.storage_client
