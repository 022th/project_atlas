"""
Atlas v4 — Voice Output com Edge-TTS (Francisca Neural)
Gera áudio contínuo e natural (sem pausas robóticas entre frases)
e suporta interrupção instantânea (ESC, F8 ou detecção de voz).
"""
import asyncio
import os
import re
import tempfile
import threading
import time

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class VoiceOutput:
    """Converte texto em fala usando Edge-TTS com prosódia natural e fluida."""

    def __init__(self, voice="pt-BR-FranciscaNeural", gui=None):
        self.voice = voice
        self.gui = gui
        self.temp_dir = tempfile.gettempdir()
        self._speaking = False
        self._stop_flag = threading.Event()

        if EDGE_TTS_AVAILABLE and PYGAME_AVAILABLE:
            pygame.mixer.init()
            self.available = True
            print(f"[voice] TTS ativo: {voice}")
            # Pré-gera o áudio de confirmação para latência 0 ao ser chamada
            self._ack_cache = os.path.join(self.temp_dir, "atlas_ack_sim.mp3")
            try:
                asyncio.run(self._generate_audio("Sim?", self._ack_cache))
            except Exception:
                pass
        else:
            self.available = False
            missing = []
            if not EDGE_TTS_AVAILABLE:
                missing.append("edge-tts")
            if not PYGAME_AVAILABLE:
                missing.append("pygame")
            print(f"[voice] TTS indisponível. Instale: pip install {' '.join(missing)}")

    def _clean_text(self, text):
        """Limpa código, markdown e JSON para o áudio falar de forma 100% natural."""
        if not text:
            return ""

        # Remove blocos de código com ``` ... ```
        text = re.sub(r'```(?:json|python|[a-zA-Z]*)?[\s\S]*?```', '', text)

        # Remove blocos de JSON { ... } para NUNCA falar código
        text = re.sub(r'\{[\s\S]*?\}', '', text)

        # Remove tags como "json", "python" soltas
        text = re.sub(r'^\s*(?:json|code|python)\b', '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Remove formatação markdown
        text = re.sub(r'[*#_`~>]', '', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)

        # Limpa espaços e quebras repetidas
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _is_interrupted(self):
        """Verifica interrupção por tecla (ESC/F8) ou flag."""
        if self._stop_flag.is_set():
            return True
        if KEYBOARD_AVAILABLE and (keyboard.is_pressed("esc") or keyboard.is_pressed("f8")):
            return True
        return False

    def stop(self):
        """Interrompe a fala imediatamente."""
        self._stop_flag.set()
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    @property
    def is_speaking(self):
        return self._speaking

    def speak(self, text):
        """
        Converte o texto completo em fala com prosódia natural contínua.
        Toca sem pausas estranhas entre frases e permite interrupção por ESC/F8.
        """
        if not self.available or not text:
            return

        clean = self._clean_text(text)
        if not clean or len(clean.strip()) == 0:
            return

        try:
            if self.gui:
                self.gui.set_state("speaking")
            self._stop_flag.clear()
            self._speaking = True
            audio_path = os.path.join(self.temp_dir, "atlas_response.mp3")

            # Gera áudio contínuo de uma só vez (sem cortes robóticos)
            asyncio.run(self._generate_audio(clean, audio_path))

            # Reprodução
            self._play(audio_path)
        except Exception as e:
            print(f"[voice] Erro no TTS: {e}")
        finally:
            self._speaking = False
            if self.gui:
                self.gui.set_state("idle")

    def acknowledge(self, phrase="Sim?"):
        """Responde imediatamente ao chamado com voz (ex: 'Sim?') em 0ms."""
        if not self.available:
            return
        try:
            if self.gui:
                self.gui.set_state("speaking")
            self._speaking = True
            print(f"\nAtlas: {phrase}")
            # Se for "Sim?" e já estiver em cache, toca direto em 0ms
            if phrase == "Sim?" and hasattr(self, "_ack_cache") and os.path.exists(self._ack_cache):
                self._play(self._ack_cache)
                return

            ack_path = os.path.join(self.temp_dir, "atlas_ack.mp3")
            asyncio.run(self._generate_audio(phrase, ack_path))
            self._play(ack_path)
        except Exception as e:
            print(f"[voice] Erro no acknowledge: {e}")
        finally:
            self._speaking = False

    async def _generate_audio(self, text, output_path):
        """Gera o áudio neural via Edge-TTS."""
        communicate = edge_tts.Communicate(text, voice=self.voice)
        await communicate.save(output_path)

    def _play(self, filepath):
        """Toca o áudio com monitoramento de interrupção instantânea."""
        try:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if self._is_interrupted():
                    pygame.mixer.music.stop()
                    print("\n   ⏹️ [Fala interrompida]")
                    break
                pygame.time.wait(30)
        finally:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
