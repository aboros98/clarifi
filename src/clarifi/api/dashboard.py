import asyncio

from fastapi import APIRouter, HTTPException

from clarifi.tools.alerts import query_alerts
from clarifi.tools.finance import query_cashflow, query_receivables

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KPI error: {e}")
    return {"cashflow": cashflow, "receivables": receivables, "alerts": alerts}


@router.get("/alerts")
async def get_alerts():
    """Get active alerts."""
    try:
        return await query_alerts.ainvoke({})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert error: {e}")
