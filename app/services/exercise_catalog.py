import unicodedata
from typing import List, Optional, TypedDict

class CatalogEntry(TypedDict):
    canonical_name: str
    muscle_group: str
    aliases: List[str]

# Catálogo de exercícios comuns de musculação: nome canônico, grupo muscular e apelidos/variações
# conhecidas (usados para reconhecer o mesmo exercício mesmo quando a IA ou o OCR escrevem o nome
# de forma diferente, ex: "Supino Reto" vs "Supino Reto com Barra" vs "Bench Press").
EXERCISE_CATALOG: List[CatalogEntry] = [
    # Peito
    {"canonical_name": "Supino Reto", "muscle_group": "Peito", "aliases": ["supino reto", "supino plano", "bench press", "flat bench"]},
    {"canonical_name": "Supino Inclinado", "muscle_group": "Peito", "aliases": ["supino inclinado", "incline press", "incline bench"]},
    {"canonical_name": "Supino Declinado", "muscle_group": "Peito", "aliases": ["supino declinado", "decline press", "decline bench"]},
    {"canonical_name": "Crucifixo", "muscle_group": "Peito", "aliases": ["crucifixo", "peck deck", "voador", "chest fly", "fly"]},
    {"canonical_name": "Cross Over", "muscle_group": "Peito", "aliases": ["cross over", "crossover", "cabo cruzado"]},
    {"canonical_name": "Flexão de Braço", "muscle_group": "Peito", "aliases": ["flexao de braco", "flexao", "push-up", "push up", "pushup"]},

    # Costas
    {"canonical_name": "Puxada Frontal", "muscle_group": "Costas", "aliases": ["puxada frontal", "puxada", "lat pull down", "pulldown", "puxada alta"]},
    {"canonical_name": "Remada Curvada", "muscle_group": "Costas", "aliases": ["remada curvada", "bent over row"]},
    {"canonical_name": "Remada Baixa", "muscle_group": "Costas", "aliases": ["remada baixa", "remada no cabo", "seated row", "remada sentada"]},
    {"canonical_name": "Remada Unilateral", "muscle_group": "Costas", "aliases": ["remada unilateral", "remada serrote", "serrote", "dumbbell row"]},
    {"canonical_name": "Barra Fixa", "muscle_group": "Costas", "aliases": ["barra fixa", "pull-up", "pull up", "pullup", "chin-up"]},
    {"canonical_name": "Levantamento Terra", "muscle_group": "Costas", "aliases": ["levantamento terra", "terra", "deadlift"]},
    {"canonical_name": "Puxada Triângulo", "muscle_group": "Costas", "aliases": ["puxada triangulo", "puxada fechada", "close grip pulldown"]},

    # Ombros
    {"canonical_name": "Desenvolvimento", "muscle_group": "Ombros", "aliases": ["desenvolvimento", "shoulder press", "overhead press", "military press", "arnold press"]},
    {"canonical_name": "Elevação Lateral", "muscle_group": "Ombros", "aliases": ["elevacao lateral", "lateral raise"]},
    {"canonical_name": "Elevação Frontal", "muscle_group": "Ombros", "aliases": ["elevacao frontal", "front raise"]},
    {"canonical_name": "Remada Alta", "muscle_group": "Ombros", "aliases": ["remada alta", "upright row"]},
    {"canonical_name": "Face Pull", "muscle_group": "Ombros", "aliases": ["face pull", "puxada facial"]},
    {"canonical_name": "Encolhimento", "muscle_group": "Ombros", "aliases": ["encolhimento", "shrug"]},

    # Bíceps
    {"canonical_name": "Rosca Direta", "muscle_group": "Bíceps", "aliases": ["rosca direta", "barbell curl"]},
    {"canonical_name": "Rosca Alternada", "muscle_group": "Bíceps", "aliases": ["rosca alternada", "alternating curl"]},
    {"canonical_name": "Rosca Scott", "muscle_group": "Bíceps", "aliases": ["rosca scott", "preacher curl"]},
    {"canonical_name": "Rosca Martelo", "muscle_group": "Bíceps", "aliases": ["rosca martelo", "hammer curl"]},
    {"canonical_name": "Rosca Concentrada", "muscle_group": "Bíceps", "aliases": ["rosca concentrada", "concentration curl"]},
    {"canonical_name": "Rosca no Cabo", "muscle_group": "Bíceps", "aliases": ["rosca no cabo", "rosca cabo", "cable curl"]},

    # Tríceps
    {"canonical_name": "Tríceps Pulley", "muscle_group": "Tríceps", "aliases": ["triceps pulley", "triceps corda", "tricep pushdown", "pushdown"]},
    {"canonical_name": "Tríceps Testa", "muscle_group": "Tríceps", "aliases": ["triceps testa", "skull crusher", "french press"]},
    {"canonical_name": "Tríceps Francês", "muscle_group": "Tríceps", "aliases": ["triceps frances"]},
    {"canonical_name": "Mergulho", "muscle_group": "Tríceps", "aliases": ["mergulho", "dips", "paralelas"]},
    {"canonical_name": "Tríceps Coice", "muscle_group": "Tríceps", "aliases": ["triceps coice", "kickback"]},

    # Pernas
    {"canonical_name": "Agachamento Livre", "muscle_group": "Pernas", "aliases": ["agachamento livre", "agachamento", "squat", "back squat"]},
    {"canonical_name": "Leg Press", "muscle_group": "Pernas", "aliases": ["leg press", "leg press 45"]},
    {"canonical_name": "Hack Squat", "muscle_group": "Pernas", "aliases": ["hack squat", "hack"]},
    {"canonical_name": "Cadeira Extensora", "muscle_group": "Pernas", "aliases": ["cadeira extensora", "leg extension"]},
    {"canonical_name": "Cadeira Flexora", "muscle_group": "Pernas", "aliases": ["cadeira flexora", "mesa flexora", "leg curl"]},
    {"canonical_name": "Stiff", "muscle_group": "Pernas", "aliases": ["stiff", "romanian deadlift", "terra romeno"]},
    {"canonical_name": "Afundo", "muscle_group": "Pernas", "aliases": ["afundo", "passada", "lunge"]},
    {"canonical_name": "Elevação Pélvica", "muscle_group": "Pernas", "aliases": ["elevacao pelvica", "hip thrust", "gluteo"]},
    {"canonical_name": "Cadeira Adutora", "muscle_group": "Pernas", "aliases": ["cadeira adutora", "adutora"]},
    {"canonical_name": "Cadeira Abdutora", "muscle_group": "Pernas", "aliases": ["cadeira abdutora", "abdutora"]},

    # Panturrilha
    {"canonical_name": "Panturrilha em Pé", "muscle_group": "Panturrilha", "aliases": ["panturrilha em pe", "panturrilha", "calf raise"]},
    {"canonical_name": "Panturrilha Sentado", "muscle_group": "Panturrilha", "aliases": ["panturrilha sentado", "seated calf"]},

    # Core / Abdômen
    {"canonical_name": "Abdominal", "muscle_group": "Core", "aliases": ["abdominal", "crunch", "sit-up", "sit up"]},
    {"canonical_name": "Prancha", "muscle_group": "Core", "aliases": ["prancha", "plank"]},
    {"canonical_name": "Elevação de Pernas", "muscle_group": "Core", "aliases": ["elevacao de pernas", "leg raise"]},

    # Cardio / Mobilidade / Aquecimento e Volta à Calma
    {"canonical_name": "Esteira", "muscle_group": "Cardio", "aliases": ["esteira", "treadmill", "corrida"]},
    {"canonical_name": "Bicicleta", "muscle_group": "Cardio", "aliases": ["bicicleta", "bike"]},
    {"canonical_name": "Elíptico", "muscle_group": "Cardio", "aliases": ["eliptico", "elliptical"]},
    {"canonical_name": "Mobilidade Articular", "muscle_group": "Mobilidade", "aliases": ["mobilidade", "circunducao", "ativacao", "rotacao articular"]},
    {"canonical_name": "Alongamento", "muscle_group": "Mobilidade", "aliases": ["alongamento", "stretching", "respiracao diafragmatica"]},
]

def _normalize(text: str) -> str:
    text = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))

# Aliases ordenados do mais longo para o mais curto: garante que "supino inclinado" seja
# testado antes de "supino" isolado, evitando classificar tudo genericamente.
_SORTED_ALIASES = sorted(
    ((_normalize(alias), entry) for entry in EXERCISE_CATALOG for alias in entry["aliases"]),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

def resolve_catalog_entry(exercise_name: str) -> Optional[CatalogEntry]:
    """Encontra a entrada do catálogo cujo apelido/nome mais específico aparece no nome do exercício."""
    normalized = _normalize(exercise_name)
    if not normalized:
        return None
    for alias, entry in _SORTED_ALIASES:
        if alias in normalized:
            return entry
    return None

def get_muscle_group(exercise_name: str) -> str:
    """Grupo muscular do exercício via catálogo, ou 'Outros' se não reconhecido."""
    entry = resolve_catalog_entry(exercise_name)
    return entry["muscle_group"] if entry else "Outros"

def get_canonical_name(exercise_name: str) -> str:
    """
    Identidade canônica do exercício, usada para casar histórico de progressão entre variações
    de escrita do MESMO exercício (ex: "Supino Reto" vs "Supino Reto com Barra"). Propositalmente
    NÃO une exercícios diferentes (ex: "Supino Reto" e "Crucifixo") mesmo que do mesmo grupo
    muscular — cargas de exercícios diferentes não são comparáveis, então cada um deve manter
    seu próprio histórico de progressão.
    """
    entry = resolve_catalog_entry(exercise_name)
    if entry:
        return entry["canonical_name"]
    return _normalize(exercise_name)
