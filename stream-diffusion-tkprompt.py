# python 3.10
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126 
# pip install opencv-python
# pip install streamdiffusion
# pip install PyOpenGL
# copy PySpout.pyd
# copy Spout.dll

# pip install --upgrade diffusers

# general stucture taken from StreamDiffusion demo - realtime-img2img
# https://github.com/cumulo-autumn/StreamDiffusion/tree/main/demo/realtime-img2img

import torch
from utils.wrapper import StreamDiffusionWrapper
import cv2
import asyncio
from PySpout import SpoutSender
from OpenGL.GL import *
import PIL.Image
import threading
import queue
import tkinter as tk

WIDTH = 512
HEIGHT = 512

def create_stream():
    acceleration = ["none", "xformers", "sfast", "tensorrt"][0],
    mode = ["img2img", "txt2img"][0]
    default_prompt = "The Joker"
    default_negative_prompt = "blurry"

    stream = StreamDiffusionWrapper(
        model_id_or_path="stabilityai/sd-turbo",
        use_tiny_vae= True,
        device=torch.device("cuda"),
        dtype=torch.float16,
        t_index_list=[35, 45],
        frame_buffer_size=1,
        width=WIDTH,
        height=HEIGHT,
        use_lcm_lora=False,
        output_type="pil",
        warmup=10,
        vae_id=None,
        acceleration=acceleration,
        mode=mode,
        use_denoising_batch=True,
        cfg_type="self",
        # use_safety_checker=True, # turns too many frames black
        # do_add_noise=True,
        # enable_similar_image_filter=True,
        # similar_image_filter_threshold=0.98,
        # engine_dir="engines",
    )

    stream.prepare(
        prompt=default_prompt,
        negative_prompt=default_negative_prompt,
        num_inference_steps=50,
        guidance_scale=1.4,
        delta=0.0
    )
    return stream

async def update_data(queue, frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(frame).permute(2, 0, 1).float() / 255  
    input_batch = tensor.unsqueeze(0).to(device="cuda", dtype=torch.float16)
    await queue.put(input_batch)

async def get_latest_data(queue):
    try:
        return await queue.get()
    except asyncio.QueueEmpty:
        return None

def prompt_window(q:queue.Queue):
    def submit_text(event=None):
        text = input_field.get()
        result_label.config(text=f"You entered: {text}")
        q.put(text)
        if text == "end":
            window.destroy()

    window = tk.Tk()
    window.title("Prompt Input - Type 'end' to exit")

    input_field = tk.Entry(window, width=30)
    input_field.pack(padx=5, pady=5)
    input_field.bind("<Return>", submit_text)

    result_label = tk.Label(window, text="")
    result_label.pack(padx=5, pady=5)

    window.mainloop()

async def main():
    stream = create_stream()
    frame_queue = asyncio.Queue()
    prompt_queue = queue.Queue()
    t = threading.Thread(target=prompt_window, args=(prompt_queue,))    
    current_prompt = "Skeleton in desolate Landscape"

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    spout = SpoutSender("Stream", WIDTH, HEIGHT, GL_RGB)

    if not cap.isOpened():
        print("Error: Could not open video capture.")
        sys.exit(1)

    t.start()
    while True:
        ret, frame = cap.read()

        if not ret:
            await asyncio.sleep(0.01)  # prevent CPU overuse
            continue

        try:
            text = prompt_queue.get_nowait()
            print(text)
            if text == "end":
                break
            current_prompt = text
        except queue.Empty:
            pass

        await update_data(frame_queue, frame)
        frame_data = await get_latest_data(frame_queue)
        if frame_data is not None:
            image = stream(frame_data, current_prompt)
            spout.send_image(image, False)

if __name__ == "__main__":
    asyncio.run(main())