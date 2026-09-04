import sys
sys.stdout.reconfigure(encoding='utf-8')

from config import *
from openrouter_client import OmniRouter
from prompt_builder import build_system_prompt
from tool_executor import process_response

router = OmniRouter(OPENROUTER_API_KEY, POOL_FAST, POOL_SMART, POOL_CODE, POOL_FALLBACK)

# Monta prompt COM ferramentas
system_prompt = build_system_prompt(configs_dir=CONFIGS_DIR, tools_enabled=True)

# Teste 1: Pergunta que deve gerar ferramenta
test_queries = [
    "que horas são?",
    "como tá o PC?",
    "Qual dia é hoje?",
    "me explica o que é Python",
]

for q in test_queries:
    print(f"\n{'='*50}")
    print(f"Você: {q}")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": q},
    ]

    response = router.chat(messages, max_tokens=200)
    is_tool, result = process_response(response)

    if is_tool:
        print(f"🔧 [FERRAMENTA] → {result}")
    else:
        print(f"💬 [CONVERSA] → {result[:150]}...")
