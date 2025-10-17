from gpiozero import Servo, LED
from time import sleep

myGPIO=11

servo=LED("BOARD15")

i = 0
while True:
    print("Hello")
    servo.on()
    sleep(0.001)
    servo.off()
    sleep(0.019)
