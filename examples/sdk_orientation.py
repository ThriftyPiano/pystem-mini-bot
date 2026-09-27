# filename: orientation.py
# Roll, pitch and yaw from the IMU selected by config.IMU ('mpu6050' on
# the Max V1, 'bmi270' on the StickS3). Backends return accel in g and
# gyro in deg/s, remapped to robot axes by config.IMU_AXES.

import time
import math
from config import IMU, IMU_AXES, EXT_I2C

# MPU-6050 registers
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43
PWR_MGMT_1 = 0x6B
ACCEL_CONFIG = 0x1C
GYRO_CONFIG = 0x1B

MPU_ACCEL_LSB_PER_G = 16384.0    # +/- 2 g
MPU_GYRO_LSB_PER_DPS = 131.0     # +/- 250 deg/s


class MPU6050:
    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.address = address

        try:
            self.i2c.writeto(self.address, bytes([PWR_MGMT_1, 0]))
            print(f"MPU-6050 found at I2C address: {hex(self.address)}")
        except OSError:
            raise OSError(f"MPU-6050 not found at address {hex(self.address)}. Check wiring and AD0 pin.")

        self.i2c.writeto(self.address, bytes([PWR_MGMT_1, 0]))
        self.i2c.writeto(self.address, bytes([ACCEL_CONFIG, 0]))
        self.i2c.writeto(self.address, bytes([GYRO_CONFIG, 0]))

    def _read_16bit_signed_value(self, data):
        high = data[0]
        low = data[1]
        value = (high << 8) | low
        if value > 32767:
            value -= 65536
        return value

    def get_accel_data(self):
        data = self.i2c.readfrom_mem(self.address, ACCEL_XOUT_H, 6)
        accel_x = self._read_16bit_signed_value(data[0:2])
        accel_y = self._read_16bit_signed_value(data[2:4])
        accel_z = self._read_16bit_signed_value(data[4:6])
        return accel_x, accel_y, accel_z

    def get_gyro_data(self):
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
    # Through the frozen sticks3 module, which owns the stick's I2C bus.
    # The driver's .gyro is in deg/s despite its docstring saying rad/s.
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
    if IMU == 'mpu6050':
        from machine import I2C, Pin
        bus = EXT_I2C
        i2c = I2C(bus['id'],
                  sda=Pin(bus['sda'] if sda_pin is None else sda_pin),
                  scl=Pin(bus['scl'] if scl_pin is None else scl_pin),
                  freq=bus['freq'])

        # 0x68, or 0x69 with AD0 high; other devices (WonderEcho 0x34) share the bus.
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
    out = []
    for spec in IMU_AXES:
        sign = -1.0 if spec.startswith('-') else 1.0
        out.append(sign * vec['xyz'.index(spec[-1])])
    return out[0], out[1], out[2]


class OrientationSensor:
    def __init__(self, sda_pin=None, scl_pin=None):
        self.imu = _make_imu(sda_pin, scl_pin)

        self.accel_x_offset = 0
        self.accel_y_offset = 0
        self.accel_z_offset = 0
        self.gyro_x_offset = 0
        self.gyro_y_offset = 0
        self.gyro_z_offset = 0

        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.yaw_rate = 0   # deg/s, clockwise positive
        self.last_time = time.ticks_ms()

        self.calibrate()

    def _read(self):
        accel, gyro = self.imu.read()
        return _axis_remap(accel), _axis_remap(gyro)

    def calibrate(self, samples=50):
        """Measure the at-rest offsets. Keep the robot still."""
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

        # The z offset keeps gravity (1 g) in the reading.
        self.accel_x_offset = accel_x_sum / samples
        self.accel_y_offset = accel_y_sum / samples
        self.accel_z_offset = accel_z_sum / samples - 1.0
        self.gyro_x_offset = gyro_x_sum / samples
        self.gyro_y_offset = gyro_y_sum / samples
        self.gyro_z_offset = gyro_z_sum / samples

        print("Calibration complete.")

    def update(self):
        """Integrate the sensors; returns (roll, pitch, yaw) in degrees."""
        current_time = time.ticks_ms()
        dt = (current_time - self.last_time) / 1000.0
        self.last_time = current_time

        (accel_x_g, accel_y_g, accel_z_g), (gyro_x_dps, gyro_y_dps, gyro_z_dps) = self._read()

        accel_x_g -= self.accel_x_offset
        accel_y_g -= self.accel_y_offset
        accel_z_g -= self.accel_z_offset
        gyro_x_dps -= self.gyro_x_offset
        gyro_y_dps -= self.gyro_y_offset
        gyro_z_dps -= self.gyro_z_offset

        accel_pitch = math.degrees(math.atan2(-accel_x_g, math.sqrt(accel_y_g**2 + accel_z_g**2)))
        accel_roll = math.degrees(math.atan2(accel_y_g, math.sqrt(accel_x_g**2 + accel_z_g**2)))

        gyro_roll = self.roll + gyro_x_dps * dt
        gyro_pitch = self.pitch + gyro_y_dps * dt
        gyro_yaw = self.yaw + gyro_z_dps * dt

        alpha = 0.98
        self.roll = alpha * gyro_roll + (1 - alpha) * accel_roll
        self.pitch = alpha * gyro_pitch + (1 - alpha) * accel_pitch

        self.yaw = gyro_yaw
        self.yaw_rate = gyro_z_dps

        return self.roll, self.pitch, self.yaw

    def get_yaw(self):
        return self.yaw

    def reset_yaw(self):
        self.yaw = 0
