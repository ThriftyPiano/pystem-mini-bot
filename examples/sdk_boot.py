# filename: boot.py
# Waiting for start button before launching main.py
from machine import Pin
import time

BUTTON_PIN = 26

# Enable internal Pull-Down if your button connects to 3.3V
# OR Pull-Up if your button connects to GND. 
# Assuming Pull-Up based on your previous code, but typically buttons connect to GND.
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

button_pressed = False
last_press_time = 0  # Initialize timestamp

def button_pressed_callback(pin):
    global button_pressed, last_press_time
    
    current_time = time.ticks_ms()
    
    # --- DEBOUNCE CHECK ---
    # If the last press was less than 200ms ago, ignore this one.
    if time.ticks_diff(current_time, last_press_time) < 200:
        return
    # ----------------------
    
    last_press_time = current_time
    print("Launching main program...")
    button_pressed = True

# Note: If your button connects to GND, use IRQ_FALLING. 
# If it connects to 3.3V, use IRQ_RISING.
# Bouncing happens on both edges, so usually, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING is safest if you want to catch either.
button.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=button_pressed_callback)

print("Waiting for start button...")

while not button_pressed:
    time.sleep(0.1)

# Clean up the interrupt so it doesn't interfere with main.py
button.irq(handler=None)