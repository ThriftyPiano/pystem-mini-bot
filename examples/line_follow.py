# Line Following Robot using Color Sensor and Motor Pair
# Follows the RIGHT EDGE of a black line (left=black, right=white)

import time
import motor_pair
from color_sensor import reflection

# Edge following parameters
BASE_SPEED = 200  # Base speed for motors (degrees per second)
MAX_SPEED = 400   # Maximum speed when on edge
MIN_SPEED = 0    # Minimum speed when turning

# Sensor thresholds for edge following
EDGE_TARGET = 35

# Proportional control parameters
KP = 8  # Proportional gain for edge following

class LineFollower:    
    def __init__(self, pair_id=motor_pair.PAIR_1, left_port='A', right_port='B'):
        # Initialize motor pair (disable orientation for line following)
        motor_pair.pair(pair_id, left_port, right_port)
        self.pair_id = pair_id
        self.motor_pair = motor_pair._get_pair(pair_id)
        
        # Edge following state
        self.edge_found = False
        self.search_direction = 1  # 1 = right, -1 = left
        self.lost_edge_time = 0
    
    def read_sensor(self):
        return reflection('C')
    
    def proportional_control(self):
        error = self.read_sensor() - EDGE_TARGET
        correction = KP * error
        correction = max(-100, min(100, correction))
        return correction
    
    def follow_line(self):
        correction = self.proportional_control()
        
        # Calculate motor speeds with correction
        # Positive correction = turn right, Negative correction = turn left
        left_speed = BASE_SPEED + correction
        right_speed = BASE_SPEED - correction
        
        # Limit speeds to reasonable ranges
        left_speed = max(MIN_SPEED, min(MAX_SPEED, left_speed))
        right_speed = max(MIN_SPEED, min(MAX_SPEED, right_speed))
        
        # Apply motor speeds
        self.motor_pair.move_tank(left_speed, right_speed)
    
    def run(self):
        print("Starting line following...")        
        while True:
            self.follow_line()
            time.sleep_ms(50)
    
    def stop(self):
        self.motor_pair.stop()

if __name__ == "__main__":
    follower = LineFollower()
    follower.run()
