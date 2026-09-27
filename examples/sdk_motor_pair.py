# filename: motor_pair.py
# SPIKE Prime compatible motor pair module: differential drive with
# IMU-based straight-line correction and yaw-based turns.

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

PAIR_1 = 1
PAIR_2 = 2
PAIR_3 = 3

class MotorPair:
    def __init__(self, pair_id, left_port, right_port, use_orientation=True):
        self.pair_id = pair_id
        self.left_port = left_port
        self.right_port = right_port
        self.wheel_circumference = MOTOR_CONFIG['wheel_diameter_cm'] * math.pi
        self.wheel_distance = MOTOR_CONFIG['wheel_distance_cm']
        self.default_velocity = MOTOR_CONFIG['default_speed_dps']
        self.left_reversed = False
        self.right_reversed = True

        self.orientation_sensor = None
        if use_orientation and HAS_ORIENTATION:
            try:
                self.orientation_sensor = OrientationSensor()
                print("Orientation sensor initialized for straight-line correction")
            except Exception as e:
                print(f"Failed to initialize orientation sensor: {e}")
                self.orientation_sensor = None

    def _get_motor_velocity(self, velocity, is_right_motor=False):
        return velocity

    def _get_motor_degrees(self, degrees, is_right_motor=False):
        if is_right_motor and self.right_reversed:
            return -degrees
        elif not is_right_motor and self.left_reversed:
            return -degrees
        return degrees

    def move(self, steering, velocity=None):
        """Move with steering: -100 (full left) to 100 (full right), 0 = straight."""
        if velocity is None:
            velocity = self.default_velocity

        left_velocity = velocity
        right_velocity = velocity

        if steering != 0:
            if steering > 0:
                left_velocity = velocity
                right_velocity = velocity * (1 - abs(steering) / 100)
            else:
                left_velocity = velocity * (1 - abs(steering) / 100)
                right_velocity = velocity

        motor.run(self.left_port, int(left_velocity))
        motor.run(self.right_port, int(-right_velocity if self.right_reversed else right_velocity))

    def _init_yaw_reference(self, steering):
        target_yaw = 0
        if self.orientation_sensor and steering == 0:
            self.orientation_sensor.update()
            self.orientation_sensor.reset_yaw()
            target_yaw = 0
        return target_yaw

    def _apply_yaw_correction(self, steering, target_yaw, velocity, correction_mode='position'):
        yaw_error = 0
        if self.orientation_sensor and steering == 0:
            try:
                self.orientation_sensor.update()
                current_yaw = self.orientation_sensor.get_yaw()
                yaw_error = target_yaw - current_yaw

                # Re-applied every call, no dead band: a correction left on
                # the motors inside a dead band drives S-curves.
                correction = yaw_error * 10
                correction = max(-60, min(60, correction))
                if abs(yaw_error) <= 0.5:
                    correction = 0
                if correction_mode == 'position':
                    left_motor = motor._get_motor(self.left_port)
                    right_motor = motor._get_motor(self.right_port)

                    if left_motor.is_running:
                        corrected_velocity = velocity + correction
                        left_motor.target_velocity = corrected_velocity

                    if right_motor.is_running:
                        corrected_velocity = -velocity + correction
                        right_motor.target_velocity = corrected_velocity

                elif correction_mode == 'velocity':
                    corrected_left_velocity = velocity + correction
                    corrected_right_velocity = -velocity + correction

                    motor.run(self.left_port, int(corrected_left_velocity))
                    motor.run(self.right_port, int(corrected_right_velocity))

            except Exception as e:
                pass

        return yaw_error

    def move_for_degrees(self, degrees, steering=0, velocity=None):
        if velocity is None:
            velocity = self.default_velocity

        target_yaw = self._init_yaw_reference(steering)

        left_degrees = degrees
        right_degrees = degrees

        if steering != 0:
            if steering > 0:
                right_degrees = degrees * (1 - abs(steering) / 100)
            else:
                left_degrees = degrees * (1 - abs(steering) / 100)

        left_motor = motor._get_motor(self.left_port)
        right_motor = motor._get_motor(self.right_port)

        start_left_position = left_motor.position
        start_right_position = right_motor.position
        target_left_position = start_left_position + left_degrees
        target_right_position = start_right_position + (-right_degrees)

        motor.run(self.left_port, int(velocity))
        motor.run(self.right_port, int(-velocity))

        # "Reached" is at or past the target in the direction of travel: a
        # fast wheel can step over a window around the target between reads.
        left_dir = 1 if target_left_position >= start_left_position else -1
        right_dir = 1 if target_right_position >= start_right_position else -1
        while True:
            left_reached = (left_motor.position - target_left_position) * left_dir >= -20
            right_reached = (right_motor.position - target_right_position) * right_dir >= -20

            if left_reached or right_reached:
                break

            if left_reached and not left_motor.is_running == False:
                motor.stop(self.left_port)
            if right_reached and not right_motor.is_running == False:
                motor.stop(self.right_port)

            if not (left_reached and right_reached):
                yaw_error = self._apply_yaw_correction(steering, target_yaw, velocity, 'velocity')

            time.sleep_ms(10)

        self.stop()

    def move_for_time(self, time_ms, steering=0, velocity=None):
        if velocity is None:
            velocity = self.default_velocity

        target_yaw = self._init_yaw_reference(steering)

        self.move(steering, velocity)

        left_motor = motor._get_motor(self.left_port)
        right_motor = motor._get_motor(self.right_port)
        start_time = time.ticks_ms()

        while time.ticks_diff(time.ticks_ms(), start_time) < time_ms:
            yaw_error = self._apply_yaw_correction(steering, target_yaw, velocity, 'velocity')

            time.sleep_ms(10)

        self.stop()

    def stop(self):
        motor.stop(self.left_port)
        motor.stop(self.right_port)

    def move_tank(self, left_velocity, right_velocity):
        motor.run(self.left_port, int(left_velocity))
        motor.run(self.right_port, int(-right_velocity if self.right_reversed else right_velocity))

    def move_tank_for_degrees(self, degrees, left_velocity, right_velocity):
        """Turn by `degrees` of yaw (positive = clockwise)."""
        if not self.orientation_sensor:
            print("Warning: No orientation sensor available, using motor degrees instead of yaw")
            motor.run_for_degrees(self.left_port, int(degrees), int(left_velocity), stop=False)
            motor.run_for_degrees(self.right_port, int(degrees), int(-right_velocity), stop=False)

            while (motor._get_motor(self.left_port).is_running or
                   motor._get_motor(self.right_port).is_running):
                time.sleep_ms(10)
            return

        self.orientation_sensor.update()
        start_yaw = self.orientation_sensor.get_yaw()
        target_yaw = start_yaw + degrees

        # Closed loop on yaw: slow down near the target, reverse if it
        # overshoots, and re-check once stopped so momentum cannot leave
        # the robot outside the tolerance.
        tolerance = 3.0
        slow_zone = 30.0
        min_scale = 0.35
        timeout_ms = 10000
        start_time = time.ticks_ms()
        moving = False

        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            self.orientation_sensor.update()
            current_yaw = self.orientation_sensor.get_yaw()

            yaw_error = target_yaw - current_yaw

            if yaw_error > 180:
                yaw_error -= 360
            elif yaw_error < -180:
                yaw_error += 360

            if abs(yaw_error) <= tolerance:
                if moving:
                    self.stop()
                    moving = False
                    time.sleep_ms(200)
                    continue
                break

            direction = 1 if (yaw_error > 0) == (degrees > 0) else -1
            scale = max(min_scale, min(1.0, abs(yaw_error) / slow_zone)) * direction
            self.move_tank(left_velocity * scale, right_velocity * scale)
            moving = True

            time.sleep_ms(10)

        self.stop()

    def move_tank_for_time(self, time_ms, left_velocity, right_velocity):
        self.move_tank(left_velocity, right_velocity)
        time.sleep_ms(time_ms)
        self.stop()

    def get_orientation(self):
        if self.orientation_sensor:
            return self.orientation_sensor.update()
        return None, None, None

    def get_yaw(self):
        if self.orientation_sensor:
            self.orientation_sensor.update()
            return self.orientation_sensor.get_yaw()
        return 0

    def reset_yaw(self):
        if self.orientation_sensor:
            self.orientation_sensor.reset_yaw()

_motor_pairs = {}

def pair(pair_id, left_port, right_port):
    _motor_pairs[pair_id] = MotorPair(pair_id, left_port, right_port)

def unpair(pair_id):
    if pair_id in _motor_pairs:
        del _motor_pairs[pair_id]

def _get_pair(pair_id):
    if pair_id not in _motor_pairs:
        raise ValueError(f"Motor pair {pair_id} not paired")
    return _motor_pairs[pair_id]

# --- SPIKE Prime API ---

def move(pair_id, steering, *, velocity=None):
    pair = _get_pair(pair_id)
    pair.move(steering, velocity)

def move_for_degrees(pair_id, degrees, steering, *, velocity=None, stop=True):
    pair = _get_pair(pair_id)
    pair.move_for_degrees(degrees, steering, velocity)
    if stop:
        pair.stop()

def move_for_time(pair_id, time_ms, steering, *, velocity=None, stop=True):
    pair = _get_pair(pair_id)
    pair.move_for_time(time_ms, steering, velocity)
    if stop:
        pair.stop()

def move_tank(pair_id, left_velocity, right_velocity):
    pair = _get_pair(pair_id)
    pair.move_tank(left_velocity, right_velocity)

def move_tank_for_degrees(pair_id, degrees, left_velocity, right_velocity, *, stop=True):
    pair = _get_pair(pair_id)
    pair.move_tank_for_degrees(degrees, left_velocity, right_velocity)
    if stop:
        pair.stop()

def move_tank_for_time(pair_id, time_ms, left_velocity, right_velocity, *, stop=True):
    pair = _get_pair(pair_id)
    pair.move_tank_for_time(time_ms, left_velocity, right_velocity)
    if stop:
        pair.stop()

def stop(pair_id):
    pair = _get_pair(pair_id)
    pair.stop()

def get_default_velocity(pair_id):
    pair = _get_pair(pair_id)
    return pair.default_velocity

def set_default_velocity(pair_id, velocity):
    pair = _get_pair(pair_id)
    pair.default_velocity = velocity

def set_motor_rotation(pair_id, degrees, motor="both"):
    pass

def set_stop_action(pair_id, action="brake"):
    pass
