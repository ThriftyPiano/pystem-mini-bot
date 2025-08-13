# filename: orientation.py
# MPU-6050 Orientation Module for robot navigation
# Provides yaw, pitch, roll data for motor control

import time
import math
import sys
from machine import I2C, Pin

# MPU6050 Register addresses
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43
PWR_MGMT_1 = 0x6B
ACCEL_CONFIG = 0x1C
GYRO_CONFIG = 0x1B

class MPU6050:
    """
    A simple MicroPython driver for the MPU-6050.
    """
    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.address = address
        
        # Check if the device is on the bus
        try:
            self.i2c.writeto(self.address, bytes([PWR_MGMT_1, 0]))
            print(f"MPU-6050 found at I2C address: {hex(self.address)}")
        except OSError:
            raise OSError(f"MPU-6050 not found at address {hex(self.address)}. Check wiring and AD0 pin.")

        # Wake up the sensor
        self.i2c.writeto(self.address, bytes([PWR_MGMT_1, 0]))
        # Configure accelerometer and gyroscope to full scale ranges
        # Accelerometer: +/- 2g (default)
        # Gyroscope: +/- 250 deg/s (default)
        self.i2c.writeto(self.address, bytes([ACCEL_CONFIG, 0]))
        self.i2c.writeto(self.address, bytes([GYRO_CONFIG, 0]))

    def _read_16bit_signed_value(self, data):
        """
        Takes a 2-byte list and returns a signed 16-bit integer.
        """
        high = data[0]
        low = data[1]
        value = (high << 8) | low
        # Handle signed 16-bit values
        if value > 32767:
            value -= 65536
        return value

    def get_accel_data(self):
        """
        Reads all 6 bytes of accelerometer data in a single I2C transaction
        and returns the raw values.
        """
        data = self.i2c.readfrom_mem(self.address, ACCEL_XOUT_H, 6)
        accel_x = self._read_16bit_signed_value(data[0:2])
        accel_y = self._read_16bit_signed_value(data[2:4])
        accel_z = self._read_16bit_signed_value(data[4:6])
        return accel_x, accel_y, accel_z

    def get_gyro_data(self):
        """
        Reads all 6 bytes of gyroscope data in a single I2C transaction
        and returns the raw values.
        """
        data = self.i2c.readfrom_mem(self.address, GYRO_XOUT_H, 6)
        gyro_x = self._read_16bit_signed_value(data[0:2])
        gyro_y = self._read_16bit_signed_value(data[2:4])
        gyro_z = self._read_16bit_signed_value(data[4:6])
        return gyro_x, gyro_y, gyro_z

class OrientationSensor:
    """
    Orientation sensor class for robot navigation using MPU6050
    """
    def __init__(self, sda_pin=21, scl_pin=22):
        # Initialize I2C
        self.i2c = I2C(1, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
        
        # Find MPU6050 device
        devices = self.i2c.scan()
        if not devices:
            raise OSError("No I2C devices found. Please check your wiring.")
        
        # Use first device found (typically MPU6050 at 0x68)
        mpu_address = devices[0]
        print(f"Found I2C device at address: {hex(mpu_address)}")
        
        # Initialize MPU6050
        self.mpu = MPU6050(self.i2c, address=mpu_address)
        
        # Calibration offsets
        self.accel_x_offset = 0
        self.accel_y_offset = 0
        self.accel_z_offset = 0
        self.gyro_x_offset = 0
        self.gyro_y_offset = 0
        self.gyro_z_offset = 0
        
        # Orientation variables
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.last_time = time.ticks_ms()
        
        # Calibrate sensor
        self.calibrate()
    
    def calibrate(self, samples=50):
        """Calibrate the sensor by taking offset readings"""
        print("Calibrating orientation sensor... Please keep still.")
        
        accel_x_sum = accel_y_sum = accel_z_sum = 0
        gyro_x_sum = gyro_y_sum = gyro_z_sum = 0
        
        for _ in range(samples):
            accel_x, accel_y, accel_z = self.mpu.get_accel_data()
            gyro_x, gyro_y, gyro_z = self.mpu.get_gyro_data()
            
            accel_x_sum += accel_x
            accel_y_sum += accel_y
            accel_z_sum += accel_z
            gyro_x_sum += gyro_x
            gyro_y_sum += gyro_y
            gyro_z_sum += gyro_z
            
            time.sleep_ms(20)
        
        self.accel_x_offset = accel_x_sum / samples
        self.accel_y_offset = accel_y_sum / samples
        self.accel_z_offset = accel_z_sum / samples
        self.gyro_x_offset = gyro_x_sum / samples
        self.gyro_y_offset = gyro_y_sum / samples
        self.gyro_z_offset = gyro_z_sum / samples
        
        print("Calibration complete.")
    
    def update(self):
        """
        Update roll, pitch, and yaw based on current time and sensor readings.
        Returns tuple of (roll, pitch, yaw) in degrees.
        """
        current_time = time.ticks_ms()
        dt = (current_time - self.last_time) / 1000.0  # Time in seconds
        self.last_time = current_time

        # Get raw sensor data
        accel_x, accel_y, accel_z = self.mpu.get_accel_data()
        gyro_x, gyro_y, gyro_z = self.mpu.get_gyro_data()

        # Apply calibration offsets
        accel_x -= self.accel_x_offset
        accel_y -= self.accel_y_offset
        accel_z -= self.accel_z_offset
        gyro_x -= self.gyro_x_offset
        gyro_y -= self.gyro_y_offset
        gyro_z -= self.gyro_z_offset

        # Convert raw accelerometer data to g's (sensitivity scale factor for +/- 2g)
        accel_x_g = accel_x / 16384.0
        accel_y_g = accel_y / 16384.0
        accel_z_g = accel_z / 16384.0

        # Calculate pitch and roll from accelerometer data
        accel_pitch = math.degrees(math.atan2(-accel_x_g, math.sqrt(accel_y_g**2 + accel_z_g**2)))
        accel_roll = math.degrees(math.atan2(accel_y_g, math.sqrt(accel_x_g**2 + accel_z_g**2)))

        # Convert raw gyroscope data to degrees per second (sensitivity scale factor for +/- 250 deg/s)
        gyro_x_dps = gyro_x / 131.0
        gyro_y_dps = gyro_y / 131.0
        gyro_z_dps = gyro_z / 131.0

        # Calculate pitch, roll, and yaw from gyroscope data
        gyro_roll = self.roll + gyro_x_dps * dt
        gyro_pitch = self.pitch + gyro_y_dps * dt
        gyro_yaw = self.yaw + gyro_z_dps * dt

        # Simple complementary filter to combine accelerometer and gyroscope data
        alpha = 0.98  # Filter coefficient
        self.roll = alpha * gyro_roll + (1 - alpha) * accel_roll
        self.pitch = alpha * gyro_pitch + (1 - alpha) * accel_pitch

        # Yaw is calculated only from the gyroscope
        self.yaw = gyro_yaw
        
        return self.roll, self.pitch, self.yaw
    
    def get_yaw(self):
        """Get current yaw angle in degrees"""
        return self.yaw
    
    def reset_yaw(self):
        """Reset yaw to zero (set current direction as reference)"""
        self.yaw = 0
