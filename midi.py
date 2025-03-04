import mido
import threading
import queue

PORT_NAME = "Launch Control XL"

# Create a queue to store MIDI messages
midi_queue = queue.Queue()



def midi_listener(port_name):
    """Function to run in a separate thread, listening for MIDI messages."""
    with mido.open_input(port_name) as inport:
        print(f"Listening for MIDI messages on {port_name}...")
        for msg in inport:
            midi_queue.put(msg)  # Put MIDI message into the queue

# Get available MIDI input ports
midi_ports = mido.get_input_names()
print("Available MIDI input ports:", midi_ports)

# Check if the desired port exists
if PORT_NAME in midi_ports:
    midi_port = PORT_NAME
else:
    raise RuntimeError(f"Could not find MIDI port '{PORT_NAME}'. Available ports: {midi_ports}")

# Start MIDI listener thread
midi_thread = threading.Thread(target=midi_listener, args=(midi_port,), daemon=True)
midi_thread.start()

# Main application loop
while True:
    try:
        msg = midi_queue.get(timeout=0.1)  # Get message from queue (non-blocking)
        print(f"Received: {msg}")
    except queue.Empty:
        pass  # No message, continue main loop

