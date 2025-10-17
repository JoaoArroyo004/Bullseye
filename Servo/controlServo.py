from gpiozero import Servo, LED
from time import sleep

myGPIO=11

servo=Servo("BOARD37")

i = 0
while True:
    servo.value = 0
    print(0)
    sleep(1)
    servo.value = 0.5
    print(30)
    sleep(1)    
    servo.value = 1
    print(60)
    sleep(1)
    servo.value = 0.5
    print(30)
    sleep(1)
    servo.value = 0
    print(0)
    sleep(1)
    servo.value = -0.5
    print(-30)
    sleep(1)
    servo.value = -1
    print(-60)
    sleep(1)
    servo.value = -0.5
    print(-30)
    sleep(1)

