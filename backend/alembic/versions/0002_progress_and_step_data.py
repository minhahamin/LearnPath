"""add roadmaps.progress_json and react_steps.data

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "roadmaps",
        sa.Column("progress_json", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column("react_steps", sa.Column("data", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("react_steps", "data")
    op.drop_column("roadmaps", "progress_json")
