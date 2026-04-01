"""Per-request context variables for the agent execution.

Uses Python's contextvars so that values set in the graph node
are automatically visible to any tool coroutine called within
the same async task — no need to change tool signatures.
"""

from contextvars import ContextVar

# Set in react_agent_node before agent.ainvoke(); read by tools.
current_user_id: ContextVar[str] = ContextVar("current_user_id", default="anonymous")
