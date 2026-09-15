# filename: motor.py  (GEARS simulator build)
# SPIKE Prime compatible motor API for the browser simulator. Same public
# functions and signatures as examples/sdk_motor.py, implemented on GEARS's
# simPython.Motor instead of PWM + encoder interrupts. motor_pair.py (the
# real on-device file) drives this through run/run_for_degrees/stop,
# _get_motor(), and the .position / .is_running / .target_velocity
# attributes of the Motor objects, so those are kept attribute-compatible.
import simPython
import time
from config import MOTOR_PINS, MOTOR_CONFIG, MOTOR_REVERSED

# Port constants
PORT_A = 'A'
PORT_B = 'B'
PORT_C = 'C'
PORT_D = 'D'
PORT_E = 'E'
PORT_F = 'F'

# Direction constants
CLOCKWISE = 1
COUNTERCLOCKWISE = -1
SHORTEST_PATH = 0
LONGEST_PATH = 1

# A tight Python loop never yields to the browser; sleeping even 1 ms
# inside every sensor read hands control back so the physics keeps
# stepping (GEARS's own ev3dev2 shim does the same).
_SENSOR_DELAY = 0.001
_WAIT_RUNNING_TIMEOUT_MS = 100
_MOVE_TIMEOUT_MS = 5000   # matches the on-device "TIMEOUT: Forcing stop."


class Motor:
    def __init__(self, port):
        if port not in MOTOR_PINS:
            raise ValueError("No motor on port " + repr(port))
        self.port = port
        self.wheel = simPython.Motor(MOTOR_PINS[port]['sim'])
        self.sign = -1 if MOTOR_REVERSED.get(port) else 1
        self.wheel.stop_action('brake')
        self.target_position = 0
        self.target_velocity = MOTOR_CONFIG['default_speed_dps']
        self.current_speed = 0

    # --- attributes motor_pair.py reads directly ---
    @property
    def position(self):
        time.sleep(_SENSOR_DELAY)
        return self.sign * int(self.wheel.position())

    @position.setter
    def position(self, value):
        self.wheel.position(int(self.sign * value))

    @property
    def velocity(self):
        time.sleep(_SENSOR_DELAY)
        return self.sign * self.wheel.speed()

    @property
    def is_running(self):
        time.sleep(_SENSOR_DELAY)
        state = self.wheel.state()
        return 'running' in state or 'ramping' in state

    # --- helpers ---
    def _set_speed(self, velocity):
        self.wheel.speed_sp(int(self.sign * velocity))

    def stop(self):
        self.wheel.command('stop')
        self.current_speed = 0

    def _wait_until_running(self):
        t0 = time.ticks_ms()
        while not self.is_running:
            if time.ticks_diff(time.ticks_ms(), t0) > _WAIT_RUNNING_TIMEOUT_MS:
                return
            time.sleep(0.005)

    def _wait_until_stopped(self):
        t0 = time.ticks_ms()
        while self.is_running:
            time.sleep(0.01)
            if time.ticks_diff(time.ticks_ms(), t0) > _MOVE_TIMEOUT_MS:
                print("TIMEOUT: Forcing stop.")
                self.stop()
                return


_motors = {}

def _get_motor(port):
    if port not in _motors:
        _motors[port] = Motor(port)
    return _motors[port]


def run(port, velocity, *, acceleration=1000):
    m = _get_motor(port)
    m.target_velocity = velocity
    if velocity == 0:
        m.stop()
        return
    m.current_speed = velocity
    m._set_speed(velocity)
    m.wheel.command('run-forever')


def run_for_degrees(port, degrees, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    # Direction comes from the sign of degrees; velocity is a magnitude,
    # as on the device.
    m = _get_motor(port)
    m.target_position = m.position + degrees
    m.target_velocity = velocity
    m.current_speed = abs(velocity)
    m._set_speed(abs(velocity))
    m.wheel.position_sp(int(m.sign * degrees))
    m.wheel.command('run-to-rel-pos')
    if stop:
        m._wait_until_running()
        m._wait_until_stopped()


def run_for_time(port, time_ms, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    run(port, velocity)
    time.sleep_ms(time_ms)
    if stop:
        _get_motor(port).stop()


def run_to_position(port, position, velocity, *, direction=SHORTEST_PATH, stop=True, acceleration=1000, deceleration=1000):
    m = _get_motor(port)
    m.target_position = position
    m.target_velocity = velocity
    m.current_speed = abs(velocity)
    m._set_speed(abs(velocity))
    m.wheel.position_sp(int(m.sign * position))
    m.wheel.command('run-to-abs-pos')
    if stop:
        m._wait_until_running()
        m._wait_until_stopped()


def run_to_degrees_counted(port, degrees, velocity, *, stop=True, acceleration=1000, deceleration=1000):
    run_to_position(port, degrees, velocity, stop=stop, acceleration=acceleration, deceleration=deceleration)


def stop(port, *, stop=True):
    _get_motor(port).stop()


def reset_relative_position(port, position):
    _get_motor(port).position = position


def get_position(port):
    return _get_motor(port).position


def get_degrees_counted(port):
    return get_position(port)


def get_velocity(port):
    return _get_motor(port).velocity


def get_default_velocity(port):
    return MOTOR_CONFIG['default_speed_dps']


def set_degrees_counted(port, degrees_counted):
    reset_relative_position(port, degrees_counted)


def was_interrupted(port): return False
def was_stalled(port): return False


def get_duty_cycle(port):
    return _get_motor(port).current_speed


for _port in MOTOR_PINS:
    _get_motor(_port)
