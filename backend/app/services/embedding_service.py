import hashlib
import math
from functools import lru_cache

import httpx

from app.core.config import settings


@lru_cache(maxsize=1)
def _load_fastembed_model():
	from fastembed import TextEmbedding

	return TextEmbedding(model_name=settings.embedding_model_name)


def gerar_embedding(texto: str) -> list[float]:
	if not texto.strip():
		return [0.0] * settings.embedding_dimension

	provider = (settings.embedding_provider or "fastembed").lower()
	if provider == "ollama":
		vector = _gerar_embedding_ollama(texto)
		if vector:
			return _ajustar_dimensao(vector)
		return _gerar_embedding_fallback(texto)
	if provider == "huggingface":
		vector = _gerar_embedding_huggingface(texto)
		if vector:
			return _ajustar_dimensao(vector)
		return _gerar_embedding_fallback(texto)

	try:
		model = _load_fastembed_model()
		vector = next(model.embed([texto]))
		as_list = vector.tolist() if hasattr(vector, "tolist") else list(vector)
		return _ajustar_dimensao(as_list)
	except Exception:
		return _gerar_embedding_fallback(texto)


def gerar_embeddings(textos: list[str]) -> list[list[float]]:
	if not textos:
		return []
	return [gerar_embedding(texto) for texto in textos]


def _gerar_embedding_fallback(texto: str) -> list[float]:
	# Fallback deterministico para manter o fluxo do RAG mesmo sem modelo local.
	digest = hashlib.sha256(texto.encode("utf-8")).digest()
	values: list[float] = []
	while len(values) < settings.embedding_dimension:
		for byte in digest:
			values.append((byte / 255.0) * 2.0 - 1.0)
			if len(values) == settings.embedding_dimension:
				break

	norm = math.sqrt(sum(value * value for value in values)) or 1.0
	return [value / norm for value in values]


def _gerar_embedding_ollama(texto: str) -> list[float] | None:
	payload = {
		"model": settings.ollama_embedding_model,
		"prompt": texto,
	}
	try:
		with httpx.Client(timeout=30.0) as client:
			response = client.post(
				f"{settings.ollama_base_url.rstrip('/')}/api/embeddings",
				json=payload,
			)
			response.raise_for_status()
			data = response.json()
			emb = data.get("embedding")
			if isinstance(emb, list):
				return [float(x) for x in emb]
	except Exception:
		return None
	return None


def _gerar_embedding_huggingface(texto: str) -> list[float] | None:
	if not settings.huggingface_api_token:
		return None

	headers = {
		"Authorization": f"Bearer {settings.huggingface_api_token}",
		"Content-Type": "application/json",
	}
	payload = {"inputs": texto}
	try:
		with httpx.Client(timeout=40.0) as client:
			response = client.post(
				f"https://api-inference.huggingface.co/pipeline/feature-extraction/{settings.huggingface_embedding_model}",
				headers=headers,
				json=payload,
			)
			response.raise_for_status()
			data = response.json()
			if isinstance(data, list) and data:
				if isinstance(data[0], list):
					# Alguns modelos retornam token embeddings; fazemos mean pooling.
					token_vectors = data
					first_len = len(token_vectors[0]) if token_vectors[0] else 0
					if first_len:
						means: list[float] = []
						for idx in range(first_len):
							col_sum = 0.0
							count = 0
							for token in token_vectors:
								if idx < len(token):
									col_sum += float(token[idx])
									count += 1
							means.append(col_sum / count if count else 0.0)
						return means
				return [float(x) for x in data]
	except Exception:
		return None
	return None


def _ajustar_dimensao(vector: list[float]) -> list[float]:
	if len(vector) >= settings.embedding_dimension:
		return vector[: settings.embedding_dimension]
	return vector + [0.0] * (settings.embedding_dimension - len(vector))
