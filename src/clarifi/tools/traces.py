"""Trace tools — agent reads/writes analysis notes per folder.

The agent leaves a trace (like clarifi.md) after analyzing a folder.
Next time it opens the folder, it loads the trace for context.
"""

from datetime import datetime, timezone

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.file_tree import VirtualFolder


@tool
async def read_trace(folder_path: str) -> dict:
    """Citește notele de analiză (trace) pentru un folder. Returnează notele anterioare ale agentului.
    Args: folder_path — calea folderului (ex: "/Facturi/2026", "/Contracte/TechCorp")"""

    async with get_async_session() as session:
        folder = (await session.execute(
            select(VirtualFolder).where(VirtualFolder.path == folder_path)
        )).scalar_one_or_none()

        if not folder:
            return {"status": "not_found", "folder_path": folder_path, "trace": None}

        if not folder.trace_content:
            return {
                "status": "empty",
                "folder_path": folder_path,
                "trace": None,
                "file_count": folder.file_count,
                "message": f"Folder-ul '{folder.name}' nu a fost analizat încă.",
            }

    return {
        "status": "found",
        "folder_path": folder_path,
        "folder_name": folder.name,
        "trace": folder.trace_content,
        "summary": folder.trace_summary,
        "findings": folder.trace_findings,
        "last_analyzed_at": folder.last_analyzed_at.isoformat() if folder.last_analyzed_at else None,
        "documents_analyzed": folder.documents_analyzed,
        "file_count": folder.file_count,
    }


@tool
async def write_trace(
    folder_path: str,
    content: str,
    summary: str,
    findings: dict | None = None,
    documents_analyzed: int = 0,
) -> dict:
    """Scrie sau actualizează notele de analiză (trace) după ce ai analizat conținutul unui folder.
    Args:
        folder_path — calea folderului
        content — notele în markdown (ce ai găsit, ce ai analizat)
        summary — rezumat pe o linie (apare în lista de foldere)
        findings — date structurate: {invoices_found, contracts_found, risks, actions}
        documents_analyzed — câte documente ai analizat
    """
    now = datetime.now(timezone.utc)

    async with get_async_session() as session:
        folder = (await session.execute(
            select(VirtualFolder).where(VirtualFolder.path == folder_path)
        )).scalar_one_or_none()

        if not folder:
            return {"error": f"Folder-ul '{folder_path}' nu a fost găsit."}

        folder.trace_content = content
        folder.trace_summary = summary
        folder.trace_findings = findings
        folder.last_analyzed_at = now
        folder.documents_analyzed = documents_analyzed
        folder_name = folder.name

    return {
        "status": "saved",
        "folder_path": folder_path,
        "folder_name": folder_name,
        "summary": summary,
    }
