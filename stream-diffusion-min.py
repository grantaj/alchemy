# python 3.10 - version limited by spout and streamdiffusion

# ---- REQUIRED ----
# 1. DEPENDENCIES
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126 
# pip install streamdiffusion
# pip install opencv-python

# 2. SPOUT https://github.com/Off-World-Live/pyspout
# copy PySpout.pyd
# copy Spout.dll
# pip install PyOpenGL

# ---- OPTIONAL ----
# 3. FIX WARNING - UPGRADE DIFFUSERS
# pip install diffusers --upgrade
# pip install peft

# 4. XFORMERS
# pip install -U xformers --index-url https://download.pytorch.org/whl/cu126

import torch
from utils.wrapper import StreamDiffusionWrapper
import cv2
from PySpout import SpoutSender
import PIL.Image
from OpenGL.GL import GL_RGB

# import PIL.Image
# from streamdiffusion.image_utils import pil2tensor, postprocess_image

width = 512
height = 512

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
cap.set(cv2.CAP_PROP_FPS, 8)
cv2.CAP_PROP_BUFFERSIZE = 1

sender = SpoutSender("StreamDiffusion", width, height, GL_RGB)

sdw = StreamDiffusionWrapper(
    model_id_or_path="KBlueLeaf/kohaku-v2.1",
    t_index_list=[32, 45],
    frame_buffer_size=1,
    width=width,
    height=height,
    acceleration=None,
    do_add_noise=False,
    enable_similar_image_filter=True,
    similar_image_filter_threshold=0.99,
    similar_image_filter_max_skip_frame=10,
    mode="img2img",
    use_denoising_batch=True,
    cfg_type= "self",
    seed=2
)

sdw.prepare(
    prompt="skeleton warrior in a empty wasteland",
    guidance_scale=1.0,
    delta=0.5,
)

while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(0.01)  # Prevent CPU overuse
        continue

    # OLD METHOD - uses pillow, pil2tensor, torch.cat, postprocess_image
    # img = PIL.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    # input_frame = pil2tensor(img)
    # input_batch = torch.cat([input_frame])
    # output_images = sdw.stream(input_batch.to(device="cuda", dtype=torch.float16)).cpu()
    # output_image = postprocess_image(output_images, output_type="pil")[0]
    # sender.send_image(output_image, False)
    
    # NEW METHOD
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Convert to PyTorch tensor and normalize to [0,1]
    tensor = torch.from_numpy(frame).permute(2, 0, 1).float() / 255  

    # Add batch dimension (1, C, H, W) and move to GPU as float16
    input_batch = tensor.unsqueeze(0).to(device="cuda", dtype=torch.float16)    

    # Stream through model (stays on GPU)
    output_images = sdw.stream(input_batch)
    
    # Convert output tensor to PIL Image
    output_tensor = output_images[0].clamp(0, 1)
    output_tensor = (output_tensor * 255).byte().cpu()  # Convert to uint8 on CPU
    output_array = output_tensor.permute(1, 2, 0).numpy()  # Convert CHW → HWC
    output_image = PIL.Image.fromarray(output_array)
    
    sender.send_image(output_image, False)