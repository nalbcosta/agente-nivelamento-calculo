"""add student memorized concepts table

Revision ID: 0003_add_student_memorized_concepts
Revises: 0002_add_pgvector_to_document_chunks
Create Date: 2026-05-27 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_student_memorized_concepts"
down_revision: str | None = "0002_add_pgvector_to_document_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_memorized_concepts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.String(length=120), nullable=False),
        sa.Column("concept", sa.String(length=255), nullable=False),
        sa.Column("normalized_concept", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "normalized_concept", name="uq_student_memorized_concept"),
    )
    op.create_index("ix_student_memorized_concepts_id", "student_memorized_concepts", ["id"], unique=False)
    op.create_index(
        "ix_student_memorized_concepts_student_id",
        "student_memorized_concepts",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_student_memorized_concepts_student_id", table_name="student_memorized_concepts")
    op.drop_index("ix_student_memorized_concepts_id", table_name="student_memorized_concepts")
    op.drop_table("student_memorized_concepts")
