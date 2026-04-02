import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base, SoftDeleteMixin


class DocumentType(str, enum.Enum):
    INVOICE_ISSUED = "invoice_issued"
    INVOICE_RECEIVED = "invoice_received"
    CONTRACT = "contract"
    CIM = "cim"                       # Contract individual de munca
    LEASING_CONTRACT = "leasing_contract"
    UTILITY_BILL = "utility_bill"
    ESTIMATE = "estimate"
    BANK_STATEMENT = "bank_statement"
    PAYMENT_PROOF = "payment_proof"
    PAYSLIP = "payslip"               # Fluturas de salariu
    OTHER = "other"


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    VALIDATING = "validating"
    NEEDS_REVIEW = "needs_review"
    VALIDATED = "validated"
    STORED = "stored"
    FAILED = "failed"
    REJECTED = "rejected"


class Document(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )

    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type_enum"), nullable=False
    )
    document_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # Owner — links document to the user who uploaded it
    user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True,
    )

    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status_enum"),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
    )
    ocr_applied: Mapped[bool] = mapped_column(default=False, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    extraction_prompt_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    extraction_raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(nullable=True)
    extraction_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    contains_pii: Mapped[bool] = mapped_column(default=False, nullable=False)
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_documents_status_type", "processing_status", "document_type"),
    )


class DocumentProcessingLog(Base):
    __tablename__ = "document_processing_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    step: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

