# filename: color_sensor.py
# TCRT5000 reflection sensor, SPIKE Prime color_sensor API: reflection(port) -> 0-100.
import machine
import math
from config import COLOR_SENSOR_PINS

_adcs = {}

def _adc(port):
    if port not in COLOR_SENSOR_PINS:
        if len(COLOR_SENSOR_PINS) == 1:
            port = next(iter(COLOR_SENSOR_PINS))
        else:
            raise ValueError("No color sensor on port {!r}; configured ports: {}".format(
                port, ", ".join(sorted(COLOR_SENSOR_PINS))))
    if port not in _adcs:
        adc = machine.ADC(machine.Pin(COLOR_SENSOR_PINS[port]))
        adc.atten(machine.ADC.ATTN_11DB)   # full 0-3.6 V range
        _adcs[port] = adc
    return _adcs[port]

def reflection(port):
    sensor_value = _adc(port).read() + 1
    sensor_value = 100 - int(math.log2(sensor_value) * 8)
    return sensor_value
