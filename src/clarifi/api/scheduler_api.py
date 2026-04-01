"""Scheduler management API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.decision_log import SchedulerRun
from clarifi.models.scheduled_task import ScheduledTask

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/tasks")
async def list_tasks(active_only: bool = False):
    """List all scheduled tasks."""
    async with get_async_session() as session:
        q = select(ScheduledTask).order_by(ScheduledTask.next_run_at)
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
async def delete_task(task_id: str):
    """Deactivate a scheduled task."""
    async with get_async_session() as session:
        task = await session.get(ScheduledTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.is_active = False
        title = task.title
    return {"status": "deactivated", "task_id": task_id, "title": title}


@router.get("/runs")
async def list_runs(
    task_id: str | None = None,
    limit: int = Query(50, le=200),
):
    """List scheduler run history."""
    async with get_async_session() as session:
        q = select(SchedulerRun).order_by(SchedulerRun.started_at.desc())
        if task_id:
            q = q.where(SchedulerRun.task_id == task_id)
        runs = (await session.execute(q.limit(limit))).scalars().all()

    return {
        "runs": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "error_message": r.error_message,
            }
            for r in runs
        ]
    }
