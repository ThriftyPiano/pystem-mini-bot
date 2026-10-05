# filename: motor.py
# SPIKE Prime compatible motor module: continuous-rotation servos with
# single-channel encoders, closed-loop velocity and position control.

from machine import Pin, PWM, Timer
import time
import math
from config import MOTOR_PINS, MOTOR_CONFIG

PORT_A = 'A'
PORT_B = 'B'
PORT_C = 'C'
PORT_D = 'D'
PORT_E = 'E'
PORT_F = 'F'

VELOCITY_WINDOW_TICKS = 4   # x control_loop_ms

# Per-wheel velocity loop (feedforward + PI on measured speed). The
# feedforward does the bulk of the work; the PI only trims. These are low
# on purpose: the speed measurement lags ~200 ms (the window below, needed
# because one 50 ms tick sees only ~1 encoder pulse at cruise), so an
# aggressive integral winds up and oscillates against that lag -- a single
# wheel commanded 150 dps swung between 20 and 270 dps with ki=1.5.
# Tuned on the real robot (2026-10, BLE telemetry).
VELOCITY_KP = 0.12
VELOCITY_KI = 0.10
# Weight of each fresh windowed sample in the measured-velocity EMA; 1.0
# disables the extra smoothing. The windowed speed is quantised to ~45 dps
# steps (one encoder pulse per ~45 dps over the window), so a little EMA
# keeps that quantisation noise out of the correction without much lag.
VELOCITY_MEAS_ALPHA = 0.6
# A measured speed this far above the commanded one cannot come from the
# drive (the loop only ever pushes towards the target); it is an encoder
# fault and is not fed back.
ENCODER_PLAUSIBLE_DPS = 150
# Anti-stiction (see _velocity_control): with no encoder pulse for this long
# while commanded, the integral is bumped by STALL_KICK (dps*s; x VELOCITY_KI
# = 1.5% PWM) every control tick until the wheel moves.
STALL_KICK_MS = 150
STALL_KICK = 15.0
# No pulse for this long while driven above the feedforward: give up on the
# encoder for this run (see _velocity_control).
ENCODER_SILENT_MS = 700

CLOCKWISE = 1
COUNTERCLOCKWISE = -1
SHORTEST_PATH = 0
LONGEST_PATH = 1

class Motor:
    def __init__(self, port, servo_pin, encoder_pin):
        self.port = port
        self.servo_pin = servo_pin
        self.encoder_pin = encoder_pin

        self.pwm = PWM(Pin(servo_pin))
        self.pwm.freq(50)

        self.encoder = Pin(encoder_pin, Pin.IN, Pin.PULL_UP)

        self.position = 0
        self.pulse_count = 0
        self.last_pulse_time = time.ticks_ms()
        self.velocity = 0
        self.direction = 1

        self.target_position = 0
        self.target_velocity = MOTOR_CONFIG['default_speed_dps']
        self.is_running = False
        self.current_speed = 0
        self.control_mode = 'idle'   # 'idle' | 'velocity' | 'position'
        self.velocity_integral = 0.0
        self.measured_velocity = 0.0
        # Set when the encoder reports an impossible speed, or none at all,
        # during a run (see _velocity_control); cleared when the next run
        # starts. A paired move does not let a suspect encoder decide the
        # distance.
        self.encoder_suspect = False
        self.encoder_faults = 0
        # last (PWM %, dps) pair at which the loop held its speed
        self._good_percent = None
        self._good_dps = 0
        # (position, ticks_ms) of the last few control ticks: velocity is
        # measured over ~200 ms because one tick sees only ~2 pulses.
        self._pos_hist = None
        # Slew-limited target the velocity loop tracks, so both wheels
        # accelerate together on a step input.
        self._ramped_target = 0.0

        self.encoder.irq(trigger=Pin.IRQ_RISING, handler=self._encoder_callback)

        timer_id = ord(port) - ord('A')
        if timer_id < 0 or timer_id > 3:
            raise ValueError("Only ports A-D are supported.")
        self.control_timer = Timer(timer_id)

        self._set_servo_speed(0)

    def _encoder_callback(self, pin):
        current_time = time.ticks_ms()

        # 5 ms debounce
        if time.ticks_diff(current_time, self.last_pulse_time) < 5:
            return

        self.pulse_count += 1

        degrees_per_pulse = 360 / MOTOR_CONFIG['pulses_per_revolution']
        self.position += self.direction * degrees_per_pulse

        dt = time.ticks_diff(current_time, self.last_pulse_time) / 1000.0
        if dt > 0:
            self.velocity = degrees_per_pulse / dt * self.direction

        self.last_pulse_time = current_time

    def _set_servo_speed(self, speed):
        """Set speed in percent; 0 cuts the PWM signal (hard stop)."""

        if speed == 0:
            self.direction = 0
            self.current_speed = 0
            self.pwm.duty_u16(0)
            return

        self.pwm.freq(50)
        pulse_width = int(1500 + (speed * 5))
        pulse_width = max(1000, min(2000, pulse_width))

        self.direction = 1 if speed > 0 else -1

        duty = int((pulse_width / 20000) * 1023)
        self.pwm.duty_u16(int(duty * 64))
        self.current_speed = speed

    def _position_control(self, timer):
        if not self.is_running:
            self._set_servo_speed(0)
            self.control_timer.deinit()
            return

        current_pos_snapshot = self.position
        error = self.target_position - current_pos_snapshot

        if abs(error) <= 30:
            self.is_running = False
            self._set_servo_speed(0)
            self.control_timer.deinit()
            return

        kp = 0.8
        speed_command = error * kp

        max_user_speed = abs(self.target_velocity / (MOTOR_CONFIG['max_speed_dps'] / 100))
        if speed_command > 0:
            final_speed = min(speed_command, max_user_speed)
        else:
            final_speed = max(speed_command, -max_user_speed)

        # 15% minimum power so the motor does not stall
        if abs(final_speed) < 15:
            final_speed = 15 if final_speed > 0 else -15

        self._set_servo_speed(final_speed)

    def _velocity_control(self, timer):
        if not self.is_running:
            self._set_servo_speed(0)
            self.control_timer.deinit()
            return

        commanded = self.target_velocity
        dt = MOTOR_CONFIG['control_loop_ms'] / 1000.0

        RAMP_RATE = 300.0   # dps per second
        max_step = RAMP_RATE * dt
        err_t = commanded - self._ramped_target
        if abs(err_t) <= max_step:
            self._ramped_target = commanded
        elif err_t > 0:
            self._ramped_target += max_step
        else:
            self._ramped_target -= max_step

        if commanded == 0 and self._ramped_target == 0:
            self._set_servo_speed(0)
            self.velocity_integral = 0.0
            return

        target = self._ramped_target

        now = time.ticks_ms()
        pos = self.position
        hist = self._pos_hist
        if hist is None:
            hist = self._pos_hist = [(pos, now)] * VELOCITY_WINDOW_TICKS
            inst = 0.0
        else:
            old_pos, old_t = hist.pop(0)
            hist.append((pos, now))
            dt_win = time.ticks_diff(now, old_t) / 1000.0
            inst = (pos - old_pos) / dt_win if dt_win > 0 else 0.0
        a = VELOCITY_MEAS_ALPHA
        self.measured_velocity = (1.0 - a) * self.measured_velocity + a * inst
        measured = self.measured_velocity

        max_dps = MOTOR_CONFIG['max_speed_dps']
        ff_percent = target / (max_dps / 100.0)

        silent_ms = time.ticks_diff(now, self.last_pulse_time)
        # a healthy wheel at `target` pulses every 360/ppr/target seconds
        pulse_ms = 360000.0 / MOTOR_CONFIG['pulses_per_revolution'] / max(abs(target), 1.0)
        if (silent_ms > max(ENCODER_SILENT_MS, 3 * pulse_ms)
                and abs(self.current_speed) >= abs(ff_percent) + 10):
            # Commanded, driven well above the feedforward, and not a single
            # pulse in ENCODER_SILENT_MS: the wheel is blocked, or the
            # encoder has gone quiet (seen on the real robot: the left
            # encoder dropped out for 14 s mid-run). Winding up further
            # only drives an unmeasured wheel to full power -- that run
            # swung the robot 116 degrees on a "straight" -- so hold the
            # feedforward open-loop and flag the encoder instead.
            self.encoder_faults += 1
            if not self.encoder_suspect:
                self.encoder_suspect = True
                print("ENCODER SILENT %s: no pulses for %d ms at %d%% PWM (%d dps commanded)"
                      % (self.port, silent_ms, self.current_speed, target))
            self.velocity_integral = 0.0
            # Drive open loop at the PWM that last held the commanded speed
            # while the encoder still worked (scaled to the current
            # target), not the nominal feedforward: these servos are far
            # from linear (the left one makes 115 dps at 10%), so on the
            # real robot the nominal value sent a wheel off at twice the
            # speed of its partner and the "straight" curved 47 degrees.
            if self._good_percent is not None and self._good_dps:
                new_percent = self._good_percent * target / self._good_dps
            else:
                new_percent = ff_percent
        elif abs(measured) > abs(target) + ENCODER_PLAUSIBLE_DPS:
            # The encoder reports a speed the drive cannot have produced:
            # spurious pulses (seen on the real robot: 335 dps "measured" on
            # a wheel the loop had already cut to its PWM floor). Trusting it
            # locks the loop off -- the wheel stays dead because the phantom
            # speed keeps the output at the floor -- so run this tick on
            # feedforward alone and flag the encoder for the move.
            self.encoder_faults += 1
            if not self.encoder_suspect:
                self.encoder_suspect = True
                print("ENCODER FAULT %s: %d dps reported with %d dps commanded at %d%% PWM"
                      % (self.port, measured, target, self.current_speed))
            new_percent = ff_percent
        else:
            error = target - measured
            self.velocity_integral += error * dt
            # Stiction kick: a wheel that is commanded but has not pulsed
            # for STALL_KICK_MS is stuck below its break-away PWM (seen on
            # the real robot: the right servo needs ~17% to move, the left
            # ~10%, and a 30 dps creep feeds forward only 5.5%). The plain
            # integral takes seconds to climb that far, during which a turn
            # proceeds in one-wheel jerks and translates the robot. Wind up
            # faster while stalled; once pulses resume the normal error
            # winds it back.
            if time.ticks_diff(now, self.last_pulse_time) > STALL_KICK_MS:
                self.velocity_integral += STALL_KICK * (1 if target > 0 else -1)
            self.velocity_integral = max(-200, min(200, self.velocity_integral))

            kp = VELOCITY_KP
            ki = VELOCITY_KI
            correction = error * kp + self.velocity_integral * ki

            new_percent = ff_percent + correction
            # remember what PWM actually produces this speed (used if the
            # encoder drops out later in the run)
            if abs(target) > 20 and abs(error) < 0.3 * abs(target):
                self._good_percent = self.current_speed
                self._good_dps = target
        # PWM keeps the sign of the target: the single-channel encoder
        # cannot see a direction flip.
        if target > 0.1:
            new_percent = max(0.5, min(100, new_percent))
        elif target < -0.1:
            new_percent = max(-100, min(-0.5, new_percent))
        else:
            new_percent = 0
        self._set_servo_speed(new_percent)

    def stop(self):
        self.is_running = False
        self.control_mode = 'idle'
        self.velocity_integral = 0.0
        self.measured_velocity = 0.0
        self._ramped_target = 0.0
        self.velocity = 0
        self.control_timer.deinit()
        self._set_servo_speed(0)
        time.sleep_ms(50)
        self._set_servo_speed(0)
        time.sleep_ms(50)
        self._set_servo_speed(0)
        return

_motors = {}

def _get_motor(port):
    if port not in _motors:
        if port in MOTOR_PINS:
            pins = MOTOR_PINS[port]
            _motors[port] = Motor(port, pins['servo'], pins['encoder'])
        else:
            raise ValueError(f"Invalid port: {port}")
    return _motors[port]

# --- API Functions ---

def run(port, velocity, *, acceleration=1000):
    motor = _get_motor(port)
    motor.target_velocity = velocity
    if velocity == 0:
        motor.stop()
        return
    if motor.control_mode != 'velocity':
        motor.velocity_integral = 0.0
        motor.measured_velocity = 0.0
        motor._ramped_target = 0.0
        motor._pos_hist = None
        motor.encoder_suspect = False
        motor.encoder_faults = 0
        # The silence/stiction timers count from the start of this run,
        # not from the last pulse of the previous one.
        motor.last_pulse_time = time.ticks_ms()
        motor.control_timer.deinit()
        motor.control_mode = 'velocity'
        motor.is_running = True
        motor.control_timer.init(
            period=MOTOR_CONFIG['control_loop_ms'],
            mode=Timer.PERIODIC,
            callback=motor._velocity_control)
    else:
        motor.is_running = True

def run_for_degrees(port, degrees, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    motor = _get_motor(port)

    start_position = motor.position
    motor.target_position = start_position + degrees
    motor.target_velocity = velocity
    motor.is_running = True

    motor.control_timer.deinit()
    motor.control_mode = 'position'
    motor.control_timer.init(period=MOTOR_CONFIG['control_loop_ms'], mode=Timer.PERIODIC, callback=motor._position_control)

    start_time = time.ticks_ms()

    if stop:
        while motor.is_running:
            time.sleep_ms(10)
            if time.ticks_diff(time.ticks_ms(), start_time) > 5000:
                print("TIMEOUT: Forcing stop.")
                motor.stop()
                break

def run_for_time(port, time_ms, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    motor = _get_motor(port)
    speed_percent = max(-100, min(100, velocity / (MOTOR_CONFIG['max_speed_dps'] / 100)))
    motor._set_servo_speed(speed_percent)
    motor.is_running = True
    time.sleep_ms(time_ms)
    if stop:
        motor.stop()

def run_to_position(port, position, velocity, *, direction=SHORTEST_PATH, stop=True, acceleration=1000, deceleration=1000):
    motor = _get_motor(port)
    motor.target_position = position
    motor.target_velocity = velocity
    motor.is_running = True
    motor.control_timer.deinit()
    motor.control_mode = 'position'
    motor.control_timer.init(period=MOTOR_CONFIG['control_loop_ms'], mode=Timer.PERIODIC, callback=motor._position_control)

    start_time = time.ticks_ms()
    if stop:
        while motor.is_running:
            time.sleep_ms(10)
            if time.ticks_diff(time.ticks_ms(), start_time) > 5000:
                print("TIMEOUT: Forcing stop.")
                motor.stop()
                break

def run_to_degrees_counted(port, degrees, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    run_to_position(port, degrees, velocity, stop=stop, acceleration=acceleration, deceleration=deceleration)

def stop(port, *, stop=True):
    motor = _get_motor(port)
    motor.stop()

def stop_all(*ports):
    """Cut power to all the given motors at the same instant, then stop each."""
    for port in ports:
        _get_motor(port)._set_servo_speed(0)
    for port in ports:
        _get_motor(port).stop()

def reset_relative_position(port, position):
    motor = _get_motor(port)
    motor.position = position

def get_position(port):
    motor = _get_motor(port)
    return motor.position

def get_degrees_counted(port):
    return get_position(port)

def get_velocity(port):
    motor = _get_motor(port)
    return motor.velocity

def get_default_velocity(port):
    return MOTOR_CONFIG['default_speed_dps']

def set_degrees_counted(port, degrees_counted):
    reset_relative_position(port, degrees_counted)

def was_interrupted(port): return False
def was_stalled(port): return False
def get_duty_cycle(port):
    motor = _get_motor(port)
    return motor.current_speed

# Hold every configured motor at duty 0 from import: a floating servo pin
# can drift on noise after a soft reset.
for _port in MOTOR_PINS:
    _get_motor(_port)
