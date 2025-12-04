from gpiozero import Device, Servo
from gpiozero.pins.lgpio import LGPIOFactory
from time import sleep, time
from threading import Lock

# =======================
# GPIOZERO CONFIGURATION
# =======================
Device.pin_factory = LGPIOFactory()

SERVO_PIN = 18 
# Configuração padrão. Se seu servo for digital (barulhento), tente min=0.0006 e max=0.0024
servo = Servo(SERVO_PIN, min_pulse_width=0.0005, max_pulse_width=0.0025)

# =======================
# CONFIGURAÇÃO DE TRACKING
# =======================
FRAME_WIDTH = 640
CENTER_X = FRAME_WIDTH // 2

DEAD_ZONE = 100          
MAX_ANGLE = 120
MIN_ANGLE = 0
NEUTRAL_ANGLE = 60      

# Passos bem largos. O servo vai dar "tiros" precisos.
MAX_DELTA_PER_CYCLE = 5.0  
SMOOTH_FACTOR = 0.6        

# Intervalo entre verificações (Lentidão proposital)
SERVO_UPDATE_DELAY = 0.5 
SERVO_RETURN_DELAY = 5.0

# =======================
# INTERNAL STATE
# =======================
current_angle = NEUTRAL_ANGLE 
internal_lock = Lock()

def angle_to_normalized(angle):
    normalized = (angle - MIN_ANGLE) / (MAX_ANGLE - MIN_ANGLE) * 2 - 1
    return max(-1, min(1, normalized))

def execute_move(target_ang):
    """
    Função 'Atômica': Liga, Move, Espera, Desliga.
    Isso elimina o espasmo porque garante o ciclo completo.
    """
    global current_angle
    
    # 1. Trava os limites
    target_ang = max(MIN_ANGLE, min(MAX_ANGLE, target_ang))
    
    # 2. Só executa se tiver diferença real (> 1 grau)
    if abs(current_angle - target_ang) < 1.0:
        return False

    # 3. Manda o sinal
    servo.value = angle_to_normalized(target_ang)
    current_angle = target_ang
    
    # 4. O PULO DO GATO: Espera o motor chegar fisicamente lá.
    # Um servo comum leva ~0.1s para andar 60 graus. 0.2s é margem de segurança.
    sleep(0.25) 
    
    # 5. Corta o sinal para evitar tremedeira (Jitter)
    servo.detach()
    
    return True

def servo_handler(shared_data=None, data_lock=None):
    global current_angle
    if data_lock is None:
        data_lock = internal_lock

    print("[SERVO] Modo Discreto (Anti-Espasmo) Ativado")
    
    # Move para o centro inicial e desliga
    execute_move(NEUTRAL_ANGLE)
    
    last_loop_time = 0 
    last_detection_time = time()

    try:
        while True:
            current_time = time()

            # Controle de taxa de atualização (0.5s)
            if (current_time - last_loop_time) < SERVO_UPDATE_DELAY:
                sleep(1)
                continue

            last_loop_time = current_time
            target_x = None
            
            # --- LEITURA ---
            if shared_data:
                with data_lock:
                    target_x = shared_data.get("target_x", None)

            # --- LÓGICA ---
            if target_x is not None:
                last_detection_time = current_time
                error = target_x - CENTER_X
                
                if abs(error) > DEAD_ZONE:
                    print(f">>> [ALVO] Detectado em X={target_x} (Erro: {error})")
                    
                    correction = -(error * (MAX_ANGLE - MIN_ANGLE) / FRAME_WIDTH)
                    desired_angle = current_angle + correction
                    
                    # Calcula novo ângulo
                    new_angle = current_angle + (desired_angle - current_angle) * SMOOTH_FACTOR
                    
                    # Limita o passo máximo
                    delta = new_angle - current_angle
                    if delta > MAX_DELTA_PER_CYCLE:
                        new_angle = current_angle + MAX_DELTA_PER_CYCLE
                    elif delta < -MAX_DELTA_PER_CYCLE:
                        new_angle = current_angle - MAX_DELTA_PER_CYCLE

                    # Executa o movimento "blindado"
                    if execute_move(new_angle):
                        print(f"    -> MOVED to {new_angle:.1f}°")
                    else:
                        # Se a mudança for muito pequena, garante que está desligado
                        servo.detach()

            else:
                # Retorno ao centro se perdeu o alvo
                if (current_time - last_detection_time) > SERVO_RETURN_DELAY: # 5 segundos perdido
                    if abs(current_angle - NEUTRAL_ANGLE) > 5:
                        print(">>> [LOST] Voltando ao centro...")
                        step = 5 if current_angle < NEUTRAL_ANGLE else -5
                        execute_move(current_angle + step)
                    else:
                        servo.detach()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[SERVO ERROR] {e}")
    finally:
        servo.detach()