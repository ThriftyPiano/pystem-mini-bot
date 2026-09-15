# filename: orientation.py  (GEARS simulator build)
# Same OrientationSensor interface as examples/sdk_orientation.py
# (calibrate / update / get_yaw / reset_yaw, .roll .pitch .yaw in degrees),
# backed by GEARS's GyroSensor.
#
# Sign convention: yaw increases CLOCKWISE seen from above. That is what
# motor_pair.py assumes (its straight-line correction speeds the left wheel
# up when yaw drops, and move_tank_for_degrees(+90) spins clockwise to
# reach start_yaw + 90); with the opposite sign the correction is positive
# feedback and the robot spirals. GEARS's gyro is clockwise-positive
# natively, so no flip is needed here.
import simPython
import time
from config import GYRO_PORT

_SENSOR_DELAY = 0.001
_YAW_SIGN = 1


class OrientationSensor:
    def __init__(self, sda_pin=None, scl_pin=None):
        self.gyro = simPython.GyroSensor(GYRO_PORT)
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.last_time = time.ticks_ms()
        self.calibrate()

    def calibrate(self, samples=50):
        # A simulated gyro has no bias to remove; keep the call (and the
        # message students are used to) but don't burn a second on it.
        print("Calibrating orientation sensor... Please keep still.")
        self.gyro.reset()
        print("Calibration complete.")

    def update(self):
        time.sleep(_SENSOR_DELAY)
        self.roll = self.gyro.rollAngleAndRate(True)[0]
        self.pitch = self.gyro.pitchAngleAndRate(True)[0]
        self.yaw = _YAW_SIGN * self.gyro.yawAngleAndRate(True)[0] + self._yaw_offset
        self.last_time = time.ticks_ms()
        return self.roll, self.pitch, self.yaw

    _yaw_offset = 0

    def get_yaw(self):
        return self.yaw

    def reset_yaw(self):
        time.sleep(_SENSOR_DELAY)
        self._yaw_offset = -_YAW_SIGN * self.gyro.yawAngleAndRate(True)[0]
        self.yaw = 0
