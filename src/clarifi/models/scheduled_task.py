import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base


class ScheduleType(str, enum.Enum):
    ONE_SHOT = "one_shot"
    RECURRING = "recurring"


class ScheduledTask(Base, AuditMixin):
    """Tasks that the agent schedules for itself or the user creates.

    The background worker polls this table and triggers the agent
    when next_run_at <= now().
    """

    __tablename__ = "scheduled_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # What
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType, name="schedule_type_enum"),
        nullable=False,
    )
    cron_expression: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Execution tracking
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Owner
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Origin
    created_by_agent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )

    # What to trigger
    trigger_flow_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="conversation",
    )
    trigger_message: Mapped[str] = mapped_column(
        Text, nullable=False,
    )

    # Link to related entity
    related_entity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    related_entity_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
    )

    # Extra data
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notification_channels: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )

    __table_args__ = (
        Index("ix_scheduled_tasks_active_next", "is_active", "next_run_at"),
        Index("ix_scheduled_tasks_entity", "related_entity_type", "related_entity_id"),
    )
