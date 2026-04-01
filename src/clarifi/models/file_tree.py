"""File tree — virtual folder structure for organizing documents.

Users dump files → agent organizes into folders like:
  /Contracte/TechCorp/CTR-2025-001.pdf
  /Facturi/2026/Martie/INV-2026-008.pdf
  /Extrase Bancare/BCR/Martie 2026.pdf
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base


class VirtualFolder(Base, AuditMixin):
    """A folder in the virtual file tree. Can be nested."""

    __tablename__ = "virtual_folders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    path: Mapped[str] = mapped_column(
        String(2000), nullable=False, default="/",
    )
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Trace — agent's analysis notes for this folder
    trace_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    trace_findings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    documents_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_virtual_folders_path", "path"),
    )


class FileEntry(Base, AuditMixin):
    """A file entry linking a document to a virtual folder."""

    __tablename__ = "file_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    folder_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    storage_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="supabase",
    )
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded",
    )
    extracted_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extracted_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_file_entries_status", "status"),
    )
