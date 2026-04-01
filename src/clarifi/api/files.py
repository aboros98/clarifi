"""File tree API — folder management + file uploads for the frontend."""

import asyncio
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.file_tree import FileEntry, VirtualFolder
from clarifi.tools.cloud_sync import upload_to_storage

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/tree")
async def get_tree():
    """Get the full folder tree."""
    async with get_async_session() as session:
        folders = (await session.execute(
            select(VirtualFolder).order_by(VirtualFolder.path)
        )).scalars().all()

    return {
        "folders": [
            {
                "id": f.id,
                "name": f.name,
                "path": f.path,
                "parent_id": f.parent_id,
                "file_count": f.file_count,
                "trace_summary": f.trace_summary,
                "last_analyzed": f.last_analyzed_at.isoformat() if f.last_analyzed_at else None,
            }
            for f in folders
        ],
    }


@router.get("/folder/{folder_id}")
async def get_folder_contents(folder_id: str):
    """Get files in a specific folder."""
    async with get_async_session() as session:
        folder = await session.get(VirtualFolder, folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        subfolders = (await session.execute(
            select(VirtualFolder).where(VirtualFolder.parent_id == folder_id)
            .order_by(VirtualFolder.name)
        )).scalars().all()

        files = (await session.execute(
            select(FileEntry).where(FileEntry.folder_id == folder_id)
            .order_by(FileEntry.filename)
        )).scalars().all()

    return {
        "folder": {
            "id": folder.id,
            "name": folder.name,
            "path": folder.path,
            "trace_summary": folder.trace_summary,
            "trace_content": folder.trace_content,
        },
        "subfolders": [
            {"id": sf.id, "name": sf.name, "path": sf.path, "file_count": sf.file_count}
            for sf in subfolders
        ],
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "mime_type": f.mime_type,
                "file_size": f.file_size,
                "status": f.status,
                "storage_provider": f.storage_provider,
                "extracted_entity_type": f.extracted_entity_type,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in files
        ],
    }


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    auto_process: bool = True,
):
    """Upload a file. If auto_process=true, the background agent will analyze it."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await upload_to_storage.ainvoke({
            "file_path": tmp_path,
            "folder_path": "/Neprocesat",
        })

        if auto_process and result.get("status") == "uploaded":
            # Trigger background agent to process this file
            asyncio.create_task(_background_process(result.get("document_id", ""), file.filename))

        return result
    finally:
        os.unlink(tmp_path)


async def _background_process(document_id: str, filename: str):
    """Trigger background agent to analyze an uploaded file."""
    try:
        from clarifi.agent.graph import get_graph
        from langchain_core.messages import HumanMessage

        graph = await get_graph()
        await asyncio.wait_for(
            graph.ainvoke(
                {
                    "messages": [HumanMessage(content=(
                        f"Document nou încărcat: {filename}. "
                        f"Procesează-l: extrage date, organizează, creează remindere."
                    ))],
                    "user_id": "background-agent",
                    "mode": "background",
                },
                config={"configurable": {"thread_id": f"upload-{document_id}"}},
            ),
            timeout=300,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Background processing failed for %s", filename, exc_info=True)
