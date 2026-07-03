# filename: head.py
# Pan/tilt head module for ESP32 Mini Bot.
# Two positional (0-180 deg) servos — pan = yaw (side to side),
# tilt = pitch (up and down). Unlike motor.py these are standard hobby
# servos with no encoders: you command an angle and the servo holds it.

from machine import Pin, PWM
import time
from config import HEAD_SERVOS, HEAD_CONFIG

# Axis constants
PAN = 'pan'
TILT = 'tilt'


class HeadServo:
    """A single positional servo. Maps an angle (deg) to a 50Hz pulse width."""

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
        # Rest at center so the head starts in a known, safe pose.
        self.move_to(HEAD_CONFIG['center_angle'])

    def move_to(self, degrees):
        """Drive the servo to an absolute angle (clamped to the travel limits)."""
        degrees = max(self.min_angle, min(self.max_angle, degrees))
        span_us = self.max_us - self.min_us
        pulse_us = self.min_us + (degrees / 180.0) * span_us
        # 50Hz -> 20000us period. duty_u16 is 0-65535 over the full period.
        self.pwm.duty_u16(int(pulse_us / 20000.0 * 65535))
        self.angle = degrees
        return self.angle

    def release(self):
        """Stop holding position (cut the PWM signal so the servo goes limp)."""
        self.pwm.duty_u16(0)


# Global head instance (lazy init — mirrors style of wonder_echo.py)
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
    """Turn the head side to side. 0 = full right, 90 = center, 180 = full left."""
    return _get(PAN).move_to(degrees)


def tilt(degrees):
    """Tilt the head up and down. 0 = full down, 90 = level, 180 = full up."""
    return _get(TILT).move_to(degrees)


def look(pan_deg, tilt_deg):
    """Aim both axes at once."""
    pan(pan_deg)
    tilt(tilt_deg)


def center():
    """Return both axes to their center (rest) pose."""
    c = HEAD_CONFIG['center_angle']
    look(c, c)


def nod(times=2, *, amount=20, speed_ms=250):
    """Nod 'yes' by rocking the tilt axis around center."""
    c = HEAD_CONFIG['center_angle']
    for _ in range(times):
        tilt(c - amount)
        time.sleep_ms(speed_ms)
        tilt(c + amount)
        time.sleep_ms(speed_ms)
    tilt(c)


def shake(times=2, *, amount=30, speed_ms=250):
    """Shake 'no' by rocking the pan axis around center."""
    c = HEAD_CONFIG['center_angle']
    for _ in range(times):
        pan(c - amount)
        time.sleep_ms(speed_ms)
        pan(c + amount)
        time.sleep_ms(speed_ms)
    pan(c)


def dance(times=2, *, beat_ms=200):
    """Do a little head dance: sway, bob, and groove diagonally to a beat.

    Amplitudes and speed are kept moderate on purpose — big fast servo
    slews spike the current draw and can brown out the board (see nod/shake).
    """
    c = HEAD_CONFIG['center_angle']
    for _ in range(times):
        # sway side to side
        pan(c - 30)
        time.sleep_ms(beat_ms)
        pan(c + 30)
        time.sleep_ms(beat_ms)
        pan(c)
        time.sleep_ms(beat_ms)
        # bob up and down
        tilt(c + 20)
        time.sleep_ms(beat_ms)
        tilt(c - 20)
        time.sleep_ms(beat_ms)
        tilt(c)
        time.sleep_ms(beat_ms)
        # diagonal grooves
        look(c - 25, c + 15)
        time.sleep_ms(beat_ms)
        look(c + 25, c - 15)
        time.sleep_ms(beat_ms)
    center()


def get_position(name):
    """Return the last commanded angle for an axis (PAN or TILT)."""
    return _get(name).angle


def release():
    """Cut power to both servos so the head goes limp (saves current / stops jitter)."""
    for name in HEAD_SERVOS:
        _get(name).release()
