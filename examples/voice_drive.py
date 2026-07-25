# ============================================
# VOICE DRIVE EXAMPLE - Drive Your Robot With Your Voice!
# ============================================
# This program lets you control your robot by speaking commands.
# Each command runs the robot CONTINUOUSLY until you say a new one.
#
# HOW TO USE:
#   1. Power on the robot (the WonderEcho needs ~1 second to start).
#   2. Run this program.
#   3. Say "Hello Hiwonder" to wake the module up.
#   4. Then say one of: "forward", "backward", "turn left",
#      "turn right", "stop", "dance".
#   5. The robot keeps doing the action until you say another command.

# STEP 1: Import the libraries we need
# --------------------------------------------
import motor               # Per-motor velocity control (closed-loop)
import wonder_echo         # Voice recognition (Hiwonder WonderEcho)
import head                # Pan/tilt head servos (for the dance)
import time

# STEP 2: How fast to move
# --------------------------------------------
DRIVE_VELOCITY = 270   # forward/backward speed in deg/sec
TURN_VELOCITY  = 38    # in-place spin speed -> chassis ~34 deg/sec yaw rate.
                       # ~10 sec for a full 360 spin. The closed-loop
                       # integrator ramps PWM up to overcome static friction
                       # automatically, so the slow target works across
                       # different surfaces.

# STEP 3: Action functions
# --------------------------------------------
# Port A = left wheel, Port B = right wheel.
# The right motor is mounted reversed, so its forward-chassis direction
# is NEGATIVE port velocity. That's why each function below uses opposite
# signs on A and B for translation, and matching signs for rotation.

def go_forward():
    motor.run(motor.PORT_A,  DRIVE_VELOCITY)
    motor.run(motor.PORT_B, -DRIVE_VELOCITY)

def go_backward():
    motor.run(motor.PORT_A, -DRIVE_VELOCITY)
    motor.run(motor.PORT_B,  DRIVE_VELOCITY)

def turn_left():
    # Left wheel back, right wheel forward -> rotate CCW
    motor.run(motor.PORT_A, -TURN_VELOCITY)
    motor.run(motor.PORT_B, -TURN_VELOCITY)

def turn_right():
    # Left wheel forward, right wheel back -> rotate CW
    motor.run(motor.PORT_A,  TURN_VELOCITY)
    motor.run(motor.PORT_B,  TURN_VELOCITY)

def stop():
    motor.stop(motor.PORT_A)
    motor.stop(motor.PORT_B)

def do_dance():
    # Whole-body dance: the wheels wiggle and spin while the head grooves.
    # motor.run() is non-blocking (a background timer holds each wheel at its
    # target velocity), so we kick off a wheel move and layer head moves on
    # top, then change it up. Kept moderate on purpose: two motors plus two
    # servos moving at once draws a lot of current, and big simultaneous
    # slews can brown out the board -- so gentle acceleration and mostly
    # in-place spins (short forward/back pops add flavor without wandering).
    SPIN = 110   # deg/sec, lively in-place spin
    POP  = 170   # deg/sec, short forward/back pop
    ACC  = 600   # gentler accel -> smaller current spike than the 1000 default
    beat = 260

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

    c = 90  # head center
    for _ in range(2):
        # spin one way, head leads into the turn
        spin_cw();  head.look(c - 60, c + 30)
        time.sleep_ms(beat * 2)
        # spin back the other way
        spin_ccw(); head.look(c + 60, c + 30)
        time.sleep_ms(beat * 2)
        # little forward/back pops with head bobs
        pop_forward(); head.tilt(c - 40)
        time.sleep_ms(beat)
        pop_back();    head.tilt(c + 40)
        time.sleep_ms(beat)

    stop()            # wheels off
    head.center()     # head back to rest
    head.release()    # servos limp

ACTIONS = {
    wonder_echo.CMD_FORWARD:  ('forward',  go_forward),
    wonder_echo.CMD_BACKWARD: ('backward', go_backward),
    wonder_echo.CMD_LEFT:     ('left',     turn_left),
    wonder_echo.CMD_RIGHT:    ('right',    turn_right),
    wonder_echo.CMD_STOP:     ('stop',     stop),
    wonder_echo.CMD_DANCE:    ('dance',    do_dance),
}

# STEP 4: Main loop - listen and dispatch
# --------------------------------------------
print('Voice control ready. Say "Hello Hiwonder" then a command.')
print('Press Ctrl-C to exit.')

# Audible "I'm alive" announcement so you know voice_drive is running.
# TYPE_BROADCAST phrase id 6 = "parking completed" on the stock firmware.
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

# ============================================
# EXPERIMENT IDEAS:
# ============================================
# 1. Make a "fast" mode: when you say "forward" twice in a row, double
#    DRIVE_VELOCITY. (Track the previous command in a variable.)
# 2. Use wonder_echo.speak(wonder_echo.TYPE_COMMAND, 1) to have the
#    robot acknowledge each command audibly.
# 3. Add a safety stop: if color_sensor.reflection() drops near zero
#    (edge of table!), stop even if no voice command came in.
# ============================================
