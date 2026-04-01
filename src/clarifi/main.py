import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clarifi.agent.graph import close_graph, get_graph
from clarifi.api import (
    chat,
    dashboard,
    decisions,
    documents,
    documents_api,
    files,
    folders,
    health,
    integrations,
    onboarding,
    scheduler_api,
    settings_api,
)
from clarifi.config import settings
from clarifi.discovery.watcher import watch_directory
from clarifi.scheduler import run_scheduler_loop

# ── Structured logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
# Quiet noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("langgraph").setLevel(logging.WARNING)

logger = logging.getLogger("clarifi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Clarifi (model=%s, db=%s)",
                settings.llm_model, settings.database_url[:40])

    app.state.graph = await get_graph()
    logger.info("Agent graph compiled")

    # Background tasks — run inside the server process
    scheduler_task = asyncio.create_task(run_scheduler_loop())
    watcher_task = asyncio.create_task(watch_directory())
    logger.info("Background tasks started (scheduler + watcher)")

    yield

    scheduler_task.cancel()
    watcher_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass
    await close_graph()
    logger.info("Clarifi stopped")


app = FastAPI(
    title="Clarifi",
    description="AI financial assistant for services companies",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core endpoints
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(dashboard.router)

# Dashboard API endpoints
app.include_router(decisions.router)
app.include_router(scheduler_api.router)
app.include_router(folders.router)
app.include_router(documents_api.router)
app.include_router(integrations.router)
app.include_router(onboarding.router)
app.include_router(files.router)
app.include_router(settings_api.router)
