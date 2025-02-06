import sounddevice as sd
import numpy as np
import queue
import whisper
import soundfile as sf
import tempfile
import os
import warnings

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

# Load Whisper model
model = whisper.load_model("base", device="cpu")

# Audio parameters
SAMPLE_RATE = 16000  # Match Whisper's preferred input rate
BUFFER_DURATION = 2  # Buffer at least 2 seconds before transcription

# Queue for audio buffering
audio_queue = queue.Queue()
chunk_buffer = []  # Buffer to accumulate audio

def audio_callback(indata, frames, time, status):
    """Accumulate multiple chunks before transcription."""
    global chunk_buffer
    if status:
        print(status)
    chunk_buffer.append(indata.copy())
    
    # Ensure we have enough audio before processing
    if len(chunk_buffer) >= int(BUFFER_DURATION * SAMPLE_RATE / frames):
        full_chunk = np.concatenate(chunk_buffer, axis=0)
        chunk_buffer = []
        audio_queue.put(full_chunk)  # Send a longer chunk for transcription

def transcribe_audio():
    """Continuously transcribe audio chunks from the queue."""
    while True:
        audio_chunk = audio_queue.get()
        if audio_chunk is None:
            break  # Stop when None is received
        
        if len(audio_chunk) == 0:
            continue
        
        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_audio:
            sf.write(temp_audio.name, audio_chunk, SAMPLE_RATE)
            result = model.transcribe(temp_audio.name, language="en")
            print(result["text"])

# Set up input stream
stream = sd.InputStream(
    samplerate=SAMPLE_RATE, 
    channels=1, 
    dtype="float32", 
    callback=audio_callback
)

print("Audio streaming and transcription started. Press Ctrl+C to stop.")
try:
    stream.start()
    transcribe_audio()
except KeyboardInterrupt:
    print("\nStopping audio stream...")
    stream.stop()
    audio_queue.put(None)
