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
	langchain_response = _gerar_com_ollama_langchain(prompt)
	if langchain_response:
		return langchain_response

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
	langchain_response = _gerar_com_huggingface_langchain(prompt)
	if langchain_response:
		return langchain_response

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


def _gerar_com_ollama_langchain(prompt: str) -> str | None:
	try:
		from langchain_core.output_parsers import StrOutputParser
		from langchain_core.prompts import ChatPromptTemplate
		from langchain_ollama import ChatOllama

		chat_prompt = ChatPromptTemplate.from_messages(
			[
				("system", NIVELAMENTO_SYSTEM_PROMPT),
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
		if isinstance(result, str) and result.strip():
			return result.strip()
	except Exception:
		return None
	return None


def _gerar_com_huggingface_langchain(prompt: str) -> str | None:
	if not settings.huggingface_api_token:
		return None

	try:
		from langchain_core.output_parsers import StrOutputParser
		from langchain_core.prompts import PromptTemplate

		try:
			from langchain_huggingface import HuggingFaceEndpoint
		except Exception:
			from langchain_community.llms import HuggingFaceEndpoint

		template = PromptTemplate.from_template("{system}\n\n{user_prompt}")
		llm = HuggingFaceEndpoint(
			repo_id=settings.huggingface_chat_model,
			huggingfacehub_api_token=settings.huggingface_api_token,
			temperature=settings.llm_temperature,
			max_new_tokens=settings.llm_max_new_tokens,
            model=settings.huggingface_chat_model,
		)
		chain = template | llm | StrOutputParser()
		result = chain.invoke(
			{
				"system": NIVELAMENTO_SYSTEM_PROMPT,
				"user_prompt": prompt,
			}
		)
		if isinstance(result, str) and result.strip():
			return result.strip()
	except Exception:
		return None
	return None
