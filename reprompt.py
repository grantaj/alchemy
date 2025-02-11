import requests
import json
import os
from pydub import AudioSegment
import base64
import uuid
import re

# Configuration
WHISPER_API_URL = "http://localhost:8080/inference"  # Updated for correct endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"  # Change based on available models
STABLE_DIFFUSION_URL = "http://localhost:7860/sdapi/v1/txt2img"  # Adjust if needed


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

import re

def strip_triple_backticks(text):
    """
    Removes triple backticks (``` ... ```), ensures the JSON output has
    opening `{` and closing `}` curly braces if they are missing.
    """
    # Remove triple backticks (handles both ```json and plain ```)
    cleaned_text = re.sub(r"```(?:json)?\s*([\s\S]+?)\s*```", r"\1", text).strip()
    
    # Ensure it starts with '{' and ends with '}' (valid JSON object)
    if not cleaned_text.startswith("{"):
        cleaned_text = "{" + cleaned_text
    if not cleaned_text.endswith("}"):
        cleaned_text = cleaned_text + "}"

    return cleaned_text


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


def generate_unique_filename():
    """Generates a unique filename using UUID."""
    unique_id = uuid.uuid4().hex  # Generate a unique ID
    return f"{unique_id}"

def generate_sd_image(prompt, output_folder="generated_images"):
    os.makedirs(output_folder, exist_ok=True)  # Ensure output folder exists

    payload = {
        "prompt": prompt,
        "steps": 10,  # Adjust as needed
        "cfg_scale": 7.5,  # Adjust as needed
        "width": 512,  # Adjust as needed
        "height": 512,  # Adjust as needed
        "sampler_index": "Euler a"
    }

    response = requests.post(STABLE_DIFFUSION_URL, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        images = result.get("images", [])
        if images:
            # Convert base64 image to file
            img_data = images[0]
            filename = generate_unique_filename()
            img_path = os.path.join(output_folder, f"{filename}.png")
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(img_data))
            print(f"Saved: {img_path}")
            return img_path
    else:
        raise Exception(f"Stable Diffusion API error: {response.text}")
    
# Main function
def process_audio(input_audio_path, guiding_prompt, image_prompt):
    wav_path = "temp.wav"
    convert_audio_to_wav(input_audio_path, wav_path)

    print("Transcribing audio...")
    transcription = transcribe_audio(wav_path)
    print("Transcription:", transcription)

    print("Reprocessing text with Ollama...")
    reprocessed_text = reprocess_text_with_ollama(transcription, guiding_prompt)
    print("Raw: ", reprocessed_text)
    reprocessed_text = strip_triple_backticks(reprocessed_text)
    print("Fixed: ", reprocessed_text)

    try:
        response = json.loads(reprocessed_text)
    except json.JSONDecodeError as e:
        raise Exception(f"Error decoding JSON: {e}\nResponse received: {reprocessed_text}")

    sd_prompt = response.get("sd-prompt", [])

    print(f"Generating {len(sd_prompt)} images with Stable Diffusion...")

    # Process each prompt with Stable Diffusion
    for prompt in sd_prompt:
        print(f"   - {prompt}")
        generate_sd_image(f"{image_prompt} {prompt}")

    # Cleanup temporary file
    os.remove(wav_path)
    return reprocessed_text


    
# Example usage
if __name__ == "__main__":
    input_audio = "o3mini-summer.wav"  # Change this to your audio file path
    guiding_prompt = """Give me a stream of conciousness response to this poem. It should not be literal. You can be creative. Don't use cliches or overused metaphor. Your response should be rich in imagery, but poetic in its own right. The final output should be a series of text prompts suitable for input into stable diffusion for generation of a sequence of images that accompany the poem. The goal ios not to illustrate the poem, rather create an evocative, immersive and compelling environment for the viewer to inhabit while they contemplate the poem. Do not give explanation or any further questions. Just give the stream of consciousness and the stable diffusion prompts. Give your output as a valid, raw JSON file with one field "response" for the stream of conciousness and another field "sd-prompt" which is an array of strings containing the stable diffusion prompts. Do not include triple backticks in your output. Your output is being fed directly into a JSON parser so needs to be raw and valid JSON."""

    image_prompt = "illustration gothic cyberpunk style simplified inked outlines translucent washes dripping"
    
    output_text = process_audio(input_audio, guiding_prompt, image_prompt)
    
    print("\nFinal Output:\n", output_text)
