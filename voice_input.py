import math
import time
import re
import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

# Tenta importar dependências
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


class VoiceInput:
    """Captura áudio do microfone via chamada 'ATLAS' ou Hotkey F8 e transcreve com Whisper local."""

    def __init__(
        self,
        model_size="medium",
        hotkey="f8",
        use_wakeword=True,
        wakeword_name="Atlas",
    ):
        self.hotkey = hotkey
        self.target_samplerate = 16000  # Whisper requer 16kHz
        self.model = None
        self.tiny_model = None
        self.use_wakeword = use_wakeword
        self.wakeword_name = wakeword_name.lower()
        self.is_processing = False
        self._buffer = []
        self._is_recording = False

        if not WHISPER_AVAILABLE:
            print("[voice] faster-whisper não instalado. Modo texto apenas.")
            return

        # Configura microfone padrão do Windows
        self._setup_default_device()

        # Carrega Whisper principal (medium/small para transcrição perfeita)
        print(f"[voice] Carregando Whisper '{model_size}'... ", end="", flush=True)
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("OK!")

        # Carrega detector ultrarrápido para a palavra 'ATLAS'
        if self.use_wakeword:
            try:
                print(f"[voice] Carregando detector de ativação 'ATLAS'... ", end="", flush=True)
                self.tiny_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                print("OK!")
            except Exception as e:
                print(f"Erro: {e}")
                self.use_wakeword = False

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
        if self.use_wakeword and self.tiny_model:
            return self._listen_atlas_wakeword()
        else:
            return self.record_on_hotkey()

    def _listen_atlas_wakeword(self):
        """Escuta continuamente no microfone chamadas pelo nome 'ATLAS' (ou 'Ei Atlas' / 'Hey Atlas')."""
        if not self.available or self.is_processing:
            return None

        print(f"\n🎤 Ouvindo... (Chame 'ATLAS' ou 'EI ATLAS', ou segure {self.hotkey.upper()})")

        sr = self.native_samplerate
        chunk_duration = 1.2  # janela de 1.2s para detectar a palavra 'Atlas'
        chunk_samples = int(sr * chunk_duration)

        try:
            with sd.InputStream(device=None, samplerate=sr, channels=1, dtype="float32") as stream:
                while not self.is_processing:
                    # Atalho manual F8 sempre funcional
                    if KEYBOARD_AVAILABLE and keyboard.is_pressed(self.hotkey):
                        return self.record_on_hotkey()

                    data, _ = stream.read(chunk_samples)
                    audio_f32 = data.flatten()

                    max_vol = np.max(np.abs(audio_f32))

                    # Só processa se houver voz/som no microfone
                    if max_vol > 0.015:
                        audio_16k = self._resample_audio(audio_f32, sr, self.target_samplerate)
                        audio_norm = self._normalize_audio(audio_16k)

                        # Teste ultrarrápido com modelo tiny (50ms)
                        segments, _ = self.tiny_model.transcribe(
                            audio_norm,
                            language="pt",
                            beam_size=1,
                            vad_filter=False,
                            no_speech_threshold=0.5,
                        )
                        detected_text = " ".join(s.text for s in segments).strip().lower()

                        # Verifica se 'atlas' ou variações fonéticas estão no texto
                        if re.search(r'\b(atlas|atla|atlass|ei atlas|hey atlas)\b', detected_text):
                            print(f"\n🔥 [WAKE WORD DETECTADA: ATLAS]")

                            # Checa se o usuário já fez a pergunta na mesma frase (ex: "Atlas que horas são?")
                            match = re.search(r'\b(?:atlas|atla|atlass|ei atlas|hey atlas)\b\s*(.+)', detected_text)
                            if match and len(match.group(1).split()) >= 2:
                                question = match.group(1).strip()
                                print(f"   🎉 Pergunta capturada na frase: \"{question}\"")
                                return question

                            # Caso só tenha dito "Atlas", grava a pergunta por 4 segundos
                            print("   🔴 Gravando sua pergunta (4 segundos)... FALE AGORA!")
                            question_audio = sd.rec(int(sr * 4.0), samplerate=sr, channels=1, dtype="float32")
                            sd.wait()
                            question_audio = question_audio.flatten()

                            q_vol = np.max(np.abs(question_audio))
                            if q_vol > 0.001:
                                q_16k = self._resample_audio(question_audio, sr, self.target_samplerate)
                                q_norm = self._normalize_audio(q_16k)

                                print("   ⏳ Transcrevendo...", end="", flush=True)
                                text = self._transcribe(q_norm)
                                if text:
                                    print(" OK!")
                                    return text
                                else:
                                    print(" (não entendi, tente novamente)")
                                    return None
                            else:
                                print(" (áudio zerado)")
                                return None

                    time.sleep(0.02)
        except Exception as e:
            print(f"\n   [voice] Erro no Wake Word Atlas: {e}")
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
                beam_size=5,
                vad_filter=False,
                condition_on_previous_text=False,
                initial_prompt="Conversa em português do Brasil com o assistente inteligente Atlas.",
            )
            text = " ".join(s.text for s in segments).strip()
            return text if text else None
        except Exception as e:
            print(f"\n   [voice] Erro na transcrição: {e}")
            return None
