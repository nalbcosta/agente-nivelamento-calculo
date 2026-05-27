import json
import logging

import httpx
from huggingface_hub import InferenceClient

from app.core.config import settings
from app.prompts.nivelamento_prompt import NIVELAMENTO_SYSTEM_PROMPT


logger = logging.getLogger(__name__)


def gerar_texto_nivelamento_llm(prompt: str, fallback_text: str) -> tuple[str, str]:
	return gerar_texto_llm(
		prompt=prompt,
		fallback_text=fallback_text,
		system_prompt=NIVELAMENTO_SYSTEM_PROMPT,
	)


def gerar_texto_llm(prompt: str, fallback_text: str, system_prompt: str) -> tuple[str, str]:
	provider = (settings.llm_provider or "fallback").strip().lower()
	provider_order = {
		"ollama": ["ollama"],
		"huggingface": ["huggingface"],
		"auto": ["huggingface", "ollama"],
		"fallback": [],
		"rule": [],
	}.get(provider, [])

	for candidate in provider_order:
		response = _gerar_com_ollama(prompt, system_prompt) if candidate == "ollama" else _gerar_com_huggingface(prompt, system_prompt)
		text = _normalizar_texto_resposta(response)
		if text:
			return text, candidate

	if provider not in {"fallback", "rule"} and provider_order == []:
		logger.warning("LLM provider desconhecido: %s. Usando fallback.", provider)

	return fallback_text, "fallback"


def _gerar_com_ollama(prompt: str, system_prompt: str) -> str | None:
	langchain_response = _gerar_com_ollama_langchain(prompt, system_prompt)
	if langchain_response:
		return langchain_response

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
	except Exception:
		return None


def _gerar_com_huggingface(prompt: str, system_prompt: str) -> str | None:
	inference_client_response = _gerar_com_huggingface_inference_client(prompt, system_prompt)
	if inference_client_response:
		return inference_client_response

	if settings.huggingface_use_langchain:
		langchain_response = _gerar_com_huggingface_langchain(prompt, system_prompt)
		if langchain_response:
			return langchain_response

	if not settings.huggingface_api_token:
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
	try:
		with httpx.Client(timeout=45.0) as client:
			response = client.post(
				f"https://router.huggingface.co/hf-inference/models/{settings.huggingface_chat_model}",
				headers=headers,
				json=payload,
			)
			response.raise_for_status()
			data = response.json()
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
					logger.warning("Hugging Face inference error: %s", data.get("error"))
					return None
			if isinstance(data, str):
				try:
					parsed = json.loads(data)
				except Exception:
					return _normalizar_texto_resposta(data)
				if isinstance(parsed, list) and parsed:
					entry = parsed[0]
					if isinstance(entry, dict):
						generated = entry.get("generated_text")
						normalized = _normalizar_texto_resposta(generated)
						if normalized:
							return normalized
	except Exception as exc:
		logger.warning("Hugging Face HTTP generation failed: %s", exc)
		return None
	return None


def _gerar_com_huggingface_inference_client(prompt: str, system_prompt: str) -> str | None:
	if not settings.huggingface_api_token:
		return None

	try:
		client = InferenceClient(api_key=settings.huggingface_api_token)
		completion = client.chat.completions.create(
			model=settings.huggingface_chat_model,
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
				return _normalizar_texto_resposta(message.content)
	except Exception as exc:
		logger.warning("Hugging Face InferenceClient generation failed: %s", exc)
		return None
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
	except Exception:
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
