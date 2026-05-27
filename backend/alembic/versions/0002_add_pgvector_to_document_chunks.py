"""add pgvector columns to document_chunks

Revision ID: 0002_add_pgvector_to_document_chunks
Revises: 0001_initial_schema
Create Date: 2026-05-25 01:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0002_add_pgvector_to_document_chunks"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("document_chunks", sa.Column("chunk_index", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("embedding", Vector(384), nullable=True))

    op.execute("UPDATE document_chunks SET chunk_index = id WHERE chunk_index IS NULL")
    op.alter_column("document_chunks", "chunk_index", nullable=False)

    op.create_index(
        "ix_document_chunks_source_chunk_index",
        "document_chunks",
        ["source", "chunk_index"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.drop_index("ix_document_chunks_source_chunk_index", table_name="document_chunks")
    op.drop_column("document_chunks", "embedding")
    op.drop_column("document_chunks", "chunk_index")
