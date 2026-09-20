# filename: config.py
# Pin configuration for the SPIKE Prime compatible API.
#
# The SDK runs on two boards. BOARD is detected from the firmware's machine
# string at import time; every hardware-specific fact the other sdk modules
# need is looked up here, keyed on it.
#
#   'maxv1'   — the original robot: ESP32 Max V1 board, external MPU-6050
#               and WonderEcho voice module on I2C bus 1, one TCRT5000
#               line sensor.
#   'sticks3' — M5StickS3 on the Bot HAT (hardware/sticks3-bot-hat). Uses
#               the stick's internal BMI270 via the frozen `sticks3` module,
#               and the built-in `speech_commands` recognizer instead of a
#               WonderEcho. Requires the speech-commands firmware.
#
# Uncomment the override to force a board if detection ever picks wrong.
import sys

BOARD = 'sticks3' if 'S3' in sys.implementation._machine else 'maxv1'
# BOARD = 'maxv1'

if BOARD == 'maxv1':
    # Motor Pin Mappings
    # Each motor needs: servo pin, encoder pin.
    # A = left wheel, B = right wheel (the convention motor_pair / voice_drive expect).
    MOTOR_PINS = {
        'A': {'servo': 16, 'encoder': 13},
        'B': {'servo': 18, 'encoder': 25},
    }

    # Head Servo Pin Mappings
    # The head uses two positional (0-180 deg) servos — no encoders.
    # pan = side-to-side (yaw), tilt = up-and-down (pitch).
    HEAD_SERVOS = {
        'pan': 19,
        'tilt': 17,
    }

    # TCRT5000 line/color sensor ADC pins by port letter. The Max V1 robot
    # has a single sensor; color_sensor.reflection() falls back to it for
    # any port name when only one is configured.
    COLOR_SENSOR_PINS = {
        'C': 32,
    }

    # No HC-SR04 header on the Max V1 board.
    DISTANCE_SENSOR_PINS = {}

    # Start button boot.py waits on (active low, internal pull-up).
    BUTTON_PIN = 27

    # External I2C bus shared by the MPU-6050 and the WonderEcho.
    EXT_I2C = {'id': 1, 'sda': 21, 'scl': 22, 'freq': 400000}

    # Orientation sensor backend (see orientation.py).
    IMU = 'mpu6050'

else:  # 'sticks3' — pins from hardware/sticks3-bot-hat/README.md
    MOTOR_PINS = {
        'A': {'servo': 5, 'encoder': 43},   # WHEEL A / ENC A (left)
        'B': {'servo': 4, 'encoder': 44},   # WHEEL B / ENC B (right)
    }

    HEAD_SERVOS = {
        'pan': 6,
        'tilt': 7,
    }

    # COLOR header (V G - A0, 3V3): TCRT5000 reflection sensor's A0 on
    # G1 = ADC1_CH0. Port 'C' like the Max V1 so line_follow.py runs unchanged.
    COLOR_SENSOR_PINS = {
        'C': 1,
    }

    # DIST header (5V TRIG ECHO GND): HC-SR04. The HAT divides the 5 V echo
    # pulse down to 3.3 V before G8; TRIG is driven at 3.3 V, which the
    # sensor accepts.
    DISTANCE_SENSOR_PINS = {
        'D': {'trig': 2, 'echo': 8},
    }

    # BtnA on the front of the stick (active low, internal pull-up).
    BUTTON_PIN = 11

    # No external I2C peripherals: the IMU is on the stick's internal bus
    # (owned by the frozen sticks3 module) and voice commands come from the
    # on-device speech_commands module, not a WonderEcho.
    EXT_I2C = None

    IMU = 'bmi270'

# How the IMU's axes map onto the robot's. Each entry names the sensor axis
# (with optional '-' to flip) that supplies the robot's x, y, z; the robot's
# z is "up", so yaw is the rotation about it and motor_pair expects it to
# grow when the robot turns clockwise. The Max V1 mapping is identity (the
# MPU-6050 board is mounted flat). The StickS3 lies flat, screen up, on the
# HAT: its z is up (+1 g at rest, measured 2026-09-19) but the BMI270's yaw
# rate is counter-clockwise-positive, so z is flipped here. Change this
# table, not orientation.py, if the stick is ever mounted differently.
IMU_AXES = {
    'maxv1':   ('x', 'y', 'z'),
    'sticks3': ('x', 'y', '-z'),
}[BOARD]

# Head Servo Configuration
HEAD_CONFIG = {
    # Servo pulse range in microseconds at 50Hz. 500us -> 0 deg, 2500us -> 180 deg.
    # Narrow these toward 600/2400 if a servo buzzes or grinds at the extremes.
    'min_pulse_us': 500,
    'max_pulse_us': 2500,

    # Software travel limits in degrees, so user code can't drive the head
    # into its mechanical stops. center() and the default rest both sit at 90.
    'min_angle': 0,
    'max_angle': 180,
    'center_angle': 90,
}

# Motor Configuration
MOTOR_CONFIG = {
    # Encoder pulses per WHEEL revolution. The encoder disc has 20 slots and
    # sits on the motor shaft, with a ~2:1 gearbox between the motor and the
    # wheel — so each wheel turn produces ~40 rising edges on the encoder.
    'pulses_per_revolution': 40,
    
    # Wheel specifications (for distance calculations)
    'wheel_diameter_cm': 6.0,  # Wheel diameter in cm
    'wheel_distance_cm': 6.7,  # Distance between wheels in cm
    
    # Motor limits
    'max_speed_dps': 540,  # Maximum speed in degrees per second
    'default_speed_dps': 360,  # Default speed in degrees per second
    
    # Control parameters
    'position_tolerance': 20,  # Position control tolerance in degrees
    'control_loop_ms': 50,  # Control loop period in milliseconds
}
