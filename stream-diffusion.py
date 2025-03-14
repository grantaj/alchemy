# StreamDiffusion/examples/screen with cv2 input
import os
import sys
import time
import threading
from multiprocessing import Process, Queue, get_context
from multiprocessing.connection import Connection
from typing import List, Literal, Dict, Optional
import torch
import PIL.Image
from streamdiffusion.image_utils import pil2tensor
import cv2
import fire

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.viewer import receive_images
from utils.wrapper import StreamDiffusionWrapper

inputs = []

def webcam_capture(event, height, width):
    global inputs
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    while True:
        if event.is_set():
            break
        ret, frame = cap.read()
        if not ret:
            continue
        img = PIL.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        inputs.append(pil2tensor(img))
    cap.release()

def image_generation_process(
    queue: Queue,
    fps_queue: Queue,
    close_queue: Queue,
    model_id_or_path: str,
    lora_dict: Optional[Dict[str, float]],
    prompt: str,
    negative_prompt: str,
    frame_buffer_size: int,
    width: int,
    height: int,
    acceleration: Literal["none", "xformers", "tensorrt"],
    use_denoising_batch: bool,
    seed: int,
    cfg_type: Literal["none", "full", "self", "initialize"],
    guidance_scale: float,
    delta: float,
    do_add_noise: bool,
    enable_similar_image_filter: bool,
    similar_image_filter_threshold: float,
    similar_image_filter_max_skip_frame: float,
):
    global inputs
    stream = StreamDiffusionWrapper(
        model_id_or_path=model_id_or_path,
        lora_dict=lora_dict,
        t_index_list=[32, 45],
        frame_buffer_size=frame_buffer_size,
        width=width,
        height=height,
        warmup=10,
        acceleration=acceleration,
        do_add_noise=do_add_noise,
        enable_similar_image_filter=enable_similar_image_filter,
        similar_image_filter_threshold=similar_image_filter_threshold,
        similar_image_filter_max_skip_frame=similar_image_filter_max_skip_frame,
        mode="img2img",
        use_denoising_batch=use_denoising_batch,
        cfg_type=cfg_type,
        seed=seed,
    )
    stream.prepare(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=50,
        guidance_scale=guidance_scale,
        delta=delta,
    )
    event = threading.Event()
    capture_thread = threading.Thread(target=webcam_capture, args=(event, height, width))
    capture_thread.start()
    time.sleep(5)
    while True:
        try:
            if not close_queue.empty():
                break
            if len(inputs) < frame_buffer_size:
                time.sleep(0.005)
                continue
            start_time = time.time()
            sampled_inputs = []
            for i in range(frame_buffer_size):
                index = (len(inputs) // frame_buffer_size) * i
                sampled_inputs.append(inputs[len(inputs) - index - 1])
            input_batch = torch.cat(sampled_inputs)
            inputs.clear()
            output_images = stream.stream(
                input_batch.to(device=stream.device, dtype=stream.dtype)
            ).cpu()
            if frame_buffer_size == 1:
                output_images = [output_images]
            for output_image in output_images:
                queue.put(output_image, block=False)
            fps = 1 / (time.time() - start_time)
            fps_queue.put(fps)
        except KeyboardInterrupt:
            break
    print("closing image_generation_process...")
    event.set()
    capture_thread.join()
    print(f"fps: {fps}")

def main(
    model_id_or_path: str = "KBlueLeaf/kohaku-v2.1",
    lora_dict: Optional[Dict[str, float]] = None,
    prompt: str = "skeleton warrior in a empty wasteland",
    negative_prompt: str = "anime, cartoon",
    frame_buffer_size: int = 1,
    width: int = 512,
    height: int = 512,
    acceleration: Literal["none", "xformers", "tensorrt"] = "xformers",
    use_denoising_batch: bool = True,
    seed: int = 2,
    cfg_type: Literal["none", "full", "self", "initialize"] = "self",
    guidance_scale: float = 1.4,
    delta: float = 0.5,
    do_add_noise: bool = False,
    enable_similar_image_filter: bool = True,
    similar_image_filter_threshold: float = 0.99,
    similar_image_filter_max_skip_frame: float = 10,
):
    ctx = get_context('spawn')
    queue = ctx.Queue()
    fps_queue = ctx.Queue()
    close_queue = Queue()
    process1 = ctx.Process(
        target=image_generation_process,
        args=(
            queue,
            fps_queue,
            close_queue,
            model_id_or_path,
            lora_dict,
            prompt,
            negative_prompt,
            frame_buffer_size,
            width,
            height,
            acceleration,
            use_denoising_batch,
            seed,
            cfg_type,
            guidance_scale,
            delta,
            do_add_noise,
            enable_similar_image_filter,
            similar_image_filter_threshold,
            similar_image_filter_max_skip_frame,
        ),
    )
    process1.start()
    process2 = ctx.Process(target=receive_images, args=(queue, fps_queue))
    process2.start()
    process2.join()
    print("process2 terminated.")
    close_queue.put(True)
    print("process1 terminating...")
    process1.join(5)
    if process1.is_alive():
        print("process1 still alive. force killing...")
        process1.terminate()
    process1.join()
    print("process1 terminated.")

if __name__ == "__main__":
    fire.Fire(main)