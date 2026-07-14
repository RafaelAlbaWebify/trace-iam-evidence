"""Create immutable investigation timeline events.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("investigation_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_label", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.String(length=512), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_timeline_events_investigation_created",
        "timeline_events",
        ["investigation_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_timeline_events_investigation_created", table_name="timeline_events")
    op.drop_table("timeline_events")
