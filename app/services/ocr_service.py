import easyocr

# Inicializar OCR (uma vez só)
reader = easyocr.Reader(['pt', 'en'], gpu=False)

# Detecções com confiança <= esse valor são descartadas. Mais baixo que o threshold "óbvio"
# (0.5) de propósito: uma linha ligeiramente ruidosa ainda ajuda a etapa de estruturação
# (structure_reference_table, em llm_service.py) a recuperar o exercício; descartar cedo demais
# perde a linha inteira sem chance de correção.
_CONFIDENCE_THRESHOLD = 0.3

# Detecções cujo centro Y difere por menos que isso são consideradas da mesma "linha" visual
# da tabela/ficha, mesmo com pequena inclinação do texto na foto.
_ROW_BAND_PX = 15


def _box_center(bbox) -> tuple[float, float]:
    xs = [point[0] for point in bbox]
    ys = [point[1] for point in bbox]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _sort_reading_order(detections: list) -> list:
    """
    EasyOCR devolve as detecções em uma ordem interna qualquer (não necessariamente a ordem de
    leitura da imagem) — sem isso, uma tabela de treino vira uma lista de exercícios embaralhada.
    Reordena em ordem de leitura (cima->baixo, esquerda->direita): agrupa detecções por "linha"
    usando o centro Y de cada bounding box com uma banda de tolerância, e dentro de cada linha
    ordena por X crescente. Recebe/devolve a lista no formato do EasyOCR: [(bbox, text, conf), ...].
    """
    items = []
    for bbox, text, conf in detections:
        x, y = _box_center(bbox)
        items.append((y, x, bbox, text, conf))

    items.sort(key=lambda item: item[0])

    rows: list = []
    current_row: list = []
    last_y = None
    for item in items:
        y = item[0]
        if last_y is not None and abs(y - last_y) > _ROW_BAND_PX:
            rows.append(current_row)
            current_row = []
        current_row.append(item)
        last_y = y
    if current_row:
        rows.append(current_row)

    ordered = []
    for row in rows:
        row.sort(key=lambda item: item[1])
        ordered.extend(row)

    return [(item[2], item[3], item[4]) for item in ordered]


def extract_text_from_image(image_path: str) -> str:
    """Extrai texto da imagem usando EasyOCR, em ordem de leitura (linha/coluna)."""
    try:
        result = reader.readtext(image_path)
        ordered = _sort_reading_order(result)
        texts = [text for _, text, conf in ordered if conf > _CONFIDENCE_THRESHOLD]
        return "\n".join(texts)
    except Exception as e:
        print(f"Erro OCR: {e}")
        return ""
