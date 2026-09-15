# filename: orientation.py
# Orientation module for robot navigation.
# Provides yaw, pitch, roll data for motor control.
#
# The IMU is selected by config.IMU:
#   'mpu6050' — external MPU-6050 on the Max V1 board's I2C bus (config.EXT_I2C)
#   'bmi270'  — the M5StickS3's internal BMI270, via the frozen sticks3 module
# Every backend hands the filter the same thing — accel in g, gyro in deg/s,
# already remapped to the robot's axes by config.IMU_AXES — so the
# complementary filter below is hardware-independent.

import time
import math
from config import IMU, IMU_AXES, EXT_I2C

# MPU6050 Register addresses
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43
PWR_MGMT_1 = 0x6B
ACCEL_CONFIG = 0x1C
GYRO_CONFIG = 0x1B

# MPU-6050 sensitivity at the ranges configured below.
MPU_ACCEL_LSB_PER_G = 16384.0    # +/- 2 g
MPU_GYRO_LSB_PER_DPS = 131.0     # +/- 250 deg/s


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

    def read(self):
        """Return ((ax, ay, az) in g, (gx, gy, gz) in deg/s)."""
        ax, ay, az = self.get_accel_data()
        gx, gy, gz = self.get_gyro_data()
        return ((ax / MPU_ACCEL_LSB_PER_G, ay / MPU_ACCEL_LSB_PER_G, az / MPU_ACCEL_LSB_PER_G),
                (gx / MPU_GYRO_LSB_PER_DPS, gy / MPU_GYRO_LSB_PER_DPS, gz / MPU_GYRO_LSB_PER_DPS))


class BMI270:
    """
    The M5StickS3's internal BMI270, through the frozen sticks3 board module
    (which owns the stick's shared 100 kHz I2C bus — never open a second
    I2C object on those pins). The driver reports .acceleration in m/s^2
    and .gyro in deg/s (raw / 131.2 LSB-per-dps at the +/-250 dps range the
    board module selects — despite its docstring saying rad/s).
    """
    G = 9.80665

    def __init__(self):
        import sticks3
        self.dev = sticks3.imu()
        print("BMI270 found on the StickS3 internal bus")

    def read(self):
        """Return ((ax, ay, az) in g, (gx, gy, gz) in deg/s)."""
        ax, ay, az = self.dev.acceleration
        gyro_dps = self.dev.gyro
        return ((ax / self.G, ay / self.G, az / self.G), gyro_dps)


def _make_imu(sda_pin=None, scl_pin=None):
    """Instantiate the backend named by config.IMU."""
    if IMU == 'mpu6050':
        from machine import I2C, Pin
        bus = EXT_I2C
        i2c = I2C(bus['id'],
                  sda=Pin(bus['sda'] if sda_pin is None else sda_pin),
                  scl=Pin(bus['scl'] if scl_pin is None else scl_pin),
                  freq=bus['freq'])

        # Find MPU6050 device (fixed address: 0x68, or 0x69 if AD0 is pulled high).
        # Don't use devices[0] — other I2C peripherals (e.g. WonderEcho at 0x34)
        # may also be on the bus.
        devices = i2c.scan()
        if not devices:
            raise OSError("No I2C devices found. Please check your wiring.")

        if 0x68 in devices:
            mpu_address = 0x68
        elif 0x69 in devices:
            mpu_address = 0x69
        else:
            raise OSError(
                "MPU-6050 not found at 0x68/0x69. Devices on bus: "
                + ", ".join(hex(d) for d in devices)
            )
        print(f"Found MPU-6050 at I2C address: {hex(mpu_address)}")
        return MPU6050(i2c, address=mpu_address)

    if IMU == 'bmi270':
        return BMI270()

    raise ValueError("Unknown IMU backend in config: " + repr(IMU))


def _axis_remap(vec):
    """Reorder/flip a sensor (x, y, z) triple into robot axes per config.IMU_AXES."""
    out = []
    for spec in IMU_AXES:
        sign = -1.0 if spec.startswith('-') else 1.0
        out.append(sign * vec['xyz'.index(spec[-1])])
    return out[0], out[1], out[2]


class OrientationSensor:
    """
    Orientation sensor class for robot navigation.
    """
    def __init__(self, sda_pin=None, scl_pin=None):
        # sda_pin / scl_pin override config.EXT_I2C for the MPU-6050 backend
        # only; they are ignored by the BMI270, whose bus is fixed.
        self.imu = _make_imu(sda_pin, scl_pin)
        
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

    def _read(self):
        """Backend reading in robot axes: ((ax, ay, az) g, (gx, gy, gz) deg/s)."""
        accel, gyro = self.imu.read()
        return _axis_remap(accel), _axis_remap(gyro)
    
    def calibrate(self, samples=50):
        """Calibrate the sensor by taking offset readings"""
        print("Calibrating orientation sensor... Please keep still.")
        
        accel_x_sum = accel_y_sum = accel_z_sum = 0
        gyro_x_sum = gyro_y_sum = gyro_z_sum = 0
        
        for _ in range(samples):
            (accel_x, accel_y, accel_z), (gyro_x, gyro_y, gyro_z) = self._read()
            
            accel_x_sum += accel_x
            accel_y_sum += accel_y
            accel_z_sum += accel_z
            gyro_x_sum += gyro_x
            gyro_y_sum += gyro_y
            gyro_z_sum += gyro_z
            
            time.sleep_ms(20)
        
        # At rest the accelerometer should read exactly gravity, (0, 0, 1 g)
        # in robot axes — so the offset is the deviation from that, not the
        # whole reading. Subtracting the full at-rest vector would remove
        # gravity itself and leave the tilt estimate with nothing to
        # measure against, so roll/pitch would wander with noise.
        self.accel_x_offset = accel_x_sum / samples
        self.accel_y_offset = accel_y_sum / samples
        self.accel_z_offset = accel_z_sum / samples - 1.0
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

        # Get sensor data (g and deg/s, robot axes)
        (accel_x_g, accel_y_g, accel_z_g), (gyro_x_dps, gyro_y_dps, gyro_z_dps) = self._read()

        # Apply calibration offsets
        accel_x_g -= self.accel_x_offset
        accel_y_g -= self.accel_y_offset
        accel_z_g -= self.accel_z_offset
        gyro_x_dps -= self.gyro_x_offset
        gyro_y_dps -= self.gyro_y_offset
        gyro_z_dps -= self.gyro_z_offset

        # Calculate pitch and roll from accelerometer data
        accel_pitch = math.degrees(math.atan2(-accel_x_g, math.sqrt(accel_y_g**2 + accel_z_g**2)))
        accel_roll = math.degrees(math.atan2(accel_y_g, math.sqrt(accel_x_g**2 + accel_z_g**2)))

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
