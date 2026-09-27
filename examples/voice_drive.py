# Voice drive with the WonderEcho module (Max V1 robot only).
# Say "Hello Hiwonder", then "forward", "backward", "turn left",
# "turn right", "stop" or "dance". Each command runs until the next one.
# The StickS3 robot uses voice_speech.py instead.

import motor
import wonder_echo
import head
import time
from config import BOARD

if BOARD == 'sticks3':
    raise SystemExit("voice_drive.py needs the WonderEcho on the Max V1 robot. "
                     "On the StickS3 robot run voice_speech.py instead.")

DRIVE_VELOCITY = 270   # deg/sec
TURN_VELOCITY  = 38    # deg/sec per wheel, ~34 deg/sec chassis yaw

# Port A = left wheel, port B = right wheel (mounted reversed).

def go_forward():
    motor.run(motor.PORT_A,  DRIVE_VELOCITY)
    motor.run(motor.PORT_B, -DRIVE_VELOCITY)

def go_backward():
    motor.run(motor.PORT_A, -DRIVE_VELOCITY)
    motor.run(motor.PORT_B,  DRIVE_VELOCITY)

def turn_left():
    motor.run(motor.PORT_A, -TURN_VELOCITY)
    motor.run(motor.PORT_B, -TURN_VELOCITY)

def turn_right():
    motor.run(motor.PORT_A,  TURN_VELOCITY)
    motor.run(motor.PORT_B,  TURN_VELOCITY)

def stop():
    motor.stop(motor.PORT_A)
    motor.stop(motor.PORT_B)

def _dance_poll(ms):
    # Sleep ~ms while still listening, so "stop" interrupts the dance.
    slept = 0
    while slept < ms:
        cmd = wonder_echo.read_command()
        if cmd != wonder_echo.CMD_NONE:
            return cmd
        time.sleep_ms(120)
        slept += 120
    return wonder_echo.CMD_NONE

def do_dance():
    # Kept moderate: two motors plus two servos slewing at once can brown
    # out the board.
    SPIN = 100
    POP  = 150
    ACC  = 450
    beat = 260
    c = 90

    def spin_cw():
        motor.run(motor.PORT_A,  SPIN, acceleration=ACC)
        motor.run(motor.PORT_B,  SPIN, acceleration=ACC)
    def spin_ccw():
        motor.run(motor.PORT_A, -SPIN, acceleration=ACC)
        motor.run(motor.PORT_B, -SPIN, acceleration=ACC)
    def pop_forward():
        motor.run(motor.PORT_A,  POP, acceleration=ACC)
        motor.run(motor.PORT_B, -POP, acceleration=ACC)
    def pop_back():
        motor.run(motor.PORT_A, -POP, acceleration=ACC)
        motor.run(motor.PORT_B,  POP, acceleration=ACC)

    moves = (
        (spin_cw,     lambda: head.look(c - 60, c + 30), 2),
        (spin_ccw,    lambda: head.look(c + 60, c + 30), 2),
        (pop_forward, lambda: head.tilt(c - 40),         1),
        (pop_back,    lambda: head.tilt(c + 40),         1),
    )

    interrupt = wonder_echo.CMD_NONE
    while interrupt == wonder_echo.CMD_NONE:
        for wheels, headmove, mult in moves:
            wheels()
            headmove()
            interrupt = _dance_poll(beat * mult)
            if interrupt != wonder_echo.CMD_NONE:
                break

    stop()
    head.center()
    head.release()

    # Run the interrupting drive command; never re-enter the dance from here.
    if interrupt not in (wonder_echo.CMD_STOP, wonder_echo.CMD_DANCE):
        entry = ACTIONS.get(interrupt)
        if entry is not None:
            name, fn = entry
            print('-> %s' % name)
            fn()

ACTIONS = {
    wonder_echo.CMD_FORWARD:  ('forward',  go_forward),
    wonder_echo.CMD_BACKWARD: ('backward', go_backward),
    wonder_echo.CMD_LEFT:     ('left',     turn_left),
    wonder_echo.CMD_RIGHT:    ('right',    turn_right),
    wonder_echo.CMD_STOP:     ('stop',     stop),
    wonder_echo.CMD_DANCE:    ('dance',    do_dance),
}

print('Voice control ready. Say "Hello Hiwonder" then a command.')
print('Press Ctrl-C to exit.')

# Broadcast phrase 6 ("parking completed") announces that the program is running.
wonder_echo.speak(wonder_echo.TYPE_BROADCAST, 6)

try:
    while True:
        cmd = wonder_echo.read_command()
        if cmd != wonder_echo.CMD_NONE:
            entry = ACTIONS.get(cmd)
            if entry is not None:
                name, fn = entry
                print('-> %s' % name)
                fn()
            else:
                print('unknown cmd id: 0x%02x' % cmd)
        time.sleep_ms(150)
except KeyboardInterrupt:
    stop()
    print('Stopped.')
