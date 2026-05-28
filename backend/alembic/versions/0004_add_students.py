"""add students table

Revision ID: 0004_add_students
Revises: 0003_add_student_memorized_concepts
Create Date: 2026-05-28 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_add_students"
down_revision: str | None = "0003_add_student_memorized_concepts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.String(length=120), nullable=False),
        sa.Column("background", sa.Text(), nullable=True),
        sa.Column("known_topics_json", sa.Text(), nullable=True),
        sa.Column("consolidation_history_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_students_student_id"),
    )
    op.create_index("ix_students_id", "students", ["id"], unique=False)
    op.create_index("ix_students_student_id", "students", ["student_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_students_student_id", table_name="students")
    op.drop_index("ix_students_id", table_name="students")
    op.drop_table("students")
