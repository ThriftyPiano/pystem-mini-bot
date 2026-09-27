# filename: boot.py
# Starts the Bluetooth REPL, then waits for the start button before main.py.
from machine import Pin
import time

try:
    from config import BOARD, BUTTON_PIN, LCD_ROTATION, BLE_REPL
except ImportError:
    BOARD = 'maxv1'
    BUTTON_PIN = 27
    LCD_ROTATION = 0
    BLE_REPL = False

ble_name = None
if BLE_REPL:
    try:
        import ble_repl
        ble_name = ble_repl.start()
    except Exception as e:
        print("Bluetooth unavailable:", e)

try:
    import screen
except ImportError:
    screen = None

def show(*lines):
    if screen:
        screen.show(*lines)
    else:
        print(*lines)

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

button_pressed = False
last_press_time = 0

def button_pressed_callback(pin):
    global button_pressed, last_press_time

    current_time = time.ticks_ms()

    # 200 ms debounce
    if time.ticks_diff(current_time, last_press_time) < 200:
        return

    last_press_time = current_time
    print("Launching main program...")
    button_pressed = True

button.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=button_pressed_callback)

show("Press top btn", "to start")

while not button_pressed:
    time.sleep(0.1)

button.irq(handler=None)
show("Starting")
