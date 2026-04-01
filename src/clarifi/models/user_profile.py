"""User profile — links a Supabase user to a company."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base


class UserProfile(Base, AuditMixin):
    """Links a Supabase auth user_id to their company and role."""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="owner")
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    __table_args__ = (
        Index("ix_user_profiles_company", "company_id"),
    )
