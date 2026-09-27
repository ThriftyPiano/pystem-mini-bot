# filename: distance_sensor.py
# HC-SR04 ultrasonic sensor on the Bot HAT's DIST header, SPIKE Prime
# distance_sensor API: distance(port) -> millimetres.
import machine
import time
from config import DISTANCE_SENSOR_PINS

_MM_PER_US = 0.1715     # speed of sound, halved for the round trip
_TIMEOUT_US = 30000     # ~5 m round trip
_MIN_PING_INTERVAL_MS = 60   # datasheet minimum between pings

_sensors = {}   # port -> (trig Pin, echo Pin)
_last_ping = {}  # port -> ticks_ms of the last trigger


def _pins(port):
    if port not in DISTANCE_SENSOR_PINS:
        if len(DISTANCE_SENSOR_PINS) == 1:
            port = next(iter(DISTANCE_SENSOR_PINS))
        else:
            raise ValueError("No distance sensor on port {!r}; configured ports: {}".format(
                port, ", ".join(sorted(DISTANCE_SENSOR_PINS)) or "none"))
    if port not in _sensors:
        pins = DISTANCE_SENSOR_PINS[port]
        trig = machine.Pin(pins['trig'], machine.Pin.OUT, value=0)
        echo = machine.Pin(pins['echo'], machine.Pin.IN)
        _sensors[port] = (trig, echo)
        _last_ping[port] = time.ticks_add(time.ticks_ms(), -_MIN_PING_INTERVAL_MS)
    return port, _sensors[port]


def distance(port):
    """Distance to the nearest object in millimetres, or -1 if nothing is in range."""
    port, (trig, echo) = _pins(port)
    wait = _MIN_PING_INTERVAL_MS - time.ticks_diff(time.ticks_ms(), _last_ping[port])
    if wait > 0:
        time.sleep_ms(wait)
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    _last_ping[port] = time.ticks_ms()
    pulse = machine.time_pulse_us(echo, 1, _TIMEOUT_US)
    if pulse < 0:
        return -1
    return int(pulse * _MM_PER_US)


def distance_cm(port):
    """Distance in whole centimetres, -1 if out of range."""
    mm = distance(port)
    return -1 if mm < 0 else mm // 10
