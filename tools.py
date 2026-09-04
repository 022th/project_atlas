"""
Atlas v4 — Ferramentas do Sistema
Cada ferramenta é uma função Python pura que executa uma ação real no Windows
e retorna um texto descritivo do resultado.
"""
import os
import sys
import datetime
import subprocess
import webbrowser

# Dependências opcionais — falham silenciosamente
try:
    import pyautogui
    pyautogui.FAILSAFE = True  # mover mouse pro canto cancela tudo
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


# ============================================================
# FERRAMENTAS
# ============================================================

def screenshot(save_path=None):
    """Tira um screenshot da tela inteira. Retorna o caminho do arquivo salvo."""
    if not PYAUTOGUI_AVAILABLE:
        return "❌ pyautogui não instalado. Instale com: pip install pyautogui"

    if save_path is None:
        os.makedirs("screenshots", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"screenshots/screen_{timestamp}.png"

    img = pyautogui.screenshot()
    img.save(save_path)
    width, height = img.size
    return f"Screenshot salvo em '{save_path}' ({width}x{height}px)."


def open_app(name):
    """Abre um aplicativo pelo nome no Windows de forma robusta e nativa."""
    name_clean = name.strip().lower()

    # 1. Protocolos Windows diretos (mais rápidos e infalíveis)
    protocols = {
        "spotify": "spotify:",
        "discord": "discord:",
        "steam": "steam:",
        "calculadora": "calculator:",
        "calculator": "calculator:",
        "configurações": "ms-settings:",
        "settings": "ms-settings:",
    }
    if name_clean in protocols:
        try:
            os.startfile(protocols[name_clean])
            return f"Abrindo {name}."
        except Exception:
            pass

    # 2. Comandos nativos do Windows padrão
    windows_builtins = {
        "bloco de notas": "notepad",
        "notepad": "notepad",
        "calculadora": "calc",
        "calculator": "calc",
        "calc": "calc",
        "paint": "mspaint",
        "mspaint": "mspaint",
        "explorador": "explorer",
        "explorer": "explorer",
        "cmd": "cmd",
        "terminal": "cmd",
        "powershell": "powershell",
    }
    if name_clean in windows_builtins:
        try:
            subprocess.Popen(windows_builtins[name_clean], shell=True)
            return f"Abrindo {name}."
        except Exception as e:
            return f"❌ Erro ao abrir {name}: {e}"

    # 3. Busca de atalhos (.lnk) no Menu Iniciar do Windows
    start_menu_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]

    for sm_dir in start_menu_dirs:
        if not os.path.exists(sm_dir):
            continue
        for root, _, files in os.walk(sm_dir):
            for f in files:
                if f.lower().endswith(".lnk"):
                    f_name = f.lower()[:-4]
                    if name_clean in f_name or f_name in name_clean:
                        full_lnk = os.path.join(root, f)
                        try:
                            os.startfile(full_lnk)
                            return f"Abrindo {name}."
                        except Exception:
                            pass

    # 4. Caminhos diretos comuns em Program Files e AppData
    known_paths = {
        "spotify": [
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
        ],
        "discord": [
            os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe"),
        ],
        "chrome": [
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "google chrome": [
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        ],
        "vscode": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft VS Code\Code.exe"),
        ],
        "visual studio code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        ],
        "vs code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        ],
        "steam": [
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Steam\steam.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Steam\steam.exe"),
        ],
    }

    if name_clean in known_paths:
        for p in known_paths[name_clean]:
            if os.path.exists(p):
                try:
                    if "Discord\\Update.exe" in p:
                        subprocess.Popen([p, "--processStart", "Discord.exe"])
                    else:
                        os.startfile(p)
                    return f"Abrindo {name}."
                except Exception:
                    pass

    # 5. Fallback final silencioso
    try:
        os.startfile(name_clean)
        return f"Abrindo {name}."
    except Exception:
        return f"Não encontrei o aplicativo '{name}' instalado no computador."


def close_app(name):
    """Fecha um aplicativo pelo nome do processo."""
    if not PSUTIL_AVAILABLE:
        return "❌ psutil não instalado. Instale com: pip install psutil"

    # Mapa de nomes comuns → nomes de processo
    process_map = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "discord": "Discord.exe",
        "spotify": "Spotify.exe",
        "steam": "steam.exe",
        "bloco de notas": "notepad.exe",
        "notepad": "notepad.exe",
        "vscode": "Code.exe",
        "vs code": "Code.exe",
        "visual studio code": "Code.exe",
        "calculadora": "Calculator.exe",
        "paint": "mspaint.exe",
        "explorer": "explorer.exe",
    }

    name_lower = name.strip().lower()
    proc_name = process_map.get(name_lower, f"{name_lower}.exe")

    killed = 0
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == proc_name.lower():
                proc.terminate()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed > 0:
        return f"{name} fechado ({killed} processo(s) encerrado(s))."
    else:
        return f"Não encontrei '{name}' em execução."


def type_text(text):
    """Digita texto no campo ativo do Windows."""
    if not PYAUTOGUI_AVAILABLE:
        return "❌ pyautogui não instalado."

    import time
    time.sleep(0.3)  # pequena pausa para o campo receber foco
    pyautogui.write(text, interval=0.02)
    return f"Texto digitado: \"{text[:50]}{'...' if len(text) > 50 else ''}\""


def press_key(keys):
    """
    Pressiona atalhos de teclado.
    Aceita formatos: "ctrl+s", "alt+f4", "enter", "tab", "f5"
    """
    if not PYAUTOGUI_AVAILABLE:
        return "❌ pyautogui não instalado."

    # Normaliza os nomes das teclas
    key_map = {
        "ctrl": "ctrl", "control": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "enter": "enter", "return": "enter",
        "tab": "tab",
        "esc": "escape", "escape": "escape",
        "space": "space", "espaço": "space",
        "delete": "delete", "del": "delete",
        "backspace": "backspace",
        "up": "up", "cima": "up",
        "down": "down", "baixo": "down",
        "left": "left", "esquerda": "left",
        "right": "right", "direita": "right",
        "win": "win", "windows": "win",
        "printscreen": "printscreen", "print": "printscreen",
    }

    parts = [k.strip().lower() for k in keys.replace("+", " ").split()]
    mapped = []
    for p in parts:
        mapped.append(key_map.get(p, p))

    try:
        if len(mapped) == 1:
            pyautogui.press(mapped[0])
        else:
            pyautogui.hotkey(*mapped)
        return f"Tecla(s) pressionada(s): {' + '.join(mapped)}"
    except Exception as e:
        return f"❌ Erro ao pressionar tecla: {e}"


def search_web(query):
    """Abre uma pesquisa no navegador padrão."""
    import urllib.parse
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"Pesquisa aberta no navegador: \"{query}\""


def get_datetime():
    """Retorna data e hora atual formatados."""
    now = datetime.datetime.now()
    dia_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                  "sexta-feira", "sábado", "domingo"]
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

    ds = dia_semana[now.weekday()]
    mes = meses[now.month - 1]
    hora = now.strftime("%H:%M")

    return f"Hoje é {ds}, {now.day} de {mes} de {now.year}. São {hora}."


def clipboard_read():
    """Lê o conteúdo atual da área de transferência."""
    if not PYPERCLIP_AVAILABLE:
        return "❌ pyperclip não instalado."
    try:
        content = pyperclip.paste()
        if content:
            preview = content[:200] + ("..." if len(content) > 200 else "")
            return f"Clipboard: \"{preview}\""
        else:
            return "A área de transferência está vazia."
    except Exception as e:
        return f"❌ Erro ao ler clipboard: {e}"


def clipboard_write(text):
    """Escreve texto na área de transferência."""
    if not PYPERCLIP_AVAILABLE:
        return "❌ pyperclip não instalado."
    try:
        pyperclip.copy(text)
        return f"Texto copiado para a área de transferência."
    except Exception as e:
        return f"❌ Erro ao copiar: {e}"


def volume_control(action):
    """
    Controla o volume do sistema Windows.
    action: "up" / "aumentar", "down" / "diminuir", "mute" / "mutar"
    """
    if not PYAUTOGUI_AVAILABLE:
        return "❌ pyautogui não instalado."

    action_lower = action.strip().lower()

    if action_lower in ("up", "aumentar", "subir", "mais"):
        for _ in range(5):  # 5 toques = ~10% de volume
            pyautogui.press("volumeup")
        return "Volume aumentado."
    elif action_lower in ("down", "diminuir", "descer", "menos", "baixar"):
        for _ in range(5):
            pyautogui.press("volumedown")
        return "Volume diminuído."
    elif action_lower in ("mute", "mutar", "silenciar", "mudo"):
        pyautogui.press("volumemute")
        return "Volume mutado/desmutado."
    else:
        return f"Ação '{action}' não reconhecida. Use: aumentar, diminuir ou mutar."


def system_info():
    """Retorna informações do sistema (CPU, RAM, disco)."""
    if not PSUTIL_AVAILABLE:
        return "❌ psutil não instalado."

    cpu_pct = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    ram_used_gb = ram.used / (1024 ** 3)
    ram_total_gb = ram.total / (1024 ** 3)
    ram_pct = ram.percent

    disk = psutil.disk_usage("C:\\")
    disk_free_gb = disk.free / (1024 ** 3)
    disk_total_gb = disk.total / (1024 ** 3)

    battery_info = ""
    try:
        bat = psutil.sensors_battery()
        if bat:
            plug = "carregando" if bat.power_plugged else "na bateria"
            battery_info = f" Bateria: {bat.percent}% ({plug})."
    except Exception:
        pass

    return (
        f"CPU: {cpu_pct}% de uso. "
        f"RAM: {ram_used_gb:.1f}GB / {ram_total_gb:.1f}GB ({ram_pct}%). "
        f"Disco C: {disk_free_gb:.0f}GB livres de {disk_total_gb:.0f}GB."
        f"{battery_info}"
    )


# ============================================================
# CATÁLOGO DE FERRAMENTAS (para o prompt da IA)
# ============================================================

TOOL_CATALOG = {
    "screenshot": {
        "description": "Tira um print da tela inteira e salva como imagem",
        "args": {},
        "example": "Tira um print da tela",
        "requires_confirm": False,
    },
    "open_app": {
        "description": "Abre um aplicativo pelo nome",
        "args": {"name": "Nome do app (ex: Discord, Chrome, Bloco de Notas)"},
        "example": "Abre o Discord",
        "requires_confirm": False,
    },
    "close_app": {
        "description": "Fecha um aplicativo em execução",
        "args": {"name": "Nome do app para fechar"},
        "example": "Fecha o Chrome",
        "requires_confirm": True,
    },
    "type_text": {
        "description": "Digita texto no campo ativo da tela",
        "args": {"text": "Texto a ser digitado"},
        "example": "Digita 'Olá mundo'",
        "requires_confirm": True,
    },
    "press_key": {
        "description": "Pressiona uma tecla ou atalho de teclado",
        "args": {"keys": "Teclas (ex: ctrl+s, alt+f4, enter)"},
        "example": "Aperta Ctrl+S",
        "requires_confirm": True,
    },
    "search_web": {
        "description": "Pesquisa algo no Google abrindo o navegador",
        "args": {"query": "Termo de pesquisa"},
        "example": "Pesquisa preço do dólar",
        "requires_confirm": False,
    },
    "get_datetime": {
        "description": "Retorna a data e hora atual",
        "args": {},
        "example": "Que horas são?",
        "requires_confirm": False,
    },
    "clipboard_read": {
        "description": "Lê o conteúdo copiado na área de transferência",
        "args": {},
        "example": "O que tem no clipboard?",
        "requires_confirm": False,
    },
    "clipboard_write": {
        "description": "Copia um texto para a área de transferência",
        "args": {"text": "Texto a copiar"},
        "example": "Copia esse texto",
        "requires_confirm": False,
    },
    "volume_control": {
        "description": "Controla o volume do sistema (aumentar, diminuir, mutar)",
        "args": {"action": "aumentar, diminuir ou mutar"},
        "example": "Aumenta o volume",
        "requires_confirm": False,
    },
    "system_info": {
        "description": "Mostra informações do PC (CPU, RAM, disco)",
        "args": {},
        "example": "Como tá o PC?",
        "requires_confirm": False,
    },
}

# Mapa de nome → função
TOOL_FUNCTIONS = {
    "screenshot": lambda args: screenshot(args.get("save_path")),
    "open_app": lambda args: open_app(args.get("name", "")),
    "close_app": lambda args: close_app(args.get("name", "")),
    "type_text": lambda args: type_text(args.get("text", "")),
    "press_key": lambda args: press_key(args.get("keys", "")),
    "search_web": lambda args: search_web(args.get("query", "")),
    "get_datetime": lambda args: get_datetime(),
    "clipboard_read": lambda args: clipboard_read(),
    "clipboard_write": lambda args: clipboard_write(args.get("text", "")),
    "volume_control": lambda args: volume_control(args.get("action", "")),
    "system_info": lambda args: system_info(),
}


def get_tools_prompt():
    """Gera a descrição de ferramentas para injetar no system prompt da IA."""
    lines = [
        "Você tem acesso às seguintes FERRAMENTAS para controlar o PC do usuário.",
        "Quando quiser usar uma ferramenta, responda APENAS com um bloco JSON assim:",
        "",
        '```json',
        '{"tool": "nome_da_ferramenta", "args": {"argumento": "valor"}}',
        '```',
        "",
        "Se a ferramenta não precisa de argumentos, use args vazio: {}",
        "IMPORTANTE: Quando quiser usar uma ferramenta, responda SOMENTE com o JSON, sem texto extra.",
        "Se não precisar de ferramenta, responda normalmente em texto.",
        "",
        "Ferramentas disponíveis:",
    ]

    for name, info in TOOL_CATALOG.items():
        args_desc = ""
        if info["args"]:
            args_list = [f'{k}: {v}' for k, v in info["args"].items()]
            args_desc = f" | Args: {', '.join(args_list)}"
        lines.append(f"  • {name}: {info['description']}{args_desc}")
        lines.append(f"    Exemplo do usuário: \"{info['example']}\"")

    return "\n".join(lines)
