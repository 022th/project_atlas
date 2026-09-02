"""Diagnóstico de áudio + Whisper. Grava 5s do microfone e tenta transcrever."""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import sounddevice as sd
import wave
import os

print("=== DIAGNÓSTICO DE ÁUDIO ===\n")

# 1. Lista dispositivos de áudio
print("📋 Dispositivos de entrada disponíveis:")
devices = sd.query_devices()
default_input = sd.default.device[0]
for i, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        marker = " ← DEFAULT" if i == default_input else ""
        print(f"  [{i}] {d['name']} (canais: {d['max_input_channels']}){marker}")

print(f"\n🎤 Gravando 5 segundos do microfone padrão [{default_input}]...")
print("   FALE ALGO AGORA!\n")

samplerate = 16000
duration = 5
audio = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=1, dtype="float32")
sd.wait()

audio = audio.flatten()

# 2. Analisa o áudio
volume_max = np.max(np.abs(audio))
volume_rms = np.sqrt(np.mean(audio ** 2))
print(f"📊 Volume máximo: {volume_max:.4f} (precisa ser > 0.01)")
print(f"📊 Volume RMS:    {volume_rms:.6f}")

if volume_max < 0.001:
    print("\n❌ PROBLEMA: Volume praticamente ZERO!")
    print("   → O microfone pode estar mutado ou errado.")
    print("   → Verifique nas Configurações do Windows > Som > Entrada")
elif volume_max < 0.01:
    print("\n⚠️  Volume MUITO baixo. Pode não transcrever bem.")
    print("   → Aumente o volume do microfone nas configurações do Windows.")
else:
    print("\n✅ Volume OK!")

# 3. Salva WAV para referência
wav_path = "test_audio.wav"
with wave.open(wav_path, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)  # 16-bit
    wf.setframerate(samplerate)
    wf.writeframes((audio * 32767).astype(np.int16).tobytes())
print(f"\n💾 Áudio salvo em: {os.path.abspath(wav_path)}")
print("   (Abra no Windows pra confirmar se tem som)")

# 4. Tenta transcrever
print("\n⏳ Transcrevendo com Whisper...")
try:
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    
    # Tenta sem filtro
    segments, info = model.transcribe(audio, language="pt", beam_size=5, vad_filter=False)
    text = " ".join(s.text for s in segments).strip()
    
    if text:
        print(f"✅ Transcrição: \"{text}\"")
    else:
        print("❌ Whisper retornou vazio.")
        print("   Tentando com arquivo WAV...")
        segments, info = model.transcribe(wav_path, language="pt", beam_size=5, vad_filter=False)
        text2 = " ".join(s.text for s in segments).strip()
        if text2:
            print(f"✅ Via WAV funcionou: \"{text2}\"")
            print("   → O problema é o formato do array. Vou ajustar o voice_input.py")
        else:
            print("❌ Via WAV também vazio. Volume muito baixo ou microfone errado.")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n=== FIM DO DIAGNÓSTICO ===")
