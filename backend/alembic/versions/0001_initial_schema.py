"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-05-25 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("prerequisite_tag", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_id", "document_chunks", ["id"], unique=False)

    op.create_table(
        "student_readiness",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.String(length=120), nullable=False),
        sa.Column("is_ready", sa.Boolean(), nullable=False),
        sa.Column("gaps_summary", sa.Text(), nullable=True),
        sa.Column("support_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_readiness_id", "student_readiness", ["id"], unique=False)
    op.create_index(
        "ix_student_readiness_student_id",
        "student_readiness",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_student_readiness_student_id", table_name="student_readiness")
    op.drop_index("ix_student_readiness_id", table_name="student_readiness")
    op.drop_table("student_readiness")

    op.drop_index("ix_document_chunks_id", table_name="document_chunks")
    op.drop_table("document_chunks")
