# filename: motor_pair.py
# SPIKE Prime Compatible Motor Pair Module for ESP32
# Controls two motors together for robot movement

import motor
import time
import math
from config import MOTOR_CONFIG
try:
    from orientation import OrientationSensor
    HAS_ORIENTATION = True
except ImportError:
    HAS_ORIENTATION = False
    print("Warning: orientation module not available, straight-line correction disabled")

# Pair constants
PAIR_1 = 1
PAIR_2 = 2
PAIR_3 = 3

class MotorPair:
    """Motor pair controller for differential drive robots"""
    
    def __init__(self, pair_id, left_port, right_port, use_orientation=True):
        self.pair_id = pair_id
        self.left_port = left_port
        self.right_port = right_port
        self.wheel_circumference = MOTOR_CONFIG['wheel_diameter_cm'] * math.pi  # Calculate from diameter
        self.wheel_distance = MOTOR_CONFIG['wheel_distance_cm']  # cm, distance between wheels
        self.default_velocity = MOTOR_CONFIG['default_speed_dps']  # degrees per second
        # Set which motor should be reversed (typically right motor in differential drive)
        self.left_reversed = False
        self.right_reversed = True
        
        # Initialize orientation sensor if available and requested
        self.orientation_sensor = None
        if use_orientation and HAS_ORIENTATION:
            try:
                self.orientation_sensor = OrientationSensor()
                print("Orientation sensor initialized for straight-line correction")
            except Exception as e:
                print(f"Failed to initialize orientation sensor: {e}")
                self.orientation_sensor = None
        
    def _get_motor_velocity(self, velocity, is_right_motor=False):
        """Get the correct velocity for a motor considering reversal"""
        # Don't reverse velocity here - let run_for_degrees handle it
        return velocity
    
    def _get_motor_degrees(self, degrees, is_right_motor=False):
        """Get the correct degrees for a motor considering reversal"""
        # For reversed motors, we need to reverse the degrees direction
        if is_right_motor and self.right_reversed:
            return -degrees
        elif not is_right_motor and self.left_reversed:
            return -degrees
        return degrees
        
    def move(self, steering, velocity=None):
        """Move with steering control"""
        if velocity is None:
            velocity = self.default_velocity
            
        # Calculate left and right velocities based on steering
        # steering: -100 (full left) to 100 (full right), 0 = straight
        left_velocity = velocity
        right_velocity = velocity
        
        if steering != 0:
            # Differential steering
            if steering > 0:  # Turn right
                left_velocity = velocity
                right_velocity = velocity * (1 - abs(steering) / 100)
            else:  # Turn left
                left_velocity = velocity * (1 - abs(steering) / 100)
                right_velocity = velocity
        
        motor.run(self.left_port, int(left_velocity))
        motor.run(self.right_port, int(-right_velocity if self.right_reversed else right_velocity))
    
    def _init_yaw_reference(self, steering):
        """Initialize yaw reference for straight-line movement"""
        target_yaw = 0
        if self.orientation_sensor and steering == 0:
            self.orientation_sensor.update()  # Get current orientation
            self.orientation_sensor.reset_yaw()  # Set current direction as reference
            target_yaw = 0
        return target_yaw
    
    def _apply_yaw_correction(self, steering, target_yaw, velocity, correction_mode='position'):
        """Apply yaw correction for straight-line movement
        
        Args:
            steering: Current steering value
            target_yaw: Target yaw angle
            velocity: Base velocity
            correction_mode: 'position' for target_velocity adjustment, 'velocity' for direct motor.run()
        
        Returns:
            yaw_error for debugging purposes
        """
        yaw_error = 0
        if self.orientation_sensor and steering == 0:
            try:
                # Update orientation
                self.orientation_sensor.update()
                current_yaw = self.orientation_sensor.get_yaw()
                yaw_error = target_yaw - current_yaw
                
                # Apply correction if yaw error is significant
                if abs(yaw_error) > 1.0:
                    # Calculate correction factor (proportional control)
                    correction = yaw_error * 10
                    correction = max(-50, min(50, correction))  # Limit correction
                    
                    if correction_mode == 'position':
                        # For move_for_degrees - adjust target_velocity
                        left_motor = motor._get_motor(self.left_port)
                        right_motor = motor._get_motor(self.right_port)
                        
                        if left_motor.is_running:
                            corrected_velocity = velocity + correction
                            left_motor.target_velocity = corrected_velocity
                        
                        if right_motor.is_running:
                            corrected_velocity = -velocity + correction
                            right_motor.target_velocity = corrected_velocity
                    
                    elif correction_mode == 'velocity':
                        # For move_for_time - direct motor speed adjustment
                        corrected_left_velocity = velocity + correction
                        corrected_right_velocity = -velocity + correction
                        
                        motor.run(self.left_port, int(corrected_left_velocity))
                        motor.run(self.right_port, int(corrected_right_velocity))
                        
            except Exception as e:
                # If orientation fails, continue without correction
                pass
        
        return yaw_error
    
    def move_for_degrees(self, degrees, steering=0, velocity=None):
        """Move for specified degrees with optional steering and straight-line correction"""
        if velocity is None:
            velocity = self.default_velocity
        
        # Initialize yaw reference for straight-line movement
        target_yaw = self._init_yaw_reference(steering)
            
        # Calculate movement for each wheel
        left_degrees = degrees
        right_degrees = degrees
        
        if steering != 0:
            # Adjust degrees for turning
            if steering > 0:  # Turn right
                right_degrees = degrees * (1 - abs(steering) / 100)
            else:  # Turn left
                left_degrees = degrees * (1 - abs(steering) / 100)
        
        # Get motor instances and reset positions
        left_motor = motor._get_motor(self.left_port)
        right_motor = motor._get_motor(self.right_port)
        
        # Reset relative positions for this movement
        start_left_position = left_motor.position
        start_right_position = right_motor.position
        target_left_position = start_left_position + left_degrees
        target_right_position = start_right_position + (-right_degrees)  # Right motor is reversed
        
        # Start both motors with continuous running
        motor.run(self.left_port, int(velocity))
        motor.run(self.right_port, int(-velocity))
        
        # Monitor position and apply corrections until target reached
        while True:
            # Check if both motors have reached their targets
            left_reached = abs(left_motor.position - target_left_position) <= 20
            right_reached = abs(right_motor.position - target_right_position) <= 20
            
            if left_reached or right_reached:
                break
            
            # Stop individual motors that have reached their target
            if left_reached and not left_motor.is_running == False:
                motor.stop(self.left_port)
            if right_reached and not right_motor.is_running == False:
                motor.stop(self.right_port)
            
            # Apply yaw correction using helper function (only if both motors still running)
            if not (left_reached and right_reached):
                yaw_error = self._apply_yaw_correction(steering, target_yaw, velocity, 'velocity')
            
            # print(f"Left: {left_motor.position:.1f}/{target_left_position:.1f}, Right: {right_motor.position:.1f}/{target_right_position:.1f}, Yaw: {yaw_error:.1f}")
            time.sleep_ms(10)
        
        # Ensure both motors are stopped
        self.stop()

    def move_for_time(self, time_ms, steering=0, velocity=None):
        """Move for specified time with steering and straight-line correction"""
        if velocity is None:
            velocity = self.default_velocity
        
        # Initialize yaw reference for straight-line movement
        target_yaw = self._init_yaw_reference(steering)
            
        # Start movement
        self.move(steering, velocity)
        
        left_motor = motor._get_motor(self.left_port)
        right_motor = motor._get_motor(self.right_port)
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < time_ms:
            # Apply yaw correction using helper function
            yaw_error = self._apply_yaw_correction(steering, target_yaw, velocity, 'velocity')
            
            time.sleep_ms(10)
        
        # Stop both motors
        self.stop()
    
    def stop(self):
        """Stop both motors"""
        motor.stop(self.left_port)
        motor.stop(self.right_port)
    
    def move_tank(self, left_velocity, right_velocity):
        """Tank-style movement with independent wheel control"""
        motor.run(self.left_port, int(left_velocity))
        motor.run(self.right_port, int(-right_velocity if self.right_reversed else right_velocity))
    
    def move_tank_for_degrees(self, degrees, left_velocity, right_velocity):
        """Turn robot by specified degrees using yaw feedback
        
        Args:
            degrees: Degrees to turn (positive = clockwise, negative = counter-clockwise)
            left_velocity: Velocity for left motor
            right_velocity: Velocity for right motor
        """
        if not self.orientation_sensor:
            # Fallback to original behavior if no orientation sensor
            print("Warning: No orientation sensor available, using motor degrees instead of yaw")
            motor.run_for_degrees(self.left_port, int(degrees), int(left_velocity), stop=False)
            motor.run_for_degrees(self.right_port, int(degrees), int(-right_velocity), stop=False)
            
            # Wait for both to complete
            while (motor._get_motor(self.left_port).is_running or 
                   motor._get_motor(self.right_port).is_running):
                time.sleep_ms(10)
            return
        
        # Initialize yaw reference
        self.orientation_sensor.update()
        start_yaw = self.orientation_sensor.get_yaw()
        target_yaw = start_yaw + degrees
        
        # Start tank movement
        motor.run(self.left_port, int(left_velocity))
        motor.run(self.right_port, int(-right_velocity if self.right_reversed else right_velocity))
        
        # Monitor yaw until target is reached
        tolerance = 3.0  # 3 degree tolerance
        timeout_ms = 10000  # 10 second timeout
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            # Update orientation
            self.orientation_sensor.update()
            current_yaw = self.orientation_sensor.get_yaw()
            
            # Calculate yaw error (handle wrap-around)
            yaw_error = target_yaw - current_yaw
            
            # Handle yaw wrap-around (crossing 180/-180 boundary)
            if yaw_error > 180:
                yaw_error -= 360
            elif yaw_error < -180:
                yaw_error += 360
            
            # Check if we've reached the target
            if abs(yaw_error) <= tolerance:
                break
            
            time.sleep_ms(10)
        
        # Stop both motors
        self.stop()
    
    def move_tank_for_time(self, time_ms, left_velocity, right_velocity):
        """Tank movement for specified time"""
        self.move_tank(left_velocity, right_velocity)
        time.sleep_ms(time_ms)
        self.stop()
    
    def get_orientation(self):
        """Get current orientation (roll, pitch, yaw) if sensor is available"""
        if self.orientation_sensor:
            return self.orientation_sensor.update()
        return None, None, None
    
    def get_yaw(self):
        """Get current yaw angle in degrees"""
        if self.orientation_sensor:
            self.orientation_sensor.update()
            return self.orientation_sensor.get_yaw()
        return 0
    
    def reset_yaw(self):
        """Reset yaw to zero (set current direction as reference)"""
        if self.orientation_sensor:
            self.orientation_sensor.reset_yaw()

# Global motor pairs
_motor_pairs = {}

def pair(pair_id, left_port, right_port):
    """Pair two motors together"""
    _motor_pairs[pair_id] = MotorPair(pair_id, left_port, right_port)

def unpair(pair_id):
    """Unpair motors"""
    if pair_id in _motor_pairs:
        del _motor_pairs[pair_id]

def _get_pair(pair_id):
    """Get motor pair instance"""
    if pair_id not in _motor_pairs:
        raise ValueError(f"Motor pair {pair_id} not paired")
    return _motor_pairs[pair_id]

# SPIKE Prime Motor Pair API Functions

def move(pair_id, steering, *, velocity=None):
    """Move with steering (-100 to 100, 0 = straight)"""
    pair = _get_pair(pair_id)
    pair.move(steering, velocity)

def move_for_degrees(pair_id, degrees, steering, *, velocity=None, stop=True):
    """Move for specified degrees with steering"""
    pair = _get_pair(pair_id)
    pair.move_for_degrees(degrees, steering, velocity)
    if stop:
        pair.stop()

def move_for_time(pair_id, time_ms, steering, *, velocity=None, stop=True):
    """Move for specified time with steering"""
    pair = _get_pair(pair_id)
    pair.move_for_time(time_ms, steering, velocity)
    if stop:
        pair.stop()

def move_tank(pair_id, left_velocity, right_velocity):
    """Tank-style movement with independent wheel speeds"""
    pair = _get_pair(pair_id)
    pair.move_tank(left_velocity, right_velocity)

def move_tank_for_degrees(pair_id, degrees, left_velocity, right_velocity, *, stop=True):
    """Tank movement for specified degrees"""
    pair = _get_pair(pair_id)
    pair.move_tank_for_degrees(degrees, left_velocity, right_velocity)
    if stop:
        pair.stop()

def move_tank_for_time(pair_id, time_ms, left_velocity, right_velocity, *, stop=True):
    """Tank movement for specified time"""
    pair = _get_pair(pair_id)
    pair.move_tank_for_time(time_ms, left_velocity, right_velocity)
    if stop:
        pair.stop()

def stop(pair_id):
    """Stop both motors in pair"""
    pair = _get_pair(pair_id)
    pair.stop()

def get_default_velocity(pair_id):
    """Get default velocity for pair"""
    pair = _get_pair(pair_id)
    return pair.default_velocity

def set_default_velocity(pair_id, velocity):
    """Set default velocity for pair"""
    pair = _get_pair(pair_id)
    pair.default_velocity = velocity

def set_motor_rotation(pair_id, degrees, motor="both"):
    """Set motor rotation (placeholder for compatibility)"""
    pass

def set_stop_action(pair_id, action="brake"):
    """Set stop action (placeholder for compatibility)"""
    pass
