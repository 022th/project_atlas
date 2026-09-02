import asyncio
import os
import tempfile

# Tenta importar edge-tts, pygame e keyboard
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
    """Converte texto em fala usando Edge-TTS (vozes neurais gratuitas da Microsoft)."""

    def __init__(self, voice="pt-BR-FranciscaNeural"):
        self.voice = voice
        self.temp_dir = tempfile.gettempdir()

        if EDGE_TTS_AVAILABLE and PYGAME_AVAILABLE:
            pygame.mixer.init()
            self.available = True
            print(f"[voice] TTS ativo: {voice}")
        else:
            self.available = False
            missing = []
            if not EDGE_TTS_AVAILABLE:
                missing.append("edge-tts")
            if not PYGAME_AVAILABLE:
                missing.append("pygame")
            print(f"[voice] TTS indisponível. Instale: pip install {' '.join(missing)}")

    def _clean_text_for_speech(self, text):
        """Limpa marcações markdown (*, #, `, _, etc) para o áudio falar de forma fluida."""
        import re
        text = re.sub(r'[\*#_`~>]', '', text)  # remove símbolos de markdown
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # converte [link](url) em apenas texto
        text = re.sub(r'\s+', ' ', text).strip()  # limpa espaços extras
        return text

    def stop(self):
        """Interrompe a reprodução de áudio imediatamente."""
        if PYGAME_AVAILABLE and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

    def speak(self, text):
        """Converte texto em áudio e toca no speaker com suporte a interrupção por tecla (ESC ou F8)."""
        if not self.available:
            return

        try:
            clean_text = self._clean_text_for_speech(text)
            if not clean_text:
                return
            audio_path = os.path.join(self.temp_dir, "atlas_response.mp3")
            asyncio.run(self._generate_audio(clean_text, audio_path))
            self._play(audio_path)
        except Exception as e:
            print(f"[voice] Erro no TTS: {e}")

    async def _generate_audio(self, text, output_path):
        """Gera o arquivo de áudio com edge-tts."""
        communicate = edge_tts.Communicate(text, voice=self.voice)
        await communicate.save(output_path)

    def _play(self, filepath):
        """Toca o áudio. Pode ser interrompido imediatamente pressionando ESC ou F8."""
        try:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                # Interrupção instantânea: ESC cancela, F8 cancela e já abre pra falar
                if KEYBOARD_AVAILABLE and (keyboard.is_pressed("esc") or keyboard.is_pressed("f8")):
                    pygame.mixer.music.stop()
                    print("\n   ⏹️ [Fala interrompida]")
                    break
                pygame.time.wait(30)
        finally:
            pygame.mixer.music.unload()
