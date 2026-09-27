# Blink the robot's light once a second: the built-in LED on the Max V1
# (GPIO 2), the screen on the StickS3 (which has no LED).

from machine import Pin
import time

try:
    import sticks3
    screen = sticks3.display()
    led = None
except ImportError:
    screen = None
    led = Pin(2, Pin.OUT)

GREEN = 0x07E0   # RGB565
BLACK = 0x0000

def light_on():
    if screen is not None:
        screen.fill(GREEN)
    else:
        led.on()

def light_off():
    if screen is not None:
        screen.fill(BLACK)
    else:
        led.off()

print("Starting LED blink example...")
print("Watch your robot's light!")

while True:
    light_on()
    print("LED ON")
    time.sleep(1)

    light_off()
    print("LED OFF")
    time.sleep(1)
