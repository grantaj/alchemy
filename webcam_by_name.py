import cv2
from pygrabber.dshow_graph import FilterGraph

# List available cameras
graph = FilterGraph()
devices = graph.get_input_devices()
print("Available devices:", devices)

# Select the camera by name (modify the name as needed)
desired_camera_name = "Logitech Brio"
device_index = None

for index, name in enumerate(devices):
    if desired_camera_name.lower() in name.lower():
        device_index = index
        break

if device_index is not None:
    print(f"Using device index: {device_index}")
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print("Failed to open the camera.")
    else:
        print("Camera opened successfully.")
else:
    print("Desired camera not found.")
