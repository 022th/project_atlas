import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

from config import *
from openrouter_client import OmniRouter
from prompt_builder import build_system_prompt

router = OmniRouter(OPENROUTER_API_KEY, POOL_FAST, POOL_SMART, POOL_CODE, POOL_FALLBACK)
system_prompt = build_system_prompt(configs_dir=CONFIGS_DIR)

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "me conta resumidamente o que é inteligência artificial"},
]

print("Testando streaming...")
t0 = time.time()
first = True

for sentence in router.chat_stream(messages, max_tokens=200):
    if first:
        print(f"⚡ Primeira frase chegou em: {time.time()-t0:.2f}s")
        first = False
    print(f"  → [{time.time()-t0:.2f}s] '{sentence}'")

print(f"\nTotal: {time.time()-t0:.2f}s")
