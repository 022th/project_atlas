"""Script de teste interativo para verificar gravação F8 e transcrição com callback."""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import time
import math
import numpy as np
import sounddevice as sd
import keyboard
from scipy.signal import resample_poly
from faster_whisper import WhisperModel

print("=== TESTE DE GRAVAÇÃO COM CALLBACK ===")

device_info = sd.query_devices(kind="input")
native_sr = int(device_info["default_samplerate"])
print(f"🎤 Microfone padrão: {device_info['name']} ({native_sr}Hz)")

print("⏳ Carregando Whisper 'small'...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("✅ Whisper carregado!")

print("\n--------------------------------------------------")
print("👉 Segure F8 para falar, solte para transcrever!")
print("   Pressione ESC para encerrar o teste.")
print("--------------------------------------------------\n")

buffer = []
is_recording = False

def callback(indata, frames, time_info, status):
    if is_recording:
        buffer.append(indata.copy())

while True:
    if keyboard.is_pressed("esc"):
        print("\nSaindo...")
        break

    if keyboard.is_pressed("f8"):
        print("🔴 Gravando... FALE AGORA!")
        buffer = []
        with sd.InputStream(device=None, samplerate=native_sr, channels=1, dtype="float32", callback=callback):
            is_recording = True
            while keyboard.is_pressed("f8"):
                time.sleep(0.02)
            is_recording = False

        if buffer:
            audio = np.concatenate(buffer, axis=0).flatten().astype(np.float32)
            dur = len(audio) / native_sr
            max_vol = np.max(np.abs(audio))
            rms_vol = np.sqrt(np.mean(audio ** 2))

            print(f"   ⏱️ Duração: {dur:.1f}s | Volume máx: {max_vol:.4f} | RMS: {rms_vol:.6f}")

            if max_vol < 0.001:
                print("   ❌ Áudio zerado! O microfone não entregou som.\n")
                continue

            gcd = math.gcd(native_sr, 16000)
            up = 16000 // gcd
            down = native_sr // gcd
            audio_16k = resample_poly(audio, up, down).astype(np.float32)
            audio_norm = audio_16k / max_vol * 0.90

            print("   ⏳ Transcrevendo...")
            segments, info = model.transcribe(audio_norm, language="pt", beam_size=5, vad_filter=False)
            text = " ".join(s.text for s in segments).strip()

            if text:
                print(f"   🎉 Transcrição: \"{text}\"\n")
            else:
                print("   ❌ Whisper retornou vazio.\n")
        else:
            print("   ❌ Nenhum áudio capturado.\n")

        time.sleep(0.5)

    time.sleep(0.05)
