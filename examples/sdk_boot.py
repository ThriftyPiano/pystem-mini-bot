# filename: boot.py
# Waiting for start button before launching main.py
from machine import Pin
import time

try:
    from config import BOARD, BUTTON_PIN, LCD_ROTATION, BLE_REPL
except ImportError:
    # config.py missing from the device: fall back to the Max V1 pin so
    # the board still boots into main.py.
    BOARD = 'maxv1'
    BUTTON_PIN = 27
    LCD_ROTATION = 0
    BLE_REPL = False

# REPL over Bluetooth so the IDE can connect without a cable. Started
# here, before the button wait, and left running for main.py; the name
# goes on the screen so you connect to the right robot.
ble_name = None
if BLE_REPL:
    try:
        import ble_repl
        ble_name = ble_repl.start()
    except Exception as e:
        print("Bluetooth unavailable:", e)

# The prompt also goes on the StickS3's screen (screen.py: four lines,
# line 1 is the Bluetooth status that ble_repl maintains, lines 2-4 are
# ours). On a board without a screen it just prints.
try:
    import screen
except ImportError:
    screen = None

def show(*lines):
    if screen:
        screen.show(*lines)
    else:
        print(*lines)

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

show("Press top button to start")

while not button_pressed:
    time.sleep(0.1)

# Clean up the interrupt so it doesn't interfere with main.py
button.irq(handler=None)
show("Starting")
