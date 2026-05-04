# ============================================
# VOICE DRIVE EXAMPLE - Drive Your Robot With Your Voice!
# ============================================
# This program lets you control your robot by speaking commands.
# It uses the Hiwonder WonderEcho voice module to listen for commands,
# then drives the wheels with the motor_pair module.
#
# HOW TO USE:
#   1. Power on the robot (the WonderEcho needs ~1 second to start).
#   2. Run this program (press the start button after upload).
#   3. Say "Hello Hiwonder" to wake the module up.
#   4. Then say one of: "forward", "backward", "turn left",
#      "turn right", "stop".
#   5. The robot will perform the matching action.

# STEP 1: Import the libraries we need
# --------------------------------------------
import motor               # Individual motor control (port names)
import motor_pair          # Drives the two wheels together
import wonder_echo         # Voice recognition + speech (Hiwonder WonderEcho)
import time

# STEP 2: Pair the motors
# --------------------------------------------
# Left motor on port A, right motor on port B - same as motor_control.py
print("Pairing motors...")
motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)

# STEP 3: How fast and how far to move per voice command
# --------------------------------------------
# These values are intentionally short so each command is a small,
# safe nudge. Increase them once you trust the setup.
DRIVE_DEGREES = 360 * 2    # 2 wheel rotations forward/backward (~38 cm)
DRIVE_VELOCITY = 360       # 360 deg/s = 1 rotation per second
TURN_DEGREES = 200         # in-place spin amount (tune for your wheels)
TURN_VELOCITY = 300

# STEP 4: Map each voice command id to a motion function
# --------------------------------------------
# wonder_echo.read_command() returns one of these ids:
#   CMD_FORWARD  = 0x01    "forward"
#   CMD_BACKWARD = 0x02    "backward"
#   CMD_LEFT     = 0x03    "turn left"
#   CMD_RIGHT    = 0x04    "turn right"
#   CMD_STOP     = 0x09    "stop"
#   CMD_NONE     = 0x00    nothing recognized
def go_forward():
    print("-> forward")
    motor_pair.move_for_degrees(motor_pair.PAIR_1, DRIVE_DEGREES, 0, velocity=DRIVE_VELOCITY)

def go_backward():
    print("-> backward")
    motor_pair.move_for_degrees(motor_pair.PAIR_1, -DRIVE_DEGREES, 0, velocity=DRIVE_VELOCITY)

def turn_left():
    print("-> turn left")
    # Tank turn: left wheel back, right wheel forward
    motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, TURN_DEGREES, -TURN_VELOCITY, TURN_VELOCITY)

def turn_right():
    print("-> turn right")
    # Tank turn: left wheel forward, right wheel back
    motor_pair.move_tank_for_degrees(motor_pair.PAIR_1, TURN_DEGREES, TURN_VELOCITY, -TURN_VELOCITY)

def stop():
    print("-> stop")
    motor_pair.stop(motor_pair.PAIR_1)

ACTIONS = {
    wonder_echo.CMD_FORWARD:  go_forward,
    wonder_echo.CMD_BACKWARD: go_backward,
    wonder_echo.CMD_LEFT:     turn_left,
    wonder_echo.CMD_RIGHT:    turn_right,
    wonder_echo.CMD_STOP:     stop,
}

# STEP 5: Main loop - listen and dispatch
# --------------------------------------------
print('Voice control ready. Say "Hello Hiwonder" then a command.')
print("Press Ctrl-C to exit.")

try:
    while True:
        cmd = wonder_echo.read_command()
        if cmd != wonder_echo.CMD_NONE:
            action = ACTIONS.get(cmd)
            if action is not None:
                action()
            else:
                # Recognized something, but not a command we handle.
                print("unknown command id:", hex(cmd))
        # Poll about 7x/second - fast enough to feel responsive,
        # slow enough not to thrash the I2C bus.
        time.sleep_ms(150)
except KeyboardInterrupt:
    motor_pair.stop(motor_pair.PAIR_1)
    print("Stopped.")

# ============================================
# EXPERIMENT IDEAS:
# ============================================
# 1. Make "forward" speed up each time (DRIVE_VELOCITY += 60).
# 2. Use wonder_echo.speak(wonder_echo.TYPE_COMMAND, 1) to have
#    the robot acknowledge each command audibly.
# 3. Add a "dance" command that runs your own move sequence when
#    you say "forward" twice in a row.
# 4. Combine with color_sensor.reflection() to refuse to drive
#    forward if the sensor sees an edge (no floor).
# ============================================
