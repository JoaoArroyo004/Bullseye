from gpiozero import Servo, LED
from time import sleep

myGPIO=11

servo=Servo("BOARD15")

i = 0
while True:
    servo.detach
    sleep(1)
    print(servo.pulse_width)
    servo.mid()
    sleep(1)
