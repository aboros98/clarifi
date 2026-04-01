import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base, FreshnessMixin, SoftDeleteMixin, SourceTraceableMixin


class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class BankTransaction(Base, AuditMixin, SoftDeleteMixin, SourceTraceableMixin, FreshnessMixin):
    __tablename__ = "bank_transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bank_account_iban: Mapped[str] = mapped_column(String(34), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type_enum"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RON")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    counterparty_iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    balance_after: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    bank_transaction_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, unique=True
    )
    is_matched: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (
        Index("ix_bank_tx_date", "transaction_date"),
        Index("ix_bank_tx_iban", "bank_account_iban"),
        Index("ix_bank_tx_matched", "is_matched"),
    )


class MatchConfidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MANUAL = "manual"


class PaymentInvoiceMatch(Base, AuditMixin):
    __tablename__ = "payment_invoice_matches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bank_transaction_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    matched_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    confidence: Mapped[MatchConfidence] = mapped_column(
        Enum(MatchConfidence, name="match_confidence_enum"), nullable=False
    )
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_pim_unconfirmed", "confirmed"),
    )
