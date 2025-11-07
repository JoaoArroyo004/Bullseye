from Source.Services.Server.server import server_handler
import os
import sys
import threading
import time

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

functions = [
    lambda: camera_handler(),
    lambda: servo_handler(),
    lambda: server_handler()
]

# Configure the thread behavior inside the functions which are inside the array on line 12
def camera_handler():
    while True:
        with data_lock:
            system_state["counter"] += 1
            print(f"[camera_handler] Counter: {system_state['counter']}")
        time.sleep(1)

def servo_handler():
    while True:
        with data_lock:
            system_state["message"] = f"Message updated by servo_handler at {time.time()}"
            print(f"[servo_handler] {system_state['message']}")
        time.sleep(2)

threads = []
for func in functions:
    t = threading.Thread(target=func, daemon=True)  # daemon=True: allows program to exit if main exits
    threads.append(t)
    t.start()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Exiting program...")
