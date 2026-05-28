"""resize embedding column to 1536 for gemini-embedding-2 (MRL truncated)

Revision ID: 0004_resize_embedding_to_3072
Revises: 0003_add_student_memorized_concepts
Create Date: 2026-05-28 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0004_resize_embedding_to_3072"
down_revision: str | None = "0003_add_student_memorized_concepts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_DIM = 384
_NEW_DIM = 1536  # MRL-truncated from 3072 to stay within pgvector ivfflat 2000-dim limit


def upgrade() -> None:
    # Drop the old index — cannot exist while the column type changes.
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")

    # Drop and re-add the column because PostgreSQL cannot alter a vector dimension in-place.
    # Existing embeddings are incompatible; the ingestion endpoint must be called again.
    op.drop_column("document_chunks", "embedding")
    op.add_column("document_chunks", sa.Column("embedding", Vector(_NEW_DIM), nullable=True))

    # Re-create the approximate-search index.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.drop_column("document_chunks", "embedding")
    op.add_column("document_chunks", sa.Column("embedding", Vector(_OLD_DIM), nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
