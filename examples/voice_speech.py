# ============================================
# VOICE CONTROL WITH YOUR OWN SPEECH MODEL
# ============================================
# Train a model on the Speech page with the commands below (or your own),
# then run this on the StickS3 robot (write the model to the robot from
# the IDE too) or in the Simulator with that model selected.
import motor
import motor_pair
import speech
import screen   # screen.show() prints, and draws on the StickS3's screen

motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)
screen.show("Voice control", "starting...")
speech.start()
screen.show("Ready!", "Say a command")
print("Commands:", speech.labels())

try:
    while True:
        cmd = speech.wait_for_command()
        screen.show("Heard:", cmd)
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
    screen.show("Stopped")
