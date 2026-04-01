"""memU integration — direct Python usage (self-hosted via Supabase PostgreSQL).

memU (https://github.com/NevaMind-AI/memU) provides:
- 3-layer hierarchical memory (resources → items → categories)
- Proactive context retrieval
- Pattern detection across conversations
- Knowledge extraction from interactions

Uses Supabase PostgreSQL + pgvector as backend. No REST API needed.
"""

import logging

from clarifi.config import settings

logger = logging.getLogger(__name__)

_service = None


def get_memu_service():
    """Get or create the memU service singleton.

    Returns None if memU is not enabled or not installed.
    Uses Supabase PostgreSQL as backend with pgvector for embeddings.
    """
    global _service
    if not settings.memu_enabled:
        return None

    if _service is not None:
        return _service

    try:
        from memu import MemUService
    except ImportError:
        logger.warning(
            "memU not installed. Run: pip install memu-py[postgres]\n"
            "Or clone: git clone https://github.com/NevaMind-AI/memU.git && pip install -e './memU[postgres]'"
        )
        return None

    # Parse Supabase PostgreSQL URL into components for memU
    # DATABASE_URL format: postgresql+asyncpg://user:pass@host:port/db
    db_config = _parse_database_url(settings.database_url)
    if not db_config:
        logger.warning("memU requires PostgreSQL (Supabase). Current DATABASE_URL is not PostgreSQL.")
        return None

    api_key = settings.memu_llm_api_key or settings.google_api_key

    try:
        _service = MemUService(
            llm_profiles={
                "default": {
                    "base_url": settings.memu_llm_base_url,
                    "api_key": api_key,
                    "chat_model": settings.memu_llm_model,
                    "client_backend": "httpx",
                },
            },
            database_config={
                "metadata_store": {
                    "provider": "postgres",
                    "host": db_config["host"],
                    "port": db_config["port"],
                    "user": db_config["user"],
                    "password": db_config["password"],
                    "database": db_config["database"],
                    "vector_store": "pgvector",
                },
            },
        )
        logger.info("memU initialized with Supabase PostgreSQL (%s)", db_config["host"])
        return _service
    except Exception:
        logger.warning("memU initialization failed", exc_info=True)
        return None


def _parse_database_url(url: str) -> dict | None:
    """Parse a PostgreSQL URL into components for memU config."""
    if not url or "postgresql" not in url:
        return None

    # Remove driver prefix: postgresql+asyncpg:// → just the rest
    clean = url.split("://", 1)[-1]
    # user:pass@host:port/db
    try:
        userpass, hostdb = clean.split("@", 1)
        user, password = userpass.split(":", 1)
        hostport, database = hostdb.split("/", 1)
        if ":" in hostport:
            host, port_str = hostport.split(":", 1)
            port = int(port_str)
        else:
            host = hostport
            port = 5432
        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
        }
    except (ValueError, IndexError):
        return None


async def memorize(content: str, metadata: dict | None = None) -> dict:
    """Store a conversation turn in memU, scoped to a specific user.
    Each user has isolated memory — they never see other users' context."""
    service = get_memu_service()
    if not service:
        return {"status": "disabled"}

    user_id = (metadata or {}).get("user_id", "default")

    try:
        # Write content to a temp resource for memU to process
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            result = await service.memorize(
                resource_url=tmp_path,
                modality="conversation",
                user={"user_id": user_id},
            )
        finally:
            os.unlink(tmp_path)
        return {"status": "ok", "items": len(result.get("items", []))}
    except Exception:
        logger.warning("memU memorize failed (user=%s)", user_id, exc_info=True)
        return {"status": "error"}


async def retrieve(query: str, user_id: str = "default", limit: int = 5) -> list[dict]:
    """Retrieve relevant memories for a specific user.
    Memory is scoped per user — each user only sees their own context."""
    service = get_memu_service()
    if not service:
        return []

    try:
        result = await service.retrieve(
            queries=[{"role": "user", "content": {"text": query}}],
            where={"user_id": user_id},
            method="rag",
        )
        items = result.get("items", [])[:limit]
        return items
    except Exception:
        logger.warning("memU retrieve failed (user=%s)", user_id, exc_info=True)
        return []
