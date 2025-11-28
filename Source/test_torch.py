import threading
from Services.Camera.camera_handlerv3 import camera_handler

def main():
    shared_data = {
        "main_target": None,  # Nome do target que você deseja acompanhar, caso queira definir
        "target_x": None,
        "target_count": 0
    }

    data_lock = threading.Lock()

    camera_thread = threading.Thread(target=camera_handler, args=(shared_data, data_lock))
    camera_thread.start()

    print("Pressione Ctrl+C para sair...")
    try:
        while True:
            import time
            time.sleep(2)
            with data_lock:
                target_x = shared_data.get("target_x")
                count = shared_data.get("target_count")
            print(f"[INFO] Faces detectadas: {count}, Target X: {target_x}")
    except KeyboardInterrupt:
        print("Saindo...")

    camera_thread.join()

if __name__ == "__main__":
    main()
