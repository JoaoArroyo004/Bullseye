import threading

shared_data = {
    "operation_mode": 'sleep',  # [sleep, multiple, single]
    "target_count": 0,    
    "current_targets": ["Aa", "Bb", "Gavril"],
    "amount_photos": {"Aa": 0, "Bb": 0, "Gavril": 0},
    "main_target": "Gavril",
    "target_x": None
}

data_lock = threading.Lock()
