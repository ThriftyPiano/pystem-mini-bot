# Line following with the color sensor: follows the right edge of a black
# line on a white surface.

import time
import motor_pair
from color_sensor import reflection

BASE_SPEED = 200   # degrees per second
MAX_SPEED = 400
MIN_SPEED = 0

EDGE_TARGET = 35   # sensor reading on the edge (0 = dark, 100 = bright)

KP = 8             # steering gain


class LineFollower:
    def __init__(self, pair_id=motor_pair.PAIR_1, left_port='A', right_port='B'):
        motor_pair.pair(pair_id, left_port, right_port)
        self.pair_id = pair_id
        self.motor_pair = motor_pair._get_pair(pair_id)

        self.edge_found = False
        self.search_direction = 1
        self.lost_edge_time = 0

        print("Line follower initialized!")
        print(f"Base speed: {BASE_SPEED}, Target: {EDGE_TARGET}")

    def read_sensor(self):
        return reflection('C')

    def proportional_control(self):
        sensor_value = self.read_sensor()
        error = sensor_value - EDGE_TARGET

        correction = KP * error
        correction = max(-100, min(100, correction))

        return correction

    def follow_line(self):
        correction = self.proportional_control()

        left_speed = BASE_SPEED + correction
        right_speed = BASE_SPEED - correction

        left_speed = max(MIN_SPEED, min(MAX_SPEED, left_speed))
        right_speed = max(MIN_SPEED, min(MAX_SPEED, right_speed))

        self.motor_pair.move_tank(left_speed, right_speed)

    def run(self):
        print("Starting line following...")
        print("Make sure your robot is positioned on the line edge!")
        print("Press Ctrl+C to stop")

        while True:
            self.follow_line()
            time.sleep_ms(50)

    def stop(self):
        self.motor_pair.stop()
        print("Robot stopped!")


if __name__ == "__main__":
    follower = LineFollower()
    follower.run()
