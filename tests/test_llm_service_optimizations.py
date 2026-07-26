import json
import app.services.llm_service as llm_service

class FakeMessage:
    def __init__(self, content):
        self.content = content

class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)

class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]

def test_estimate_max_tokens_scales_with_days():
    assert llm_service._estimate_max_tokens(1) == 2100
    assert llm_service._estimate_max_tokens(3) == 3900
    assert llm_service._estimate_max_tokens(6) == 6600

def test_estimate_max_tokens_never_exceeds_ceiling():
    assert llm_service._estimate_max_tokens(20) == 8192

def test_structure_reference_table_uses_light_model_and_reduced_tokens(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeResponse(json.dumps({"rows": []}))

    monkeypatch.setattr(llm_service.client.chat.completions, "create", fake_create)
    llm_service.structure_reference_table.cache_clear()

    llm_service.structure_reference_table("texto de referência de teste único")

    assert captured["model"] == llm_service.LIGHT_MODEL
    assert captured["model"] != llm_service.MODEL
    assert captured["max_tokens"] == 2048

def test_structure_reference_table_is_cached_to_avoid_repeat_spend(monkeypatch):
    call_count = {"n": 0}

    def fake_create(**kwargs):
        call_count["n"] += 1
        return FakeResponse(json.dumps({"rows": [{"exercise": "Supino"}]}))

    monkeypatch.setattr(llm_service.client.chat.completions, "create", fake_create)
    llm_service.structure_reference_table.cache_clear()

    result1 = llm_service.structure_reference_table("mesmo texto de referência")
    result2 = llm_service.structure_reference_table("mesmo texto de referência")

    assert call_count["n"] == 1
    assert result1 == result2

def test_parse_workout_from_text_uses_main_model_with_reduced_tokens(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeResponse(json.dumps({"workouts": []}))

    monkeypatch.setattr(llm_service.client.chat.completions, "create", fake_create)

    llm_service.parse_workout_from_text("texto qualquer extraído da imagem")

    assert captured["model"] == llm_service.MODEL
    assert captured["max_tokens"] == 2048

def test_parse_reference_and_generate_uses_dynamic_max_tokens(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeResponse(json.dumps({"workouts": []}))

    monkeypatch.setattr(llm_service.client.chat.completions, "create", fake_create)

    llm_service.parse_reference_and_generate("referência de teste", {"goal": "hipertrofia", "days_per_week": 3})

    assert captured["model"] == llm_service.MODEL
    assert captured["max_tokens"] == llm_service._estimate_max_tokens(3)

def test_generate_workout_uses_dynamic_max_tokens(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeResponse(json.dumps({"workouts": []}))

    monkeypatch.setattr(llm_service.client.chat.completions, "create", fake_create)

    llm_service.generate_workout({"goal": "hipertrofia", "days_per_week": 2})

    assert captured["model"] == llm_service.MODEL
    assert captured["max_tokens"] == llm_service._estimate_max_tokens(2)
