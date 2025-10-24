import time
from servo_handler import set_angle, cleanup, current_angle

# Parâmetros da câmera simulada
FRAME_WIDTH = 640
CENTER_X = FRAME_WIDTH // 2
DEAD_ZONE = 20

# Lista de "rostos" simulados (x, y)
simulated_faces = [10, 100, 200, 320, 450, 600,50,30,315,330,640, 100, 540, 320, 310, 400, 200, 150, 30]

try:
    for target_x in simulated_faces:
        print(f"\nSimulando rosto em x={target_x}")

        # Calcula erro relativo ao centro
        error = target_x - CENTER_X

        # Aplica zona morta
        if abs(error) > DEAD_ZONE:
            # Converte deslocamento do centro em ângulo
            delta_angle = -(error * 45 / CENTER_X)  # mesmo cálculo do servo_handler
            target_angle = current_angle + delta_angle
            target_angle = max(0, min(120, target_angle))
            print(f"Movendo servo para {target_angle:.1f}°")
            set_angle(target_angle)
        else:
            print("Rosto dentro da zona morta, servo não se move")

        time.sleep(0.1)

finally:
    cleanup()
