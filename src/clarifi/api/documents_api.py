"""Document management API endpoints (list, details)."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.document import Document

router = APIRouter(prefix="/api", tags=["documents"])


def _doc_type_value(d):
    return d.document_type.value if d.document_type else "unknown"


def _status_value(d):
    return d.processing_status.value if d.processing_status else "unknown"


@router.get("/documents")
async def list_documents(limit: int = Query(50, le=200), offset: int = 0):
    """List all processed documents."""
    async with get_async_session() as session:
        docs = (await session.execute(
            select(Document)
            .where(Document.is_deleted == False)
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
async def get_document(doc_id: str):
    """Get document details including extracted text."""
    async with get_async_session() as session:
        d = await session.get(Document, doc_id)
        if not d:
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
