import json

import httpx
import pytest
from groq import RateLimitError as GroqRateLimitError

import app.services.llm_service as llm_service


def _groq_rate_limit_error(message="rate_limit_exceeded. Please try again in 8m51.36s."):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return GroqRateLimitError(message, response=response, body=None)


def _raise_groq_rate_limit(**kwargs):
    raise _groq_rate_limit_error()


def _fake_ollama_response(payload: dict):
    return {"message": {"content": json.dumps(payload)}}


@pytest.fixture(autouse=True)
def _restore_ollama_flag():
    original = llm_service.OLLAMA_AVAILABLE
    yield
    llm_service.OLLAMA_AVAILABLE = original


def test_groq_rate_limit_falls_back_to_ollama_success(monkeypatch):
    monkeypatch.setattr(llm_service.client.chat.completions, "create", _raise_groq_rate_limit)
    llm_service.OLLAMA_AVAILABLE = True

    expected = {"workouts": [{"name": "Treino A", "notes": "", "exercises": []}]}
    monkeypatch.setattr(llm_service.ollama, "chat", lambda **kwargs: _fake_ollama_response(expected))

    result = llm_service.generate_workout({"goal": "hipertrofia", "days_per_week": 1})

    assert result == expected


def test_groq_rate_limit_and_ollama_unavailable_raises_combined_message(monkeypatch):
    monkeypatch.setattr(llm_service.client.chat.completions, "create", _raise_groq_rate_limit)
    llm_service.OLLAMA_AVAILABLE = False

    with pytest.raises(llm_service.LLMRateLimitError) as exc_info:
        llm_service.generate_workout({"goal": "hipertrofia", "days_per_week": 1})

    message = str(exc_info.value)
    assert "Limite diário de tokens da IA (Groq)" in message
    assert "Ollama" in message


def test_groq_rate_limit_and_ollama_error_raises_combined_message(monkeypatch):
    monkeypatch.setattr(llm_service.client.chat.completions, "create", _raise_groq_rate_limit)
    llm_service.OLLAMA_AVAILABLE = True

    def fake_chat(**kwargs):
        raise ConnectionError("Connection refused")

    monkeypatch.setattr(llm_service.ollama, "chat", fake_chat)

    with pytest.raises(llm_service.LLMRateLimitError) as exc_info:
        llm_service.parse_workout_from_text("texto de treino qualquer")

    message = str(exc_info.value)
    assert "Limite diário de tokens da IA (Groq)" in message
    assert "Ollama" in message


def test_structure_reference_table_prefers_ollama_over_groq(monkeypatch):
    llm_service.OLLAMA_AVAILABLE = True
    llm_service.structure_reference_table.cache_clear()

    expected_rows = [{"exercise": "Supino", "nickname": "", "equipment": "", "accessory": "", "method": ""}]
    monkeypatch.setattr(llm_service.ollama, "chat", lambda **kwargs: _fake_ollama_response({"rows": expected_rows}))

    groq_called = {"called": False}

    def fail_if_called(**kwargs):
        groq_called["called"] = True
        raise AssertionError("Groq não deveria ser chamada quando o Ollama responde com sucesso")

    monkeypatch.setattr(llm_service.client.chat.completions, "create", fail_if_called)

    result = llm_service.structure_reference_table("texto único de referência para teste de fallback do Ollama")

    assert result == expected_rows
    assert groq_called["called"] is False


def test_structure_reference_table_falls_back_to_groq_when_ollama_unavailable(monkeypatch):
    llm_service.OLLAMA_AVAILABLE = False
    llm_service.structure_reference_table.cache_clear()

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    expected_rows = [{"exercise": "Agachamento", "nickname": "", "equipment": "", "accessory": "", "method": ""}]

    def fake_create(**kwargs):
        assert kwargs["model"] == llm_service.LIGHT_MODEL
        return FakeResponse(json.dumps({"rows": expected_rows}))

    monkeypatch.setattr(llm_service.client.chat.completions, "create", fake_create)

    result = llm_service.structure_reference_table("outro texto único de referência sem ollama disponível")

    assert result == expected_rows


def test_structure_reference_table_handles_bare_list_from_ollama(monkeypatch):
    """
    Regressão: o Ollama (modelo local pequeno) às vezes devolve uma lista JSON solta em vez do
    objeto {"rows": [...]} pedido no prompt — sem normalização isso quebrava com
    AttributeError: 'list' object has no attribute 'get'.
    """
    llm_service.OLLAMA_AVAILABLE = True
    llm_service.structure_reference_table.cache_clear()

    bare_list = [{"exercise": "Supino", "nickname": "", "equipment": "", "accessory": "", "method": ""}]
    monkeypatch.setattr(llm_service.ollama, "chat", lambda **kwargs: _fake_ollama_response(bare_list))

    result = llm_service.structure_reference_table("texto único de referência com resposta em lista solta")

    assert result == bare_list


def test_generate_workout_fallback_handles_bare_list_from_ollama(monkeypatch):
    """Mesma regressão de formato solto, mas no caminho de fallback por 429 da Groq."""
    monkeypatch.setattr(llm_service.client.chat.completions, "create", _raise_groq_rate_limit)
    llm_service.OLLAMA_AVAILABLE = True

    bare_workouts = [{"name": "Treino A", "notes": "", "exercises": []}]
    monkeypatch.setattr(llm_service.ollama, "chat", lambda **kwargs: _fake_ollama_response(bare_workouts))

    result = llm_service.generate_workout({"goal": "hipertrofia", "days_per_week": 1})

    assert result == {"workouts": bare_workouts}
