# ============================================
# VOICE CONTROL WITH YOUR OWN SPEECH MODEL
# ============================================
# Train a model on the Speech page with the commands below (or your own),
# then run this on the StickS3 robot (upload speech_model.py too) or in
# the Simulator with that model selected.
import motor
import motor_pair
import speech

motor_pair.pair(motor_pair.PAIR_1, motor.PORT_A, motor.PORT_B)
speech.start()
print("Say: forward, backward, left, right, stop")

try:
    while True:
        cmd = speech.wait_for_command()
        print("heard:", cmd)
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
