from __future__ import annotations

import json
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import get_db as route_get_db
from app.db.models import Student
from app.main import app
from app.services import consolidacao_service


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "consolidacao_test.sqlite3"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    # Student table is required: avaliar_consolidacao calls _get_or_create_student on every request.
    Student.__table__.create(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[route_get_db] = override_get_db

    monkeypatch.setattr(consolidacao_service, "garantir_base_vetorial", lambda _db: None)
    monkeypatch.setattr(
        consolidacao_service,
        "recuperar_contexto_semantico",
        lambda _payload, _db: ["Limites, Derivada, Regra da Cadeia e Regra de L'Hopital."],
    )
    monkeypatch.setattr(
        consolidacao_service,
        "extrair_topicos",
        lambda _text: ["Limites", "Derivada", "Regra da Cadeia"],
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_consolidacao_returns_llm_json_payload(client: TestClient, monkeypatch) -> None:
    llm_payload = {
        "consolidation_questions": [
            "O que representa um limite?",
            "Como voce interpreta derivada como taxa de variacao?",
            "Quando aplicar a regra da cadeia?",
        ],
        "dominated_objectives": ["Limites"],
        "partial_objectives": ["Derivada"],
        "not_understood_objectives": ["Regra da Cadeia"],
        "review_recommendation": "Revisar regra da cadeia com 3 exemplos guiados.",
    }
    # gerar_texto_llm is called with response_mime_type as a keyword arg — the lambda must accept it.
    monkeypatch.setattr(
        consolidacao_service,
        "gerar_texto_llm",
        lambda prompt, fallback_text, system_prompt, response_mime_type=None: (json.dumps(llm_payload), "gemini"),
    )

    payload = {
        "student_id": "aluno_consolidacao_001",
        "student_background": "Tenho base em limites.",
        "known_topics": ["Limites"],
        "answered_questions": ["Limite e aproximacao de valor."],
    }
    response = client.post("/api/v1/consolidacao", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["llm_source"] == "gemini"
    assert len(body["consolidation_questions"]) == 3
    assert body["dominated_objectives"] == ["Limites"]
    assert body["not_understood_objectives"] == ["Regra da Cadeia"]


def test_consolidacao_falls_back_when_llm_json_is_invalid(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        consolidacao_service,
        "gerar_texto_llm",
        lambda prompt, fallback_text, system_prompt, response_mime_type=None: ("resposta invalida", "gemini"),
    )

    payload = {
        "student_id": "aluno_consolidacao_002",
        "student_background": "Tenho dificuldade com regra da cadeia.",
        "known_topics": ["Limites"],
        "answered_questions": ["Derivada e inclinacao da tangente."],
    }
    response = client.post("/api/v1/consolidacao", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["llm_source"] == "fallback"
    assert len(body["consolidation_questions"]) >= 3
    assert isinstance(body["review_recommendation"], str)
    assert body["review_recommendation"].strip() != ""


def test_consolidacao_fallback_uses_answered_questions_for_partial_diagnosis(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        consolidacao_service,
        "gerar_texto_llm",
        lambda prompt, fallback_text, system_prompt, response_mime_type=None: ("resposta invalida", "gemini"),
    )

    payload = {
        "student_id": "aluno_consolidacao_003",
        "student_background": "",
        "known_topics": ["Limites"],
        "answered_questions": [
            "A regra da cadeia e usada para derivar composicao de funcoes.",
            "Eu ainda erro alguns passos, mas sei quando aplicar.",
        ],
    }
    response = client.post("/api/v1/consolidacao", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["llm_source"] == "fallback"
    assert "Limites" in body["dominated_objectives"]
    assert "Regra da Cadeia" in body["partial_objectives"]
