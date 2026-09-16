# ============================================
# VOICE CONTROL WITH YOUR OWN SPEECH MODEL
# ============================================
# Train a model on the Speech page with the commands below (or your own),
# then run this on the StickS3 robot (write the model to the robot from
# the IDE too) or in the Simulator with that model selected.
import motor
import motor_pair
import speech

# The StickS3 has a screen; the Max V1 and the simulator do not.
try:
    import sticks3
    import vga1_16x32 as font
    lcd = sticks3.display()
except ImportError:
    lcd = None

def show(*lines):
    """Print the lines, and draw them on the screen when there is one
    (8 characters per line in the 16x32 font)."""
    print(*lines)
    if lcd is None:
        return
    lcd.fill(0)
    for i, s in enumerate(lines):
        lcd.text(font, str(s)[:8], 4, 20 + 45 * i, 0xFFFF)

motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)
show("Voice", "control", "starting")
speech.start()
show("Say a", "command", "Ready!")
print("Commands:", speech.labels())

try:
    while True:
        cmd = speech.wait_for_command()
        show("Heard:", cmd)
        if cmd == 'forward':
            motor_pair.move(motor_pair.PAIR_1, 0, velocity=360)
        elif cmd == 'backward':
            motor_pair.move(motor_pair.PAIR_1, 0, velocity=-360)
        elif cmd == 'left':
            motor_pair.move_tank(motor_pair.PAIR_1, -180, 180)
        elif cmd == 'right':
            motor_pair.move_tank(motor_pair.PAIR_1, 180, -180)
        elif cmd == 'stop':
            motor_pair.stop(motor_pair.PAIR_1)
finally:
    motor_pair.stop(motor_pair.PAIR_1)
    speech.stop()
    show("Stopped")
