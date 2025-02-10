import os
import cv2
import requests
import json
import base64
from PIL import Image
from io import BytesIO

# CONFIGURATION
input_video = "input.mp4"
output_video = "output.mp4"
frames_dir = "frames"
processed_dir = "processed_frames"
sd_webui_url = "http://127.0.0.1:7860"  # Update if your A1111 server runs on a different port
prompt = "A surreal painting of the scene, vibrant colors, dreamlike"  # Modify as needed
strength = 0.7  # How much modification from the input (0 = no change, 1 = completely different)
steps = 50  # Sampling steps
model = "stable-diffusion-v1-5"  # Change if using another model

# Ensure directories exist
os.makedirs(frames_dir, exist_ok=True)
os.makedirs(processed_dir, exist_ok=True)

# Extract frames from video
def extract_frames(video_path, output_folder):
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_path = os.path.join(output_folder, f"frame_{frame_count:05d}.png")
        cv2.imwrite(frame_path, frame)
        frame_count += 1
    cap.release()
    print(f"Extracted {frame_count} frames.")

# Convert an image to base64 for API request
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Send request to Stable Diffusion WebUI
def process_frame(image_path, prompt, strength, steps):
    image_base64 = encode_image(image_path)
    payload = {
        "init_images": [image_base64],
        "prompt": prompt,
        "denoising_strength": strength,
        "steps": steps,
        "sampler_index": "Euler a",
        "cfg_scale": 7,
    }
    response = requests.post(f"{sd_webui_url}/sdapi/v1/img2img", json=payload)
    if response.status_code == 200:
        response_data = response.json()
        image_data = response_data["images"][0]
        image = Image.open(BytesIO(base64.b64decode(image_data)))
        return image
    else:
        print(f"Error processing frame: {response.text}")
        return None

# Process all frames with Stable Diffusion
def process_frames():
    frame_files = sorted(os.listdir(frames_dir))
    for frame_file in frame_files:
        frame_path = os.path.join(frames_dir, frame_file)
        processed_image = process_frame(frame_path, prompt, strength, steps)
        if processed_image:
            processed_image.save(os.path.join(processed_dir, frame_file))
    print("Processing complete.")

# Reassemble frames into a video
def create_video(output_video, frame_rate=30):
    os.system(f'ffmpeg -framerate {frame_rate} -i {processed_dir}/frame_%05d.png -c:v libx264 -pix_fmt yuv420p {output_video}')
    print(f"Output video saved as {output_video}")

# Run the pipeline
extract_frames(input_video, frames_dir)
process_frames()
create_video(output_video)
