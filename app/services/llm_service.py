import os
import re
import json
from functools import lru_cache
from groq import Groq, RateLimitError as GroqRateLimitError
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
# Modelo menor/mais barato para tarefas de baixa complexidade (limpeza/estruturação de texto),
# que também consome de um orçamento de tokens diário SEPARADO do MODEL na Groq — usar aqui
# poupa tokens do MODEL principal, usado nas tarefas que realmente precisam de raciocínio maior.
LIGHT_MODEL = "llama-3.1-8b-instant"

def _estimate_max_tokens(days: int, base: int = 1200, per_day: int = 900, ceiling: int = 8192) -> int:
    """
    Calcula um teto de max_tokens proporcional ao número de treinos pedidos, em vez de sempre
    reservar o teto máximo (8192). A Groq reserva o max_tokens solicitado ao verificar o limite
    diário de tokens, então pedir só o necessário reduz a chance de bater o limite (TPD) sem
    necessidade, mesmo quando a geração real usa bem menos que isso.
    """
    return min(ceiling, base + per_day * max(1, days))

class LLMRateLimitError(Exception):
    """
    Levantado quando a Groq recusa a chamada por limite de tokens/requisições atingido
    (HTTP 429). Os routers capturam isso especificamente para devolver uma mensagem clara
    ao usuário em vez do 500 genérico "Falha ao gerar treinos".
    """
    pass

def _format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    minutes, secs = divmod(seconds, 60)
    if minutes and secs:
        return f"{minutes} min {secs}s"
    if minutes:
        return f"{minutes} min"
    return f"{secs}s"

def _build_rate_limit_message(e: Exception) -> str:
    retry_seconds = None
    match = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", str(e))
    if match:
        minutes = int(match.group(1)) if match.group(1) else 0
        retry_seconds = minutes * 60 + float(match.group(2))

    if retry_seconds:
        return (f"⏳ Limite diário de tokens da IA (Groq) atingido. "
                f"Tente novamente em ~{_format_duration(retry_seconds)}.")
    return "⏳ Limite de uso da IA (Groq) atingido no momento. Tente novamente em alguns minutos."

GOAL_RULES = {
    "hipertrofia": "HIPERTROFIA: Tensão mecânica + dano muscular. 3-5 séries, 6-12 reps, RPE 7-9, descanso 60-120s.",
    "forca": "FORÇA MÁXIMA: Adaptação neural. 4-6 séries, 1-5 reps, 80-95% 1RM, descanso 3-5 min.",
    "resistencia": "RESISTÊNCIA MUSCULAR: Sustentação de esforço. 2-3 séries, 15-25+ reps, RPE 6-8, descanso 30-45s.",
    "hiit": "HIIT: Estímulo metabólico máximo. Picos >90% FCmáx intercalados com recuperação incompleta.",
    "funcional": "FUNCIONAL: Padrões de movimento (empurrar, puxar, agachar, girar). Core, estabilidade, mobilidade.",
    "lesao": "REABILITAÇÃO/LESÃO: Segurança absoluta. Cargas submáximas, isometria, excêntrico lento, ADM controlada. Sem impacto.",
    "emagrecimento": "EMAGRECIMENTO: Preservar massa magra com alto gasto calórico. Circuitos, compostos multiarticulares, alta densidade.",
    "crossfit": "CROSSFIT/WOD: Alta intensidade, ginástica, levantamento olímpico, metabólico. Eficiência sob fadiga."
}

SYSTEM_PROMPT = """Você é um Preparador Físico de Elite, Cientista do Esporte e Especialista em Fisiologia do Exercício e Biomecânica aplicada ao Alto Rendimento.

Sua conduta é guiada por 5 pilares inegociáveis:
1. Individualidade Biológica: Treino sob medida, sem genericidade.
2. Sobrecarga Progressiva Baseada em Dados: Estresse incremental controlado.
3. Especificidade Desportiva: Transferência direta para o gesto motor.
4. Gerenciamento de Fadiga (Recovery): Descanso e restauração tecidual como partes ativas.
5. Qualidade de Movimento (Biomecânica Limpa): Técnica perfeita precede a carga.

────────────────────────────
MAPEAMENTO OBRIGATÓRIO DOS CAMPOS DO JSON (DECORE E SIGA):
────────────────────────────

• "name"        → NOME TÉCNICO DO EXERCÍCIO (ex: "Agachamento Livre", "Bloco 1: Mobilidade de Quadril").
• "nickname"    → INTENSIDADE / RPE / %1RM / %FCmáx. 
                  Exemplos: "RPE 8", "75% 1RM", "85% FCmáx", "Rx (peso corporal)", "Leve".
• "sets"        → NÚMERO INTEIRO DE SÉRIES (ex: 4). NUNCA use "3-4".
• "reps"        → NÚMERO INTEIRO DE REPETIÇÕES (ex: 10). NUNCA use "8-12". Use a média (10).
• "weight_kg"   → CARGA EM QUILOS (ex: 60.0). Use 0.0 para peso do corpo ou aquecimento.
• "accessory"   → TEMPO DE DESCANSO entre séries (ex: "90s", "3 min", "45s").
• "method"      → CADÊNCIA / TEMPO DE EXECUÇÃO / INTENÇÃO DO MOVIMENTO.
                  Exemplos: "3-0-X-0 (explosivo)", "4-2-1-0 (excêntrico lento)", "Isometria 3s", "AMRAP 20min", "Tabata 4min".
• "equipment"   → EQUIPAMENTO UTILIZADO (ex: "Barra e Anilhas", "Elástico", "Nenhum").

────────────────────────────
EXEMPLOS DE PREENCHIMENTO POR OBJETIVO (nickname | accessory | method):
────────────────────────────
HIPERTROFIA: "RPE 8" | "90s" | "3-0-1-0 (controle excêntrico)"
FORÇA MÁXIMA: "85% 1RM" | "3 min" | "X-0-1-0 (concêntrica explosiva)"
HIIT: "90% FCmáx" | "15s" | "40s esforço / 15s descanso (Tabata)"
LESÃO/REABILITAÇÃO: "RPE 4" | "60s" | "Isometria 5s + excêntrico 4s"
CROSSFIT/WOD: "Rx" | "0s (sem descanso)" | "AMRAP 12min"

────────────────────────────
ESTRUTURA OBRIGATÓRIA DA SESSÃO (3 BLOCOS):
────────────────────────────

Todo treino DEVE conter na lista "exercises":

BLOCO 1 - WARM-UP & RAMP (Aquecimento):
  - Mobilidade articular específica + ativação de core/estabilizadores.
  - Use weight_kg: 0.0, nickname: "Ativação", method: "Controle e amplitude".

BLOCO 2 - MAIN SESSION (Sessão Principal):
  - Exercícios complexos primeiro (exigem mais do SNC).
  - Preencha todos os campos conforme o mapeamento acima.

BLOCO 3 - COOL-DOWN (Volta à Calma):
  - Relaxamento, respiração diafragmática, alongamento leve.
  - Use weight_kg: 0.0, nickname: "Recuperação", method: "Parassimpático".

────────────────────────────
GESTÃO DE RISCO (Passo D) - Use o campo "notes" do treino:
────────────────────────────

Inclua alertas como:
- "⚠️ Se dor articular > RPE 3, substitua [exercício] por [variante segura]."
- "🚨 Sinais de overtraining (insônia, queda de rendimento): reduzir volume 30-50% (Deload)."
Seja direto: no máximo 2 frases curtas, sem repetir informação que já está nos campos dos exercícios.

────────────────────────────
REGRAS CRÍTICAS DE FORMATAÇÃO:
────────────────────────────

1. Responda APENAS com JSON válido. Sem markdown, sem texto fora do JSON.
2. NUNCA use 'null'. Use "" para strings vazias.
3. "sets", "reps" e "weight_kg" DEVEM ser números únicos (4, 10, 60.0). NUNCA intervalos ("10-12").
4. Se o usuário pedir N treinos, gere N objetos dentro de "workouts".
5. Seja direto em todo campo de texto livre (name, method, notes): frases curtas, sem repetição, sem explicações
   desnecessárias. Precisão técnica sim, enrolação não.

FORMATO OBRIGATÓRIO DE RESPOSTA:
{
  "workouts": [
    {
      "name": "Treino A - Força de Membros Inferiores",
      "notes": "⚠️ ALERTA: Se dor no joelho > RPE 3, troque Agachamento por Leg Press 45º. Monitorar sono para evitar overtraining.",
      "exercises": [
        {
          "name": "Bloco 1: RAMP - Mobilidade de Tornozelo e Ativação de Glúteo",
          "nickname": "Ativação",
          "equipment": "Elástico e Colchonete",
          "accessory": "45s",
          "method": "Controle e Amplitude",
          "sets": 2,
          "reps": 15,
          "weight_kg": 0.0
        },
        {
          "name": "Agachamento Livre",
          "nickname": "RPE 8",
          "equipment": "Barra e Anilhas",
          "accessory": "3 min",
          "method": "3-0-X-0 (Explosivo na subida)",
          "sets": 4,
          "reps": 5,
          "weight_kg": 100.0
        },
        {
          "name": "Bloco 3: Cool-down - Respiração Diafragmática",
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
}"""

def parse_workout_from_text(raw_text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extraia o treino da imagem/texto seguindo o mapeamento JSON (nickname=Intensidade/RPE, method=Cadência). Números únicos:\n\n{raw_text}"}
            ],
            temperature=0.2,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        return {"workouts": []}
    except GroqRateLimitError as e:
        raise LLMRateLimitError(_build_rate_limit_message(e)) from e
    except Exception as e:
        print(f"❌ Erro OCR: {e}")
        return {"workouts": []}

STRUCTURE_SYSTEM_PROMPT = """Você é um assistente de digitação especializado em fichas de treino de academia.

Você recebe um texto bruto extraído via OCR de uma tabela de outro aplicativo/planilha de treino, com colunas:
Exercício, Apelido (variação do exercício), Equipamento, Acessório (acessório físico), Método (esquema de séries/técnica).
O texto pode estar desorganizado, com colunas fora de ordem ou linhas quebradas, por causa do OCR.

TAREFA: Reconstrua a tabela original em uma lista JSON de linhas, uma por exercício, respeitando a ORDEM em que aparecem no texto.

REGRAS:
1. Cada linha deve ter exatamente estas chaves: "exercise", "nickname", "equipment", "accessory", "method".
2. Corrija erros ÓBVIOS de OCR usando o contexto de nomes comuns de exercícios de musculação
   (ex: "5UPIN0" → "Supino", "REM4DA" → "Remada", "0mbros" → "Ombros", letras/números trocados, caracteres soltos ou duplicados).
3. NÃO invente informação que não está no texto. Se uma célula estiver vazia, ilegível ou ausente, use "" (string vazia).
4. Ignore colunas irrelevantes (ex: checkbox de "Vídeo", números de página, cabeçalhos repetidos).
5. Responda APENAS com JSON válido, sem markdown, no formato:
{"rows": [{"exercise": "Supino", "nickname": "Inclinado", "equipment": "Halter", "accessory": "Banco Inclinado", "method": "Pirâmide truncada crescente 12-10-8"}]}
"""

@lru_cache(maxsize=32)
def structure_reference_table(raw_text: str) -> list:
    """
    Converte o texto bruto do OCR em linhas estruturadas (Exercício/Apelido/Equipamento/
    Acessório/Método), corrigindo erros óbvios de leitura, para exibição em tabela editável
    na tela de revisão antes da geração dos treinos.

    Usa LIGHT_MODEL (menor/mais barato) — é uma tarefa de limpeza/reorganização de texto, não
    exige o raciocínio do modelo principal — e é cacheada (@lru_cache): reenviar a mesma imagem/
    texto (ex: usuário tenta de novo após um erro) não gasta tokens de novo.
    """
    try:
        response = client.chat.completions.create(
            model=LIGHT_MODEL,
            messages=[
                {"role": "system", "content": STRUCTURE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Texto bruto extraído via OCR:\n\n{raw_text}"}
            ],
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content:
            data = json.loads(content)
            return data.get("rows", [])
        return []
    except GroqRateLimitError as e:
        raise LLMRateLimitError(_build_rate_limit_message(e)) from e
    except Exception as e:
        print(f"❌ Erro Estruturação de Referência: {e}")
        return []

def parse_reference_and_generate(raw_text: str, request_data: dict) -> dict:
    """
    Usa uma tabela de referência (extraída via OCR de outro app/planilha de treino) como
    base/estilo para remontar de 1 a N treinos, seguindo o perfil do professor e a
    metodologia de 3 blocos já obrigatória no app. A referência usa rótulos de coluna
    (Apelido, Acessório, Método) com significado DIFERENTE do JSON de saída deste app
    (nickname=intensidade/RPE, accessory=descanso, method=cadência) — o prompt abaixo
    instrui a tradução explícita entre os dois vocabulários.
    """
    try:
        goal = request_data.get('goal', 'hipertrofia').lower()
        goal_rule = GOAL_RULES.get(goal, GOAL_RULES["hipertrofia"])
        days = request_data.get('days_per_week', 1)

        prof_info = ""
        if request_data.get('professor_name'):
            prof_info += f"Treinador: {request_data['professor_name']}\n"
        if request_data.get('specialization'):
            prof_info += f"Especialização: {request_data['specialization']}\n"
        if request_data.get('training_philosophy'):
            prof_info += f"Filosofia: {request_data['training_philosophy']}\n"
        if request_data.get('preferred_methods'):
            prof_info += f"Métodos: {request_data['preferred_methods']}\n"
        if request_data.get('rest_time'):
            prof_info += f"Descanso Padrão: {request_data['rest_time']}\n"

        prof_block = f"👨‍🏫 CONTEXTO DO PROFISSIONAL:\n{prof_info}" if prof_info else ""
        instr_block = f"🎯 INSTRUÇÕES ESPECÍFICAS DO PEDIDO (PRIORIDADE MÁXIMA): {request_data.get('custom_instructions')}" if request_data.get('custom_instructions') else ""

        volume_adjustment = (request_data.get('volume_adjustment') or 'manter').lower()
        if volume_adjustment == 'aumentar':
            volume_block = ("🔼 VOLUME: Aumente o volume total (séries x reps x carga) em relação à referência, de forma "
                             "progressiva e segura — ex: +1 série em exercícios-chave, ou leve incremento de reps/carga. "
                             "Não exagere: aumento moderado (10-20%), coerente com o nível informado.")
        elif volume_adjustment == 'diminuir':
            volume_block = ("🔽 VOLUME: Reduza o volume total (séries x reps) em relação à referência — ex: menos séries "
                             "ou reps por exercício — mantendo a qualidade do estímulo para o objetivo pedido.")
        else:
            volume_block = "➡️ VOLUME: Mantenha o volume total (séries x reps) equivalente ao observado na referência."

        reference_block = f"""
📋 TABELA DE REFERÊNCIA (treino que o aluno JÁ EXECUTOU/CONHECE — usada como base de volume/estilo/equipamento, pode ter ruído de OCR):
---
{raw_text}
---

🚨 REGRA MAIS IMPORTANTE DESTA TAREFA — NÃO É PARA COPIAR:
O objetivo NUNCA é devolver a mesma tabela reescrita. É criar um treino NOVO, uma VARIAÇÃO da referência, para o aluno
não fazer sempre os mesmos exercícios. Para CADA exercício principal do Bloco 2 (Main Session):
- SUBSTITUA por um exercício EQUIVALENTE — mesmo grupo muscular e padrão de movimento (empurrar/puxar/agachar/etc.),
  equipamento similar ou disponível — mas DIFERENTE do exercício original da referência.
  Exemplos de substituição válida: "Supino Reto com Barra" → "Supino Inclinado com Halteres" ou "Crucifixo na Máquina";
  "Puxada Frontal" → "Remada Curvada" ou "Puxada Triângulo"; "Agachamento Livre" → "Leg Press 45°" ou "Hack Squat".
- PROIBIDO usar o mesmo "Exercício" + "Apelido" da referência para o mesmo padrão de movimento no treino gerado —
  isso seria copiar, não variar. Se não souber uma alternativa segura para algum exercício, escolha qualquer exercício
  consagrado do mesmo grupo muscular, mesmo que não estivesse na tabela.
- O volume (número de exercícios por grupo muscular, séries, estrutura geral) deve seguir a REGRA DE VOLUME abaixo.

{volume_block}

🎯 SELEÇÃO DE GRUPOS MUSCULARES/FOCO:
As INSTRUÇÕES ESPECÍFICAS DO PEDIDO (se houver, ver acima) e o OBJETIVO "{goal}" DEFINEM quais grupos musculares entram.
- Se as instruções pedirem um foco específico (ex: "treino de peito", "só membros inferiores", "sem agachamento"),
  gere substitutos SOMENTE dentro desse foco no Bloco 2 (Main Session). NÃO inclua exercícios de outros grupos
  musculares só porque o grupo aparecia na referência — isso é um erro grave.
- Se as instruções NÃO especificarem um foco (pedido genérico), use como referência de grupos musculares os que
  aparecem na tabela, distribuindo as variações entre os {days} treino(s) pedidos.

⚠️ TRADUÇÃO OBRIGATÓRIA DE TERMINOLOGIA (a referência usa rótulos DIFERENTES do seu JSON de saída — NÃO copie literalmente):
- "Exercício" (nome-base, ex: "SUPINO") + "Apelido" da referência (VARIANTE do exercício, ex: "INCLINADO" — NÃO é intensidade/RPE)
  → combine os dois em "name" da saída (ex: "Supino Inclinado").
- "Equipamento" (ex: "HALTER") + "Acessório" da referência (acessório FÍSICO usado, ex: "BANCO INCLINADO", "PESO CORPORAL" — NÃO é tempo de descanso)
  → combine os dois em "equipment" da saída (ex: "Halter + Banco Inclinado").
- "Método" da referência mistura esquema de séries/técnica com contagem (ex: "PIRÂMIDE TRUNCADA CRESCENTE 12-10-8",
  "MÚLTIPLAS SÉRIES 3x12 REPS.", "ISOMETRIA 1x30 S", "SÉRIE SIMPLES 1x20 REPS."):
  → Extraia "sets" e "reps" como NÚMEROS INTEIROS ÚNICOS (nunca intervalos) a partir do esquema.
    Exemplos: "12-10-8" → sets=3, reps=10 (média); "3x12" → sets=3, reps=12; "1x30 S" (isometria) → sets=1, reps=30
    (segundos sob tensão, já que o app não tem campo de tempo separado).
  → Preserve a descrição do esquema dentro de "method" da saída (ex: "Pirâmide truncada crescente (12-10-8)"),
    podendo complementar com a cadência/intenção de movimento adequada ao objetivo.
- A referência NÃO tem colunas de intensidade/RPE nem de tempo de descanso.
  → Preencha "nickname" (INTENSIDADE/RPE/%1RM) e "accessory" (TEMPO DE DESCANSO) exatamente como faria ao gerar um
    treino do zero, seguindo o MAPEAMENTO OBRIGATÓRIO já descrito acima, com base no objetivo "{goal}".
- Ignore a coluna "Vídeo" (irrelevante) e qualquer ruído típico de OCR (cabeçalhos repetidos, números de página, caracteres quebrados).
"""

        anamnese_prompt = f"""
        CONTEXTO DO ATLETA:
        - Objetivo: {goal_rule}
        - Nível: {request_data.get('level', 'intermediário')}
        - Frequência: {days} treino(s)

        {prof_block}
        {instr_block}

        {reference_block}

        TAREFA: Crie EXATAMENTE {days} treino(s) NOVOS — uma VARIAÇÃO da referência, com exercícios SUBSTITUÍDOS
        conforme a REGRA MAIS IMPORTANTE acima. Não devolva os mesmos exercícios da tabela.
        - Inclua os 3 Blocos obrigatórios (Warm-up/RAMP, Main Session, Cool-down) em cada treino — a referência raramente
          traz aquecimento/volta à calma, então complemente com exercícios adequados ao foco pedido.
        - No Bloco 2 (Main Session), use exercícios SUBSTITUTOS (equivalentes, não literais) do estilo/equipamentos da
          referência, respeitando o foco de grupos musculares e a regra de volume; adapte intensidade ao nível informado.
        - Preencha nickname com INTENSIDADE/RPE e method com CADÊNCIA/ESQUEMA (conforme tradução acima).
        - "sets", "reps" e "weight_kg" DEVEM ser números únicos, nunca intervalos.
        - Use o campo 'notes' para Alertas de Risco (lesão, overtraining), como de costume.
        """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": anamnese_prompt}
            ],
            temperature=0.4,
            max_tokens=_estimate_max_tokens(days),
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        return {"workouts": []}
    except GroqRateLimitError as e:
        raise LLMRateLimitError(_build_rate_limit_message(e)) from e
    except Exception as e:
        print(f"❌ Erro Extração de Referência: {e}")
        return {"workouts": []}

def generate_workout(request_data: dict) -> dict:
    try:
        goal = request_data.get('goal', 'hipertrofia').lower()
        goal_rule = GOAL_RULES.get(goal, GOAL_RULES["hipertrofia"])
        days = request_data.get('days_per_week', 1)
        
        prof_info = ""
        if request_data.get('professor_name'):
            prof_info += f"Treinador: {request_data['professor_name']}\n"
        if request_data.get('specialization'):
            prof_info += f"Especialização: {request_data['specialization']}\n"
        if request_data.get('training_philosophy'):
            prof_info += f"Filosofia: {request_data['training_philosophy']}\n"
        if request_data.get('preferred_methods'):
            prof_info += f"Métodos: {request_data['preferred_methods']}\n"
        if request_data.get('rest_time'):
            prof_info += f"Descanso Padrão: {request_data['rest_time']}\n"

        prof_block = f"👨‍🏫 CONTEXTO DO PROFISSIONAL:\n{prof_info}" if prof_info else ""
        instr_block = f"⚠️ INSTRUÇÕES ESPECÍFICAS: {request_data.get('custom_instructions')}" if request_data.get('custom_instructions') else ""

        anamnese_prompt = f"""
        CONTEXTO DO ATLETA:
        - Objetivo: {goal_rule}
        - Nível: {request_data.get('level', 'intermediário')}
        - Frequência: {days} treino(s)
        
        {prof_block}
        {instr_block}
        
        TAREFA: Monte EXATAMENTE {days} treino(s). 
        - Inclua os 3 Blocos (Warm-up, Main Session, Cool-down).
        - Preencha nickname com INTENSIDADE/RPE e method com CADÊNCIA/TEMPO DE EXECUÇÃO.
        - Use o campo 'notes' para Alertas de Risco (lesão, overtraining).
        """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": anamnese_prompt}
            ],
            temperature=0.7,
            max_tokens=_estimate_max_tokens(days),
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        return {"workouts": []}
    except GroqRateLimitError as e:
        raise LLMRateLimitError(_build_rate_limit_message(e)) from e
    except Exception as e:
        print(f"❌ Erro Geração: {e}")
        return {"workouts": []}