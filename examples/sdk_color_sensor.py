# filename: color_sensor.py
import machine
import math
from config import COLOR_SENSOR_PINS

# One ADC per configured sensor port, created on first use.
_adcs = {}

def _adc(port):
    if port not in COLOR_SENSOR_PINS:
        if len(COLOR_SENSOR_PINS) == 1:
            # A single-sensor board answers to any port name.
            port = next(iter(COLOR_SENSOR_PINS))
        else:
            raise ValueError("No color sensor on port {!r}; configured ports: {}".format(
                port, ", ".join(sorted(COLOR_SENSOR_PINS))))
    if port not in _adcs:
        adc = machine.ADC(machine.Pin(COLOR_SENSOR_PINS[port]))
        # Set the attenuation for the ADC. This is important for ESP32.
        # machine.ADC.ATTN_11DB sets the full range (0V to 3.6V).
        adc.atten(machine.ADC.ATTN_11DB)
        _adcs[port] = adc
    return _adcs[port]

def reflection(port):
    # Read the analog value from the TCRT5000 sensor on the given port.
    # The value will be a 12-bit integer (0-4095).
    sensor_value = _adc(port).read() + 1
    sensor_value = 100 - int(math.log2(sensor_value) * 8)
    return sensor_value
