"""Scheduling and reminder tools."""

from datetime import UTC, datetime, timedelta

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.agent.context import current_user_id
from clarifi.db.session import get_async_session
from clarifi.models.scheduled_task import ScheduledTask, ScheduleType


@tool
async def create_reminder(
    title: str,
    when: str,
    message: str,
    entity_type: str = "",
    entity_id: str = "",
    user_id: str = "",
    recurring: bool = False,
    cron: str = "",
) -> dict:
    """Creează un reminder programat. Agentul sau utilizatorul îl poate crea.
    Args:
        title — descriere scurtă
        when — dată ISO sau relativă: '7 days', '2026-04-15', '30 days'
        message — ce să spună agentul când reminder-ul se declanșează
        entity_type — opțional: 'folder', 'client', 'contract', 'invoice' (leagă de o entitate)
        entity_id — opțional: ID-ul entității (folder_id, company_id, contract_id)
        recurring — True pentru remindere recurente
        cron — expresie cron pentru recurente (ex: '0 8 * * 1' pentru luni 8:00)
    """
    now = datetime.now(UTC)

    # Parse 'when'
    if "day" in when.lower():
        try:
            days = int("".join(c for c in when if c.isdigit()))
        except ValueError:
            days = 1
        run_at = now + timedelta(days=days)
    else:
        try:
            run_at = datetime.fromisoformat(when)
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=UTC)
        except ValueError:
            run_at = now + timedelta(days=1)

    schedule_type = ScheduleType.RECURRING if recurring else ScheduleType.ONE_SHOT

    async with get_async_session() as session:
        task = ScheduledTask(
            task_type="reminder",
            title=title,
            schedule_type=schedule_type,
            cron_expression=cron if recurring else None,
            next_run_at=run_at,
            is_active=True,
            created_by_agent=True,
            trigger_flow_type="conversation",
            trigger_message=message,
            user_id=user_id or current_user_id.get() or None,
            related_entity_type=entity_type or None,
            related_entity_id=entity_id or None,
            notification_channels=["app"],
        )
        session.add(task)
        await session.flush()
        task_id = str(task.id)

    return {
        "status": "created",
        "task_id": task_id,
        "title": title,
        "next_run": run_at.isoformat(),
        "type": schedule_type.value,
    }


@tool
async def list_reminders() -> dict:
    """List all active scheduled reminders and tasks."""
    async with get_async_session() as session:
        q = select(ScheduledTask).where(ScheduledTask.is_active == True).order_by(ScheduledTask.next_run_at).limit(20)
        tasks = (await session.execute(q)).scalars().all()

    return {
        "count": len(tasks),
        "reminders": [
            {
                "id": str(t.id),
                "title": t.title,
                "type": t.schedule_type.value,
                "next_run": t.next_run_at.isoformat() if t.next_run_at else None,
                "cron": t.cron_expression,
                "run_count": t.run_count,
            }
            for t in tasks
        ],
    }


@tool
async def cancel_reminder(task_id: str) -> dict:
    """Cancel a scheduled reminder by its ID.
    Args: task_id — the reminder's ID from list_reminders."""
    async with get_async_session() as session:
        task = await session.get(ScheduledTask, task_id)
        if not task:
            return {"error": f"Reminder {task_id} not found"}
        task.is_active = False
        title = task.title
    return {"status": "cancelled", "task_id": task_id, "title": title}
