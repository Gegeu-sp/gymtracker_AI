from dotenv import load_dotenv
from app.services.llm_service import parse_workout_from_text, generate_workout
import os

load_dotenv()

print("🧪 Teste 1: Extrair treino de texto OCR")
texto_exemplo = """
Supino reto 4x10 60kg
Agachamento 5x5 100kg
Rosca direta 3x12 15kg
"""
resultado = parse_workout_from_text(texto_exemplo)
print(resultado)

print("\n🧪 Teste 2: Gerar treino do zero")
treino = generate_workout(
    goal="hipertrofia",
    level="intermediário",
    days_per_week=4
)
print(treino)