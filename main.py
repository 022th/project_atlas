import sys
import os

# Força UTF-8 no Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

from config import (
    OPENROUTER_API_KEY, MAX_TOKENS, TEMPERATURE, DB_FILE, CONFIGS_DIR,
    WHISPER_MODEL_SIZE, POOL_FAST, POOL_SMART, POOL_CODE, POOL_FALLBACK,
    USE_WAKEWORD, WAKEWORD_NAME,
)
from openrouter_client import OmniRouter
from memory import TroyMemory
from prompt_builder import build_system_prompt
from categorizer import Categorizer
from voice_input import VoiceInput
from voice_output import VoiceOutput


def main():
    # Valida API key
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sk-or-COLE_SUA_KEY_AQUI":
        print("❌ API key não configurada!")
        print("   Edite o arquivo .env: OPENROUTER_API_KEY=sk-or-sua_key")
        return

    # Inicializa OmniRouter
    router = OmniRouter(
        api_key=OPENROUTER_API_KEY,
        pool_fast=POOL_FAST,
        pool_smart=POOL_SMART,
        pool_code=POOL_CODE,
        pool_fallback=POOL_FALLBACK,
    )
    memory = TroyMemory(DB_FILE)
    categorizer = Categorizer(memory, router)

    # Voz (opcional com suporte a Wake Word 'ATLAS')
    voice_in = VoiceInput(
        model_size=WHISPER_MODEL_SIZE,
        hotkey="f8",
        use_wakeword=USE_WAKEWORD,
        wakeword_name=WAKEWORD_NAME,
    )
    voice_out = VoiceOutput(voice="pt-BR-FranciscaNeural")

    # Modo de input
    voice_mode = voice_in.available
    if voice_mode:
        if voice_in.use_wakeword:
            input_mode = f"WAKE WORD ({WAKEWORD_NAME.upper()})"
        else:
            input_mode = "VOZ (F8)"
    else:
        input_mode = "TEXTO"

    print()
    print("=" * 50)
    print("🤖 Atlas v3 — Assistente Pessoal + OmniRouter")
    print("=" * 50)
    print(f"  Modo: {input_mode}")
    print(f"  Router: OmniRouter (FAST / SMART / CODE)")
    print(f"  Banco: {DB_FILE}")
    if voice_mode:
        if voice_in.use_wakeword:
            print(f"  Ativação: Diga 'ATLAS' ou 'EI ATLAS' (ou segure F8)")
        else:
            print(f"  Hotkey: Segure F8 para falar")
    print()
    print("  Comandos:")
    print("    'sair'      → encerra")
    print("    '/voz'      → alterna entre voz e texto")
    print("    '/wakeword' → alterna modo Wake Word / Hotkey F8")
    print("    '/projetos'  → lista projetos salvos")
    print("    '/stats'     → estatísticas do OmniRouter")
    print("=" * 50)
    print()

    while True:
        # --- INPUT ---
        if voice_mode and voice_in.available:
            user_input = voice_in.listen_input()
            if user_input:
                print(f"Você: {user_input}")
            else:
                continue
        else:
            try:
                user_input = input("Você: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nAtlas: Até logo! 👋")
                break

        if not user_input:
            continue

        # --- COMANDOS ---
        if user_input.lower() == "sair":
            print("Atlas: Até logo! 👋")
            break

        if user_input.lower() == "/voz":
            if voice_in.available:
                voice_mode = not voice_mode
                mode_str = "VOZ" if voice_mode else "TEXTO"
                print(f"Atlas: Modo alterado para {mode_str}\n")
            else:
                print("Atlas: Voz indisponível.\n")
            continue

        if user_input.lower() == "/wakeword":
            if voice_in.available:
                voice_in.use_wakeword = not voice_in.use_wakeword
                estado = "ATIVADO (Diga 'ATLAS')" if voice_in.use_wakeword else "DESATIVADO (usando hotkey F8)"
                print(f"Atlas: Modo Wake Word {estado}\n")
            else:
                print("Atlas: Wake Word indisponível.\n")
            continue

        if user_input.lower() == "/projetos":
            projects = memory.get_all_projects()
            if projects:
                print("Atlas: Projetos salvos:")
                for p in projects:
                    cp = memory.get_checkpoint(p)
                    summary = cp["summary"][:60] if cp and cp["summary"] else "sem resumo"
                    print(f"  • {p}: {summary}")
            else:
                print("Atlas: Nenhum projeto salvo ainda.")
            print()
            continue

        if user_input.lower() == "/stats":
            print(f"Atlas: Estatísticas do OmniRouter:\n{router.get_stats()}\n")
            continue

        # --- TRAVA VOZ ---
        if voice_mode and voice_in.available:
            voice_in.lock()

        # --- DETECÇÃO DE PROJETO ---
        detected_project = categorizer.detect_project_sync(user_input)
        checkpoint = None
        recent = []

        if detected_project:
            checkpoint = memory.get_checkpoint(detected_project)
            recent = memory.get_recent_conversations(limit=5, project=detected_project)
        else:
            recent = memory.get_recent_conversations(limit=5)

        # --- MONTA PROMPT ---
        system_prompt = build_system_prompt(
            configs_dir=CONFIGS_DIR,
            checkpoint=checkpoint,
            recent_conversations=recent,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        # --- OMNIROUTER: classifica e envia ---
        category = router.classify(user_input)
        print(f"\n   [{category.upper()}] ", end="", flush=True)
        response = router.chat(messages, max_tokens=MAX_TOKENS, temperature=TEMPERATURE)
        print(f"\nAtlas: {response}\n")

        # --- SALVA CONVERSA ---
        memory.save_conversation(user_input, response, project=detected_project)
        conv_id = memory.get_last_conversation_id()

        # --- CATEGORIZA EM BACKGROUND ---
        categorizer.categorize_in_background(conv_id, user_input, response)

        # --- VOZ ---
        if voice_mode and voice_out.available:
            voice_out.speak(response)

        # --- DESTRAVA VOZ ---
        if voice_mode and voice_in.available:
            voice_in.unlock()


if __name__ == "__main__":
    main()
