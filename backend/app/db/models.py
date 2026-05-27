from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentChunk(Base):
	__tablename__ = "document_chunks"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	source: Mapped[str] = mapped_column(String(255), nullable=False)
	chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
	chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
	embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
	prerequisite_tag: Mapped[str | None] = mapped_column(String(120), nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)


class StudentReadiness(Base):
	__tablename__ = "student_readiness"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	student_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
	is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
	gaps_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
	support_text: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)


class StudentMemorizedConcept(Base):
	__tablename__ = "student_memorized_concepts"
	__table_args__ = (
		UniqueConstraint("student_id", "normalized_concept", name="uq_student_memorized_concept"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	student_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
	concept: Mapped[str] = mapped_column(String(255), nullable=False)
	normalized_concept: Mapped[str] = mapped_column(String(255), nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)
