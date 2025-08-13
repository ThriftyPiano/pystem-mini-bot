# filename: boot.py
# Waiting for start button before launching main.py
from machine import Pin
import time

BUTTON_PIN = 26

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
button_pressed = False

def button_pressed_callback(pin):
    print("Launching main program...")
    global button_pressed
    button_pressed = True

button.irq(trigger=Pin.IRQ_RISING, handler=button_pressed_callback)

print("Waiting for start button...")

while not button_pressed:
    time.sleep(0.1)
