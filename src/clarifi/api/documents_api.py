"""Document management API endpoints (list, details, delete)."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from clarifi.agent.context import current_user_id
from clarifi.api.chat import _extract_user_id
from clarifi.db.session import get_async_session
from clarifi.models.document import Document

router = APIRouter(prefix="/api", tags=["documents"])


def _doc_type_value(d):
    return d.document_type.value if d.document_type else "unknown"


def _status_value(d):
    return d.processing_status.value if d.processing_status else "unknown"


@router.get("/documents")
async def list_documents(request: Request, limit: int = Query(50, le=200), offset: int = 0):
    """List all processed documents for the authenticated user."""
    user_id = _extract_user_id(request)
    current_user_id.set(user_id)

    async with get_async_session() as session:
        docs = (await session.execute(
            select(Document)
            .where(Document.is_deleted == False)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )).scalars().all()

    return {
        "documents": [
            {
                "id": d.id,
                "filename": d.original_filename,
                "mime_type": d.mime_type,
                "document_type": _doc_type_value(d),
                "processing_status": _status_value(d),
                "extraction_confidence": float(d.extraction_confidence) if d.extraction_confidence else None,
                "page_count": d.page_count,
                "ocr_applied": d.ocr_applied,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ]
    }


@router.get("/documents/{doc_id}")
async def get_document(request: Request, doc_id: str):
    """Get document details including extracted text."""
    user_id = _extract_user_id(request)
    current_user_id.set(user_id)

    async with get_async_session() as session:
        d = await session.get(Document, doc_id)
        if not d or d.user_id != user_id:
            raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": d.id,
        "filename": d.original_filename,
        "mime_type": d.mime_type,
        "document_type": _doc_type_value(d),
        "processing_status": _status_value(d),
        "extraction_confidence": float(d.extraction_confidence) if d.extraction_confidence else None,
        "extraction_raw_response": d.extraction_raw_response,
        "page_count": d.page_count,
        "ocr_applied": d.ocr_applied,
        "raw_text": d.raw_text[:5000] if d.raw_text else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "reviewed_by": d.reviewed_by,
        "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
    }


@router.delete("/documents/{doc_id}")
async def delete_document(request: Request, doc_id: str):
    """Delete a document — clears hash so same file can be re-uploaded."""
    user_id = _extract_user_id(request)
    current_user_id.set(user_id)

    async with get_async_session() as session:
        d = await session.get(Document, doc_id)
        if not d or d.user_id != user_id:
            raise HTTPException(status_code=404, detail="Document not found")
        d.is_deleted = True
        d.deleted_at = datetime.now(UTC)
        # Clear hash so same file can be re-uploaded
        d.file_hash_sha256 = f"deleted_{doc_id}_{d.file_hash_sha256}"
    return {"status": "deleted", "id": doc_id}
