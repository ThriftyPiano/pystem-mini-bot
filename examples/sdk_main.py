# filename: main.py
# Default program: shows where to program the robot, then voice control
# if a speech model is on the robot. Writing any program from the IDE replaces it.
import screen

try:
    import speech_model
except ImportError:
    speech_model = None

screen.show("Program me at", "robot.pystem", ".com")

if speech_model is not None:
    import time
    time.sleep(3)
    import motor
    import motor_pair
    import speech

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
