import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ============================================================
# OmniRouter — Pools de Modelos por Categoria
# ============================================================
# Cada pool é uma lista de modelos tentados em ordem.
# Se o 1º falhar (429/timeout), tenta o próximo automaticamente.
#
# FAST: conversa casual, saudações, respostas curtas
# SMART: raciocínio, explicações longas, análises
# CODE: programação, scripts, debug
# ============================================================

POOL_FAST = [
    "google/gemma-4-26b-a4b-it:free",
    "minimax/minimax-m2.7:free",
    "liquid/lfm-2.5-2.6b:free",
]

POOL_SMART = [
    "minimax/minimax-m3:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
]

POOL_CODE = [
    "poolside/laguna-s-2.1:free",
    "cohere/north-mini-code:free",
    "minimax/minimax-m3:free",
]

# Fallback universal — se TODOS os modelos do pool escolhido falharem
POOL_FALLBACK = [
    "openrouter/free",
    "minimax/minimax-m3:free",
]

MAX_TOKENS = 500
TEMPERATURE = 0.7

# Paths
DB_FILE = "memories/troy.db"
CONFIGS_DIR = "configs"

# Modelo de voz Whisper local:
# "small"  = rápido (~2s), ~500MB RAM, boa precisão.
# "medium" = mais preciso (~3-4s), ~1.5GB RAM, excelente para fala rápida/gírias.
WHISPER_MODEL_SIZE = "small"

# Configurações de Wake Word (Palavra de Ativação):
# USE_WAKEWORD = True (ativa escuta viva por voz chamando "ATLAS")
USE_WAKEWORD = True
WAKEWORD_NAME = "Atlas"

# Ferramentas do Sistema (v4):
# Permite que a Atlas controle o PC (abrir apps, screenshot, volume, etc.)
TOOLS_ENABLED = True

# Interface Visual Desktop (v5):
# Abre a orbe flutuante 3D (Buraco Negro) sempre visível no canto superior direito
ENABLE_GUI = True
