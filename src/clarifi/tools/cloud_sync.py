"""Cloud sync tools — upload to Supabase Storage, sync from Google Drive."""

import hashlib
import logging
import mimetypes
from pathlib import Path

import httpx
from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.agent.context import current_user_id
from clarifi.config import settings
from clarifi.db.session import get_async_session
from clarifi.models.document import Document, DocumentType, ProcessingStatus
from clarifi.models.file_tree import FileEntry, VirtualFolder
from clarifi.models.integration import IntegrationConfig

logger = logging.getLogger(__name__)

SUPABASE_STORAGE_URL = f"{settings.supabase_url}/storage/v1" if hasattr(settings, "supabase_url") and settings.supabase_url else None


@tool
async def upload_to_storage(file_path: str, folder_path: str = "/Neprocesat") -> dict:
    """Upload a local file to cloud storage (Supabase) and register in the file tree.
    Args:
        file_path — local path to the file
        folder_path — virtual folder to place it in (e.g., "/Facturi/2026")
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"Fișierul nu a fost găsit: {file_path}"}

    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"

    storage_url = None

    # Upload to Supabase Storage if configured
    if SUPABASE_STORAGE_URL and hasattr(settings, "supabase_service_key") and settings.supabase_service_key:
        try:
            storage_path = f"documents/{file_hash}_{path.name}"
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{SUPABASE_STORAGE_URL}/object/documents/{storage_path}",
                    headers={
                        "Authorization": f"Bearer {settings.supabase_service_key}",
                        "Content-Type": mime_type,
                    },
                    content=file_bytes,
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    storage_url = f"{SUPABASE_STORAGE_URL}/object/public/documents/{storage_path}"
                    logger.info("Uploaded to Supabase Storage: %s", storage_path)
                else:
                    logger.warning("Supabase Storage upload failed: %s", resp.text[:200])
        except Exception:
            logger.warning("Supabase Storage upload failed", exc_info=True)

    async with get_async_session() as session:
        # Check duplicate
        existing = (await session.execute(
            select(Document).where(Document.file_hash_sha256 == file_hash)
        )).scalar_one_or_none()
        if existing:
            return {"status": "duplicate", "document_id": existing.id}

        # Create document record
        uid = current_user_id.get()
        doc = Document(
            original_filename=path.name,
            storage_path=storage_url or str(path),
            mime_type=mime_type,
            file_size_bytes=len(file_bytes),
            file_hash_sha256=file_hash,
            document_type=DocumentType.OTHER,
            processing_status=ProcessingStatus.UPLOADED,
            user_id=uid,
        )
        session.add(doc)
        await session.flush()
        doc_id = doc.id

        # Add to file tree
        folder = (await session.execute(
            select(VirtualFolder).where(VirtualFolder.path == folder_path)
        )).scalar_one_or_none()

        if not folder:
            folder = VirtualFolder(name=folder_path.split("/")[-1] or "Root", path=folder_path, auto_created=True, user_id=uid)
            session.add(folder)
            await session.flush()

        entry = FileEntry(
            folder_id=folder.id,
            document_id=doc_id,
            filename=path.name,
            storage_url=storage_url or str(path),
            storage_provider="supabase" if storage_url else "local",
            file_size=len(file_bytes),
            mime_type=mime_type,
            status="uploaded",
        )
        session.add(entry)
        folder.file_count += 1

    return {
        "status": "uploaded",
        "document_id": doc_id,
        "filename": path.name,
        "storage": "supabase" if storage_url else "local",
        "folder": folder_path,
    }


@tool
async def sync_google_drive(folder_id: str = "") -> dict:
    """Sync files from a connected Google Drive folder. Downloads new files and ingests them.
    Args: folder_id — Google Drive folder ID (leave empty to sync all connected folders)."""

    async with get_async_session() as session:
        # Get Drive tokens
        config = (await session.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.provider == "google_drive",
                IntegrationConfig.status == "connected",
            )
        )).scalar_one_or_none()

        if not config or not config.config:
            return {"error": "Google Drive nu este conectat. Mergi la Settings → Google Drive."}

        tokens = config.config
        access_token = tokens.get("access_token")
        if not access_token:
            return {"error": "Token Google Drive expirat. Reconectează din Settings."}

    # List files from Drive
    query = "mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": query,
                    "fields": "files(id,name,mimeType,size,modifiedTime)",
                    "pageSize": 50,
                    "orderBy": "modifiedTime desc",
                },
                timeout=15,
            )
            if resp.status_code == 401:
                return {"error": "Token Google Drive expirat. Reconectează din Settings."}
            resp.raise_for_status()
            files = resp.json().get("files", [])

        if not files:
            return {"status": "no_new_files", "message": "Niciun fișier nou pe Drive."}

        # Download and ingest each file
        synced = 0
        for f in files[:20]:  # Limit to 20 per sync
            try:
                dl_resp = await client.get(
                    f"https://www.googleapis.com/drive/v3/files/{f['id']}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"alt": "media"},
                    timeout=30,
                )
                if dl_resp.status_code != 200:
                    continue

                # Save to temp and upload
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{f['name']}") as tmp:
                    tmp.write(dl_resp.content)
                    tmp_path = tmp.name

                result = await upload_to_storage.ainvoke({
                    "file_path": tmp_path,
                    "folder_path": "/Google Drive",
                })

                import os
                os.unlink(tmp_path)

                if result.get("status") in ("uploaded", "duplicate"):
                    synced += 1

            except Exception:
                logger.warning("Failed to sync Drive file: %s", f["name"], exc_info=True)

        return {
            "status": "synced",
            "files_found": len(files),
            "files_synced": synced,
        }

    except Exception as e:
        return {"error": f"Eroare la sincronizare Drive: {e}"}
