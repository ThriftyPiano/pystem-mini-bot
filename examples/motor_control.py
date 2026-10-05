# Motor control: drive a 40 cm square with motor_pair (straight, turn right, repeat).
#
# Speed matters: fast wheels slip (spin without moving the robot), which ruins
# both the distance and the heading hold. A slow drive lets the tyres grip, so
# the IMU yaw-hold and the encoder distance both land where they should. On a
# grippy floor you can raise DRIVE_VELOCITY/TURN_VELOCITY; if the robot slips
# (encoders turn but it barely moves), lower them.

import math
import motor
import motor_pair
import time
from config import MOTOR_CONFIG

SIDE_M = 0.4            # length of each side (40 cm)
DRIVE_VELOCITY = 90     # wheel deg/s while driving straight (slow = no slip)
TURN_VELOCITY = 40      # wheel deg/s per wheel while turning in place (slow = less coast past the target)

WHEEL_CIRCUMFERENCE_CM = math.pi * MOTOR_CONFIG['wheel_diameter_cm']
SIDE_DEGREES = round(SIDE_M * 100 / WHEEL_CIRCUMFERENCE_CM * 360)      # wheel degrees per side

print("Pairing motors...")
motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)

for side in range(4):
    print("Side", side + 1, ": straight for", SIDE_M, "m")
    motor_pair.move_for_degrees(motor_pair.PAIR_1, SIDE_DEGREES, 0, velocity=DRIVE_VELOCITY)
    time.sleep(0.2)

    print("Turning right 90 degrees...")
    motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, 90, TURN_VELOCITY, -TURN_VELOCITY)
    time.sleep(0.2)

motor_pair.stop(motor_pair.PAIR_1)
print("Square complete!")
