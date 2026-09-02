"""Script de teste isolado para Palavra de Ativação (Wake Word) com openWakeWord."""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import time
import math
import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from openwakeword.model import Model
from faster_whisper import WhisperModel

print("=== TESTE DE WAKE WORD (PALAVRA DE ATIVAÇÃO) ===")

# Detecta microfone padrão do Windows
device_info = sd.query_devices(kind="input")
native_sr = int(device_info["default_samplerate"])
dev_name = device_info.get("name", "Microfone Padrão")
print(f"🎤 Microfone: {dev_name} ({native_sr}Hz)")

print("⏳ Carregando detector de Wake Word (openWakeWord)...")
# Usando 'hey_jarvis' ou 'alexa' como modelo de teste pré-treinado
oww_model = Model(wakeword_models=["hey_jarvis", "alexa"], inference_framework="onnx")
print("✅ Detector pronto! (Modelos de teste: 'Hey Jarvis' ou 'Alexa')")

print("⏳ Carregando Whisper...")
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
print("✅ Whisper pronto!")

print("\n--------------------------------------------------")
print("👉 O microfone está ouvindo em segundo plano (CPU ~0.5%)")
print("🗣️  Diga \"HEY JARVIS\" ou \"ALEXA\" em voz alta para ativar!")
print("   Pressione CTRL+C para sair.")
print("--------------------------------------------------\n")

# openWakeWord espera áudio em 16kHz int16 em blocos de 1280 amostras (80ms)
chunk_size_16k = 1280
chunk_size_native = int(chunk_size_16k * native_sr / 16000)

gcd = math.gcd(native_sr, 16000)
up = 16000 // gcd
down = native_sr // gcd

def resample_to_16k_int16(audio_float32):
    """Converte e reamostra áudio nativo para 16kHz int16 pro openWakeWord."""
    if native_sr != 16000:
        resampled = resample_poly(audio_float32, up, down)
    else:
        resampled = audio_float32
    # Converte float32 (-1.0 a 1.0) para int16
    return (np.clip(resampled, -1.0, 1.0) * 32767).astype(np.int16)

try:
    with sd.InputStream(device=None, samplerate=native_sr, channels=1, dtype="float32") as stream:
        print("🟢 Ouvindo ativamente...\n")
        while True:
            # Lê um bloco do microfone
            data, _ = stream.read(chunk_size_native)
            audio_f32 = data.flatten()

            # Prepara para openWakeWord
            audio_16k_i16 = resample_to_16k_int16(audio_f32)

            # Previsão da palavra de ativação
            prediction = oww_model.predict(audio_16k_i16)

            # Verifica pontuação
            for wakeword, score in oww_model.prediction_buffer.items():
                if score[-1] > 0.5:  # Limiar de confiança 50%
                    print(f"🔥 ATIVADO! Palavra detectada: \"{wakeword}\" (confiança: {score[-1]:.2f})")
                    print("   🔴 Gravando sua pergunta (4 segundos)... FALE AGORA!")

                    # Grava 4 segundos de pergunta
                    question_audio = sd.rec(int(native_sr * 4.0), samplerate=native_sr, channels=1, dtype="float32")
                    sd.wait()
                    question_audio = question_audio.flatten()

                    # Transcreve com Whisper
                    max_vol = np.max(np.abs(question_audio))
                    if max_vol > 0.001:
                        q_16k = resample_poly(question_audio, up, down).astype(np.float32)
                        q_norm = q_16k / max_vol * 0.90

                        print("   ⏳ Transcrevendo...")
                        segments, _ = whisper_model.transcribe(q_norm, language="pt", beam_size=5, vad_filter=False)
                        text = " ".join(s.text for s in segments).strip()

                        if text:
                            print(f"   🎉 Pergunta capturada: \"{text}\"\n")
                        else:
                            print("   ❌ Não entendi o que você disse após a ativação.\n")
                    else:
                        print("   ❌ Áudio zerado após a ativação.\n")

                    # Reseta o buffer da previsão para não reativar em loop
                    oww_model.reset()
                    print("🟢 Voltando a ouvir em segundo plano...\n")
                    break

            time.sleep(0.01)

except KeyboardInterrupt:
    print("\nTeste encerrado.")
except Exception as e:
    print(f"\n❌ Erro: {e}")
