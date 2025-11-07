import RPi.GPIO as GPIO
import time

# =======================
# CONFIGURAÇÃO DO SERVO
# =======================
SERVO_PIN = 18  # GPIO18 (pino físico 12)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz típico
pwm.start(0)

current_angle = 45  # posição inicial (meio)

# Parâmetros do rastreamento
FRAME_WIDTH = 640
CENTER_X = FRAME_WIDTH // 2
DEAD_ZONE = 20  # pixels de tolerância
MAX_ANGLE = 120
MIN_ANGLE = 0

def set_angle(angle):
    """Move o servo para o ângulo especificado (0 a 120°)."""
    global current_angle
    angle = max(MIN_ANGLE, min(MAX_ANGLE, angle))
    duty = 2 + (angle / 18)  # duty cycle típico
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.3)
    pwm.ChangeDutyCycle(0)
    current_angle = angle
    print(f"[SERVO] Movido para {angle:.1f}° (Duty {duty:.2f}%)")

def servo_handler(shared_data=None, data_lock=None):
    """
    Thread principal do servo.
    Lê shared_data["target_x"] e converte em target_angle para seguir o rosto.
    """
    global current_angle
    print("[SERVO] Thread iniciada")

    try:
        while True:
            target_angle = current_angle

            if shared_data and data_lock:
                with data_lock:
                    target_x = shared_data.get("target_x", None)
                    face_count = shared_data.get("target_count", 0)

                if target_x is None:
                    time.sleep(0.1)
                    continue
                if face_count > 0 and target_x is not None:
                    error = target_x - CENTER_X

                    # só atualiza se fora da zona morta
                    if abs(error) > DEAD_ZONE:
                        # converte deslocamento do centro em variação de ângulo
                        # 45° = centro, +/- proporcional ao erro
                        delta_angle = -(error * 45 / CENTER_X)  # inverso do movimento
                        target_angle = current_angle + delta_angle
                        target_angle = max(MIN_ANGLE, min(MAX_ANGLE, target_angle))

            # move apenas se diferença significativa
            if abs(target_angle - current_angle) >= 1:  # 1° de tolerância
                set_angle(target_angle)

            time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

def cleanup():
    """Para o PWM e limpa GPIO."""
    pwm.stop()
    GPIO.cleanup()
