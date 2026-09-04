"""
Atlas v4 — Tool Executor
Detecta comandos de ferramenta na resposta da IA (JSON) e executa localmente.
"""
import json
import re
from tools import TOOL_CATALOG, TOOL_FUNCTIONS

# Apelidos/variações comuns que as IAs às vezes geram
TOOL_ALIASES = {
    "getdatetime": "get_datetime",
    "get_date_time": "get_datetime",
    "datetime": "get_datetime",
    "hora": "get_datetime",
    "data": "get_datetime",
    "horario": "get_datetime",
    "openapp": "open_app",
    "open": "open_app",
    "closeapp": "close_app",
    "close": "close_app",
    "typetext": "type_text",
    "type": "type_text",
    "presskey": "press_key",
    "press": "press_key",
    "searchweb": "search_web",
    "search": "search_web",
    "google": "search_web",
    "clipboardread": "clipboard_read",
    "clipboardwrite": "clipboard_write",
    "volumecontrol": "volume_control",
    "volume": "volume_control",
    "systeminfo": "system_info",
    "sysinfo": "system_info",
    "print": "screenshot",
    "tela": "screenshot",
}


def normalize_tool_name(tool_name):
    """Normaliza o nome da ferramenta considerando apelidos."""
    if not tool_name:
        return tool_name
    cleaned = tool_name.lower().strip()
    return TOOL_ALIASES.get(cleaned, cleaned)


def extract_tool_call(response_text):
    """
    Analisa a resposta da IA e extrai o comando de ferramenta se houver.
    Retorna (tool_name, args_dict) ou (None, None) se não for um comando.
    """
    if not response_text:
        return None, None

    text = response_text.strip()

    # 1. Tenta extrair JSON de bloco de markdown ```json ... ```
    json_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_block:
        try:
            data = json.loads(json_block.group(1))
            if "tool" in data:
                return normalize_tool_name(data["tool"]), data.get("args", {})
        except json.JSONDecodeError:
            pass

    # 2. Tenta extrair qualquer objeto JSON { ... "tool": ... } no texto
    # (cobre casos como 'json {"tool": ...}' ou '{ "tool": ... }' embutido)
    json_candidates = re.findall(r'\{[^{}]*?"tool"[^{}]*?\}', text, re.DOTALL)
    for cand in json_candidates:
        try:
            data = json.loads(cand)
            if "tool" in data:
                return normalize_tool_name(data["tool"]), data.get("args", {})
        except json.JSONDecodeError:
            pass

    # 3. Tenta encontrar JSON com chaves aninhadas (ex: args com dict)
    nested_match = re.search(r'\{.*?"tool"\s*:\s*.*\}', text, re.DOTALL)
    if nested_match:
        try:
            cand = nested_match.group(0)
            # Remove sufixos não-json se houver
            last_brace = cand.rfind("}")
            if last_brace != -1:
                cand = cand[:last_brace + 1]
            data = json.loads(cand)
            if "tool" in data:
                return normalize_tool_name(data["tool"]), data.get("args", {})
        except json.JSONDecodeError:
            pass

    # 4. Regex flexível para extração direta se o JSON estiver ligeiramente mal formatado
    flex_match = re.search(r'["\']?tool["\']?\s*:\s*["\']([a-zA-Z0-9_\-]+)["\']', text)
    if flex_match:
        tool_name = normalize_tool_name(flex_match.group(1))
        # Tenta pegar args
        args = {}
        args_match = re.search(r'["\']?args["\']?\s*:\s*(\{.*?\})', text, re.DOTALL)
        if args_match:
            try:
                args = json.loads(args_match.group(1))
            except json.JSONDecodeError:
                pass
        return tool_name, args

    return None, None


def execute_tool(tool_name, args, ask_confirm_fn=None):
    """
    Executa uma ferramenta pelo nome com os argumentos fornecidos.
    """
    tool_name = normalize_tool_name(tool_name)

    if tool_name not in TOOL_CATALOG:
        return f"❌ Ferramenta '{tool_name}' não existe."

    if tool_name not in TOOL_FUNCTIONS:
        return f"❌ Ferramenta '{tool_name}' não tem implementação."

    catalog_entry = TOOL_CATALOG[tool_name]

    # Confirmação para ferramentas perigosas
    if catalog_entry.get("requires_confirm", False):
        desc = catalog_entry["description"]
        args_str = ", ".join(f"{k}={v}" for k, v in args.items()) if args else ""
        confirm_msg = f"⚠️ Ferramenta: {tool_name}({args_str}) — {desc}"

        if ask_confirm_fn:
            if not ask_confirm_fn(confirm_msg):
                return "Ação cancelada pelo usuário."
        else:
            print(f"\n{confirm_msg}")
            try:
                resp = input("   Executar? (s/n): ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                return "Ação cancelada."
            if resp not in ("s", "sim", "y", "yes"):
                return "Ação cancelada pelo usuário."

    # Executa a ferramenta
    try:
        func = TOOL_FUNCTIONS[tool_name]
        result = func(args)
        return result
    except Exception as e:
        return f"❌ Erro ao executar {tool_name}: {e}"


def process_response(response_text, ask_confirm_fn=None):
    """
    Processa a resposta da IA:
    - Se contém um comando de ferramenta → executa e retorna (True, resultado)
    - Se é texto normal → retorna (False, response_text)
    """
    tool_name, args = extract_tool_call(response_text)

    if tool_name:
        result = execute_tool(tool_name, args, ask_confirm_fn)
        return True, result

    return False, response_text
