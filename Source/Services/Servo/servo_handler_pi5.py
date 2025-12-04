from gpiozero import Device, Servo
from gpiozero.pins.lgpio import LGPIOFactory
from time import sleep, time
from threading import Lock

# =======================
# GPIOZERO CONFIGURATION
# =======================
Device.pin_factory = LGPIOFactory()  # For Raspberry Pi 5

SERVO_PIN = 18 
# Ajuste fino: Se seu servo for digital, min/max podem precisar de ajuste
# Padrão SG90/MG90s costuma ser 0.0005 a 0.0025, mas servos grandes podem ser 0.0006 a 0.0024
servo = Servo(SERVO_PIN, min_pulse_width=0.0005, max_pulse_width=0.0025)

# =======================
# TRACKING PARAMETERS
# =======================
FRAME_WIDTH = 640
CENTER_X = FRAME_WIDTH // 2
DEAD_ZONE = 30          # Aumentei um pouco para evitar oscilação fina
MAX_ANGLE = 120
MIN_ANGLE = 0
MAX_DELTA_PER_CYCLE = 3 # Reduzi para o movimento ser menos "agressivo"
SMOOTH_FACTOR = 0.2     # Mais suavização (era 0.3)
NEUTRAL_ANGLE = 60      

# Configuração de "Paciência" (Debounce)
LOST_TARGET_DELAY = 2.0 # Segundos para esperar antes de voltar ao centro se perder o alvo
AUTO_DETACH_DELAY = 0.5 # Segundos parado para desligar o motor (evita tremedeira)

# =======================
# INTERNAL STATE
# =======================
current_angle = NEUTRAL_ANGLE 
internal_lock = Lock()

def angle_to_normalized(angle):
    normalized = (angle - MIN_ANGLE) / (MAX_ANGLE - MIN_ANGLE) * 2 - 1
    return max(-1, min(1, normalized))

def move_servo_safe(target_ang):
    """Move e atualiza o estado global"""
    global current_angle
    # Clamp
    target_ang = max(MIN_ANGLE, min(MAX_ANGLE, target_ang))
    
    # Só envia comando se tiver diferença real para poupar CPU/Jitter
    if abs(current_angle - target_ang) > 0.1:
        servo.value = angle_to_normalized(target_ang)
        current_angle = target_ang
        return True # Moveu
    return False # Não moveu

def servo_handler(shared_data=None, data_lock=None):
    global current_angle
    if data_lock is None:
        data_lock = internal_lock

    print("[SERVO] Handler Started (Pi 5 Optimized)")

    # Inicializa no centro
    move_servo_safe(NEUTRAL_ANGLE)
    
    last_detection_time = time()
    last_move_time = time()
    is_active = True

    try:
        while True:
            target_x = None
            
            # 1. Leitura Segura
            if shared_data:
                with data_lock:
                    target_x = shared_data.get("target_x", None)

            current_time = time()

            # 2. Lógica de Controle
            if target_x is not None:
                last_detection_time = current_time
                error = target_x - CENTER_X
                
                # Só calcula novo ângulo se estiver fora da zona morta
                if abs(error) > DEAD_ZONE:
                    # PID Proporcional simplificado
                    # Se error é positivo (direita), ângulo deve diminuir (ou aumentar, depende da montagem do servo)
                    # Assumindo: Direita da imagem > CENTER_X.
                    # Correção: O servo gira inversamente ou diretamente?
                    # Vou manter sua lógica original de sinal negativo:
                    correction = -(error * (MAX_ANGLE - MIN_ANGLE) / FRAME_WIDTH)
                    
                    desired_angle = current_angle + correction
                    
                    # Suavização (Exponential Moving Average)
                    new_angle = current_angle + (desired_angle - current_angle) * SMOOTH_FACTOR
                    
                    # Limita a velocidade (Delta máx)
                    if (new_angle - current_angle) > MAX_DELTA_PER_CYCLE:
                        new_angle = current_angle + MAX_DELTA_PER_CYCLE
                    elif (new_angle - current_angle) < -MAX_DELTA_PER_CYCLE:
                        new_angle = current_angle - MAX_DELTA_PER_CYCLE

                    if move_servo_safe(new_angle):
                        last_move_time = current_time
                        is_active = True

            else:
                # 3. Target Perdido - Lógica de Histerese (Debounce)
                # Só volta para o centro se perdeu o alvo por X segundos
                if (current_time - last_detection_time) > LOST_TARGET_DELAY:
                    # Move suavemente para o centro se já não estiver lá
                    if abs(current_angle - NEUTRAL_ANGLE) > 1:
                        # Move devagar para o centro
                        step = 1 if current_angle < NEUTRAL_ANGLE else -1
                        move_servo_safe(current_angle + step)
                        last_move_time = current_time
                        is_active = True
                        sleep(0.02) # Volta lenta

            # 4. Anti-Jitter (O Segredo para Pi 5)
            # Se faz tempo que não movemos, desliga o sinal PWM (Detach)
            if is_active and (current_time - last_move_time) > AUTO_DETACH_DELAY:
                servo.detach()
                is_active = False
                # print("[SERVO] Idle state - Motor Detached") 

            sleep(0.04) # ~25Hz loop rate é suficiente para servo mecânico

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[SERVO ERROR] {e}")
    finally:
        servo.detach()
        print("[SERVO] Stopped")