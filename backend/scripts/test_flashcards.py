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


def run_flashcards(client: httpx.Client, base_url: str, payload: dict) -> dict:
    url = f"{base_url}{DEFAULT_API_PREFIX}/flashcards"
    response = client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teste o Case 3 de memorizacao (flashcards) da API de calculo."
    )
    parser.add_argument(
        "--backend-url",
        default=DEFAULT_BACKEND_URL,
        help="URL base do backend FastAPI (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--student-id",
        default="aluno_flashcard_001",
        help="Identificador do aluno usado no payload.",
    )
    parser.add_argument(
        "--student-background",
        default="Ja estudei limites e derivadas basicas, mas erro aplicacao da regra da cadeia.",
        help="Background do aluno para memorizacao.",
    )
    parser.add_argument(
        "--known-topics",
        nargs="*",
        default=["Limites", "Derivada"],
        help="Topicos conhecidos pelo aluno.",
    )
    parser.add_argument(
        "--memorized-concepts",
        nargs="*",
        default=["Limites", "Derivada"],
        help="Conceitos que ja foram memorizados e nao devem voltar nos proximos cards.",
    )
    parser.add_argument(
        "--target-flashcards",
        type=int,
        default=5,
        help="Quantidade de flashcards a solicitar (1 a 8).",
    )
    return parser.parse_args()


def _extract_concepts(payload: dict) -> list[str]:
    cards = payload.get("flashcards", [])
    concepts: list[str] = []
    for item in cards:
        concept = item.get("concept")
        if isinstance(concept, str):
            concepts.append(concept)
    return concepts


def _normalize(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values}


def main() -> int:
    args = parse_args()
    payload = {
        "student_id": args.student_id,
        "student_background": args.student_background,
        "known_topics": args.known_topics,
        "memorized_concepts": args.memorized_concepts,
        "target_flashcards": args.target_flashcards,
    }

    with httpx.Client(timeout=40.0) as client:
        print("[1/3] Ingerindo a aula de Calculo I no backend...")
        ingest_result = ingest_lesson(client, args.backend_url)
        print(json.dumps(ingest_result, indent=2, ensure_ascii=False))

        print("\n[2/3] Rodando Case 3 (primeira interacao de flashcards)...")
        first_result = run_flashcards(client, args.backend_url, payload)
        print(json.dumps(first_result, indent=2, ensure_ascii=False))

        first_concepts = _extract_concepts(first_result)
        memorized_norm = _normalize(args.memorized_concepts)
        repeated = [c for c in first_concepts if c.strip().lower() in memorized_norm]
        if repeated:
            print("\n[ERRO] A resposta retornou conceitos ja memorizados:", repeated)
            return 1

        print("\n[3/3] Validando adaptacao na proxima interacao...")
        # Simula que todos os cards da primeira rodada foram memorizados.
        second_payload = dict(payload)
        second_payload["memorized_concepts"] = list(args.memorized_concepts) + first_concepts
        second_result = run_flashcards(client, args.backend_url, second_payload)
        print(json.dumps(second_result, indent=2, ensure_ascii=False))

        second_concepts = _extract_concepts(second_result)
        first_norm = _normalize(first_concepts)
        second_repeated = [c for c in second_concepts if c.strip().lower() in first_norm]
        if second_repeated:
            print("\n[ERRO] A segunda interacao repetiu conceitos da primeira rodada:", second_repeated)
            return 1

        print("\n[OK] Case 3 validado: flashcards em formato pergunta/resposta e sem repeticao de conceitos memorizados.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
