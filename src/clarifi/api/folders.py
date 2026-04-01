"""Watched folder management API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.integration import WatchedFolder


class AddFolderRequest(BaseModel):
    provider: str = "local"
    folder_path: str | None = None
    folder_id: str | None = None
    display_name: str = ""

router = APIRouter(prefix="/api", tags=["folders"])


@router.get("/folders")
async def list_folders():
    """List all watched folders."""
    async with get_async_session() as session:
        folders = (await session.execute(
            select(WatchedFolder).order_by(WatchedFolder.created_at.desc())
        )).scalars().all()

    return {
        "folders": [
            {
                "id": f.id,
                "provider": f.provider,
                "folder_path": f.folder_path,
                "folder_id": f.folder_id,
                "display_name": f.display_name,
                "is_active": f.is_active,
                "last_synced_at": f.last_synced_at.isoformat() if f.last_synced_at else None,
                "files_processed": f.files_processed,
            }
            for f in folders
        ]
    }


@router.post("/folders")
async def add_folder(body: AddFolderRequest):
    """Add a new watched folder."""
    async with get_async_session() as session:
        folder = WatchedFolder(
            provider=body.provider,
            folder_path=body.folder_path,
            folder_id=body.folder_id,
            display_name=body.display_name or body.folder_path or "New Folder",
            is_active=True,
        )
        session.add(folder)
        await session.flush()
        folder_id = folder.id
        name = folder.display_name

    return {"status": "created", "id": folder_id, "display_name": name}


@router.delete("/folders/{folder_id}")
async def remove_folder(folder_id: str):
    """Deactivate a watched folder."""
    async with get_async_session() as session:
        folder = await session.get(WatchedFolder, folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        folder.is_active = False
        name = folder.display_name
    return {"status": "deactivated", "id": folder_id, "display_name": name}
