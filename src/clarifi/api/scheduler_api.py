"""Scheduler management API endpoints."""

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from clarifi.agent.context import current_user_id
from clarifi.api.chat import _extract_user_id
from clarifi.db.session import get_async_session
from clarifi.models.decision_log import SchedulerRun
from clarifi.models.scheduled_task import ScheduledTask

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/tasks")
async def list_tasks(request: Request, active_only: bool = False):
    """List scheduled tasks for the authenticated user."""
    user_id = _extract_user_id(request)
    current_user_id.set(user_id)

    async with get_async_session() as session:
        q = select(ScheduledTask).where(ScheduledTask.user_id == user_id).order_by(ScheduledTask.next_run_at)
        if active_only:
            q = q.where(ScheduledTask.is_active == True)
        tasks = (await session.execute(q)).scalars().all()

    return {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "task_type": t.task_type,
                "schedule_type": t.schedule_type.value,
                "cron_expression": t.cron_expression,
                "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
                "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
                "run_count": t.run_count,
                "is_active": t.is_active,
                "created_by_agent": t.created_by_agent,
                "trigger_message": t.trigger_message,
            }
            for t in tasks
        ]
    }


@router.delete("/tasks/{task_id}")
async def delete_task(request: Request, task_id: str):
    """Deactivate a scheduled task."""
    user_id = _extract_user_id(request)
    current_user_id.set(user_id)

    async with get_async_session() as session:
        task = await session.get(ScheduledTask, task_id)
        if not task or task.user_id != user_id:
            raise HTTPException(status_code=404, detail="Task not found")
        task.is_active = False
        title = task.title
    return {"status": "deactivated", "task_id": task_id, "title": title}


@router.get("/runs")
async def list_runs(
    request: Request,
    task_id: str | None = None,
    limit: int = Query(50, le=200),
):
    """List scheduler run history for the authenticated user's tasks."""
    user_id = _extract_user_id(request)
    current_user_id.set(user_id)

    async with get_async_session() as session:
        # Get task IDs owned by this user to scope runs
        user_task_ids_q = select(ScheduledTask.id).where(ScheduledTask.user_id == user_id)
        user_task_ids = set((await session.execute(user_task_ids_q)).scalars().all())

        q = select(SchedulerRun).where(
            SchedulerRun.task_id.in_(user_task_ids)
        ).order_by(SchedulerRun.started_at.desc())
        if task_id:
            if task_id not in user_task_ids:
                return {"runs": []}
            q = q.where(SchedulerRun.task_id == task_id)
        runs = (await session.execute(q.limit(limit))).scalars().all()

        # Fetch task titles for display
        run_task_ids = {r.task_id for r in runs}
        tasks = {}
        if run_task_ids:
            task_rows = (await session.execute(
                select(ScheduledTask).where(ScheduledTask.id.in_(run_task_ids))
            )).scalars().all()
            tasks = {t.id: t.title for t in task_rows}

    return {
        "runs": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "task_title": tasks.get(r.task_id, ""),
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "error_message": r.error_message,
                "output": r.output.get("response", "") if r.output else None,
            }
            for r in runs
        ]
    }
