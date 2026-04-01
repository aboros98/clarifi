import json
import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


TOOL_LABELS = {
    "query_cashflow": "Verific cashflow-ul",
    "query_receivables": "Verific creantele",
    "query_profitability": "Verific profitabilitatea",
    "query_invoices": "Caut facturi",
    "query_contracts": "Verific contracte",
    "query_milestones": "Verific milestone-uri",
    "query_alerts": "Verific alerte",
    "query_transactions": "Caut tranzactii",
    "extract_fields": "Extrag date din document",
    "save_extracted_data": "Salvez date",
    "ingest_document": "Procesez document",
    "calculate": "Calculez",
    "discover_data": "Verific ce date exista",
    "search_data": "Caut in baza de date",
    "score_client_risk": "Evaluez riscul clientului",
    "detect_unissued_invoices": "Verific facturi neemise",
    "project_cashflow_daily": "Proiectez cashflow",
    "create_reminder": "Creez reminder",
    "create_folder": "Creez folder",
    "move_file": "Organizez fisier",
}


def extract_ai_response(result: dict) -> str:
    """Extract the last AI message content from agent result.
    Handles both string content and Gemini's list-of-parts format."""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            content = msg.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = []
                for part in content:
                    if isinstance(part, dict) and part.get("text"):
                        texts.append(part["text"])
                    elif isinstance(part, str):
                        texts.append(part)
                if texts:
                    return "\n".join(texts)
            return str(content)
    return ""


def extract_tool_calls(result: dict) -> list[str]:
    """Extract tool names called during agent execution."""
    tools = []
    for msg in result.get("messages", []):
        for tc in getattr(msg, "tool_calls", []):
            name = tc.get("name", "")
            if name and name not in tools:
                tools.append(name)
    return tools


def _extract_user_id(request_or_ws) -> str:
    """Extract user_id from Supabase JWT. Uses clarifi.auth for verification."""
    from clarifi.auth import get_user_id
    return get_user_id(request_or_ws)


@router.websocket("/ws/chat/{thread_id}")
async def chat_websocket(websocket: WebSocket, thread_id: str):
    """WebSocket endpoint for streaming chat with per-user memory."""
    await websocket.accept()
    graph = websocket.app.state.graph
    user_id = _extract_user_id(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue
            user_message = data.get("message", "")

            now = datetime.now(ZoneInfo("Europe/Bucharest"))
            user_message = f"[{now.strftime('%d.%m.%Y, %H:%M')}] {user_message}"

            input_state = {
                "messages": [HumanMessage(content=user_message)],
                "user_id": user_id,
            }
            config = {"configurable": {"thread_id": f"{user_id}:{thread_id}"}}

            async for event in graph.astream_events(
                input_state, config=config, version="v2"
            ):
                kind = event.get("event")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        await websocket.send_json(
                            {"type": "stream", "content": chunk.content}
                        )

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass


@router.post("/chat")
async def chat_sync(request: Request):
    """POST endpoint for chat with per-user conversation memory.
    Send thread_id to continue a conversation, or omit for new thread.
    user_id is extracted from Supabase JWT."""
    graph = request.app.state.graph
    body = await request.json()
    user_message = body.get("message", "")
    thread_id = body.get("thread_id", str(uuid.uuid4()))
    user_id = _extract_user_id(request)

    now = datetime.now(ZoneInfo("Europe/Bucharest"))
    user_message = f"[{now.strftime('%d.%m.%Y, %H:%M')}] {user_message}"

    input_state = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
    }
    # Prefix thread_id with user_id to isolate conversation memory per user
    config = {"configurable": {"thread_id": f"{user_id}:{thread_id}"}}

    try:
        result = await graph.ainvoke(input_state, config=config)
    except Exception:
        from fastapi import HTTPException
        logger.exception("Agent error in /chat endpoint")
        raise HTTPException(status_code=500, detail="Eroare la procesare. Incearca din nou.")

    response = extract_ai_response(result)
    if not response:
        logger.warning("Agent returned empty response for thread %s", thread_id)
        response = "Nu am putut genera un raspuns. Incearca sa reformulezi intrebarea."

    tools_used = extract_tool_calls(result)
    tool_labels = [TOOL_LABELS.get(t, t) for t in tools_used]

    return {
        "response": response,
        "thread_id": thread_id,
        "user_id": user_id,
        "tools_used": tool_labels,
    }
