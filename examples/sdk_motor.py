# filename: motor.py
# SPIKE Prime Compatible Motor Module for ESP32
# Supports continuous servo motors with LM393 encoders

from machine import Pin, PWM, Timer
import time
import math
from config import MOTOR_PINS, MOTOR_CONFIG

# Port constants (matching SPIKE Prime API)
PORT_A = 'A'
PORT_B = 'B'
PORT_C = 'C'
PORT_D = 'D'
PORT_E = 'E'
PORT_F = 'F'

# Motor direction constants
CLOCKWISE = 1
COUNTERCLOCKWISE = -1
SHORTEST_PATH = 0
LONGEST_PATH = 1

class Motor:
    """ESP32 Motor controller that mimics SPIKE Prime motor interface"""
    
    def __init__(self, port, servo_pin, encoder_pin):
        self.port = port
        self.servo_pin = servo_pin
        self.encoder_pin = encoder_pin
        
        # Setup servo PWM (50Hz for standard servos)
        self.pwm = PWM(Pin(servo_pin))
        self.pwm.freq(50)
        
        # Setup encoder pin
        self.encoder = Pin(encoder_pin, Pin.IN)
        
        # Encoder state
        self.position = 0
        self.pulse_count = 0
        self.last_pulse_time = time.ticks_ms()
        self.velocity = 0
        self.direction = 1  # 1 for forward, -1 for reverse
        
        # Motor state
        self.target_position = 0
        self.target_velocity = MOTOR_CONFIG['default_speed_dps']  # Default target velocity
        self.is_running = False
        self.current_speed = 0
        
        # Setup encoder interrupt (count rising edges)
        self.encoder.irq(trigger=Pin.IRQ_RISING, handler=self._encoder_callback)
        
        # Timer for position control
        timer_id = ord(port) - ord('A')
        # ESP32 only supports 0-3, so error if port is invalid
        if timer_id < 0 or timer_id > 3:
            raise ValueError("Only ports A-D are supported.")
        self.control_timer = Timer(timer_id)
        
        # Stop motor initially
        self._set_servo_speed(0)
    
    def _encoder_callback(self, pin):
        """Handle encoder interrupts to track position"""
        current_time = time.ticks_ms()
        
        # Count pulses
        self.pulse_count += 1
        
        # Update position based on direction and pulse count
        degrees_per_pulse = 360 / MOTOR_CONFIG['pulses_per_revolution']
        self.position += self.direction * degrees_per_pulse
        
        # Calculate velocity (degrees per second)
        dt = time.ticks_diff(current_time, self.last_pulse_time) / 1000.0
        if dt > 0:
            self.velocity = degrees_per_pulse / dt * self.direction
        
        self.last_pulse_time = current_time
    
    def _set_servo_speed(self, speed):
        """Set servo speed (-100 to 100, 0 = stop)"""
        # Convert speed to servo pulse width
        # Typical servo: 1ms = full reverse, 1.5ms = stop, 2ms = full forward
        if speed == 0:
            pulse_width = 1500  # Stop position
            self.direction = 0
            self.pwm.duty_u16(0)
        else:
            self.pwm.freq(50)
            # Map -100 to 100 -> 1000 to 2000 microseconds
            pulse_width = int(1500 + (speed * 5))
            pulse_width = max(1000, min(2000, pulse_width))
            # Track direction for encoder counting
            self.direction = 1 if speed > 0 else -1
        
        # Convert to duty cycle (50Hz = 20ms period)
        duty = int((pulse_width / 20000) * 1023)
        if speed == 0:
            duty = 0
        self.pwm.duty_u16(int(duty * 64))  # Convert to 16-bit duty cycle
        self.current_speed = speed
    
    def _position_control(self, timer):
        """Position control loop"""
        if not self.is_running:
            self._set_servo_speed(0)
            self.control_timer.deinit()
            return
            
        error = self.target_position - self.position
        
        if abs(error) < MOTOR_CONFIG['position_tolerance']:  # Use configured tolerance
            self._set_servo_speed(0)
            self.is_running = False
            self.control_timer.deinit()
            return
        
        # Use target velocity to limit speed
        # Convert target velocity to speed percentage
        max_speed_percent = max(-100, min(100, self.target_velocity / (MOTOR_CONFIG['max_speed_dps'] / 100)))
        
        # # Simple proportional control with velocity limiting
        # speed = max(-100, min(100, error * 0.2))
        # # Limit speed to target velocity
        # if speed > 0:
        #     speed = min(speed, abs(max_speed_percent))
        # else:
        #     speed = max(speed, -abs(max_speed_percent))
        
        # # Ensure minimum speed is not too low
        # if abs(speed) < 15:  # Minimum speed threshold
        #     speed = 15 if speed > 0 else -15
        # self._set_servo_speed(speed)

        self._set_servo_speed(max_speed_percent)

    def stop(self):
        """Stop the motor"""
        self.is_running = False
        self._set_servo_speed(0)
        self.control_timer.deinit()
        self.pwm.duty_u16(0)
        print('stop motor ' + self.port)

# Global motor instances
_motors = {}

def _get_motor(port):
    """Get or create motor instance for port"""
    if port not in _motors:
        if port in MOTOR_PINS:
            pins = MOTOR_PINS[port]
            _motors[port] = Motor(port, pins['servo'], pins['encoder'])
        else:
            raise ValueError(f"Invalid port: {port}. Available ports: {list(MOTOR_PINS.keys())}")
    
    return _motors[port]

# SPIKE Prime Motor API Functions

def run(port, velocity, *, acceleration=1000):
    """Run motor at specified velocity (degrees per second)"""
    motor = _get_motor(port)
    
    # Convert degrees per second to servo speed percentage
    # Use configured max speed for conversion
    speed_percent = max(-100, min(100, velocity / (MOTOR_CONFIG['max_speed_dps'] / 100)))
    motor._set_servo_speed(speed_percent)
    motor.is_running = True

def run_for_degrees(port, degrees, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    """Run motor for specified degrees"""
    motor = _get_motor(port)
    
    start_position = motor.position
    motor.target_position = start_position + degrees
    motor.target_velocity = velocity  # Store target velocity for position control
    motor.is_running = True
    
    # Start position control
    motor.control_timer.init(period=MOTOR_CONFIG['control_loop_ms'], mode=Timer.PERIODIC, callback=motor._position_control)
    
    # Wait for completion if blocking
    if stop:
        while motor.is_running:
            time.sleep_ms(10)

def run_for_time(port, time_ms, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    """Run motor for specified time"""
    motor = _get_motor(port)
    
    # Convert degrees per second to servo speed percentage
    speed_percent = max(-100, min(100, velocity / (MOTOR_CONFIG['max_speed_dps'] / 100)))
    motor._set_servo_speed(speed_percent)
    motor.is_running = True
    
    # Run for specified time
    time.sleep_ms(time_ms)
    
    if stop:
        motor.stop()

def run_to_position(port, position, velocity, *, direction=SHORTEST_PATH, stop=True, acceleration=1000, deceleration=1000):
    """Run motor to absolute position"""
    motor = _get_motor(port)
    
    motor.target_position = position
    motor.target_velocity = velocity  # Store target velocity for position control
    motor.is_running = True
    
    # Start position control
    motor.control_timer.init(period=MOTOR_CONFIG['control_loop_ms'], mode=Timer.PERIODIC, callback=motor._position_control)
    
    # Wait for completion if blocking
    if stop:
        while motor.is_running:
            time.sleep_ms(10)

def run_to_degrees_counted(port, degrees, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    """Run motor to position relative to last reset"""
    run_to_position(port, degrees, velocity, stop=stop, acceleration=acceleration, deceleration=deceleration)

def stop(port, *, stop=True):
    """Stop motor"""
    motor = _get_motor(port)
    motor.stop()

def reset_relative_position(port, position):
    """Reset relative position counter"""
    motor = _get_motor(port)
    motor.position = position

def get_position(port):
    """Get current position in degrees"""
    motor = _get_motor(port)
    return motor.position

def get_degrees_counted(port):
    """Get degrees counted since last reset"""
    return get_position(port)

def get_velocity(port):
    """Get current velocity in degrees per second"""
    motor = _get_motor(port)
    return motor.velocity

def get_default_velocity(port):
    """Get default velocity (placeholder)"""
    return MOTOR_CONFIG['default_speed_dps']

def set_degrees_counted(port, degrees_counted):
    """Set the degrees counted value"""
    reset_relative_position(port, degrees_counted)

def was_interrupted(port):
    """Check if motor was interrupted (placeholder)"""
    return False

def was_stalled(port):
    """Check if motor was stalled (placeholder)"""
    return False

def get_duty_cycle(port):
    """Get current duty cycle percentage"""
    motor = _get_motor(port)
    return motor.current_speed
