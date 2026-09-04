"""
Atlas v5 — Interface Desktop (Buraco Negro 3D)
Janela 100% transparente, sem bordas, oculta da barra de tarefas
e integrada à bandeja do sistema (aba de ícones ocultos / System Tray).
"""
import os
import sys
import threading
import ctypes
from ctypes import wintypes

# Define fundo transparente para o runtime do WebView2 antes de inicializar
os.environ["WEBVIEW2_DEFAULT_BACKGROUND_COLOR"] = "0"

import webview

try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

try:
    import clr
    clr.AddReference('System.Drawing')
    clr.AddReference('System.Windows.Forms')
    from System.Drawing import Color
    from System import Action
    CLR_AVAILABLE = True
except Exception:
    CLR_AVAILABLE = False

try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class AtlasGUI:
    def __init__(self, html_path=None):
        self.window = None
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.html_path = html_path or os.path.join(base_dir, "ui", "black_hole.html")
        self.current_state = "idle"
        self.is_loaded = False
        self.tray_icon = None

    def create_window(self):
        """Cria e posiciona a janela flutuante no canto superior direito."""
        screen_width = 1920
        try:
            if webview.screens and len(webview.screens) > 0:
                screen_width = webview.screens[0].width
        except Exception:
            pass

        win_w = 280
        win_h = 280
        pos_x = max(20, screen_width - win_w - 20)
        pos_y = 20

        # Criação da janela flutuante com cor-chave para transparência
        self.window = webview.create_window(
            title="Atlas Core",
            url=self.html_path,
            width=win_w,
            height=win_h,
            x=pos_x,
            y=pos_y,
            frameless=True,
            easy_drag=True,
            on_top=True,
            shadow=False,
            background_color="#050711",
        )

        # Hook para aplicar transparência por ColorKey e remover da barra de tarefas
        self.window.events.shown += self._setup_native_window
        return self.window

    def _setup_native_window(self):
        """
        Aplica transparência via Colorkey nativo do Windows (SetLayeredWindowAttributes)
        e oculta da barra de tarefas (WS_EX_TOOLWINDOW).
        """
        try:
            form = self.window.native
            if form:
                hwnd = form.Handle.ToInt64()
                user32 = ctypes.windll.user32
                GWL_EXSTYLE = -20
                WS_EX_LAYERED = 0x00080000
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_APPWINDOW = 0x00040000
                LWA_COLORKEY = 0x00000001

                # COLORREF para #050711 (0x00BBGGRR: R=0x05, G=0x07, B=0x11 -> 0x00110705)
                crKey = 0x00110705

                style = user32.GetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE)
                new_style = (style | WS_EX_LAYERED | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
                user32.SetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE, new_style)
                user32.SetLayeredWindowAttributes(wintypes.HWND(hwnd), crKey, 0, LWA_COLORKEY)
                user32.SetWindowPos(
                    wintypes.HWND(hwnd), 0, 0, 0, 0, 0,
                    0x0001 | 0x0002 | 0x0004 | 0x0020
                )
                print("[GUI] Orbe flutuante transparente ativada com sucesso.")

        except Exception as e:
            print(f"[gui] Aviso ao configurar janela nativa: {e}")

    def _start_tray_icon(self):
        """Cria o ícone na aba de ícones ocultos (System Tray) ao lado do relógio."""
        if not PYSTRAY_AVAILABLE:
            return

        try:
            # Gera imagem do ícone da Atlas (Buraco Negro com anel cósmico)
            img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse((4, 4, 60, 60), fill=(14, 116, 144, 255), outline=(56, 189, 248, 255), width=4)
            d.ellipse((18, 18, 46, 46), fill=(2, 2, 5, 255), outline=(125, 211, 252, 255), width=3)

            def toggle_orb(icon, item):
                if self.window and self.window.native:
                    try:
                        form = self.window.native
                        if CLR_AVAILABLE:
                            def _toggle():
                                if form.Visible:
                                    form.Hide()
                                else:
                                    form.Show()
                                    form.Activate()
                            form.BeginInvoke(Action(_toggle))
                        else:
                            if form.Visible:
                                form.Hide()
                            else:
                                form.Show()
                    except Exception as err:
                        print(f"[gui] Erro ao alternar orbe: {err}")

            def quit_app(icon, item):
                icon.stop()
                if self.window:
                    self.window.destroy()
                os._exit(0)

            menu = pystray.Menu(
                pystray.MenuItem("Exibir / Ocultar Orbe", toggle_orb, default=True),
                pystray.MenuItem("Sair do Atlas", quit_app),
            )

            self.tray_icon = pystray.Icon("Atlas", img, "Atlas Assistant", menu)
            self.tray_icon.run_detached()
            print("[System Tray] Ícone ativo na aba de ícones ocultos do Windows.")
        except Exception as e:
            print(f"[gui] Aviso ao iniciar System Tray: {e}")

    def set_state(self, state):
        """
        Atualiza o estado visual da orbe:
          'idle'      -> Vácuo cósmico (Ciano calmo)
          'listening' -> Absorção de voz (Verde esmeralda neon)
          'thinking'  -> Dobra temporal (Roxo / Violeta em alta rotação)
          'speaking'  -> Radiação Hawking (Solar / Fogo com ondas gravitacionais)
        """
        self.current_state = state
        if self.window:
            try:
                self.window.evaluate_js(f"if (window.setMode) window.setMode('{state}')")
            except Exception:
                pass

    def set_status_text(self, text):
        """Atualiza a pílula de texto embaixo da orbe."""
        if self.window:
            try:
                clean = text.replace("'", "\\'")
                self.window.evaluate_js(f"if (window.setStatusText) window.setStatusText('{clean}')")
            except Exception:
                pass

    def start(self, worker_func=None):
        """Inicia a bandeja do sistema e o loop da interface gráfica."""
        self._start_tray_icon()
        webview.start(worker_func, debug=False)
