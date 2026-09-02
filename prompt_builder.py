import os


def build_system_prompt(configs_dir, checkpoint=None, recent_conversations=None):
    """
    Monta o system prompt completo lendo os arquivos de config e injetando
    checkpoint do projeto ativo + histórico recente.
    """
    # Lê regras e personalidade dos arquivos editáveis
    regras = _read_config(os.path.join(configs_dir, "regras.txt"))
    personalidade = _read_config(os.path.join(configs_dir, "personalidade.txt"))

    # Bloco base
    prompt = f"Você é Atlas, um assistente IA pessoal inteligente e direto.\n\n[REGRAS]\n{regras}\n\n[PERSONALIDADE]\n{personalidade}"

    # Checkpoint do projeto ativo (se detectado)
    if checkpoint:
        prompt += f"""

--- CONTEXTO DO PROJETO ATIVO: {checkpoint['project'].upper()} ---
Resumo: {checkpoint['summary']}
Onde paramos: {checkpoint['where_we_stopped']}
"""

    # Histórico recente
    if recent_conversations:
        prompt += "\n--- CONVERSAS RECENTES ---\n"
        for conv in recent_conversations:
            project_tag = f" [{conv['project']}]" if conv.get("project") else ""
            prompt += f"User{project_tag}: {conv['user_input']}\n"
            # Só inclui resumo da resposta pra não explodir o contexto
            atlas_short = conv["troy_output"][:200]
            prompt += f"Atlas: {atlas_short}\n\n"
        prompt += "--- FIM DAS CONVERSAS RECENTES ---\n"

    return prompt


def _read_config(filepath):
    """Lê um arquivo de config. Retorna string vazia se não existir."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""
