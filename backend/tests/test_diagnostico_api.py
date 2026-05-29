from __future__ import annotations

import json
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import get_db as route_get_db
from app.main import app
from app.services import diagnostico_service


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "diagnostico_test.sqlite3"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    # diagnostico_service does not write to any table — no table creation needed.
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[route_get_db] = override_get_db

    monkeypatch.setattr(diagnostico_service, "garantir_base_vetorial", lambda _db: None)
    monkeypatch.setattr(
        diagnostico_service,
        "recuperar_contexto_semantico",
        lambda _payload, _db: ["Limites, Derivada e Regra da Cadeia."],
    )
    monkeypatch.setattr(
        diagnostico_service,
        "extrair_topicos",
        lambda _text: ["Limites", "Derivada", "Regra da Cadeia"],
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_diagnostico_classifica_objetivos_por_resposta(client: TestClient, monkeypatch) -> None:
    llm_payload = {
        "summary": "Aluno demonstrou dominio em Limites mas dificuldade em Regra da Cadeia.",
        "objectives": [
            {
                "objective": "Limites",
                "status": "Dominado",
                "justification": "Resposta correta e completa.",
            },
            {
                "objective": "Derivada",
                "status": "Parcial",
                "justification": "Conceito entendido mas com imprecisao na definicao formal.",
            },
            {
                "objective": "Regra da Cadeia",
                "status": "Nao dominado",
                "justification": "Nenhuma resposta correta sobre o tema.",
            },
        ],
        "review_actions": [
            "Revisar Regra da Cadeia com exercicios guiados.",
            "Consolidar Derivada com exercicios de aplicacao.",
        ],
    }
    # gerar_texto_llm for diagnostico is called WITHOUT response_mime_type — 3-param lambda is correct here.
    monkeypatch.setattr(
        diagnostico_service,
        "gerar_texto_llm",
        lambda prompt, fallback_text, system_prompt: (json.dumps(llm_payload), "gemini"),
    )

    payload = {
        "student_id": "aluno_diagnostico_001",
        "student_background": "Estudei limites e derivadas.",
        "known_topics": ["Limites"],
        "answered_questions": [
            "Limite e o valor que uma funcao se aproxima.",
            "Derivada e a taxa de variacao instantanea.",
            "Nao sei como aplicar a regra da cadeia.",
        ],
    }
    response = client.post("/api/v1/diagnostico", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["llm_source"] == "gemini"
    assert isinstance(body["summary"], str) and body["summary"]

    objectives = body["objectives"]
    assert len(objectives) == 3
    statuses = {obj["objective"]: obj["status"] for obj in objectives}
    assert statuses["Limites"] == "Dominado"
    assert statuses["Regra da Cadeia"] == "Nao dominado"

    assert len(body["review_actions"]) == 2


def test_diagnostico_uses_fallback_when_llm_returns_invalid_json(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostico_service,
        "gerar_texto_llm",
        lambda prompt, fallback_text, system_prompt: ("texto invalido sem json", "gemini"),
    )

    payload = {
        "student_id": "aluno_diagnostico_002",
        "student_background": "Tenho base em algebra.",
        "known_topics": ["Limites"],
        "answered_questions": ["Limite e aproximacao de um valor."],
    }
    response = client.post("/api/v1/diagnostico", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["llm_source"] == "fallback"
    assert isinstance(body["summary"], str) and body["summary"]
    assert isinstance(body["objectives"], list) and len(body["objectives"]) > 0
    assert isinstance(body["review_actions"], list)
