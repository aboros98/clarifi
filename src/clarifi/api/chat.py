import json
import uuid

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage

router = APIRouter(tags=["chat"])


def extract_ai_response(result: dict) -> str:
    """Extract the last AI message content from agent result."""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            return msg.content
    return ""


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
            # Allow client to override user_id (for testing)
            uid = data.get("user_id", user_id)

            input_state = {
                "messages": [HumanMessage(content=user_message)],
                "user_id": uid,
            }
            config = {"configurable": {"thread_id": f"{uid}:{thread_id}"}}

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
    user_id is extracted from Supabase JWT or can be passed in body."""
    graph = request.app.state.graph
    body = await request.json()
    user_message = body.get("message", "")
    thread_id = body.get("thread_id", str(uuid.uuid4()))
    user_id = body.get("user_id", _extract_user_id(request))

    input_state = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
    }
    # Prefix thread_id with user_id to isolate conversation memory per user
    config = {"configurable": {"thread_id": f"{user_id}:{thread_id}"}}

    try:
        result = await graph.ainvoke(input_state, config=config)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")

    return {
        "response": extract_ai_response(result),
        "thread_id": thread_id,
        "user_id": user_id,
    }
