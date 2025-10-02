# ============================================
# MOTOR CONTROL EXAMPLE - Make Your Robot Move!
# ============================================
# This program teaches you how to control your robot's wheels.
# Your robot has two motors (left and right) that work together
# to make it go forward, backward, turn, and more!

# STEP 1: Import the libraries we need
# --------------------------------------------
import motor           # Controls individual motors
import motor_pair      # Controls two motors working together
import time            # Creates delays between movements

# STEP 2: Set up the motors
# --------------------------------------------
print("Pairing motors...")

# Connect the left and right motors together as a pair
# - PAIR_1: A label for this motor pair (you could have multiple pairs)
# - PORT_A: The left motor is connected to port A
# - PORT_B: The right motor is connected to port B
# Think of this like connecting two wheels to a steering wheel
motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)

# STEP 3: Move forward in a straight line
# --------------------------------------------
print("Moving straight for 10 rotations...")

# Move the robot forward by rotating the wheels
# - PAIR_1: Which motor pair to move
# - 360 * 10: How many degrees to rotate (360° = 1 full rotation, so 10 rotations)
# - 0: Steering (0 = straight, positive = right, negative = left)
# - velocity=360: How fast to move (360 degrees per second = 1 rotation/second)
motor_pair.move_for_degrees(motor_pair.PAIR_1, 360 * 10, 0, velocity=360)
time.sleep(1)  # Wait 1 second before next command

# STEP 4: Turn right
# --------------------------------------------
print("Turning right for 90 degrees...")

# Turn the robot by moving wheels at different speeds
# - PAIR_1: Which motor pair to use
# - 68: How many degrees the robot should turn
# - 90: Left wheel speed (positive = forward)
# - -90: Right wheel speed (negative = backward)
# When one wheel goes forward and one backward, the robot spins in place!
motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, 68, 90, -90)
time.sleep(1)

# STEP 5: Move forward for a specific time
# --------------------------------------------
print("Moving straight for 3 seconds...")

# Move forward for 3 seconds instead of a specific distance
# - PAIR_1: Which motor pair to move
# - 3000: How long to move in milliseconds (3000ms = 3 seconds)
# - 0: Steering (0 = straight)
# - velocity=360: Speed (360 degrees per second)
motor_pair.move_for_time(motor_pair.PAIR_1, 3000, 0, velocity=360)
time.sleep(1)

# STEP 6: Turn left
# --------------------------------------------
print("Turning left for 180 degrees...")

# Turn left (opposite of turning right)
# - PAIR_1: Which motor pair to use
# - -165: Negative degrees = turn left
# - -90: Left wheel backward
# - 90: Right wheel forward
# Notice: negative degrees + opposite wheel directions = turn left!
motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, -165, -90, 90)
time.sleep(1)

# STEP 7: Move forward again
# --------------------------------------------
print("Moving straight for 3 seconds...")
motor_pair.move_for_time(motor_pair.PAIR_1, 3000, 0, velocity=360)
time.sleep(1)

# STEP 8: Stop the motors
# --------------------------------------------
motor_pair.stop(motor_pair.PAIR_1)
print("Motors stopped!")
print("Program complete!")

# ============================================
# UNDERSTANDING THE MOVEMENT:
# ============================================
# - Both wheels forward at same speed = straight
# - Both wheels backward at same speed = reverse
# - One wheel faster than other = gentle turn
# - Wheels spinning opposite directions = spin in place
# - velocity controls speed (higher = faster)
# - degrees controls distance (more degrees = farther)
#
# EXPERIMENT IDEAS:
# ============================================
# 1. Change the velocity to make the robot go faster or slower
# 2. Change the degrees to make it move farther or turn more
# 3. Can you make the robot drive in a square?
# 4. Can you make it drive in a circle?
# 5. Try making your own dance routine!
# ============================================
