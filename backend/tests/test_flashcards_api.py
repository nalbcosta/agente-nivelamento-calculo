from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import get_db as route_get_db
from app.db.models import StudentMemorizedConcept
from app.main import app
from app.services import flashcard_service


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "flashcards_test.sqlite3"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    StudentMemorizedConcept.__table__.create(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[route_get_db] = override_get_db

    # Keep the endpoint deterministic and independent of vector search in tests.
    monkeypatch.setattr(flashcard_service, "garantir_base_vetorial", lambda _db: None)
    monkeypatch.setattr(
        flashcard_service,
        "recuperar_contexto_semantico",
        lambda _payload, _db: ["Limites, Derivada e Regra da Cadeia"],
    )
    monkeypatch.setattr(
        flashcard_service,
        "extrair_topicos",
        lambda _text: ["Limites", "Derivada", "Regra da Cadeia"],
    )
    monkeypatch.setattr(
        flashcard_service,
        "_gerar_flashcards_llm",
        lambda _payload, _ctx, _selected: ({}, "fallback"),
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_flashcards_persist_memorized_concepts_between_calls(client: TestClient) -> None:

    first_payload = {
        "student_id": "aluno_persist_001",
        "student_background": "",
        "known_topics": [],
        "memorized_concepts": ["Limites"],
        "target_flashcards": 3,
    }
    first_response = client.post("/api/v1/flashcards", json=first_payload)
    assert first_response.status_code == 200

    second_payload = {
        "student_id": "aluno_persist_001",
        "student_background": "",
        "known_topics": [],
        # Apenas o novo conceito memorizado; sem necessidade de reenviar todos.
        "memorized_concepts": ["Derivada"],
        "target_flashcards": 3,
    }
    second_response = client.post("/api/v1/flashcards", json=second_payload)
    assert second_response.status_code == 200

    second_json = second_response.json()
    memorized = {value.lower() for value in second_json["memorized_concepts"]}
    assert "limites" in memorized
    assert "derivada" in memorized

    returned_concepts = {item["concept"].lower() for item in second_json["flashcards"]}
    assert "limites" not in returned_concepts
    assert "derivada" not in returned_concepts


def test_flashcards_use_persisted_state_without_new_payload(client: TestClient) -> None:

    create_state_payload = {
        "student_id": "aluno_persist_002",
        "student_background": "",
        "known_topics": [],
        "memorized_concepts": ["Limites"],
        "target_flashcards": 3,
    }
    first_response = client.post("/api/v1/flashcards", json=create_state_payload)
    assert first_response.status_code == 200

    second_payload = {
        "student_id": "aluno_persist_002",
        "student_background": "",
        "known_topics": [],
        "memorized_concepts": [],
        "target_flashcards": 3,
    }
    second_response = client.post("/api/v1/flashcards", json=second_payload)
    assert second_response.status_code == 200

    second_json = second_response.json()
    memorized = {value.lower() for value in second_json["memorized_concepts"]}
    assert "limites" in memorized

    returned_concepts = {item["concept"].lower() for item in second_json["flashcards"]}
    assert "limites" not in returned_concepts


def test_flashcards_use_llm_items_when_available(client: TestClient, monkeypatch) -> None:

    def fake_llm_cards(_payload, _ctx, selected):
        concept = selected[0]
        normalized = concept.strip().lower()
        return (
            {
                normalized: flashcard_service.FlashcardItem(
                    concept=concept,
                    front=f"Pergunta LLM sobre {concept}",
                    back=f"Resposta LLM sobre {concept}",
                )
            },
            "huggingface",
        )

    monkeypatch.setattr(flashcard_service, "_gerar_flashcards_llm", fake_llm_cards)

    payload = {
        "student_id": "aluno_llm_001",
        "student_background": "",
        "known_topics": [],
        "memorized_concepts": [],
        "target_flashcards": 1,
    }
    response = client.post("/api/v1/flashcards", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["llm_source"] == "huggingface"
    assert len(body["flashcards"]) == 1
    assert body["flashcards"][0]["front"].startswith("Pergunta LLM")
