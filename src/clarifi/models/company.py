import enum
import uuid

from sqlalchemy import Enum, Index, String, Text, UniqueConstraint
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base, SoftDeleteMixin, SourceTraceableMixin


class CompanyRole(str, enum.Enum):
    CLIENT = "client"
    SUPPLIER = "supplier"
    BOTH = "both"
    OWN_COMPANY = "own_company"


class Company(Base, AuditMixin, SoftDeleteMixin, SourceTraceableMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    legal_name: Mapped[str] = mapped_column(String(500), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[CompanyRole] = mapped_column(
        Enum(CompanyRole, name="company_role_enum"), nullable=False
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bank_accounts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    name_variants: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("tax_id", name="uq_companies_tax_id"),
        Index("ix_companies_legal_name", "legal_name"),
        Index("ix_companies_role", "role"),
    )


class Contact(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    role_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)

