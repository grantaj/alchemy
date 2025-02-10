import requests
import json
import os
from pydub import AudioSegment

# Configuration
WHISPER_API_URL = "http://localhost:8080"  # Adjust as needed
OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Adjust as needed
OLLAMA_MODEL = "llama3"  # Ensure this model is available

# Function to convert audio to WAV (whisper.cpp prefers WAV files)
def convert_audio_to_wav(input_audio_path, output_wav_path):
    audio = AudioSegment.from_file(input_audio_path)
    audio.export(output_wav_path, format="wav")
    return output_wav_path

# Function to transcribe audio using whisper.cpp
def transcribe_audio(audio_path):
    files = {'audio': open(audio_path, 'rb')}
    response = requests.post(f"{WHISPER_API_URL}/transcribe", files=files)
    if response.status_code == 200:
        return response.json().get("text", "")
    else:
        raise Exception(f"Whisper API error: {response.text}")

# Function to process text with Ollama
def reprocess_text_with_ollama(text, guiding_prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{guiding_prompt}\n\n{text}",
        "stream": False  # Set to True for streaming responses
    }
    response = requests.post(OLLAMA_API_URL, json=payload)
    if response.status_code == 200:
        return response.json().get("response", "")
    else:
        raise Exception(f"Ollama API error: {response.text}")

# Main function
def process_audio(input_audio_path, guiding_prompt):
    wav_path = "temp.wav"
    convert_audio_to_wav(input_audio_path, wav_path)

    print("Transcribing audio...")
    transcription = transcribe_audio(wav_path)
    print("Transcription:", transcription)

    print("Reprocessing text with Ollama...")
    reprocessed_text = reprocess_text_with_ollama(transcription, guiding_prompt)
    print("Reprocessed Text:", reprocessed_text)

    # Cleanup temporary files
    os.remove(wav_path)
    return reprocessed_text

# Example usage
if __name__ == "__main__":
    input_audio = "input.mp3"  # Change this to your audio file path
    guiding_prompt = "Please clean up and summarize the following transcript in a formal tone."
    output_text = process_audio(input_audio, guiding_prompt)
    print("\nFinal Output:\n", output_text)
