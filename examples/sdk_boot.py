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

# On the StickS3 the prompt also goes on the built-in LCD. The stick sits
# sideways on the robot, so the screen is used in landscape (see
# config.LCD_ROTATION): 240x135, frozen 16x32 font = 15 characters/line.
lcd = None
if BOARD == 'sticks3':
    try:
        import sticks3
        import vga1_16x32 as font
        lcd = sticks3.display(LCD_ROTATION)
    except Exception as e:
        print("LCD unavailable:", e)

def show(*lines):
    """Draw up to four lines of text, centred on the screen."""
    if lcd is None:
        return
    lcd.fill(0)
    step = font.HEIGHT + 8
    y = max(0, (lcd.height - len(lines) * step + 8) // 2)
    for i, s in enumerate(lines):
        x = max(0, (lcd.width - len(s) * font.WIDTH) // 2)
        lcd.text(font, s, x, y + step * i, 0xFFFF)

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

def show_prompt():
    if ble_name:
        state = "IDE connected" if ble_repl.connected() else "Press top btn"
        show(ble_name, state, "to start")
    else:
        show("Press top", "button", "to start")

show_prompt()
was_connected = False
while not button_pressed:
    time.sleep(0.1)
    if ble_name and ble_repl.connected() != was_connected:
        was_connected = not was_connected
        show_prompt()

# Clean up the interrupt so it doesn't interfere with main.py
button.irq(handler=None)
show("Starting")
