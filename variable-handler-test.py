from variable_handler import VariableHandler
import time

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
