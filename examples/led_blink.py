# ============================================
# LED BLINK EXAMPLE - Your First Robot Program!
# ============================================
# This is the perfect first program to test your ESP32 connection.
# It makes the built-in LED on your ESP32 board blink on and off.
# Think of this as the "Hello World" of robotics!

# STEP 1: Import the libraries we need
# --------------------------------------------
# 'machine' is a library that lets us control the ESP32's hardware
# We specifically need 'Pin' to control the LED pins
from machine import Pin

# 'time' is a library that lets us create delays and pauses
# We'll use it to control how fast the LED blinks
import time

# STEP 2: Set up the LED
# --------------------------------------------
# Create a variable called 'led' that represents the built-in LED
# - Pin(2, ...) means we're using GPIO pin 2 (where the LED is connected)
# - Pin.OUT means we want to OUTPUT signals to this pin (turn it on/off)
# Think of this like getting a remote control for the LED
led = Pin(2, Pin.OUT)

# Print a message to let you know the program started
# You'll see this in the serial monitor/terminal
print("Starting LED blink example...")
print("Watch your ESP32's built-in LED!")

# STEP 3: The main blinking loop
# --------------------------------------------
# 'while True:' creates an infinite loop - this code will run forever
# (or until you stop the program or unplug the robot)
while True:
    # Turn the LED ON
    led.on()
    print("LED ON")  # Print status so you can see it in the terminal too
    
    # Wait for 1 second (1000 milliseconds)
    # The LED stays on during this time
    time.sleep(1)
    
    # Turn the LED OFF
    led.off()
    print("LED OFF")  # Print status
    
    # Wait for 1 second again
    # The LED stays off during this time
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
# ============================================
