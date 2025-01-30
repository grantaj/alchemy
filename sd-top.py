# me - this DAT
# scriptOp - the OP which is cooking
import requests
import json
import base64
import numpy as np
import cv2
import numpy

# Stable Diffusion API URL (local A1111 instance)
SD_API_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"
SCRIPT_TOP = "script2"

# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def onSetupParameters(scriptOp):
	page = scriptOp.appendCustomPage('Alchemy')
	page.appendPulse('Generate')
	page.appendStr('Prompt')
	return


# called whenever custom pulse parameter is pushed
def onPulse(par):
	prompt = op(SCRIPT_TOP).par.Prompt
	print(f'prompt: "{prompt}"')
	print(f'sent to: {SD_API_URL}')
	send_prompt(prompt.val)
	return


def onCook(scriptOp):
	image = me.fetch("image_data", None)
	if image is not None:
		scriptOp.copyNumpyArray(image)
	return


def send_prompt(prompt):
	"""Send text prompt to Stable Diffusion and update the TOP output."""
	payload = {
		"prompt": prompt,
		"steps": 30,
		"width": 512,
		"height": 512,
		"cfg_scale": 7,
		"sampler_name": "Euler a",
	}

	try:
		response = requests.post(SD_API_URL, json=payload, timeout=5)
	except:
		print("Error: No response from the server.")
		return

	if response.status_code == 200:
		result = response.json()
		image_data = result["images"][0]  # Base64 encoded image
		image = convert_base64_to_nparray(image_data)
		me.store("image_data", image)
	else:
		print(f"Error: {response.status_code} - {response.text}")
	

def convert_base64_to_nparray(image_data):
	"""Update the Script TOP with the generated image"""
	# Decode Base64 image to bytes
	image_bytes = base64.b64decode(image_data)

	# Convert bytes to a NumPy array
	np_arr = np.frombuffer(image_bytes, dtype=np.uint8)

	# Decode image into OpenCV format (BGR)
	image = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)

	# Convert BGR to RGB if necessary
	if image.shape[-1] == 3:
		image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
	return image
