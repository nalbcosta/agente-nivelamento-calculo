import json

import httpx

from app.core.config import settings
from app.prompts.nivelamento_prompt import NIVELAMENTO_SYSTEM_PROMPT


def gerar_texto_nivelamento_llm(prompt: str, fallback_text: str) -> str:
	provider = (settings.llm_provider or "rule").lower()
	if provider == "ollama":
		response = _gerar_com_ollama(prompt)
		if response:
			return response
		return fallback_text
	if provider == "huggingface":
		response = _gerar_com_huggingface(prompt)
		if response:
			return response
		return fallback_text
	return fallback_text


def _gerar_com_ollama(prompt: str) -> str | None:
	payload = {
		"model": settings.ollama_chat_model,
		"prompt": f"{NIVELAMENTO_SYSTEM_PROMPT}\n\n{prompt}",
		"stream": False,
		"options": {
			"temperature": settings.llm_temperature,
		},
	}
	try:
		with httpx.Client(timeout=40.0) as client:
			response = client.post(
				f"{settings.ollama_base_url.rstrip('/')}/api/generate",
				json=payload,
			)
			response.raise_for_status()
			data = response.json()
			text = data.get("response")
			return text.strip() if isinstance(text, str) and text.strip() else None
	except Exception:
		return None


def _gerar_com_huggingface(prompt: str) -> str | None:
	if not settings.huggingface_api_token:
		return None

	headers = {
		"Authorization": f"Bearer {settings.huggingface_api_token}",
		"Content-Type": "application/json",
	}
	payload = {
		"inputs": f"{NIVELAMENTO_SYSTEM_PROMPT}\n\n{prompt}",
		"parameters": {
			"max_new_tokens": settings.llm_max_new_tokens,
			"temperature": settings.llm_temperature,
			"return_full_text": False,
		},
	}
	try:
		with httpx.Client(timeout=45.0) as client:
			response = client.post(
				f"https://api-inference.huggingface.co/models/{settings.huggingface_chat_model}",
				headers=headers,
				json=payload,
			)
			response.raise_for_status()
			data = response.json()
			if isinstance(data, list) and data:
				first = data[0]
				if isinstance(first, dict):
					generated = first.get("generated_text")
					if isinstance(generated, str) and generated.strip():
						return generated.strip()
			if isinstance(data, dict):
				if "generated_text" in data and isinstance(data["generated_text"], str):
					return data["generated_text"].strip()
				if "error" in data:
					return None
			if isinstance(data, str):
				parsed = json.loads(data)
				if isinstance(parsed, list) and parsed:
					entry = parsed[0]
					if isinstance(entry, dict):
						generated = entry.get("generated_text")
						if isinstance(generated, str) and generated.strip():
							return generated.strip()
	except Exception:
		return None
	return None
