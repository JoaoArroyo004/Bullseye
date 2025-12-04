import threading

from system_state import SystemState

system_state = SystemState()
data_lock = threading.Lock() # Lock/Unlock (Semaphore)