# filename: distance_sensor.py
# HC-SR04 ultrasonic distance sensor on the Bot HAT's DIST header, with the
# SPIKE Prime distance_sensor API: distance(port) -> millimetres.
#
# The HAT feeds the sensor 5 V and divides its 5 V ECHO pulse down to 3.3 V
# (R4/R5) before it reaches the StickS3, so the sensor plugs straight in:
# header order is 5V TRIG ECHO GND, the same as the pins on the module.
import machine
import time
from config import DISTANCE_SENSOR_PINS

# Speed of sound 343 m/s -> 0.343 mm/us, halved for the round trip.
_MM_PER_US = 0.1715
# Longest echo we wait for: 30 ms is ~5 m round trip (sensor's rated max is 4 m).
_TIMEOUT_US = 30000
# The HC-SR04 datasheet asks for >= 60 ms between pings or echoes overlap.
_MIN_PING_INTERVAL_MS = 60

_sensors = {}   # port -> (trig Pin, echo Pin)
_last_ping = {}  # port -> ticks_ms of the last trigger


def _pins(port):
    if port not in DISTANCE_SENSOR_PINS:
        if len(DISTANCE_SENSOR_PINS) == 1:
            # A single-sensor board answers to any port name.
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
    """Distance to the nearest object in millimetres, or -1 if nothing is in range.

    Same contract as SPIKE Prime's distance_sensor.distance(). Blocks for up
    to ~30 ms while it waits for the echo; consecutive calls are spaced out
    to 60 ms so echoes from the previous ping can't be mistaken for this one.
    """
    port, (trig, echo) = _pins(port)
    wait = _MIN_PING_INTERVAL_MS - time.ticks_diff(time.ticks_ms(), _last_ping[port])
    if wait > 0:
        time.sleep_ms(wait)
    # 10 us trigger pulse
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    _last_ping[port] = time.ticks_ms()
    # ECHO goes high for as long as the ping took to come back.
    # time_pulse_us returns -2 if the pulse never started, -1 if it never ended.
    pulse = machine.time_pulse_us(echo, 1, _TIMEOUT_US)
    if pulse < 0:
        return -1
    return int(pulse * _MM_PER_US)


def distance_cm(port):
    """Convenience wrapper: distance in whole centimetres, -1 if out of range."""
    mm = distance(port)
    return -1 if mm < 0 else mm // 10
