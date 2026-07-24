import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from google.cloud import firestore, storage

from src.config.config import settings
from src.core.logger import configure_uvicorn_loggers, get_logger
from src.worker.routers import ingest

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Worker application startup and shutdown."""
    configure_uvicorn_loggers()

    # Initialize shared resources on startup.
    # All semaphores are created here to ensure they are bound to the correct event loop.
    app.state.source_semaphore = asyncio.Semaphore(10)
    app.state.firestore_client = firestore.AsyncClient()
    app.state.storage_client = storage.Client()

    logger.info("App startup completed | app: worker")
    yield
    logger.info("App shutdown completed | app: worker")


app = FastAPI(title="Gemini News Brief Worker App", lifespan=lifespan)

app.include_router(ingest.router)


@app.get("/")
async def root():
    """Return a welcome message."""
    return {"message": "Welcome to Gemini News Brief Worker App"}


@app.get("/health")
async def health_check():
    """Return health status for Cloud Run and Load Balancers to verify service availability."""
    return {"status": "healthy", "version": "1.0.0"}


def run_app() -> None:
    """Run the Worker application with configured runtime settings."""
    import uvicorn

    uvicorn.run(
        "src.worker.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=not settings.is_gcp,
    )


if __name__ == "__main__":
    run_app()
