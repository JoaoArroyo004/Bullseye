import threading
import time
import sys

# Importações dos seus serviços
from Services.Server.server import server_handler
from Services.Camera.camera_handlerv2 import camera_handler
# from Services.Servo.servo_handler_pi5 import servo_handler
from Services.Shared.shared_data import shared_data, data_lock

def main():
    print("[SYSTEM] Inicializando Threads de Background...")

    # 1. Iniciar Servo em Thread (Daemon para morrer quando o app fechar)
    # t_servo = threading.Thread(target=servo_handler, args=(shared_data, data_lock), daemon=True)
    # t_servo.start()

    # 2. Iniciar Server em Thread
    t_server = threading.Thread(target=server_handler, daemon=True)
    t_server.start()
    
    # Pequena pausa para garantir que threads subiram
    time.sleep(1.0)

    print("[SYSTEM] Iniciando Câmera na MAIN THREAD (Obrigatório para OpenCV GUI)...")
    
    try:
        # Thread principal roda a caemra
        # Isso resolve o problema de travamento da janela/buffer.
        camera_handler(shared_data, data_lock)
        
    except KeyboardInterrupt:
        print("\n[SYSTEM] Interrupção detectada. Encerrando...")
    except Exception as e:
        print(f"[ERROR] Erro fatal na main: {e}")
    finally:
        print("[SYSTEM] Saindo...")
        sys.exit(0)

if __name__ == "__main__":
    main()