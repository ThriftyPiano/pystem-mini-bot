"""Record the StickS3 robot's microphone over USB into a 16 kHz mono WAV.

Made for the one-time motor-noise recordings the Speech page trains with
(speech-commands/motor*.wav): the clip is captured on the stick into PSRAM,
streamed back as base64 over the raw REPL and written as a WAV here.

The REPL is busy while recording, so --drive runs a wheel pattern
(forward, backward, spin left, spin right, 2 s each) during the capture —
put the robot on the floor with room to move, or hold it with the wheels
free. Needs the SDK (config/motor/motor_pair) on the device for --drive.

Usage:
    ROBOT_PORT=/dev/ttyACM0 python3 -m util.record_mic speech-commands/motor1.wav --seconds 20 --drive
"""
import argparse
import base64
import sys
import wave

from util.repl import RawREPL

RATE = 16000

DEVICE_CODE = r"""
import time, gc
import sticks3
SECONDS = {seconds}
DRIVE = {drive}
n = SECONDS * {rate} * 2
chunk = bytearray(5120)
pos = 0
if DRIVE:
    import motor, motor_pair
    motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)
    pattern = (
        lambda: motor_pair.move(motor_pair.PAIR_1, 0, velocity=360),
        lambda: motor_pair.move(motor_pair.PAIR_1, 0, velocity=-360),
        lambda: motor_pair.move_tank(motor_pair.PAIR_1, -180, 180),
        lambda: motor_pair.move_tank(motor_pair.PAIR_1, 180, -180),
    )
mic = sticks3.microphone()
mic.readinto(chunk)   # drop the codec's start-up samples
f = open('{tmp}', 'wb')
t0 = time.ticks_ms()
step = -1
try:
    while pos < n:
        if DRIVE:
            s = (time.ticks_diff(time.ticks_ms(), t0) // 2000) % len(pattern)
            if s != step:
                step = s
                pattern[s]()
        k = mic.readinto(chunk)
        m = min(k, n - pos)
        f.write(memoryview(chunk)[:m])
        pos += m
finally:
    if DRIVE:
        motor_pair.stop(motor_pair.PAIR_1)
    f.close()
print('RECORDED', pos)
"""

PULL_CODE = r"""
from ubinascii import b2a_base64
f = open('{tmp}', 'rb')
f.seek({off})
print('PIECE', b2a_base64(f.read({size}))[:-1].decode())
f.close()
"""

TMP_FILE = 'motor_rec.raw'
PIECE = 24000


def record(seconds, drive, repl):
    """Record on the device into a temporary file, then pull it in pieces
    (one raw-REPL round trip each) and delete it."""
    code = DEVICE_CODE.format(seconds=seconds, drive=drive, rate=RATE, tmp=TMP_FILE)
    out = repl.run(code, stream=True, echo=False, timeout=seconds + 60, end_marker=b'RECORDED')
    if 'RECORDED' not in out:
        raise RuntimeError('device did not finish the recording:\n' + out[-500:])
    tail = repl.run("print('OK')", stream=True, echo=False, timeout=5, end_marker=b'OK')
    n = int((out + tail).split('RECORDED')[1].split()[0])
    pcm = bytearray()
    while len(pcm) < n:
        code = PULL_CODE.format(tmp=TMP_FILE, off=len(pcm), size=min(PIECE, n - len(pcm)))
        out = repl.run(code, stream=True, echo=False, timeout=30, end_marker=b'\x04')
        if 'PIECE' not in out:
            raise RuntimeError('pull failed at %d:\n%s' % (len(pcm), out[-300:]))
        line = out[out.index('PIECE') + 6:].split()[0]
        pcm += base64.b64decode(line)
        print('\r  pulled %d / %d bytes' % (len(pcm), n), end='', flush=True)
    print()
    repl.run("import os; os.remove('%s')" % TMP_FILE, settle=0.5)
    return bytes(pcm)


def write_wav(path, pcm):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', help='output .wav path (e.g. speech-commands/motor1.wav)')
    ap.add_argument('--seconds', type=int, default=20, help='clip length (default 20, max 60)')
    ap.add_argument('--drive', action='store_true', help='run a wheel pattern during the capture')
    args = ap.parse_args()
    seconds = max(1, min(args.seconds, 60))
    print('Recording %d s%s...' % (seconds, ' while driving' if args.drive else ''))
    with RawREPL() as r:
        pcm = record(seconds, args.drive, r)
    write_wav(args.out, pcm)
    peak = max(abs(int.from_bytes(pcm[i:i + 2], 'little', signed=True)) for i in range(0, len(pcm), 2))
    print('Wrote %s: %.1f s, peak %d/32767' % (args.out, len(pcm) / 2 / RATE, peak))
    if peak < 500:
        print('Warning: very quiet - is the microphone working?', file=sys.stderr)


if __name__ == '__main__':
    main()
