import sys
import os
import re

os.environ["WEBVIEW2_DEFAULT_BACKGROUND_COLOR"] = "0"

# Força UTF-8 no Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

from config import (
    OPENROUTER_API_KEY, MAX_TOKENS, TEMPERATURE, DB_FILE, CONFIGS_DIR,
    WHISPER_MODEL_SIZE, POOL_FAST, POOL_SMART, POOL_CODE, POOL_FALLBACK,
    USE_WAKEWORD, WAKEWORD_NAME, TOOLS_ENABLED, ENABLE_GUI,
)
from openrouter_client import OmniRouter
from memory import TroyMemory
from prompt_builder import build_system_prompt
from categorizer import Categorizer
from voice_input import VoiceInput
from voice_output import VoiceOutput
from tool_executor import process_response
from vad import SileroVAD
from gui import AtlasGUI


def process_voice_command(user_input, voice_in, voice_out, memory, router):
    """
    Processa comandos executados por voz ou texto.
    Retorna True se for um comando (interrompe envio à IA), False se for conversa.
    """
    text = user_input.strip().lower()

    if re.search(r'\b(sair|encerrar|desligar|tchau|fechar atlas|desliga atlas|modo off)\b', text):
        msg = "Até logo! Desligando os sistemas."
        print(f"Atlas: {msg}")
        if voice_out.available:
            voice_out.speak(msg)
        sys.exit(0)

    if text == "/projetos" or re.search(r'\b(projetos|listar projetos|quais são os projetos|meus projetos|projetos salvos|ver projetos)\b', text):
        projects = memory.get_all_projects()
        if projects:
            p_list = ", ".join(projects)
            msg = f"Você tem {len(projects)} projetos salvos: {p_list}."
            print(f"Atlas: {msg}")
            for p in projects:
                cp = memory.get_checkpoint(p)
                summary = cp["summary"][:60] if cp and cp["summary"] else "sem resumo"
                print(f"  • {p}: {summary}")
        else:
            msg = "Nenhum projeto salvo no banco ainda."
            print(f"Atlas: {msg}")
        print()
        if voice_out.available:
            voice_out.speak(msg)
        return True

    if text == "/stats" or re.search(r'\b(stats|estatísticas|ver stats|estatísticas do router|status do router)\b', text):
        stats_text = router.get_stats()
        print(f"Atlas: Estatísticas do OmniRouter:\n{stats_text}\n")
        if voice_out.available:
            voice_out.speak("Estatísticas do OmniRouter exibidas na tela.")
        return True

    if text == "/wakeword" or re.search(r'\b(usar f8|modo f8|desativar wakeword|ativar wakeword|alternar escuta)\b', text):
        if voice_in.available:
            voice_in.use_wakeword = not voice_in.use_wakeword
            if voice_in.use_wakeword:
                msg = "Modo escuta ativado. Pode me chamar dizendo Atlas."
            else:
                msg = "Modo alterado para hotkey F8."
            print(f"Atlas: {msg}\n")
            if voice_out.available:
                voice_out.speak(msg)
        return True

    if text == "/voz" or text == "alternar voz":
        if voice_in.available:
            msg = "Modo de voz alternado."
            print(f"Atlas: {msg}\n")
            if voice_out.available:
                voice_out.speak(msg)
        return True

    return False


def main():
    # Valida API key
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sk-or-COLE_SUA_KEY_AQUI":
        print("❌ API key não configurada!")
        print("   Edite o arquivo .env: OPENROUTER_API_KEY=sk-or-sua_key")
        return

    # Inicializa Silero VAD (detecção natural de silêncio para entrada de voz)
    vad = SileroVAD()

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

    # Inicializa Interface Gráfica (Buraco Negro 3D) se ativada
    gui = None
    if ENABLE_GUI:
        try:
            gui = AtlasGUI()
            gui.create_window()
            print("🌌 [GUI] Interface do Buraco Negro 3D iniciada (Always-on-top, canto superior direito).")
        except Exception as e:
            print(f"⚠️ [GUI] Não foi possível iniciar a interface gráfica: {e}")
            gui = None

    # Voz com VAD integrado e resposta de ativação
    voice_out = VoiceOutput(voice="pt-BR-FranciscaNeural", gui=gui)
    voice_in = VoiceInput(
        model_size=WHISPER_MODEL_SIZE,
        hotkey="f8",
        use_wakeword=USE_WAKEWORD,
        wakeword_name=WAKEWORD_NAME,
        vad=vad,
        voice_out=voice_out,
        gui=gui,
    )

    # Modo de input
    voice_mode = voice_in.available
    if voice_mode:
        if voice_in.use_wakeword:
            input_mode = f"WAKE WORD ({WAKEWORD_NAME.upper()})"
        else:
            input_mode = "VOZ (F8)"
    else:
        input_mode = "TEXTO"

    vad_status = "✅ Silero VAD (corta ao parar de falar)" if vad.available else "⚠️ Timer"
    tools_status = "✅ ATIVAS (11 ferramentas)" if TOOLS_ENABLED else "❌ DESATIVADAS"
    gui_status = "✅ ATIVA (Buraco Negro 3D no topo direito)" if gui else "❌ DESATIVADA"

    print()
    print("=" * 52)
    print("🤖 Atlas v5 — Assistente Pessoal (com Singularidade 3D)")
    print("=" * 52)
    print(f"  Modo entrada : {input_mode}")
    print(f"  Detecção voz : {vad_status}")
    print(f"  Fala         : Natural contínua (Edge-TTS)")
    print(f"  Router       : OmniRouter (FAST / SMART / CODE)")
    print(f"  Ferramentas  : {tools_status}")
    print(f"  Interface    : {gui_status}")
    print()
    print("  Comandos de Voz & Texto:")
    print("    • 'Desligar' / 'Sair'          → Encerra")
    print("    • 'Listar projetos'             → Projetos salvos")
    print("    • 'Ver estatísticas' / '/stats' → Stats do router")
    print("    • 'Usar F8' / '/wakeword'       → Alterna escuta")
    print("=" * 52)
    print()

    def run_atlas_loop():
        """Loop de conversação contínuo que roda em paralelo à interface gráfica."""
        while True:
            if gui:
                gui.set_state("idle")

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

            # --- PROCESSA COMANDOS ---
            if process_voice_command(user_input, voice_in, voice_out, memory, router):
                continue

            # --- TRAVA VOZ E SETA MODO PENSANDO ---
            if voice_mode and voice_in.available:
                voice_in.lock()

            if gui:
                gui.set_state("thinking")

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
                tools_enabled=TOOLS_ENABLED,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]

            # --- OMNIROUTER: classifica e gera resposta ---
            category = router.classify(user_input)
            print(f"\n   [{category.upper()}] ", end="", flush=True)

            response = router.chat(messages, max_tokens=MAX_TOKENS, temperature=TEMPERATURE)

            # --- PROCESSA FERRAMENTAS ---
            if TOOLS_ENABLED:
                is_tool, tool_result = process_response(response)
                if is_tool:
                    print(f"\n   🔧 [FERRAMENTA EXECUTADA]")
                    print(f"Atlas: {tool_result}\n")

                    memory.save_conversation(user_input, tool_result, project=detected_project)
                    conv_id = memory.get_last_conversation_id()
                    categorizer.categorize_in_background(conv_id, user_input, tool_result)

                    # Fala SOMENTE o resultado humano da ferramenta (NUNCA código JSON!)
                    if voice_mode and voice_out.available:
                        voice_out.speak(tool_result)

                    if voice_mode and voice_in.available:
                        voice_in.unlock()

                    if gui:
                        gui.set_state("idle")
                    continue

            # --- CONVERSA NORMAL ---
            print(f"\nAtlas: {response}\n")

            # Salva conversa
            memory.save_conversation(user_input, response, project=detected_project)
            conv_id = memory.get_last_conversation_id()
            categorizer.categorize_in_background(conv_id, user_input, response)

            # Fala de forma natural e contínua
            if voice_mode and voice_out.available:
                voice_out.speak(response)

            # Destrava voz e volta para idle
            if voice_mode and voice_in.available:
                voice_in.unlock()

            if gui:
                gui.set_state("idle")

    # Inicia com ou sem janela gráfica
    if gui:
        gui.start(run_atlas_loop)
    else:
        run_atlas_loop()


if __name__ == "__main__":
    main()
