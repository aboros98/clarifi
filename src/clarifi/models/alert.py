import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertType(str, enum.Enum):
    INVOICE_OVERDUE = "invoice_overdue"
    INVOICE_DUE_SOON = "invoice_due_soon"
    CONTRACT_EXPIRING = "contract_expiring"
    CONTRACT_RENEWAL = "contract_renewal"
    MILESTONE_DUE = "milestone_due"
    PAYMENT_UNMATCHED = "payment_unmatched"
    CASHFLOW_LOW = "cashflow_low"
    EXTRACTION_FAILED = "extraction_failed"
    REVIEW_NEEDED = "review_needed"
    DUPLICATE_DOCUMENT = "duplicate_document"
    OBLIGATION_DUE = "obligation_due"
    PENALTY_RISK = "penalty_risk"
    ESTIMATE_EXPIRING = "estimate_expiring"
    PROJECT_OVER_BUDGET = "project_over_budget"
    NEGATIVE_MARGIN = "negative_margin"


class Alert(Base, AuditMixin):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type_enum"), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity_enum"), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status_enum"),
        default=AlertStatus.NEW,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    related_entity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    related_entity_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_alerts_status_severity", "status", "severity"),
        Index("ix_alerts_type", "alert_type"),
        Index("ix_alerts_entity", "related_entity_type", "related_entity_id"),
    )
