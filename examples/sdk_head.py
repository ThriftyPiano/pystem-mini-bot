# filename: head.py
# Pan/tilt head: two positional (0-180 deg) hobby servos, no encoders.

from machine import Pin, PWM
import time
from config import HEAD_SERVOS, HEAD_CONFIG

PAN = 'pan'
TILT = 'tilt'


class HeadServo:
    def __init__(self, name, pin):
        self.name = name
        self.pin = pin
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(50)
        self.min_us = HEAD_CONFIG['min_pulse_us']
        self.max_us = HEAD_CONFIG['max_pulse_us']
        self.min_angle = HEAD_CONFIG['min_angle']
        self.max_angle = HEAD_CONFIG['max_angle']
        self.angle = None
        self.move_to(HEAD_CONFIG['center_angle'])

    def move_to(self, degrees):
        degrees = max(self.min_angle, min(self.max_angle, degrees))
        span_us = self.max_us - self.min_us
        pulse_us = self.min_us + (degrees / 180.0) * span_us
        self.pwm.duty_u16(int(pulse_us / 20000.0 * 65535))
        self.angle = degrees
        return self.angle

    def release(self):
        self.pwm.duty_u16(0)


_head = {}


def _get(name):
    if name not in _head:
        if name in HEAD_SERVOS:
            _head[name] = HeadServo(name, HEAD_SERVOS[name])
        else:
            raise ValueError("Invalid head axis: {}".format(name))
    return _head[name]


# --- API Functions ---

def pan(degrees):
    """0 = full right, 90 = center, 180 = full left."""
    return _get(PAN).move_to(degrees)


def tilt(degrees):
    """0 = full down, 90 = level, 180 = full up."""
    return _get(TILT).move_to(degrees)


def look(pan_deg, tilt_deg):
    pan(pan_deg)
    tilt(tilt_deg)


def center():
    c = HEAD_CONFIG['center_angle']
    look(c, c)


def nod(times=2, *, amount=20, speed_ms=250):
    c = HEAD_CONFIG['center_angle']
    for _ in range(times):
        tilt(c - amount)
        time.sleep_ms(speed_ms)
        tilt(c + amount)
        time.sleep_ms(speed_ms)
    tilt(c)


def shake(times=2, *, amount=30, speed_ms=250):
    c = HEAD_CONFIG['center_angle']
    for _ in range(times):
        pan(c - amount)
        time.sleep_ms(speed_ms)
        pan(c + amount)
        time.sleep_ms(speed_ms)
    pan(c)


def dance(times=2, *, beat_ms=250):
    # Big fast servo slews can brown out the board; raise beat_ms if so.
    c = HEAD_CONFIG['center_angle']
    pan_wide = 75
    tilt_wide = 50
    for _ in range(times):
        pan(c - pan_wide)
        time.sleep_ms(beat_ms)
        pan(c + pan_wide)
        time.sleep_ms(beat_ms)
        pan(c)
        time.sleep_ms(beat_ms)
        tilt(c + tilt_wide)
        time.sleep_ms(beat_ms)
        tilt(c - tilt_wide)
        time.sleep_ms(beat_ms)
        tilt(c)
        time.sleep_ms(beat_ms)
        look(c - pan_wide, c + tilt_wide)
        time.sleep_ms(beat_ms)
        look(c + pan_wide, c - tilt_wide)
        time.sleep_ms(beat_ms)
    center()


def get_position(name):
    """Last commanded angle for an axis (PAN or TILT)."""
    return _get(name).angle


def release():
    """Cut power to both servos so the head goes limp."""
    for name in HEAD_SERVOS:
        _get(name).release()
