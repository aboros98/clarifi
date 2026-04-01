import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base, SoftDeleteMixin


class ProjectStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_company_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status_enum"),
        default=ProjectStatus.PROPOSED,
        nullable=False,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)


    __table_args__ = (
        Index("ix_projects_status", "status"),
    )
