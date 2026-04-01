"""File watcher — monitors a local directory for new documents.

Flow:
1. New file appears in inbox/
2. Watcher picks it up → triggers background agent
3. Agent: parses, extracts, organizes into virtual folder tree, creates reminders
4. Original file removed from inbox/ (data is now in DB + Supabase Storage)

The organization happens in the VIRTUAL FOLDER TREE (database), not in filesystem directories.
The inbox/ is just a drop zone — files leave it once processed.
"""

import asyncio
import logging
import time
from pathlib import Path

from langchain_core.messages import HumanMessage

from clarifi.config import settings

logger = logging.getLogger("clarifi.watcher")

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".txt",
    ".png", ".jpg", ".jpeg", ".tiff",
    ".csv", ".xlsx", ".xls",
}

_failed_files: dict[str, float] = {}  # path → time.monotonic() of last failure
_RETRY_COOLDOWN = 300  # 5 minutes


async def process_file(file_path: Path) -> bool:
    """Process a file through the background agent. Returns True if successful."""
    try:
        logger.info("New file: %s", file_path.name)

        from clarifi.agent.graph import get_graph

        graph = await get_graph()

        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("Europe/Bucharest"))
        timestamp = now.strftime("%d.%m.%Y, %H:%M")

        message = (
            f"[{timestamp}] Document nou: {file_path.name} (la {file_path}). "
            f"Parsează-l, extrage datele, organizează-l în folder-ul potrivit, "
            f"și creează remindere pentru deadline-uri."
        )

        await asyncio.wait_for(
            graph.ainvoke(
                {
                    "messages": [HumanMessage(content=message)],
                    "user_id": "background-agent",
                    "mode": "background",
                },
                config={"configurable": {"thread_id": f"watcher-{file_path.name}"}},
            ),
            timeout=300,
        )

        # Remove original from inbox — data is now in DB
        file_path.unlink(missing_ok=True)
        logger.info("Done: %s", file_path.name)
        return True

    except asyncio.TimeoutError:
        logger.error("Timeout (>300s): %s", file_path.name)
        return False
    except Exception:
        logger.exception("Failed: %s", file_path.name)
        return False


async def watch_directory(
    watch_dir: str | None = None,
    poll_interval: int = 10,
) -> None:
    """Poll inbox/ for new files. Trigger background agent for each."""
    inbox = Path(watch_dir or settings.watch_dir)
    inbox.mkdir(parents=True, exist_ok=True)

    logger.info("Watcher started: %s (poll every %ds)", inbox, poll_interval)

    while True:
        try:
            now_mono = time.monotonic()

            # Clean up old entries from _failed_files (older than 1 hour)
            stale = [
                p for p, t in _failed_files.items()
                if now_mono - t > 3600
            ]
            for p in stale:
                del _failed_files[p]

            new_files = [
                f for f in inbox.iterdir()
                if f.is_file()
                and f.suffix.lower() in SUPPORTED_EXTENSIONS
                and _failed_files.get(str(f), 0) + _RETRY_COOLDOWN < now_mono
            ]

            if new_files:
                logger.info("Found %d new file(s)", len(new_files))
                for f in new_files:
                    if not await process_file(f):
                        _failed_files[str(f)] = time.monotonic()

        except asyncio.CancelledError:
            logger.info("Watcher stopped")
            break
        except Exception:
            logger.exception("Watcher error")

        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(watch_directory())
