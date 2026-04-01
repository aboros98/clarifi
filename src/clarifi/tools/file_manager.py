"""File management tools — the agent can create folders, move files, organize documents.

The agent uses these to organize user's documents into a logical tree:
  /Contracte/TechCorp/CTR-2025-001.pdf
  /Facturi/2026/03/INV-2026-008.pdf
  /Extrase Bancare/BCR/Martie 2026.csv
"""

from langchain_core.tools import tool
from sqlalchemy import func, select

from clarifi.db.session import get_async_session
from clarifi.models.document import Document
from clarifi.models.file_tree import FileEntry, VirtualFolder


@tool
async def create_folder(name: str, parent_path: str = "/") -> dict:
    """Create a virtual folder for organizing documents.
    Args:
        name — folder name (e.g., "Contracte", "Facturi 2026")
        parent_path — parent folder path (e.g., "/" for root, "/Contracte" for subfolder)
    Use this to organize documents into a logical structure."""

    path = f"{parent_path.rstrip('/')}/{name}"

    async with get_async_session() as session:
        existing = (await session.execute(
            select(VirtualFolder).where(VirtualFolder.path == path)
        )).scalar_one_or_none()
        if existing:
            return {"status": "exists", "id": existing.id, "path": path}

        # Find parent
        parent_id = None
        if parent_path != "/":
            parent = (await session.execute(
                select(VirtualFolder).where(VirtualFolder.path == parent_path)
            )).scalar_one_or_none()
            if parent:
                parent_id = parent.id

        folder = VirtualFolder(
            name=name,
            parent_id=parent_id,
            path=path,
            auto_created=True,
        )
        session.add(folder)
        await session.flush()
        fid = folder.id

    return {"status": "created", "id": fid, "path": path, "name": name}


@tool
async def list_folders(parent_path: str = "/") -> dict:
    """List folders and files at a given path. Shows the folder tree.
    Args: parent_path — "/" for root, "/Contracte" for a subfolder."""

    async with get_async_session() as session:
        if parent_path == "/":
            folders = (await session.execute(
                select(VirtualFolder).where(VirtualFolder.parent_id.is_(None))
                .order_by(VirtualFolder.name)
            )).scalars().all()
        else:
            parent = (await session.execute(
                select(VirtualFolder).where(VirtualFolder.path == parent_path)
            )).scalar_one_or_none()
            if not parent:
                return {"error": f"Folder '{parent_path}' not found"}
            folders = (await session.execute(
                select(VirtualFolder).where(VirtualFolder.parent_id == parent.id)
                .order_by(VirtualFolder.name)
            )).scalars().all()

        # Get files in current folder
        parent_folder = (await session.execute(
            select(VirtualFolder).where(VirtualFolder.path == parent_path)
        )).scalar_one_or_none() if parent_path != "/" else None

        files = []
        if parent_folder:
            files_q = (await session.execute(
                select(FileEntry).where(FileEntry.folder_id == parent_folder.id)
                .order_by(FileEntry.filename)
            )).scalars().all()
            files = [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "mime_type": f.mime_type,
                    "status": f.status,
                    "extracted_type": f.extracted_entity_type,
                }
                for f in files_q
            ]

    return {
        "path": parent_path,
        "folders": [
            {"id": f.id, "name": f.name, "path": f.path, "file_count": f.file_count}
            for f in folders
        ],
        "files": files,
    }


@tool
async def move_file(file_id: str, target_folder_path: str) -> dict:
    """Move a file to a different folder.
    Args:
        file_id — the file entry ID
        target_folder_path — destination folder path (e.g., "/Contracte/TechCorp")
    """
    async with get_async_session() as session:
        file = await session.get(FileEntry, file_id)
        if not file:
            return {"error": f"File {file_id} not found"}

        target = (await session.execute(
            select(VirtualFolder).where(VirtualFolder.path == target_folder_path)
        )).scalar_one_or_none()
        if not target:
            return {"error": f"Folder '{target_folder_path}' not found"}

        old_folder_id = file.folder_id
        file.folder_id = target.id

        # Update counts
        if old_folder_id:
            old = await session.get(VirtualFolder, old_folder_id)
            if old and old.file_count > 0:
                old.file_count -= 1
        target.file_count += 1

        filename = file.filename

    return {"status": "moved", "file": filename, "to": target_folder_path}


@tool
async def organize_inbox() -> dict:
    """Scan all unorganized documents and sort them into folders by type and date.
    Creates a standard folder structure:
      /Contracte/{client}
      /Facturi/{year}/{month}
      /Extrase Bancare/{bank}
      /Neprocesat
    """
    async with get_async_session() as session:
        # Create standard folders
        standard = {
            "/Contracte": "Contracte",
            "/Facturi": "Facturi",
            "/Extrase Bancare": "Extrase Bancare",
            "/Neprocesat": "Documente neprocesate",
        }
        folder_ids = {}
        for path, name in standard.items():
            existing = (await session.execute(
                select(VirtualFolder).where(VirtualFolder.path == path)
            )).scalar_one_or_none()
            if not existing:
                f = VirtualFolder(name=name, path=path, auto_created=True)
                session.add(f)
                await session.flush()
                folder_ids[path] = f.id
            else:
                folder_ids[path] = existing.id

        # Find documents without a file_entry
        docs = (await session.execute(
            select(Document).where(
                Document.is_deleted == False,
                Document.id.not_in(
                    select(FileEntry.document_id).where(FileEntry.document_id.isnot(None))
                ),
            ).limit(100)
        )).scalars().all()

        organized = 0
        for doc in docs:
            # Determine folder based on document type
            doc_type = doc.document_type.value if doc.document_type else "other"
            if "contract" in doc_type:
                folder_id = folder_ids["/Contracte"]
            elif "invoice" in doc_type:
                folder_id = folder_ids["/Facturi"]
            elif "bank" in doc_type:
                folder_id = folder_ids["/Extrase Bancare"]
            else:
                folder_id = folder_ids["/Neprocesat"]

            entry = FileEntry(
                folder_id=folder_id,
                document_id=doc.id,
                filename=doc.original_filename,
                storage_url=doc.storage_path,
                storage_provider="local",
                file_size=doc.file_size_bytes,
                mime_type=doc.mime_type,
                status=doc.processing_status.value,
            )
            session.add(entry)

            # Update folder count
            folder = await session.get(VirtualFolder, folder_id)
            if folder:
                folder.file_count += 1

            organized += 1

    return {
        "status": "organized",
        "documents_organized": organized,
        "folders_created": list(standard.keys()),
    }


@tool
async def read_document_content(document_id: str, max_chars: int = 5000) -> dict:
    """Read the text content of a document. Use to inspect what's in a file.
    Args:
        document_id — the document ID
        max_chars — max characters to return (default 5000)
    """
    async with get_async_session() as session:
        doc = await session.get(Document, document_id)
        if not doc:
            return {"error": f"Document {document_id} not found"}

    return {
        "filename": doc.original_filename,
        "document_type": doc.document_type.value,
        "processing_status": doc.processing_status.value,
        "page_count": doc.page_count,
        "text": doc.raw_text[:max_chars] if doc.raw_text else "[Niciun text extras]",
        "text_length": len(doc.raw_text) if doc.raw_text else 0,
        "ocr_applied": doc.ocr_applied,
    }


@tool
async def get_file_tree() -> dict:
    """Get the complete folder/file tree structure. Shows how documents are organized."""
    async with get_async_session() as session:
        folders = (await session.execute(
            select(VirtualFolder).order_by(VirtualFolder.path)
        )).scalars().all()

        # Count total files
        total_files = (await session.execute(
            select(func.count(FileEntry.id))
        )).scalar_one()

        # Unorganized documents
        unorganized = (await session.execute(
            select(func.count(Document.id)).where(
                Document.is_deleted == False,
                Document.id.not_in(
                    select(FileEntry.document_id).where(FileEntry.document_id.isnot(None))
                ),
            )
        )).scalar_one()

    tree = [
        {
            "path": f.path,
            "name": f.name,
            "files": f.file_count,
            "trace_summary": f.trace_summary,
            "last_analyzed": f.last_analyzed_at.isoformat() if f.last_analyzed_at else None,
        }
        for f in folders
    ]

    return {
        "tree": tree,
        "total_folders": len(folders),
        "total_files": total_files,
        "unorganized_documents": unorganized,
    }
