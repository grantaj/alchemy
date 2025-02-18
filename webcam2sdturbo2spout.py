# Requirements that work on Fraz's machine

# 1. SD-turbo - https://huggingface.co/stabilityai/sd-turbo
# pip install diffusers transformers accelerate --upgrade

# 1.1 PyTorch might need to be reinstalled with appropriate cuda version - https://pytorch.org/
# pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# 2. pyspout - https://github.com/Off-World-Live/pyspout
# copy spout.dll and PySpout.pyd file into directory
# pip install pyopengl

# 3. Other - opencv & pillow
# pip install opencv-python pillow

import cv2
from diffusers import AutoPipelineForImage2Image
from diffusers.utils import load_image
import torch
from PIL import Image
from PySpout import SpoutSender
from OpenGL.GL import * 
import numpy as np

pipe = AutoPipelineForImage2Image.from_pretrained("stabilityai/sdxl-turbo", torch_dtype=torch.float16, variant="fp16")
pipe.to("cuda")

sender = SpoutSender("MyName", 640, 480, GL_RGB)

cap = cv2.VideoCapture(0)

def convert_cv2_to_pillow(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(image)
    return image

def convert_pillow_to_cv2(image):
    image = np.array(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    return image

def generate_image(image):
    image = load_image(image)
    image = pipe("frog people", image=image, num_inference_steps=2, strength=0.5, guidance_scale=0.0).images[0]
    return image

while True:
    ret, frame = cap.read()

    image = convert_cv2_to_pillow(frame)
    image = generate_image(image)
    image = convert_pillow_to_cv2(image)
    
    sender.send_image(image, False)