import requests
import json
import os
import base64
import uuid
import re
import threading
import queue
import wave
import pyaudio
from pydub import AudioSegment
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO

# Configuration
WHISPER_API_URL = "http://localhost:8080/inference"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
STABLE_DIFFUSION_URL = "http://localhost:7860/sdapi/v1/txt2img"
CHUNK_DURATION = 5  # seconds

# Queue for processing pipeline
audio_queue = queue.Queue()
processing_queue = queue.Queue()
image_display_queue = queue.Queue()


def record_audio():
    """Records audio from the microphone in chunks and places it in the processing queue."""
    p = pyaudio.PyAudio()
    format = pyaudio.paInt16
    channels = 1
    rate = 16000
    chunk_size = 1024
    
    stream = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk_size)
    
    print("Recording started...")
    while True:
        frames = []
        for _ in range(0, int(rate / chunk_size * CHUNK_DURATION)):
            data = stream.read(chunk_size)
            frames.append(data)
        
        filename = f"chunk_{uuid.uuid4().hex}.wav"
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(format))
            wf.setframerate(rate)
            wf.writeframes(b"".join(frames))
        
        audio_queue.put(filename)  # Send to processing queue
    
    stream.stop_stream()
    stream.close()
    p.terminate()


def transcribe_audio(audio_path):
    """Sends audio to Whisper for transcription."""
    with open(audio_path, "rb") as f:
        response = requests.post(
            WHISPER_API_URL,
            files={"file": f},
            data={"temperature": "0.0", "temperature_inc": "0.2", "response_format": "json"},
        )
    
    if response.status_code == 200:
        response_json = response.json()
        return response_json.get("text", "").strip()
    else:
        raise Exception(f"Whisper API error: {response.text}")


def reprocess_text_with_ollama(text, guiding_prompt):
    """Sends text to Ollama for reprocessing."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{guiding_prompt}\n\n{text}",
        "stream": False
    }
    response = requests.post(OLLAMA_API_URL, json=payload)
    if response.status_code == 200:
        return response.json().get("response", "").strip()
    else:
        raise Exception(f"Ollama API error: {response.text}")


def generate_sd_image(prompt, output_folder="generated_images"):
    """Sends a text prompt to Stable Diffusion, saves the generated image, and displays it."""
    os.makedirs(output_folder, exist_ok=True)
    payload = {
        "prompt": prompt,
        "steps": 10,
        "cfg_scale": 7.5,
        "width": 512,
        "height": 512,
        "sampler_index": "Euler a"
    }
    response = requests.post(STABLE_DIFFUSION_URL, json=payload)
    if response.status_code == 200:
        result = response.json()
        images = result.get("images", [])
        if images:
            img_data = images[0]
            img_bytes = base64.b64decode(img_data)
            image = Image.open(BytesIO(img_bytes))
            filename = f"{uuid.uuid4().hex}.png"
            img_path = os.path.join(output_folder, filename)
            image.save(img_path)
            print(f"Saved image: {img_path}")
            print("enqueueing image for display")
            image_display_queue.put(image)
            
    else:
        raise Exception(f"Stable Diffusion API error: {response.text}")

        
def process_audio():
    """Processes recorded audio through transcription, text processing, and image generation."""
    guiding_prompt = "Generate a poetic response suitable for image generation. Just give the text all on one line by itself, do not give explanation or any further questions."
    image_prompt = "illustration inked outline translucent washes"
    
    while True:
        audio_path = audio_queue.get()
        try:
            transcription = transcribe_audio(audio_path)
            print("Transcription:", transcription)
            
            response = reprocess_text_with_ollama(transcription, guiding_prompt)
            #response = json.loads(reprocessed_text)
            print(response)
            generate_sd_image(f"{image_prompt} {response}")
            # sd_prompts = response.get("sd-prompt", [])
            
            #for prompt in sd_prompts:
            #    generate_sd_image(f"{image_prompt} {prompt}")
        
        except Exception as e:
            print(f"Error processing audio chunk: {e}")
        finally:
            os.remove(audio_path)


if __name__ == "__main__":
    recording_thread = threading.Thread(target=record_audio, daemon=True)
    processing_thread = threading.Thread(target=process_audio, daemon=True)
    
    recording_thread.start()
    processing_thread.start()

    plt.ion()  # Turn on interactive mode for non-blocking updates
    fig, ax = plt.subplots()  # Create figure and axis once

    
    while True:
        print("Waiting for images")
        image = image_display_queue.get()
        print("Displaying image")
        ax.clear()  # Clear the previous image
        ax.imshow(image)
        ax.axis("off")
        plt.draw()  # Update the figure
        plt.pause(0.1)  # Allow UI to update
