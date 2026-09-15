# filename: config.py  (GEARS simulator build)
#
# Simulator counterpart of examples/sdk_config.py. There are no pins here:
# the sdk modules that run in the browser (motor, orientation, color_sensor,
# head, wonder_echo) talk to GEARS's simPython bridge instead of machine.*,
# and only need port names. motor_pair.py is the real on-device file,
# loaded unmodified, so this must export the same names it imports.
import sys

BOARD = 'sim'

# GEARS gives the two drive wheels the fixed addresses outA / outB.
MOTOR_PINS = {
    'A': {'sim': 'outA'},   # left wheel
    'B': {'sim': 'outB'},   # right wheel
}

# The physical right-wheel servo is mounted mirrored, so +velocity on port B
# drives the robot backwards and motor_pair.py negates B to compensate.
# The simulator mirrors that wiring so the same motor_pair.py works.
MOTOR_REVERSED = {'A': False, 'B': True}

# No head servos in the simulated robot; head.py keeps the API and state.
HEAD_SERVOS = {'pan': None, 'tilt': None}

# Sensors get GEARS port names in the order they appear in
# robots/minibot.json: in1 = downward colour sensor, in2 = gyro.
COLOR_SENSOR_PINS = {'C': 'in1'}
GYRO_PORT = 'in2'

BUTTON_PIN = None
EXT_I2C = None
IMU = 'gears'
IMU_AXES = ('x', 'y', 'z')

HEAD_CONFIG = {
    'min_pulse_us': 500,
    'max_pulse_us': 2500,
    'min_angle': 0,
    'max_angle': 180,
    'center_angle': 90,
}

# Same keys as the on-device MOTOR_CONFIG. The geometry matches
# robots/minibot.json (measured from the Onshape assembly: 5.6 cm rubber
# discs whose contact patches are 8.2 cm apart) so motor_pair's
# distance/turn maths agrees with the physics it is driving.
MOTOR_CONFIG = {
    'pulses_per_revolution': 40,
    'wheel_diameter_cm': 5.6,
    'wheel_distance_cm': 8.2,
    'max_speed_dps': 540,
    'default_speed_dps': 360,
    'position_tolerance': 20,
    'control_loop_ms': 50,
}
