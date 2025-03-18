import mido
import threading
import queue
import json
import os
from variable_handler import VariableHandler

PORT_NAME = "Launch Control XL"

# Queue for MIDI messages
midi_queue = queue.Queue()

# Dictionary to store mappings
midi_mappings = {}

# JSON file for saving/loading mappings
MAPPING_FILE = "midi_mappings.json"

# Load existing mappings if available
def load_mappings():
    global midi_mappings
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r") as file:
            midi_mappings = json.load(file)
        print(f"Loaded {len(midi_mappings)} mappings from {MAPPING_FILE}")
    else:
        print("No existing mappings found.")

# Save mappings to a JSON file
def save_mappings():
    with open(MAPPING_FILE, "w") as file:
        json.dump(midi_mappings, file, indent=4)
    print(f"Saved mappings to {MAPPING_FILE}")

# MIDI listener function
def midi_listener(port_name):
    """Runs in a separate thread, listening for MIDI messages."""
    with mido.open_input(port_name) as inport:
        print(f"Listening for MIDI messages on {port_name}...")
        for msg in inport:
            midi_queue.put(msg)  # Put the received MIDI message in the queue

def flush_midi_queue():
    """Remove all queued MIDI messages to prevent stale input."""
    while not midi_queue.empty():
        try:
            midi_queue.get_nowait()  # Non-blocking get
        except queue.Empty:
            break  # Exit if queue is already empty

# Start MIDI listening thread
def start_midi_thread(midi_port):
    thread = threading.Thread(target=midi_listener, args=(midi_port,), daemon=True)
    thread.start()

# Enter Learn Mode
def learn_mode():
    flush_midi_queue()
    
    print("\n--- Learn Mode Activated ---")
    print("Send a MIDI message (press a key, turn a knob, etc.)...")
    
    while True:
        try:
            msg = midi_queue.get(timeout=10)  # Wait for MIDI message
            #msg_key = (msg.type, msg.note if msg.type in ['note_on', 'note_off'] else msg.control)
            msg_key = f"{msg.type}_{msg.note if msg.type in ['note_on', 'note_off'] else msg.control}"
            print(f"\nMIDI message received: {msg}")

            # Prompt user for function name
            function_name = input(f"Enter function name for {msg_key}: ").strip()
            if function_name:
                midi_mappings[msg_key] = function_name
                print(f"Assigned {msg_key} -> {function_name}")
            else:
                print("No function assigned, ignoring this mapping.")

            break  # Exit learn mode after receiving a message
        except queue.Empty:
            print("Learn mode timed out. No MIDI message received.")
            break  # Exit learn mode

# Perform Mode
def perform_mode(handler):
    print("\n--- Perform Mode Activated ---")
    print("Listening for incoming MIDI messages... (Press Enter to exit)")
    
    stop_flag = threading.Event()
    def listen_for_exit():
        input()  # Wait for user to press Enter
        stop_flag.set()
    
    exit_thread = threading.Thread(target=listen_for_exit, daemon=True)
    exit_thread.start()
    
    while not stop_flag.is_set():
        try:
            msg = midi_queue.get(timeout=1)  # Check for messages every second
            msg_key = f"{msg.type}_{msg.note if msg.type in ['note_on', 'note_off'] else msg.control}"
            
            if msg_key in midi_mappings:
                handler.update_variable(midi_mappings[msg_key], msg.value)
                #print(f"Function: {midi_mappings[msg_key]}, Value: {msg.value}")
            else:
                print(f"Unmapped MIDI message: {msg}")
        except queue.Empty:
            pass  # No messages, just continue checking
    
    print("Exiting Perform Mode...")
            
# Main menu
def main_menu():
    handler = VariableHandler()
    fader_0 = [0]
    fader_1 = [0]
    knob_0 = [0]

    handler.register("fader_0", fader_0)
    handler.register("fader_1", fader_1)
    handler.register("knob_0", knob_0)
    
    while True:
        print("\n--- MIDI Learn Mode CLI ---")
        print("1. Enter Learn Mode")
        print("2. Show Mappings")
        print("3. Save Mappings")
        print("4. Load Mappings")
        print("5. Perform")
        print("6. Exit")


        choice = input("Choose an option: ").strip()
        
        if choice == "1":
            learn_mode()
        elif choice == "2":
            print("\nCurrent MIDI Mappings:")
            for key, value in midi_mappings.items():
                print(f"{key} -> {value}")
        elif choice == "3":
            save_mappings()
        elif choice == "4":
            load_mappings()
        elif choice == "5":
            perform_mode(handler)
            print(f"fader_0 {fader_0}")
            print(f"fader_1 {fader_1}")
            print(f"knob_0 {knob_0}")
        elif choice == "q":
            print("Exiting...")
            break
        else:
            print("Invalid choice, try again.")

# Main execution
if __name__ == "__main__":
    # Detect available MIDI ports
    midi_ports = mido.get_input_names()
    print("Available MIDI input ports:", midi_ports)
    
    if not midi_ports:
        print("No MIDI input ports found!")
        exit(1)

    # Check if the desired port exists
    if PORT_NAME in midi_ports:
        selected_midi_port = PORT_NAME
    else:
        raise RuntimeError(f"Could not find MIDI port '{PORT_NAME}'. Available ports: {midi_ports}")

    print(f"Using MIDI port: {selected_midi_port}")

    # Load existing mappings
    load_mappings()

    # Start the MIDI listening thread
    start_midi_thread(selected_midi_port)

    # Start the CLI menu
    main_menu()
