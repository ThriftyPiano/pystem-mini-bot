# filename: distance_sensor.py  (GEARS simulator build)
# Same API as examples/sdk_distance_sensor.py: distance(port) -> millimetres,
# -1 when nothing is in range. Backed by GEARS's UltrasonicSensor component
# (robots/minibot.json), which reports centimetres and its ray length when
# nothing is hit.
import simPython
import time
from config import DISTANCE_SENSOR_PINS

_SENSOR_DELAY = 0.001
# HC-SR04 rated range; matches the rayLength option in robots/minibot.json.
_MAX_CM = 400
_sensors = {}


def _sensor(port):
    if port not in DISTANCE_SENSOR_PINS:
        if len(DISTANCE_SENSOR_PINS) == 1:
            # A single-sensor robot answers to any port name.
            port = list(DISTANCE_SENSOR_PINS.keys())[0]
        else:
            raise ValueError("No distance sensor on port " + repr(port))
    if port not in _sensors:
        _sensors[port] = simPython.UltrasonicSensor(DISTANCE_SENSOR_PINS[port])
    return _sensors[port]


def distance(port):
    """Distance to the nearest object in millimetres, or -1 if nothing is in range."""
    time.sleep(_SENSOR_DELAY)
    cm = _sensor(port).dist()
    if cm >= _MAX_CM:
        return -1
    return int(cm * 10)


def distance_cm(port):
    """Convenience wrapper: distance in whole centimetres, -1 if out of range."""
    mm = distance(port)
    return -1 if mm < 0 else mm // 10
