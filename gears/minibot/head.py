# filename: head.py  (GEARS simulator build)
# The simulated Mini Bot has no pan/tilt head. The API is kept so programs
# that move the head still run: the angles are tracked, reported in the
# simulator console via minibot_sim, and the timed moves take real time.
import time
import minibot_sim
from config import HEAD_CONFIG

_position = {'pan': HEAD_CONFIG['center_angle'], 'tilt': HEAD_CONFIG['center_angle']}

def _clamp(degrees):
    return max(HEAD_CONFIG['min_angle'], min(HEAD_CONFIG['max_angle'], degrees))

def _move(name, degrees):
    _position[name] = _clamp(degrees)
    minibot_sim.head_moved(_position['pan'], _position['tilt'])

def pan(degrees):
    _move('pan', degrees)

def tilt(degrees):
    _move('tilt', degrees)

def look(pan_deg, tilt_deg):
    _move('pan', pan_deg)
    _move('tilt', tilt_deg)

def center():
    look(HEAD_CONFIG['center_angle'], HEAD_CONFIG['center_angle'])

def nod(times=2, *, amount=20, speed_ms=250):
    c = HEAD_CONFIG['center_angle']
    for _ in range(times):
        tilt(c - amount); time.sleep_ms(speed_ms)
        tilt(c + amount); time.sleep_ms(speed_ms)
    tilt(c)

def shake(times=2, *, amount=30, speed_ms=250):
    c = HEAD_CONFIG['center_angle']
    for _ in range(times):
        pan(c - amount); time.sleep_ms(speed_ms)
        pan(c + amount); time.sleep_ms(speed_ms)
    pan(c)

def dance(times=2, *, beat_ms=250):
    c = HEAD_CONFIG['center_angle']
    for _ in range(times):
        look(c - 75, c - 50); time.sleep_ms(beat_ms)
        look(c + 75, c + 50); time.sleep_ms(beat_ms)
        look(c + 75, c - 50); time.sleep_ms(beat_ms)
        look(c - 75, c + 50); time.sleep_ms(beat_ms)
    center()

def get_position(name):
    return _position[name]

def release():
    pass
