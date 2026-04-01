"""Watched folders and integration configuration models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base


class WatchedFolder(Base, AuditMixin):
    """Folders being watched for new documents (local, Google Drive, etc.)."""

    __tablename__ = "watched_folders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="local"
    )
    folder_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    folder_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    files_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_watched_folders_active", "is_active"),
    )


class IntegrationConfig(Base, AuditMixin):
    """Configuration for external integrations (Drive, Telegram, etc.)."""

    __tablename__ = "integration_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="disconnected"
    )
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_integration_configs_provider", "provider"),
    )
