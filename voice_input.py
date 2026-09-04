"""
Atlas v4 — Voice Input com detecção precisa de Wake Word 'ATLAS',
resposta de voz imediata ('Sim?') e Silero VAD.
"""
import math
import time
import re
import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    WhisperModel = None

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

# Variações fonéticas de Atlas que o Whisper pode reconhecer
WAKE_VARIATIONS = {
    "atlas", "atla", "atlá", "atras", "atrás", "atlass", "atletas", "atas", "alas", "actas"
}


class VoiceInput:
    """Captura áudio do microfone via chamada viva 'ATLAS' ou Hotkey F8 e transcreve com Whisper local."""

    def __init__(
        self,
        model_size="medium",
        hotkey="f8",
        use_wakeword=True,
        wakeword_name="Atlas",
        vad=None,
        voice_out=None,
        gui=None,
    ):
        self.hotkey = hotkey
        self.target_samplerate = 16000  # Whisper requer 16kHz
        self.model = None
        self.use_wakeword = use_wakeword
        self.wakeword_name = wakeword_name.lower()
        self.vad = vad  # SileroVAD instance
        self.voice_out = voice_out  # VoiceOutput instance para resposta rápida ('Sim?')
        self.gui = gui  # AtlasGUI instance para sincronização visual
        self.is_processing = False
        self._buffer = []
        self._is_recording = False

        if not WHISPER_AVAILABLE:
            print("[voice] faster-whisper não instalado. Modo texto apenas.")
            return

        # Configura microfone padrão do Windows
        self._setup_default_device()

        # Carrega Whisper principal
        print(f"[voice] Carregando Whisper '{model_size}'... ", end="", flush=True)
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("OK!")

    def _setup_default_device(self):
        """Detecta a taxa nativa do microfone padrão do Windows."""
        try:
            device_info = sd.query_devices(kind="input")
            self.native_samplerate = int(device_info["default_samplerate"])
            dev_name = device_info.get("name", "Microfone Padrão")
            print(f"[voice] Microfone padrão Windows: {dev_name} ({self.native_samplerate}Hz)")
        except Exception as e:
            print(f"[voice] Erro ao consultar microfone: {e}. Usando 44100Hz.")
            self.native_samplerate = 44100

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback do sounddevice para gravação via F8."""
        if self._is_recording:
            self._buffer.append(indata.copy())

    def _resample_audio(self, audio, orig_rate, target_rate):
        """Reamostragem de alta fidelidade via scipy resample_poly."""
        if orig_rate == target_rate:
            return audio.astype(np.float32)

        gcd = math.gcd(int(orig_rate), int(target_rate))
        up = int(target_rate) // gcd
        down = int(orig_rate) // gcd

        resampled = resample_poly(audio, up, down)
        return resampled.astype(np.float32)

    def _normalize_audio(self, audio):
        """Normaliza o volume para evitar áudio estourado ou muito baixo."""
        max_val = np.max(np.abs(audio))
        if max_val > 0.001:
            audio = audio / max_val * 0.90
        return audio

    @property
    def available(self):
        return self.model is not None

    def lock(self):
        self.is_processing = True

    def unlock(self):
        self.is_processing = False

    def listen_input(self):
        """
        Método principal de entrada. Se use_wakeword estiver ativo, escuta pela chamada 'ATLAS'.
        Caso contrário (ou como fallback), escuta por F8.
        """
        if self.use_wakeword and self.vad and self.vad.available:
            return self._listen_atlas_wakeword()
        else:
            return self.record_on_hotkey()

    def _listen_atlas_wakeword(self):
        """
        Escuta o microfone usando Silero VAD para capturar fala sem latência.
        Ao detectar 'ATLAS', responde por voz ('Sim?') e depois grava a pergunta.
        """
        if not self.available or self.is_processing:
            return None

        print(f"\n🎤 Ouvindo ativamente... (Diga 'ATLAS' ou 'EI ATLAS', ou segure {self.hotkey.upper()})")

        while not self.is_processing:
            # Atalho manual F8 sempre funcional a qualquer momento
            if KEYBOARD_AVAILABLE and keyboard.is_pressed(self.hotkey):
                return self.record_on_hotkey()

            # Silero VAD aguarda fala humana com pre-buffer (não corta início)
            audio_16k = self.vad.listen_until_silence(
                silence_s=0.45,
                is_interrupted=lambda: self.is_processing or (KEYBOARD_AVAILABLE and keyboard.is_pressed(self.hotkey)),
            )

            if audio_16k is None or len(audio_16k) == 0:
                time.sleep(0.01)
                continue

            # Transcreve com Whisper rápido com contexto prioritário para Atlas
            audio_norm = self._normalize_audio(audio_16k)
            try:
                segments, _ = self.model.transcribe(
                    audio_norm,
                    language="pt",
                    beam_size=1,
                    vad_filter=False,
                    initial_prompt="Atlas. Ei Atlas. Assistente Atlas.",
                )
                heard_text = " ".join(s.text for s in segments).strip()
            except Exception:
                continue

            if not heard_text:
                continue

            # Limpa pontuações para análise de palavras
            clean_text = re.sub(r'[^\w\s]', '', heard_text.lower()).strip()
            words = clean_text.split()

            # Procura por qualquer variação da palavra de ativação
            wake_idx = -1
            for idx, w in enumerate(words):
                if w in WAKE_VARIATIONS:
                    wake_idx = idx
                    break

            if wake_idx != -1:
                print(f"\n🔥 [WAKE WORD DETECTADA: ATLAS]")

                # Caso 1: Usuário já fez a pergunta na mesma frase (ex: "Atlas que horas são?")
                remaining_words = words[wake_idx + 1:]
                if len(remaining_words) >= 2:
                    if self.gui:
                        self.gui.set_state("thinking")
                    question = " ".join(remaining_words)
                    print(f"   🎉 Pergunta capturada na frase: \"{question}\"")
                    return question

                # Caso 2: Usuário chamou pelo nome "Atlas"!
                # Atlas responde imediatamente com áudio ("Sim?")
                if self.voice_out and self.voice_out.available:
                    self.voice_out.acknowledge("Sim?")
                else:
                    print("\nAtlas: Sim?")

                # Só AGORA abre o microfone para o usuário falar a pergunta!
                if self.gui:
                    self.gui.set_state("listening")
                print("   🔴 Pode falar sua pergunta...")
                q_audio = self.vad.listen_until_silence(
                    silence_s=0.45,
                    is_interrupted=lambda: self.is_processing,
                )

                if q_audio is not None and len(q_audio) > 0:
                    if self.gui:
                        self.gui.set_state("thinking")
                    q_norm = self._normalize_audio(q_audio)
                    print("   ⏳ Processando...", end="", flush=True)
                    text = self._transcribe(q_norm)
                    if text:
                        print(" OK!")
                        return text
                    else:
                        if self.gui:
                            self.gui.set_state("idle")
                        print(" (não entendi a pergunta)")
                else:
                    if self.gui:
                        self.gui.set_state("idle")
                    print(" (nenhuma pergunta detectada)")

            time.sleep(0.01)

        return None

    def record_on_hotkey(self):
        """Espera o usuário pressionar F8, grava via callback enquanto segurada, e transcreve."""
        if not self.available or self.is_processing:
            return None

        if not KEYBOARD_AVAILABLE:
            print("[voice] keyboard não instalado. Modo texto apenas.")
            return None

        print(f"\n🎤 Segure {self.hotkey.upper()} para falar, solte para processar...")

        keyboard.wait(self.hotkey)

        if self.is_processing:
            return None

        print("   🔴 Gravando...", end="", flush=True)

        sr = self.native_samplerate
        self._buffer = []

        try:
            with sd.InputStream(
                device=None,
                samplerate=sr,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            ):
                self._is_recording = True
                while keyboard.is_pressed(self.hotkey):
                    time.sleep(0.02)
                self._is_recording = False
        except Exception as e:
            print(f"\n   [voice] Erro na gravação: {e}")
            self._is_recording = False
            return None

        if not self._buffer:
            print(" (nenhum áudio capturado)")
            return None

        audio = np.concatenate(self._buffer, axis=0).flatten().astype(np.float32)
        duration = len(audio) / sr

        if duration < 0.4:
            print(f" ({duration:.1f}s — muito curto, ignorado)")
            return None

        audio_16k = self._resample_audio(audio, sr, self.target_samplerate)
        audio_final = self._normalize_audio(audio_16k)

        print(f" ({duration:.1f}s capturados)")
        print("   ⏳ Transcrevendo...", end="", flush=True)

        text = self._transcribe(audio_final)

        if text:
            print(f" OK!")
            return text
        else:
            print(" (não entendi, tente novamente)")
            return None

    def _transcribe(self, audio):
        """Transcreve o áudio com o Whisper principal."""
        try:
            segments, info = self.model.transcribe(
                audio,
                language="pt",
                beam_size=1,
                vad_filter=False,
                condition_on_previous_text=False,
                initial_prompt="Conversa em português do Brasil com o assistente inteligente Atlas.",
            )
            text = " ".join(s.text for s in segments).strip()
            return text if text else None
        except Exception as e:
            print(f"\n   [voice] Erro na transcrição: {e}")
            return None
