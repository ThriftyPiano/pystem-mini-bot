# filename: color_sensor.py  (GEARS simulator build)
import simPython
import time
from config import COLOR_SENSOR_PINS

_SENSOR_DELAY = 0.001
_sensors = {}

def _sensor(port):
    if port not in COLOR_SENSOR_PINS:
        if len(COLOR_SENSOR_PINS) == 1:
            # A single-sensor robot answers to any port name.
            port = list(COLOR_SENSOR_PINS.keys())[0]
        else:
            raise ValueError("No color sensor on port " + repr(port))
    if port not in _sensors:
        _sensors[port] = simPython.ColorSensor(COLOR_SENSOR_PINS[port])
    return _sensors[port]

def reflection(port):
    # Reflected light 0-100, white high / black low — the same sense as the
    # TCRT5000 reading on the robot (though not the same scale).
    time.sleep(_SENSOR_DELAY)
    rgb = _sensor(port).value()
    return int((rgb[0] + rgb[1] + rgb[2]) / 3 / 2.55)
