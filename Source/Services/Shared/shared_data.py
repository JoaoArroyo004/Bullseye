import threading

shared_data = {
    "operation_mode": 0,  # [sleep, multiple, single]
    "target_count": 0,
    "identifiable_targets": ["Aa", "Bb", "Arnaldo", "Beraldo", "Cernaldo"],
    "current_targets": ["Aa", "Bb"],
    "target_x": None
}

data_lock = threading.Lock()
