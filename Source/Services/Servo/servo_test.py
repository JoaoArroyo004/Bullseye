import time
from servo_handler import set_angle, cleanup

x, y = 10, 10

angle = 45  
print(f"Movendo servo para {angle}°")
set_angle(angle)
time.sleep(2)

# for a in [0, 45, 90]:
#     print(f"Movendo servo para {a}°")
#     set_angle(a)
#     time.sleep(2)

cleanup()
