# filename: speech.py
# Speech commands for the M5StickS3 robot.
#
# Wraps the trained model (speech_model.py from the Speech page) and the
# stick's microphone in a background thread, so a program only has to ask
# what was heard. The same API exists in the browser simulator.
#
#   import speech
#   speech.start()
#   while True:
#       cmd = speech.wait_for_command()
#       if cmd == 'forward': ...
#
# Needs the StickS3 speech firmware (frozen sticks3 + speech_commands
# modules) and a speech_model.py on the device. Not available on the
# Max V1 robot, which has no microphone: use wonder_echo there.
import time

_labels = []
_last = None
_pending = None
_running = False
_thread_started = False

# Recognition covers the last ~1 s of audio; this chunk is the slide step
# between evaluations (5120 bytes = 160 ms at 16 kHz 16-bit mono). The
# ~1 s window re-hits a word several times, so accept one command per
# DEBOUNCE_MS at most.
_CHUNK_BYTES = 5120
_DEBOUNCE_MS = 1000


def start(model=None, threshold=70, grace_ms=2000):
    """Load the model and start listening in the background.

    model:     ignored on the device (the uploaded speech_model.py is the
               model); accepted so simulator programs run unchanged.
    threshold: minimum probability (0-100) to accept a word.
    grace_ms:  delay before the thread starts. A running thread blocks
               MicroPython's soft reset, which locks the IDE out; the
               grace period leaves time to Ctrl-C at boot.
    """
    global _labels, _running, _thread_started
    try:
        import speech_model
        import sticks3
        import _thread
    except ImportError:
        raise OSError("speech needs the StickS3 speech firmware and a speech_model.py "
                      "trained on the Speech page (upload it with the IDE)")
    if _thread_started:
        _running = True
        return
    _labels = list(speech_model.labels)
    mic = sticks3.microphone()
    if grace_ms:
        time.sleep_ms(grace_ms)
    _running = True
    _thread_started = True
    _thread.stack_size(24 * 1024)
    _thread.start_new_thread(_worker, (mic, speech_model, threshold))
    print("speech: listening for", ", ".join(l for l in _labels if l != '[OTHER]'))


def _worker(mic, speech_model, threshold):
    global _last, _pending
    buf = bytearray(_CHUNK_BYTES)
    last_ms = -_DEBOUNCE_MS
    try:
        while _running:
            mic.readinto(buf)
            label, prob = speech_model.predict(buf)
            if label != '[OTHER]' and prob > threshold:
                now = time.ticks_ms()
                if time.ticks_diff(now, last_ms) >= _DEBOUNCE_MS:
                    last_ms = now
                    _last = label
                    _pending = label
            # Brief yield so the USB stack and other tasks are serviced.
            time.sleep_ms(5)
    except BaseException as e:
        # Surface thread crashes instead of silently wedging the board.
        print('speech thread died:', repr(e))


def stop():
    """Stop listening. Call this before the program ends so soft reset works."""
    global _running
    _running = False
    time.sleep_ms(300)


def labels():
    """The command words of the loaded model (without the '[OTHER]' class)."""
    return [l for l in _labels if l != '[OTHER]']


def get_command():
    """Next unread recognized command, or None."""
    global _pending
    cmd = _pending
    _pending = None
    return cmd


def last_command():
    """Most recent recognized command (not consumed)."""
    return _last


def wait_for_command(timeout_ms=None):
    """Block until a command is heard; returns it, or None on timeout."""
    t0 = time.ticks_ms()
    while True:
        cmd = get_command()
        if cmd:
            return cmd
        if timeout_ms is not None and time.ticks_diff(time.ticks_ms(), t0) >= timeout_ms:
            return None
        time.sleep_ms(20)


def is_listening():
    return _running
