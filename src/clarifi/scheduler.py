"""Embedded scheduler — runs as a background task inside FastAPI.

Polls scheduled_tasks table every 60s, executes due tasks via the agent,
records results in scheduler_runs, and sends notifications.
"""

import asyncio
import logging
from datetime import datetime, timezone

from croniter import croniter
from langchain_core.messages import HumanMessage
from sqlalchemy import select

from clarifi.config import settings
from clarifi.db.session import async_session_factory, get_async_session
from clarifi.models.decision_log import SchedulerRun
from clarifi.models.scheduled_task import ScheduleType, ScheduledTask

logger = logging.getLogger("clarifi.scheduler")

POLL_INTERVAL = 60


class _TaskProxy:
    """Lightweight stand-in for ScheduledTask, used after session is closed."""

    __slots__ = ("id", "title", "trigger_message", "notification_channels", "user_id")

    def __init__(self, data: dict):
        self.id = data["id"]
        self.title = data["title"]
        self.trigger_message = data["trigger_message"]
        self.notification_channels = data["notification_channels"]
        self.user_id = data.get("user_id")


async def _send_notification(message: str, channels: list | None):
    """Send notification via configured channels."""
    if not channels:
        return

    if "telegram" in channels and settings.telegram_bot_token:
        try:
            import httpx

            # Send to all known Telegram chat IDs (stored in integration_configs)
            from clarifi.models.integration import IntegrationConfig

            async with get_async_session() as session:
                config = (await session.execute(
                    select(IntegrationConfig).where(
                        IntegrationConfig.provider == "telegram",
                        IntegrationConfig.status == "connected",
                    )
                )).scalar_one_or_none()

                chat_id = config.config.get("chat_id") if config and config.config else None

            if chat_id:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                        json={"chat_id": chat_id, "text": message[:4000], "parse_mode": "Markdown"},
                        timeout=10,
                    )
                logger.info("Telegram notification sent to chat %s", chat_id)
            else:
                logger.info("Telegram configured but no chat_id stored. Message: %s", message[:100])
        except Exception:
            logger.warning("Telegram notification failed", exc_info=True)


async def _execute_task(task: ScheduledTask) -> tuple[str, str | None]:
    """Execute a single scheduled task via the agent graph."""
    from clarifi.agent.graph import get_graph
    from clarifi.api.chat import extract_ai_response

    graph = await get_graph()
    user_id = task.user_id or "scheduler"
    input_state = {
        "messages": [HumanMessage(content=task.trigger_message)],
        "user_id": user_id,
    }

    result = await graph.ainvoke(
        input_state,
        config={"configurable": {"thread_id": f"{user_id}:scheduler-{task.id}"}},
    )

    response = extract_ai_response(result)

    await _send_notification(
        f"[{task.title}] {response[:500]}",
        task.notification_channels if isinstance(task.notification_channels, list) else None,
    )

    return "success", response, None


async def process_due_tasks():
    """Find due tasks, execute them OUTSIDE the session, then record results."""
    now = datetime.now(timezone.utc)

    # Step 1: Fetch due tasks and collect their data
    task_data = []
    async with async_session_factory() as session:
        q = (
            select(ScheduledTask)
            .where(ScheduledTask.is_active == True, ScheduledTask.next_run_at <= now)
            .order_by(ScheduledTask.next_run_at)
            .limit(10)
        )
        tasks = (await session.execute(q)).scalars().all()
        if not tasks:
            return 0

        logger.info("Found %d due task(s)", len(tasks))

        # Snapshot task data so we can release the session
        for t in tasks:
            task_data.append({
                "id": t.id,
                "title": t.title,
                "task_type": t.task_type,
                "trigger_message": t.trigger_message,
                "schedule_type": t.schedule_type,
                "cron_expression": t.cron_expression,
                "run_count": t.run_count,
                "max_runs": t.max_runs,
                "notification_channels": t.notification_channels,
                "user_id": t.user_id,
            })

    # Step 2: Execute tasks WITHOUT holding a DB session
    results = []
    for td in task_data:
        started_at = datetime.now(timezone.utc)
        status = "failed"
        error_msg = None
        response = None

        try:
            logger.info("Executing: %s (type=%s)", td["title"], td["task_type"])
            status, response, error_msg = await _execute_task(_TaskProxy(td))
            logger.info("  Completed: %s", status)
        except Exception as e:
            error_msg = str(e)
            logger.exception("  Failed: %s", td["title"])

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        results.append((td, started_at, completed_at, status, response, error_msg, duration_ms))

    # Step 3: Record results and update tasks in a fresh session
    async with async_session_factory() as session:
        for td, started_at, completed_at, status, response, error_msg, duration_ms in results:
            # Record run with agent output
            run = SchedulerRun(
                task_id=td["id"],
                started_at=started_at,
                completed_at=completed_at,
                status=status,
                duration_ms=duration_ms,
                error_message=error_msg,
                output={"response": response[:2000]} if response else None,
            )
            session.add(run)

            # Update task
            task = await session.get(ScheduledTask, td["id"])
            if task:
                task.last_run_at = now
                task.run_count = td["run_count"] + 1

                if td["schedule_type"] == ScheduleType.ONE_SHOT:
                    task.is_active = False
                elif td["schedule_type"] == ScheduleType.RECURRING and td["cron_expression"]:
                    cron = croniter(td["cron_expression"], now)
                    next_dt = cron.get_next(datetime)
                    # Ensure tz-aware (croniter may return naive)
                    if next_dt.tzinfo is None:
                        next_dt = next_dt.replace(tzinfo=timezone.utc)
                    task.next_run_at = next_dt
                    logger.info("  Next run: %s", task.next_run_at)

                if td["max_runs"] and task.run_count >= td["max_runs"]:
                    task.is_active = False

        await session.commit()

    return len(results)


async def run_scheduler_loop():
    """Main scheduler loop — runs as a background task in FastAPI."""
    logger.info("Scheduler started (polling every %ds)", POLL_INTERVAL)

    while True:
        try:
            count = await process_due_tasks()
            if count:
                logger.info("Processed %d task(s)", count)
        except asyncio.CancelledError:
            logger.info("Scheduler stopped")
            break
        except Exception:
            logger.exception("Scheduler loop error")

        await asyncio.sleep(POLL_INTERVAL)
