"""Document upload API — saves file immediately, processes in background."""

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
    """Upload a document. Returns immediately, processes in background.

    The document appears in the UI as 'Se analizeaza...' until the
    background agent finishes extraction and organization.
    """
    # Read file content
    content = await file.read()
    filename = file.filename or "unknown"
    file_hash = hashlib.sha256(content).hexdigest()

    # Save to permanent storage immediately
    storage_dir = Path(settings.processed_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    permanent_path = storage_dir / f"{file_hash}_{filename}"
    permanent_path.write_bytes(content)

    mime_type = (
        mimetypes.guess_type(filename)[0] or "application/octet-stream"
    )

    user_id = _extract_user_id(request)

    # Create document record immediately (status: uploaded)
    async with get_async_session() as session:
        # Check duplicate
        from sqlalchemy import select

        existing = (await session.execute(
            select(Document).where(Document.file_hash_sha256 == file_hash)
        )).scalar_one_or_none()

        if existing:
            return {
                "status": "duplicate",
                "document_id": existing.id,
                "filename": filename,
            }

        doc = Document(
            original_filename=filename,
            storage_path=str(permanent_path),
            mime_type=mime_type,
            file_size_bytes=len(content),
            file_hash_sha256=file_hash,
            document_type=DocumentType.OTHER,
            processing_status=ProcessingStatus.UPLOADED,
            user_id=user_id,
        )
        session.add(doc)
        await session.flush()
        doc_id = doc.id

    # Trigger background processing (non-blocking)
    asyncio.create_task(
        _background_process(str(permanent_path), filename, doc_id, user_id)
    )

    return {
        "status": "processing",
        "document_id": doc_id,
        "filename": filename,
        "message": "Document incarcat. Se analizeaza in fundal.",
    }


async def _background_process(
    file_path: str, filename: str, doc_id: str, user_id: str,
):
    """Run the agent in background mode to extract + organize the document."""
    try:
        from langchain_core.messages import HumanMessage

        from clarifi.agent.graph import get_graph

        graph = await get_graph()
        await asyncio.wait_for(
            graph.ainvoke(
                {
                    "messages": [HumanMessage(content=(
                        f"Document nou: {filename} (la {file_path}). "
                        f"Document ID: {doc_id}. "
                        f"Proceseaza-l: extrage date, organizeaza in foldere, "
                        f"creeaza remindere pentru deadline-uri."
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
        logger.info("Background processing done: %s", filename)
    except Exception:
        logger.exception("Background processing failed: %s", filename)
        # Mark document as failed
        try:
            async with get_async_session() as session:
                doc = await session.get(Document, doc_id)
                if doc:
                    doc.processing_status = ProcessingStatus.FAILED
        except Exception:
            pass
