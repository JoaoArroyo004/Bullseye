import threading
import time

from Services.Server.server import server_handler
from Services.Camera.camera_handler import camera_handler
from Services.Servo.servo_handler import servo_handler
from Services.Shared.shared_data import shared_data, data_lock

functions = [
    lambda: camera_handler(shared_data, data_lock),
    lambda: servo_handler(shared_data, data_lock),
    lambda: server_handler()
]

threads = []
for func in functions:
    t = threading.Thread(target=func, daemon=True)
    threads.append(t)
    t.start()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Exiting program...")
