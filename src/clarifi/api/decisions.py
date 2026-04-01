"""Decision log and audit trail API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from clarifi.db.session import get_async_session
from clarifi.models.decision_log import AgentSession, DecisionLog

router = APIRouter(prefix="/api", tags=["decisions"])


@router.get("/decisions")
async def list_decisions(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    decision_type: str | None = None,
    session_id: str | None = None,
):
    """List decision log entries with pagination and filtering."""
    async with get_async_session() as session:
        q = select(DecisionLog).order_by(DecisionLog.timestamp.desc())
        if decision_type:
            q = q.where(DecisionLog.decision_type == decision_type)
        if session_id:
            q = q.where(DecisionLog.session_id == session_id)

        total_q = select(func.count(DecisionLog.id))
        if decision_type:
            total_q = total_q.where(DecisionLog.decision_type == decision_type)
        total = (await session.execute(total_q)).scalar_one()

        decisions = (await session.execute(q.offset(offset).limit(limit))).scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "decisions": [
            {
                "id": d.id,
                "timestamp": d.timestamp.isoformat(),
                "decision_type": d.decision_type,
                "tool_name": d.tool_name,
                "tool_input": d.tool_input,
                "tool_output": d.tool_output,
                "reasoning": d.reasoning,
                "entity_type": d.entity_type,
                "entity_id": d.entity_id,
                "duration_ms": d.duration_ms,
                "session_id": d.session_id,
            }
            for d in decisions
        ],
    }


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str):
    """Get a single decision log entry with full details."""
    async with get_async_session() as session:
        d = await session.get(DecisionLog, decision_id)
        if not d:
            raise HTTPException(status_code=404, detail="Decision not found")
    return {
        "id": d.id,
        "timestamp": d.timestamp.isoformat(),
        "decision_type": d.decision_type,
        "tool_name": d.tool_name,
        "tool_input": d.tool_input,
        "tool_output": d.tool_output,
        "reasoning": d.reasoning,
        "entity_type": d.entity_type,
        "entity_id": d.entity_id,
        "duration_ms": d.duration_ms,
        "session_id": d.session_id,
    }


@router.get("/sessions")
async def list_sessions(limit: int = Query(20, le=100)):
    """List agent conversation sessions."""
    async with get_async_session() as session:
        sessions = (await session.execute(
            select(AgentSession)
            .order_by(AgentSession.started_at.desc())
            .limit(limit)
        )).scalars().all()

    return {
        "sessions": [
            {
                "id": s.id,
                "started_at": s.started_at.isoformat(),
                "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
                "message_count": s.message_count,
                "title": s.title,
                "status": s.status,
            }
            for s in sessions
        ]
    }
