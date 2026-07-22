import easyocr

# Inicializar OCR (uma vez só)
reader = easyocr.Reader(['pt', 'en'], gpu=False)

def extract_text_from_image(image_path: str) -> str:
    """Extrai texto da imagem usando EasyOCR."""
    try:
        result = reader.readtext(image_path)
        texts = [item[1] for item in result if item[2] > 0.5]
        return "\n".join(texts)
    except Exception as e:
        print(f"Erro OCR: {e}")
        return ""