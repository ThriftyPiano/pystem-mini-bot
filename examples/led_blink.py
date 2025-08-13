# Basic LED Blink Example
from machine import Pin
import time

# Configure the built-in LED (usually pin 2 on ESP32)
led = Pin(2, Pin.OUT)

print("Starting LED blink example...")

# Blink the LED forever
while True:
    led.on()
    print("LED ON")
    time.sleep(1)
    
    led.off()
    print("LED OFF")
    time.sleep(1)
