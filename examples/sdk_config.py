# filename: config.py
# ESP32 Pin Configuration for SPIKE Prime Compatible API
# Modify these pin assignments to match your hardware setup

# Motor Pin Mappings
# Each motor needs: servo pin, encoder pin
MOTOR_PINS = {
    'A': {'servo': 16, 'encoder': 13},
    'B': {'servo': 17, 'encoder': 14},
    'C': {'servo': 5, 'encoder': 12},
    'D': {'servo': 18, 'encoder': 25},
    'E': {'servo': 19, 'encoder': 26},
    'F': {'servo': 23, 'encoder': 27}
}

# Motor Configuration
MOTOR_CONFIG = {
    # Encoder pulses per revolution (adjust for your encoders)
    'pulses_per_revolution': 20,
    
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
