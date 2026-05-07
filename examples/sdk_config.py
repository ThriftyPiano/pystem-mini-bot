# filename: config.py
# ESP32 Pin Configuration for SPIKE Prime Compatible API
# Modify these pin assignments to match your hardware setup

# Motor Pin Mappings
# Each motor needs: servo pin, encoder pin.
# A = left wheel, B = right wheel (the convention motor_pair / voice_drive expect).
MOTOR_PINS = {
    'A': {'servo': 16, 'encoder': 13},
    'B': {'servo': 18, 'encoder': 25},
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
