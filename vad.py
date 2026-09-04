"""
Atlas v3.5 — Silero VAD Wrapper
Detecta início e fim de fala via Silero VAD v5 (1.8MB, CPU-only).
Substitui o timer fixo de 4 segundos por detecção natural de silêncio.
"""
import math
import time
import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

try:
    from silero_vad import load_silero_vad, get_speech_timestamps
    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False


class SileroVAD:
    """
    Silero VAD v5: detecta voz em tempo real e grava até silêncio natural.
    RAM extra: ~200MB (torch runtime + modelo de 1.8MB).
    """

    # Parâmetros VAD
    CHUNK_SAMPLES_16K = 512        # 32ms por chunk @ 16kHz (exigido pelo Silero)
    VAD_THRESHOLD = 0.4            # probabilidade mínima para considerar voz
    SILENCE_DURATION_S = 0.6       # segundos de silêncio para encerrar a gravação
    MIN_SPEECH_DURATION_S = 0.3    # ignora ruídos curtíssimos (< 300ms)
    MAX_RECORD_DURATION_S = 60     # segurança: corta em 60s mesmo sem silêncio

    def __init__(self, native_samplerate=44100):
        self.native_samplerate = native_samplerate
        self.model = None
        self.available = False

        if not SILERO_AVAILABLE:
            print("[vad] silero-vad não instalado. Use: pip install silero-vad")
            return

        try:
            import torch
            print("[vad] Carregando Silero VAD... ", end="", flush=True)
            self.model = load_silero_vad()
            self.model.eval()
            self.available = True
            print("OK!")
        except Exception as e:
            print(f"Erro: {e}")

    def _resample_to_16k(self, audio_f32, orig_rate):
        """Reamostra áudio nativo → 16kHz para o Silero."""
        if orig_rate == 16000:
            return audio_f32.astype(np.float32)
        gcd = math.gcd(int(orig_rate), 16000)
        up = 16000 // gcd
        down = orig_rate // gcd
        return resample_poly(audio_f32, up, down).astype(np.float32)

    def _to_torch(self, audio_f32):
        """Converte numpy float32 → tensor torch float32."""
        import torch
        return torch.from_numpy(audio_f32)

    def listen_until_silence(
        self,
        silence_s=None,
        on_speech_start=None,
        is_interrupted=None,
    ):
        """
        Grava do microfone até detectar silêncio natural (padrão: 0.6s).

        Parâmetros:
          silence_s: segundos de silêncio para encerrar (None → usa SILENCE_DURATION_S)
          on_speech_start: callback chamado quando a voz começa (ex: mostrar "🔴 Gravando...")
          is_interrupted: callable que retorna True se a gravação deve ser abortada

        Retorna: np.ndarray float32 @ 16kHz com a fala capturada, ou None se vazio.
        """
        if not self.available:
            return None

        silence_s = silence_s or self.SILENCE_DURATION_S
        silence_chunks_needed = int(silence_s / (self.CHUNK_SAMPLES_16K / 16000))

        sr = self.native_samplerate
        chunk_native = int(self.CHUNK_SAMPLES_16K * sr / 16000)

        recording = []          # áudio gravado (16kHz)
        speech_started = False
        speech_frames = 0
        silence_chunks = 0
        total_chunks = 0
        max_chunks = int(self.MAX_RECORD_DURATION_S / (self.CHUNK_SAMPLES_16K / 16000))
        pre_buffer_size = 10  # ~320ms de áudio antes do início da fala
        pre_buffer = []

        try:
            with sd.InputStream(device=None, samplerate=sr, channels=1, dtype="float32") as stream:
                while total_chunks < max_chunks:
                    if is_interrupted and is_interrupted():
                        return None

                    data, _ = stream.read(chunk_native)
                    chunk_f32 = data.flatten()
                    chunk_16k = self._resample_to_16k(chunk_f32, sr)
                    total_chunks += 1

                    # Predição VAD (32ms por chamada)
                    t = self._to_torch(chunk_16k)
                    with __import__("torch").no_grad():
                        speech_prob = self.model(t, 16000).item()

                    is_speech = speech_prob >= 0.25  # Mais sensível para voz humana

                    if is_speech:
                        silence_chunks = 0
                        speech_frames += 1

                        if not speech_started:
                            speech_started = True
                            if on_speech_start:
                                on_speech_start()
                            # Inclui o pre-buffer para não cortar o 'A' de 'Atlas'
                            recording.extend(pre_buffer)

                        recording.append(chunk_16k)

                    elif speech_started:
                        recording.append(chunk_16k)
                        silence_chunks += 1

                        if silence_chunks >= silence_chunks_needed:
                            break  # silêncio suficiente → encerra
                    else:
                        # Mantém os últimos 320ms no pre-buffer
                        pre_buffer.append(chunk_16k)
                        if len(pre_buffer) > pre_buffer_size:
                            pre_buffer.pop(0)

        except Exception as e:
            print(f"\n[vad] Erro na gravação: {e}")
            return None

        if not recording:
            return None

        audio = np.concatenate(recording)

        # Descarta se muito curto (ruído acidental)
        duration = len(audio) / 16000
        if duration < self.MIN_SPEECH_DURATION_S:
            return None

        return audio

    def is_speech_present(self, audio_chunk_16k):
        """
        Verifica se há voz em um chunk de áudio (para barge-in em tempo real).
        Retorna probabilidade 0.0-1.0.
        """
        if not self.available:
            return 0.0
        try:
            t = self._to_torch(audio_chunk_16k.astype(np.float32))
            with __import__("torch").no_grad():
                return self.model(t, 16000).item()
        except Exception:
            return 0.0
