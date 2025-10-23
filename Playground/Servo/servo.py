import RPi.GPIO as GPIO
import time

# ==== CONFIGURAÇÕES ====
SERVO_PIN = 18        # Pino GPIO (modo BCM)
PWM_FREQ = 50         # Frequência típica para servo (50Hz)
FRAME_WIDTH = 640     # Largura do frame da câmera (ajuste conforme seu caso)

# ==== SETUP ====
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, PWM_FREQ)
pwm.start(0)

# ==== FUNÇÕES AUXILIARES ====

def angle_to_duty(angle):
    """
    Converte um ângulo (0 a 180) para duty cycle (%)
    Servos comuns usam ~2.5% (0°) até ~12.5% (180°)
    """
    return 2.5 + (angle / 180.0) * 10

def x_to_angle(x, frame_width=FRAME_WIDTH, max_angle=90):
    """
    Converte a posição X (0 até frame_width) em ângulo (0 até max_angle)
    """
    x = max(0, min(x, frame_width))  # garante que fique dentro do limite
    angle = (x / frame_width) * max_angle
    return angle

def move_servo_to(x):
    """
    Recebe a coordenada X e move o servo para o ângulo correspondente
    """
    angle = x_to_angle(x)
    duty = angle_to_duty(angle)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.3)  # tempo para o servo alcançar a posição
    pwm.ChangeDutyCycle(0)  # evita vibração

# ==== EXEMPLO DE USO ====
try:
    while True:
        # Exemplo: leitura simulada de um ponto (x, y)
        x = int(input("Digite o valor de X (0 a 640): "))
        move_servo_to(x)

except KeyboardInterrupt:
    print("\nEncerrando...")
finally:
    pwm.stop()
    GPIO.cleanup()
