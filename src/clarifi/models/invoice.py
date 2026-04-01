import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base, FreshnessMixin, SoftDeleteMixin, SourceTraceableMixin


class InvoiceDirection(str, enum.Enum):
    ISSUED = "issued"
    RECEIVED = "received"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class Invoice(Base, AuditMixin, SoftDeleteMixin, SourceTraceableMixin, FreshnessMixin):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[InvoiceDirection] = mapped_column(
        Enum(InvoiceDirection, name="invoice_direction_enum"), nullable=False
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status_enum"),
        default=InvoiceStatus.DRAFT,
        nullable=False,
    )

    issuer_company_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    recipient_company_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    contract_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RON")
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0.00")
    )
    amount_remaining: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    payment_terms_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "uq_invoices_number_direction",
            "invoice_number",
            "direction",
            "issuer_company_id",
            unique=True,
        ),
        CheckConstraint("total_amount >= 0", name="ck_invoices_positive_total"),
        CheckConstraint("amount_paid >= 0", name="ck_invoices_positive_paid"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_direction", "direction"),
        Index("ix_invoices_due_date", "due_date"),
    )


class InvoiceLineItem(Base, AuditMixin):
    __tablename__ = "invoice_line_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("19.00")
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

