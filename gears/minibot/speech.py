# filename: speech.py  (GEARS simulator build)
# Same API as examples/sdk_speech.py. Recognition runs in the browser
# (speech-commands/runtime.js, the device's own WASM pipeline) on the model
# chosen on the simulator page; this module just reads what it heard.
import time
import minibot_sim

_last = None

def start(model=None, threshold=70, grace_ms=0):
    """Start listening. `model` (a session name) is informational here — the
    simulator page chooses the model; pass it anyway so the same program
    runs on the robot."""
    if not minibot_sim.speech_start():
        raise OSError("No speech model selected on the simulator page")
    print("speech: listening for", ", ".join(labels()))

def stop():
    minibot_sim.speech_stop()

def labels():
    """The command words of the loaded model (without the '[OTHER]' class)."""
    return [l for l in minibot_sim.speech_labels() if l != '[OTHER]']

def get_command():
    """Next unread recognized command, or None."""
    global _last
    word = minibot_sim.speech_command()
    if not word:
        return None
    _last = word
    return word

def last_command():
    return _last

def wait_for_command(timeout_ms=None):
    """Block until a command is heard; None on timeout."""
    t0 = time.ticks_ms()
    while True:
        cmd = get_command()
        if cmd:
            return cmd
        if timeout_ms is not None and time.ticks_diff(time.ticks_ms(), t0) >= timeout_ms:
            return None
        time.sleep_ms(20)

def is_listening():
    return bool(minibot_sim.speech_is_listening())
