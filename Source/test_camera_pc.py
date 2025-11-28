# test_camera_pc.py
import threading
from Services.Camera.camera_handlerv2 import camera_handler
from Services.Shared.shared_data import shared_data, data_lock
def main():
    # Dados compartilhados entre threads

    # Rodar o handler da câmera em uma thread
    camera_thread = threading.Thread(target=camera_handler, args=(shared_data, data_lock))
    camera_thread.start()

    print("Pressione Ctrl+C para sair...")
    try:
        while True:
            # Apenas imprime o status do target a cada 2s
            import time
            time.sleep(2)
            with data_lock:
                target_x = shared_data.get("target_x")
                count = shared_data.get("target_count")
            print(f"[INFO] Faces detectadas: {count}, Target X: {target_x}")
    except KeyboardInterrupt:
        print("Saindo...")
    finally:
        # O camera_handler fecha o OpenCV automaticamente ao pressionar 'q'
        camera_thread.join()

if __name__ == "__main__":
    main()
