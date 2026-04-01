"""User profile — links a Supabase user to a company.

A user can belong to multiple companies via UserCompanyLink.
UserProfile.company_id is the *active* company.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base


class UserProfile(Base, AuditMixin):
    """Links a Supabase auth user_id to their active company and role."""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True,
    )
    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="owner")
    onboarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(), nullable=True,
    )

    __table_args__ = (
        Index("ix_user_profiles_company", "company_id"),
    )


class UserCompanyLink(Base, AuditMixin):
    """Many-to-many: a user can manage multiple companies."""

    __tablename__ = "user_company_links"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="owner")

    __table_args__ = (
        Index("ix_ucl_user_company", "user_id", "company_id", unique=True),
    )
