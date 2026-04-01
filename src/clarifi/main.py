import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clarifi.agent.graph import get_graph
from clarifi.api import chat, dashboard, documents, health
from clarifi.config import settings
from clarifi.api import decisions, documents_api, files, folders, integrations, onboarding, scheduler_api, settings_api
from clarifi.discovery.watcher import watch_directory
from clarifi.scheduler import run_scheduler_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = await get_graph()

    # Background tasks — run inside the server process
    scheduler_task = asyncio.create_task(run_scheduler_loop())
    watcher_task = asyncio.create_task(watch_directory())

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
