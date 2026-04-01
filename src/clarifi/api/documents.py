"""Document upload API — creates placeholder, processes in background."""

import asyncio
import hashlib
import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from sqlalchemy import select

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
    """Upload a document. Creates a placeholder visible as 'Se analizeaza...',
    then processes in background. The agent updates the record when done."""
    content = await file.read()
    if len(content) == 0:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Fisierul este gol")

    filename = file.filename or "unknown"
    file_hash = hashlib.sha256(content).hexdigest()
    user_id = _extract_user_id(request)

    # Check duplicate
    async with get_async_session() as session:
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

    # Save file to disk (hash prefix for uniqueness)
    storage_dir = Path(settings.processed_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    permanent_path = storage_dir / f"{file_hash}_{filename}"
    permanent_path.write_bytes(content)

    # Clean filename for display (remove hash prefix if present)
    display_name = filename

    mime_type = (
        mimetypes.guess_type(filename)[0] or "application/octet-stream"
    )

    # Create placeholder record — visible immediately as "Se analizeaza..."
    async with get_async_session() as session:
        placeholder = Document(
            original_filename=display_name,
            storage_path=str(permanent_path),
            mime_type=mime_type,
            file_size_bytes=len(content),
            file_hash_sha256=file_hash,
            document_type=DocumentType.OTHER,
            processing_status=ProcessingStatus.UPLOADED,
            user_id=user_id,
        )
        session.add(placeholder)
        await session.flush()
        doc_id = placeholder.id

    # Background processing — agent will update this record
    asyncio.create_task(
        _background_process(str(permanent_path), filename, doc_id, user_id)
    )

    return {
        "status": "processing",
        "document_id": doc_id,
        "filename": filename,
    }


async def _background_process(
    file_path: str, filename: str, doc_id: str, user_id: str,
):
    """Run agent in background. Updates the placeholder Document on completion."""
    try:
        from langchain_core.messages import HumanMessage

        from clarifi.agent.graph import get_graph

        graph = await get_graph()
        await asyncio.wait_for(
            graph.ainvoke(
                {
                    "messages": [HumanMessage(content=(
                        f"Document nou: {filename} (la {file_path}). "
                        f"Document ID deja creat: {doc_id}. "
                        f"Proceseaza-l: parseaza, extrage date, salveaza, "
                        f"organizeaza in foldere, creeaza remindere. "
                        f"IMPORTANT: documentul exista deja in DB cu ID {doc_id}, "
                        f"NU crea alt document — foloseste acest ID."
                    ))],
                    "user_id": user_id,
                    "mode": "background",
                },
                config={
                    "configurable": {
                        "thread_id": f"{user_id}:upload-{doc_id}",
                    },
                },
            ),
            timeout=300,
        )

        # Mark as stored
        async with get_async_session() as session:
            doc = await session.get(Document, doc_id)
            if doc:
                doc.processing_status = ProcessingStatus.STORED
        logger.info("Background processing done: %s", filename)

    except Exception:
        logger.exception("Background processing failed: %s", filename)
        try:
            async with get_async_session() as session:
                doc = await session.get(Document, doc_id)
                if doc:
                    doc.processing_status = ProcessingStatus.FAILED
        except Exception:
            pass
