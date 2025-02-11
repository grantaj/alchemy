import requests
import json
import os
from pydub import AudioSegment

# Configuration
WHISPER_API_URL = "http://localhost:8080/inference"  # Updated for correct endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"  # Change based on available models

# Function to convert audio to WAV (Whisper.cpp prefers WAV)
def convert_audio_to_wav(input_audio_path, output_wav_path):
    audio = AudioSegment.from_file(input_audio_path)
    audio.export(output_wav_path, format="wav")
    return output_wav_path

# Function to transcribe audio using Whisper.cpp
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        response = requests.post(
            WHISPER_API_URL,
            files={"file": f},  # Corrected field name
            data={"temperature": "0.0", "temperature_inc": "0.2", "response_format": "json"},
        )

    print("Whisper API Response:", response.status_code)  # Print status code

    if response.status_code == 200:
        response_json = response.json()
        #print("Full Whisper API Response:", json.dumps(response_json, indent=2))  # Print full JSON response
        return response_json.get("text", "").strip()  # Extract transcription
    else:
        raise Exception(f"Whisper API error: {response.text}")


# Function to process text with Ollama
def reprocess_text_with_ollama(text, guiding_prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{guiding_prompt}\n\n{text}",
        "stream": False  # Set to True for streaming responses
    }

    #print(f"llama prompt: {guiding_prompt}\n\n{text}")
    
    response = requests.post(OLLAMA_API_URL, json=payload)

    if response.status_code == 200:
        return response.json().get("response", "").strip()
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
    #print("Reprocessed Text:", reprocessed_text)

    # Cleanup temporary file
    os.remove(wav_path)
    return reprocessed_text

# Example usage
if __name__ == "__main__":
    input_audio = "o3mini-summer.wav"  # Change this to your audio file path
    guiding_prompt = """Give me a stream of conciousness response to this poem. It should not be literal. You can be creative. Don't use cliches or overused metaphor. Your response should be rich in imagery, but poetic in its own right. The final output should be a series of text prompts suitable for input into stable diffusion for generation of a sequence of images that accompany the poem. The goal ios not to illustrate the poem, rather create an evocative, immersive and compelling environment for the viewer to inhabit while they contemplate the poem. Do not give explanation or any further questions. Just give the stream of consciousness and the stable diffusion prompts. Give your output as a valid, structured JSON file with one field "response" for the stream of conciousness and another field "sd-prompt" which is an array of strings containing the stable diffusion prompts."""
    
    output_text = process_audio(input_audio, guiding_prompt)
    
    print("\nFinal Output:\n", output_text)
