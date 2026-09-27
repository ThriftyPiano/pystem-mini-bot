# Motor control: drive a 1 m square with motor_pair (straight, turn right, repeat).

import math
import motor
import motor_pair
import time
from config import MOTOR_CONFIG

SIDE_M = 1.0            # length of each side
SPEED_M_PER_S = 0.2
TURN_VELOCITY = 90      # wheel deg/s while turning in place

WHEEL_CIRCUMFERENCE_CM = math.pi * MOTOR_CONFIG['wheel_diameter_cm']
VELOCITY = round(SPEED_M_PER_S * 100 / WHEEL_CIRCUMFERENCE_CM * 360)   # wheel deg/s
SIDE_DEGREES = round(SIDE_M * 100 / WHEEL_CIRCUMFERENCE_CM * 360)      # wheel degrees per side

print("Pairing motors...")
motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)

for side in range(4):
    print("Side", side + 1, ": straight for", SIDE_M, "m")
    motor_pair.move_for_degrees(motor_pair.PAIR_1, SIDE_DEGREES, 0, velocity=VELOCITY)
    time.sleep(1)

    print("Turning right 90 degrees...")
    motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, 90, TURN_VELOCITY, -TURN_VELOCITY)
    time.sleep(1)

motor_pair.stop(motor_pair.PAIR_1)
print("Square complete!")
