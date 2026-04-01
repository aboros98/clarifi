import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base, SoftDeleteMixin, SourceTraceableMixin


class EstimateStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONVERTED = "converted"


class Estimate(Base, AuditMixin, SoftDeleteMixin, SourceTraceableMixin):
    __tablename__ = "estimates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    estimate_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    client_company_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    contract_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RON")

    status: Mapped[EstimateStatus] = mapped_column(
        Enum(EstimateStatus, name="estimate_status_enum"),
        default=EstimateStatus.DRAFT,
        nullable=False,
    )


class EstimateLineItem(Base, AuditMixin):
    __tablename__ = "estimate_line_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    estimate_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

