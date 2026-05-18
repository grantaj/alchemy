import sounddevice as sd
import numpy as np
import queue

# Audio parameters
SAMPLE_RATE = 16000  # Match Whisper's preferred input rate

# Queue for audio buffering
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """Capture audio and queue it for playback."""
    if status:
        print(status)
    
    # Ensure correct format and queue for playback
    audio_queue.put(indata.copy())

def playback_stream():
    """Continuously play back audio chunks from the queue."""
    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as out_stream:
        while True:
            audio_chunk = audio_queue.get()
            if audio_chunk is None:
                break  # Stop the loop when None is received
            out_stream.write(audio_chunk)

# Set up input stream
stream = sd.InputStream(
    samplerate=SAMPLE_RATE, 
    channels=1, 
    dtype="float32", 
    callback=audio_callback
)

print("Audio streaming started. Press Ctrl+C to stop.")
try:
    stream.start()
    playback_stream()
except KeyboardInterrupt:
    print("\nStopping audio stream...")
    stream.stop()
    audio_queue.put(None)

