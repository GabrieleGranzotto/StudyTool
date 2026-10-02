import pyaudio
import numpy as np
import whisper

print("1. Caricamento modello Whisper (se si blocca qui, è colpa di PyTorch)...")
modello = whisper.load_model("base")
print("✅ Modello caricato!")

print("\n2. Apertura microfono (se dà errore qui, sono i permessi di Windows o PyAudio)...")
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)

print("🎙️ PARLA ORA per 5 secondi (il microfono è chiuso, in registrazione)...")
frames = []
for _ in range(0, int(16000 / 1024 * 5)):
    data = stream.read(1024, exception_on_overflow=False)
    frames.append(data)

print("🛑 Registrazione terminata. Il microfono ora è chiuso (disattivato). Avvio trascrizione...")
stream.stop_stream()
stream.close()
p.terminate()

audio_data = b''.join(frames)
audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

print("⏳ Elaborazione della trascrizione in corso...")
risultato = modello.transcribe(audio_np, language="it", fp16=False)

print(f"\n✨ RISULTATO FINALE: {risultato['text']}")