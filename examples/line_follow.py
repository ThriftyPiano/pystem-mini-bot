# ============================================
# LINE FOLLOWING ROBOT - Autonomous Behavior!
# ============================================
# This is your first AUTONOMOUS robot program!
# The robot uses its color sensor to detect and follow a line automatically.
# It follows the RIGHT EDGE of a black line on a white surface.
#
# HOW IT WORKS:
# The robot constantly reads the sensor and adjusts its steering to stay
# on the edge between black and white. If it drifts left (too much black),
# it turns right. If it drifts right (too much white), it turns left.
# This creates smooth line following behavior!

import time
import motor_pair
from color_sensor import reflection

# ============================================
# CONFIGURATION SETTINGS
# ============================================
# These numbers control how the robot behaves. You can experiment with them!

# Motor speed settings (in degrees per second)
BASE_SPEED = 200   # Normal cruising speed - try 150 for slower, 250 for faster
MAX_SPEED = 400    # Maximum speed when correcting course
MIN_SPEED = 0      # Minimum speed (0 = wheel can stop if needed)

# Sensor target value
EDGE_TARGET = 35   # The "perfect" sensor reading (between black and white)
                   # Lower = darker, Higher = brighter
                   # Try adjusting this if your robot can't find the line

# Control system setting
KP = 8             # How aggressively the robot corrects its steering
                   # Higher = sharper turns (might wobble)
                   # Lower = gentler turns (might lose the line)

# ============================================
# THE LINEFOLLOWER CLASS
# ============================================
# A "class" is like a blueprint for creating a robot controller.
# It bundles together all the code needed to make the robot follow a line.

class LineFollower:    
    def __init__(self, pair_id=motor_pair.PAIR_1, left_port='A', right_port='B'):
        """
        Initialize the line follower robot.
        This runs once when you create a LineFollower object.
        It sets up the motors and sensor.
        """
        # Connect and pair the left and right motors
        motor_pair.pair(pair_id, left_port, right_port)
        self.pair_id = pair_id
        self.motor_pair = motor_pair._get_pair(pair_id)
        
        # Variables to track the robot's state
        self.edge_found = False        # Has the robot found the line edge?
        self.search_direction = 1      # Which way to search: 1=right, -1=left
        self.lost_edge_time = 0        # How long since we lost the line
        
        print("Line follower initialized!")
        print(f"Base speed: {BASE_SPEED}, Target: {EDGE_TARGET}")
    
    def read_sensor(self):
        """
        Read the current brightness from the color sensor.
        Returns a number from 0 (very dark) to 100 (very bright).
        The sensor is connected to port 'C'.
        """
        return reflection('C')
    
    def proportional_control(self):
        """
        Calculate how much the robot needs to turn to stay on the line.
        This is called "proportional control" - a fundamental concept in robotics!
        
        HOW IT WORKS:
        1. Read the sensor value
        2. Compare it to our target (EDGE_TARGET)
        3. Calculate the "error" (difference between actual and target)
        4. Multiply error by KP to get correction amount
        5. Limit the correction so it's not too extreme
        
        EXAMPLE:
        If sensor reads 50 (too bright/white) and target is 35:
        - error = 50 - 35 = 15 (we're too far right)
        - correction = 8 * 15 = 120 (would turn left)
        - but we limit it to max 100, so correction = 100
        This makes the left wheel speed up and right wheel slow down = turn left!
        """
        # Step 1: Calculate the error
        sensor_value = self.read_sensor()
        error = sensor_value - EDGE_TARGET
        
        # Step 2: Calculate correction based on error
        correction = KP * error
        
        # Step 3: Limit correction to prevent crazy speeds
        # max() and min() ensure correction stays between -100 and +100
        correction = max(-100, min(100, correction))
        
        return correction
    
    def follow_line(self):
        """
        Execute one step of line following.
        This function is called many times per second to continuously
        adjust the robot's path.
        """
        # Get the steering correction from our control algorithm
        correction = self.proportional_control()
        
        # Apply the correction to motor speeds
        # POSITIVE correction = sensor too bright = turn LEFT
        #   (speed up left wheel, slow down right wheel)
        # NEGATIVE correction = sensor too dark = turn RIGHT  
        #   (slow down left wheel, speed up right wheel)
        
        left_speed = BASE_SPEED + correction
        right_speed = BASE_SPEED - correction
        
        # Make sure speeds don't go below MIN_SPEED or above MAX_SPEED
        # This prevents wheels from spinning too fast or going backward
        left_speed = max(MIN_SPEED, min(MAX_SPEED, left_speed))
        right_speed = max(MIN_SPEED, min(MAX_SPEED, right_speed))
        
        # Send the calculated speeds to the motors
        self.motor_pair.move_tank(left_speed, right_speed)
    
    def run(self):
        """
        Start the line following robot.
        This creates an infinite loop that constantly:
        1. Reads the sensor
        2. Calculates correction
        3. Adjusts motor speeds
        4. Waits a tiny bit (50ms)
        5. Repeats forever!
        """
        print("Starting line following...")
        print("Make sure your robot is positioned on the line edge!")
        print("Press Ctrl+C to stop")
        
        # The main loop - runs forever until you stop the program
        while True:
            # Execute one line-following step
            self.follow_line()
            
            # Wait 50 milliseconds before the next step
            # This gives the motors time to respond and prevents overwhelming the system
            time.sleep_ms(50)
    
    def stop(self):
        """
        Stop the robot's motors.
        Call this when you want to end the program gracefully.
        """
        self.motor_pair.stop()
        print("Robot stopped!")

# ============================================
# MAIN PROGRAM EXECUTION
# ============================================
# This code only runs when you execute this file directly
# (not when it's imported by another program)

if __name__ == "__main__":
    # Create a LineFollower robot object
    follower = LineFollower()
    
    # Start following the line!
    # This will run forever until you stop the program
    follower.run()

# ============================================
# HOW TO USE THIS PROGRAM:
# ============================================
# 1. Create a line track:
#    - Use black electrical tape on white paper, or
#    - Print a black line on white paper
#    - Line should be about 1-2 cm wide
#
# 2. Position your robot:
#    - Place robot so sensor is over the RIGHT EDGE of the line
#    - The sensor should see half black, half white
#
# 3. Run the program:
#    - Click "Write to Robot" in the IDE
#    - Watch your robot follow the line!
#
# EXPERIMENT IDEAS:
# ============================================
# 1. Change BASE_SPEED - what happens if you go faster or slower?
# 2. Adjust KP - try 4 or 12 - how does steering change?
# 3. Change EDGE_TARGET if your robot can't find the line
# 4. Try different line colors or surfaces
# 5. Make a complex track with turns and loops!
# ============================================
