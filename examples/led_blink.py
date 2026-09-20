# ============================================
# LED BLINK EXAMPLE - Your First Robot Program!
# ============================================
# This is the perfect first program to test your connection to the robot.
# It blinks a light on and off once a second. Think of this as the
# "Hello World" of robotics!
#
# The two robots have different lights:
#   - ESP32 Max V1 robot: the built-in LED on GPIO pin 2
#   - StickS3 robot: no LED, so we flash the stick's colour screen instead

# STEP 1: Import the libraries we need
# --------------------------------------------
# 'machine' is a library that lets us control the board's hardware
# We specifically need 'Pin' to control the LED pins
from machine import Pin

# 'time' is a library that lets us create delays and pauses
# We'll use it to control how fast the LED blinks
import time

# STEP 2: Find out which light we have
# --------------------------------------------
# The StickS3 has a 'sticks3' module built into its firmware. If we can
# import it, we are on the stick and will use its screen as the light.
try:
    import sticks3
    screen = sticks3.display()   # the 135x240 colour screen
    led = None
except ImportError:
    screen = None
    # Create a variable called 'led' that represents the built-in LED
    # - Pin(2, ...) means we're using GPIO pin 2 (where the LED is connected)
    # - Pin.OUT means we want to OUTPUT signals to this pin (turn it on/off)
    # Think of this like getting a remote control for the LED
    led = Pin(2, Pin.OUT)

GREEN = 0x07E0   # screen colours are 16-bit RGB565 numbers
BLACK = 0x0000

def light_on():
    if screen is not None:
        screen.fill(GREEN)   # paint the whole screen green
    else:
        led.on()

def light_off():
    if screen is not None:
        screen.fill(BLACK)   # paint the whole screen black
    else:
        led.off()

# Print a message to let you know the program started
# You'll see this in the serial monitor/terminal
print("Starting LED blink example...")
print("Watch your robot's light!")

# STEP 3: The main blinking loop
# --------------------------------------------
# 'while True:' creates an infinite loop - this code will run forever
# (or until you stop the program or unplug the robot)
while True:
    # Turn the light ON
    light_on()
    print("LED ON")  # Print status so you can see it in the terminal too

    # Wait for 1 second (1000 milliseconds)
    # The light stays on during this time
    time.sleep(1)

    # Turn the light OFF
    light_off()
    print("LED OFF")  # Print status

    # Wait for 1 second again
    # The light stays off during this time
    time.sleep(1)

    # After this, the loop repeats from the top!
    # So: ON for 1 second -> OFF for 1 second -> repeat forever

# ============================================
# EXPERIMENT IDEAS:
# ============================================
# Try changing the numbers in time.sleep():
# - time.sleep(0.5) = faster blinking (half second)
# - time.sleep(2) = slower blinking (2 seconds)
# - Can you make it blink 3 times fast, then pause?
# - On the StickS3, try another colour: 0xF800 is red, 0x001F is blue
# ============================================
