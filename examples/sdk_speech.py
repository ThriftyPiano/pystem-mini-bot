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
# While a program is listening, the robot also advertises over Bluetooth
# as "Mini Bot XXXX": the Speech page's "Connect Robot" button records clips
# through the robot's own microphone (motor noise included) to train on.
# Nothing extra to call - any program that uses speech.start() serves it.
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
_model = None
_threshold = 70

# Recognition covers the last ~1 s of audio; this chunk is the slide step
# between evaluations (5120 bytes = 160 ms at 16 kHz 16-bit mono). The
# ~1 s window re-hits a word several times, so accept one command per
# DEBOUNCE_MS at most.
_CHUNK_BYTES = 5120
_DEBOUNCE_MS = 1000


def start(model=None, threshold=70, grace_ms=2000, recorder=True):
    """Load the model and start listening in the background.

    model:     ignored on the device (the uploaded speech_model.py is the
               model); accepted so simulator programs run unchanged.
    threshold: minimum probability (0-100) to accept a word.
    grace_ms:  delay before the thread starts. A running thread blocks
               MicroPython's soft reset, which locks the IDE out; the
               grace period leaves time to Ctrl-C at boot.
    recorder:  also advertise over Bluetooth as "Mini Bot XXXX" so the Speech
               page can record training clips through this microphone
               while the program runs. Pass False to keep the radio off.
    """
    global _labels, _model, _threshold, _running, _thread_started
    try:
        import speech_model
        import sticks3
        import _thread
    except ImportError:
        raise OSError("speech needs the StickS3 speech firmware and a speech_model.py "
                      "trained on the Speech page (upload it with the IDE)")
    _model = speech_model
    _labels = list(speech_model.labels)
    _threshold = threshold
    if recorder:
        _recorder_start()
    if _thread_started:
        _running = True
        return
    mic = sticks3.microphone()
    if grace_ms:
        time.sleep_ms(grace_ms)
    _running = True
    _thread_started = True
    _thread.stack_size(24 * 1024)
    _thread.start_new_thread(_worker, (mic, speech_model))
    print("speech: listening for", ", ".join(l for l in _labels if l != '[OTHER]'))


def _worker(mic, model):
    global _last, _pending, _thread_started
    buf = bytearray(_CHUNK_BYTES)
    last_ms = -_DEBOUNCE_MS
    try:
        while _running:
            mic.readinto(buf)
            if _rec_capturing:
                _rec_feed(buf)
            label, prob = model.predict(buf)
            if label != '[OTHER]' and prob > _threshold:
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
    finally:
        # Let start() spin up a fresh thread after stop().
        _thread_started = False


def stop():
    """Stop listening. Call this before the program ends so soft reset works."""
    global _running
    _running = False
    _recorder_stop()
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


def recorder_connected():
    """True while the Speech page is connected over Bluetooth."""
    return _conn is not None


# ---------------------------------------------------------------------
# Bluetooth recorder
#
# One GATT service, which the Speech page finds with Web Bluetooth:
#   CTRL (write)   b'rec <ms>'  capture <ms> of microphone audio (100-10000)
#                  b'stop'      abandon a capture
#   DATA (notify)  b'S' + text  status: b'Srec' when the capture starts
#                  b'H' + <I total bytes> + <H sample rate>   clip header
#                  b'D' + pcm   16-bit little-endian mono, MTU-sized pieces
#                  b'E'         end of clip
# The listening thread copies its microphone chunks into the clip buffer
# (it keeps recognising meanwhile, so the robot still obeys commands), and
# a short-lived thread streams the finished clip so neither the listener
# nor the program's control loop waits on the radio.
# ---------------------------------------------------------------------
_SVC_UUID = '7a5e0001-9b4c-4f2e-8a2d-3c1e5d6f7a01'
_CTRL_UUID = '7a5e0002-9b4c-4f2e-8a2d-3c1e5d6f7a01'
_DATA_UUID = '7a5e0003-9b4c-4f2e-8a2d-3c1e5d6f7a01'
_NAME = 'Mini Bot'      # + last two MAC bytes, so several robots can be on at once
_name = _NAME
_SAMPLE_RATE = 16000
_BYTES_PER_MS = 32          # 16 kHz x 16-bit mono
_MAX_REC_MS = 10000

_ble = None
_conn = None
_mtu = 23
_ctrl_h = None
_data_h = None
_rec_buf = None
_rec_pos = 0
_rec_capturing = False
_rec_sending = False


def _recorder_start():
    global _ble, _ctrl_h, _data_h
    if _ble is not None:
        return
    try:
        import bluetooth
    except ImportError:
        print('speech: no bluetooth module in this firmware, recorder off')
        return
    global _name
    ble = bluetooth.BLE()
    ble.active(True)
    mac = ble.config('mac')[1]
    _name = '%s %02X%02X' % (_NAME, mac[-2], mac[-1])
    ble.config(gap_name=_name, mtu=517)
    ble.irq(_ble_irq)
    ((_ctrl_h, _data_h),) = ble.gatts_register_services((
        (bluetooth.UUID(_SVC_UUID), (
            (bluetooth.UUID(_CTRL_UUID), 0x0008 | 0x0004),   # write, write-no-response
            (bluetooth.UUID(_DATA_UUID), 0x0010 | 0x0002),   # notify, read
        )),
    ))
    ble.gatts_set_buffer(_ctrl_h, 32)
    _ble = ble
    _advertise(ble)
    print('speech: recorder ready, connect from the Speech page as "%s"' % _name)


def _advertise(ble):
    import bluetooth
    # The 128-bit service UUID goes in the advertisement (what the Speech
    # page filters on); the name fits in the scan response.
    adv = b'\x02\x01\x06' + b'\x11\x07' + bytes(bluetooth.UUID(_SVC_UUID))
    name = _name.encode()
    resp = bytes([len(name) + 1, 0x09]) + name
    ble.gap_advertise(200000, adv_data=adv, resp_data=resp)


def _recorder_stop():
    global _ble, _conn, _rec_buf, _rec_capturing
    _rec_capturing = False
    _rec_buf = None
    _conn = None
    if _ble is not None:
        try:
            _ble.active(False)
        except Exception:
            pass
        _ble = None


def _ble_irq(event, data):
    global _conn, _mtu, _rec_capturing, _rec_buf
    if event == 1:                          # central connected
        _conn = data[0]
        _mtu = 23
    elif event == 2:                        # central disconnected
        _conn = None
        _rec_capturing = False
        _rec_buf = None
        if _ble is not None:
            _advertise(_ble)
    elif event == 21:                       # MTU exchanged
        _mtu = data[1]
    elif event == 3 and data[1] == _ctrl_h and _ble is not None:  # write to CTRL
        _rec_command(bytes(_ble.gatts_read(_ctrl_h)))


def _rec_command(cmd):
    global _rec_buf, _rec_pos, _rec_capturing
    parts = cmd.split()
    if not parts:
        return
    if parts[0] == b'stop':
        _rec_capturing = False
        _rec_buf = None
        _status(b'stopped')
    elif parts[0] == b'rec':
        if _rec_capturing or _rec_sending:
            _status(b'busy')
            return
        try:
            ms = int(parts[1]) if len(parts) > 1 else 1000
        except ValueError:
            ms = 1000
        ms = min(max(ms, 100), _MAX_REC_MS)
        _rec_buf = bytearray(ms * _BYTES_PER_MS)
        _rec_pos = 0
        _rec_capturing = True
        _status(b'rec')


def _status(text):
    try:
        _notify(b'S' + text, retries=20)
    except Exception:
        pass


def _rec_feed(buf):
    """Called by the listening thread with each microphone chunk."""
    global _rec_pos, _rec_capturing
    import _thread
    rec = _rec_buf
    if rec is None:
        _rec_capturing = False
        return
    n = min(len(buf), len(rec) - _rec_pos)
    rec[_rec_pos:_rec_pos + n] = memoryview(buf)[:n]
    _rec_pos += n
    if _rec_pos >= len(rec):
        _rec_capturing = False
        _thread.stack_size(12 * 1024)
        _thread.start_new_thread(_rec_send, (rec,))


def _rec_send(rec):
    global _rec_sending, _rec_buf
    import struct
    _rec_sending = True
    try:
        total = len(rec)
        _notify(b'H' + struct.pack('<IH', total, _SAMPLE_RATE))
        step = max(_mtu - 4, 16)
        mv = memoryview(rec)
        for i in range(0, total, step):
            if _conn is None:
                raise OSError('disconnected')
            _notify(b'D' + bytes(mv[i:i + step]))
        _notify(b'E')
    except Exception as e:
        print('speech recorder: send failed:', repr(e))
    finally:
        _rec_sending = False
        _rec_buf = None


def _notify(pkt, retries=400):
    """gatts_notify with retries: NimBLE raises ENOMEM while its transmit
    queue is full, which is the normal back-pressure signal here."""
    if _ble is None or _conn is None:
        raise OSError('not connected')
    for _ in range(retries):
        try:
            _ble.gatts_notify(_conn, _data_h, pkt)
            return
        except OSError:
            time.sleep_ms(5)
    raise OSError('notify timed out')
