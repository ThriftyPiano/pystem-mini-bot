# filename: config.py
# Board detection and pin configuration for the SDK.
#   'maxv1'   ESP32 Max V1 board, MPU-6050 + WonderEcho on I2C bus 1
#   'sticks3' M5StickS3 on the Bot HAT (hardware/sticks3-bot-hat), speech firmware
import sys

BOARD = 'sticks3' if 'S3' in sys.implementation._machine else 'maxv1'
# BOARD = 'maxv1'

if BOARD == 'maxv1':
    # A = left wheel, B = right wheel
    MOTOR_PINS = {
        'A': {'servo': 16, 'encoder': 13},
        'B': {'servo': 18, 'encoder': 25},
    }

    HEAD_SERVOS = {
        'pan': 19,
        'tilt': 17,
    }

    COLOR_SENSOR_PINS = {
        'C': 32,
    }

    DISTANCE_SENSOR_PINS = {}

    BUTTON_PIN = 27

    EXT_I2C = {'id': 1, 'sda': 21, 'scl': 22, 'freq': 400000}

    IMU = 'mpu6050'

    LCD_ROTATION = 0

    # Bluetooth takes ~60 KB of the Max V1's ~100 KB heap.
    BLE_REPL = False

else:  # 'sticks3', pins from hardware/sticks3-bot-hat/README.md
    MOTOR_PINS = {
        'A': {'servo': 5, 'encoder': 43},   # WHEEL A / ENC A (left)
        'B': {'servo': 4, 'encoder': 44},   # WHEEL B / ENC B (right)
    }

    HEAD_SERVOS = {
        'pan': 6,
        'tilt': 7,
    }

    COLOR_SENSOR_PINS = {
        'C': 1,      # COLOR header A0, ADC1_CH0
    }

    DISTANCE_SENSOR_PINS = {
        'D': {'trig': 2, 'echo': 8},   # DIST header, ECHO divided to 3.3 V on the HAT
    }

    BUTTON_PIN = 11   # BtnA

    EXT_I2C = None

    IMU = 'bmi270'

    LCD_ROTATION = 3  # landscape, power-button edge up

    BLE_REPL = True

# Sensor axis (optionally '-' to flip) supplying the robot's x, y, z.
# motor_pair expects yaw to grow clockwise; the BMI270's yaw rate is
# counter-clockwise-positive, hence the flipped z on the StickS3.
IMU_AXES = {
    'maxv1':   ('x', 'y', 'z'),
    'sticks3': ('x', 'y', '-z'),
}[BOARD]

HEAD_CONFIG = {
    # Pulse width at 50 Hz: 500 us -> 0 deg, 2500 us -> 180 deg.
    'min_pulse_us': 500,
    'max_pulse_us': 2500,

    'min_angle': 0,
    'max_angle': 180,
    'center_angle': 90,
}

MOTOR_CONFIG = {
    # Encoder pulses per wheel revolution (20-slot disc, ~2:1 gearbox).
    'pulses_per_revolution': 40,

    'wheel_diameter_cm': 6.0,
    'wheel_distance_cm': 6.7,

    'max_speed_dps': 540,
    'default_speed_dps': 360,

    'position_tolerance': 20,
    'control_loop_ms': 50,
}
