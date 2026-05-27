from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import get_db as route_get_db
from app.db.models import StudentReadiness
from app.main import app
from app.services import nivelamento_service


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "nivelamento_test.sqlite3"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    StudentReadiness.__table__.create(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[route_get_db] = override_get_db

    monkeypatch.setattr(nivelamento_service, "garantir_base_vetorial", lambda _db: None)
    monkeypatch.setattr(
        nivelamento_service,
        "recuperar_contexto_semantico",
        lambda _payload, _db: ["Funcoes, Regras de Potencia e Algebra, Trigonometria, Limites e Derivada."],
    )
    monkeypatch.setattr(
        nivelamento_service,
        "gerar_texto_nivelamento_llm",
        lambda prompt, fallback_text: ("Suporte curto para nivelamento.", "huggingface"),
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_nivelamento_uses_llm_extracted_prerequisites(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        nivelamento_service,
        "extrair_prerequisitos_topicos_llm",
        lambda _ctx: (
            ["Funcoes", "Trigonometria"],
            ["Limites", "Derivada"],
        ),
    )

    payload = {
        "student_id": "aluno_nivelamento_001",
        "student_background": "Conheco trigonometria e funcoes.",
        "known_topics": ["Funcoes", "Trigonometria"],
    }
    response = client.post("/api/v1/nivelamento", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["extracted_prerequisites"] == ["Funcoes", "Trigonometria"]
    assert body["missing_prerequisites"] == []
    assert body["is_ready"] is True
    assert body["llm_source"] == "huggingface"


def test_nivelamento_falls_back_to_static_extraction_when_llm_empty(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        nivelamento_service,
        "extrair_prerequisitos_topicos_llm",
        lambda _ctx: ([], []),
    )

    payload = {
        "student_id": "aluno_nivelamento_002",
        "student_background": "Conheco apenas funcoes.",
        "known_topics": ["Funcoes"],
    }
    response = client.post("/api/v1/nivelamento", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert "Regras de Potencia e Algebra" in body["extracted_prerequisites"]
    assert "Trigonometria" in body["missing_prerequisites"]
    assert body["is_ready"] is False
    assert body["llm_source"] == "huggingface"
