import asyncio
import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.decision_log import SchedulerRun
from clarifi.models.scheduled_task import ScheduledTask
from clarifi.tools.alerts import query_alerts
from clarifi.tools.finance import query_cashflow, query_receivables

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/kpis")
async def get_kpis():
    """Get a real-time KPI snapshot for the dashboard."""
    try:
        cashflow, receivables, alerts = await asyncio.gather(
            query_cashflow.ainvoke({}),
            query_receivables.ainvoke({"status": "all"}),
            query_alerts.ainvoke({}),
        )
    except Exception:
        logger.exception("KPI error in /dashboard/kpis")
        raise HTTPException(status_code=500, detail="Eroare la procesare. Incearca din nou.")
    # Recent agent activity (scheduler runs)
    recent_activity = []
    try:
        async with get_async_session() as session:
            runs = (await session.execute(
                select(SchedulerRun)
                .where(SchedulerRun.output.isnot(None))
                .order_by(SchedulerRun.started_at.desc())
                .limit(5)
            )).scalars().all()

            task_ids = {r.task_id for r in runs}
            tasks = {}
            if task_ids:
                rows = (await session.execute(
                    select(ScheduledTask).where(
                        ScheduledTask.id.in_(task_ids),
                    )
                )).scalars().all()
                tasks = {t.id: t.title for t in rows}

            for r in runs:
                output = r.output.get("response", "") if r.output else ""
                if output:
                    recent_activity.append({
                        "title": tasks.get(r.task_id, "Agent"),
                        "summary": output[:200],
                        "status": r.status,
                        "timestamp": r.started_at.isoformat(),
                    })
    except Exception:
        logger.debug("Failed to load recent activity", exc_info=True)

    return {
        "cashflow": cashflow,
        "receivables": receivables,
        "alerts": alerts,
        "recent_activity": recent_activity,
    }


@router.get("/alerts")
async def get_alerts():
    """Get active alerts."""
    try:
        return await query_alerts.ainvoke({})
    except Exception:
        logger.exception("Alert error in /alerts")
        raise HTTPException(status_code=500, detail="Eroare la procesare. Incearca din nou.")
