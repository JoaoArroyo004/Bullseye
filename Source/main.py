import threading
import time

from Source.Services.Server.server import server_handler

shared_data = {
    "operation_mode": 0, # [sleep, multiple, single]
    "target_count": 0,
    "identifiable_targets": ["Aa", "Bb", "Arnaldo", "Beraldo", "Cernaldo"],
    "current_targets": ["Aa", "Bb"]
}
data_lock = threading.Lock() # Lock/Unlock (Semaphore)

functions = [
    lambda: camera_handler(),
    lambda: servo_handler(),
    lambda: server_handler()
]

# Configure the thread behavior inside the functions which are inside the array on line 12
def camera_handler():
    while True:
        with data_lock:
            shared_data["counter"] += 1
            print(f"[camera_handler] Counter: {shared_data['counter']}")
        time.sleep(1)

def servo_handler():
    while True:
        with data_lock:
            shared_data["message"] = f"Message updated by servo_handler at {time.time()}"
            print(f"[servo_handler] {shared_data['message']}")
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
