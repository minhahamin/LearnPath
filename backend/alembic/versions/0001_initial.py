"""initial schema: roadmaps, react_steps, run_logs

Revision ID: 0001
Revises:
Create Date: 2026-09-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roadmaps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "react_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "roadmap_id", sa.Integer(), sa.ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_react_steps_roadmap_id", "react_steps", ["roadmap_id"])

    op.create_table(
        "run_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "roadmap_id", sa.Integer(), sa.ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_run_logs_roadmap_id", "run_logs", ["roadmap_id"])


def downgrade() -> None:
    op.drop_index("ix_run_logs_roadmap_id", table_name="run_logs")
    op.drop_table("run_logs")
    op.drop_index("ix_react_steps_roadmap_id", table_name="react_steps")
    op.drop_table("react_steps")
    op.drop_table("roadmaps")
