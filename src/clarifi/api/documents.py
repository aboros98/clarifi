import os
import tempfile
import uuid

from fastapi import APIRouter, File, Request, UploadFile
from langchain_core.messages import HumanMessage

from clarifi.api.chat import extract_ai_response, _extract_user_id

router = APIRouter(tags=["documents"])


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload a document. The agent parses it and asks user to confirm extracted data."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        graph = request.app.state.graph
        user_id = _extract_user_id(request)
        thread_id = f"upload-{uuid.uuid4()}"

        msg = f"Am primit un document nou: {file.filename} (salvat la {tmp_path}). Procesează-l și arată-mi ce ai extras."
        input_state = {
            "messages": [HumanMessage(content=msg)],
            "user_id": user_id,
        }
        config = {"configurable": {"thread_id": f"{user_id}:{thread_id}"}}

        result = await graph.ainvoke(input_state, config=config)
        return {"status": "processed", "response": extract_ai_response(result)}
    finally:
        os.unlink(tmp_path)
