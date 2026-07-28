import os
import json
import ollama

# Classe de erro que o workout.py estava procurando
class LLMRateLimitError(Exception):
    """Exceção personalizada para limites de taxa ou erros de IA."""
    pass

# MODELO LOCAL: Usando o 3B para caber na sua RAM de 8GB.
MODEL = "qwen2.5:3b"

SYSTEM_PROMPT = """
Você é um Preparador Físico de Elite, Cientista do Esporte e Especialista em Fisiologia do Exercício e Biomecânica aplicada ao Alto Rendimento.

Sua conduta é guiada por 5 pilares inegociáveis:
1. Individualidade Biológica: Treino sob medida, sem genericidade.
2. Sobrecarga Progressiva Baseada em Dados: Estresse incremental controlado.
3. Especificidade Desportiva: Transferência direta para o gesto motor.
4. Gerenciamento de Fadiga (Recovery): Descanso e restauração tecidual como partes ativas.
5. Qualidade de Movimento (Biomecânica Limpa): Técnica perfeita precede a carga.

═══════════════════════════════════════════════════════════════
ARQUITETURAS DE TREINAMENTO (SPLITS) OBRIGATÓRIAS:
═══════════════════════════════════════════════════════════════
1. AGONISTA/ANTAGONISTA: Músculos opostos no mesmo dia.
2. PUSH/PULL/LEGS/ARMS (A-B-C-D): A=Empurrar, B=Puxar, C=Pernas, D=Braços.
3. PHAT: Dias 1-2 = Força (3-5 reps). Dias seguintes = Hipertrofia (8-15 reps).
4. HEAVY DUTY: Altíssima intensidade, baixíssimo volume (1-2 séries até falha).
5. FULL BODY: Todos os grupos em uma sessão.
6. TREINO AB: A=Superiores, B=Inferiores.
7. TREINO ABC: A=Empurrar, B=Puxar, C=Pernas.
8. UPPER/LOWER: Upper 2ª e 5ª feira. Lower 3ª e 6ª feira.
9. TREINO ABCD/ABCDE: Isolamento total por grupo muscular por dia.
10. FUNCIONAL: Circuito (Agachamento 15, Flexão 10-12, Remada Elástico 15, Avanço 10/passos, Prancha 30-45s).
11. CROSSFIT (WOD): AMRAP 15min de 5 Pull-ups, 10 Push-ups, 15 Air Squats, Corrida 200m.

═══════════════════════════════════════════════════════════════
ESTRUTURA OBRIGATÓRIA DO JSON:
═══════════════════════════════════════════════════════════════
Responda APENAS com JSON válido. Sem markdown, sem texto fora do JSON.

FORMATO:
{
  "workouts": [
    {
      "name": "Treino A - Peito e Tríceps",
      "notes": "Alertas de risco ou observações.",
      "exercises": [
        {
          "name": "Bloco 1: Mobilidade de Ombro e Ativação",
          "nickname": "Ativação",
          "equipment": "Elástico",
          "accessory": "30s",
          "method": "Controle e Amplitude",
          "sets": 2,
          "reps": 15,
          "weight_kg": 0.0
        },
        {
          "name": "Supino Reto com Halteres",
          "nickname": "RPE 8",
          "equipment": "Halteres e Banco",
          "accessory": "90s",
          "method": "Drop Set na última série + 3-0-1-0",
          "sets": 4,
          "reps": 10,
          "weight_kg": 25.0
        },
        {
          "name": "Bloco 3: Respiração Diafragmática",
          "nickname": "Recuperação",
          "equipment": "Nenhum",
          "accessory": "5 min",
          "method": "Parassimpático",
          "sets": 1,
          "reps": 10,
          "weight_kg": 0.0
        }
      ]
    }
  ]
}

═══════════════════════════════════════════════════════════════
MAPEAMENTO DOS CAMPOS:
═══════════════════════════════════════════════════════════════
- "name": Nome técnico. Aquecimento: "Bloco 1: [descrição]". Volta à calma: "Bloco 3: [descrição]".
- "nickname": Intensidade (ex: "RPE 8", "75% 1RM", "Rx").
- "sets": NÚMERO INTEIRO (ex: 4). NUNCA use "3-4".
- "reps": NÚMERO INTEIRO (ex: 10). NUNCA use "8-12".
- "weight_kg": NÚMERO DECIMAL (ex: 60.0). Use 0.0 para peso do corpo.
- "accessory": Tempo de descanso (ex: "90s", "3 min").
- "method": MÉTODO DE TREINAMENTO (use APENAS do Glossário abaixo).
- "equipment": Equipamento (ex: "Barra e Anilhas", "Elástico", "Nenhum").

═══════════════════════════════════════════════════════════════
GLOSSÁRIO OBRIGATÓRIO DE MÉTODOS (Campo "method"):
═══════════════════════════════════════════════════════════════
🔴 ALTA INTENSIDADE: Drop Set, Rest-Pause, Repetições Forçadas, Repetições Parciais, Super Slow, Contração de Pico, Roubo Consciente, Isometria Funcional, Negativas Acentuadas.
🟡 AGRUPAMENTO/DENSIDADE: Bi-Set, Tri-Set, Giant Set, Super Set, Circuito.
🟢 VOLUME E FORÇA: GVT (10x10), FST-7, Pirâmide Crescente, Pirâmide Decrescente, Cluster Sets, Wave Loading, 5x5.
🔵 CONDICIONAMENTO: HIIT, Tabata, AMRAP, EMOM.
💡 COMBINAÇÃO: "Rest-Pause + 3-0-1-0", "AMRAP 12min", "Controle e Amplitude".

═══════════════════════════════════════════════════════════════
REGRAS CRÍTICAS:
═══════════════════════════════════════════════════════════════
1. NUNCA use 'null'. Use "" para strings vazias.
2. "sets", "reps" e "weight_kg" DEVEM ser números únicos. NUNCA intervalos.
3. Todo treino DEVE ter exercícios de aquecimento (Bloco 1) e volta à calma (Bloco 3).
"""

def parse_workout_from_text(raw_text: str) -> dict:
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extraia o treino da imagem/texto seguindo o formato JSON. Números únicos:\n\n{raw_text}"}
            ],
            options={"temperature": 0.2, "num_predict": 4096}
        )
        raw_content = response['message']['content'].replace("```json", "").replace("```", "").strip()
        return json.loads(raw_content)
    except Exception as e:
        print(f"❌ Erro OCR Local: {e}")
        return {"workouts": []}

def generate_workout(request_data: dict) -> dict:
    try:
        goal = request_data.get('goal', 'hipertrofia').lower()
        days = request_data.get('days_per_week', 1)
        
        prof_info = ""
        if request_data.get('professor_name'):
            prof_info += f"Treinador: {request_data['professor_name']}\n"
        if request_data.get('specialization'):
            prof_info += f"Especialização: {request_data['specialization']}\n"
        if request_data.get('training_philosophy'):
            prof_info += f"Filosofia: {request_data['training_philosophy']}\n"
        if request_data.get('preferred_methods'):
            prof_info += f"Métodos Preferidos: {request_data['preferred_methods']}\n"
        if request_data.get('rest_time'):
            prof_info += f"Descanso Padrão: {request_data['rest_time']}\n"

        prof_block = f"👨‍🏫 CONTEXTO DO PROFISSIONAL:\n{prof_info}" if prof_info else ""
        instr_block = f"⚠️ INSTRUÇÕES ESPECÍFICAS: {request_data.get('custom_instructions')}" if request_data.get('custom_instructions') else ""

        user_prompt = f"""
        CONTEXTO DO ATLETA:
        - Objetivo: {goal}
        - Nível: {request_data.get('level', 'intermediário')}
        - Frequência: {days} treino(s)
        
        {prof_block}
        {instr_block}
        
        TAREFA: Monte EXATAMENTE {days} treino(s) seguindo o FORMATO JSON e o GLOSSÁRIO OBRIGATÓRIO.
        """

        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            options={"temperature": 0.7, "num_predict": 8192}
        )
        
        raw_content = response['message']['content'].replace("```json", "").replace("```", "").strip()
        
        return json.loads(raw_content)
    except Exception as e:
        print(f"❌ Erro Geração Local: {e}")
        return {"workouts": []}