from app.services.ocr_service import _sort_reading_order, extract_text_from_image
import app.services.ocr_service as ocr_service


def _box(x, y, w=100, h=20):
    """Bounding box no formato do EasyOCR: 4 pontos (top-left, top-right, bottom-right, bottom-left)."""
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def test_sort_reading_order_fixes_out_of_order_rows():
    """
    Regressão: EasyOCR devolve detecções numa ordem interna qualquer, não necessariamente a
    ordem de leitura da imagem — sem reordenar, uma ficha de treino sai com os exercícios
    embaralhados. Aqui a linha 2 (y=100) aparece ANTES da linha 1 (y=20) na lista de entrada.
    """
    detections = [
        (_box(10, 100), "Agachamento", 0.9),   # linha 2
        (_box(10, 20), "Supino", 0.9),         # linha 1
        (_box(200, 20), "Inclinado", 0.9),     # linha 1, coluna 2 (depois de "Supino")
    ]

    ordered = _sort_reading_order(detections)
    texts = [text for _, text, _ in ordered]

    assert texts == ["Supino", "Inclinado", "Agachamento"]


def test_sort_reading_order_groups_same_row_within_tolerance():
    """Pequenas variações de Y (inclinação da foto) não devem quebrar o agrupamento por linha."""
    detections = [
        (_box(200, 22), "Livre", 0.9),
        (_box(10, 18), "Agachamento", 0.9),
    ]

    ordered = _sort_reading_order(detections)
    texts = [text for _, text, _ in ordered]

    assert texts == ["Agachamento", "Livre"]


def test_extract_text_from_image_includes_lower_confidence_detections(monkeypatch):
    """
    Regressão: threshold de confiança antigo (> 0.5) descartava exercícios com leitura mais
    difícil silenciosamente. Uma detecção com confiança 0.4 agora deve ser incluída.
    """
    class FakeReader:
        def readtext(self, path):
            return [
                (_box(10, 20), "Supino Reto", 0.9),
                (_box(10, 60), "Remada Baixa", 0.4),
            ]

    monkeypatch.setattr(ocr_service, "reader", FakeReader())

    text = extract_text_from_image("fake.jpg")
    assert "Supino Reto" in text
    assert "Remada Baixa" in text


def test_extract_text_from_image_still_drops_very_low_confidence(monkeypatch):
    class FakeReader:
        def readtext(self, path):
            return [
                (_box(10, 20), "Supino Reto", 0.9),
                (_box(10, 60), "Ruído Ilegível", 0.1),
            ]

    monkeypatch.setattr(ocr_service, "reader", FakeReader())

    text = extract_text_from_image("fake.jpg")
    assert "Supino Reto" in text
    assert "Ruído Ilegível" not in text
