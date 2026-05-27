import json
import logging
import time
from urllib.parse import quote

import httpx
from huggingface_hub import InferenceClient

from app.core.config import settings
from app.prompts.nivelamento_prompt import NIVELAMENTO_SYSTEM_PROMPT


logger = logging.getLogger(__name__)
_LLM_CACHE: dict[str, str] = {}
_LLM_CACHE_LIMIT = 200


def gerar_texto_nivelamento_llm(prompt: str, fallback_text: str) -> tuple[str, str]:
	return gerar_texto_llm(
		prompt=prompt,
		fallback_text=fallback_text,
		system_prompt=NIVELAMENTO_SYSTEM_PROMPT,
	)


def gerar_texto_llm(prompt: str, fallback_text: str, system_prompt: str) -> tuple[str, str]:
	provider = (settings.llm_provider or "fallback").strip().lower()
	provider_order = {
		"ollama": ["ollama", "groq", "huggingface"],
		"huggingface": ["huggingface", "groq", "ollama"],
		"groq": ["groq", "ollama", "huggingface"],
		"auto": ["groq", "huggingface", "ollama"],
		"fallback": [],
		"rule": [],
	}.get(provider, [])
	logger.info("LLM generation start. provider=%s provider_order=%s", provider, provider_order)

	for candidate in provider_order:
		cache_key = _build_cache_key(candidate, system_prompt, prompt)
		if candidate == "ollama":
			response = _gerar_com_ollama(prompt, system_prompt)
		elif candidate == "huggingface":
			response = _gerar_com_huggingface(prompt, system_prompt)
		else:
			response = _gerar_com_groq(prompt, system_prompt)
		text = _normalizar_texto_resposta(response)
		if text:
			_store_cache(cache_key, text)
			logger.info("LLM generation success. provider=%s", candidate)
			return text, candidate
		cached = _LLM_CACHE.get(cache_key)
		if cached:
			logger.warning("LLM provider=%s failed, using cached response.", candidate)
			return cached, candidate
		logger.warning("LLM generation empty response from provider=%s", candidate)

	if provider not in {"fallback", "rule"} and provider_order == []:
		logger.warning("LLM provider desconhecido: %s. Usando fallback.", provider)
	if provider_order:
		logger.warning("All configured LLM providers returned empty/failed responses. Using fallback.")

	return fallback_text, "fallback"


def _gerar_com_groq(prompt: str, system_prompt: str) -> str | None:
	if not settings.groq_api_token:
		logger.warning("Groq API token not configured.")
		return None

	headers = {
		"Authorization": f"Bearer {settings.groq_api_token}",
		"Content-Type": "application/json",
	}
	payload = {
		"model": settings.groq_chat_model,
		"messages": [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": prompt},
		],
		"temperature": settings.llm_temperature,
		"max_tokens": settings.llm_max_new_tokens,
	}

	for attempt in range(1, 4):
		try:
			with httpx.Client(timeout=45.0) as client:
				response = client.post(
					f"{settings.groq_base_url.rstrip('/')}/chat/completions",
					headers=headers,
					json=payload,
				)
				if response.status_code == 429:
					logger.warning("Groq rate limited (429). attempt=%s", attempt)
					if attempt < 3:
						time.sleep(1.0 * attempt)
						continue
				response.raise_for_status()
				data = response.json()
				if isinstance(data, dict):
					choices = data.get("choices")
					if isinstance(choices, list) and choices:
						first = choices[0]
						if isinstance(first, dict):
							message = first.get("message")
							if isinstance(message, dict):
								content = _normalizar_texto_resposta(message.get("content"))
								if content:
									return content
								reasoning = _normalizar_texto_resposta(message.get("reasoning_content"))
								if reasoning:
									return reasoning
				logger.warning("Groq returned payload without usable content.")
		except Exception as exc:
			logger.warning("Groq generation failed: %s", exc)
			if attempt < 3:
				time.sleep(1.0 * attempt)
				continue
			return None

	return None


def _gerar_com_ollama(prompt: str, system_prompt: str) -> str | None:
	payload = {
		"model": settings.ollama_chat_model,
		"prompt": f"{system_prompt}\n\n{prompt}",
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
			return _normalizar_texto_resposta(text)
	except Exception as exc:
		logger.warning("Ollama HTTP generation failed: %s", exc)

	langchain_response = _gerar_com_ollama_langchain(prompt, system_prompt)
	if langchain_response:
		return langchain_response
	return None


def _gerar_com_huggingface(prompt: str, system_prompt: str) -> str | None:
	router_chat_response = _gerar_com_huggingface_router_chat(prompt, system_prompt)
	if router_chat_response:
		return router_chat_response

	inference_client_response = _gerar_com_huggingface_inference_client(prompt, system_prompt)
	if inference_client_response:
		return inference_client_response

	if settings.huggingface_use_langchain:
		langchain_response = _gerar_com_huggingface_langchain(prompt, system_prompt)
		if langchain_response:
			return langchain_response

	if not settings.huggingface_api_token:
		logger.warning("Hugging Face API token not configured.")
		return None

	headers = {
		"Authorization": f"Bearer {settings.huggingface_api_token}",
		"Content-Type": "application/json",
	}
	payload = {
		"inputs": f"{system_prompt}\n\n{prompt}",
		"parameters": {
			"max_new_tokens": settings.llm_max_new_tokens,
			"temperature": settings.llm_temperature,
			"return_full_text": False,
		},
		"options": {
			"wait_for_model": True,
		},
	}
	for model in _huggingface_model_candidates():
		for endpoint in _huggingface_http_endpoints(model):
			try:
				with httpx.Client(timeout=45.0) as client:
					response = client.post(
						endpoint,
						headers=headers,
						json=payload,
					)
					response.raise_for_status()
					data = response.json()
					parsed = _parse_huggingface_text_payload(data)
					if parsed:
						logger.info("Hugging Face HTTP generation success. model=%s endpoint=%s", model, endpoint)
						return parsed
					logger.warning(
						"Hugging Face HTTP returned unsupported/empty payload. model=%s endpoint=%s payload_type=%s",
						model,
						endpoint,
						type(data).__name__,
					)
			except Exception as exc:
				logger.warning("Hugging Face HTTP generation failed. model=%s endpoint=%s error=%s", model, endpoint, exc)
	return None


def _gerar_com_huggingface_router_chat(prompt: str, system_prompt: str) -> str | None:
	if not settings.huggingface_api_token:
		return None

	headers = {
		"Authorization": f"Bearer {settings.huggingface_api_token}",
		"Content-Type": "application/json",
	}

	for model in _huggingface_model_candidates():
		payload = {
			"model": model,
			"messages": [
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": prompt},
			],
			"max_tokens": settings.llm_max_new_tokens,
			"temperature": settings.llm_temperature,
		}
		try:
			with httpx.Client(timeout=45.0) as client:
				response = client.post(
					"https://router.huggingface.co/v1/chat/completions",
					headers=headers,
					json=payload,
				)
				response.raise_for_status()
				data = response.json()
				if isinstance(data, dict):
					choices = data.get("choices")
					if isinstance(choices, list) and choices:
						first = choices[0]
						if isinstance(first, dict):
							message = first.get("message")
							if isinstance(message, dict):
								content = _normalizar_texto_resposta(message.get("content"))
								if content:
									logger.info("Hugging Face Router chat success. model=%s", model)
									return content
				logger.warning("Hugging Face Router chat returned payload without content. model=%s", model)
		except Exception as exc:
			logger.warning("Hugging Face Router chat failed. model=%s error=%s", model, exc)

	return None


def _gerar_com_huggingface_inference_client(prompt: str, system_prompt: str) -> str | None:
	if not settings.huggingface_api_token:
		return None

	for model in _huggingface_model_candidates():
		try:
			client = InferenceClient(api_key=settings.huggingface_api_token)
			completion = client.chat.completions.create(
				model=model,
				messages=[
					{"role": "system", "content": system_prompt},
					{"role": "user", "content": prompt},
				],
				max_tokens=settings.llm_max_new_tokens,
				temperature=settings.llm_temperature,
			)
			if completion and completion.choices:
				message = completion.choices[0].message
				if message:
					text = _normalizar_texto_resposta(message.content)
					if text:
						logger.info("Hugging Face InferenceClient generation success. model=%s", model)
						return text
			logger.warning("Hugging Face InferenceClient returned completion without usable content. model=%s", model)
		except Exception as exc:
			logger.warning("Hugging Face InferenceClient generation failed. model=%s error=%s", model, exc)
	return None


def _huggingface_model_candidates() -> list[str]:
	configured = (settings.huggingface_chat_model or "").strip()
	if not configured:
		return []

	candidates = [configured]
	if configured == "meta-llama/Llama-3.1-8B-Instruct":
		candidates.append("meta-llama/Meta-Llama-3.1-8B-Instruct")
	if configured == "meta-llama/Meta-Llama-3.1-8B-Instruct":
		candidates.append("meta-llama/Llama-3.1-8B-Instruct")

	# Deduplicate while preserving order.
	seen: set[str] = set()
	result: list[str] = []
	for item in candidates:
		if item in seen:
			continue
		seen.add(item)
		result.append(item)
	return result


def _huggingface_http_endpoints(model: str) -> list[str]:
	encoded_model = quote(model, safe="")
	return [
		f"https://router.huggingface.co/hf-inference/models/{model}",
		f"https://api-inference.huggingface.co/models/{encoded_model}",
	]


def _parse_huggingface_text_payload(data: object) -> str | None:
	if isinstance(data, list) and data:
		first = data[0]
		if isinstance(first, dict):
			generated = first.get("generated_text")
			parsed = _normalizar_texto_resposta(generated)
			if parsed:
				return parsed

	if isinstance(data, dict):
		if "generated_text" in data:
			parsed = _normalizar_texto_resposta(data["generated_text"])
			if parsed:
				return parsed
		if "error" in data:
			logger.warning("Hugging Face inference error payload: %s", data.get("error"))
			return None

	if isinstance(data, str):
		try:
			parsed_data = json.loads(data)
		except Exception:
			return _normalizar_texto_resposta(data)
		if isinstance(parsed_data, list) and parsed_data:
			entry = parsed_data[0]
			if isinstance(entry, dict):
				generated = entry.get("generated_text")
				normalized = _normalizar_texto_resposta(generated)
				if normalized:
					return normalized
	return None


def _gerar_com_ollama_langchain(prompt: str, system_prompt: str) -> str | None:
	try:
		from langchain_core.output_parsers import StrOutputParser
		from langchain_core.prompts import ChatPromptTemplate
		from langchain_ollama import ChatOllama

		chat_prompt = ChatPromptTemplate.from_messages(
			[
				("system", system_prompt),
				("human", "{user_prompt}"),
			]
		)
		llm = ChatOllama(
			model=settings.ollama_chat_model,
			base_url=settings.ollama_base_url,
			temperature=settings.llm_temperature,
		)
		chain = chat_prompt | llm | StrOutputParser()
		result = chain.invoke({"user_prompt": prompt})
		return _normalizar_texto_resposta(result)
	except Exception as exc:
		logger.warning("Ollama LangChain generation failed: %s", exc)
		return None
	return None


def _gerar_com_huggingface_langchain(prompt: str, system_prompt: str) -> str | None:
	if not settings.huggingface_api_token:
		return None

	try:
		from langchain_core.output_parsers import StrOutputParser
		from langchain_core.prompts import PromptTemplate

		try:
			from langchain_huggingface import HuggingFaceEndpoint as HfEndpoint

			llm = HfEndpoint(
				model=settings.huggingface_chat_model,
				huggingfacehub_api_token=settings.huggingface_api_token,
				temperature=settings.llm_temperature,
				max_new_tokens=settings.llm_max_new_tokens,
				task="text-generation",
				return_full_text=False,
			)
		except ImportError:
			from langchain_community.llms import HuggingFaceEndpoint as HfEndpoint

			llm = HfEndpoint(
				model=settings.huggingface_chat_model,
				huggingfacehub_api_token=settings.huggingface_api_token,
				temperature=settings.llm_temperature,
				max_new_tokens=settings.llm_max_new_tokens,
				task="text-generation",
				return_full_text=False,
			)

		template = PromptTemplate.from_template("{system}\n\n{user_prompt}")
		chain = template | llm | StrOutputParser()
		result = chain.invoke(
			{
				"system": system_prompt,
				"user_prompt": prompt,
			}
		)
		return _normalizar_texto_resposta(result)
	except Exception as exc:
		logger.warning("Hugging Face LangChain generation failed: %s", exc)
		return None
	return None


def _normalizar_texto_resposta(value: object) -> str | None:
	if not isinstance(value, str):
		return None
	text = value.strip()
	if not text:
		return None

	if "```" in text:
		text = text.replace("```json", "").replace("```", "").strip()

	return text or None


def _build_cache_key(provider: str, system_prompt: str, prompt: str) -> str:
	return f"{provider}::{hash(system_prompt)}::{hash(prompt)}"


def _store_cache(cache_key: str, text: str) -> None:
	if cache_key in _LLM_CACHE:
		_LLM_CACHE[cache_key] = text
		return
	if len(_LLM_CACHE) >= _LLM_CACHE_LIMIT:
		first_key = next(iter(_LLM_CACHE.keys()))
		_LLM_CACHE.pop(first_key, None)
	_LLM_CACHE[cache_key] = text
