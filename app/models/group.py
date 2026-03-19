import uuid
from datetime import datetime, timezone

from sqlalchemy import Index, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_profiles.id"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_groups_profile_run", "profile_id", "run_id"),
    )
