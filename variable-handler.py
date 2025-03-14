import threading
import queue
import time

class VariableHandler:
    def __init__(self):
        self.registry = {}  # Stores variable references
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.running = True
        self.handler_thread = threading.Thread(target=self._handler_loop, daemon=True)
        self.handler_thread.start()

    def register(self, identifier, variable_ref):
        """Register a variable with an identifier."""
        with self.lock:
            self.registry[identifier] = variable_ref

    def update_variable(self, identifier, value):
        """Send an update request to the queue."""
        self.queue.put((identifier, value))

    def _handler_loop(self):
        """Handler thread that processes the queue."""
        while self.running:
            try:
                identifier, value = self.queue.get(timeout=1)
                with self.lock:
                    if identifier in self.registry:
                        self.registry[identifier][0] = value  # Update reference
            except queue.Empty:
                continue

    def stop(self):
        """Stop the handler thread."""
        self.running = False
        self.handler_thread.join()


# Example Usage
if __name__ == "__main__":
    handler = VariableHandler()

    # Example variables
    my_var_1 = [0]  # Using a mutable type (list) for reference
    my_var_2 = ["default"]

    print("Initial speed:", my_var_1[0])
    print("Initial mode:", my_var_2[0])

    # Register variables
    handler.register("speed", my_var_1)
    handler.register("mode", my_var_2)

    
    modes = ["slow", "medium", "fast", "super", "duper"]
    for speed in range(0,len(modes)):
        
        # Simulate external updates
        handler.update_variable("speed", speed)
        handler.update_variable("mode", modes[speed])
        time.sleep(0.5)
        print(f"\rSpeed: {my_var_1[0]:3d}, Mode: {my_var_2[0]:7}", end="", flush="True")


    print()
    handler.stop()
