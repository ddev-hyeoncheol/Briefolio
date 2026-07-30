import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from google.cloud import firestore, storage

from src.config.config import settings
from src.core.logger import configure_uvicorn_loggers, get_logger
from src.ingest.router import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Ingest application startup and shutdown."""
    configure_uvicorn_loggers()

    # Create the shared enrich semaphore here so it is bound to the correct event loop.
    enrich_semaphore = asyncio.Semaphore(10)
    firestore_client = firestore.AsyncClient()
    storage_client = storage.Client()

    app.state.enrich_semaphore = enrich_semaphore
    app.state.firestore_client = firestore_client
    app.state.storage_client = storage_client
    logger.info("App startup completed | app: ingest")
    try:
        yield
    finally:
        firestore_client.close()
        storage_client.close()
        logger.info("App shutdown completed | app: ingest")


app = FastAPI(title="Briefolio Ingest App", lifespan=lifespan)

app.include_router(router)


@app.get("/")
async def root():
    """Return a welcome message."""
    return {"message": "Welcome to Briefolio Ingest App"}


@app.get("/health")
async def health_check():
    """Return health status for Cloud Run and Load Balancers to verify service availability."""
    return {"status": "healthy", "version": "1.0.0"}


def run_app() -> None:
    """Run the Ingest application with configured runtime settings."""
    import uvicorn

    uvicorn.run(
        "src.ingest.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=not settings.is_gcp,
    )


if __name__ == "__main__":
    run_app()
