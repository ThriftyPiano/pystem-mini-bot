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

# Straight-line yaw hold (PD on yaw error, wheel deg/s per degree and per deg/s).
YAW_KP = 3.0
YAW_KD = 0.3
YAW_MAX_CORRECTION = 40
# Yaw-feedback turns.
TURN_TOLERANCE_DEG = 3.0
TURN_SLOW_ZONE_DEG = 45.0   # start slowing this far from the target
TURN_MIN_SCALE = 0.25       # creep speed near the target, as a fraction of the commanded speed
TURN_RAMP_MS = 500          # speed ramps up from the creep speed over this time after each (re)start
TURN_TIMEOUT_MS = 10000
HEADING_FIX_DPS = 60        # wheel speed used to square up after a straight run

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
        # The heading the robot is meant to be on: straight runs hold it
        # and turns add to it, so an error left by one move is corrected
        # by the next instead of accumulating. A free movement (steering,
        # tank) makes it unknown; it is re-read from the sensor afterwards.
        self.target_heading = 0.0
        self._heading_unknown = False

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

    # ---- heading bookkeeping

    def _current_yaw(self):
        sensor = self.orientation_sensor
        if sensor is None:
            return 0.0
        sensor.update()
        return sensor.get_yaw()

    def _settle_heading(self):
        if self.orientation_sensor and self._heading_unknown:
            self.target_heading = self._current_yaw()
            self._heading_unknown = False

    def _drive(self, steering, velocity):
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

    def move(self, steering, velocity=None):
        """Move with steering: -100 (full left) to 100 (full right), 0 = straight."""
        if velocity is None:
            velocity = self.default_velocity
        self._heading_unknown = True
        self._drive(steering, velocity)

    def _init_yaw_reference(self, steering):
        if self.orientation_sensor and steering == 0:
            self._settle_heading()
            return self.target_heading
        self._heading_unknown = True
        return 0

    def _apply_yaw_correction(self, steering, target_yaw, velocity, correction_mode='position'):
        yaw_error = 0
        if self.orientation_sensor and steering == 0:
            try:
                current_yaw = self._current_yaw()
                yaw_error = target_yaw - current_yaw

                correction = yaw_error * YAW_KP - self.orientation_sensor.yaw_rate * YAW_KD
                correction = max(-YAW_MAX_CORRECTION, min(YAW_MAX_CORRECTION, correction))
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

    def _turn_to_heading(self, target_yaw, left_velocity, right_velocity, clockwise_sign):
        """Closed loop on yaw: slows down near the target, reverses if it
        overshoots, and re-checks once stopped so momentum cannot leave the
        robot outside the tolerance. clockwise_sign is +1 when the given
        wheel velocities turn the robot clockwise (yaw increasing), -1 otherwise."""
        start_time = time.ticks_ms()
        moving = False
        direction = 0
        phase_start = start_time

        while time.ticks_diff(time.ticks_ms(), start_time) < TURN_TIMEOUT_MS:
            yaw_error = target_yaw - self._current_yaw()

            if abs(yaw_error) <= TURN_TOLERANCE_DEG:
                if moving:
                    self.stop()
                    moving = False
                    direction = 0
                    time.sleep_ms(200)
                    continue
                break

            now = time.ticks_ms()
            wanted = clockwise_sign if yaw_error > 0 else -clockwise_sign
            if wanted != direction:
                direction = wanted
                phase_start = now
            ramp = min(1.0, time.ticks_diff(now, phase_start) / TURN_RAMP_MS)
            scale = min(1.0, abs(yaw_error) / TURN_SLOW_ZONE_DEG) * ramp
            scale = max(TURN_MIN_SCALE, scale) * direction
            self.move_tank(left_velocity * scale, right_velocity * scale, _free=False)
            moving = True

            time.sleep_ms(10)

        self.stop()

    def _fix_heading(self):
        """After a straight run: square up to the target heading if the stop left it off."""
        if not self.orientation_sensor or self._heading_unknown:
            return
        if abs(self.target_heading - self._current_yaw()) > TURN_TOLERANCE_DEG:
            self._turn_to_heading(self.target_heading, HEADING_FIX_DPS, -HEADING_FIX_DPS, 1)

    # ---- moves

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

            self._apply_yaw_correction(steering, target_yaw, velocity, 'velocity')

            time.sleep_ms(10)

        self.stop()
        self._fix_heading()

    def move_for_time(self, time_ms, steering=0, velocity=None):
        if velocity is None:
            velocity = self.default_velocity

        target_yaw = self._init_yaw_reference(steering)

        self._drive(steering, velocity)

        start_time = time.ticks_ms()

        while time.ticks_diff(time.ticks_ms(), start_time) < time_ms:
            self._apply_yaw_correction(steering, target_yaw, velocity, 'velocity')

            time.sleep_ms(10)

        self.stop()
        self._fix_heading()

    def stop(self):
        motor.stop_all(self.left_port, self.right_port)

    def move_tank(self, left_velocity, right_velocity, _free=True):
        if _free:
            self._heading_unknown = True
        motor.run(self.left_port, int(left_velocity))
        motor.run(self.right_port, int(-right_velocity if self.right_reversed else right_velocity))

    def move_tank_for_degrees(self, degrees, left_velocity, right_velocity):
        """Turn by `degrees` of yaw (positive = clockwise) from the target heading."""
        if not self.orientation_sensor:
            print("Warning: No orientation sensor available, using motor degrees instead of yaw")
            motor.run_for_degrees(self.left_port, int(degrees), int(left_velocity), stop=False)
            motor.run_for_degrees(self.right_port, int(degrees), int(-right_velocity), stop=False)

            while (motor._get_motor(self.left_port).is_running or
                   motor._get_motor(self.right_port).is_running):
                time.sleep_ms(10)
            return

        self._settle_heading()
        self.target_heading += degrees
        self._turn_to_heading(self.target_heading, left_velocity, right_velocity,
                              1 if degrees >= 0 else -1)

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
            return self._current_yaw()
        return 0

    def reset_yaw(self):
        """Make the current direction the target heading (yaw 0)."""
        if self.orientation_sensor:
            self.orientation_sensor.reset_yaw()
        self.target_heading = 0.0
        self._heading_unknown = False

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
