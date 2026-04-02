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


class ContractType(str, enum.Enum):
    SERVICE = "service"           # Prestari servicii
    CIM = "cim"                   # Contract individual de munca
    LEASING = "leasing"           # Leasing auto/echipamente
    UTILITIES = "utilities"       # Curent, gaz, internet, telefon
    RENT = "rent"                 # Chirie
    SUBSCRIPTION = "subscription" # Abonamente software, SaaS
    OTHER = "other"


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class Contract(Base, AuditMixin, SoftDeleteMixin, SourceTraceableMixin, FreshnessMixin):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contract_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    counterparty_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )

    total_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RON")
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    signed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_renewal: Mapped[bool] = mapped_column(default=False, nullable=False)
    renewal_notice_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status_enum"),
        default=ContractStatus.DRAFT,
        nullable=False,
    )

    contract_type: Mapped[ContractType] = mapped_column(
        Enum(ContractType, name="contract_type_enum"),
        default=ContractType.SERVICE,
        nullable=False,
    )

    # Recurring payment info (CIM salaries, leasing, rent, utilities)
    is_recurring: Mapped[bool] = mapped_column(default=False, nullable=False)
    recurring_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True,
    )  # Monthly amount if recurring

    payment_terms_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billing_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        CheckConstraint("total_value >= 0", name="ck_contracts_positive_value"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_contracts_date_order",
        ),
        Index("ix_contracts_status", "status"),
        Index("ix_contracts_dates", "start_date", "end_date"),
    )


class ContractMilestone(Base, AuditMixin):
    __tablename__ = "contract_milestones"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contract_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)



class ContractObligation(Base, AuditMixin):
    __tablename__ = "contract_obligations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contract_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    obligated_party: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    recurring: Mapped[bool] = mapped_column(default=False, nullable=False)
    recurrence_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fulfilled: Mapped[bool] = mapped_column(default=False, nullable=False)



class ContractPenalty(Base, AuditMixin):
    __tablename__ = "contract_penalties"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contract_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    trigger_condition: Mapped[str] = mapped_column(Text, nullable=False)
    penalty_type: Mapped[str] = mapped_column(String(50), nullable=False)
    penalty_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    cap_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)

