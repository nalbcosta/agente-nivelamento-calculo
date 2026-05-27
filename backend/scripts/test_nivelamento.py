#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

import httpx

DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_API_PREFIX = "/api/v1"


def ingest_lesson(client: httpx.Client, base_url: str) -> dict:
    url = f"{base_url}{DEFAULT_API_PREFIX}/nivelamento/ingest"
    response = client.post(url)
    response.raise_for_status()
    return response.json()


def run_nivelamento(client: httpx.Client, base_url: str, payload: dict) -> dict:
    url = f"{base_url}{DEFAULT_API_PREFIX}/nivelamento"
    response = client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def _normalize(items: list[str]) -> set[str]:
    return {item.strip().lower() for item in items if isinstance(item, str) and item.strip()}


def _validate_nivelamento_response(result: dict) -> tuple[bool, str]:
    prerequisites = result.get("extracted_prerequisites", [])
    support_text = result.get("support_text", "")
    missing = result.get("missing_prerequisites", [])
    lesson_topics = result.get("detected_lesson_topics", [])

    if not isinstance(prerequisites, list) or len(prerequisites) == 0:
        return False, "Nao retornou pre-requisitos extraidos da aula."

    if not isinstance(support_text, str) or len(support_text.strip()) < 30:
        return False, "Nao retornou conteudo breve de nivelamento com qualidade minima."

    extracted_norm = _normalize(prerequisites)
    if "calculo" in extracted_norm:
        return False, "Pre-requisitos invalidos: retornou termo generico em vez de fundamentos especificos."

    if not isinstance(lesson_topics, list) or len(lesson_topics) == 0:
        return False, "Nao retornou topicos detectados da aula para contextualizar o nivelamento."

    if not isinstance(missing, list):
        return False, "Campo missing_prerequisites invalido."

    return True, "Case 1 validado: pre-requisitos extraidos e nivelamento explicativo retornado."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teste o fluxo de ingestão e nivelamento da API de cálculo."
    )
    parser.add_argument(
        "--backend-url",
        default=DEFAULT_BACKEND_URL,
        help="URL base do backend FastAPI (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--student-id",
        default="aluno_001",
        help="Identificador do aluno usado no payload.",
    )
    parser.add_argument(
        "--student-background",
        default="Conheco funcoes, regras de potencia e trigonometria.",
        help="Background do aluno para nivelamento.",
    )
    parser.add_argument(
        "--known-topics",
        nargs="*",
        default=["Funcoes", "Regras de Potencia e Algebra", "Trigonometria"],
        help="Topicos conhecidos pelo aluno.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = {
        "student_id": args.student_id,
        "student_background": args.student_background,
        "known_topics": args.known_topics,
    }

    with httpx.Client(timeout=30.0) as client:
        print("[1/2] Ingerindo a aula de Calculo I no backend...")
        ingest_result = ingest_lesson(client, args.backend_url)
        print(json.dumps(ingest_result, indent=2, ensure_ascii=False))

        print("\n[2/2] Avaliando nivelamento do aluno...")
        nivelamento_result = run_nivelamento(client, args.backend_url, payload)
        print(json.dumps(nivelamento_result, indent=2, ensure_ascii=False))

        ok, message = _validate_nivelamento_response(nivelamento_result)
        if not ok:
            print(f"\n[ERRO] {message}")
            return 1
        print(f"\n[OK] {message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
