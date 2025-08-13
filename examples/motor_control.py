# Basic Motor Control Example
import motor
import motor_pair
import time

print("Pairing motors...")
motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)

print("Moving straight for 10 rotations...")
motor_pair.move_for_degrees(motor_pair.PAIR_1, 360 * 10, 0, velocity=360)
time.sleep(1)

print("Turning right for 90 degrees...")
motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, 68, 90, -90)
time.sleep(1)

print("Moving straight for 3 seconds...")
motor_pair.move_for_time(motor_pair.PAIR_1, 3000, 0, velocity=360)
time.sleep(1)

print("Turning left for 180 degrees...")
motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, -165, -90, 90)
time.sleep(1)

print("Moving straight for 3 seconds...")
motor_pair.move_for_time(motor_pair.PAIR_1, 3000, 0, velocity=360)
time.sleep(1)

# Stop
motor_pair.stop(motor_pair.PAIR_1)
print("Motors stopped!")
