import sounddevice as sd
import numpy as np
import soundfile as sf

SAMPLE_RATE = 16000  # Whisper requires 16kHz
DURATION = 5  # Record for 5 seconds

print("Recording... Speak now!")

audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
sd.wait()  # Wait for recording to finish

sf.write("test_audio.wav", audio, SAMPLE_RATE)

print("Recording complete. Check 'test_audio.wav' to verify.")
