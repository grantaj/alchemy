import threading
import queue
import time

class VariableHandler:
    """
    A threaded variable management system that allows external tasks to update 
    registered variables asynchronously via a queue.

    This class maintains a registry of variables identified by unique string 
    identifiers. Other tasks can send (identifier, value) pairs to a queue, 
    and a background handler thread updates the corresponding registered variables.

    Variable References:
    --------------------
    Since Python variables are immutable by default (e.g., integers, strings),
    mutable containers such as lists or dictionaries are used to store references.
    The registered variable must be a mutable container (e.g., `[value]` for a single
    value) so that updates modify the contained value rather than reassigning a local
    variable.

    Example Usage:
    --------------
    ```python
    handler = VariableHandler()

    my_var = [0]  # Using a list to hold a mutable reference
    handler.register("speed", my_var)

    handler.update_variable("speed", 42)  # Update via the handler
    time.sleep(0.5)  # Allow handler to process the update

    print(my_var[0])  # Output: 42
    handler.stop()
    ```
    
    Methods:
    --------
    - `register(identifier: str, variable_ref: list)`: Registers a variable reference.
    - `update_variable(identifier: str, value)`: Sends an update request to the queue.
    - `stop()`: Stops the handler thread safely.

    Thread Safety:
    --------------
    A threading lock (`self.lock`) ensures safe access to the registry across multiple threads.
    """
    
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
