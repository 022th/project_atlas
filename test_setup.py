"""Teste rápido de importação e validação dos módulos do Troy."""
from config import OPENROUTER_API_KEY, MODELS, MAX_TOKENS, TEMPERATURE, MEMORY_FILE, TOPICS_FILE
from openrouter_client import OpenRouterClient
from memory import TroyMemory

print("✅ Todos os módulos importam corretamente")
print(f"   Modelos configurados: {len(MODELS)}")

has_key = bool(OPENROUTER_API_KEY) and OPENROUTER_API_KEY != "sk-or-COLE_SUA_KEY_AQUI"
print(f"   API key configurada: {has_key}")

if not has_key:
    print("\n⚠️  API key ainda não configurada!")
    print("   Edite o arquivo troy/.env e cole sua key do OpenRouter")

# Testa memory
memory = TroyMemory(MEMORY_FILE, TOPICS_FILE)
entry_id = memory.save_conversation("teste de memória", "memória funcionando!")
found = memory.search_relevant("teste")
print(f"\n✅ Memory: gravou e buscou com sucesso ({len(found)} resultado(s))")

# Testa tag
memory.tag_last(entry_id, project="teste-sistema", tags=["validacao"])
found_tagged = memory.search_relevant("teste-sistema")
print(f"✅ Tag: marcação retroativa funcionou ({len(found_tagged)} resultado(s))")

print("\n🎉 Tudo pronto! Rode 'python main.py' para iniciar o Troy.")
