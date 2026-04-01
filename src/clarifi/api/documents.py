"""Document upload API — saves file, processes in background."""

import asyncio
import hashlib
import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile

from clarifi.api.chat import _extract_user_id
from clarifi.config import settings
from clarifi.db.session import get_async_session
from clarifi.models.document import Document, DocumentType, ProcessingStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload a document. Returns immediately, processes in background."""
    content = await file.read()
    if len(content) == 0:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Fisierul este gol")

    filename = file.filename or "unknown"
    file_hash = hashlib.sha256(content).hexdigest()

    # Check duplicate before saving
    async with get_async_session() as session:
        from sqlalchemy import select

        existing = (await session.execute(
            select(Document).where(
                Document.file_hash_sha256 == file_hash,
                Document.is_deleted == False,  # noqa: E712
            )
        )).scalar_one_or_none()

        if existing:
            return {
                "status": "duplicate",
                "document_id": existing.id,
                "filename": filename,
            }

    # Save file to disk
    storage_dir = Path(settings.processed_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    permanent_path = storage_dir / f"{file_hash}_{filename}"
    permanent_path.write_bytes(content)

    user_id = _extract_user_id(request)

    # Trigger background processing — the agent's ingest_document tool
    # will create the Document record with proper type and extract data
    asyncio.create_task(
        _background_process(str(permanent_path), filename, user_id)
    )

    return {
        "status": "processing",
        "filename": filename,
        "message": "Document incarcat. Se analizeaza in fundal.",
    }


async def _background_process(
    file_path: str, filename: str, user_id: str,
):
    """Run the agent in background mode to extract + organize."""
    try:
        from langchain_core.messages import HumanMessage

        from clarifi.agent.graph import get_graph

        graph = await get_graph()
        await asyncio.wait_for(
            graph.ainvoke(
                {
                    "messages": [HumanMessage(content=(
                        f"Document nou: {filename} (la {file_path}). "
                        f"Proceseaza-l: parseaza, extrage date, salveaza, "
                        f"organizeaza in foldere, creeaza remindere."
                    ))],
                    "user_id": user_id,
                    "mode": "background",
                },
                config={
                    "configurable": {
                        "thread_id": f"{user_id}:upload-{filename}",
                    },
                },
            ),
            timeout=300,
        )
        logger.info("Background processing done: %s", filename)
    except Exception:
        logger.exception("Background processing failed: %s", filename)
