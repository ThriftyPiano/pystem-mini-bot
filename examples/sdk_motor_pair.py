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

# Straight-line yaw hold (PID on yaw error, wheel deg/s per degree and per deg/s).
# The integral term is what cancels a constant left/right imbalance (a weak
# motor, one side dragging): P alone settles with a standing heading error.
# Gains are tuned LOW against the real robot (2026-10, BLE yaw telemetry on
# the StickS3 bot): the outer loop acts through each wheel's velocity loop,
# which measures speed over a ~200 ms window and slews at 300 dps/s, so a
# high-bandwidth outer loop corrects half a wiggle late and oscillates.
# KP=3/KI=8 wiggled +-20 degrees at 1 Hz on hardwood; these hold +-2.
# (The simulator's wheels respond instantly, so it tolerates far higher
# gains -- do not retune these against the simulator alone.)
YAW_KP = 0.6
YAW_KI = 0.5
YAW_KD = 0.8
YAW_MAX_CORRECTION = 40
# Yaw-feedback turns.
TURN_TOLERANCE_DEG = 3.0        # close enough to not start a correction move
TURN_STOP_DEG = 0.5             # once moving, creep until this close / crossing
TURN_COAST_DEG = 7.5            # the robot turns about this much more after the stop command
                                # (measured on the robot with the gyro sampled through stop():
                                # 7-8 degrees at 40 dps/wheel, 8-9 at 70; a rate-based estimate
                                # was tried and failed -- the creep is jerky and one spiky gyro
                                # sample stopped turns 10-16 degrees early)
TURN_SLOW_ZONE_DEG = 45.0   # start slowing this far from the target
TURN_MIN_SCALE = 0.25       # creep speed near the target, as a fraction of the commanded speed
TURN_MIN_DPS = 30           # but never slower than this per wheel (a slower wheel stalls on carpet)
TURN_RAMP_MS = 500          # speed ramps up from the creep speed over this time after each (re)start
TURN_TIMEOUT_MS = 15000
TURN_STALL_DEG = 2.0        # a yaw gain smaller than this does not count as progress
TURN_STALL_MS = 2500        # give up if no progress for this long (slipping/blocked)

# Telemetry for troubleshooting on the real robot (off by default, student
# programs stay quiet). With DEBUG = True every straight run prints
#   #S t=<ms> yaw=<deg> err=<deg> corr=<dps> L=<target>/<measured>/<pos>/<pwm%> R=...
# every DEBUG_PERIOD_MS, and every turn prints
#   #T t=<ms> yaw=<deg> err=<deg> scale=<-1..1> L=... R=...
# Each move ends with a '#S END' / '#T END' line giving the exit reason, the
# time taken, the yaw change and the encoder travel, so a run that went wrong
# (a turn that spun past its target, a straight that curved, a wheel that
# never reached its speed) shows up in the robot's own output.
DEBUG = False
DEBUG_PERIOD_MS = 200

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
        # and turns add to it, so the error a turn leaves is corrected by
        # the next straight run instead of accumulating. A free movement
        # (steering, tank) makes it unknown; it is re-read from the sensor
        # afterwards.
        self.target_heading = 0.0
        self._heading_unknown = False
        self._yaw_integral = 0.0
        self._yaw_last_ms = time.ticks_ms()
        self._last_correction = 0.0
        self._debug_next_ms = 0

        self.orientation_sensor = None
        if use_orientation and HAS_ORIENTATION:
            try:
                self.orientation_sensor = OrientationSensor()
            except Exception as e:
                print(f"Failed to initialize orientation sensor: {e}")
                self.orientation_sensor = None
        if self.orientation_sensor and hasattr(motor, 'set_idle_hook'):
            # keep the yaw integrating while the motors' stop() sleeps (the
            # robot is still coasting then); the simulator's shim has no hook
            motor.set_idle_hook(self._idle_sampling)

    def _idle_sampling(self, ms):
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < ms:
            self._current_yaw()
            time.sleep_ms(5)

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

    # ---- telemetry (see DEBUG above)

    def _debug_due(self, now):
        if not DEBUG or time.ticks_diff(now, self._debug_next_ms) < DEBUG_PERIOD_MS:
            return False
        self._debug_next_ms = now
        return True

    def _debug_wheels(self):
        """Per wheel: target dps / measured dps / encoder position / PWM %.
        Measured far below target with the PWM pinned at 100 means the loop
        is winding up against a wheel it cannot see moving -- a stalled
        wheel, or an encoder that has stopped delivering pulses."""
        l = motor._get_motor(self.left_port)
        r = motor._get_motor(self.right_port)
        # getattr: the simulator's motor shim has no velocity loop
        return "L=%d/%d/%d/%d%% R=%d/%d/%d/%d%%" % (
            l.target_velocity, getattr(l, 'measured_velocity', 0), l.position, l.current_speed,
            r.target_velocity, getattr(r, 'measured_velocity', 0), r.position, r.current_speed)

    def _debug_gap_reset(self, now):
        self._max_gap = [0, 0]
        self._gap_start = now

    def _debug_gap_track(self, now):
        """Longest silence between encoder pulses on each wheel while it is
        being driven (counted from the start of this move): evidence for or
        against a flaky encoder connection."""
        for i, port in enumerate((self.left_port, self.right_port)):
            m = motor._get_motor(port)
            last = getattr(m, 'last_pulse_time', None)
            if m.current_speed != 0 and last is not None:
                gap = min(time.ticks_diff(now, last),
                          time.ticks_diff(now, self._gap_start))
                if gap > self._max_gap[i]:
                    self._max_gap[i] = gap

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
        self._yaw_integral = 0.0
        self._yaw_last_ms = time.ticks_ms()
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

                now = time.ticks_ms()
                dt = time.ticks_diff(now, self._yaw_last_ms) / 1000.0
                self._yaw_last_ms = now
                if 0 < dt < 0.5:
                    self._yaw_integral += yaw_error * dt
                    limit = YAW_MAX_CORRECTION / YAW_KI
                    self._yaw_integral = max(-limit, min(limit, self._yaw_integral))

                correction = (yaw_error * YAW_KP
                              + self._yaw_integral * YAW_KI
                              - self.orientation_sensor.yaw_rate * YAW_KD)
                correction = max(-YAW_MAX_CORRECTION, min(YAW_MAX_CORRECTION, correction))
                self._last_correction = correction
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
        """Closed loop on yaw: ramps up, slows down over the last degrees,
        reverses if it goes past the target while moving, and creeps all the
        way to the target before stopping. Stopping as soon as the error was
        inside a tolerance band left every turn systematically short by the
        whole band (the band is always entered from the approach side), so
        the tolerance only decides whether a turn is worth starting; a turn
        in progress ends at TURN_STOP_DEG / on crossing the target. It does
        not hunt after stopping: whatever the coast leaves is absorbed by the
        next straight run, which holds the same target heading.
        clockwise_sign is +1 when the given wheel velocities turn the robot
        clockwise (yaw increasing), -1 otherwise."""
        start_time = time.ticks_ms()
        direction = 0
        phase_start = start_time
        min_scale = TURN_MIN_SCALE
        top = max(abs(left_velocity), abs(right_velocity))
        if top > 0:
            min_scale = max(min_scale, min(1.0, TURN_MIN_DPS / top))

        # Stall guard: if the yaw stops getting closer to the target for
        # TURN_STALL_MS, the robot is not turning (wheels slipping, blocked by
        # a wall, a snagged cable) -- give up rather than drive in place until
        # the 15 s timeout, which on a low-grip floor is several full spins.
        start_yaw = self._current_yaw()
        best_err = abs(target_yaw - start_yaw)
        best_ms = start_time
        reason = "timeout"
        self._debug_next_ms = start_time
        self._debug_gap_reset(start_time)
        if DEBUG:
            print("#T START target=%.1f yaw=%.1f req=%.1f" % (
                target_yaw, start_yaw, target_yaw - start_yaw))

        while time.ticks_diff(time.ticks_ms(), start_time) < TURN_TIMEOUT_MS:
            yaw_error = target_yaw - self._current_yaw()

            if abs(yaw_error) < best_err - TURN_STALL_DEG:
                best_err = abs(yaw_error)
                best_ms = time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), best_ms) > TURN_STALL_MS:
                print("TURN STALLED: not progressing, giving up")
                reason = "stalled"
                break

            if direction == 0:
                # Not moving yet: already close enough to not bother.
                if abs(yaw_error) <= TURN_TOLERANCE_DEG:
                    reason = "close"
                    break
            else:
                # Moving: stop when the remaining error (measured along the
                # direction being turned) is down to the coast, or crossed.
                if yaw_error * direction * clockwise_sign <= TURN_STOP_DEG + TURN_COAST_DEG:
                    reason = "reached"
                    break

            now = time.ticks_ms()
            wanted = clockwise_sign if yaw_error > 0 else -clockwise_sign
            if wanted != direction:
                direction = wanted
                phase_start = now
            ramp = min(1.0, time.ticks_diff(now, phase_start) / TURN_RAMP_MS)
            scale = min(1.0, abs(yaw_error) / TURN_SLOW_ZONE_DEG) * ramp
            scale = max(min_scale, scale) * direction
            self.move_tank(left_velocity * scale, right_velocity * scale, _free=False)

            if DEBUG:
                self._debug_gap_track(now)
            if self._debug_due(now):
                print("#T t=%d yaw=%.1f err=%.1f scale=%.2f %s" % (
                    time.ticks_diff(now, start_time), target_yaw - yaw_error,
                    yaw_error, scale, self._debug_wheels()))

            time.sleep_ms(10)

        self.stop()
        if reason in ("stalled", "timeout"):
            # The turn did not get there: the target heading is now a
            # fiction. Re-read it before the next move, or that move holds
            # a heading the robot never reached and drives in an arc.
            self._heading_unknown = True
        if DEBUG:
            time.sleep_ms(200)      # let the coast settle before the final read
            net = self._current_yaw() - start_yaw
            req = target_yaw - start_yaw
            flag = ""
            if abs(net) > abs(req) + 180:
                flag = " SPIN: turned %.0f for a %.0f request" % (net, req)
            elif abs(req) > TURN_TOLERANCE_DEG and net * req < 0 and abs(net) > TURN_TOLERANCE_DEG:
                flag = " WRONG WAY: turned %.0f for a %.0f request" % (net, req)
            print("#T END reason=%s ms=%d req=%.1f net=%.1f left=%.1f gapL=%d gapR=%d%s" % (
                reason, time.ticks_diff(time.ticks_ms(), start_time), req, net,
                target_yaw - self._current_yaw(), self._max_gap[0], self._max_gap[1], flag))

    # ---- moves

    def move_for_degrees(self, degrees, steering=0, velocity=None):
        if velocity is None:
            velocity = self.default_velocity
        velocity = abs(velocity)

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

        # Negative degrees drive backwards: the wheels must run towards the
        # targets, not at +velocity regardless -- otherwise the targets
        # recede and the loop never exits (a runaway).
        signed_velocity = velocity if degrees >= 0 else -velocity
        motor.run(self.left_port, int(signed_velocity))
        motor.run(self.right_port, int(-signed_velocity))

        # "Reached" is at or past the target in the direction of travel: a
        # fast wheel can step over a window around the target between reads.
        left_dir = 1 if target_left_position >= start_left_position else -1
        right_dir = 1 if target_right_position >= start_right_position else -1
        # Belt and braces: even a stalled wheel ends the move eventually.
        timeout_ms = int(abs(degrees) / max(velocity, 1) * 3000) + 2000
        start_time = time.ticks_ms()
        start_yaw = self._current_yaw()
        reason = "timeout"
        self._debug_next_ms = start_time
        self._debug_gap_reset(start_time)
        if DEBUG:
            print("#S START deg=%d v=%d target_yaw=%.1f yaw=%.1f" % (
                degrees, signed_velocity, target_yaw, start_yaw))
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            left_reached = (left_motor.position - target_left_position) * left_dir >= -20
            right_reached = (right_motor.position - target_right_position) * right_dir >= -20

            # An encoder the velocity loop has flagged as spurious (see
            # motor.ENCODER_PLAUSIBLE_DPS) races ahead of the wheel; letting
            # it end the move cut a 400 mm run to 53 mm. Unless both are
            # suspect, only the trusted wheel decides.
            left_ok = not getattr(left_motor, 'encoder_suspect', False)
            right_ok = not getattr(right_motor, 'encoder_suspect', False)
            if not (left_ok or right_ok):
                left_ok = right_ok = True
            if (left_reached and left_ok) or (right_reached and right_ok):
                reason = "left" if (left_reached and left_ok) else "right"
                break

            yaw_error = self._apply_yaw_correction(steering, target_yaw, signed_velocity, 'velocity')

            now = time.ticks_ms()
            if DEBUG:
                self._debug_gap_track(now)
            if self._debug_due(now):
                print("#S t=%d yaw=%.1f err=%.1f corr=%.1f %s" % (
                    time.ticks_diff(now, start_time), target_yaw - yaw_error,
                    yaw_error, self._last_correction, self._debug_wheels()))

            time.sleep_ms(10)
        else:
            print("TIMEOUT: Forcing stop.")

        self.stop()
        if DEBUG:
            time.sleep_ms(200)
            print("#S END reason=%s ms=%d drift=%.1f Lenc=%d Renc=%d of %d gapL=%d gapR=%d encfaultL=%d encfaultR=%d" % (
                reason, time.ticks_diff(time.ticks_ms(), start_time),
                self._current_yaw() - start_yaw,
                left_motor.position - start_left_position,
                right_motor.position - start_right_position, degrees,
                self._max_gap[0], self._max_gap[1],
                getattr(left_motor, 'encoder_faults', 0), getattr(right_motor, 'encoder_faults', 0)))

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

    def stop(self):
        motor.stop_all(self.left_port, self.right_port)
        # Keep the yaw integration continuous across the stop: stop_all
        # sleeps while the servos brake, and the first read after that gap
        # must not carry the stop jerk over the whole gap.
        if self.orientation_sensor:
            self._current_yaw()

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
        # The turning sense of the wheel velocities, not of `degrees`: a
        # left-forward/right-backward pair turns clockwise whichever way the
        # caller wants to go, and _turn_to_heading flips the pair itself when
        # the target lies the other way. Deriving it from `degrees` (as this
        # once did) made move_tank_for_degrees(-60, 70, -70) drive clockwise
        # with an ever-growing error: a full-circle spin until the timeout.
        if left_velocity != right_velocity:
            clockwise_sign = 1 if left_velocity > right_velocity else -1
        else:
            clockwise_sign = 1 if degrees >= 0 else -1
        self._turn_to_heading(self.target_heading, left_velocity, right_velocity,
                              clockwise_sign)

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
