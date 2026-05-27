#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

import httpx

DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_API_PREFIX = "/api/v1"


def ingest_lesson(client: httpx.Client, base_url: str) -> dict:
    url = f"{base_url}{DEFAULT_API_PREFIX}/nivelamento/ingest"
    response = client.post(url)
    response.raise_for_status()
    return response.json()


def run_consolidacao(client: httpx.Client, base_url: str, payload: dict) -> dict:
    url = f"{base_url}{DEFAULT_API_PREFIX}/consolidacao"
    response = client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teste o fluxo de consolidacao de aprendizagem da API de calculo."
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
        default="Conheco limites e derivadas basicas, mas tenho duvidas na regra da cadeia.",
        help="Background do aluno para consolidacao.",
    )
    parser.add_argument(
        "--known-topics",
        nargs="*",
        default=["Limites", "Derivada"],
        help="Topicos conhecidos pelo aluno.",
    )
    parser.add_argument(
        "--answered-questions",
        nargs="*",
        default=[
            "Derivada e a taxa de variacao instantanea.",
            "Tenho dificuldade para identificar quando usar regra da cadeia.",
        ],
        help="Respostas curtas do aluno para diagnostico de consolidacao.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = {
        "student_id": args.student_id,
        "student_background": args.student_background,
        "known_topics": args.known_topics,
        "answered_questions": args.answered_questions,
    }

    with httpx.Client(timeout=40.0) as client:
        print("[1/2] Ingerindo a aula de Calculo I no backend...")
        ingest_result = ingest_lesson(client, args.backend_url)
        print(json.dumps(ingest_result, indent=2, ensure_ascii=False))

        print("\n[2/2] Avaliando consolidacao de aprendizagem...")
        consolidacao_result = run_consolidacao(client, args.backend_url, payload)
        print(json.dumps(consolidacao_result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
