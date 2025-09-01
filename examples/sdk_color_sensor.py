# filename: color_sensor.py
import machine
import math

# Define the analog pin connected to the TCRT5000 sensor.
sensor_pin = machine.Pin(32)
adc = machine.ADC(sensor_pin)

# Set the attenuation for the ADC. This is important for ESP32.
# machine.ADC.ATTN_11DB sets the full range (0V to 3.6V).
adc.atten(machine.ADC.ATTN_11DB)

def reflection(port):
    # Read the analog value from the sensor.
    # The value will be a 12-bit integer (0-4095).
    sensor_value = adc.read() + 1
    sensor_value = 100 - int(math.log2(sensor_value) * 8)
    return sensor_value
