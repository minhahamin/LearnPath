from datetime import datetime

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # 'running' is added on top of the spec's success|partial|failed so the
    # frontend can poll a single status field while the ReAct loop executes.
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")
    # {resource_url: completed_bool} - kept separate from result_json so the
    # LLM's original output stays untouched and auditable.
    progress_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    steps: Mapped[list["ReactStep"]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan", order_by="ReactStep.step_order"
    )
    logs: Mapped[list["RunLog"]] = relationship(back_populates="roadmap", cascade="all, delete-orphan")


class ReactStep(Base):
    __tablename__ = "react_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.id", ondelete="CASCADE"))
    step_order: Mapped[int] = mapped_column(nullable=False)
    step_type: Mapped[str] = mapped_column(Text, nullable=False)  # thought | action | observation
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # structured detail behind the human-readable `content` summary - e.g. the
    # per-result evaluations (title/url/level/confidence/reason) for an
    # observation step. None for steps with nothing extra to show.
    data: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    roadmap: Mapped["Roadmap"] = relationship(back_populates="steps")


class RunLog(Base):
    __tablename__ = "run_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.id", ondelete="CASCADE"))
    retry_count: Mapped[int] = mapped_column(default=0)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    roadmap: Mapped["Roadmap"] = relationship(back_populates="logs")
