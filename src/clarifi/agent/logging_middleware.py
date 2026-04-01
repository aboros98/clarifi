"""Middleware that wraps tools with automatic decision logging.

Creates wrapper tools that log every call to decision_log table.
Does NOT mutate original tool objects (Pydantic v2 forbids setattr on models).
"""

import logging
import time
from datetime import datetime, timezone

from langchain_core.tools import StructuredTool

from clarifi.db.session import get_async_session
from clarifi.models.decision_log import DecisionLog

logger = logging.getLogger(__name__)

_cache: dict[str, StructuredTool] = {}


def _serialize_safe(obj, max_len: int = 5000):
    if obj is None:
        return None
    if isinstance(obj, dict):
        s = str(obj)
        return obj if len(s) < max_len else {"_truncated": s[:max_len]}
    if isinstance(obj, str):
        return obj[:max_len]
    return str(obj)[:max_len]


async def _log_tool_call(
    tool_name: str,
    tool_input: dict | None,
    tool_output: dict | str | None,
    duration_ms: int,
    session_id: str | None = None,
):
    try:
        async with get_async_session() as session:
            log = DecisionLog(
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                decision_type="tool_call",
                tool_name=tool_name,
                tool_input=_serialize_safe(tool_input),
                tool_output=_serialize_safe(tool_output),
                duration_ms=duration_ms,
            )
            session.add(log)
    except Exception:
        logger.debug("Decision log write failed", exc_info=True)


def wrap_tool_with_logging(tool, session_id: str | None = None):
    """Create a new tool that delegates to the original + logs the call.
    Returns a cached wrapper (idempotent per tool name)."""
    if tool.name in _cache:
        return _cache[tool.name]

    original_coroutine = tool.coroutine

    async def logged_func(**kwargs):
        start = time.monotonic()
        try:
            result = await original_coroutine(**kwargs)
            duration = int((time.monotonic() - start) * 1000)
            await _log_tool_call(
                tool_name=tool.name,
                tool_input=_serialize_safe(kwargs),
                tool_output=_serialize_safe(result),
                duration_ms=duration,
                session_id=session_id,
            )
            return result
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            await _log_tool_call(
                tool_name=tool.name,
                tool_input=_serialize_safe(kwargs),
                tool_output={"error": str(e)},
                duration_ms=duration,
                session_id=session_id,
            )
            raise

    wrapper = StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        coroutine=logged_func,
    )
    _cache[tool.name] = wrapper
    return wrapper


def wrap_tools_with_logging(tools: list, session_id: str | None = None) -> list:
    """Wrap all tools with logging. Cached — safe to call every turn."""
    return [wrap_tool_with_logging(t, session_id) for t in tools]
