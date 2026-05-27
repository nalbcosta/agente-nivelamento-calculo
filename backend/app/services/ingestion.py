from pathlib import Path
import unicodedata

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.services.embedding_service import gerar_embeddings


PREREQUISITES = [
	"Funcoes",
	"Regras de Potencia e Algebra",
	"Trigonometria",
]

TOPICS = [
	"Limites",
	"Regra de L'Hopital",
	"Derivada",
	"Regra da Cadeia",
]


def processar_documento(caminho: str) -> dict[str, object]:
	path = Path(caminho)
	if not path.exists():
		return {
			"status": "error",
			"message": f"Arquivo nao encontrado: {caminho}",
			"lesson_text": "",
			"prerequisites": [],
			"topics": [],
		}

	lesson_text = path.read_text(encoding="utf-8")
	prerequisites = extrair_prerequisitos(lesson_text)
	topics = extrair_topicos(lesson_text)

	return {
		"status": "ok",
		"message": "Documento processado com sucesso",
		"lesson_text": lesson_text,
		"chunks": gerar_chunks(lesson_text),
		"prerequisites": prerequisites,
		"topics": topics,
	}


def ingerir_documento_no_pgvector(db: Session, caminho: str, source: str) -> dict[str, object]:
	processed = processar_documento(caminho)
	if processed.get("status") != "ok":
		return processed

	chunks = processed.get("chunks", [])
	if not isinstance(chunks, list) or not chunks:
		return {
			"status": "error",
			"message": "Nao foi possivel gerar chunks para ingestao",
		}

	embeddings = gerar_embeddings([chunk for chunk in chunks if isinstance(chunk, str)])

	db.execute(delete(DocumentChunk).where(DocumentChunk.source == source))

	rows = []
	for idx, chunk in enumerate(chunks):
		embedding = embeddings[idx] if idx < len(embeddings) else None
		rows.append(
			DocumentChunk(
				source=source,
				chunk_index=idx,
				chunk_text=chunk,
				embedding=embedding,
			)
		)

	db.add_all(rows)
	db.commit()

	return {
		"status": "ok",
		"message": "Documento ingerido no pgvector",
		"chunks_count": len(rows),
		"prerequisites": processed.get("prerequisites", []),
		"topics": processed.get("topics", []),
	}


def extrair_prerequisitos(lesson_text: str) -> list[str]:
	if not lesson_text:
		return []

	normalized_text = normalizar_texto(lesson_text)

	found: list[str] = []
	for item in PREREQUISITES:
		if normalizar_texto(item) in normalized_text:
			found.append(item)
	return found


def extrair_topicos(lesson_text: str) -> list[str]:
	if not lesson_text:
		return []

	normalized_text = normalizar_texto(lesson_text)

	found: list[str] = []
	for item in TOPICS:
		if normalizar_texto(item) in normalized_text:
			found.append(item)
	return found


def normalizar_texto(texto: str) -> str:
	normalized = unicodedata.normalize("NFD", texto)
	without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
	return without_marks.lower()


def gerar_chunks(lesson_text: str) -> list[str]:
	if not lesson_text:
		return []

	parts = [part.strip() for part in lesson_text.split("\n\n") if part.strip()]
	chunks: list[str] = []
	current = ""
	max_size = 700

	for part in parts:
		candidate = f"{current}\n\n{part}".strip() if current else part
		if len(candidate) <= max_size:
			current = candidate
		else:
			if current:
				chunks.append(current)
			current = part

	if current:
		chunks.append(current)

	return chunks
